# send_inbound_schedule_multi.py
import json
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional, Dict, Literal

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

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
    results = {}
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

    Parameters
    ----------
    times : ["HH:MM", ...]  24時間表記
    weekdays : ["mon","tue",...] または ["月","火",...]
    label_mode : "next_hour_if_55" | "none"
    text_template : 省略時は DEFAULT_TEXT。{now} と {label} が使える。

    Returns
    -------
    dict : 反映後の状態（times, weekdays, label_mode, text_template, job_ids）
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
        times=["09:55","10:55","11:55","12:55","13:55","14:55","15:35"],
        weekdays=["mon","tue","wed","thu","fri"],
    )

    print("Scheduler starting... Current:", get_current_schedule())
    sched.start()
