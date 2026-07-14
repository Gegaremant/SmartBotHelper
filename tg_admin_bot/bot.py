import os, asyncio, aiohttp, json, datetime, subprocess, asyncssh
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

proxy_url = os.getenv("http_proxy") or os.getenv("HTTP_PROXY")
session = AiohttpSession(proxy=proxy_url) if proxy_url else None
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"), session=session)
dp = Dispatcher()

STATE_FILE = "/workspace/shared_state.json"
HOSTS_FILE = "/workspace/hosts.json"
ALLOWED_IDS = [int(x.strip()) for x in os.getenv("ALLOWED_TELEGRAM_ID", "0").split(",") if x.strip().isdigit()]
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

class Form(StatesGroup):
    waiting_for_model = State()
    waiting_for_host = State()
    waiting_for_log_hours = State()
    waiting_for_ssh_host = State()
    waiting_for_new_admin = State()

def get_state():
    try:
        with open(STATE_FILE, "r") as f: return json.load(f)
    except: return {"main_model": "qwen3.6:27b", "vision_model": "llava", "log_hours": 24}

def save_state(d):
    with open(STATE_FILE, "w") as f: json.dump(d, f)

def get_hosts():
    try:
        with open(HOSTS_FILE, "r") as f: return json.load(f)
    except: return []

def save_hosts(h):
    with open(HOSTS_FILE, "w") as f: json.dump(h, f)

def main_kb():
    b = ReplyKeyboardBuilder()
    b.button(text="🧠 Ollama")
    b.button(text="📋 Логи и Отчеты")
    b.button(text="🚨 Мониторинг")
    b.button(text="🌐 Удаленные сервера")
    b.button(text="🖥️ Система")
    b.button(text="🗣 Голос")
    b.button(text="💾 Резервная копия")
    b.button(text="👥 Админы")
    b.adjust(2)
    return b.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    if m.from_user.id not in ALLOWED_IDS: return
    await m.answer("🛠️ Босс-Администратор запущен.", reply_markup=main_kb())

# --- OLLAMA ---
@dp.message(F.text == "🧠 Ollama")
async def ollama_menu(m: types.Message):
    if m.from_user.id not in ALLOWED_IDS: return
    b = InlineKeyboardBuilder()
    b.button(text="⬇️ Скачать модель", callback_data="ollama_pull")
    b.button(text="🗑 Удалить модель", callback_data="ollama_rm_choose")
    b.button(text="🧹 Память (VRAM)", callback_data="ollama_vram_manage")
    b.button(text="⚙️ Настройки Ollama", callback_data="ollama_settings")
    b.button(text="🎯 Выбрать основную", callback_data="ollama_sel_main")
    b.button(text="👁 Выбрать Vision", callback_data="ollama_sel_vision")
    b.adjust(1)
    await m.answer("Управление Ollama:", reply_markup=b.as_markup())

@dp.callback_query(F.data == "ollama_pull")
async def cb_ollama_pull(cq: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_model)
    await cq.message.answer("Введите название модели для скачивания (например: llama3.2):")
    await cq.answer()

active_downloads = {}

@dp.message(Form.waiting_for_model)
async def process_pull(m: types.Message, state: FSMContext):
    model_name = m.text.strip()
    await state.clear()
    
    b = InlineKeyboardBuilder()
    b.button(text="📊 Смотреть прогресс", callback_data=f"pullprog_{model_name[:40]}")
    msg = await m.answer(f"⬇️ Модель {model_name} поставлена на закачку!", reply_markup=b.as_markup())
    
    asyncio.create_task(download_model(model_name, m.chat.id))

async def download_model(model_name, chat_id):
    active_downloads[model_name] = {"status": "starting", "pct": 0}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{OLLAMA_HOST}/api/pull", json={"name": model_name, "stream": True}, timeout=0) as r:
                if r.status != 200:
                    err_txt = await r.text()
                    raise Exception(f"HTTP {r.status}: {err_txt}")
                async for line in r.content:
                    if not line: continue
                    try:
                        data = json.loads(line)
                        if "error" in data:
                            raise Exception(data["error"])
                        status = data.get("status", "")
                        completed = data.get("completed", 0)
                        total = data.get("total", 1) # prevent div/0
                        if total > 0 and completed > 0:
                            pct = round(completed / total * 100, 1)
                        else:
                            pct = 0
                        active_downloads[model_name] = {"status": status, "pct": pct, "completed": completed, "total": total}
                    except json.JSONDecodeError: pass
        active_downloads[model_name] = {"status": "success", "pct": 100}
        await bot.send_message(chat_id, f"✅ Модель {model_name} успешно скачана!")
    except Exception as e:
        active_downloads[model_name] = {"status": f"error: {e}", "pct": 0}
        await bot.send_message(chat_id, f"❌ Ошибка скачивания {model_name}:\n{e}")

