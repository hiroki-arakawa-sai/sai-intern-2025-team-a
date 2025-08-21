# schedule_inbound.py
import json
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional, Dict, Literal, Tuple

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import threading

# ---- 設定 ----
URL = "https://ip0-254.science-arts.com/buddybot/peerchat"
BOT_TOKEN = "sAhXLR6fcsx_D1Iw99Ykd2N.MzMqR34ACvAL3EI8qnVsms5jbpa5Up2.nAMe69TAlCXsxgPWcsJg_7GqChwvYcEtaKjuc6rFblRRq5ooY3G38vPo845.01bOM_tkz3ydq6z0fQ3.WTb2X0r7ou_giuq66r83BNS_d2vY26wHaxTMdmlbv3bXXGgwxpEfpXtAqQif27_KkjA8431qsA7TagjZJB3xgazS4445I8F7SdsWFRBSB8f09Y8dkpwvcEwk2n5mTjQ06n8"
TENANT = "team.a"
TARGET_USERS = [  # ここに送り先を追加
    f"a1@{TENANT}",
    f"a2@{TENANT}",
    # f"a3@{TENANT}",
]
BOT_NAME = f"BuddyBot72aa07a63b5ceeb2@{TENANT}"
JST = ZoneInfo("Asia/Tokyo")
MAX_WORKERS = 8  # 同時送信の最大並列数

# 初期スケジュール（引数省略時に使用）
INITIAL_TIMES = ["09:44", "10:55", "11:55", "12:55", "13:55", "14:55", "15:55"]
INITIAL_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]

# スケジューラ（外部から再設定可能）
sched = BlockingScheduler(
    timezone=JST,
    job_defaults={"coalesce": True, "misfire_grace_time": 120},
)
JOB_ID_PREFIX = "user_sched_"
DEFAULT_TEXT = "定時巡回時刻{label} 5分前です"  # {now}, {label} をプレースホルダとして使用可能
# --------------

def ensure_ascii(s: str) -> str:
    if any(ord(ch) > 127 for ch in s):
        raise ValueError(f"Header contains non-ASCII: {repr(s)}")
    return s

def build_session() -> requests.Session:
    """接続再利用＋軽いリトライを行う Session を作成"""
    sess = requests.Session()
    retry = Retry(
        total=3, connect=3, read=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods={"POST"},
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    return sess

SESSION = build_session()

def send_inbound(text: str, target_user: str):
    headers = {"Authorization": ensure_ascii(f"Bearer {BOT_TOKEN.strip()}")}
    parameter = {
        "chatBotName": BOT_NAME,
        "targetUserName": target_user,
        "language": 1,
        "type": 4,
        "text": text,
    }
    files = {"parameter": (None, json.dumps(parameter, ensure_ascii=False), "application/json")}
    resp = SESSION.post(URL, headers=headers, files=files, timeout=(5, 30))
    ok_ng = "OK" if resp.ok else "NG"
    print(datetime.now(JST), target_user, ok_ng, resp.status_code, resp.text[:160])
    return resp

def send_inbound_all(text: str):
    """TARGET_USERS へ順不同並列で一括送信（重複を排除してから送る）"""
    users = list(dict.fromkeys(TARGET_USERS))
    results: Dict[str, Optional[int]] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, len(users)))) as ex:
        future_map = {ex.submit(send_inbound, text, u): u for u in users}
        for fut in as_completed(future_map):
            user = future_map[fut]
            try:
                resp = fut.result()
                results[user] = resp.status_code
            except Exception as e:
                print(datetime.now(JST), user, "EXC", repr(e))
                results[user] = None
    return results

# ====== ここから“曜日・時刻を受け取り反映する”ための追加コード ======

# 入力検証
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_WEEK_MAP_EN = {
    "mon":"mon","tue":"tue","wed":"wed","thu":"thu","fri":"fri","sat":"sat","sun":"sun",
    "monday":"mon","tuesday":"tue","wednesday":"wed","thursday":"thu","friday":"fri",
    "saturday":"sat","sunday":"sun",
}
_WEEK_MAP_JA = {"月":"mon","火":"tue","水":"wed","木":"thu","金":"fri","土":"sat","日":"sun"}

LabelMode = Literal["none", "next_hour_if_55"]

# ====== ここから “配列要素の指定削除・変更（追加/置換）” 用ユーティリティ ======

# 直近に反映された曜日を保持（apply_schedule_from_payloadで更新）
_LAST_WEEKDAYS: List[str] = []

