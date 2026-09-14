import csv
from io import StringIO
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import keyring

TELEGRAM_TOKEN = keyring.get_password('token', 'tg')
CITY = 'Minsk'

# ==== ФУНКЦИИ ДЛЯ API ====

def get_weather():
    url = f"https://wttr.in/{CITY}?format=j1"
    r = requests.get(url).json()
    forecast = []
    for day in r["weather"]:
        date = day["date"]
        avgtemp = day["avgtempC"]
        desc = day["hourly"][4]["weatherDesc"][0]["value"]
        forecast.append(f"{date}: {avgtemp}°C, {desc}")
    return "\n".join(forecast)

def get_stock_price():
    ticker = "MSFT.US"
    url = f"https://stooq.com/q/l/?s={ticker}&f=sd2t2ohlcv&h&e=csv"
    r = requests.get(url)
    r.encoding = "utf-8"
    data = list(csv.DictReader(StringIO(r.text)))
    if data and "Close" in data[0]:
        price = data[0]["Close"]
        return f"Цена акции {ticker}: {price} USD"
    else:
        return "Не удалось получить данные по акции."

def get_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    r = requests.get(url).json()
    price = r["bitcoin"]["usd"]
    return f"Bitcoin: {price} USD"

def get_ip():
    url = 'https://api.ipify.org?format=json'
    r = requests.get(url).json()
    return f"Ваш IP: {r['ip']}"

def get_cat_url():
    url = "https://thecatapi.com"
    try:
        r = requests.get(url).json()
        return r[0]["url"]  # API возвращает список, берем первый элемент и ключ 'url'
    except Exception:
        return None


# ==== ОБРАБОТЧИКИ ТЕЛЕГРАМ ====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Названия кнопок теперь полностью совпадают с условиями проверки
    keyboard = [['Погода', 'Акции', 'Валюта', 'IP', 'Кот']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Привет, выберите действие:', reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    if text == 'погода':
        await update.message.reply_text(get_weather())
    elif text == 'акции':
        await update.message.reply_text(get_stock_price())
    elif text == 'валюта':
        await update.message.reply_text(get_btc_price())
    elif text == 'ip':
        await update.message.reply_text(get_ip())
    elif text == 'кот':
        cat_url = get_cat_url()
        if cat_url:
            await update.message.reply_photo(photo=cat_url, caption="Вот ваш котик! 🐱")
        else:
            await update.message.reply_text("Не удалось поймать котика, попробуйте позже.")
    else:
        await update.message.reply_text('Не понял команду')

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()