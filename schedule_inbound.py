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
TARGET_USERS = [
    f"a1@{TENANT}",
    f"a2@{TENANT}",
    f"a3@{TENANT}",
    f"a4@{TENANT}",
]
BOT_NAME = f"BuddyBot72aa07a63b5ceeb2@{TENANT}"
JST = ZoneInfo("Asia/Tokyo")
MAX_WORKERS = 8  # 同時送信の最大並列数

# ====== 巡回時間と場所をこの辞書で一元管理 ======
# キー: "HH:MM"（巡回の“ラベル/目標時刻”）
# 値: その時刻に対応する場所名
LOCATION_MAP: Dict[str, str] = {}

# スケジューラ
sched = BlockingScheduler(
    timezone=JST,
    job_defaults={"coalesce": True, "misfire_grace_time": 120},
)
JOB_ID_PREFIX = "user_sched_"

# 送信文テンプレ（{now}, {label}, {place}, {lead}, {pre} が使用可）
# lead_minutes=0 のときは {pre} は "です"、>0 のときは "の{lead}分前です"
DEFAULT_TEXT = "定時巡回{label}（{place}）{pre}"

# ====== 共通ユーティリティ ======
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_JOB_ID_RE = re.compile(rf"^{JOB_ID_PREFIX}(\d{{3}})_([0-2]\d[0-5]\d)_(\d{{2}})$")
LabelMode = Literal["none", "next_hour_if_55"]  # （後方互換用だが実運用は辞書主導）

# GET用に追加
_lock = threading.RLock()
_times: List[str] = [] # "HH:MM" の配列を個々で保持

def get_times() -> List[str]:
    """現在登録されている時刻一覧を昇順で返す"""
    with _lock:
        return sorted(_times)

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

def _parse_job_id(job_id: str) -> Optional[Tuple[int, str, int]]:
    """
    JOB_ID_PREFIX + {連番3桁}_{通知時刻HHMM}_{lead分2桁}
    例: user_sched_000_0955_05  （9:55に通知、labelは10:00、lead=5）
    """
    m = _JOB_ID_RE.match(job_id)
    if not m:
        return None
    return int(m.group(1)), m.group(2), int(m.group(3))

def _hm_to_minutes(h: int, m: int) -> int:
    return h * 60 + m

def _minutes_to_hm(total: int) -> Tuple[int, int]:
    total %= 1440
    return total // 60, total % 60

def _timestr_to_hm(timestr: str) -> Tuple[int, int]:
    timestr = timestr.strip()
    if not _TIME_RE.match(timestr):
        raise ValueError(f"Invalid time: '{timestr}' (HH:MM)")
    h, m = map(int, timestr.split(":"))
    return h, m

def _format_hm(h: int, m: int) -> str:
    return f"{h:02d}:{m:02d}"

def _current_times_from_jobs() -> List[str]:
    """現在登録されている “通知時刻(HH:MM)” の一覧を昇順で返す"""
    hm_set = set()
    for j in sched.get_jobs():
        parsed = _parse_job_id(j.id)
        if not parsed:
            continue
        hhmm = parsed[1]  # 通知HHMM
        hm_set.add(f"{hhmm[:2]}:{hhmm[2:]}")
    return sorted(hm_set)

# ====== 場所辞書の設定 ======
def set_location_map(new_map: Dict[str, str]) -> Dict[str, str]:
    """
    'HH:MM' -> '場所名' のマップを丸ごと設定。キー/値を検証して反映。
    """
    global LOCATION_MAP
    if not isinstance(new_map, dict):
        raise ValueError("location_map must be a dict like {'HH:MM': '場所名', ...}")
    norm: Dict[str, str] = {}
    for k, v in new_map.items():
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"Invalid place for time '{k}': must be non-empty string")
        k = k.strip()
        if not _TIME_RE.match(k):
            raise ValueError(f"Invalid time key in location_map: '{k}' (HH:MM)")
        norm[k] = v.strip()
    LOCATION_MAP = norm
    return LOCATION_MAP

def get_location_map() -> Dict[str, str]:
    return dict(LOCATION_MAP)

# ====== スケジュール構築（辞書から一括） ======
def _make_job_func(label_time: str, lead_minutes: int, text_template: Optional[str]):
    """
    実行時に送る文面を作るジョブ。
    - label_time: 巡回の“ラベル/目標時刻” ("HH:MM")  … テンプレの {label} に入る
    - lead_minutes: 事前通知の分数。0 のとき “ちょうどの時刻”
    - 場所は LOCATION_MAP[label_time] を毎回参照（変更が即反映される）
    """
    def _job():
        now = datetime.now(JST)
        place = LOCATION_MAP.get(label_time, "")
        lead = lead_minutes
        pre = f"の{lead}分前です" if lead > 0 else "です"
        template = text_template or DEFAULT_TEXT
        text = template.format(
            now=now.strftime("%H:%M"),
            label=label_time,
            place=place,
            lead=lead,
            pre=pre,
        )
        send_inbound_all(text)
    return _job

