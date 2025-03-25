# config.py
TELEGRAM_TOKEN = ""
PUBLIC_CHANNEL_ID = ""
PRIVATE_CHANNEL_ID = ""  # کانال خصوصی
MERCHANT_ID = "12345678-1234-1234-1234-123456789abc"  # 36 کاراکتر دلخواه
SANDBOX_PAYMENT_URL = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
SANDBOX_VERIFY_URL = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
SANDBOX_START_PAY = "https://sandbox.zarinpal.com/pg/StartPay/"
DATABASE_NAME = "users.db"
SUBSCRIPTION_AMOUNT = 10000  # مبلغ اشتراک به ریال
SUBSCRIPTION_DURATION = 30  # مدت اشتراک به روز
LOG_FILE = "bot.log"
CALLBACK_URL = "https://yourusername.pythonanywhere.com/callback"  # برای زرین‌پال
