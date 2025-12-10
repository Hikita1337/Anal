import re
import os

# Параметры
INPUT_FILE = os.path.join("History", "timeline1.txt")  # путь к твоему файлу
OUTPUT_FILE = os.path.join("History", "cs2run_csgoih_urls.txt")  # файл для результата

INCLUDE_DOMAINS = ["cs2run.app", "csgoih.run"]
EXCLUDE_DOMAINS = ["yandex", "google", "top-fwz1.mail.ru"]

URL_REGEX = re.compile(r"https?://[^\s\"']+")

def extract_urls_from_line(line):
    return URL_REGEX.findall(line)

def filter_domains(urls, include_domains, exclude_domains):
    filtered = []
    for u in urls:
        if any(dom in u for dom in include_domains) and not any(ex in u for ex in exclude_domains):
            filtered.append(u)
    return filtered

def main():
    found = []
    with open(INPUT_FILE, encoding="utf-8", errors="ignore") as f:
        for line in f:
            urls = extract_urls_from_line(line)
            for u in filter_domains(urls, INCLUDE_DOMAINS, EXCLUDE_DOMAINS):
                found.append(u)

    # удаляем дубли, сохраняя порядок
    unique = []
    seen = set()
    for u in found:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    # сохраняем в файл
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for u in unique:
            out.write(u + "\n")

    print(f"[OK] Результат сохранён в {OUTPUT_FILE}, всего {len(unique)} URL")

if __name__ == "__main__":
    main()