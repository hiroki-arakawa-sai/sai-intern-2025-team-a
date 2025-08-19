import uvicorn

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

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
    print(f"[DEBUG] 受け取った data: {req.data}")
    return Response(message=f"受け取ったデータ: {req.data}")

if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="0.0.0.0", port=8000)