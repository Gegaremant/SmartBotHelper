import requests
import json
from tasks import phone_exec, click, speak

# Адрес локальной Ollama (через проброшенный порт)
OLLAMA_URL = "http://localhost:11434/api/generate"

def ask_brain(prompt):
    """Отправляет запрос в модель и получает ответ"""
    payload = {
        "model": "hermes3:latest", # или твоя модель
        "prompt": f"Ты — ассистент на телефоне. Отвечай коротко. Если нужно действие, пиши в формате ACTION:command. Твой запрос: {prompt}",
        "stream": False
    }
    response = requests.post(OLLAMA_URL, json=payload)
    data = response.json()
    if 'response' in data:
        return data['response']
    else:
        return f"Error from Ollama: {data}"

def process_action(text):
    """Парсинг ответа модели и выполнение"""
    if "ACTION:" in text:
        command = text.split("ACTION:")[1].strip()
        print(f"Brain wants to execute: {command}")
        # Здесь можно добавить защиту, чтобы LLM не вызвала опасные команды
        phone_exec(command) 
    else:
        # Если действий нет, просто говорим в телефон
        speak(text)

# Пример использования
if __name__ == "__main__":
    user_input = "Открой Telegram"
    ai_response = ask_brain(user_input)
    print(f"AI: {ai_response}")
    process_action(ai_response)
