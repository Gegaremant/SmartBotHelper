FROM python:3.10-slim
RUN apt-get update && apt-get install -y docker.io docker-compose curl rclone iputils-ping lm-sensors && rm -rf /var/lib/apt/lists/*
RUN pip install aiogram aiohttp aiohttp-socks apscheduler asyncssh
WORKDIR /app
COPY bot.py .
CMD ["python", "bot.py"]
