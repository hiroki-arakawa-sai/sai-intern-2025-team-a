import uvicorn

import db
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
print("db初期化前")
db.init_db()
print("db初期化後")


class Message(BaseModel):
    senderUserName: str
    message: str

# すべての送信者とメッセージを返す---------------------------------------------
@app.get("/api/all")
def get_all_info():
    print("dbから取得前")
    rows = db.get_message()
    print("dbから取得後")
    #JSONに変換
    return [
        {"userName": row[0], "message": row[1]}
        for row in rows
    ]

# nameと一致するユーザー名を返す-------------------------------------------------
@app.get("/api/test/{name}")
def get_message(name: str):
    rows = db.extract_message_from_sender(name)
    #return {"[DEBUG] message": name}
    return [
        {"message": row[0]}
        for row in rows
    ]


if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="0.0.0.0", port=8000)