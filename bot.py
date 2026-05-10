import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8796589455:AAEJTy8MnSNeaKzhP5T4Wxhj60CKYZzMiIU"  # Вставь токен от @BotFather

logging.basicConfig(level=logging.INFO)

# ==============================
# КАТАЛОГ ТРЕНИРОВОК
# ==============================
CATALOG = {
    "breath": {
        "title": "🌬️ Дыхание",
        "items": [
            ("Метод Вима Хофа", "https://t.me/vimhofprac"),
        ]
    },
    "gymn": {
        "title": "🤸 Гимнастика",
        "items": [
            ("Гимнастика для шеи (Шишонин)", "https://t.me/shishgimn"),
            ("Восстановление зрения (Жданов)", "https://t.me/jdanzren"),
        ]
    },
    "yoga": {
        "title": "🧘 Цигун и йога",
        "items": [
            ("Цигун", "https://t.me/liholden"),
            ("Йога нидра", "https://t.me/c/2994536092/120/1211"),
        ]
    },
    "face": {
        "title": "💆 Фейсбилдинг",
        "items": [
            ("Екатерина — Часть 1", "https://t.me/+piqhVLNzL_RiMjQy"),
            ("Екатерина — Часть 2", "https://t.me/+SOsZbQwL3IYxNmFi"),
            ("Екатерина — Часть 3", "https://t.me/+Y986VEUy8FwyYTcy"),
            ("Екатерина — Часть 4", "https://t.me/+3SSRWjsFi4VhZTcy"),
        ]
    },
    "bio": {
        "title": "⚙️ Биомеханика",
        "items": [
            ("Биомеханика", "https://t.me/+af3c1XonTeg3Zjdi"),
            ("МФР", "https://t.me/+EdbAKVizs61jNDky"),
            ("Динамические растяжки", "https://t.me/+2jCKBQJVhRc4MjM6"),
            ("Переобучение движению", "https://t.me/+qhb_GYcP3vs5NGIy"),
        ]
    },
    "massage": {
        "title": "👐 Массаж",
        "items": [
            ("Массаж глаз", "https://t.me/c/2994536092/120/1773"),
        ]
    },
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(CATALOG[key]["title"], callback_data=f"cat_{key}")]
        for key in CATALOG
    ]
    text = "💪 *Привет! Выбери категорию тренировки:*"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.replace("cat_", "")
    cat = CATALOG.get(key)
    if not cat:
        return
    keyboard = [
        [InlineKeyboardButton(f"▶️ {name}", url=url)]
        for name, url in cat["items"]
    ]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    await query.edit_message_text(
        f"*{cat['title']}*\n\nВыбери тренировку:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(show_category, pattern="^cat_"))
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
