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

# Define Docker Compose content for Guacamole
docker_compose_yml = """
services:
  guacd:
    image: guacamole/guacd:latest
    container_name: guacd
    restart: unless-stopped
    networks:
      - guacnetwork_net

  guacamole:
    image: guacamole/guacamole:latest
    container_name: guacamole
    restart: unless-stopped
    ports:
      - "36495:8080"
    environment:
      - GUACD_HOSTNAME=guacd
      - GUACD_PORT=4822
      - GUACAMOLE_HOME=/etc/guacamole
    volumes:
      - ./config/user-mapping.xml:/etc/guacamole/user-mapping.xml:ro
    depends_on:
      - guacd
    networks:
      - guacnetwork_net

networks:
  guacnetwork_net:
    driver: bridge
"""

# Define user-mapping.xml content
user_mapping_xml = """<user-mapping>
    <!-- 
      Логин для входа в веб-интерфейс Guacamole.
      ЗАМЕНИТЕ ПАРОЛЬ НА ВАШ РЕАЛЬНЫЙ ПАРОЛЬ ОТ СЕРВЕРА!
    -->
    <authorize username="sokolovanv" password="ParallelCrossing5%">
        
        <!-- Подключение к RDP серверу хоста (Debian) -->
        <connection name="Debian Server RDP">
            <protocol>rdp</protocol>
            <!-- IP of the host from within the container network. Since guacnetwork_net is bridge, host is reachable via the default gateway of the container -->
            <param name="hostname">172.17.0.1</param>
            <param name="port">3389</param>
            <!-- Автоматическая передача логина и пароля из веб-интерфейса в RDP -->
            <param name="username">${GUAC_USERNAME}</param>
            <param name="password">${GUAC_PASSWORD}</param>
            <param name="ignore-cert">true</param>
            <param name="security">any</param>
        </connection>

    </authorize>
</user-mapping>
"""

commands = [
    # 1. XRDP Fixes
    f"echo '{password}' | sudo -S sed -i 's/allowed_users=console/allowed_users=anybody/' /etc/X11/Xwrapper.config",
    f"echo '{password}' | sudo -S apt-get update",
    f"echo '{password}' | sudo -S DEBIAN_FRONTEND=noninteractive apt-get install -y tigervnc-standalone-server docker.io docker-compose-v2 iproute2",
    
    # Session resume policy
    # We change Policy=Default to Policy=U in sesman.ini so XRDP reconnects strictly based on username, ignoring resolution changes.
    f"echo '{password}' | sudo -S sed -i 's/Policy=Default/Policy=U/' /etc/xrdp/sesman.ini",
    f"echo '{password}' | sudo -S sed -i 's/Policy=UBC/Policy=U/' /etc/xrdp/sesman.ini",
    f"echo '{password}' | sudo -S sed -i 's/Policy=UBI/Policy=U/' /etc/xrdp/sesman.ini",
    f"echo '{password}' | sudo -S systemctl restart xrdp",
    
    # 2. Guacamole Installation
    f"echo '{password}' | sudo -S mkdir -p /opt/guacamole/config",
    # Write files locally then upload and move to avoid quoting issues
    "mkdir -p /home/Gemini_agent/guacamole_temp",
    "cat << 'EOF' > /home/Gemini_agent/guacamole_temp/docker-compose.yml\n" + docker_compose_yml + "EOF",
    "cat << 'EOF' > /home/Gemini_agent/guacamole_temp/user-mapping.xml\n" + user_mapping_xml + "EOF",
    f"echo '{password}' | sudo -S mv /home/Gemini_agent/guacamole_temp/docker-compose.yml /opt/guacamole/docker-compose.yml",
    f"echo '{password}' | sudo -S mv /home/Gemini_agent/guacamole_temp/user-mapping.xml /opt/guacamole/config/user-mapping.xml",
    f"echo '{password}' | sudo -S chown -R {user}:{user} /opt/guacamole",
    f"cd /opt/guacamole && echo '{password}' | sudo -S docker compose down && echo '{password}' | sudo -S docker compose up -d"
]

for cmd in commands:
    print(f"Running command...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    
    if out: print(f"STDOUT: {out}")
    if err and "Password:" not in err and "[sudo]" not in err: 
        print(f"STDERR: {err}")

ssh.close()
print("Remote deployment finished!")
