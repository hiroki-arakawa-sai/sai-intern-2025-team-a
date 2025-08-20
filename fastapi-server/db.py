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
        text TEXT
        )
    """)

    conn.commit()
    conn.close()
# 受け取った文字列を保存----------------------------------------------------------------
def save_message(username, text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (userName, text) VALUES (?, ?)", (username, text))
    conn.commit()
    conn.close()
    print("DBに保存しました", text)
# 文字列を取り出す---------------------------------------------------------
def get_message():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT userName, text FROM messages")
    rows = cursor.fetchall()
    conn.close()
    print("[DEBUG] all_rows = ", rows)
    return rows
# 送信者からメッセージを抽出---------------------------------------------------------------
def extract_message_from_sender(user_name: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM messages WHERE userName = ?", (user_name,))
    rows = cursor.fetchall()
    print("[DEBUG] usename_rows = ", rows)
    conn.close()
    return rows