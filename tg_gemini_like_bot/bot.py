import os, asyncio, aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession

# Ищем прокси в переменных окружения Docker (проверяем оба регистра)
proxy_url = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")

if proxy_url:
    print(f"🤖 Запуск бота через прокси: {proxy_url}")
    session = AiohttpSession(proxy=proxy_url)
else:
    print("⚠️ Прокси не найден в окружении, запуск напрямую...")
    session = None

# Инициализируем бота с правильной сессией
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"), session=session)
dp = Dispatcher()
hist = {}

# Промпт для твоего «клона»
sys_p = "Ты — продвинутый ИИ-ассистент, аналог Gemini. Общайся с инженерным юмором, адаптивно, глубоко, но лаконично."

async def get_active_model():
    """Автоматически ищет Hermes или любую доступную модель в Ollama"""
    ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Проверяем, что сейчас загружено в память
            async with session.get(f"{ollama_host}/api/ps") as r:
                if r.status == 200:
                    data = await r.json()
                    if data.get("models"):
                        return data["models"][0]["name"]

            # 2. Если память пуста, ищем Hermes в скачанных моделях
            async with session.get(f"{ollama_host}/api/tags") as r:
                if r.status == 200:
                    data = await r.json()
                    models = [m["name"] for m in data.get("models", [])]
                    if models:
                        hermes_models = [m for m in models if "hermes" in m.lower()]
                        return hermes_models[0] if hermes_models else models[0]
        except Exception as e:
            print(f"Ошибка опроса Ollama API: {e}")
    return "qwen3.6:27b"  # Твой бэкап

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    if m.from_user.id != int(os.getenv("ALLOWED_TELEGRAM_ID", 0)): return
    hist[m.from_user.id] = []
    current_model = await get_active_model()
    await m.answer(f"🧠 Аналог Gemini на связи!\n🤖 Активная модель: `{current_model}`\nЗадавай вопросы.")

@dp.message(Command("clear"))
async def cmd_clear(m: types.Message):
    if m.from_user.id != int(os.getenv("ALLOWED_TELEGRAM_ID", 0)): return
    hist[m.from_user.id] = []
    await m.answer("🧹 Контекст очищен!")

@dp.message(F.text)
async def handle_chat(m: types.Message):
    uid = m.from_user.id
    if uid != int(os.getenv("ALLOWED_TELEGRAM_ID", 0)): return
    if uid not in hist: hist[uid] = []

    hist[uid].append({"role": "user", "content": m.text})
    hist[uid] = hist[uid][-15:] # Храним последние 15 реплик

    current_model = await get_active_model()
    pld = {
        "model": current_model, 
        "messages": [{"role": "system", "content": sys_p}] + hist[uid], 
        "stream": False
    }
    s_msg = await m.answer("💭 Думаю...")
    async with aiohttp.ClientSession() as osess:
        try:
            async with osess.post(f"{os.getenv('OLLAMA_HOST')}/api/chat", json=pld, timeout=90) as r:
                if r.status == 200:
                    res = await r.json()
                    ans = res["message"]["content"]
                    hist[uid].append({"role": "assistant", "content": ans})
                    await s_msg.edit_text(ans, parse_mode="Markdown" if "```" in ans else None)
                else:
                    await s_msg.edit_text("❌ Ошибка ядра Ollama.")
        except Exception as e:
            await s_msg.edit_text(f"💥 Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
