import csv
from io import StringIO
import keyring
import requests
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.error import TimedOut, BadRequest
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = keyring.get_password('token', 'tg')
CITY = 'Minsk'
RANDOM_SOUNDS = [
    r'C:\Users\USER\Downloads\e61cdb72dc8aa8c.mp3',
    # Если добавите еще файлы, пишите их через запятую здесь:
    # r'C:\Users\USER\Downloads\another_sound.mp3'
]
# ==== ФУНКЦИИ ДЛЯ API ====
def get_weather():
    # Проверьте эту строку: здесь СЛЭШ ОБЯЗАТЕЛЕН. Должно быть wttr.in/Minsk
    url = f"https://wttr.in/{CITY}?format=j1"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return f"Ошибка сервера погоды: статус {response.status_code}"
        
        r = response.json()
        
        # Печатаем структуру в консоль, чтобы вы видели, что присылает сайт
        print("--- ОТВЕТ ОТ WTTR.IN ПОЛУЧЕН ---")
        if "weather" in r and len(r["weather"]) > 0:
            print("Первый день погоды:", r["weather"][0].keys())
        
        forecast = []
        for day in r["weather"]:
            date = day["date"]
            avgtemp = day["avgtempC"]
            # Защита: проверяем структуру ответа wttr.in
            if "hourly" in day and len(day["hourly"]) > 0 and "weatherDesc" in day["hourly"][0]:
                desc = day["hourly"][0]["weatherDesc"][0]["value"]
            else:
                desc = "нет описания"
            forecast.append(f"{date}: {avgtemp}°C, {desc}")
        return "\n".join(forecast)
    except Exception as e:
        return f"Не удалось получить погоду: {e}"

def get_stock_price():
    ticker = "MSFT.US"
    # Проверьте эту строку: параметры должны идти после /q/l/?s=
    url = f"https://stooq.com/q/l/?s={ticker}&f=sd2t2ohlcv&h&e=csv"
    try:
        r = requests.get(url, timeout=5)
        r.encoding = "utf-8"
        data = list(csv.DictReader(StringIO(r.text)))
        if data and "Close" in data[0]:
            price = data[0]["Close"]
            return f"Цена акции {ticker}: {price} USD"
        else:
            return "Не удалось получить данные по акции."
    except Exception as e:
        return f"Ошибка при запросе акций: {e}"

def get_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return "Не удалось получить курс BTC (сервер недоступен)."
        
        r = response.json()
        if "bitcoin" in r and "usd" in r["bitcoin"]:
            price = r["bitcoin"]["usd"]
            return f"Bitcoin: {price} USD"
        else:
            return "Не удалось распарсить данные CoinGecko."
    except Exception as e:
        return f"Ошибка при запросе криптовалюты: {e}"

def get_IP():
    url = 'https://api.ipify.org?format=json'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return "Не удалось определить IP."
            
        r = response.json()
        return f"Your IP: {r['ip']}"
    except Exception as e:
        return f"Ошибка запроса IP: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Погода', 'Акции', 'Валюта', 'IP']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привет, выберите действие:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    try:
        # Проверка стандартных команд
        if text == 'погода':
            await update.message.reply_text(get_weather())
        elif text == 'акции':
            await update.message.reply_text(get_stock_price())
        elif text == 'валюта':
            await update.message.reply_text(get_btc_price())
        elif text == 'ip':
            await update.message.reply_text(get_IP())
            
        # Если человек нажал на кнопку «🎵 Аудио»
        elif text == '🎵 аудио':
            # Выбираем случайный путь из списка
            random_audio_path = random.choice(RANDOM_SOUNDS)
            
            try:
                # Открываем выбранный файл в бинарном режиме чтения
                with open(random_audio_path, 'rb') as audio_file:
                    await update.message.reply_audio(
                        audio=audio_file, 
                        caption='Случайный звук с компьютера', 
                        write_timeout=30
                    )
            except FileNotFoundError:
                await update.message.reply_text('Файл по этому пути не найден на компьютере.')
            except BadRequest:
                await update.message.reply_text('Не удалось отправить аудио.')
                
            # Возвращаем главное меню
            main_key = [['Погода', 'Акции', 'Валюта', 'IP']]
            reply_markup = ReplyKeyboardMarkup(main_key, resize_keyboard=True)
            await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
            
        # Если введено любое другое (неправильное) слово
        else:
            # 1. Сразу пишем текст ошибки
            await update.message.reply_text('Не понял команду.', write_timeout=60)
            
            # 2. Сразу отправляем картинку-предупреждение
            try:
                test_photo_url = 'https://picsum.photos'
                await update.message.reply_photo(photo=test_photo_url, caption='Пожалуйста, выберите действие из меню.')
            except BadRequest:
                pass
                
            # 3. Выводим новое меню, где есть только одно слово «🎵 Аудио»
            audio_key = [['🎵 Аудио']]
            reply_markup = ReplyKeyboardMarkup(audio_key, resize_keyboard=True)
            await update.message.reply_text("Новое действие:", reply_markup=reply_markup)
            
    except TimedOut:
        print('ТГ завис')
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка в коде: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот успешно запущен...")
    app.run_polling()

if __name__ == '__main__':
    main()