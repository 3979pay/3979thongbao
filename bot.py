import sqlite3
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "YOUR_NEW_BOT_TOKEN"

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
        time TEXT
    )
    """)
    con.commit()
    con.close()


async def send_message(chat_id, text):
    await app.bot.send_message(chat_id=chat_id, text=text)


def check_notifications():
    now = datetime.now()

    con = db()
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id,chat_id,message,kind,time FROM notifications"
    ).fetchall()

    for row in rows:
        if row[3] == "daily" and now.strftime("%H:%M") == row[4]:
            asyncio.run(send_message(row[1], "🔔 " + row[2]))

        if row[3] == "once" and now.strftime("%Y-%m-%d %H:%M") == row[4]:
            asyncio.run(send_message(row[1], "🔔 " + row[2]))
            cur.execute("DELETE FROM notifications WHERE id=?", (row[0],))

    con.commit()
    con.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Telegram Notification Bot\n\n"
        "/them_daily HH:MM noi dung\n"
        "/them_once YYYY-MM-DD HH:MM noi dung\n"
        "/list\n"
        "/xoa ID"
    )


async def them_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("/them_daily 08:00 Noi dung")
        return

    con = db()
    con.execute(
        "INSERT INTO notifications VALUES(NULL,?,?,?,?)",
        (
            update.effective_chat.id,
            " ".join(context.args[1:]),
            "daily",
            context.args[0]
        )
    )
    con.commit()
    con.close()

    await update.message.reply_text("✅ Đã thêm lịch hàng ngày")


async def them_once(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("/them_once 2026-08-15 09:00 Noi dung")
        return

    con = db()
    con.execute(
        "INSERT INTO notifications VALUES(NULL,?,?,?,?)",
        (
            update.effective_chat.id,
            " ".join(context.args[2:]),
            "once",
            context.args[0] + " " + context.args[1]
        )
    )
    con.commit()
    con.close()

    await update.message.reply_text("✅ Đã thêm lịch")


async def list_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = db()
    rows = con.execute(
        "SELECT id,message,time FROM notifications WHERE chat_id=?",
        (update.effective_chat.id,)
    ).fetchall()
    con.close()

    if not rows:
        await update.message.reply_text("Không có thông báo")
        return

    text = "📋 Danh sách:\n\n"
    for r in rows:
        text += f"{r[0]} - {r[1]} - {r[2]}\n"

    await update.message.reply_text(text)


async def xoa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("/xoa ID")
        return

    con = db()
    con.execute(
        "DELETE FROM notifications WHERE id=? AND chat_id=?",
        (context.args[0], update.effective_chat.id)
    )
    con.commit()
    con.close()

    await update.message.reply_text("✅ Đã xóa")


def main():
    global app

    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("them_daily", them_daily))
    app.add_handler(CommandHandler("them_once", them_once))
    app.add_handler(CommandHandler("list", list_notify))
    app.add_handler(CommandHandler("xoa", xoa))

    scheduler.add_job(check_notifications, "interval", seconds=30)
    scheduler.start()

    app.run_polling()


if __name__ == "__main__":
    main()