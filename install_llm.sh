#!/bin/bash
mkdir -p tg_admin_bot tg_antigravity_bot tg_gemini_like_bot xray_client projects
cat << 'EON' > .env
TG_ADMIN_BOT_TOKEN=1234567890:ABCdefGh_admin_bot
TG_ANTIGRAVITY_BOT_TOKEN=1234567890:XYZabcDe_agent_bot
TG_GEMINI_BOT_TOKEN=1234567890:LMNopqrSt_ai_companion_bot
ALLOWED_TELEGRAM_ID=123456789
VLESS_SERVER_ADDRESS=vpn-client.gegaremant.ru
VLESS_SERVER_PORT=59305
VLESS_UUID=863ee7f5-67fb-4d0a-9d65-19311791c945
EON
cat << 'EON' > xray_client/config.json
{"inbounds":[{"port":1081,"protocol":"http","settings":{}}],"outbounds":[{"protocol":"vless","settings":{"vnext":[{"address":"vpn-client.gegaremant.ru","port":59305,"users":[{"id":"863ee7f5-67fb-4d0a-9d65-19311791c945","encryption":"none"}]}]},"streamSettings":{"network":"ws","security":"none","wsSettings":{"path":"/smart-vless/"}}}]}
EON
cat << 'EON' > docker-compose.yml
version: '3.8'
services:
  vless-client:
    image: teddysun/xray:latest
    container_name: vless-client
    restart: unless-stopped
    ports: ["1080:1080","1081:1081"]
    volumes: ["./xray_client:/etc/xray"]
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    ports: ["11434:11434"]
    volumes: ["ollama_data:/root/.ollama"]
    environment: ["http_proxy=http://vless-client:1081","https_proxy=http://vless-client:1081"]
    deploy:
      resources:
        reservations:
          devices: [{"driver":"nvidia","count":"all","capabilities":["gpu"]}]
    depends_on: ["vless-client"]
  tg-admin-bot:
    build: ./tg_admin_bot
    container_name: tg-admin-bot
    restart: unless-stopped
    environment: ["TELEGRAM_BOT_TOKEN=${TG_ADMIN_BOT_TOKEN}","ALLOWED_TELEGRAM_ID=${ALLOWED_TELEGRAM_ID}"]
    volumes: ["/var/run/docker.sock:/var/run/docker.sock","./xray_client:/etc/xray"]
  tg-antigravity-bot:
    build: ./tg_antigravity_bot
    container_name: tg-antigravity-bot
    restart: unless-stopped
    environment: ["TELEGRAM_BOT_TOKEN=${TG_ANTIGRAVITY_BOT_TOKEN}","ALLOWED_TELEGRAM_ID=${ALLOWED_TELEGRAM_ID}","OLLAMA_HOST=http://ollama:11434"]
    volumes: ["./projects:/workspace"]
    depends_on: ["ollama"]
  tg-gemini-like-bot:
    build: ./tg_gemini_like_bot
    container_name: tg-gemini-like-bot
    restart: unless-stopped
    environment: ["TELEGRAM_BOT_TOKEN=${TG_GEMINI_BOT_TOKEN}","ALLOWED_TELEGRAM_ID=${ALLOWED_TELEGRAM_ID}","OLLAMA_HOST=http://ollama:11434"]
    depends_on: ["ollama"]
  antigravity-ide:
    image: ghcr.io/antigravity-dev/ide:latest
    container_name: antigravity-ide
    restart: unless-stopped
    ports: ["36490:8080"]
    environment:
      - "PASSWORD=${VSCODE_PASSWORD:-secret}"
      - "OLLAMA_HOST=http://ollama:11434"
      - "http_proxy=http://vless-client:1081"
      - "https_proxy=http://vless-client:1081"
      - "no_proxy=localhost,127.0.0.1,0.0.0.0,ollama"
      - 'EXTENSIONS_GALLERY={"serviceUrl":"https://marketplace.visualstudio.com/_apis/public/gallery","cacheUrl":"https://vscode.blob.core.windows.net/gallery/index","itemUrl":"https://marketplace.visualstudio.com/items","controlUrl":"","recommendationsUrl":""}'
    volumes: ["/home/projects:/home/coder/project", "./code-server-config:/home/coder/.config"]
    depends_on: ["ollama"]
