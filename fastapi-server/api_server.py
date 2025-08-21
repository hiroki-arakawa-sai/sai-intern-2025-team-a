from tkinter.constants import BROWSE

import uvicorn
import db

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

import schedule_inbound as inbound

# FastAPIアプリを初期化
app = FastAPI()

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
    db.save_message(req.senderUserName, req.data)
    print(f"[DEBUG] 受け取った data: {req.data}")
    print(f"[DEBUG] 送信者: {req.senderUserName} ")
    db.get_message()
    return Response(message=f"受け取ったデータ: {req.data}")

db.init_db()

inbound.start_in_background(

)

if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="0.0.0.0", port=8000)