FROM python:3.10-slim
RUN pip install aiogram aiohttp aiohttp-socks
WORKDIR /app
COPY bot.py .
CMD ["python", "bot.py"]
