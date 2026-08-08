import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# CẤU HÌNH
# =========================

TOKEN = "8776864453:AAEGGFR09xA1gXfEjDne5n6NXl9yAWPW0Vs"

ADMIN_ID = 7028707015

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DB = "notifications.db"


# =========================
# DATABASE
# =========================

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

    con.execute("""
        CREATE TABLE IF NOT EXISTS allowed_users(
            user_id INTEGER PRIMARY KEY
        )
    """)

    # Admin luôn có quyền
    con.execute(
        "INSERT OR IGNORE INTO allowed_users(user_id) VALUES(?)",
        (ADMIN_ID,)
    )

    con.commit()
    con.close()


# =========================
# KIỂM TRA QUYỀN
# =========================

def is_allowed(user_id):
    if user_id == ADMIN_ID:
        return True

    con = connect()

    row = con.execute(
        "SELECT 1 FROM allowed_users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    con.close()

    return row is not None


# =========================
# ID
# =========================

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text(
        f"🆔 Telegram ID của bạn:\n\n{user_id}"
    )


# =========================
# THÊM QUYỀN
# =========================

async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text(
            "⛔ Bạn không có quyền sử dụng lệnh này."
        )

    if not context.args:
        return await update.message.reply_text(
            "Cách dùng:\n/adduser ID"
        )

    try:
        user_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text(
            "❌ ID không hợp lệ."
        )

    con = connect()

    con.execute(
        "INSERT OR IGNORE INTO allowed_users(user_id) VALUES(?)",
        (user_id,)
    )

    con.commit()
    con.close()

    await update.message.reply_text(
        f"✅ Đã cấp quyền\n\n🆔 {user_id}"
    )


# =========================
# XÓA QUYỀN
# =========================

async def deluser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text(
            "⛔ Bạn không có quyền sử dụng lệnh này."
        )

    if not context.args:
        return await update.message.reply_text(
            "Cách dùng:\n/deluser ID"
        )

    try:
        user_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text(
            "❌ ID không hợp lệ."
        )

    if user_id == ADMIN_ID:
        return await update.message.reply_text(
            "⛔ Không thể xóa quyền Admin."
        )

    con = connect()

    con.execute(
        "DELETE FROM allowed_users WHERE user_id=?",
        (user_id,)
    )

    con.commit()
    con.close()

    await update.message.reply_text(
        f"🗑 Đã xóa quyền\n\n🆔 {user_id}"
    )


# =========================
# DANH SÁCH NGƯỜI ĐƯỢC QUYỀN
# =========================

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text(
            "⛔ Bạn không có quyền sử dụng lệnh này."
        )

    con = connect()

    rows = con.execute(
        "SELECT user_id FROM allowed_users ORDER BY user_id"
    ).fetchall()

    con.close()

    text = "👥 DANH SÁCH ĐƯỢC PHÉP\n\n"

    for row in rows:
        if row[0] == ADMIN_ID:
            text += f"👑 {row[0]} - ADMIN\n"
        else:
            text += f"👤 {row[0]}\n"

    await update.message.reply_text(text)


# =========================
# GỬI THÔNG BÁO
# =========================

async def send_notify(chat_id, nid, message, repeat):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Đã hoàn thành",
                callback_data=f"done_{nid}"
            )
        ]
    ])

    with open("gifs/IMG_4396.MP4", "rb") as video:
        await app.bot.send_animation(
            chat_id=chat_id,
            animation=video,
            caption=(
                "⚠️ Để ý nha~ không đùa đâu!\n\n"
                f"📝 Nội dung:\n{message}\n\n"
                "🕐 Múi giờ: GMT+7\n"
                "Không xác nhận sẽ nhắc lại sau 3 phút."
            ),
            reply_markup=kb
        )


# =========================
# KIỂM TRA LỊCH
# =========================

async def check_notifications(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TZ)

    day = now.strftime("%Y-%m-%d")
    hm = now.strftime("%H:%M")

    con = connect()

    rows = con.execute(
        """
        SELECT
            id,
            chat_id,
            message,
            kind,
            notify_time,
            last_sent,
            repeat_count,
            done
        FROM notifications
        """
    ).fetchall()

    for r in rows:

        if r[7]:
            continue

        send = False

        # Lịch hàng ngày
        if (
            r[3] == "daily"
            and r[4] == hm
            and r[5] is None
        ):
            send = True

        # Lịch 1 lần
        if (
            r[3] == "once"
            and r[4] == f"{day} {hm}"
            and r[5] is None
        ):
            send = True

        # Nhắc lại sau 3 phút
        if r[5]:
            last = datetime.fromisoformat(r[5])

            if (now - last).total_seconds() >= 180:
                send = True

        if send:
            await send_notify(
                r[1],
                r[0],
                r[2],
                r[6] + 1
            )

            con.execute(
                """
                UPDATE notifications
                SET
                    last_sent=?,
                    repeat_count=repeat_count+1
                WHERE id=?
                """,
                (
                    now.isoformat(),
                    r[0]
                )
            )

    con.commit()
    con.close()


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_allowed(user_id):
        return await update.message.reply_text(
            "⛔ Bạn chưa được cấp quyền sử dụng bot.\n\n"
            f"🆔 ID của bạn: {user_id}\n\n"
            "Gửi ID này cho Admin để được cấp quyền."
        )

    await update.message.reply_text(
        "🔔 BOT NHẮC NHỞ\n\n"
        "/them YYYY-MM-DD HH:MM Nội dung\n"
        "/them_ngay HH:MM Nội dung\n"
        "/list\n"
        "/xoa ID\n"
        "/id"
    )


