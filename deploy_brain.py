import paramiko

host = "88.210.29.61"
port = 34002
user = "Gemini_agent"
password = "B-FP3ITwBG"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=host, port=port, username=user, password=password)

sftp = ssh.open_sftp()
base_path = "/home/sokolovanv/remote_nas_llm/srv_llm_conf/LLM_SRV_FULL/android_agent"
sftp.put(r"c:\Projects\LLM_SRV_FULL\android_agent\brain.py", "/tmp/brain.py")
sftp.put(r"c:\Projects\LLM_SRV_FULL\android_agent\tasks.py", "/tmp/tasks.py")
sftp.close()

ssh.exec_command(f"echo '{password}' | sudo -S mv /tmp/brain.py {base_path}/brain.py")
ssh.exec_command(f"echo '{password}' | sudo -S mv /tmp/tasks.py {base_path}/tasks.py")

# test running it
stdin, stdout, stderr = ssh.exec_command(f"python3 {base_path}/brain.py")
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

ssh.close()
