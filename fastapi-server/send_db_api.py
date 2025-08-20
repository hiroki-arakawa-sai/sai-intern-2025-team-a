from fastapi import FastAPI
import db
from pydantic import BaseModel

app = FastAPI()
db.init_db()

class Message(BaseModel):
    senderUserName: str
    message: str

# すべての送信者とメッセージを返す---------------------------------------------
@app.get("/api/all")
def get_all_info():
    rows = db.get_message()
    #JSONに変換
    return [
        {"userName": row[0], "message": row[1]}
        for row in rows
    ]

# nameと一致するユーザー名を返す-------------------------------------------------
#@app.get("/api/message/{UserName}")