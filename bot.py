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


def connect():
    return sqlite3.connect(DB)


def init_db():
    con = connect()
    con.execute("""
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        message TEXT,
        kind TEXT,
        notify_time TEXT,
        done INTEGER DEFAULT 0
    )
    """)
    con.commit()
    con.close()


async def send_notify(chat_id, nid, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Đã hoàn thành", callback_data=f"done_{nid}")]
    ])
    await app.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 NHẮC NHỞ\n\n{message}",
        reply_markup=keyboard
    )


def check_notify():
    now = datetime.now(TZ)
    day = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H:%M")

    con = connect()
    rows = con.execute(
        "SELECT id,chat_id,message,kind,notify_time,done FROM notifications"
    ).fetchall()

    for r in rows:
        if r[5] == 1:
            continue

        if r[3] == "daily" and r[4] == hour:
            asyncio.run(send_notify(r[1], r[0], r[2]))

        if r[3] == "once" and r[4] == f"{day} {hour}":
            asyncio.run(send_notify(r[1], r[0], r[2]))

    con.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/them YYYY-MM-DD HH:MM Nội dung\n"
        "/them_ngay HH:MM Nội dung\n"
        "/list\n"
        "/xoa ID"
    )


async def them(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("/them 2026-08-10 09:00 Nội dung")
        return

    con = connect()
    con.execute(
        "INSERT INTO notifications(chat_id,message,kind,notify_time) VALUES(?,?,?,?)",
        (update.effective_chat.id,
         " ".join(context.args[2:]),
         "once",
         context.args[0] + " " + context.args[1])
    )
    con.commit()
    con.close()

    await update.message.reply_text("✅ Đã thêm thông báo")


async def them_ngay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("/them_ngay 08:00 Nội dung")
        return

    con = connect()
    con.execute(
        "INSERT INTO notifications(chat_id,message,kind,notify_time) VALUES(?,?,?,?)",
        (update.effective_chat.id,
         " ".join(context.args[1:]),
         "daily",
         context.args[0])
    )
    con.commit()
    con.close()

    await update.message.reply_text("✅ Đã thêm lịch hàng ngày")


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = connect()
    rows = con.execute(
        "SELECT id,message,notify_time FROM notifications WHERE chat_id=?",
        (update.effective_chat.id,)
    ).fetchall()
    con.close()

    if not rows:
        await update.message.reply_text("Không có lịch")
        return

    text = "📋 Danh sách:\n\n"
    for r in rows:
        text += f"{r[0]} - {r[1]} - {r[2]}\n"

    await update.message.reply_text(text)


async def xoa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = connect()
    con.execute(
        "DELETE FROM notifications WHERE id=? AND chat_id=?",
        (context.args[0], update.effective_chat.id)
    )
    con.commit()
    con.close()
    await update.message.reply_text("✅ Đã xóa")


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    nid = q.data.split("_")[1]

    con = connect()
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
    app.add_handler(CommandHandler("them", them))
    app.add_handler(CommandHandler("them_ngay", them_ngay))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("xoa", xoa))
    app.add_handler(CallbackQueryHandler(done))

    scheduler.add_job(check_notify, "interval", minutes=1)
    scheduler.start()

    app.run_polling()


if __name__ == "__main__":
    main()