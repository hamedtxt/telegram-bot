from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from bot import TelegramBot
from database import Database
from config import TELEGRAM_TOKEN, DATABASE_NAME
import os

app = Flask(__name__)
# تنظیم CORS برای مینی اپ
CORS(app, resources={r"/api/*": {"origins": ["https://yourusername.pythonanywhere.com", "http://localhost:5173"]}})
db = Database(DATABASE_NAME)

# تنظیم بات تلگرام
application = Application.builder().token(TELEGRAM_TOKEN).build()
bot = TelegramBot(TELEGRAM_TOKEN, db)

# ثبت handlerهای بات
application.add_handler(CommandHandler("start", bot.start))
application.add_handler(CommandHandler("verify", bot.verify_payment))
application.add_handler(CallbackQueryHandler(bot.button))
application.add_handler(MessageHandler(filters.ChatType.CHANNEL, bot.handle_message))
application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, bot.handle_webapp_data))

# مسیر webhook برای بات
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    application.process_update(update)
    return "OK"

# API برای مینی اپ
@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        products = db.get_all_products()
        product_list = [
            {"message_id": p[0], "text": p[2], "tags": p[4].split(',')} for p in products
        ]
        return jsonify({"success": True, "products": product_list})
    except Exception as e:
        print(f"Error in get_products: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/is_vip', methods=['GET'])
def is_vip():
    try:
        user_id = request.args.get('user_id')
        print(f"Received user_id: {user_id}")
        if not user_id:
            print("No user_id provided")
            return jsonify({"is_vip": False}), 200
        try:
            user_id_int = int(user_id)
            print(f"Converted user_id to int: {user_id_int}")
        except ValueError:
            print(f"Invalid user_id, treating as non-VIP: {user_id}")
            return jsonify({"is_vip": False}), 200
        is_vip_status = db.is_vip(user_id_int)
        print(f"is_vip_status: {is_vip_status}")
        return jsonify({"is_vip": is_vip_status})
    except Exception as e:
        print(f"Error in is_vip: {e}")
        return jsonify({"is_vip": False, "error": str(e)}), 500

# مسیر برای سرو فایل‌های مینی اپ
@app.route('/')
def serve_mini_app():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# مسیر callback برای زرین‌پال
@app.route('/callback', methods=['GET'])
def callback():
    authority = request.args.get('Authority')
    status = request.args.get('Status')
    if status == "OK" and bot.payment.verify_payment(authority):
        user_id = db.get_user_by_authority(authority)
        if user_id:
            bot.grant_vip_access(user_id)
            return "پرداخت موفق! حالا شما VIP هستید."
    return "پرداخت ناموفق یا کنسل شد."

if __name__ == "__main__":
    # تنظیم webhook
    application.bot.set_webhook(url="https://yourusername.pythonanywhere.com/webhook")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)