# =========================
# THÊM LỊCH 1 LẦN
# =========================

async def them(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return await update.message.reply_text(
            "⛔ Bạn chưa được cấp quyền sử dụng bot."
        )

    if len(context.args) < 3:
        return await update.message.reply_text(
            "/them 2026-08-10 09:00 Nội dung"
        )

    time = context.args[0] + " " + context.args[1]
    msg = " ".join(context.args[2:])

    con = connect()

    con.execute(
        """
        INSERT INTO notifications(
            chat_id,
            message,
            kind,
            notify_time
        )
        VALUES(?,?,?,?)
        """,
        (
            update.effective_chat.id,
            msg,
            "once",
            time
        )
    )

    con.commit()
    con.close()

    await update.message.reply_text(
        f"✅ Đã cài thông báo\n\n"
        f"⏰ {time}\n"
        f"🌏 GMT+7\n"
        f"📝 {msg}\n\n"
        "🔁 Không xác nhận sẽ nhắc lại sau 3 phút"
    )


# =========================
# THÊM LỊCH HÀNG NGÀY
# =========================

async def them_ngay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return await update.message.reply_text(
            "⛔ Bạn chưa được cấp quyền sử dụng bot."
        )

    if len(context.args) < 2:
        return await update.message.reply_text(
            "/them_ngay 08:00 Nội dung"
        )

    msg = " ".join(context.args[1:])

    con = connect()

    con.execute(
        """
        INSERT INTO notifications(
            chat_id,
            message,
            kind,
            notify_time
        )
        VALUES(?,?,?,?)
        """,
        (
            update.effective_chat.id,
            msg,
            "daily",
            context.args[0]
        )
    )

    con.commit()
    con.close()

    await update.message.reply_text(
        f"✅ Đã cài lịch hàng ngày\n\n"
        f"⏰ {context.args[0]}\n"
        f"🌏 GMT+7\n"
        f"📝 {msg}"
    )


# =========================
# DANH SÁCH LỊCH
# =========================

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return await update.message.reply_text(
            "⛔ Bạn chưa được cấp quyền sử dụng bot."
        )

    con = connect()

    rows = con.execute(
        """
        SELECT id,message,notify_time
        FROM notifications
        WHERE chat_id=?
        """,
        (update.effective_chat.id,)
    ).fetchall()

    con.close()

    if not rows:
        return await update.message.reply_text(
            "Không có lịch"
        )

    text = "📋 Danh sách:\n\n"

    for r in rows:
        text += (
            f"ID: {r[0]}\n"
            f"📝 {r[1]}\n"
            f"⏰ {r[2]} GMT+7\n\n"
        )

    await update.message.reply_text(text)


# =========================
# XÓA LỊCH
# =========================

async def xoa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return await update.message.reply_text(
            "⛔ Bạn chưa được cấp quyền sử dụng bot."
        )

    if not context.args:
        return await update.message.reply_text(
            "Cách dùng:\n/xoa ID"
        )

    try:
        nid = int(context.args[0])
    except ValueError:
        return await update.message.reply_text(
            "❌ ID lịch không hợp lệ."
        )

    con = connect()

    con.execute(
        """
        DELETE FROM notifications
        WHERE id=? AND chat_id=?
        """,
        (
            nid,
            update.effective_chat.id
        )
    )

    con.commit()
    con.close()

    await update.message.reply_text(
        "✅ Đã xóa"
    )


# =========================
# HOÀN THÀNH
# =========================

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    # Người không được cấp quyền không thể bấm hoàn thành
    if not is_allowed(q.from_user.id):
        return await q.answer(
            "⛔ Bạn không có quyền.",
            show_alert=True
        )

    await q.answer("✅ Đã xác nhận")

    nid = q.data.split("_")[1]

    con = connect()

    con.execute(
        """
        UPDATE notifications
        SET done=1
        WHERE id=?
        """,
        (nid,)
    )

    con.commit()
    con.close()

    # Xóa toàn bộ video + chữ + nút
    await context.bot.delete_message(
        chat_id=q.message.chat_id,
        message_id=q.message.message_id
    )


# =========================
# CHẠY BOT
# =========================

def main():
    global app

    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("id", id_cmd)
    )

    app.add_handler(
        CommandHandler("adduser", adduser)
    )

    app.add_handler(
        CommandHandler("deluser", deluser)
    )

    app.add_handler(
        CommandHandler("users", users_cmd)
    )

    app.add_handler(
        CommandHandler("them", them)
    )

    app.add_handler(
        CommandHandler("them_ngay", them_ngay)
    )

    app.add_handler(
        CommandHandler("list", list_cmd)
    )

    app.add_handler(
        CommandHandler("xoa", xoa)
    )

    app.add_handler(
        CallbackQueryHandler(done)
    )

    app.job_queue.run_repeating(
        check_notifications,
        interval=30,
        first=5
    )

    app.run_polling()


if __name__ == "__main__":
    main()