@dp.callback_query(F.data.startswith("pullprog_"))
async def cb_pullprog(cq: types.CallbackQuery):
    short_model = cq.data.split("_", 1)[1]
    info = None
    full_name = short_model
    for k, v in active_downloads.items():
        if k.startswith(short_model):
            info = v
            full_name = k
            break
            
    if not info:
        await cq.answer("Нет информации о скачивании (возможно завершено или была перезагрузка).", show_alert=True)
        return
    
    status = info["status"]
    pct = info["pct"]
    
    msg = f"📦 {full_name}\nСтатус: {status}\nПрогресс: {pct}%"
    if "total" in info and info["total"] > 1:
        mb_total = round(info["total"]/1024/1024, 1)
        mb_comp = round(info["completed"]/1024/1024, 1)
        msg += f" ({mb_comp} MB / {mb_total} MB)"
        
    await cq.answer(msg, show_alert=True)

async def get_ollama_models():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{OLLAMA_HOST}/api/tags") as r:
                data = await r.json()
                return [m["name"] for m in data.get("models", [])]
    except: return []

@dp.callback_query(F.data.startswith("ollama_sel_"))
async def cb_ollama_sel(cq: types.CallbackQuery):
    kind = cq.data.split("_")[2] # main or vision
    models = await get_ollama_models()
    b = InlineKeyboardBuilder()
    for m in models:
        text = m
        if any(x in m.lower() for x in ["vl", "vision", "llava", "pixtral"]):
            text += " 👁 (Vision)"
        else:
            text += " 📝 (Text)"
        b.button(text=text, callback_data=f"setmod_{kind}_{m[:40]}")
    b.adjust(1)
    await cq.message.answer("Выберите модель:", reply_markup=b.as_markup())
    await cq.answer()

@dp.callback_query(F.data.startswith("setmod_"))
async def cb_setmod(cq: types.CallbackQuery):
    _, kind, short_model = cq.data.split("_", 2)
    models = await get_ollama_models()
    model = next((x for x in models if x.startswith(short_model)), short_model)
    
    st = get_state()
    st[f"{kind}_model"] = model
    save_state(st)
    await cq.message.edit_text(f"✅ Модель для {kind} изменена на: {model}")
    await cq.answer()

# --- NEW OLLAMA FEATURES ---

