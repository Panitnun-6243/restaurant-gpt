import json
from flask import Flask, request, abort, jsonify
from azure_openai import ask_azure_gpt, ask_azure_dalle

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage

import os

# Use dotenv to load environment variables
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))


# Route / with GET method return Welcome message
@app.route("/", methods=["GET"])
def index():
    return "Welcome to OpenAI Line Bot"


# Route /message with GET method and q parameter
@app.route("/message", methods=["GET"])
def message():
    # Get query parameter
    query = request.args.get("q")

    if should_generate_image(query):
        image_url = ask_azure_dalle(query)
        return jsonify({"question": query, "image_url": image_url})

    answer = ask_azure_gpt(query)

    # return answer as json​
    return jsonify({"question": query, "answer": answer})


@app.route("/direct", methods=["POST"])
def direct():
    body = request.get_data(as_text=True)
    answer = ask_azure_gpt(body)
    return json.loads(answer)


@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    query = event.message.text

    if should_generate_image(query):
        image_url = ask_azure_dalle(query)
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text="Here is the picture"),
                ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                ),
            ],
        )
    else:
        answer = ask_azure_gpt(query)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=answer))


def should_generate_image(query):
    # Define the phrases that trigger image generation
    # Define the keywords that trigger image generation
    trigger_keywords = ["picture", "photo"]

    # Convert the query to lowercase for case-insensitive matching
    query = query.lower()

    for phrase in trigger_keywords:
        if phrase in query:
            return True

    return False


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("Starting Flask OpenAI app")

    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
