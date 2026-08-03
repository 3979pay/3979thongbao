# Telegram Notify Bot v4.1
# Replace TOKEN with your BotFather token.

TOKEN = "YOUR_BOT_TOKEN"

from telegram.ext import Application

def main():
    app = Application.builder().token(TOKEN).build()
    app.run_polling()

if __name__ == "__main__":
    main()
