import re

# Параметры
INPUT_FILE = "timeline1.txt"   # путь к твоему файлу с хронологией
DOMAINS = ["cs2run.app", "csgoih.run"]
URL_REGEX = re.compile(r"https?://[^\s\"']+")

def extract_urls_from_line(line):
    return URL_REGEX.findall(line)

def filter_domains(urls, domains):
    return [u for u in urls if any(dom in u for dom in domains)]

def main():
    found = []
    with open(INPUT_FILE, encoding="utf-8", errors="ignore") as f:
        for line in f:
            urls = extract_urls_from_line(line)
            for u in filter_domains(urls, DOMAINS):
                found.append(u)
    # удаляем дубли, сохраняем порядок появления
    unique = []
    seen = set()
    for u in found:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    # выводим
    for u in unique:
        print(u)

if __name__ == "__main__":
    main()
