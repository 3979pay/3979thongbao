from telegram.ext import Application

TOKEN = "YOUR_BOT_TOKEN"

def main():
    app = Application.builder().token(TOKEN).build()
    app.run_polling()

if __name__ == "__main__":
    main()
