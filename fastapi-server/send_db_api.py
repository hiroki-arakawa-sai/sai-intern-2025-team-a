import uvicorn

import db
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
db.init_db()

class Message(BaseModel):
    senderUserName: str
    message: str

# すべての送信者とメッセージを返す---------------------------------------------
@app.get("/api/all")
def get_all_info():
    rows = db.get_all_info()
    #JSONに変換
    return [
        {"userName": row[1], "message": row[2], "time": row[3]}
        for row in rows
    ]

# nameと一致するユーザー名を返す-------------------------------------------------
@app.get("/api/message/{name}")
def get_message(name: str):
    rows = db.extract_message_from_sender(name)
    return [
        {"message": row[0]}
        for row in rows
    ]


if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="0.0.0.0", port=8000)