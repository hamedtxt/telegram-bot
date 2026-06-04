# -*- coding: utf-8 -*-
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json

app = FastAPI(title="MT5 Telegram Mini App Backend")

# فعال‌سازی CORS برای دسترسی بدون محدودیت مینی‌اپ تلگرام
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# مسیر فایل ذخیره موقت داده‌ها در Render
DATA_FILE = "account_data.json"

class PositionModel(BaseModel):
    ticket: int
    symbol: str
    type: str
    volume: float
    open_price: float
    current_price: float
    profit: float

class AccountDataModel(BaseModel):
    balance: float
    equity: float
    positions: List[PositionModel]

def save_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"balance": 0.0, "equity": 0.0, "positions": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading data: {e}")
        return {"balance": 0.0, "equity": 0.0, "positions": []}

@app.post("/update")
async def update_status(data: AccountDataModel):
    """ دریافت اطلاعات زنده از متاتریدر ۵ """
    payload = data.dict()
    save_data(payload)
    return {"status": "success", "message": "Data updated successfully."}

@app.get("/api/status")
async def get_status():
    """ ارسال اطلاعات به مینی‌اپ تلگرام """
    return load_data()

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """ سرویس‌دهی صفحه اصلی مینی‌اپ """
    if os.path.exists("index.html"):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"<h3>خطا در خواندن فایل رابط کاربری: {e}</h3>"
    return "<h3>فایل index.html در ریشه سرور یافت نشد. مسیر فایل را در گیت‌هاب بررسی کنید.</h3>"

if __name__ == "__main__":
    import uvicorn
    # دریافت پورت از متغیرهای سیستم عامل Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
