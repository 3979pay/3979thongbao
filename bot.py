import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "YOUR_BOT_TOKEN"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")

DB = "notifications.db"
app = None
scheduler = BackgroundScheduler()


def conn():
    return sqlite3.connect(DB)


def init_db():
    c = conn()
    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        message TEXT,
        kind TEXT,
        notify_time TEXT,
        last_notify TEXT,
        repeat_count INTEGER DEFAULT 0,
        done INTEGER DEFAULT 0
    )
    """)
    c.commit()
    c.close()


def now_vn():
    return datetime.now(TZ)


async def send_reminder(row):
    nid, chat_id, message, repeat = row
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Đã hoàn thành", callback_data=f"done_{nid}")]]
    )

    text = (
        "⚠️ Để ý nha~ không đùa đâu!\n\n"
        f"📝 Nội dung:\n{message}\n\n"
        f"⏳ Đã chờ xác nhận: {repeat * 3} phút\n"
        f"🔁 Lần nhắc: {repeat}\n\n"
        "Nếu chưa xác nhận sẽ nhắc lại sau 3 phút."
    )

    await app.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=kb
    )


def checker():
    now = now_vn()
    day = now.strftime("%Y-%m-%d")
    hm = now.strftime("%H:%M")

    c = conn()
    rows = c.execute(
        "SELECT id,chat_id,message,kind,notify_time,last_notify,repeat_count,done FROM notifications"
    ).fetchall()

    for r in rows:
        if r[7]:
            continue

        send = False
        repeat = r[6]

        if r[3] == "daily" and r[4] == hm and r[5] is None:
            send = True

        if r[3] == "once" and r[4] == f"{day} {hm}" and r[5] is None:
            send = True

        if r[5]:
            last = datetime.fromisoformat(r[5])
            if (now - last).total_seconds() >= 180:
                send = True

        if send:
            asyncio.run(send_reminder((r[0], r[1], r[2], repeat)))
            c.execute(
                "UPDATE notifications SET last_notify=?, repeat_count=? WHERE id=?",
                (now.isoformat(), repeat + 1, r[0])
            )

    c.commit()
    c.close()


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

    c = conn()
    c.execute(
        "INSERT INTO notifications(chat_id,message,kind,notify_time) VALUES(?,?,?,?)",
        (update.effective_chat.id, " ".join(context.args[2:]), "once",
         context.args[0]+" "+context.args[1])
    )
    c.commit()
    c.close()
    await update.message.reply_text("✅ Đã cài thông báo")


async def them_ngay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("/them_ngay 08:00 Nội dung")
        return

    c = conn()
    c.execute(
        "INSERT INTO notifications(chat_id,message,kind,notify_time) VALUES(?,?,?,?)",
        (update.effective_chat.id, " ".join(context.args[1:]), "daily", context.args[0])
    )
    c.commit()
    c.close()
    await update.message.reply_text("✅ Đã cài lịch hàng ngày")


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    nid = q.data.split("_")[1]
    c = conn()
    c.execute("UPDATE notifications SET done=1 WHERE id=?", (nid,))
    c.commit()
    c.close()

    await q.edit_message_text("✅ Đã hoàn thành. Đã dừng nhắc.")


def main():
    global app
    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("them", them))
    app.add_handler(CommandHandler("them_ngay", them_ngay))
    app.add_handler(CallbackQueryHandler(done))

    scheduler.add_job(checker, "interval", seconds=30)
    scheduler.start()

    app.run_polling()


if __name__ == "__main__":
    main()