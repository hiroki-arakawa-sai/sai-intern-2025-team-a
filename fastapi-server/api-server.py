from tkinter.constants import BROWSE

import uvicorn
import sqlite3
# import db

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

# SQLのテーブルを作る-----------------------------------------------------
DB_NAME = "data.db"

#テーブルを作る
def init_db():
    # SQL実行
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # messageというテーブルを作る...のちのち変更して
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, # 主キー
        text TEXT
        )
    """)

    conn.commit()
    conn.close()
#----------------------------------------------------------------
# 受け取った文字列を保存
def save_message(text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (text) VALUES (?)", (text,))
    conn.commit()
    conn.close()
    print("DBに保存しました", text)
#--------------------------------------------------------------
# 文字列を取り出す
def get_message():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, text FROM messages")
    rows = cursor.fetchall()
    conn.close()
    print(rows)
    return rows
#---------------------------------------------------------------
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
    save_message(req.data)
    print(f"[DEBUG] 受け取った data: {req.data}")
    get_message()
    return Response(message=f"受け取ったデータ: {req.data}")


if __name__ == "__main__":
    # FastAPIサーバーを開始
    uvicorn.run(app, host="0.0.0.0", port=8000)