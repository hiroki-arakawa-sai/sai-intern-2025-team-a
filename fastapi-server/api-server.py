import uvicorn

from fastapi import FastAPI
from pydantic import BaseModel

# FastAPIアプリを初期化
app = FastAPI()

# 受信JSONのスキーマ定義 ---------------------------------------------
class Response(BaseModel):
    message: str

# エンドポイント -------------------------------------------------------

@app.post("/test", response_model=Response)
async def receive_message():
    return Response(message="Hello World!")



if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="0.0.0.0", port=8000)