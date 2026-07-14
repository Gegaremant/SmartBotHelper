import re
content = open(r'c:\Projects\LLM_SRV_FULL\tg_admin_bot\bot.py', encoding='utf-8').read()

pattern = re.compile(r'(async def cb_ollama_env\(cq: types\.CallbackQuery\):.*?)(@dp\.callback_query\()', re.DOTALL)
match = pattern.search(content)

if match:
    old_func = match.group(1)
    
    new_func = '''async def cb_ollama_env(cq: types.CallbackQuery):
    data = cq.data[len("ollama_env_"):] # e.g. OLLAMA_KEEP_ALIVE_60m
    if "_" not in data: return
    key, val = data.rsplit("_", 1) # splits from the right: ["OLLAMA_KEEP_ALIVE", "60m"]
    
    await cq.answer("Применяю...", show_alert=False)
    msg = await cq.message.answer(f"🔄 Обновляю `.env` и рестартую Ollama ({key}={val}) ...", parse_mode="Markdown")
    
    env_path = "/app/project_root/.env"
    if not os.path.exists(env_path):
        await msg.edit_text("❌ Файл .env не найден в /app/project_root (проверьте бинды директорий).")
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
                new_lines.append(f"{key}={val}\\n")
                found = True
            else:
                new_lines.append(line)
                
        if not found and not (val == "all" and key == "CUDA_VISIBLE_DEVICES"):
            if new_lines and not new_lines[-1].endswith("\\n"):
                new_lines[-1] += "\\n"
            new_lines.append(f"{key}={val}\\n")
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка записи .env (нет rw прав?): {e}")
        return
        
    try:
        async with asyncssh.connect(srv_ip, port=ssh_port, username=ssh_login, password=ssh_password, known_hosts=None) as conn:
            res = await conn.run("cd /root/SmartBotHelper && docker compose up -d ollama")
            if res.exit_status == 0:
                await msg.edit_text(f"✅ Успешно!\\n`{key}={val}`\\nНастройки Ollama применены.", parse_mode="Markdown")
            else:
                await msg.edit_text(f"❌ Ошибка docker compose на хосте:\\n```text\\n{res.stderr}\\n```", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка перезапуска контейнера по SSH: {e}")

'''
    
    new_content = content.replace(old_func, new_func)
    open(r'c:\Projects\LLM_SRV_FULL\tg_admin_bot\bot.py', 'w', encoding='utf-8').write(new_content)
    print('Replaced cb_ollama_env successfully.')
else:
    print('Pattern not found. Trying another way.')
