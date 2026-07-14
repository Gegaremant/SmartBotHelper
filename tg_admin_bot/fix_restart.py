import re
content = open(r'c:\Projects\LLM_SRV_FULL\tg_admin_bot\bot.py', encoding='utf-8').read()

pattern = re.compile(r'(async def restart_bots_for_admins\(\):.*?)(@dp\.callback_query\()', re.DOTALL)
match = pattern.search(content)

if match:
    old_func = match.group(1)
    
    new_func = '''async def restart_bots_for_admins():
    try:
        async with asyncssh.connect(srv_ip, port=ssh_port, username=ssh_login, password=ssh_password, known_hosts=None) as conn:
            await conn.run("docker restart tg-coder-bot tg-admin-bot")
    except Exception as e:
        print(f"Error restarting bots: {e}")

'''
    
    new_content = content.replace(old_func, new_func)
    open(r'c:\Projects\LLM_SRV_FULL\tg_admin_bot\bot.py', 'w', encoding='utf-8').write(new_content)
    print('Replaced restart_bots_for_admins successfully.')
else:
    print('Pattern not found. Trying another way.')
