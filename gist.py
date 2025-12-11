import os
import requests
import subprocess
import shutil
import gdown  # pip install gdown

# -----------------------------
# Настройки
# -----------------------------
TOKEN_FILE_URL = "https://drive.google.com/uc?id=1tuUxUWEfumOsUdJEk5q48SW5xlLXc187&export=download"
LOCAL_TOKEN_FILE = "github_token.txt"
REPO_URL = "https://github.com/Hikita1337/Anal.git"  # URL репозитория
LOCAL_REPO_DIR = "AnalRepo"  # временная папка для клона
FILE_PATH_IN_REPO = "restored.js"  # путь к файлу внутри репозитория
GIST_DESCRIPTION = "Полный restored.js для анализа API"
GIST_PUBLIC = True  # True = публичный Gist, False = приватный

# -----------------------------
# Скачиваем токен
# -----------------------------
if not os.path.exists(LOCAL_TOKEN_FILE):
    gdown.download(TOKEN_FILE_URL, LOCAL_TOKEN_FILE, quiet=False)

with open(LOCAL_TOKEN_FILE, "r", encoding="utf-8") as f:
    GITHUB_TOKEN = f.read().strip()

# -----------------------------
# Клонируем репозиторий
# -----------------------------
if os.path.exists(LOCAL_REPO_DIR):
    shutil.rmtree(LOCAL_REPO_DIR)

subprocess.run(["git", "clone", REPO_URL, LOCAL_REPO_DIR], check=True)

# -----------------------------
# Чтение файла
# -----------------------------
full_path = os.path.join(LOCAL_REPO_DIR, FILE_PATH_IN_REPO)
with open(full_path, "r", encoding="utf-8") as f:
    content = f.read()

# -----------------------------
# Формирование запроса на Gist
# -----------------------------
payload = {
    "description": GIST_DESCRIPTION,
    "public": GIST_PUBLIC,
    "files": {
        os.path.basename(FILE_PATH_IN_REPO): {"content": content}
    }
}

headers = {
    "Authorization": f"token {GITHUB_TOKEN}"
}

# -----------------------------
# Отправка запроса
# -----------------------------
response = requests.post("https://api.github.com/gists", json=payload, headers=headers)

if response.status_code == 201:
    gist_url = response.json()["html_url"]
    print(f"Gist создан успешно: {gist_url}")
else:
    print(f"Ошибка {response.status_code}: {response.text}")

# -----------------------------
# Очистка локального клона
# -----------------------------
shutil.rmtree(LOCAL_REPO_DIR)