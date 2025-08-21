import db
from pydantic import BaseModel

db.init_db()

class Message(BaseModel):
    senderUserName: str
    message: str

# すべての送信者とメッセージを返す---------------------------------------------
def get_all_info():
    rows = db.get_all_info()
    #JSONに変換
    return [
        {"userName": row[1], "message": row[2], "time": row[3]}
        for row in rows
    ]

# nameと一致するユーザー名を返す-------------------------------------------------
def get_message(name: str):
    rows = db.extract_message_from_sender(name)
    return [
        {"message": row[0]}
        for row in rows
    ]