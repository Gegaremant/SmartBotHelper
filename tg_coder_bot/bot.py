import os,asyncio,aiohttp,re,json,base64,subprocess
from aiogram import Bot,Dispatcher,types,F
from aiogram.filters import Command
from duckduckgo_search import DDGS
import speech_recognition as sr
from aiogram.types import FSInputFile
from aiogram.client.session.aiohttp import AiohttpSession

logging.basicConfig(level=logging.INFO)
ALLOWED_IDS = [int(x.strip()) for x in os.getenv("ALLOWED_TELEGRAM_ID", "0").split(",") if x.strip().isdigit()]

proxy_url = os.getenv("http_proxy") or os.getenv("HTTP_PROXY")
session = AiohttpSession(proxy=proxy_url) if proxy_url else None
bot=Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"), session=session)
dp=Dispatcher()
hist = {}
sys_p = "Ты — продвинутый ИИ-ассистент с доступом в интернет. Общайся с инженерным юмором. НИКОГДА не говори, что у тебя нет доступа к интернету — ты умеешь искать информацию в реальном времени, если это нужно."
STATE_FILE = "/workspace/shared_state.json"

def get_model(key="main_model", default="qwen3.6:27b"):
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get(key, default)
    except: pass
    return default

@dp.message(Command("start"))
async def cmd_start(m:types.Message):
 if m.from_user.id in ALLOWED_IDS:
  hist[m.from_user.id] = []
  await m.answer("🤖 Я универсальный ИИ-кодер и собеседник!\nПросто пиши мне, присылай фото или голосовые.\nДля редактирования файлов начни с `/code <задача>`.")

@dp.message(Command("clear"))
async def cmd_clear(m:types.Message):
 if m.from_user.id not in ALLOWED_IDS: return
 hist[m.from_user.id] = []
 await m.answer("🧹 Контекст беседы очищен!")

@dp.message(F.text.startswith("/code "))
async def handle_code_task(m:types.Message):
 if m.from_user.id not in ALLOWED_IDS: return
 task = m.text.replace("/code ", "", 1)
 msg = await m.answer(f"⏳ Думаю и пишу код (модель: {get_model()})...")
 try:
  await asyncio.create_subprocess_shell('git config --global user.name "Bot" && git config --global user.email "bot@example.com"')
  cmd = f"aider --model ollama/{get_model()} --yes --no-color --message \"{task}\""
  process = await asyncio.create_subprocess_shell(
   cmd, cwd="/workspace", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
  )
  stdout, _ = await process.communicate()
  out = stdout.decode('utf-8', errors='replace')
  out = re.sub(r'\x1b\[[0-9;]*m|\x1b\[\?[0-9]+[hl]', '', out)
  out = "\n".join([line for line in out.split("\n") if "Update git name" not in line and "Warning" not in line and line.strip() != ""])
  if len(out) > 3500: out = "..." + out[-3500:]
  if not out.strip(): out = "Задание выполнено (нет вывода)"
  await msg.edit_text(f"📝 Отчет:\n```text\n{out}\n```")
 except Exception as e:
  await msg.edit_text(f"❌ Ошибка:\n{e}")

async def do_chat(m:types.Message, text:str, extra_context="", reply_voice=False):
 uid = m.from_user.id
 if uid not in hist: hist[uid] = []
 
 user_content = text
 if extra_context: user_content = f"[Поиск в интернете даёт эту информацию: {extra_context}]\n\n{text}"
 
 hist[uid].append({"role": "user", "content": user_content})
 hist[uid] = hist[uid][-15:]

 s_msg = await m.answer("💭 ...")
 pld = {
  "model": get_model(),
  "messages": [{"role": "system", "content": sys_p}] + hist[uid],
  "stream": False
 }
 async with aiohttp.ClientSession() as osess:
  try:
   async with osess.post(f"{os.getenv('OLLAMA_HOST', 'http://ollama:11434')}/api/chat", json=pld, timeout=120) as r:
    if r.status == 200:
     res = await r.json()
     ans = res["message"]["content"]
     if not ans or not ans.strip():
      ans = "(Ой, модель сгенерировала пустой ответ. Попробуйте перефразировать запрос или сменить модель.)"
     hist[uid].append({"role": "assistant", "content": ans})
     await s_msg.edit_text(ans, parse_mode="Markdown" if "```" in ans else None)
     if reply_voice:
      tts_msg = await m.answer("🎙 Синтезирую ответ...")
      try:
          clean_ans = re.sub(r'```.*?```', '', ans, flags=re.DOTALL)
          clean_ans = re.sub(r'[*_`]', '', clean_ans)
          if not clean_ans.strip(): clean_ans = "В моём ответе только код или спецсимволы."
          
          with open("tts_temp.txt", "w", encoding="utf-8") as f:
              f.write(clean_ans)
          voice_model = get_model("voice_model", "ru-RU-SvetlanaNeural")
          process = await asyncio.create_subprocess_shell(f'edge-tts --voice {voice_model} -f tts_temp.txt --write-media reply.ogg')
          await process.communicate()
          await m.answer_voice(FSInputFile("reply.ogg"))
          await tts_msg.delete()
      except Exception as e:
          await tts_msg.edit_text(f"❌ Ошибка синтеза речи: {e}")
    else:
     await s_msg.edit_text("❌ Ошибка ядра Ollama.")
  except Exception as e:
   await s_msg.edit_text(f"💥 Ошибка: {e}")

