# 🤖 LLM Server Ecosystem (SmartBotHelper)

**[English](#english) | [Русский](#русский)**

---

<a name="english"></a>
## 🇬🇧 English

A comprehensive infrastructure for deploying a personal AI server with multimodal bots and web interfaces. The project is designed to work in restricted networks, utilizing a built-in VLESS/Xray client to proxy container traffic.

### ✨ Key Features

#### 1. Core
- **Ollama**: Local server for running heavy LLM models on GPUs.
- **VLESS Proxy**: The `vless-client` container ensures uncensored internet access for Ollama, OpenWebUI, and bots (via `http_proxy` and `https_proxy` forwarding).

#### 2. Web Interfaces
- **OpenWebUI** (port `36486`): An advanced ChatGPT-like interface for interacting with your local models.
- **VSCode Web IDE** (port `36490`): A full-fledged browser-based development environment with access to project files.
- **Apache Guacamole** (port `36495`, path `/guacamole/`): Access the server's graphical desktop (RDP/VNC) directly through a web browser.

#### 3. Telegram Superintelligence (`tg_coder_bot`)
- **Aider Integration**: Can write and modify code in your projects. Use the prefix `/code <task>` to execute.
- **Neural Voice 🗣️**: Automatically recognizes audio and responds with a realistic synthesized voice via **Edge-TTS** (configurable in the admin bot).
- **Vision 👁**: Analyzes sent photos using multimodal models (e.g., `qwen2.5-vl` or `llava`).
- **Web Search 🌍**: When triggered by keywords, it performs a stealth request to DuckDuckGo and answers using fresh internet data.

#### 4. Boss Administrator (`tg_admin_bot`)
A button-based Telegram admin interface:
- **Ollama Management**: Download new models, switch the main text and vision models, and generate isolated SSH proxy users.
- **Log Collection & Cleanup 📋**: A scheduled task (or on-demand button) collects all component logs into a text file, sends it to the admin, and clears them on the host to prevent storage overflow.
- **Uptime Monitoring 🚨**: Checks specified hosts/sites (HTTP, TCP) every 2 minutes and triggers an alarm if they go down.
- **System State 🖥️**: Detailed summary of RAM, Disk, CPU, detailed GPU stats (temperature, VRAM), network consumption (RX/TX), and **Docker Stats** for each container.
- **Remote Servers 🌐**: Built-in SSH client to add third-party nodes, view running Docker containers, and read their logs directly from Telegram.
- **Backup 💾**: Instant ZIP archive creation of all critical settings (`.env`, `docker-compose.yml`, bot DBs, VLESS configs) sent directly to the Telegram chat.
- **Access Control 👥**: Manage bot administrators directly from Telegram.

#### 5. Android Agent (Katya) 📱
- **Standalone Project**: Katya is developed in a separate repository. **[View Katya Repository](https://github.com/Gegaremant/Katya)**.
- **Voice Assistant**: Native Android application acting as a fully voice-controlled assistant.
- **Direct LLM Integration**: Connects directly to the local Ollama instance (using SSH tunnel or direct IP) avoiding cloud API limits.
- **Kotlin Multiplatform**: The UI is built using Kotlin Multiplatform and Compose.

### 🚀 Deployment

1. Prepare a Linux server (e.g., Ubuntu) with an NVIDIA GPU.
2. Run `chmod +x install_llm.sh && ./install_llm.sh` to install Docker and NVIDIA Container Toolkit.
3. Create a `.env` file with your tokens and passwords.
4. Run `docker compose up -d --build`.

---

<a name="русский"></a>
## 🇷🇺 Русский

Полноценная инфраструктура для развертывания персонального сервера с искусственным интеллектом, мультимодальными ботами и веб-интерфейсами. Проект рассчитан на работу в условиях блокировок, используя встроенный VLESS/Xray клиент для проксирования трафика контейнеров.

### ✨ Ключевые возможности

#### 1. Ядро (Основа)
- **Ollama**: Локальный сервер для запуска тяжелых LLM-моделей на GPU.
- **VLESS Proxy**: Контейнер `vless-client`, обеспечивающий доступ в интернет без цензуры для Ollama, OpenWebUI и ботов (через проброс `http_proxy` и `https_proxy`).

#### 2. Веб-интерфейсы
- **OpenWebUI** (порт `36486`): Продвинутый ChatGPT-подобный интерфейс для общения с вашими локальными моделями.
- **VSCode Web IDE** (порт `36490`): Полноценная среда разработки в браузере с доступом к файлам проекта.
- **Apache Guacamole** (порт `36495`, путь `/guacamole/`): Доступ к графическому рабочему столу сервера (RDP/VNC) прямо через веб-браузер.

#### 3. Telegram Суперинтеллект (`tg_coder_bot`)
- **Aider Интеграция**: Умеет писать и изменять код в ваших проектах. Для запуска используйте префикс `/code <задача>`.
- **Нейросетевой Голос 🗣️**: Автоматически распознает аудио, а также отвечает реалистичным синтезированным голосом через **Edge-TTS** (настраивается в админ-боте).
- **Зрение (Vision) 👁**: Анализирует присланные фотографии с помощью мультимодальных моделей (например, `qwen2.5-vl` или `llava`).
- **Веб-поиск 🌍**: При наличии ключевых слов делает скрытый запрос в DuckDuckGo и отвечает с учетом свежих данных из интернета.

#### 4. Босс-Администратор (`tg_admin_bot`)
Интерфейс администратора в Telegram на кнопках:
- **Управление Ollama**: Скачивание новых моделей, переключение основной текстовой модели и модели зрения, создание выделенных SSH proxy-пользователей.
- **Сбор и очистка логов 📋**: Настраиваемый планировщик раз в заданное время (или **моментально по кнопке**) собирает логи всех компонентов в текстовый файл, отправляет его администратору и полностью очищает на хосте.
- **Uptime-Мониторинг 🚨**: Раз в 2 минуты проверяет заданные хосты/сайты и бьет тревогу при их падении.
- **Состояние системы 🖥️**: Сводка о загрузке RAM, Диска, CPU, детальная статистика видеокарт (температура, VRAM), потребление сети и статистика **Docker Stats** каждого контейнера.
- **Удаленные сервера 🌐**: Встроенный SSH-клиент, позволяющий добавлять сторонние узлы и просматривать списки запущенных Docker-контейнеров на них прямо из Telegram.
- **Резервное копирование 💾**: Мгновенное создание ZIP-архива всех критических настроек (`.env`, `docker-compose.yml`, базы ботов, конфиги VLESS) с отправкой в Telegram-чат.
- **Управление доступом 👥**: Добавление и удаление администраторов для ботов.

#### 5. Мобильный Агент (Катя) 📱
- **Отдельный проект**: Катя разрабатывается в отдельном репозитории. **[Посмотреть репозиторий Katya](https://github.com/Gegaremant/Katya)**.
- **Голосовой Ассистент**: Нативное Android-приложение, выступающее в роли голосового помощника на телефоне.
- **Прямая интеграция с LLM**: Подключается напрямую к локальному серверу Ollama (через SSH туннель или IP-адрес) без облачных лимитов.
- **Kotlin Multiplatform**: Интерфейс приложения написан с использованием современных технологий KMP и Compose.

### 🚀 Развертывание

1. Подготовьте сервер с Linux (например, Ubuntu) и видеокартой NVIDIA.
2. Выполните скрипт установки Docker: `chmod +x install_llm.sh && ./install_llm.sh`
3. Создайте файл `.env` со своими токенами и паролями.
4. Выполните запуск: `docker compose up -d --build`
