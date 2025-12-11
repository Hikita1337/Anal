#!/usr/bin/env python3
"""
restore_js.py

Автономный скрипт для восстановления минифицированного и частично обфусцированного JavaScript:
- скачивает исходный JS и зависимости,
- выполняет runtime-анализ через Puppeteer,
- восстанавливает имена функций и переменных через AST,
- раскрывает строковые массивы,
- форматирует код в читаемый вид,
- выводит прогресс работы.

Выходной файл: restored.js
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path.cwd()
TOOLS = ROOT / "tools"
WORK = ROOT / "restore_work"
LOG_PREFIX = "[restore_js]"

DEFAULT_SOURCE_URL = "https://raw.githubusercontent.com/Hikita1337/Anal/refs/heads/main/2025-12-09_09-42-51-297323.js"

def log(msg):
    print(f"{LOG_PREFIX} {msg}", flush=True)

def run(cmd, cwd=None, env=None, check=True):
    log("RUN: " + " ".join(cmd))
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in p.stdout:
        print(line.rstrip())
    p.wait()
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed (exit {p.returncode}): {' '.join(cmd)}")
    return p.returncode

def ensure_dirs():
    TOOLS.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)

def write_tools():
    # run_beautify.js
    (TOOLS / "run_beautify.js").write_text(r"""
const fs = require('fs');
const child = require('child_process');
const path = require('path');
const [,, src, outdir] = process.argv;
if(!src || !outdir) { console.error("Usage: node run_beautify.js src outdir"); process.exit(2); }
const srcContent = fs.readFileSync(src,'utf8');
const bname = path.basename(src);
const out1 = path.join(outdir, bname + ".beautified.js");
try {
  child.execSync(`npx --yes js-beautify "${src}" -o "${out1}" --indent-size 2`, {stdio:'inherit'});
} catch(e) {
  const naive = srcContent.replace(/;/g, ';\n').replace(/\{/g,'{\n').replace(/\}/g,'}\n');
  fs.writeFileSync(out1, naive, 'utf8');
}
const out2 = path.join(outdir, bname + ".prettier.js");
try {
  child.execSync(`npx --yes prettier --parser babel --write "${out1}"`, {stdio:'inherit'});
  fs.copyFileSync(out1, out2);
} catch(e) {
  fs.copyFileSync(out1, out2);
}
console.log("Beautify outputs:", out1, out2);
""".lstrip())

    # deobf_string_array.js
    (TOOLS / "deobf_string_array.js").write_text(r"""