@dp.message(F.text)
async def handle_chat(m:types.Message):
 if m.from_user.id not in ALLOWED_IDS: return
 text = m.text
 extra_context = ""
 
 if re.search(r"(найди|поищи|кто такой|погода|цена|новости|интернет|найди в сети)", text, re.I):
  try:
   s_msg = await m.answer("🔍 Ищу в интернете...")
   results = await asyncio.to_thread(lambda: DDGS().text(text, max_results=3))
   extra_context = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
   if not extra_context:
       extra_context = "[Поиск в интернете не дал результатов или доступ заблокирован.]"
   await s_msg.delete()
  except Exception as e:
   print("Search error:", e)
   extra_context = f"[Ошибка поиска в интернете: {e}. Сообщите пользователю, что вы не смогли получить доступ к сети из-за технической ошибки.]"
   try: await s_msg.delete()
   except: pass
   
 await do_chat(m, text, extra_context)

@dp.message(F.voice)
async def handle_voice(m:types.Message):
 if m.from_user.id not in ALLOWED_IDS: return
 msg = await m.answer("⏳ Распознаю голос...")
 try:
  file = await bot.get_file(m.voice.file_id)
  b = await bot.download_file(file.file_path)
  with open("voice.ogg", "wb") as f: f.write(b.read())
  subprocess.run(["ffmpeg", "-y", "-i", "voice.ogg", "voice.wav"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  
  r = sr.Recognizer()
  with sr.AudioFile("voice.wav") as source:
   audio = r.record(source)
  text = await asyncio.to_thread(lambda: r.recognize_google(audio, language="ru-RU"))
  await msg.edit_text(f"🎤 Вы сказали: *{text}*", parse_mode="Markdown")
  await do_chat(m, text, reply_voice=True)
 except Exception as e:
  await msg.edit_text(f"❌ Не удалось распознать голос: {e}")

@dp.message(F.photo)
async def handle_photo(m:types.Message):
 if m.from_user.id not in ALLOWED_IDS: return
 msg = await m.answer("📸 Обрабатываю фото...")
 try:
  photo = m.photo[-1]
  file = await bot.get_file(photo.file_id)
  b = await bot.download_file(file.file_path)
  img_b64 = base64.b64encode(b.read()).decode()
  
  v_model = get_model("vision_model", "llava")
  pld = {
   "model": v_model,
   "messages": [{"role": "user", "content": m.caption or "Опиши это изображение детально.", "images": [img_b64]}],
   "stream": False
  }
  async with aiohttp.ClientSession() as osess:
   async with osess.post(f"{os.getenv('OLLAMA_HOST', 'http://ollama:11434')}/api/chat", json=pld, timeout=120) as r:
    if r.status == 200:
     res = await r.json()
     await msg.edit_text(res["message"]["content"], parse_mode="Markdown" if "```" in res["message"]["content"] else None)
    else:
     await msg.edit_text(f"❌ Ошибка Ollama (убедитесь что модель {v_model} поддерживает зрение).")
 except Exception as e:
  await msg.edit_text(f"❌ Ошибка зрения: {e}")

async def main():await dp.start_polling(bot)
if __name__=="__main__":asyncio.run(main())
