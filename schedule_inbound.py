# send_inbound_schedule.py
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# ---- 設定 ----
URL = "https://ip0-254.science-arts.com/buddybot/peerchat"
BOT_TOKEN = "sAhXLR6fcsx_D1Iw99Ykd2N.MzMqR34ACvAL3EI8qnVsms5jbpa5Up2.nAMe69TAlCXsxgPWcsJg_7GqChwvYcEtaKjuc6rFblRRq5ooY3G38vPo845.01bOM_tkz3ydq6z0fQ3.WTb2X0r7ou_giuq66r83BNS_d2vY26wHaxTMdmlbv3bXXGgwxpEfpXtAqQif27_KkjA8431qsA7TagjZJB3xgazS4445I8F7SdsWFRBSB8f09Y8dkpwvcEwk2n5mTjQ06n8"
TENANT = "team.a"
TARGET_USER = f"a1@{TENANT}"
BOT_NAME = f"BuddyBot72aa07a63b5ceeb2@{TENANT}"
JST = ZoneInfo("Asia/Tokyo")
# --------------

def ensure_ascii(s: str) -> str:
    if any(ord(ch) > 127 for ch in s):
        raise ValueError(f"Header contains non-ASCII: {repr(s)}")
    return s

def send_inbound(text: str):
    headers = {"Authorization": ensure_ascii(f"Bearer {BOT_TOKEN.strip()}")}
    parameter = {
        "chatBotName": BOT_NAME,
        "targetUserName": TARGET_USER,
        "language": 1,
        "type": 4,
        "text": text
    }
    files = {"parameter": (None, json.dumps(parameter, ensure_ascii=False), "application/json")}
    resp = requests.post(URL, headers=headers, files=files, timeout=30)
    print(datetime.now(JST), "HTTP", resp.status_code, resp.text)

def send_5min_before_top_of_hour():
    """次の“ちょうどの時刻”の5分前に相当するタイミングで呼ばれる想定。
    例: 09:55に呼ばれたら10:00の5分前として扱う。
    """
    now = datetime.now(JST)
    target = (now + timedelta(minutes=5)).replace(minute=0, second=0, microsecond=0)
    send_inbound(f"定時巡回時刻{target.strftime('%H:%M')} 5分前です")

if __name__ == "__main__":
    # APScheduler のデフォルト動作を安定化
    sched = BlockingScheduler(
        timezone=JST,
        job_defaults={
            "coalesce": True,           # 遅延時は実行をまとめる
            "misfire_grace_time": 120,  # 最大2分の遅延を許容
        },
    )

    # 毎日 09:55〜15:55（=10:00〜16:00の“5分前”）に実行
    # hour=9-15, minute=55, timezone=JST
    trigger = CronTrigger(hour="9-15", minute=55, timezone=JST)
    sched.add_job(send_5min_before_top_of_hour, trigger, id="hourly_5min_before", replace_existing=True)

    print("スケジュール設定完了。以下の時刻に送信します（JST）：12:55, 10:55, 11:55, 12:55, 13:55, 14:55, 15:55")
    sched.start()
