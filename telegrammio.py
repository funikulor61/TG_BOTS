from io import StringIO
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import csv
import requests
import keyring




TELEGRAM_TOKEN = keyring.get_password('token', 'tg')
CITY = 'Minsk'

# ==== ФУНКЦИИ ДЛЯ API ====
def get_weather():
    # Бесплатный API wttr.in
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
    # Пример: MSFT.US — Microsoft, AAPL.US — Apple
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

def get_IP():
    url = 'https://api.ipify.org?format=json'
    r = requests.get(url).json()
    return f'Your IP: {r}'
    

# === MAIN FUNCS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Погода', 'Акции', 'Валюта', 'IP']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привет, выберите действие:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    if text == 'погода':
        await update.message.reply_text(get_weather())
    elif text == 'акции':
        await update.message.reply_text(get_stock_price())
    elif text == 'валюта':
        await update.message.reply_text(get_btc_price())
    elif text == 'ip':  # Исправлено под нижний регистр кнопки 'IP'
        await update.message.reply_text(get_IP())
    else:
        # ---- ЭТОТ БЛОК СРАБОТАЕТ, ЕСЛИ КОМАНДА НЕ РАСПОЗНАНА ----
        
        # 1. Сначала пишем текст ошибки
        await update.message.reply_text('Не понял команду. Выберите из меню')
        # 2. Отправляем аудио и видео
        await update.message.reply_audio(
            audio='https://www.image2url.com/r2/default/audio/1789107910206-7deabcf4-5d44-4c2f-96fe-d27bfb638231.mp3', 
            caption='некий caption', 
            title='Лесничество', 
            performer='Лесная Братва'
        )
        await update.message.reply_
        
        # 3. Готовим новую клавиатуру
        new_keyboard = [['памагите']]
        reply_markup = ReplyKeyboardMarkup(new_keyboard, resize_keyboard=True)
        
        # 4. Отправляем фото и прикрепляем к нему новую клавиатуру
        

        
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()