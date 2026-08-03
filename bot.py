import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

TOKEN = "YOUR_BOT_TOKEN"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DB = "notifications.db"

app = None
scheduler = BackgroundScheduler()

def db():
    return sqlite3.connect(DB)

def init_db():
    c = db()
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

async def send_notice(chat_id, nid, message, count):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Đã hoàn thành", callback_data=f"done_{nid}")]
    ])
    await app.bot.send_message(
        chat_id=chat_id,
        text=(
            "⚠️ Để ý nha~ không đùa đâu!\n\n"
            f"📝 Nội dung:\n{message}\n\n"
            f"⏳ Đã chờ xác nhận: {count*3} phút\n"
            f"🔁 Lần nhắc: {count}\n\n"
            "3 phút nữa sẽ nhắc lại nếu chưa hoàn thành."
        ),
        reply_markup=kb
    )

def check():
    now = datetime.now(TZ)
    hm = now.strftime("%H:%M")
    day = now.strftime("%Y-%m-%d")
    c = db()
    rows = c.execute(
        "SELECT id,chat_id,message,kind,notify_time,last_notify,repeat_count,done FROM notifications"
    ).fetchall()

    for r in rows:
        if r[7]:
            continue
        send = False
        if r[3] == "daily" and r[4] == hm and r[5] is None:
            send = True
        if r[3] == "once" and r[4] == f"{day} {hm}" and r[5] is None:
            send = True
        if r[5]:
            last = datetime.fromisoformat(r[5])
            if (now-last).total_seconds() >= 180:
                send = True
        if send:
            asyncio.run(send_notice(r[1], r[0], r[2], r[6]))
            c.execute(
                "UPDATE notifications SET last_notify=?, repeat_count=repeat_count+1 WHERE id=?",
                (now.isoformat(), r[0])
            )
    c.commit()
    c.close()

async def start(u, c):
    await u.message.reply_text("/them YYYY-MM-DD HH:MM Nội dung\n/them_ngay HH:MM Nội dung\n/list\n/xoa ID")

async def done(u, c):
    q = u.callback_query
    await q.answer("Đã xác nhận!")
    nid = q.data.split("_")[1]
    con = db()
    con.execute("UPDATE notifications SET done=1 WHERE id=?", (nid,))
    con.commit()
    con.close()
    await q.edit_message_text("✅ Đã hoàn thành\nĐã dừng nhắc việc này.")

def main():
    global app
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(done))
    scheduler.add_job(check, "interval", seconds=30)
    scheduler.start()
    app.run_polling()

if __name__ == "__main__":
    main()