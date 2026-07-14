#!/bin/bash

# Скрипт для установки и обновления Antigravity IDE на Debian/Ubuntu
echo "==============================================="
echo "  Установка / Обновление Antigravity IDE..."
echo "==============================================="

# Обновляем / Устанавливаем IDE через официальный bash-скрипт
curl -fsSL https://opensnap.github.io/antigravity/install.sh | sudo bash -s -- --all

echo "==============================================="
echo "Готово! Antigravity IDE успешно обновлен."
echo "==============================================="
