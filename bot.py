import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8796589455:AAEJTy8MnSNeaKzhP5T4Wxhj60CKYZzMiIU"
WEBAPP_URL = "https://heroic-eagerness-production-ca5b.up.railway.app"

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(
        "💪 Открыть тренировки",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )]]
    await update.message.reply_text(
        "👋 Привет! Нажми кнопку чтобы открыть каталог тренировок:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🤖 Бот запущен!")
    app.run_polling(drop_pending_upd
