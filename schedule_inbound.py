# send_inbound_at_1113.py
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.date import DateTrigger

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

if __name__ == "__main__":
    # 今日の11:13 JST に設定
    run_at = datetime.now(JST).replace(hour=11, minute=15, second=0, microsecond=0)
    if run_at <= datetime.now(JST):
        # もしすでに過ぎていたら翌日にする
        run_at = run_at.replace(day=run_at.day + 1)

    print("次回送信予定:", run_at)

    sched = BlockingScheduler(timezone=JST)
    sched.add_job(lambda: send_inbound("定時テスト送信 11:12"), DateTrigger(run_date=run_at))
    sched.start()
