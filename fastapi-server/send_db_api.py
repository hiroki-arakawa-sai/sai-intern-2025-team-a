from fastapi import FastAPI
import db
import api_server
import sqlite3
from pydantic import BaseModel

app = FastAPI()
db.init_db()

class Message(BaseModel):
    senderUserName: str
    message: str

@app.get("/api/all")
def get_all_info():
    rows = db.get_message()
    #JSONに変換
    return [
        {"userName": row[0], "message": row[1]}
        for row in rows
    ]
