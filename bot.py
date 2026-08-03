import sqlite3
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "YOUR_BOT_TOKEN"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")

DB = "notifications.db"
app = None
scheduler = BackgroundScheduler()


def db():
    return sqlite3.connect(DB)


def init_db():
    con = db()
    con.execute("""
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        message TEXT,
        kind TEXT,
        notify_time TEXT,
        gif TEXT,
        done INTEGER DEFAULT 0
    )
    """)
    con.commit()
    con.close()


async def send_notify(chat_id, nid, message, gif):
    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Đã hoàn thành", callback_data=f"done_{nid}")]]
    )
    path = f"gifs/{gif}" if gif else None

    if path and Path(path).exists():
        await app.bot.send_animation(
            chat_id=chat_id,
            animation=open(path, "rb"),
            caption=f"🔔 NHẮC NHỞ\n\n{message}",
            reply_markup=button
        )
    else:
        await app.bot.send_message(
            chat_id=chat_id,
            text=f"🔔 NHẮC NHỞ\n\n{message}",
            reply_markup=button
        )


def check_time():
    now = datetime.now(TZ)
    day = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H:%M")

    con = db()
    rows = con.execute(
        "SELECT id,chat_id,message,kind,notify_time,gif,done FROM notifications"
    ).fetchall()

    for r in rows:
        if r[6]:
            continue
        if (r[3] == "daily" and r[4] == hour) or (r[3] == "once" and r[4] == f"{day} {hour}"):
            asyncio.run(send_notify(r[1], r[0], r[2], r[5]))

    con.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/them YYYY-MM-DD HH:MM noi dung gif.gif\n"
        "/them_ngay HH:MM noi dung gif.gif\n"
        "/list\n"
        "/xoa ID"
    )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    nid = q.data.split("_")[1]
    con = db()
    con.execute("UPDATE notifications SET done=1 WHERE id=?", (nid,))
    con.commit()
    con.close()
    await q.answer()
    await q.edit_message_text("✅ Đã hoàn thành. Dừng nhắc.")


def main():
    global app
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(done))

    scheduler.add_job(check_time, "interval", minutes=1)
    scheduler.start()

    app.run_polling()


if __name__ == "__main__":
    main()