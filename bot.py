import logging
import asyncio
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError
from pydub import AudioSegment
from payment import Payment
from database import Database
from config import PUBLIC_CHANNEL_ID, PRIVATE_CHANNEL_ID, SUBSCRIPTION_DURATION

# تنظیم لاگ
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token, db):
        self.app = Application.builder().token(token).build()
        self.payment = Payment()
        self.db = db
        self.private_content = {}
        self.bot_link = None
        self.bot_id = None
        self.default_cover_art = "AgACAgQAAxkBAAOzZ9na1eRueCgSqj-JGlhxoWvxM7IAAs7FMRs_utFS7YTey0e2b84BAAMCAAN5AAM2BA"
        logging.info("بات با موفقیت مقداردهی اولیه شد")
        self.load_products_from_db()

    def load_products_from_db(self):
        products = self.db.get_all_products()
        for product in products:
            message_id, chat_id, text, file_id, tags_str, _ = product
            tags = tags_str.split(',') if tags_str else []
            self.private_content[message_id] = {
                "message": None,
                "chat_id": chat_id,
                "text": text,
                "file_id": file_id,
                "tags": tags
            }
        logging.info(f"{len(products)} محصول از دیتابیس بارگذاری شد")

    async def initialize(self):
        bot_info = await self.app.bot.get_me()
        self.bot_link = f"https://t.me/{bot_info.username}"
        self.bot_id = bot_info.id
        logging.info(f"لینک بات: {self.bot_link}, ID بات: {self.bot_id}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        logging.info(f"کاربر {user_id} دستور /start را اجرا کرد")

        if context.args:
            param = context.args[0]
            if param.startswith("view_product_"):
                message_id = int(param.split("_")[2])
                logging.info(f"کاربر {user_id} از لینک عمیق برای پیام {message_id} وارد شد")
                if message_id in self.private_content:
                    is_vip = self.db.is_vip(user_id)
                    logging.info(f"وضعیت VIP کاربر {user_id}: {is_vip}")
                    if is_vip:
                        product = self.private_content[message_id]
                        message_text = product["text"] or "بدون توضیح"
                        file_id = product["file_id"]
                        if file_id:
                            await context.bot.send_document(
                                user_id,
                                file_id,
                                caption=f"{message_text}\nمحصول ویژه شما آماده دانلوده!"
                            )
                            logging.info(f"فایل ویژه برای کاربر VIP {user_id} ارسال شد")
                        else:
                            invite_link = await context.bot.export_chat_invite_link(PRIVATE_CHANNEL_ID)
                            await context.bot.send_message(
                                user_id,
                                f"{message_text}\nمحصول ویژه توی کانال خصوصی:\n{invite_link}"
                            )
                            logging.info(f"لینک کانال خصوصی به کاربر VIP {user_id} ارسال شد")
                    else:
                        keyboard = [[InlineKeyboardButton("خرید اشتراک ویژه", callback_data='buy_subscription')]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await context.bot.send_message(
                            user_id,
                            "این محصول ویژه‌ست! برای دسترسی، اشتراک بخرید:",
                            reply_markup=reply_markup
                        )
                        logging.info(f"کاربر غیر-VIP {user_id} درخواست محتوای ویژه کرد")
                else:
                    await context.bot.send_message(user_id, "محتوا پیدا نشد! دوباره امتحان کنید.")
                    logging.error(f"محتوای {message_id} در حافظه پیدا نشد")
                return

        # اضافه کردن دکمه Mini App
        keyboard = [
            [InlineKeyboardButton("خرید اشتراک ویژه", callback_data='buy_subscription')],
            [InlineKeyboardButton("مشاهده محصولات در وب اپ", web_app=WebAppInfo(url="https://yourusername.pythonanywhere.com"))],
            [InlineKeyboardButton("چک کردن وضعیت عضویت", callback_data='check_status')],
            [InlineKeyboardButton("دسته‌بندی محصولات", callback_data='show_categories')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "به فروشگاه محصولات دیجیتال خوش اومدی!\n"
            "محصولات رایگان توی کانال عمومی هستن.\n"
            "برای دسترسی به محصولات ویژه، اشتراک بخرید یا وب اپ رو ببینید:",
            reply_markup=reply_markup
        )
        logging.info(f"منوی شروع برای کاربر {user_id} ارسال شد")

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = str(query.message.chat_id)
        logging.info(f"کاربر {user_id} دکمه {query.data} را انتخاب کرد در چت {chat_id}")

        if chat_id == PUBLIC_CHANNEL_ID:
            keyboard = [[InlineKeyboardButton("برو به بات", url=self.bot_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="برای ادامه، به چت بات بروید:",
                reply_markup=reply_markup
            )
            logging.info(f"پیام هدایت به بات برای کاربر {user_id} توی کانال {PUBLIC_CHANNEL_ID} ارسال شد")
            return

        try:
            if query.data == "buy_subscription":
                authority, payment_link = self.payment.create_payment(user_id)
                if authority and payment_link:
                    await context.bot.send_message(
                        user_id,
                        f"برای دسترسی به محصولات ویژه:\n{payment_link}\n"
                        f"بعد از پرداخت، کد زیر رو با /verify بفرست:\n`{authority}`"
                    )
                    logging.info(f"لینک پرداخت برای کاربر {user_id} ساخته شد: {authority}")
                else:
                    await context.bot.send_message(user_id, "خطا در اتصال به درگاه پرداخت!")
                    logging.error(f"خطا در ساخت لینک پرداخت برای کاربر {user_id}")

            elif query.data == "check_status":
                is_vip = self.db.is_vip(user_id)
                logging.info(f"وضعیت VIP کاربر {user_id}: {is_vip}")
                if is_vip:
                    invite_link = await context.bot.export_chat_invite_link(PRIVATE_CHANNEL_ID)
                    await context.bot.send_message(
                        user_id,
                        f"شما کاربر ویژه هستید!\nبه کانال محصولات ویژه بروید:\n{invite_link}"
                    )
                    logging.info(f"کاربر {user_id} وضعیت VIP خود را چک کرد: VIP است")
                else:
                    await context.bot.send_message(
                        user_id,
                        "شما کاربر عادی هستید. برای دسترسی به محصولات ویژه، اشتراک بخرید."
                    )
                    logging.info(f"کاربر {user_id} وضعیت VIP خود را چک کرد: VIP نیست")

            elif query.data == "show_categories":
                all_tags = set()
                for content in self.private_content.values():
                    all_tags.update(content["tags"])
                
                if not all_tags:
                    await context.bot.send_message(user_id, "هنوز محصولی با دسته‌بندی وجود نداره!")
                    return

                keyboard = [[InlineKeyboardButton(tag[1:], callback_data=f"category_{tag}_1")] for tag in all_tags]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    user_id,
                    "دسته‌بندی محصولات رو انتخاب کنید:",
                    reply_markup=reply_markup
                )
                logging.info(f"دسته‌بندی‌ها برای کاربر {user_id} ارسال شد")

            elif query.data.startswith("category_"):
                parts = query.data.rsplit("_", 1)
                page = int(parts[-1])
                selected_tag = parts[0].replace("category_", "")
                items_per_page = 5

                products = [
                    content for content in self.private_content.values()
                    if any(selected_tag in tag for tag in content["tags"])
                ]
                
                if not products:
                    await context.bot.send_message(user_id, f"محصولی توی دسته {selected_tag} پیدا نشد!")
                    return

                total_pages = (len(products) + items_per_page - 1) // items_per_page
                start_idx = (page - 1) * items_per_page
                end_idx = start_idx + items_per_page
                page_products = products[start_idx:end_idx]

                for product in page_products:
                    text = product["text"] or "بدون توضیح"
                    clean_text = re.sub(r'#\w+', '', text).strip()
                    if not clean_text:
                        clean_text = "محصولی با توضیحات خالی"
                    message_id = product["message"].message_id if product["message"] else list(self.private_content.keys())[list(self.private_content.values()).index(product)]
                    start_link = f"{self.bot_link}?start=view_product_{message_id}"
                    keyboard = [[InlineKeyboardButton("مشاهده محصول", url=start_link)]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(
                        user_id,
                        f"{clean_text}",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )

                nav_buttons = []
                if page > 1:
                    nav_buttons.append(InlineKeyboardButton("⬅️ صفحه قبلی", callback_data=f"category_{selected_tag}_{page-1}"))
                if page < total_pages:
                    nav_buttons.append(InlineKeyboardButton("صفحه بعدی ➡️", callback_data=f"category_{selected_tag}_{page+1}"))
                
                if nav_buttons:
                    await context.bot.send_message(
                        user_id,
                        f"صفحه {page} از {total_pages}",
                        reply_markup=InlineKeyboardMarkup([nav_buttons])
                    )

                logging.info(f"لیست محصولات دسته {selected_tag} (صفحه {page}) برای کاربر {user_id} ارسال شد")

            elif query.data.startswith("get_content_"):
                message_id = int(query.data.split("_")[2])
                logging.info(f"درخواست دسترسی به محتوا برای پیام {message_id} توسط کاربر {user_id}")
                if message_id not in self.private_content:
                    await context.bot.send_message(user_id, "محتوا پیدا نشد! دوباره امتحان کنید.")
                    logging.error(f"محتوای {message_id} در حافظه پیدا نشد")
                    return

                is_vip = self.db.is_vip(user_id)
                logging.info(f"وضعیت VIP کاربر {user_id}: {is_vip}")
                if is_vip:
                    product = self.private_content[message_id]
                    message_text = product["text"] or "بدون توضیح"
                    file_id = product["file_id"]
                    if file_id:
                        await context.bot.send_document(
                            user_id,
                            file_id,
                            caption=f"{message_text}\nمحصول ویژه شما آماده دانلوده!"
                        )
                        logging.info(f"فایل ویژه برای کاربر VIP {user_id} ارسال شد")
                    else:
                        invite_link = await context.bot.export_chat_invite_link(PRIVATE_CHANNEL_ID)
                        await context.bot.send_message(
                            user_id,
                            f"{message_text}\nمحصول ویژه توی کانال خصوصی:\n{invite_link}"
                        )
                        logging.info(f"لینک کانال خصوصی به کاربر VIP {user_id} ارسال شد")
                else:
                    keyboard = [[InlineKeyboardButton("خرید اشتراک ویژه", callback_data='buy_subscription')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(
                        user_id,
                        "این محصول ویژه‌ست! برای دسترسی، اشتراک بخرید:",
                        reply_markup=reply_markup
                    )
                    logging.info(f"کاربر غیر-VIP {user_id} درخواست محتوای ویژه کرد")

        except Exception as e:
            logging.error(f"خطا در تابع button برای کاربر {user_id}: {str(e)}")
            await context.bot.send_message(user_id, f"خطا: {str(e)}")

    async def verify_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        logging.info(f"کاربر {user_id} دستور /verify را اجرا کرد")
        try:
            authority = context.args[0]
            logging.info(f"تأیید پرداخت برای کاربر {user_id} با کد {authority} شروع شد")
            if self.payment.verify_payment(authority):
                stored_user_id = self.db.get_user_by_authority(authority)
                if stored_user_id and stored_user_id != user_id:
                    await update.message.reply_text("این کد متعلق به شما نیست!")
                    logging.warning(f"کاربر {user_id} کد نامعتبر وارد کرد: {authority}")
                else:
                    self.db.add_user(user_id, authority, SUBSCRIPTION_DURATION)
                    await self.grant_vip_access(user_id)
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,))
                    subscription_end = cursor.fetchone()[0]
                    conn.close()
                    invite_link = await context.bot.export_chat_invite_link(PRIVATE_CHANNEL_ID)
                    await update.message.reply_text(
                        f"پرداخت تأیید شد! حالا می‌تونید به محصولات ویژه دسترسی داشته باشید:\n{invite_link}"
                    )
                    logging.info(f"کاربر {user_id} با موفقیت به VIP ارتقا یافت با کد {authority} - پایان اشتراک: {subscription_end}")
            else:
                await update.message.reply_text("کد نامعتبر یا پرداخت ناموفق!")
                logging.error(f"تأیید پرداخت برای کد {authority} ناموفق بود")
        except IndexError:
            await update.message.reply_text("لطفاً کد Authority رو بعد از /verify وارد کنید. مثال: /verify S000123")
            logging.warning(f"کاربر {user_id} کد Authority را وارد نکرد")
        except Exception as e:
            await update.message.reply_text(f"خطا در تأیید: {str(e)}")
            logging.error(f"خطا در تأیید پرداخت برای کاربر {user_id}: {str(e)}")

    async def grant_vip_access(self, user_id):
        logging.info(f"دسترسی VIP به کاربر {user_id} در کانال {PRIVATE_CHANNEL_ID} اعطا شد")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.channel_post:
            message = update.channel_post
            message_text = message.text or message.caption or "بدون توضیح"
            message_id = message.message_id
            chat_id = str(message.chat_id)
            logging.info(f"پیام جدید دریافت شد - Chat ID: {chat_id}, متن: {message_text[:50]}")

            if chat_id == PUBLIC_CHANNEL_ID:
                logging.info(f"پست جدید در کانال {PUBLIC_CHANNEL_ID} دریافت شد: {message_text[:50]}")
                if "#غیررایگان" in message_text:
                    keyboard = [
                        [InlineKeyboardButton("مشاهده محصول", callback_data=f"get_content_{message_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(
                        PUBLIC_CHANNEL_ID,
                        f"محصول غیررایگان جدید: {message_text}\nبرای دسترسی، دکمه زیر رو بزنید:",
                        reply_markup=reply_markup
                    )
                    logging.info(f"اعلان محصول غیررایگان با دکمه برای پیام {message_id} ارسال شد")
                else:
                    await context.bot.send_message(
                        PUBLIC_CHANNEL_ID,
                        f"محصول رایگان جدید: {message_text}"
                    )
                    logging.info(f"اعلان محصول رایگان برای پیام {message_id} ارسال شد")

            elif chat_id == PRIVATE_CHANNEL_ID:
                if message.audio or message.document or message.photo:
                    logging.info(f"محصول غیررایگان در کانال {PRIVATE_CHANNEL_ID} آپلود شد: {message_text[:50]}")
                    tags = re.findall(r'#[\w_]+', message_text)
                    if not tags:
                        tags = ["#بدون_دسته"]
                    
                    file_id = None
                    if message.audio:
                        file_id = message.audio.file_id
                    elif message.document:
                        file_id = message.document.file_id
                    elif message.photo:
                        file_id = message.photo[-1].file_id

                    self.db.add_product(message_id, chat_id, message_text, file_id, tags)
                    self.private_content[message_id] = {
                        "message": message,
                        "chat_id": chat_id,
                        "text": message_text,
                        "file_id": file_id,
                        "tags": tags
                    }
                    
                    start_link = f"{self.bot_link}?start=view_product_{message_id}"
                    keyboard = [[InlineKeyboardButton("مشاهده محصول", url=start_link)]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    cover_art = self.default_cover_art
                    if message.photo:
                        cover_art = message.photo[-1].file_id

                    try:
                        if message.audio:
                            audio_file = await message.audio.get_file()
                            file_path = await audio_file.download_to_drive()
                            audio = AudioSegment.from_file(file_path)
                            preview = audio[:15000]
                            preview_path = f"preview_{message_id}.mp3"
                            preview.export(preview_path, format="mp3")
                            with open(preview_path, 'rb') as f:
                                preview_msg = await context.bot.send_audio(
                                    PUBLIC_CHANNEL_ID,
                                    f,
                                    caption=f"{message_text}\nپیش‌نمایش محصول:",
                                    reply_markup=reply_markup
                                )
                            await context.bot.send_photo(
                                PUBLIC_CHANNEL_ID,
                                cover_art,
                                caption="کاور محصول",
                                reply_to_message_id=preview_msg.message_id
                            )
                            os.remove(file_path)
                            os.remove(preview_path)
                        else:
                            await context.bot.send_photo(
                                PUBLIC_CHANNEL_ID,
                                cover_art,
                                caption=f"{message_text}\nمشاهده محصول:",
                                reply_markup=reply_markup
                            )
                        logging.info(f"محصول غیررایگان با پیام {message_id} در کانال خصوصی ذخیره و اعلان شد")
                    except Exception as e:
                        logging.error(f"خطا در ارسال پیش‌نمایش یا کاور برای پیام {message_id}: {str(e)}")
                        await context.bot.send_message(
                            PUBLIC_CHANNEL_ID,
                            f"{message_text}\nمشاهده محصول:",
                            reply_markup=reply_markup
                        )
                        logging.info(f"به جای پیش‌نمایش، متن برای پیام {message_id} ارسال شد")
                else:
                    logging.info(f"پست بدون فایل در کانال {PRIVATE_CHANNEL_ID} نادیده گرفته شد: {message_text[:50]}")

    async def handle_webapp_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        web_app_data = update.message.web_app_data.data

        import json
        data = json.loads(web_app_data)
        action = data.get('action')
        logging.info(f"داده از Mini App دریافت شد از کاربر {user_id}: {data}")

        if action == "buy_subscription":
            self.db.add_user(user_id, "webapp_payment", SUBSCRIPTION_DURATION)
            await self.grant_vip_access(user_id)
            invite_link = await context.bot.export_chat_invite_link(PRIVATE_CHANNEL_ID)
            await update.message.reply_text(
                f"اشتراک شما با موفقیت فعال شد! حالا می‌توانید به محصولات ویژه دسترسی داشته باشید:\n{invite_link}"
            )
            logging.info(f"کاربر {user_id} از طریق Mini App به VIP ارتقا یافت")
        elif action == "get_product":
            message_id = data.get('message_id')
            logging.info(f"درخواست محصول {message_id} از Mini App توسط کاربر {user_id}")
            if message_id not in self.private_content:
                await update.message.reply_text("محصول یافت نشد!")
                logging.error(f"محصول {message_id} در حافظه پیدا نشد")
                return

            is_vip = self.db.is_vip(user_id)
            if not is_vip:
                await update.message.reply_text("برای دریافت محصول، ابتدا اشتراک بخرید.")
                logging.info(f"کاربر غیر-VIP {user_id} درخواست محصول از Mini App کرد")
                return

            product = self.private_content[message_id]
            message_text = product["text"] or "بدون توضیح"
            file_id = product["file_id"]
            if file_id:
                await context.bot.send_document(
                    user_id,
                    file_id,
                    caption=f"{message_text}\nمحصول ویژه شما آماده دانلوده!"
                )
                logging.info(f"محصول {message_id} برای کاربر VIP {user_id} از Mini App ارسال شد")
            else:
                invite_link = await context.bot.export_chat_invite_link(PRIVATE_CHANNEL_ID)
                await update.message.reply_text(
                    f"{message_text}\nمحصول ویژه توی کانال خصوصی:\n{invite_link}"
                )
                logging.info(f"لینک کانال خصوصی به کاربر VIP {user_id} از Mini App ارسال شد")

    def run(self):
        # فقط مقداردهی اولیه انجام می‌شه، webhook توی app.py تنظیم شده
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.initialize())
        logging.info("بات با webhook آماده شد")