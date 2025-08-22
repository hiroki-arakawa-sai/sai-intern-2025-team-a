# sai-intern-2025-team-a

サイエンスアーツ 夏季インターン 2025 チーム A

## Python インストール

```bash
$ winget install --id Python.Python.3.9 -e
```

## インタプリタ設定

1\. 画面右下の<インタープリターがありません>から「新規インタープリターの追加>ローカルインタープリターの追加」を選択<br>
2\. python3.9 を追加

# 下記コマンドで仮想環境を実行可能

```bash
$ cd fastapi-server
```

```bash
$ .venv/Scripts/activate.ps1
```

```bash
$ pip install -r ./fastapi-server/requirements.txt
```

# 使い方説明

## ブラウザの起動方法

ビルドとかしてないので以下の方法で起動してください

1. Node.js をインストール
2. ターミナルを開いて buddy-browser のフォルダに移動
3. `npm i`で依存関係をインストール
4. `npm run dev`でサーバーを起動して`http://localhost:****/`にアクセス

## API サーバーの起動方法

api_server.py を起動する

## buddybot console での設定

buddycom console で buddy bot api の送信先 URL を

```bash
http://{IPアドレス}:8000/api/memo
```

に設定してください
