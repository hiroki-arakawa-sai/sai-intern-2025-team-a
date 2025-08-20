# send_inbound_schedule_multi.py
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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
    print(datetime.now(JST), target_user, ok_ng, resp.status_code, resp.text)
    return resp

def send_inbound_all(text: str):
    """TARGET_USERS へ順不同並列で一括送信（重複を排除してから送る）"""
    # 重複除去しつつ順序維持
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

def send_5min_before_top_of_hour():
    """次の“ちょうどの時刻”の5分前に呼ばれる想定。例: 09:55→10:00基準"""
    now = datetime.now(JST)
    target = (now + timedelta(minutes=5)).replace(minute=0, second=0, microsecond=0)
    text = f"定時巡回時刻{target.strftime('%H:%M')} 5分前です"
    send_inbound_all(text)

if __name__ == "__main__":
    sched = BlockingScheduler(
        timezone=JST,
        job_defaults={"coalesce": True, "misfire_grace_time": 120},
    )
    # 毎日 09:55〜15:55（=10:00〜16:00の“5分前”）に実行
    trigger = CronTrigger(hour="9-15", minute=50, timezone=JST)
    sched.add_job(send_5min_before_top_of_hour, trigger, id="hourly_5min_before", replace_existing=True)

    print("スケジュール設定完了。以下の時刻に送信します（JST）：09:55, 10:55, 11:55, 12:55, 13:55, 14:55, 15:55")
    print("送信対象：", ", ".join(TARGET_USERS))
    sched.start()
