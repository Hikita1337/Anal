import requests
import os
import subprocess
import math

# --------------------------------------
# НАСТРОЙКИ
# --------------------------------------
FILE_URL = "https://gist.githubusercontent.com/Hikita1337/9c4f2873fa373fa343fc02e84ab86dda/raw/f959ae8767bf4a55b361186d1ebec8be8e5c8584/timeline1.txt"

OUTPUT_DIR = "."  # сохраняем части в корень репозитория
PARTS = 3         # количество частей

# --------------------------------------
# СКАЧИВАНИЕ ФАЙЛА
# --------------------------------------
print("Downloading timeline1.txt ...")

response = requests.get(FILE_URL)
response.raise_for_status()

full_text = response.text
size = len(full_text)

print(f"File loaded. Size: {size} characters")

# --------------------------------------
# ДЕЛЕНИЕ НА ЧАСТИ
# --------------------------------------
part_size = math.ceil(size / PARTS)

parts = []
for i in range(PARTS):
    start = i * part_size
    end = start + part_size
    parts.append(full_text[start:end])

# --------------------------------------
# СОХРАНЕНИЕ ЧАСТЕЙ
# --------------------------------------
filenames = []
for i, content in enumerate(parts, start=1):
    filename = f"timeline1_part{i}.txt"
    fullpath = os.path.join(OUTPUT_DIR, filename)
    with open(fullpath, "w", encoding="utf-8") as f:
        f.write(content)
    filenames.append(filename)
    print(f"Saved: {filename} ({len(content)} chars)")

# --------------------------------------
# GIT ADD + COMMIT + PUSH
# --------------------------------------
print("Committing and pushing to GitHub...")

subprocess.run(["git", "add"] + filenames, check=True)
subprocess.run(["git", "commit", "-m", "Added split timeline1 parts"], check=True)
subprocess.run(["git", "push"], check=True)

print("Done! Files uploaded to your repository.")