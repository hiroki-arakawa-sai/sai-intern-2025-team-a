from tkinter.constants import BROWSE
import uvicorn
import db
import schedule_inbound as inbound

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, constr
from typing import Dict, Any, List

# GET動作確認用
from fastapi import HTTPException
import traceback


# FastAPIアプリを初期化
app = FastAPI()

@app.on_event("startup")
async def _startup():
    #一度だけ呼ぶ
    inbound.set_location_map({
        "11:00": "二階テナント",
        "12:00": "駐車場",
        "13:00": "一階食品"
    })
    inbound.start_in_background(lead_minutes=5)


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

# ==== スケジュール受け取りAPI ====
# @app.get("/schedule/entries")
# async def get_entries():
#     times = inbound.get_times()
#     # 既存スケジュールには id/area が無いので、id は連番採番、area は空文字で返す
#     return [{"id": i+1, "time": t, "area": ""} for i, t in enumerate(times)]

# GET確認用------------------------------
@app.get("/schedule/entries")
async def get_entries():
    try:
        times = inbound.get_times()
    except Exception as e:
        print("[ERROR] inbound.get_times() failed:", e)
        traceback.print_exc()
        # クライアントには簡潔な500を返す
        raise HTTPException(status_code=500, detail=f"inbound.get_times() failed: {type(e).__name__}")
    # 正常時のレスポンス
    return [{"id": i+1, "time": t, "area": ""} for i, t in enumerate(times)]
# -----------------------------------------------

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

# GET簡易ヘルスチェック -----------------------------------------
@app.get("/health")
async def health():
    try:
        _ = inbound.get_times()
        return {"ok": True, "detail": "ok"}
    except Exception as e:
        return {"ok": False, "detail": f"inbound.get_times() error: {type(e).__name__}: {e}"}
# -----------------------------------------------------------

db.init_db()

#inbound.start_in_background()

if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="127.0.0.1", port=8000)
