"""
Локальный запуск: Telegram-бот + FastAPI-бэкенд.
HTML лежит отдельно на GitHub Pages.
Запуск: python main.py
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
import keyring
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ─────────────────────────────────────────────────────────────
# НАСТРОЙКИ — заполните эти три переменные
# ─────────────────────────────────────────────────────────────
BOT_TOKEN = keyring.get_password('token', 'tg')

# URL вашего WebApp на GitHub Pages (с завершающим слешем)
# Пример: "https://username.github.io/music-app/"
WEBAPP_URL = "https://funikulor61.github.io/tg_webapp_1/"

# Публичный HTTPS-адрес от ngrok (без завершающего слеша)
# Пример: "https://abc123.ngrok-free.app"
PUBLIC_URL = "https://3c12d6n8-8000.euw.devtunnels.ms/"

PORT = 8000
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════
# ЧАСТЬ 1: FASTAPI-БЭКЕНД (принимает файлы)
# ═════════════════════════════════════════════════════════════
app = FastAPI(title="Music Uploader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с GitHub Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Раздаём загруженные файлы
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")


@app.post("/api/upload")
async def upload_audio(audio: UploadFile = File(...)):
    """Принимает аудиофайл, сохраняет и возвращает публичную ссылку."""
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Файл должен быть аудиоформатом")

    MAX_SIZE = 50 * 1024 * 1024
    audio.file.seek(0, 2)
    file_size = audio.file.tell()
    audio.file.seek(0)
    if file_size > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс. 50 MB)")

    ext = Path(audio.filename).suffix or ".mp3"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename

    try:
        with open(filepath, "wb") as buffer:
            buffer.write(await audio.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения: {e}")

    base = PUBLIC_URL.rstrip("/")
    public_url = f"{base}/files/{filename}"

    return JSONResponse({
        "success": True,
        "url": public_url,
        "filename": audio.filename,
        "size": file_size,
        "uploaded_at": datetime.utcnow().isoformat(),
    })


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ═════════════════════════════════════════════════════════════
# ЧАСТЬ 2: TELEGRAM-БОТ
# ═════════════════════════════════════════════════════════════
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Кнопка открытия WebApp (HTML с GitHub Pages)."""
    await update.message.reply_text(
        "Нажмите кнопку, чтобы открыть загрузчик музыки:",
        reply_markup=ReplyKeyboardMarkup.from_button(
            KeyboardButton(
                text="🎵 Открыть загрузчик",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ),
    )


async def on_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получаем данные, отправленные из HTML через tg.sendData()."""
    try:
        data = json.loads(update.effective_message.web_app_data.data)
    except Exception as e:
        logger.error(f"Ошибка разбора данных: {e}")
        return

    logger.info(f"Данные из WebApp: {data}")

    if "url" in data:
        await update.message.reply_html(
            f"✅ Файл загружен!\n<code>{data['url']}</code>",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text("Данные получены, но ссылки нет.")


def build_bot() -> Application:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(
        MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_web_app_data)
    )
    return application


# ═════════════════════════════════════════════════════════════
# ЧАСТЬ 3: ПАРАЛЛЕЛЬНЫЙ ЗАПУСК
# ═════════════════════════════════════════════════════════════
async def run_all():
    # uvicorn как asyncio-задача
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    # Бот
    bot_app = build_bot()
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    logger.info(f"✅ Бэкенд локально: http://localhost:{PORT}")
    logger.info(f"✅ Бэкенд снаружи: {PUBLIC_URL}")
    logger.info(f"✅ WebApp (GitHub Pages): {WEBAPP_URL}")
    logger.info("Нажмите Ctrl+C для остановки.")

    try:
        await server_task
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        print("\n👋 Остановлено.")