# apply_schedule_from_payload をラップして _LAST_WEEKDAYS を同期
def _apply_and_remember(*, times: List[str], weekdays: List[str],
                        label_mode: LabelMode = "next_hour_if_55",
                        text_template: Optional[str] = None) -> Dict:
    global _LAST_WEEKDAYS
    state = apply_schedule_from_payload(
        times=times, weekdays=weekdays,
        label_mode=label_mode, text_template=text_template
    )
    _LAST_WEEKDAYS = state["weekdays"]
    return state

# 起動直後に __main__ で apply_schedule_from_payload を呼ばないケース向けの初期化
def _ensure_weekdays_initialized():
    global _LAST_WEEKDAYS
    if not _LAST_WEEKDAYS:
        _LAST_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]

# 既存ジョブIDから idx と HHMM を抽出
_JOB_ID_RE = re.compile(rf"^{JOB_ID_PREFIX}(\d{{3}})_([0-2]\d[0-5]\d)$")

def _parse_job_id(job_id: str) -> Optional[Tuple[int, str]]:
    m = _JOB_ID_RE.match(job_id)
    if not m:
        return None
    return int(m.group(1)), m.group(2)

def _timestr_to_hm(timestr: str) -> Tuple[int, int]:
    timestr = timestr.strip()
    if not _TIME_RE.match(timestr):
        raise ValueError(f"Invalid time: '{timestr}' (HH:MM)")
    h, m = map(int, timestr.split(":"))
    return h, m

def _suffix_from_time(timestr: str) -> str:
    h, m = _timestr_to_hm(timestr)
    return f"_{h:02d}{m:02d}"

def _list_job_ids_by_time(timestr: str) -> List[str]:
    suf = _suffix_from_time(timestr)
    return [j.id for j in sched.get_jobs() if j.id.startswith(JOB_ID_PREFIX) and j.id.endswith(suf)]

def _next_job_index() -> int:
    idxs: List[int] = []
    for j in sched.get_jobs():
        parsed = _parse_job_id(j.id)
        if parsed:
            idxs.append(parsed[0])
    return (max(idxs) + 1) if idxs else 0

def _current_times_from_jobs() -> List[str]:
    # 現在登録されている時刻（HH:MM）を一意化して昇順で返す
    hm_set = set()
    for j in sched.get_jobs():
        parsed = _parse_job_id(j.id)
        if not parsed:
            continue
        hhmm = parsed[1]
        hm_set.add(f"{hhmm[:2]}:{hhmm[2:]}")
    return sorted(hm_set)

# --- 時刻の追加/削除/置換 ---

def add_times(times: List[str]) -> Dict:
    """新規の時刻だけを追加（既存と重複する時刻はスキップ）"""
    _ensure_weekdays_initialized()
    norm = _validate_times(times)
    existing = set(_current_times_from_jobs())
    added_ids = []
    for t in norm:
        if t in existing:
            continue
        h, m = _timestr_to_hm(t)
        trigger = CronTrigger(day_of_week=",".join(_LAST_WEEKDAYS), hour=h, minute=m, timezone=JST)
        job = _make_job_func(h, m, "next_hour_if_55", None)  # 既定の mode/template を使う
        job_id = f"{JOB_ID_PREFIX}{_next_job_index():03d}_{h:02d}{m:02d}"
        sched.add_job(job, trigger, id=job_id, replace_existing=False)
        added_ids.append(job_id)
    return {"added_job_ids": added_ids, "times": _current_times_from_jobs(), "weekdays": _LAST_WEEKDAYS}

def remove_times(times: List[str]) -> Dict:
    """指定した時刻(HH:MM)のジョブをすべて削除"""
    removed = []
    for t in _validate_times(times):
        for jid in _list_job_ids_by_time(t):
            sched.remove_job(jid)
            removed.append(jid)
    return {"removed_job_ids": removed, "times": _current_times_from_jobs(), "weekdays": _LAST_WEEKDAYS}

def replace_time(old_time: str, new_time: str) -> Dict:
    """old_time を削除し new_time を追加（アトミック保証はしないが、順に実行）"""
    _ = remove_times([old_time])
    return add_times([new_time])

# --- 曜日の追加/削除/一括設定 ---
# CronTrigger は day_of_week を後から直接変えられないため、全ジョブを再作成する。

def set_weekdays(weekdays: List[str]) -> Dict:
    """曜日を与え直し（現在の時刻は維持）"""
    norm_wd = [_norm_weekday(w) for w in weekdays]
    if not norm_wd:
        raise ValueError("weekdays must not be empty")
    times_now = _current_times_from_jobs()
    return _apply_and_remember(times=times_now, weekdays=norm_wd)

