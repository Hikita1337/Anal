import re
import requests
import json

GIST_RAW_URL = "https://gist.githubusercontent.com/Hikita1337/a170c7a734fe705335e7a9737138f1e0/raw/restored.js"

print("[1] Downloading restored.js from Gist...")

resp = requests.get(GIST_RAW_URL)
if resp.status_code != 200:
    raise Exception(f"Failed to download Gist: {resp.status_code}")

js = resp.text
print(f"[OK] File length: {len(js)} bytes")

# ------------------------------------------------------
# Function extraction
# ------------------------------------------------------

print("[2] Extracting functions...")

# Match function declarations
FUNC_REGEX = re.compile(
    r'(?:function\s+([\w$]+)\s*\((.*?)\)\s*\{)|'          # function foo(a,b)
    r'(?:const\s+([\w$]+)\s*=\s*\((.*?)\)\s*=>\s*\{)|'     # const foo = (a,b) => {
    r'(?:var\s+([\w$]+)\s*=\s*function\s*\((.*?)\))',      # var foo = function(a,b)
    re.DOTALL
)

functions = []

for match in FUNC_REGEX.finditer(js):
    name = match.group(1) or match.group(3) or match.group(5)
    params = match.group(2) or match.group(4) or match.group(6)
    functions.append({"name": name, "params": params})

print(f"[OK] Found {len(functions)} functions total.")

# ------------------------------------------------------
# Keyword categories
# ------------------------------------------------------

KEYWORDS = {
    "balance": ["balance", "coin", "wallet", "credit"],
    "profile": ["profile", "user", "avatar", "settings"],
    "chat": ["chat", "message", "msg", "socket"],
    "admin": ["admin", "mod", "staff", "ban", "role"],
    "crash": ["crash", "multiplier", "game", "bet"],
    "roulette": ["roulette", "spin", "wheel", "color"]
}

category_hits = {k: [] for k in KEYWORDS}

print("[3] Categorizing functions...")

for func in functions:
    for cat, words in KEYWORDS.items():
        for w in words:
            pattern = r'\b' + re.escape(w) + r'\b'
            if re.search(pattern, func["name"], re.IGNORECASE):
                category_hits[cat].append(func)
                break

print("[OK] Categories processed.")

# ------------------------------------------------------
# API extraction
# ------------------------------------------------------

print("[4] Searching API requests...")

API_PATTERNS = {
    "fetch": r'fetch\s*\((.*?)\)',
    "xhr": r'new\s+XMLHttpRequest\s*\(',
    "axios": r'axios\.(get|post|put|delete)\s*\((.*?)\)',
    "urls": r'https?://[^\s\'"]+'
}

api_results = {k: [] for k in API_PATTERNS}

# fetch(...)
api_results["fetch"] = re.findall(API_PATTERNS["fetch"], js, re.DOTALL)

# axios.*
api_results["axios"] = re.findall(API_PATTERNS["axios"], js, re.DOTALL)

# xhr
api_results["xhr"] = re.findall(API_PATTERNS["xhr"], js)

# raw URLs
api_results["urls"] = re.findall(API_PATTERNS["urls"], js)

print("[OK] API extraction done.")

# ------------------------------------------------------
# Save result
# ------------------------------------------------------

output = {
    "function_categories": category_hits,
    "api_requests": api_results,
    "total_functions": len(functions),
}

with open("analysis_output.json", "w", encoding="utf8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

print("\n[FINAL] Analysis complete.")
print("Saved to analysis_output.json")