const fs = require('fs');
const path = require('path');
const [,, src, outdir] = process.argv;
if(!src || !outdir) throw "usage";
const code = fs.readFileSync(src,'utf8');
const arrRegex = /var\s+(_0x[a-f0-9]+)\s*=\s*\[((?:\s*'[^']*'\s*,?|\s*"[^"]*"\s*,?)+)\]\s*;/i;
let m = code.match(arrRegex);
let outPath = path.join(outdir, path.basename(src) + ".dearr.js");
let out = code;
let replaced = 0;
if(m){
  const varName = m[1];
  const arrText = m[2];
  const items = Array.from(arrText.matchAll(/'([^']*)'|"([^"]*)"/g)).map(x=> x[1] || x[2]);
  const decoderRegex = new RegExp("(_0x[0-9a-f]+)\\s*=\\s*function\\([^)]*\\)\\s*\\{[\\s\\S]*?return\\s+"+varName+"\\s*\\[\\s*a\\s*-\\s*(0x[0-9a-f]+|\\d+)\\s*\\]", "i");
  const dec = code.match(decoderRegex);
  if(dec){
    const func = dec[1];
    const off = parseInt(dec[2], 0);
    const callRegex = new RegExp(func + "\\(\\s*(0x[0-9a-fA-F]+|\\d+)\\s*\\)", "g");
    out = out.replace(callRegex, (s, num) => {
      try{
        let idx = parseInt(num, 0) - off;
        if(idx >= 0 && idx < items.length) { replaced++; return JSON.stringify(items[idx]); }
      }catch(e){}
      return s;
    });
    out = out.replace(arrRegex, '');
    out = out.replace(decoderRegex, '');
  }
}
fs.writeFileSync(outPath, out, 'utf8');
console.log("De-arr output:", outPath, "replacements:", replaced);
""".lstrip())

    # ast_rename.js
    (TOOLS / "ast_rename.js").write_text(r"""
const fs = require('fs');
const path = require('path');
const recast = require('recast');
const { visit } = recast.types;
const [,, src, outdir] = process.argv;
if(!src || !outdir) throw "usage";
const code = fs.readFileSync(src,'utf8');
let ast = recast.parse(code, { parser: require("recast/parsers/babel") });
const cand = {};
visit(ast, {
  visitLiteral(path) {
    const v = path.node.value;
    if(typeof v === 'string' && /^[A-Za-z_$][A-Za-z0-9_$-]{2,50}$/.test(v)) {
      cand[v] = (cand[v]||0)+1;
    }
    this.traverse(path);
  },
  visitProperty(path) {
    const key = path.node.key;
    if(key && key.type === 'Identifier') {
      cand[key.name] = (cand[key.name]||0)+1;
    }
    this.traverse(path);
  },
  visitClassDeclaration(path) {
    if(path.node.id && path.node.id.name) cand[path.node.id.name] = (cand[path.node.id.name]||0)+2;
    this.traverse(path);
  }
});
const candidates = Object.entries(cand).sort((a,b)=>b[1]-a[1]).map(x=>x[0]).slice(0,500);
const shortIds = new Set();
visit(ast, {
  visitIdentifier(path) {
    const n = path.node.name;
    if(/^[a-zA-Z0-9]{1,4}$/.test(n) || /^[yn][0-9][a-z]e?$/.test(n) ) {
      shortIds.add(n);
    }
    this.traverse(path);
  }
});
const shortList = Array.from(shortIds);
const mapping = {};
for(let i=0;i<shortList.length && i<candidates.length;i++){
  mapping[shortList[i]] = candidates[i];
}
visit(ast, {
  visitIdentifier(path) {
    const n = path.node.name;
    if(mapping[n]) {
      path.node.name = mapping[n];
    }
    this.traverse(path);
  }
});
const out = recast.print(ast).code;
const outPath = path.join(outdir, path.basename(src) + ".ast_renamed.js");
fs.writeFileSync(outPath, out, 'utf8');
console.log("AST rename written:", outPath);
""".lstrip())

    # run_puppeteer.js
    (TOOLS / "run_puppeteer.js").write_text(r"""
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');
const [,, src, outdir] = process.argv;
if(!src || !outdir) throw "usage";
(async ()=>{
  const browser = await puppeteer.launch({args: ['--no-sandbox','--disable-setuid-sandbox']});
  const page = await browser.newPage();
  const tmp = path.join(outdir, "pupp_tmp");
  fs.mkdirSync(tmp, {recursive:true});
  fs.copyFileSync(src, path.join(tmp, "file.js"));
  const html = `<!doctype html><html><head></head><body>
    <script src="./file.js"></script>
  </body></html>`;
  fs.writeFileSync(path.join(tmp, "index.html"), html, 'utf8');
  await page.goto('file://' + path.join(tmp, "index.html"), {waitUntil:'load', timeout:0});
  await page.waitForTimeout(1200);
  const dump = await page.evaluate(()=>{
    const keys = Object.keys(window).filter(k=> typeof window[k] !== 'function' && k !== 'webkitStorageInfo' && k!=='webkitIndexedDB' && k!=='performance');
    const sample = {};
    for(const k of keys.slice(0,400)){
      try {
        const v = window[k];
        if(typeof v === 'string' && v.length>3) sample[k]=v;
        else if(Array.isArray(v) && v.length>0) sample[k]=v.slice(0,20);
      } catch(e){}
    }
    return {keys: keys.slice(0,200), sample};
  });
  const outPath = path.join(outdir, path.basename(src) + ".runtime_dump.json");
  fs.writeFileSync(outPath, JSON.stringify(dump, null, 2), 'utf8');
  console.log("Runtime dump saved:", outPath);
  await browser.close();
})();
""".lstrip())

def prepare_node_env():
    cwd = TOOLS
    pkg = {
        "name": "restore_js_tools",
        "private": True,
        "dependencies": {
            "recast": "^0.23.5",
            "prettier": "^2.8.0",
            "js-beautify": "^1.15.4",
            "puppeteer": "^19.11.1"
        }
    }
    pkgfile = TOOLS / "package.json"
    if not pkgfile.exists():
        pkgfile.write_text(json.dumps(pkg, indent=2), encoding="utf8")
    try:
        run(["npm", "install", "--prefix", str(TOOLS)], cwd=TOOLS)
    except Exception as e:
        log("npm install failed or partial: " + str(e))
        log("Продолжаем, возможны ошибки, если отсутствуют пакеты.")

def download_file(url, dest):
    dest = Path(dest)
    if Path(url).exists():
        log(f"Source is local path: {url}")
        shutil.copy2(url, dest)
        return
    log(f"Downloading {url}")
    try:
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
            dest.write_bytes(data)
            log(f"Downloaded {len(data)} bytes to {dest}")
    except Exception as e:
        raise RuntimeError(f"Failed to download {url}: {e}")

def extract_imports(js_file):
    """Находит динамические импорты / скрипты для загрузки других JS"""
    imports = set()
    code = js_file.read_text(encoding='utf8')
    # import "file.js" / import x from "file.js"
    for m in re.finditer(r'import\s+(?:[\w\{\},\s]*\s+from\s+)?[\'"]([^\'"]+\.js)[\'"]', code):
        imports.add(m.group(1))
    # require("file.js")
    for m in re.finditer(r'require\([\'"]([^\'"]+\.js)[\'"]\)', code):
        imports.add(m.group(1))
    # src="file.js" в строках (дополнительно)
    for m in re.finditer(r'src=[\'"]([^\'"]+\.js)[\'"]', code):
        imports.add(m.group(1))
    return list(imports)

def download_dependencies(js_file_path, base_url=None):
    """Скачивает все JS-файлы, которые подгружает исходный JS"""
    js_file_path = Path(js_file_path)
    deps = extract_imports(js_file_path)
    dep_paths = []
    for d in deps:
        dep_name = Path(d).name
        dep_dest = WORK / dep_name
        if base_url:
            dep_url = urljoin(base_url, d)
        else:
            dep_url = d  # локальный путь
        try:
            download_file(dep_url, dep_dest)
            dep_paths.append(dep_dest)
        except Exception as e:
            log(f"Не удалось скачать зависимость {dep_url}: {e}")
    return dep_paths

def try_passes(src_path, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    basename = src_path.name
    orig_copy = outdir / (basename + ".orig.js")
    shutil.copy2(src_path, orig_copy)

    total_steps = 5
    step = 1

    log(f"Step {step}/{total_steps}: Beautify")
    try:
        run(["node", str(TOOLS / "run_beautify.js"), str(orig_copy), str(outdir)])
    except Exception as e:
        log("Beautify failed: " + str(e))
    step +=1

    log(f"Step {step}/{total_steps}: Deobfuscate string arrays")
    beaut1 = outdir / (basename + ".orig.js.beautified.js")
    found_beaut = None
    for p in outdir.glob(basename + "*.js"):
        if p.name.endswith(".beautified.js") or p.name.endswith(".prettier.js"):
            found_beaut = p
            break
    if not found_beaut:
        found_beaut = orig_copy
    try:
        run(["node", str(TOOLS / "deobf_string_array.js"), str(found_beaut), str(outdir)])
    except Exception as e:
        log("String-array pass failed: " + str(e))
    step +=1

    log(f"Step {step}/{total_steps}: AST Rename")
    candidate_for_ast = None
    for p in outdir.glob(basename + "*.dearr.js"):
        candidate_for_ast = p
        break
    if not candidate_for_ast:
        candidate_for_ast = found_beaut
    try:
        run(["node", str(TOOLS / "ast_rename.js"), str(candidate_for_ast), str(outdir)])
    except Exception as e:
        log("AST rename pass failed: " + str(e))
    step +=1

    log(f"Step {step}/{total_steps}: Puppeteer runtime analysis")
    ast_renamed = None
    for p in outdir.glob(basename + "*.ast_renamed.js"):
        ast_renamed = p
        break
    run_target = ast_renamed or candidate_for_ast or found_beaut
    try:
        run(["node", str(TOOLS / "run_puppeteer.js"), str(run_target), str(outdir)])
    except Exception as e:
        log("Puppeteer pass failed: " + str(e))
    step +=1

    log(f"Step {step}/{total_steps}: Final Prettier formatting")
    final_candidates = [p for p in outdir.glob("**/*.js") if p.is_file()]
    preferred = None
    for suf in [".ast_renamed.js", ".dearr.js", ".prettier.js", ".beautified.js", ".orig.js"]:
        for p in final_candidates:
            if p.name.endswith(suf):
                preferred = p
                break
        if preferred:
            break
    if not preferred and final_candidates:
        preferred = max(final_candidates, key=lambda p: p.stat().st_size)
    step +=1

    return outdir, preferred

def post_process(preferred_path, out_path):
    try:
        run(["npx", "--yes", "prettier", "--parser", "babel", "--write", str(preferred_path)])
    except Exception as e:
        log("Prettier final formatting failed: " + str(e))
    shutil.copy2(preferred_path, out_path)
    log(f"Final restored file: {out_path} ({out_path.stat().st_size} bytes)")

def main():
    ensure_dirs()
    write_tools()
    prepare_node_env()

    src_url = DEFAULT_SOURCE_URL
    fname = Path(src_url).name
    downloaded = WORK / fname
    download_file(src_url, downloaded)

    log("Checking for dependent JS files...")
    download_dependencies(downloaded, base_url=src_url)

    log("Starting deobfuscation and AST pipeline...")
    outdir, preferred = try_passes(downloaded, WORK)
    if not preferred:
        log("No candidate produced. Exiting.")
        sys.exit(1)

    final_out = ROOT / "restored.js"
    post_process(preferred, final_out)

    log("Done. Restored JS available at restored.js")

if __name__ == "__main__":
    main()