def clear_scheduled_jobs():
    """このモジュールが登録したジョブを全削除"""
    for job in list(sched.get_jobs()):
        if job.id.startswith(JOB_ID_PREFIX):
            sched.remove_job(job.id)

def schedule_from_location_map(*, lead_minutes: int = 0, text_template: Optional[str] = None) -> Dict:
    """
    LOCATION_MAP を唯一のソースとして、全ジョブを組み直す。
    - lead_minutes=0   → その時刻ちょうどに通知
    - lead_minutes>0   → その時刻の lead 分前（前日跨ぎも自動調整）
    """
    if not isinstance(lead_minutes, int) or lead_minutes < 0 or lead_minutes >= 24 * 60:
        raise ValueError("lead_minutes must be an integer between 0 and 1439")

    # キーを昇順に
    label_times = sorted(LOCATION_MAP.keys(), key=lambda s: tuple(map(int, s.split(":"))))

    clear_scheduled_jobs()
    job_ids = []

    for idx, label in enumerate(label_times):
        lh, lm = _timestr_to_hm(label)
        fire_minutes = _hm_to_minutes(lh, lm) - lead_minutes
        fh, fm = _minutes_to_hm(fire_minutes)  # 0:00跨ぎもOK（前日の 23:xx などになる）

        trigger = CronTrigger(hour=fh, minute=fm, timezone=JST)  # 毎日
        job = _make_job_func(label_time=label, lead_minutes=lead_minutes, text_template=text_template)
        job_id = f"{JOB_ID_PREFIX}{idx:03d}_{fh:02d}{fm:02d}_{lead_minutes:02d}"
        sched.add_job(job, trigger, id=job_id, replace_existing=True)
        job_ids.append(job_id)

    print(datetime.now(JST), "Schedule rebuilt from LOCATION_MAP:",
          {"labels": label_times, "lead_minutes": lead_minutes})
    return {
        "labels": label_times,
        "lead_minutes": lead_minutes,
        "text_template": text_template or DEFAULT_TEXT,
        "job_ids": job_ids,
    }

# ====== テンプレ変更（辞書主導運用向け） ======
def set_text_template(new_template: str, *, lead_minutes: int = 0) -> Dict:
    """
    文面テンプレートを差し替え（{now}, {label}, {place}, {lead}, {pre} が使用可）
    差し替えに合わせて、現在の LOCATION_MAP からスケジュールを再構築。
    """
    if not isinstance(new_template, str) or not new_template:
        raise ValueError("text_template must be a non-empty string")
    return schedule_from_location_map(lead_minutes=lead_minutes, text_template=new_template)

# ====== 送信先ユーザーの追加/削除 ======
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

# ====== ステータス表示など ======
def _get_job_next_time(job):
    # APS 3.x / 4.x 互換で next run を取る
    try:
        nrt = getattr(job, "next_run_time", None)
        if nrt:
            return nrt.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    try:
        nft = getattr(job, "next_fire_time", None)
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
    """前面ブロックで起動"""
    print("Scheduler starting... Current:", get_current_schedule())
    sched.start()

def stop_scheduler(wait: bool = False):
    """停止（通常は使わない）"""
    sched.shutdown(wait=wait)

# ====== 直接実行時の例 ======
if __name__ == "__main__":
    # ここで “時間→場所” を一元管理
    set_location_map({
        "11:48": "一階食品",
        "11:00": "二階テナント",
        "12:00": "駐車場",
        "13:00": "一階食品",
        "14:00": "二階テナント",
        "15:00": "三階駐車場",
        "16:00": "すべてのフロア",
    })

    # 辞書をもとに “その時間に通知” → lead_minutes=0
    schedule_from_location_map(lead_minutes=5)  # その時刻ちょうどに通知
    # もし「5分前に通知」したいなら: schedule_from_location_map(lead_minutes=5)

    # テンプレ変更もワンライナーで（任意）
    # set_text_template("まもなく{label}（{place}）{pre}", lead_minutes=5)

    print("Scheduler starting... Current:", get_current_schedule())
    sched.start()

# ====== バックグラウンド起動ラッパ ======
_scheduler_thread: Optional[threading.Thread] = None
_scheduler_lock = threading.Lock()


def start_in_background(
    *,
    lead_minutes: int = 0,
    text_template: Optional[str] = None,
) -> bool:
    """
    BlockingScheduler を別スレッドで起動する薄いラッパ。
    LOCATION_MAP を用いてスケジュールを構築する（idempotent）。
    """
    global _scheduler_thread
    with _scheduler_lock:
        if sched.running:
            return False

        # LOCATION_MAP をもとにスケジュール組み直し
        _ = schedule_from_location_map(lead_minutes=lead_minutes, text_template=text_template)

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
