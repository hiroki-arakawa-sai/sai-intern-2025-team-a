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


from send_db_api import get_all_info, get_message
from datetime import datetime

from fastapi.middleware.cors import CORSMiddleware


# FastAPIアプリを初期化
app = FastAPI()


@app.on_event("startup")
async def _startup():
    # 1) 先に LOCATION_MAP を設定（必要に応じて編集）
    inbound.set_location_map({
        "10:00": "二階テナント",
        "11:00": "一階食品",
        "12:00": "駐車場",
        "13:00": "一階食品",
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



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 必要に応じて限定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
async def receive_message(req: Request):
    send_time = str(datetime.now())[:-7]
    db.save_message(req.senderUserName, req.data, send_time)
    
    print(f"[DEBUG] 受け取った data: {req.data}")
    # print(f"[DEBUG] 送信者: {req.senderUserName} ")
    # print(f"[DEBUG] 時刻: {send_time}")
    db.get_all_info()
    #db.delete_table()
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
    """
    現在の LOCATION_MAP を [{id,time,area}, ...] 形式で返す
    """
    try:
        return inbound.get_location_list()  # time昇順で [{id,time,area}, ...]
    except Exception as e:
        print("[ERROR] inbound.get_location_list() failed:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"get_location_list failed: {type(e).__name__}")

# -----------------------------------------------

async def log_post_request(request):
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

# GET簡易ヘルスチェック -----------------------------------------
@app.get("/health")
async def health():
    try:
        _ = inbound.get_times()
        return {"ok": True, "detail": "ok"}
    except Exception as e:
        return {"ok": False, "detail": f"inbound.get_times() error: {type(e).__name__}: {e}"}
# -----------------------------------------------------------
# send_db_apiのエンドポイントを追加
@app.get("/api/all")
def api_all():
    return get_all_info()

@app.get("/api/message/{name}")
def api_message(name: str):
    return get_message(name)


db.init_db()

#inbound.start_in_background()

if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="127.0.0.1", port=8000)
