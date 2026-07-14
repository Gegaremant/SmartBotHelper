FROM python:3.10-slim
RUN apt-get update && apt-get install -y git ffmpeg && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash || echo 'OpenHands fallback'
RUN pip install aiogram pexpect aiohttp aiohttp-socks aider-chat duckduckgo-search SpeechRecognition pydub edge-tts
WORKDIR /app
COPY bot.py .
CMD ["python", "bot.py"]
