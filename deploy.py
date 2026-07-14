import paramiko
import os
from paramiko import AutoAddPolicy

host = "88.210.29.61"
port = 34002
user = "Gemini_agent"
password = "B-FP3ITwBG"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(AutoAddPolicy())
ssh.connect(hostname=host, port=port, username=user, password=password)

sftp = ssh.open_sftp()

files_to_upload = [
    (r"c:\Projects\LLM_SRV_FULL\docker-compose.yml", "/home/Gemini_agent/LLM_SRV_FULL/docker-compose.yml"),
    (r"c:\Projects\LLM_SRV_FULL\tg_coder_bot\bot.py", "/home/Gemini_agent/LLM_SRV_FULL/tg_coder_bot/bot.py"),
    (r"c:\Projects\LLM_SRV_FULL\tg_admin_bot\bot.py", "/home/Gemini_agent/LLM_SRV_FULL/tg_admin_bot/bot.py"),
    (r"c:\Projects\LLM_SRV_FULL\guacamole_config\user-mapping.xml", "/home/Gemini_agent/LLM_SRV_FULL/guacamole_config/user-mapping.xml"),
    (r"c:\Projects\LLM_SRV_FULL\README.md", "/home/Gemini_agent/LLM_SRV_FULL/README.md"),
    (r"c:\Projects\LLM_SRV_FULL\xray_client\config.json", "/home/Gemini_agent/LLM_SRV_FULL/xray_client/config.json")
]

# Create guacamole_config dir if it doesn't exist
try:
    sftp.mkdir("/home/Gemini_agent/LLM_SRV_FULL/guacamole_config")
except Exception:
    pass
try:
    sftp.mkdir("/home/Gemini_agent/LLM_SRV_FULL/xray_client")
except Exception:
    pass

for local_path, remote_path in files_to_upload:
    print(f"Uploading {local_path} to {remote_path}...")
    sftp.put(local_path, remote_path)

sftp.close()

print("Files uploaded successfully. Rebuilding docker containers...")
stdin, stdout, stderr = ssh.exec_command(f"cd /home/Gemini_agent/LLM_SRV_FULL && echo '{password}' | sudo -S docker compose up -d --build")

# Wait for completion and print output
exit_status = stdout.channel.recv_exit_status()
print("STDOUT:")
print(stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:")
print(stderr.read().decode('utf-8', errors='ignore'))
print(f"Exit status: {exit_status}")

ssh.close()
