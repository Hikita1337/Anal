import re
import requests
import json

GIST_RAW_URL = "https://gist.githubusercontent.com/Hikita1337/a170c7a734fe705335e7a9737138f1e0/raw/restored.js"
OUTPUT_FILE = "analysis_output_extended.json"

print("[1] Downloading restored.js from Gist...")

resp = requests.get(GIST_RAW_URL)
if resp.status_code != 200:
    raise Exception(f"Failed to download Gist: {resp.status_code}")

js = resp.text
print(f"[OK] File length: {len(js)} bytes")

# ------------------------------------------------------
# Extract all functions
# ------------------------------------------------------
print("[2] Extracting all functions...")

# Простая эвристика для function + arrow + var/const function
FUNC_REGEX = re.compile(
    r'(function\s+([\w$]+)?\s*\((.*?)\)\s*\{)|'         # function foo(a,b)
    r'(?:const\s+([\w$]+)\s*=\s*\((.*?)\)\s*=>\s*\{)|' # const foo = (a,b) => {
    r'(?:var\s+([\w$]+)\s*=\s*function\s*\((.*?)\))',  # var foo = function(a,b)
    re.DOTALL
)

def extract_function_bodies(js_code):
    funcs = []
    for m in FUNC_REGEX.finditer(js_code):
        name = m.group(2) or m.group(4) or m.group(6) or "<anonymous>"
        params = m.group(3) or m.group(5) or m.group(7) or ""
        # Найдем тело функции
        start = m.end()
        brace_count = 1
        i = start
        while i < len(js_code) and brace_count > 0:
            if js_code[i] == "{":
                brace_count += 1
            elif js_code[i] == "}":
                brace_count -= 1
            i += 1
        body = js_code[start:i-1].strip()
        funcs.append({"name": name, "params": params, "body": body})
    return funcs

functions = extract_function_bodies(js)
print(f"[OK] Found {len(functions)} functions.")

# ------------------------------------------------------
# Keyword categories
# ------------------------------------------------------
KEYWORDS = {
    "balance": ["balance", "wallet", "coin", "credit"],
    "profile": ["profile", "user", "avatar", "settings"],
    "chat": ["chat", "message", "msg", "socket"],
    "admin": ["admin", "mod", "staff", "ban", "role"],
    "crash": ["crash", "multiplier", "game", "bet"],
    "roulette": ["roulette", "spin", "wheel", "color"]
}

category_hits = {k: [] for k in KEYWORDS}

print("[3] Categorizing functions by keywords inside body...")

for func in functions:
    for cat, words in KEYWORDS.items():
        for w in words:
            if re.search(r'\b' + re.escape(w) + r'\b', func["body"], re.IGNORECASE):
                category_hits[cat].append(func)
                break

# ------------------------------------------------------
# API extraction
# ------------------------------------------------------
print("[4] Extracting API requests...")

API_PATTERNS = {
    "fetch": r'fetch\s*\((.*?)\)',
    "xhr": r'new\s+XMLHttpRequest\s*\(',
    "axios": r'axios\.(get|post|put|delete)\s*\((.*?)\)',
    "urls": r'https?://[^\s\'")]+'
}

api_results = {k: [] for k in API_PATTERNS}
api_results["fetch"] = re.findall(API_PATTERNS["fetch"], js, re.DOTALL)
api_results["axios"] = re.findall(API_PATTERNS["axios"], js, re.DOTALL)
api_results["xhr"] = re.findall(API_PATTERNS["xhr"], js)
api_results["urls"] = re.findall(API_PATTERNS["urls"], js)

# ------------------------------------------------------
# Save JSON
# ------------------------------------------------------
output = {
    "function_categories": category_hits,
    "api_requests": api_results,
    "total_functions": len(functions)
}

with open(OUTPUT_FILE, "w", encoding="utf8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

print(f"[FINAL] Analysis complete. Saved to {OUTPUT_FILE}")