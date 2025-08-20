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
#----------------------------------------------------------------
# 受け取った文字列を保存
def save_message(username, text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (userName, text) VALUES (?, ?)", (username, text))
    conn.commit()
    conn.close()
    print("DBに保存しました", text)
#--------------------------------------------------------------
# 文字列を取り出す
def get_message():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT userName, text FROM messages")
    rows = cursor.fetchall()
    conn.close()
    print(rows)
    return rows
#---------------------------------------------------------------