def add_weekdays(days: List[str]) -> Dict:
    _ensure_weekdays_initialized()
    cur = set(_LAST_WEEKDAYS)
    for d in days:
        cur.add(_norm_weekday(d))
    return set_weekdays(sorted(cur))

def remove_weekdays(days: List[str]) -> Dict:
    _ensure_weekdays_initialized()
    cur = set(_LAST_WEEKDAYS)
    for d in days:
        cur.discard(_norm_weekday(d))
    if not cur:
        raise ValueError("Removing these weekdays would leave none.")
    return set_weekdays(sorted(cur))

# --- 文面テンプレートやラベルモードの変更 ---
# 既存ジョブの関数クロージャに反映させるため、全ジョブを組み直す。

def set_text_template(new_template: str) -> Dict:
    if not isinstance(new_template, str) or not new_template:
        raise ValueError("text_template must be a non-empty string")
    times_now = _current_times_from_jobs()
    _ensure_weekdays_initialized()
    return apply_schedule_from_payload(
        times=times_now, weekdays=_LAST_WEEKDAYS,
        text_template=new_template, label_mode="next_hour_if_55"
    )

def set_label_mode(new_mode: LabelMode) -> Dict:
    if new_mode not in ("none", "next_hour_if_55"):
        raise ValueError("label_mode must be 'none' or 'next_hour_if_55'")
    times_now = _current_times_from_jobs()
    _ensure_weekdays_initialized()
    return apply_schedule_from_payload(
        times=times_now, weekdays=_LAST_WEEKDAYS,
        label_mode=new_mode
    )

# --- 送信先ユーザーの追加/削除 ---

def add_target_users(users: List[str]) -> List[str]:
    """TARGET_USERS に追加（重複は除去のうえ末尾へ）"""
    global TARGET_USERS
    seen = set(TARGET_USERS)
    for u in users:
        if u not in seen:
            TARGET_USERS.append(u)
            seen.add(u)
    return TARGET_USERS

def remove_target_users(users: List[str]) -> List[str]:
    """TARGET_USERS から削除"""
    global TARGET_USERS
    remove_set = set(users)
    TARGET_USERS = [u for u in TARGET_USERS if u not in remove_set]
    return TARGET_USERS
# ====== ここまで ======

def _norm_weekday(w: str) -> str:
    w0 = w.strip().lower()
    if w0 in _WEEK_MAP_EN:
        return _WEEK_MAP_EN[w0]
    # 日本語1文字にも対応（"月" など）
    if w in _WEEK_MAP_JA:
        return _WEEK_MAP_JA[w]
    raise ValueError(f"Invalid weekday: {w}")

def _validate_times(times: List[str]) -> List[str]:
    out = []
    for t in times:
        t = t.strip()
        if not _TIME_RE.match(t):
            raise ValueError(f"Invalid time: '{t}' (HH:MM)")
        out.append(t)
    return out

def _compute_label(now: datetime, h: int, m: int, mode: LabelMode) -> str:
    if mode == "next_hour_if_55" and m == 55:
        target = (now + timedelta(minutes=5)).replace(minute=0, second=0, microsecond=0)
        return target.strftime("%H:%M")
    return f"{h:02d}:{m:02d}"

def _make_job_func(h: int, m: int, label_mode: LabelMode, text_template: Optional[str]):
    """指定された時刻に呼ばれるジョブ。文面に {label}, {now} を埋め込み。"""
    def _job():
        now = datetime.now(JST)
        label = _compute_label(now, h, m, label_mode)
        template = text_template or DEFAULT_TEXT
        text = template.format(now=now.strftime("%H:%M"), label=label)
        send_inbound_all(text)
    return _job

def clear_scheduled_jobs():
    """このモジュールが登録したジョブを全削除"""
    for job in list(sched.get_jobs()):
        if job.id.startswith(JOB_ID_PREFIX):
            sched.remove_job(job.id)

