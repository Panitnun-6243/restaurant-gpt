import json
from flask import Flask, request, abort, jsonify
from azure_openai import (
    ask_azure_gpt,
    ask_azure_dalle,
    load_mock_daily_sales,
    load_mock_ingredients,
)

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

    if should_analyze_daily_sales(query):
        daily_sales = load_mock_daily_sales()
        answer = analyze_daily_sales(daily_sales)
        return jsonify({"question": query, "answer": answer})

    if should_analyze_ingredients(query):
        ingredients = load_mock_ingredients()
        answer = analyze_ingredients(ingredients)
        return jsonify({"question": query, "answer": answer})

    if should_generate_image(query):
        image_url = ask_azure_dalle(query)
        return jsonify({"question": query, "image_url": image_url})

    if should_analyze_growth(query):
        daily_sales = load_mock_daily_sales()
        answer = ask_azure_gpt(analyze_growth(daily_sales))
        return jsonify({"question": query, "answer": answer})

    if should_generate_new_menu(query):
        ingredients = load_mock_ingredients()
        answer = ask_azure_gpt(generate_menu(ingredients))
        return jsonify({"question": query, "answer": answer})

    answer = ask_azure_gpt(query)

    # return answer as json
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
                TextSendMessage(text="นี่คือภาพตัวอย่างครับ"),
                ImageSendMessage(
                    original_content_url=image_url, preview_image_url=image_url
                ),
            ],
        )
    elif should_analyze_growth(query):
        daily_sales = load_mock_daily_sales()
        answer = ask_azure_gpt(analyze_growth(daily_sales))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=answer))
    elif should_generate_new_menu(query):
        ingredients = load_mock_ingredients()
        answer = ask_azure_gpt(generate_menu(ingredients))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=answer))
    elif should_analyze_daily_sales(query):
        daily_sales = load_mock_daily_sales()
        answer = analyze_daily_sales(daily_sales)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=answer))
    elif should_analyze_ingredients(query):
        ingredients = load_mock_ingredients()
        answer = analyze_ingredients(ingredients)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=answer))
    else:
        answer = ask_azure_gpt(query)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=answer))


def analyze_daily_sales(daily_sales):
    date = daily_sales["date"]
    sales = daily_sales["sales"]

    response = f"ยอดการขายของคุณในวันที่ {date} นั้นมีดังนี้:\n"

    for i, sale in enumerate(sales, start=1):
        item = sale["item"]
        quantity = sale["quantity"]
        revenue = sale["revenue"]
        response += f"{i}. {item}: ขายได้ {quantity} จาน, รายได้ {revenue} บาท\n"

    return response


def analyze_ingredients(ingredients):
    response = "สรุปยอดสต็อกคงเหลือได้ดังนี้:\n"
    for ingredient in ingredients["ingredients"]:
        name = ingredient["name"]
        quantity = ingredient["quantity"]
        response += f"- {name} คงเหลือ {quantity} กิโลกรัม\n"
    return response


def analyze_growth(daily_sales):
    date = daily_sales["date"]
    sales = daily_sales["sales"]

    response = f"How to make more profits จากข้อมูลในวัน {date}:\n"

    for i, sale in enumerate(sales, start=1):
        item = sale["item"]
        quantity = sale["quantity"]
        revenue = sale["revenue"]
        response += f"{i}. {item}: ขายได้ {quantity} จาน, รายได้ {revenue} บาท\n"

    return response


def generate_menu(ingredients):
    # Logic: Combine random ingredients to create a new dish
    menu = "สร้างเมนูใหม่จากส่วนผสมที่คงเหลือ:\n"
    for ingredient in ingredients["ingredients"]:
        name = ingredient["name"]
        quantity = ingredient["quantity"]
        menu += f"- {name}: {quantity} กิโลกรัม\n"

    return menu


def should_analyze_daily_sales(query):
    keywords = ["ยอดการขาย", "สรุปยอด", "วันนี้ขายไปเท่าไร"]
    query = query.lower()
    for keyword in keywords:
        if keyword in query:
            return True
    return False


def should_analyze_ingredients(query):
    keywords = ["คงเหลือ", "stock", "สต็อก", "ingredient", "อาหาร", "วัตถุดิบ", "จำนวนวัตถุดิบคงเหลือ"]
    query = query.lower()
    for keyword in keywords:
        if keyword in query:
            return True
    return False


def should_analyze_growth(query):
    keywords = [
        "จะทำยังไงให้ยอดการขายนั้นเพิ่มขึ้น",
        "กำไรมากขึ้น",
        "มากขึ้น",
        "ทำยังไงให้ยอดการขายเพิ่มขึ้น",
        "จะเพิ่มยอดการขายอย่างไร",
        "จะทำยังไงให้สร้างกำไรเพิ่มมากขึ้น",
    ]
    query = query.lower()
    for keyword in keywords:
        if keyword in query:
            return True
    return False


def should_generate_new_menu(query):
    # Define the trigger word(s) that indicate generating a new menu
    trigger_words = [
        "generate menu",
        "create menu",
        "new menu",
        "เมนูใหม่",
        "สร้างเมนู",
        "สร้างเมนูใหม่",
        "สร้างเมนูใหม่จากส่วนผสมที่คงเหลือ",
        "จะจัดการกับของเหลืออย่างไร",
        "จะจัดการกับวัตถุดิบที่เหลือได้อย่างไร",
    ]

    # Convert the query to lowercase for case-insensitive matching
    query = query.lower()

    # Check if any trigger word is present in the query
    for word in trigger_words:
        if word in query:
            return True

    return False


def should_generate_image(query):
    # Define the phrases that trigger image generation
    # Define the keywords that trigger image generation
    trigger_keywords = ["picture", "photo", "image"]

    # Convert the query to lowercase for case-insensitive matching
    query = query.lower()

    for phrase in trigger_keywords:
        if phrase in query:
            return True

    return False


# def generate_new_menu(query, ingredients):
#     # Extract the remaining ingredients and quantities from the query
#     remaining_ingredients = []
#     for ingredient in ingredients["ingredients"]:
#         name = ingredient["name"]
#         quantity = ingredient["quantity"]
#         if name.lower() in query.lower() and str(quantity) in query:
#             remaining_ingredients.append(ingredient)

#     # Generate a new menu from the remaining ingredients
#     menu = "Create new menu from these left ingredients:\n"
#     for ingredient in remaining_ingredients:
#         name = ingredient["name"]
#         quantity = ingredient["quantity"]
#         menu += f"- {name}: {quantity} กิโลกรัม\n"

#     return menu


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("Starting Flask OpenAI app")

    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
