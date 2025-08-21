from tkinter.constants import BROWSE

import uvicorn
import db
from send_db_api import get_all_info, get_message
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

# FastAPIアプリを初期化
app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

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

# エンドポイント -------------------------------------------------------

@app.post("/test", response_model=Response)
async def receive_message():
    return Response(message="Hello World!")

class Request(BaseModel):
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

# send_db_apiのエンドポイントを追加
@app.get("/api/all")
def api_all():
    return get_all_info()

@app.get("/api/message/{name}")
def api_message(name: str):
    return get_message(name)

db.init_db()

if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="0.0.0.0", port=8000)