def apply_schedule_from_payload(
    *,
    times: List[str],
    weekdays: List[str],
    label_mode: LabelMode = "next_hour_if_55",
    text_template: Optional[str] = None,
) -> Dict:
    """
    外部から渡された“曜日＋時刻”を検証し、現在のスケジュールを全入れ替えする。
    """
    # 検証・正規化
    norm_times = _validate_times(times)
    if not weekdays:
        raise ValueError("weekdays must not be empty")
    norm_weekdays = [_norm_weekday(w) for w in weekdays]

    # 既存ジョブを削除 → 追加
    clear_scheduled_jobs()
    dow_expr = ",".join(norm_weekdays)  # 例: "mon,tue,wed"
    job_ids = []
    for idx, t in enumerate(norm_times):
        h, m = map(int, t.split(":"))
        trigger = CronTrigger(day_of_week=dow_expr, hour=h, minute=m, timezone=JST)
        job = _make_job_func(h, m, label_mode, text_template)
        job_id = f"{JOB_ID_PREFIX}{idx:03d}_{h:02d}{m:02d}"
        sched.add_job(job, trigger, id=job_id, replace_existing=True)
        job_ids.append(job_id)

    print(datetime.now(JST), "Schedule updated:",
          {"times": norm_times, "weekdays": norm_weekdays, "label_mode": label_mode})
    return {
        "times": norm_times,
        "weekdays": norm_weekdays,
        "label_mode": label_mode,
        "text_template": text_template or DEFAULT_TEXT,
        "job_ids": job_ids,
    }

def _get_job_next_time(job):
    try:
        nrt = getattr(job, "next_run_time", None)  # APS 3.x
        if nrt:
            return nrt.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    try:
        nft = getattr(job, "next_fire_time", None)  # APS 4.x
        if nft:
            return nft.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    # トリガから推定
    try:
        now = datetime.now(JST)
        if hasattr(job, "trigger") and hasattr(job.trigger, "get_next_fire_time"):
            nxt = job.trigger.get_next_fire_time(None, now)
            if nxt:
                if nxt.tzinfo is None:
                    nxt = nxt.replace(tzinfo=JST)
                return nxt.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None

def get_current_schedule() -> Dict:
    jobs = [j for j in sched.get_jobs() if j.id.startswith(JOB_ID_PREFIX)]
    jobs.sort(key=lambda j: j.id)
    return {
        "jobs": [{"id": j.id, "next_run_time": _get_job_next_time(j)} for j in jobs],
        "count": len(jobs),
    }

def start_scheduler():
    """外部プロセスから起動制御したい場合に使用（BlockingScheduler のため前面でブロック）"""
    print("Scheduler starting... Current:", get_current_schedule())
    sched.start()

def stop_scheduler(wait: bool = False):
    """外部プロセスから停止（通常は使わない）"""
    sched.shutdown(wait=wait)

# ====== 直接実行時（任意の初期スケジュールは登録しない） ======
if __name__ == "__main__":
    # 例: 初期スケジュールを入れたい場合は以下をアンコメント
    apply_schedule_from_payload(
        times=["09:56","10:55","11:55","12:55","13:55","14:55","15:35"],
        weekdays=["mon","tue","wed","thu","fri"],
    )
    print("Scheduler starting... Current:", get_current_schedule())
    sched.start()

# ==== バックグラウンド起動用の薄いラッパ ====
_scheduler_thread: Optional[threading.Thread] = None
_scheduler_lock = threading.Lock()

def start_in_background(
    *,
    initial_times: Optional[List[str]] = None,
    initial_weekdays: Optional[List[str]] = None,
    label_mode: LabelMode = "next_hour_if_55",
    text_template: Optional[str] = None,
) -> bool:
    """
    BlockingScheduler を別スレッドで起動する薄いラッパ。
    既に起動中なら何もしない（idempotent）。
    引数が省略された場合は INITIAL_TIMES / INITIAL_WEEKDAYS を使う。
    既にジョブ登録がある場合は再適用しない。
    """
    global _scheduler_thread, _LAST_WEEKDAYS
    with _scheduler_lock:
        if sched.running:
            return False

        # まだジョブが無ければ初期スケジュールを適用
        need_bootstrap = not [j for j in sched.get_jobs() if j.id.startswith(JOB_ID_PREFIX)]
        times = initial_times if initial_times is not None else INITIAL_TIMES
        weekdays = initial_weekdays if initial_weekdays is not None else INITIAL_WEEKDAYS
        if need_bootstrap and times and weekdays:
            state = apply_schedule_from_payload(
                times=times,
                weekdays=weekdays,
                label_mode=label_mode,
                text_template=text_template,
            )
            # 内部状態も揃えておく（add_times などで使用）
            _LAST_WEEKDAYS = state["weekdays"]

        t = threading.Thread(target=start_scheduler, daemon=True)
        t.start()
        _scheduler_thread = t
        print("[scheduler] background thread started")
        return True

def is_running() -> bool:
    """スケジューラ実行中かどうか"""
    return sched.running

def stop_background(wait: bool = False) -> None:
    """バックグラウンドで起動したスケジューラを停止"""
    stop_scheduler(wait=wait)
    # Thread は daemon=True のため join は不要
