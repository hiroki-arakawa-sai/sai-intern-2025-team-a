import uvicorn
import db
import schedule_inbound as inbound

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field, constr
from typing import Dict, Any, List, Optional

# FastAPIアプリを初期化
app = FastAPI()


# ────────────────────────────────────────────────────────────────────
# Startup: 位置マップの設定 → スケジュール再構築 → バックグラウンド起動
# ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def _startup():
    # 1) 先に LOCATION_MAP を設定（必要に応じて編集）
    inbound.set_location_map({
        "11:00": "二階テナント",
        "11:48": "一階食品",
        "12:58": "駐車場",
        "13:02": "一階食品",
        "14:16": "二階テナント",
        "15:00": "三階駐車場",
        "16:00": "すべてのフロア",
    })

    # 2) すぐにスケジュールを再構築（ここでジョブが作られる）
    inbound.schedule_from_location_map(lead_minutes=0)

    # 3) その後、バックグラウンドでスケジューラを起動
    inbound.start_in_background(lead_minutes=0)

    # デバッグ出力
    print("[DEBUG] LOCATION_MAP:", inbound.get_location_map())
    print("[DEBUG] schedule:", inbound.get_current_schedule())


# ────────────────────────────────────────────────────────────────────
# 受信JSONのスキーマ定義
# ────────────────────────────────────────────────────────────────────
class Response(BaseModel):
    message: str

class ScheduleEntry(BaseModel):
    id: int = Field(..., ge=0)  # 数値（0以上）
    time: constr(pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')  # "HH:MM"
    area: str

class MemoRequest(BaseModel):
    chatBotName: str
    senderUserName: str
    languageIndex: int
    type: int
    data: str
    customParams: Dict[str, Any] = {}


# ────────────────────────────────────────────────────────────────────
# エンドポイント
# ────────────────────────────────────────────────────────────────────
@app.post("/test", response_model=Response)
async def receive_message():
    return Response(message="Hello World!")

@app.post("/test/memo", response_model=Response)
async def receive_message_memo(req: MemoRequest):
    db.save_message(req.senderUserName, req.data)
    print(f"[DEBUG] 受け取った data: {req.data}")
    print(f"[DEBUG] 送信者: {req.senderUserName} ")
    db.get_message()
    return Response(message=f"受け取ったデータ: {req.data}")

# 巡回エントリ（時間・場所）一覧を返す
@app.get("/schedule/entries")
async def get_entries():
    # LOCATION_MAP を [{id,time,area}, ...] で返す
    return inbound.get_location_list()

# 現在のジョブ一覧（id / next_run_time）
@app.get("/schedule/jobs")
async def get_jobs():
    return inbound.get_current_schedule()

# 受信ログ用フック（デバッグ）
#現在使用していない
#async def log_post_request(request: Request):
    body = await request.body()
    print("=== POST受信 ===")
    print("Headers:", dict(request.headers))
    print("Query:", dict(request.query_params))
    print("Raw body:", body.decode("utf-8", errors="ignore"))
    return body

@app.post("/hook")
async def hook(entries: List[ScheduleEntry]):
    """
    受け取った配列 [{id,time,area}, ...] で LOCATION_MAP を上書きし、スケジュールを再構築。
    """
    # 受信データ -> dict("HH:MM" -> "場所")
    new_map = {e.time: e.area for e in entries}

    # 置き換え（追加ではない）
    inbound.set_location_map(new_map)

    # スケジュール再構築（必要なら lead_minutes を変更）
    sched_info = inbound.schedule_from_location_map(lead_minutes=0)

    return {
        "ok": True,
        "received": len(entries),
        "location_map": inbound.get_location_map(),
        "list": inbound.get_location_list(),
        "schedule": sched_info,
    }


# ────────────────────────────────────────────────────────────────────
# DB 初期化 & 起動
# ────────────────────────────────────────────────────────────────────
db.init_db()

if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="127.0.0.1", port=8000)
