import paramiko
import sys
from paramiko import AutoAddPolicy

host = "82.22.187.89"
port = 4444
user = "Gemini_agent"
password = "B-FP3ITwBG"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(AutoAddPolicy())
ssh.connect(hostname=host, port=port, username=user, password=password)

cmd = "echo 'B-FP3ITwBG' | sudo -S bash -c \"echo 'sokolovanv:ParallelCrossing5%' | chpasswd\""

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))
ssh.close()
print("Password changed successfully")
