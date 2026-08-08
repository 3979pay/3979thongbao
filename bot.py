import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

TOKEN = "8776864453:AAEGGFR09xA1gXfEjDne5n6NXl9yAWPW0Vs"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DB = "notifications.db"


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
        last_sent TEXT,
        repeat_count INTEGER DEFAULT 0,
        done INTEGER DEFAULT 0
    )
    """)
    con.commit()
    con.close()


async def send_notify(chat_id, nid, message, repeat):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Đã hoàn thành", callback_data=f"done_{nid}")]
    ])

    with open("gifs/IMG_4396.MP4", "rb") as video:
        await app.bot.send_animation(
            chat_id=chat_id,
            animation=video,
            caption=(
                "⚠️ Để ý nha~ không đùa đâu!\n\n"
                f"📝 Nội dung:\n{message}\n\n"
                "Không xác nhận sẽ nhắc lại sau 3 phút."
            ),
            reply_markup=kb
        )


async def check_notifications(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TZ)
    day = now.strftime("%Y-%m-%d")
    hm = now.strftime("%H:%M")

    con = connect()
    rows = con.execute(
        "SELECT id,chat_id,message,kind,notify_time,last_sent,repeat_count,done FROM notifications"
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
            if (now - last).total_seconds() >= 180:
                send = True

        if send:
            await send_notify(r[1], r[0], r[2], r[6] + 1)
            con.execute(
                "UPDATE notifications SET last_sent=?, repeat_count=repeat_count+1 WHERE id=?",
                (now.isoformat(), r[0])
            )

    con.commit()
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
        return await update.message.reply_text(
            "/them 2026-08-10 09:00 Nội dung"
        )

    time = context.args[0] + " " + context.args[1]
    msg = " ".join(context.args[2:])

    con = connect()
    con.execute(
        "INSERT INTO notifications(chat_id,message,kind,notify_time) VALUES(?,?,?,?)",
        (update.effective_chat.id, msg, "once", time)
    )
    con.commit()
    con.close()

    await update.message.reply_text(
        f"✅ Đã cài thông báo\n\n⏰ {time}\n📝 {msg}\n\n🔁 Không xác nhận sẽ nhắc lại sau 3 phút"
    )


async def them_ngay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text(
            "/them_ngay 08:00 Nội dung"
        )

    con = connect()
    msg = " ".join(context.args[1:])
    con.execute(
        "INSERT INTO notifications(chat_id,message,kind,notify_time) VALUES(?,?,?,?)",
        (update.effective_chat.id, msg, "daily", context.args[0])
    )
    con.commit()
    con.close()

    await update.message.reply_text(
        f"✅ Đã cài lịch hàng ngày\n\n⏰ {context.args[0]}\n📝 {msg}"
    )


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = connect()
    rows = con.execute(
        "SELECT id,message,notify_time FROM notifications WHERE chat_id=?",
        (update.effective_chat.id,)
    ).fetchall()
    con.close()

    if not rows:
        return await update.message.reply_text("Không có lịch")

    text = "📋 Danh sách:\n"
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
    await q.answer("Đã xác nhận")

    nid = q.data.split("_")[1]

    con = connect()
    con.execute(
        "UPDATE notifications SET done=1 WHERE id=?",
        (nid,)
    )
    con.commit()
    con.close()

    await q.edit_message_text("✅ Đã hoàn thành\nĐã dừng nhắc.")


async def main():
    global app

    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("them", them))
    app.add_handler(CommandHandler("them_ngay", them_ngay))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("xoa", xoa))
    app.add_handler(CallbackQueryHandler(done))

    app.job_queue.run_repeating(check_notifications, interval=30)

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

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

    app.job_queue.run_repeating(check_notifications, interval=30)

    app.run_polling()


if __name__ == "__main__":
    main()
