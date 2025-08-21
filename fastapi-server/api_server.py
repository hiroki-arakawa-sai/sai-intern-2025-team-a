from tkinter.constants import BROWSE
import uvicorn
import db

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, constr
from typing import Dict, Any

import schedule_inbound as inbound
from typing import List

# FastAPIアプリを初期化
app = FastAPI()

@app.on_event("startup")
async def _startup():
    #一度だけ呼べばOK。初期時刻/曜日を変えたけれれば引数で指定可能。
    inbound.start_in_background()


# 受信JSONのスキーマ定義 ---------------------------------------------
class Response(BaseModel):
    message: str

class ScheduleEntry(BaseModel):
    id: int = Field(..., ge=0)  # 数値（0以上）
    time: constr(pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')  # "HH:MM"
    area: str


# エンドポイント -------------------------------------------------------

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

# ==== スケジュール操作API ====

@app.get("/schedule/entries")
async def get_entries():
    times = inbound.get_times()
    # 既存スケジュールには id/area が無いので、id は連番採番、area は空文字で返す
    return [{"id": i+1, "time": t, "area": ""} for i, t in enumerate(times)]

@app.post("/schedule/add-entries")
async def add_entries(entries: List[ScheduleEntry]):
    times = sorted({e.time for e in entries})  # 重複除去
    result = inbound.add_times(times)
    return {
        "received": len(entries),
        "added_job_ids": result["added_job_ids"],
        "times": result["times"],
        "weekdays": result["weekdays"],
    }

@app.post("/schedule/sync-entries")
async def sync_entries(entries: List[ScheduleEntry]):
    new_times = sorted({e.time for e in entries})
    current = inbound.get_times()
    to_add = sorted(set(new_times) - set(current))
    to_remove = sorted(set(current) - set(new_times))

    add_res = inbound.add_times(to_add) if to_add else {"added_job_ids": []}
    rem_res = inbound.remove_times(to_remove) if to_remove else {"removed_job_ids": []}

    return {
        "added": to_add,
        "removed": to_remove,
        "times": inbound.get_times(),         # 同期後の最終配列
        "weekdays": inbound.get_current_schedule().get("weekdays", []),
        "add_job_ids": add_res.get("added_job_ids", []),
        "remove_job_ids": rem_res.get("removed_job_ids", []),
    }

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

inbound.start_in_background(

)

if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="127.0.0.1", port=8000)
