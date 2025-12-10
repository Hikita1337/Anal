import os
import requests
import subprocess
import shutil

# -----------------------------
# Настройки
# -----------------------------
GITHUB_TOKEN = "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"  # токен с правами gist
REPO_URL = "https://github.com/Hikita1337/Anal.git"  # URL репозитория
LOCAL_REPO_DIR = "AnalRepo"  # временная папка для клона
FILE_PATH_IN_REPO = "History/timeline1.txt"  # путь к файлу внутри репозитория
GIST_DESCRIPTION = "Полный timeline1.txt для анализа API"
GIST_PUBLIC = True  # True = публичный Gist, False = приватный

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
