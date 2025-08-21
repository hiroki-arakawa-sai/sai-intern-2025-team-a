import sqlite3

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
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        userName TEXT, 
        text TEXT,
        sendTime TEXT
        )
    """)

    conn.commit()
    conn.close()
# 受け取った文字列を保存----------------------------------------------------------------
def save_message(username, text, sendtime):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (userName, text, sendTime) VALUES (?, ?, ?)", (username, text, sendtime))
    conn.commit()
    conn.close()
    #print("DBに保存しました", text)
# 文字列を取り出す---------------------------------------------------------
def get_all_info():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages")
    rows = cursor.fetchall()
    conn.close()
    #print("[DEBUG] all_rows = ", rows)
    return rows
# 送信者からメッセージを抽出---------------------------------------------------------------
def extract_message_from_sender(user_name: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM messages WHERE userName = ?", (user_name,))
    rows = cursor.fetchall()
    #print("[DEBUG] usename_rows = ", rows)
    conn.close()
    return rows

#テーブル削除---------------------------------------------
def delete_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS messages;")
    print("[DEBUG] 削除した")