@dp.callback_query(F.data == "ollama_rm_choose")
async def cb_ollama_rm_choose(cq: types.CallbackQuery):
    models = await get_ollama_models()
    if not models:
        await cq.answer("Нет скачанных моделей", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    for m in models:
        text = m
        if any(x in m.lower() for x in ["vl", "vision", "llava", "pixtral"]):
            text += " 👁 (Vision)"
        else:
            text += " 📝 (Text)"
        b.button(text=f"Удалить {text}", callback_data=f"ollama_rm_{m[:40]}")
    b.adjust(1)
    await cq.message.answer("Выберите модель для удаления:", reply_markup=b.as_markup())
    await cq.answer()

@dp.callback_query(F.data.startswith("ollama_rm_"))
async def cb_ollama_rm(cq: types.CallbackQuery):
    short_model = cq.data.split("_", 2)[2]
    models = await get_ollama_models()
    model = next((x for x in models if x.startswith(short_model)), short_model)
    
    await cq.answer("Удаляю...")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.delete(f"{OLLAMA_HOST}/api/delete", json={"name": model}) as r:
                if r.status == 200:
                    await cq.message.edit_text(f"✅ Модель {model} успешно удалена.")
                else:
                    await cq.message.edit_text(f"❌ Ошибка удаления: {await r.text()}")
    except Exception as e:
        await cq.message.edit_text(f"❌ Ошибка: {e}")

@dp.callback_query(F.data == "ollama_vram_manage")
async def cb_ollama_vram_manage(cq: types.CallbackQuery):
    await cq.answer("Опрашиваю Ollama...")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{OLLAMA_HOST}/api/ps") as r:
                data = await r.json()
                loaded = data.get("models", [])
                if not loaded:
                    await cq.message.answer("В видеопамяти сейчас нет загруженных моделей (или Ollama спит).")
                    return
                b = InlineKeyboardBuilder()
                b.button(text="🧹 Выгрузить ВСЕ", callback_data="ollama_unload_all")
                for m in loaded:
                    name = m["name"]
                    size = round(m.get("size", 0) / 1024**3, 1)
                    b.button(text=f"Выгрузить {name} ({size}GB)", callback_data=f"ollama_unload_{name[:40]}")
                b.adjust(1)
                await cq.message.answer("Модели загруженные в VRAM:", reply_markup=b.as_markup())
    except Exception as e:
        await cq.message.answer(f"❌ Ошибка опроса /api/ps: {e}")

@dp.callback_query(F.data == "ollama_unload_all")
async def cb_ollama_unload_all(cq: types.CallbackQuery):
    await cq.answer("Выгружаю все модели...")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{OLLAMA_HOST}/api/ps") as r:
                data = await r.json()
                loaded = data.get("models", [])
                for m in loaded:
                    await s.post(f"{OLLAMA_HOST}/api/generate", json={"model": m["name"], "keep_alive": 0})
        await cq.message.edit_text("✅ Все модели принудительно выгружены из VRAM.")
    except Exception as e:
        await cq.message.edit_text(f"❌ Ошибка: {e}")

@dp.callback_query(F.data.startswith("ollama_unload_"))
async def cb_ollama_unload(cq: types.CallbackQuery):
    if cq.data == "ollama_unload_all": return
    short_model = cq.data.split("_", 2)[2]
    
    # We don't have the full list easily available without an API call, but Ollama can unload by short name if it matches, 
    # Actually, API requires exact name. Let's fetch loaded models to find exact match.
    model = short_model
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{OLLAMA_HOST}/api/ps") as r:
                data = await r.json()
                loaded = data.get("models", [])
                full_m = next((x["name"] for x in loaded if x["name"].startswith(short_model)), None)
                if full_m: model = full_m
    except: pass
    
    await cq.answer("Выгружаю...")
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(f"{OLLAMA_HOST}/api/generate", json={"model": model, "keep_alive": 0})
        await cq.message.edit_text(f"✅ Модель {model} выгружена из памяти.")
    except Exception as e:
        await cq.message.edit_text(f"❌ Ошибка выгрузки: {e}")

@dp.callback_query(F.data == "ollama_settings")
async def cb_ollama_settings(cq: types.CallbackQuery):
    b = InlineKeyboardBuilder()
    b.button(text="GPU: Все (0,1)", callback_data="ollama_env_CUDA_VISIBLE_DEVICES_all")
    b.button(text="GPU: Только M40", callback_data="ollama_env_CUDA_VISIBLE_DEVICES_0")
    b.button(text="GPU: Только P40", callback_data="ollama_env_CUDA_VISIBLE_DEVICES_1")
    b.button(text="Keep-Alive: Безлимит (-1)", callback_data="ollama_env_OLLAMA_KEEP_ALIVE_-1")
    b.button(text="Keep-Alive: час", callback_data="ollama_env_OLLAMA_KEEP_ALIVE_60m")
    b.button(text="Keep-Alive: 5 мин (5m)", callback_data="ollama_env_OLLAMA_KEEP_ALIVE_5m")
    b.adjust(1)
    await cq.message.answer("⚙️ Настройки Ollama (.env):\nПосле применения контейнер будет перезапущен.", reply_markup=b.as_markup())
    await cq.answer()

@dp.callback_query(F.data.startswith("ollama_env_"))
async def cb_ollama_env(cq: types.CallbackQuery):
    data = cq.data[len("ollama_env_"):] # e.g. OLLAMA_KEEP_ALIVE_60m
    if "_" not in data: return
    key, val = data.rsplit("_", 1) # splits from the right: ["OLLAMA_KEEP_ALIVE", "60m"]
    
    await cq.answer("Применяю...", show_alert=False)
    msg = await cq.message.answer(f"⏳ Обновляю `.env` и перезапускаю Ollama ({key}={val}) ...", parse_mode="Markdown")
    
    env_path = "/app/project_root/.env"
    if not os.path.exists(env_path):
        await msg.edit_text("❌ Файл .env не найден в /app/project_root (убедитесь что примонтирован).")
        return
    
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                if val == "all" and key == "CUDA_VISIBLE_DEVICES":
                    continue # Remove completely so deploy logic works
                new_lines.append(f"{key}={val}\n")
                found = True
            else:
                new_lines.append(line)
                
        if not found and not (val == "all" and key == "CUDA_VISIBLE_DEVICES"):
            if new_lines and not new_lines[-1].endswith("\\n"):
                new_lines[-1] += "\\n"
            new_lines.append(f"{key}={val}\n")
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка записи .env (нет rw прав?): {e}")
        return
        
    try:
        proc = await asyncio.create_subprocess_shell(
            "docker-compose -f /app/project_root/docker-compose.yml up -d ollama", 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        if proc.returncode == 0:
            await msg.edit_text(f"✅ Успешно!\n`{key}={val}`\nКонтейнер Ollama перезапущен.", parse_mode="Markdown")
        else:
            await msg.edit_text(f"❌ Ошибка docker-compose:\n```text\n{err.decode('utf-8', errors='replace')}\n```", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка выполнения системной команды: {e}")

# --- LOGS ---
@dp.message(F.text == "📋 Логи и Отчеты")
async def logs_menu(m: types.Message):
    if m.from_user.id not in ALLOWED_IDS: return
    b = InlineKeyboardBuilder()
    for c in ["ollama", "tg-coder-bot", "openwebui"]:
        b.button(text=f"Смотреть {c}", callback_data=f"logshow_{c}")
    b.button(text="Настроить автовыгрузку", callback_data="log_setup")
    b.button(text="Отправить отчет сейчас", callback_data="send_report_now")
    b.adjust(1)
    await m.answer("Управление логами:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("logshow_"))
async def cb_logshow(cq: types.CallbackQuery):
    c = cq.data.split("_")[1]
    proc = await asyncio.create_subprocess_shell(f"docker logs --tail 50 {c}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await proc.communicate()
    text = out.decode('utf-8', errors='replace')[-3000:]
    await cq.message.answer(f"Логи {c}:\n```text\n{text}\n```", parse_mode="Markdown")
    await cq.answer()

@dp.callback_query(F.data == "send_report_now")
async def cb_send_report_now(cq: types.CallbackQuery):
    await cq.answer("Формирую отчет...", show_alert=False)
    await scheduled_logs()

@dp.callback_query(F.data == "log_setup")
async def cb_log_setup(cq: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_log_hours)
    await cq.message.answer("Введите интервал выгрузки логов в часах (например, 24):")
    await cq.answer()

@dp.message(Form.waiting_for_log_hours)
async def process_log_hours(m: types.Message, state: FSMContext):
    try:
        hrs = int(m.text)
        st = get_state()
        st["log_hours"] = hrs
        save_state(st)
        await m.answer(f"✅ Интервал установлен: каждые {hrs} часов (применится после перезапуска).")
    except:
        await m.answer("❌ Ошибка. Введите число.")
    await state.clear()

async def scheduled_logs():
    print(f"Выгрузка логов...")
    with open("server_logs.txt", "w", encoding="utf-8") as f:
        for c in ["ollama", "tg-coder-bot", "openwebui"]:
            proc = await asyncio.create_subprocess_shell(f"docker logs --tail 2000 {c}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            out, _ = await proc.communicate()
            f.write(f"\n\n{'='*20} {c} {'='*20}\n")
            f.write(out.decode('utf-8', errors='replace'))
    
    # Очистка логов на хосте через docker socket (запуск alpine)
    await asyncio.create_subprocess_shell('docker run --rm -v /var/lib/docker/containers:/var/lib/docker/containers alpine sh -c "truncate -s 0 /var/lib/docker/containers/*/*-json.log"')
    
    for admin_id in ALLOWED_IDS:
        try:
            await bot.send_document(admin_id, types.FSInputFile("server_logs.txt"), caption="Архив логов со всех контейнеров.")
        except: pass

# --- UPTIME ---
@dp.message(F.text == "🚨 Мониторинг")
async def mon_menu(m: types.Message):
    if m.from_user.id not in ALLOWED_IDS: return
    hosts = get_hosts()
    txt = "Отслеживаемые хосты:\n" + "\n".join(hosts) if hosts else "Нет хостов."
    b = InlineKeyboardBuilder()
    b.button(text="Добавить хост", callback_data="add_host")
    b.button(text="Очистить список", callback_data="clear_hosts")
    b.adjust(1)
    await m.answer(txt, reply_markup=b.as_markup())

@dp.callback_query(F.data == "add_host")
async def cb_add_host(cq: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_host)
    await cq.message.answer("Введите IP или URL для мониторинга (например, 8.8.8.8):")
    await cq.answer()

@dp.callback_query(F.data == "clear_hosts")
async def cb_clear_hosts(cq: types.CallbackQuery):
    save_hosts([])
    await cq.message.edit_text("✅ Список мониторинга очищен.")
    await cq.answer()

@dp.message(Form.waiting_for_host)
async def process_host(m: types.Message, state: FSMContext):
    hosts = get_hosts()
    hosts.append(m.text)
    save_hosts(hosts)
    await m.answer(f"✅ Хост {m.text} добавлен в мониторинг.")
    await state.clear()

host_status = {}
async def scheduled_ping():
    hosts = get_hosts()
    for h in hosts:
        is_up = False
        if h.startswith("http://") or h.startswith("https://"):
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(h, timeout=5) as r:
                        is_up = r.status < 500
            except:
                is_up = False
        else:
            is_up = False
            for port in [80, 443, 22]:
                try:
                    conn = asyncio.open_connection(h, port)
                    _, writer = await asyncio.wait_for(conn, timeout=2.0)
                    writer.close()
                    await writer.wait_closed()
                    is_up = True
                    break
                except Exception:
                    continue
        
        was_up = host_status.get(h, True)
        if is_up and not was_up:
            for admin_id in ALLOWED_IDS:
                try:
                    await bot.send_message(admin_id, f"🟢 Сервер {h} снова в сети!")
                except: pass
        elif not is_up and was_up:
            for admin_id in ALLOWED_IDS:
                try:
                    await bot.send_message(admin_id, f"🔴 Упал {h} !!!")
                except: pass
        
        host_status[h] = is_up

# --- SYSTEM STATS ---
@dp.message(F.text == "🖥️ Система")
async def system_stats(m: types.Message):
    if m.from_user.id not in ALLOWED_IDS: return
    await m.answer("⏳ Собираю информацию о системе...")
    
    stats = []
    
    # RAM
    proc = await asyncio.create_subprocess_shell("free -m | awk 'NR==2{printf \"Memory Usage: %s/%sMB (%.2f%%)\", $3,$2,$3*100/$2 }'", stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    stats.append(f"🧠 RAM: {out.decode().strip() or 'N/A'}")
    
    # Disk
    proc = await asyncio.create_subprocess_shell("df -h / | awk '$NF==\"/\"{printf \"Disk Usage: %d/%dGB (%s)\", $3,$2,$5}'", stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    stats.append(f"💾 Диск: {out.decode().strip() or 'N/A'}")
    
    # CPU
    proc = await asyncio.create_subprocess_shell("top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'", stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    stats.append(f"⚙️ CPU: {out.decode().strip() or 'N/A'}")
    
    # GPU
    proc = await asyncio.create_subprocess_shell("docker exec ollama nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits", stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    gpu_out = out.decode().strip()
    if gpu_out:
        gpu_stats = []
        for i, line in enumerate(gpu_out.split('\n')):
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 4:
                gpu_stats.append(f"GPU {i}: {parts[0]}% Load, {parts[1]}/{parts[2]} MB VRAM, {parts[3]}°C")
        if gpu_stats:
            stats.append("🎮 GPU:\n" + "\n".join(gpu_stats))
        else:
            stats.append("🎮 GPU: N/A")
    else:
        stats.append("🎮 GPU: Не найдена или недоступна")
        
    # Sensors (Motherboard, CPU, etc)
    proc = await asyncio.create_subprocess_shell("sensors", stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    sensors_out = out.decode().strip()
    if sensors_out:
        filtered = []
        for line in sensors_out.split('\n'):
            line = line.strip()
            if not line:
                filtered.append("")
                continue
            # Keep headers
            if ":" not in line or line.startswith("Adapter:"):
                filtered.append(line)
                continue
            # Keep active fans
            if line.startswith("fan"):
                part = line.split(":")[1].strip()
                if part.startswith("0 RPM"): continue
                filtered.append(line.split("(")[0].strip())
                continue
            # Keep valid temperatures
            if "°C" in line:
                if line.startswith("Core "): continue
                if "-125.0" in line or "+115.0" in line or "-61.5" in line or "+0.0°C" in line: continue
                filtered.append(line.split("(")[0].strip())
                continue
                
        import re
        out_text = re.sub(r'\n{2,}', '\n\n', "\n".join(filtered)).strip()
        if out_text:
            stats.append(f"🌡 Температуры (Sensors):\n```text\n{out_text}\n```")
        
    # Docker
    proc = await asyncio.create_subprocess_shell("docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'", stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    docker_stats = out.decode().strip()
    if docker_stats:
        stats.append(f"🐳 Docker Stats:\n```text\n{docker_stats}\n```")
    
    # Network
    proc = await asyncio.create_subprocess_shell("cat /proc/net/dev | grep -E 'eth0|ens3|enp3s0'", stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    net_out = out.decode().strip()
    if net_out:
        stats.append(f"🌐 Сеть:\n```text\n{net_out}\n```")
        
    await m.answer("📊 **Состояние системы:**\n\n" + "\n\n".join(stats), parse_mode="Markdown")

# --- SSH REMOTE HOSTS ---
REMOTE_HOSTS_FILE = "/workspace/remote_hosts.json"

def get_remote_hosts():
    try:
        with open(REMOTE_HOSTS_FILE, "r") as f: return json.load(f)
    except: return []

def save_remote_hosts(h):
    with open(REMOTE_HOSTS_FILE, "w") as f: json.dump(h, f)

@dp.message(F.text == "🌐 Удаленные сервера")
async def ssh_menu(m: types.Message):
    if m.from_user.id not in ALLOWED_IDS: return
    hosts = get_remote_hosts()
    b = InlineKeyboardBuilder()
    for i, h in enumerate(hosts):
        name = h.get('name', h['ip'])
        b.button(text=f"Подключиться: {name}", callback_data=f"sshconn_{i}")
    b.button(text="➕ Добавить сервер", callback_data="add_ssh_host")
    b.adjust(1)
    await m.answer("Управление удаленными серверами и их логами:", reply_markup=b.as_markup())

@dp.callback_query(F.data == "add_ssh_host")
async def cb_add_ssh_host(cq: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_ssh_host)
    msg = ("Отправьте данные сервера одной строкой через пробел:\n\n"
           "Имя_сервера IP_сервера Логин Пароль\n\n"
           "Пример:\n"
           "MyServer 192.168.1.10 root mypassword123")
    await cq.message.answer(msg)
    await cq.answer()

@dp.message(Form.waiting_for_ssh_host)
async def process_ssh_host(m: types.Message, state: FSMContext):
    parts = m.text.strip().split()
    if len(parts) < 4:
        await m.answer("❌ Ошибка: нужно 4 значения (Имя, IP, Логин, Пароль) через пробел. Попробуйте снова.")
        return
    name, ip, user, pwd = parts[0], parts[1], parts[2], parts[3]
    hosts = get_remote_hosts()
    hosts.append({"name": name, "ip": ip, "user": user, "password": pwd})
    save_remote_hosts(hosts)
    await m.answer(f"✅ Сервер {name} ({ip}) сохранен!")
    await state.clear()

@dp.callback_query(F.data.startswith("sshconn_"))
async def cb_sshconn(cq: types.CallbackQuery):
    idx = int(cq.data.split("_")[1])
    hosts = get_remote_hosts()
    if idx >= len(hosts): return
    h = hosts[idx]
    
    msg = await cq.message.answer(f"⏳ Подключаюсь к {h['ip']}...")
    try:
        async with asyncssh.connect(h['ip'], username=h['user'], password=h['password'], known_hosts=None) as conn:
            res = await conn.run("docker ps --format '{{.Names}}'")
            if res.exit_status != 0:
                await msg.edit_text(f"❌ Ошибка Docker:\n{res.stderr}")
                return
            containers = res.stdout.strip().split("\n")
            containers = [c.strip() for c in containers if c.strip()]
            
            if not containers:
                await msg.edit_text("ℹ️ Нет запущенных Docker контейнеров.")
                return
                
            b = InlineKeyboardBuilder()
            for c in containers:
                b.button(text=f"Смотреть {c}", callback_data=f"sshlog_{idx}_{c}")
            b.adjust(1)
            await msg.edit_text(f"Контейнеры на {h['ip']}:", reply_markup=b.as_markup())
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка подключения: {e}")
    await cq.answer()

@dp.callback_query(F.data.startswith("sshlog_"))
async def cb_sshlog(cq: types.CallbackQuery):
    _, idx, container = cq.data.split("_", 2)
    idx = int(idx)
    hosts = get_remote_hosts()
    if idx >= len(hosts): return
    h = hosts[idx]
    
    await cq.answer("Получаю логи...")
    try:
        async with asyncssh.connect(h['ip'], username=h['user'], password=h['password'], known_hosts=None) as conn:
            res = await conn.run(f"docker logs --tail 50 {container}")
            # docker logs writes to stderr for some reason in many cases, so we combine both
            out = (res.stdout or "") + "\n" + (res.stderr or "")
            out = out[-3000:]
            await cq.message.answer(f"Логи {container} ({h['ip']}):\n```text\n{out}\n```", parse_mode="Markdown")
    except Exception as e:
        await cq.message.answer(f"❌ Ошибка получения логов: {e}")

# --- VOICE SETTINGS ---
@dp.message(F.text == "🗣 Голос")
async def voice_menu(m: types.Message):
    if m.from_user.id not in ALLOWED_IDS: return
    b = InlineKeyboardBuilder()
    b.button(text="👨 Дмитрий (Мужской)", callback_data="setvoice_ru-RU-DmitryNeural")
    b.button(text="👩 Светлана (Женский)", callback_data="setvoice_ru-RU-SvetlanaNeural")
    b.button(text="👩 Дария (Женский)", callback_data="setvoice_ru-RU-DariyaNeural")
    b.adjust(1)
    await m.answer("Выберите голос для ответов бота:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("setvoice_"))
async def cb_setvoice(cq: types.CallbackQuery):
    voice = cq.data.split("_")[1]
    st = get_state()
    st["voice_model"] = voice
    save_state(st)
    await cq.message.edit_text(f"✅ Голос изменен на: {voice}")
    await cq.answer()

# --- BACKUP ---
@dp.message(F.text == "💾 Резервная копия")
async def backup_menu(m: types.Message):
    if m.from_user.id not in ALLOWED_IDS: return
    msg = await m.answer("⏳ Создаю резервную копию настроек...")
    try:
        import zipfile
        zip_name = "backup.zip"
        with zipfile.ZipFile(zip_name, 'w') as zf:
            # Files in /workspace
            for f in ["shared_state.json", "hosts.json", "remote_hosts.json"]:
                path = f"/workspace/{f}"
                if os.path.exists(path):
                    zf.write(path, arcname=f)
            # Files in /app/project_root
            for f in [".env", "docker-compose.yml"]:
                path = f"/app/project_root/{f}"
                if os.path.exists(path):
                    zf.write(path, arcname=f)
            # xray_client configs
            if os.path.exists("/app/project_root/xray_client"):
                for root, dirs, files in os.walk("/app/project_root/xray_client"):
                    for file in files:
                        path = os.path.join(root, file)
                        arcname = os.path.relpath(path, "/app/project_root")
                        zf.write(path, arcname=arcname)
        
        for admin_id in ALLOWED_IDS:
            try:
                await bot.send_document(admin_id, types.FSInputFile(zip_name), caption="📦 Архив всех скриптов и стейтов LLM сервера.")
            except: pass
        await msg.delete()
        os.remove(zip_name)
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка бэкапа: {e}")


async def main():
    scheduler = AsyncIOScheduler()
    hrs = get_state().get("log_hours", 24)
    scheduler.add_job(scheduled_logs, "interval", hours=hrs)
    scheduler.add_job(scheduled_ping, "interval", minutes=2)
    scheduler.start()
    await dp.start_polling(bot)




import random
import string

@dp.message(F.text == "👥 Админы")
async def admins_menu(m: types.Message):
    if m.from_user.id not in ALLOWED_IDS: return
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить", callback_data="add_admin")
    b.button(text="➖ Удалить", callback_data="del_admin")
    b.button(text="🔑 Создать Proxy User", callback_data="add_proxy_user")
    b.adjust(2, 1)
    
    text = "👥 <b>Список администраторов:</b>\n"
    for aid in ALLOWED_IDS:
        try:
            chat = await bot.get_chat(aid)
            name = chat.first_name
            if chat.username: name += f" (@{chat.username})"
            text += f"- {name} (ID: {aid})\n"
        except:
            text += f"- (ID: {aid})\n"
    await m.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data == "add_admin")
async def cb_add_admin(cq: types.CallbackQuery, state: FSMContext):
    await cq.message.answer("Перешлите мне любое сообщение от пользователя, которого хотите сделать администратором.")
    await state.set_state(Form.waiting_for_new_admin)
    await cq.answer()

@dp.message(Form.waiting_for_new_admin)
async def process_new_admin(m: types.Message, state: FSMContext):
    new_id = None
    if m.forward_origin:
        if m.forward_origin.type == "user":
            new_id = m.forward_origin.sender_user.id
        else:
            await m.answer("У этого пользователя скрыт профиль при пересылке (privacy settings). Попросите его временно открыть профиль или пришлите мне его числовой ID текстом.")
            return
    elif m.text and m.text.strip().isdigit():
        new_id = int(m.text.strip())
    else:
        await m.answer("Вы не переслали сообщение от пользователя и не прислали числовой ID. Действие отменено.")
        await state.clear()
        return

    if new_id in ALLOWED_IDS:
        await m.answer("Этот пользователь уже администратор.")
    else:
        ALLOWED_IDS.append(new_id)
        await update_env_allowed_ids()
        await m.answer(f"✅ Пользователь с ID {new_id} успешно добавлен!\nПерезагружаю ботов для применения настроек...")
        await restart_bots_for_admins()
    await state.clear()

@dp.callback_query(F.data == "del_admin")
async def cb_del_admin_menu(cq: types.CallbackQuery):
    b = InlineKeyboardBuilder()
    for aid in ALLOWED_IDS:
        try:
            chat = await bot.get_chat(aid)
            name = chat.first_name
            if chat.username: name += f" (@{chat.username})"
        except:
            name = str(aid)
        
        # Don't let the first admin delete themselves
        root_admin = os.getenv("ALLOWED_TELEGRAM_ID", "").split(",")[0].strip()
        if str(aid) != root_admin:
            b.button(text=f"Удалить {name}", callback_data=f"deladm_{aid}")
            
    b.button(text="Отмена", callback_data="deladm_cancel")
    b.adjust(1)
    await cq.message.edit_reply_markup(reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("deladm_"))
async def cb_deladm_action(cq: types.CallbackQuery):
    action = cq.data.split("_")[1]
    if action == "cancel":
        await cq.message.delete()
        return
    
    aid = int(action)
    if aid in ALLOWED_IDS:
        ALLOWED_IDS.remove(aid)
        await update_env_allowed_ids()
        await cq.message.edit_text(f"✅ Администратор {aid} удален!\nПерезагружаю ботов для применения настроек...")
        await restart_bots_for_admins()
    else:
        await cq.answer("Уже удален")

async def update_env_allowed_ids():
    env_path = "/app/project_root/.env"
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(env_path, "w", encoding="utf-8") as f:
            for line in lines:
                if line.startswith("ALLOWED_TELEGRAM_ID="):
                    f.write(f"ALLOWED_TELEGRAM_ID={','.join(map(str, ALLOWED_IDS))}\n")
                else:
                    f.write(line)
    except Exception as e:
        print(f"Error saving .env: {e}")

async def restart_bots_for_admins():
    await asyncio.create_subprocess_shell("docker restart tg-coder-bot tg-admin-bot")

@dp.callback_query(F.data == "add_proxy_user")
async def cb_add_proxy_user(cq: types.CallbackQuery):
    await cq.message.answer("⏳ Создаю proxy-аккаунт на сервере, ожидайте...")
    await cq.answer()
    
    rnd = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    username = f"ollamaproxy_{rnd}"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    srv_ip = os.getenv("srv_ip")
    ssh_port = int(os.getenv("ssh_port", 22))
    ssh_login = os.getenv("ssh_login")
    ssh_password = os.getenv("ssh_password")
    
    if not srv_ip:
        await cq.message.answer("❌ Ошибка: В .env не указан srv_ip.")
        return
    
    try:
        async with asyncssh.connect(srv_ip, port=ssh_port, username=ssh_login, password=ssh_password, known_hosts=None) as conn:
            # Create user
            res = await conn.run(f"echo '{ssh_password}' | sudo -S useradd -M -s /bin/false {username}")
            if res.exit_status != 0:
                await cq.message.answer(f"❌ Ошибка создания пользователя: {res.stderr}")
                return
            
            # Set password
            res = await conn.run(f"echo '{ssh_password}' | sudo -S sh -c 'echo \"{username}:{password}\" | chpasswd'")
            if res.exit_status != 0:
                await cq.message.answer(f"❌ Ошибка смены пароля: {res.stderr}")
                return
                
            # Restrict SSH
            sshd_config = f"\nMatch User {username}\n    AllowTcpForwarding yes\n    PermitOpen 127.0.0.1:11434 localhost:11434\n    X11Forwarding no\n    PermitTTY no\n    ForceCommand /sbin/nologin\n"
            res = await conn.run(f"echo '{ssh_password}' | sudo -S sh -c \"echo -e '{sshd_config}' >> /etc/ssh/sshd_config\"")
            
            # Restart sshd
            await conn.run(f"echo '{ssh_password}' | sudo -S systemctl reload sshd")
            
        await cq.message.answer(f"✅ **Proxy-аккаунт успешно создан!**\n\nСервер: `{srv_ip}`\nПорт SSH: `{ssh_port}`\nЛогин: `{username}`\nПароль: `{password}`\n\nЭтот аккаунт может ТОЛЬКО пробрасывать порт 11434 (ssh -N -L 11434:localhost:11434).", parse_mode="Markdown")
    except Exception as e:
        await cq.message.answer(f"❌ Ошибка подключения по SSH: {e}")

if __name__=="__main__":asyncio.run(main())
