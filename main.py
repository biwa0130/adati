import os
import random
import threading
import time
import MeCab
import schedule
from flask import Flask, request, abort

# LINE SDK v3
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, PushMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# --- 環境変数の取得 ---
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GROUP_ID = os.environ.get('LINE_GROUP_ID') # ランダム投稿先のグループID

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- 文章生成（マルコフ連鎖等のベース） ---
def generate_text():
    try:
        # MeCabの初期化（エラーを回避するため引数なしでテスト）
        tagger = MeCab.Tagger("-Owakati")
        
        # ※ ここにマルコフ連鎖で文章を生成する処理を入れます
        texts = [
            "こんにちは！足立レイです。",
            "今日も1日頑張ろう！",
            "システム正常稼働中だよ。",
            "お腹すいたかも。"
        ]
        return random.choice(texts)
    except Exception as e:
        print(f"MeCab Error: {e}")
        return "MeCabの準備中です。"

# --- LINE Webhook 受信ルート ---
@app.route("/")
def hello():
    # サーバーが生きているかブラウザで確認するためのルート
    return "Adachi Rei Server is LIVE!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- メッセージを受け取ったときの処理 ---
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text
    # 「足立レイ」と呼ばれたら返信する
    if "足立レイ" in user_msg or "レイ" in user_msg:
        reply_text = generate_text()
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )

# --- 9時〜20時のランダム自動投稿 ---
def scheduled_job():
    if not GROUP_ID:
        print("GROUP_IDが設定されていません")
        return
        
    push_text = generate_text()
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=GROUP_ID,
                messages=[TextMessage(text=push_text)]
            )
        )
    print(f"自動投稿しました: {push_text}")
    # 翌日のスケジュールを再設定
    set_random_schedule()

def set_random_schedule():
    schedule.clear()
    # 9時〜19時台のランダムな時間（実質9:00〜19:59）
    random_hour = random.randint(9, 19)
    random_minute = random.randint(0, 59)
    time_str = f"{random_hour:02d}:{random_minute:02d}"
    
    schedule.every().day.at(time_str).do(scheduled_job)
    print(f"次の自動投稿は {time_str} にセットされました")

def run_schedule():
    set_random_schedule()
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- サーバー起動 ---
if __name__ == "__main__":
    # スケジュールを別スレッドで動かす
    t = threading.Thread(target=run_schedule)
    t.daemon = True
    t.start()
    
    # 開発環境用（Render上ではgunicornを使うためここは呼ばれません）
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
