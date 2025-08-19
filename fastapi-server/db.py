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