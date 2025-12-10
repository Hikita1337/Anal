import os
import re
import json
import zipfile
import subprocess
import shutil
import gdown

ZIP_FILE = "http.zip"
BASE_DIR = "http"
OUTPUT_DIR = "History"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "timeline1.txt")

# ТВОЙ GOOGLE DRIVE ID
GDRIVE_ID = "10ClYKixNN2B-k0RFX_3IcNKDvzoEqCXI"

JUNK_EXT = {".css", ".html", ".jpg", ".jpeg", ".png", ".webp", ".bin"}

TIMESTAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-\d+)")


# ANSI цвета
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def download_zip():
    if os.path.exists(ZIP_FILE):
        print(YELLOW + f"[INFO] ZIP уже скачан → {ZIP_FILE}" + RESET)
        return

    print(GREEN + "[STEP] Скачивание ZIP с Google Drive…" + RESET)

    url = f"https://drive.google.com/uc?id={GDRIVE_ID}&export=download"
    gdown.download(url, ZIP_FILE, quiet=False)

    print(GREEN + "[OK] ZIP скачан успешно" + RESET)


def unzip_if_needed():
    if os.path.exists(BASE_DIR):
        print(YELLOW + f"[INFO] Папка {BASE_DIR} уже существует, распаковка не требуется" + RESET)
        return

    print(GREEN + "[STEP] Распаковка ZIP…" + RESET)
    with zipfile.ZipFile(ZIP_FILE, "r") as z:
        z.extractall(".")

    print(GREEN + "[OK] ZIP распакован" + RESET)


def cleanup_junk():
    print(GREEN + "[STEP] Удаление мусорных файлов…" + RESET)
    removed = 0
    
    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in JUNK_EXT:
                try:
                    os.remove(os.path.join(root, f))
                    removed += 1
                except:
                    pass
    
    print(GREEN + f"[OK] Удалено мусорных файлов: {removed}" + RESET)


def collect_files():
    items = []

    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            match = TIMESTAMP_RE.search(f)
            if not match:
                continue

            timestamp = match.group(1)
            path = os.path.join(root, f)

            if "requests" in root:
                ftype = "REQUEST"
            elif "responses" in root:
                ftype = "RESPONSE"
            elif "files" in root:
                ftype = "BODY"
            else:
                continue

            items.append((timestamp, ftype, path))

    return sorted(items, key=lambda x: x[0])


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except:
        return "(unreadable)"


def parse_json_body(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            t = f.read().strip()
            if t.startswith("{") or t.startswith("["):
                return t
            return "(binary or unknown)"
    except:
        return "(unreadable)"


def build_timeline():
    print(GREEN + "[STEP] Формирование истории…" + RESET)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    items = collect_files()

    blocks = {}

    for timestamp, ftype, path in items:
        content = read_file(path)
        url_match = re.search(r"URL:\s+(.+)", content)
        url = url_match.group(1).strip() if url_match else "UNKNOWN"

        if timestamp not in blocks:
            blocks[timestamp] = {"REQUEST": None, "RESPONSE": None, "BODY": None, "url": url}

        if ftype == "BODY" and path.endswith(".json"):
            blocks[timestamp]["BODY"] = parse_json_body(path)
        else:
            blocks[timestamp][ftype] = content

        blocks[timestamp]["url"] = url

    timeline = sorted(blocks.items(), key=lambda x: x[0])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for timestamp, data in timeline:
            out.write(f"===== {timestamp} | {data['url']} =====\n")

            if data["REQUEST"]:
                out.write("\n[REQUEST]\n" + data["REQUEST"] + "\n")

            if data["RESPONSE"]:
                out.write("\n[RESPONSE]\n" + data["RESPONSE"] + "\n")

            if data["BODY"]:
                out.write("\n[BODY]\n" + data["BODY"] + "\n\n")

    print(GREEN + f"[OK] История сформирована → {OUTPUT_FILE}" + RESET)


def git_push():
    print(GREEN + "[STEP] Публикация в GitHub обычным способом…" + RESET)

    subprocess.run(["git", "add", OUTPUT_FILE])
    subprocess.run(["git", "commit", "-m", "Add processed timeline"])
    subprocess.run(["git", "push"])

    print(GREEN + "[OK] Успешно отправлено в GitHub" + RESET)



if __name__ == "__main__":
    download_zip()
    unzip_if_needed()
    cleanup_junk()
    build_timeline()
    git_push()
    print(BLUE + "[DONE] Процесс полностью завершён" + RESET)