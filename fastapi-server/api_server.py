# （不要なら削除）from tkinter.constants import BROWSE
import uvicorn
import db

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field, constr
from typing import Dict, Any, List, Optional
import re

import schedule_inbound as inbound

# FastAPIアプリを初期化
app = FastAPI()

@app.on_event("startup")
async def _startup():
    # スケジューラをバックグラウンドで起動
    # 既定の LOCATION_MAP（or 直前にPUTした内容）を元にスケジュールされます
    inbound.start_in_background()

# ====== 入出力スキーマ ======
class Response(BaseModel):
    message: str

class ScheduleEntry(BaseModel):
    id: int = Field(..., ge=0)  # 数値（0以上） ※受信時は無視してもOK
    time: constr(pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')  # "HH:MM"
    area: str

class LocationsPayload(BaseModel):
    locations: List[ScheduleEntry]
    lead_minutes: int = Field(0, ge=0, le=1439, description="事前通知分（0=ちょうど）")
    text_template: Optional[str] = Field(
        None, description="テンプレ（{now},{label},{place},{lead},{pre}）"
    )

# ====== サンプルAPI ======
@app.post("/test", response_model=Response)
async def receive_message():
    return Response(message="Hello World!")

class MemoRequest(BaseModel):
    chatBotName: str
    senderUserName: str
    languageIndex: int
    type: int
    data: str
    customParams: Dict[str, Any] = {}

@app.post("/test/memo", response_model=Response)
async def receive_message(req: MemoRequest):
    db.save_message(req.senderUserName, req.data)
    print(f"[DEBUG] 受け取った data: {req.data}")
    print(f"[DEBUG] 送信者: {req.senderUserName} ")
    db.get_message()
    return Response(message=f"受け取ったデータ: {req.data}")

# ==== スケジュール操作API（LOCATION_MAP 主導） ====

@app.get("/schedule/entries")
async def get_entries():
    """
    LOCATION_MAP を配列化して返す
    [
      {"id": 0, "time": "11:00", "area": "二階テナント"},
      {"id": 1, "time": "11:48", "area": "一階食品"},
      ...
    ]
    """
    return inbound.get_location_list()

@app.put("/schedule/entries")
async def put_entries(payload: LocationsPayload):
    """
    配列で一括更新 → LOCATION_MAP を差し替え → スケジュール再構築
    """
    # 配列 → dict へ
    new_map: Dict[str, str] = {}
    for item in payload.locations:
        new_map[item.time] = item.area

    inbound.set_location_map(new_map)

    # 現在の LOCATION_MAP からスケジュール再構築
    sched_info = inbound.schedule_from_location_map(
        lead_minutes=payload.lead_minutes, text_template=payload.text_template
    )

    return {
        "ok": True,
        "list": inbound.get_location_list(),
        "schedule": sched_info,
    }

@app.put("/schedule/entries/{time}")
async def upsert_entry(time: str, entry: ScheduleEntry):
    """
    単一時刻の追加/更新（idempotent）
    """
    if time != entry.time:
        raise HTTPException(status_code=400, detail="path time and body time mismatch")

    current = inbound.get_location_map()
    current[entry.time] = entry.area
    inbound.set_location_map(current)

    return {
        "ok": True,
        "list": inbound.get_location_list(),
    }

@app.delete("/schedule/entries/{time}")
async def delete_entry(time: str):
    """
    単一時刻の削除
    """
    if not re.match(r'^(?:[01]\d|2[0-3]):[0-5]\d$', time):
        raise HTTPException(status_code=400, detail="time must be 'HH:MM'")

    current = inbound.get_location_map()
    if time not in current:
        raise HTTPException(status_code=404, detail="time not found")

    del current[time]
    inbound.set_location_map(current)

    return {
        "ok": True,
        "list": inbound.get_location_list(),
    }

@app.get("/schedule/jobs")
async def read_jobs():
    """
    現在のジョブ一覧（id / next_run_time）
    """
    return inbound.get_current_schedule()

@app.post("/schedule/rebuild")
async def rebuild_schedule(lead_minutes: int = 0, text_template: Optional[str] = None):
    """
    LOCATION_MAP を元にスケジュールを再構築
    """
    info = inbound.schedule_from_location_map(
        lead_minutes=lead_minutes, text_template=text_template
    )
    return {"ok": True, "schedule": info, "list": inbound.get_location_list()}

# ====== フック & 起動 ======
async def log_post_request(request):
    body = await request.body()
    print("=== POST受信 ===")
    print("Headers:", dict(request.headers))
    print("Query:", dict(request.query_params))
    print("Raw body:", body.decode("utf-8", errors="ignore"))
    return body

@app.post("/hook")
async def hook(request: Request):
    await log_post_request(request)
    return {"status": "ok"}

db.init_db()



@app.on_event("startup")
async def _startup():
    # 1) 先に LOCATION_MAP を設定
    inbound.set_location_map({
        "11:00": "二階テナント",
        "11:48": "一階食品",
        "12:58": "駐車場",
        "13:02": "一階食品",
        "14:00": "二階テナント",
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

if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="127.0.0.1", port=8000)
