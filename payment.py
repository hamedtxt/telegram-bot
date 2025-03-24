import requests
import json
from config import MERCHANT_ID, SANDBOX_PAYMENT_URL, SANDBOX_VERIFY_URL, SANDBOX_START_PAY, SUBSCRIPTION_AMOUNT, CALLBACK_URL

class Payment:
    def create_payment(self, user_id):
        payload = {
            "merchant_id": MERCHANT_ID,
            "amount": SUBSCRIPTION_AMOUNT,
            "callback_url": CALLBACK_URL,
            "description": f"اشتراک VIP برای کاربر {user_id}"
        }
        headers = {"Content-Type": "application/json"}
        try:
            print("Sending request to:", SANDBOX_PAYMENT_URL)
            print("Payload:", payload)
            response = requests.post(SANDBOX_PAYMENT_URL, data=json.dumps(payload), headers=headers)
            print("Response Status:", response.status_code)
            print("Response Text:", response.text)
            response.raise_for_status()
            data = response.json()
            print("Parsed JSON:", data)
            if data.get("data") and data["data"].get("code") == 100:
                authority = data["data"]["authority"]
                return authority, f"{SANDBOX_START_PAY}{authority}"
            else:
                print(f"خطای زرین‌پال: {data.get('errors', 'Unknown error')}")
        except requests.exceptions.RequestException as e:
            print(f"خطا در درخواست: {e}")
        except ValueError as e:
            print(f"خطا در تبدیل JSON: {e}")
        return None, None

    def verify_payment(self, authority):
        payload = {
            "merchant_id": MERCHANT_ID,
            "authority": authority,
            "amount": SUBSCRIPTION_AMOUNT
        }
        try:
            response = requests.post(SANDBOX_VERIFY_URL, json=payload)
            print("Verify Response Status:", response.status_code)
            print("Verify Response Text:", response.text)
            data = response.json()
            print("Verify Parsed JSON:", data)
            return data.get("data") and data["data"].get("code") == 100
        except Exception as e:
            print(f"خطا در تأیید پرداخت: {e}")
            return False