volumes:
  ollama_data:
    external: true
    name: gegaremant_helper_ollama_data
EON
mkdir -p tg_admin_bot tg_antigravity_bot tg_gemini_like_bot
echo "FROM python:3.10-slim" > tg_admin_bot/Dockerfile
echo "RUN pip install aiogram" >> tg_admin_bot/Dockerfile
echo "WORKDIR /app" >> tg_admin_bot/Dockerfile
echo "COPY bot.py ." >> tg_admin_bot/Dockerfile
echo "CMD [\"python\", \"bot.py\"]" >> tg_admin_bot/Dockerfile
cat << 'EON' > tg_admin_bot/bot.py
import os,asyncio
from aiogram import Bot,Dispatcher,types,F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
bot=Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp=Dispatcher()
@dp.message(Command("start"))
async def cmd_start(m:types.Message):
 if m.from_user.id!=int(os.getenv("ALLOWED_TELEGRAM_ID",0)):return
 b=ReplyKeyboardBuilder()
 b.button(text="📊 Статус GPU (Tesla)")
 b.button(text="🔄 Перезапустить VLESS")
 await m.answer("🛠️ Бот-администратор запущен.",reply_markup=b.as_markup(resize_keyboard=True))
@dp.message(F.text=="📊 Статус GPU (Tesla)")
async def gpu_status(m:types.Message):
 if m.from_user.id!=int(os.getenv("ALLOWED_TELEGRAM_ID",0)):return
 proc=await asyncio.create_subprocess_shell("nvidia-smi",stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
 o,e=await proc.communicate()
 await m.answer(f"```\n{o.decode('utf-8')}\n```",parse_mode="MarkdownV2")
@dp.message(F.text=="🔄 Перезапустить VLESS")
async def restart_vless(m:types.Message):
 if m.from_user.id!=int(os.getenv("ALLOWED_TELEGRAM_ID",0)):return
 await m.answer("🔄 Перезапускаю vless-client...")
 await asyncio.create_subprocess_shell("curl --unix-socket /var/run/docker.sock -X POST http://localhost/containers/vless-client/restart")
 await m.answer("✅ Перезапущен!")
async def main():await dp.start_polling(bot)
if __name__=="__main__":asyncio.run(main())
EON
echo "FROM python:3.10-slim" > tg_antigravity_bot/Dockerfile
echo "RUN apt-get update && apt-get install -y curl git uuid-runtime && rm -rf /var/lib/apt/lists/*" >> tg_antigravity_bot/Dockerfile
echo "RUN curl -fsSL https://antigravity.google/cli/install.sh | bash || echo 'OpenHands fallback'" >> tg_antigravity_bot/Dockerfile
echo "RUN pip install aiogram pexpect" >> tg_antigravity_bot/Dockerfile
echo "WORKDIR /app" >> tg_antigravity_bot/Dockerfile
echo "COPY bot.py ." >> tg_antigravity_bot/Dockerfile
echo "CMD [\"python\", \"bot.py\"]" >> tg_antigravity_bot/Dockerfile
cat << 'EON' > tg_antigravity_bot/bot.py
import os,asyncio,pexpect
from aiogram import Bot,Dispatcher,types,F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
bot=Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp=Dispatcher()
act={}
@dp.message(Command("start"))
async def cmd_start(m:types.Message):
 if m.from_user.id==int(os.getenv("ALLOWED_TELEGRAM_ID",0)):await m.answer("🤖 Диспетчер готов!")
@dp.message(F.text)
async def handle_task(m:types.Message):
 if m.from_user.id!=int(os.getenv("ALLOWED_TELEGRAM_ID",0)):return
 try:
  ch=pexpect.spawn(f"antigravity run \"{m.text}\" --dir /workspace",encoding='utf-8',timeout=120)
  act[m.from_user.id]=ch
  await asyncio.sleep(3)
  out=ch.read_nonblocking(size=1000,timeout=5)
  b=InlineKeyboardBuilder().button(text="🚀 В бой",callback_data="approve")
  await m.answer(f"📝 План:\n```\n{out}\n```",reply_markup=b.as_markup())
 except Exception as e:await m.answer(f"❌ {e}")
@dp.callback_query(F.data=="approve")
async def approve(c:types.CallbackQuery):
 ch=act.get(c.from_user.id)
 if ch:
  ch.sendline('y')
  await c.message.edit_text("⚙️ Кодим на Tesla...")
  await asyncio.to_thread(ch.expect,pexpect.EOF)
  await c.message.answer("🎉 Готово в IDE!")
  ch.close();del act[c.from_user.id]
async def main():await dp.start_polling(bot)
if __name__=="__main__":asyncio.run(main())
EON
echo "FROM python:3.10-slim" > tg_gemini_like_bot/Dockerfile
echo "RUN pip install aiogram aiohttp" >> tg_gemini_like_bot/Dockerfile
echo "WORKDIR /app" >> tg_gemini_like_bot/Dockerfile
echo "COPY bot.py ." >> tg_gemini_like_bot/Dockerfile
echo "CMD [\"python\", \"bot.py\"]" >> tg_gemini_like_bot/Dockerfile
cat << 'EON' > tg_gemini_like_bot/bot.py
import os,asyncio,aiohttp
from aiogram import Bot,Dispatcher,types,F
from aiogram.filters import Command
bot=Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp=Dispatcher()
hist={}
sys_p="Ты — ИИ-ассистент на сервере. Общайся с инженерным юмором, адаптивно и кратко."
@dp.message(Command("start"))
async def cmd_start(m:types.Message):
 if m.from_user.id!=int(os.getenv("ALLOWED_TELEGRAM_ID",0)):return
 hist[m.from_user.id]=[]
 await m.answer("🧠 Локальный ИИ на связи! Чего замутим?")
@dp.message(Command("clear"))
async def cmd_clear(m:types.Message):
 if m.from_user.id!=int(os.getenv("ALLOWED_TELEGRAM_ID",0)):return
 hist[m.from_user.id]=[]
 await m.answer("🧹 Очищено!")
@dp.message(F.text)
async def handle_chat(m:types.Message):
 uid=m.from_user.id
 if uid!=int(os.getenv("ALLOWED_TELEGRAM_ID",0)):return
 if uid not in hist:hist[uid]=[]
 hist[uid].append({"role":"user","content":m.text})
 hist[uid]=hist[uid][-15:]
 pld={"model":"qwen2.5-coder:32b","messages":[{"role":"system","content":sys_p}]+hist[uid],"stream":False}
 s_msg=await m.answer("💭 Думаю...")
 async with aiohttp.ClientSession() as osess:
  try:
   async with osess.post(f"{os.getenv('OLLAMA_HOST')}/api/chat",json=pld,timeout=90) as r:
    if r.status==200:
     res=await r.json()
     ans=res["message"]["content"]
     hist[uid].append({"role":"assistant","content":ans})
     await s_msg.edit_text(ans,parse_mode="Markdown" if "```" in ans else None)
    else:await s_msg.edit_text("❌ Ошибка ядра Ollama.")
  except Exception as e:await s_msg.edit_text(f"💥 Ошибка: {e}")
async def main():await dp.start_polling(bot)
if __name__=="__main__":asyncio.run(main())
EON
echo "✅ Все файлы успешно развернуты!"
