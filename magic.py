#!/usr/bin/env python3
"""
magic_restore.py

One-command orchestrator to try many deobfuscation/beautify passes on a JS file,
produce a best-effort restored file "restored.js", and optionally commit & push it.

Designed for GitHub Codespaces (Python coordinator + embedded Node helper scripts).

Usage:
  python3 magic_restore.py --source <url_or_local_path> --out restored.js [--workdir tmp_work] [--commit]

BUT NOW:
 - --source is OPTIONAL.  
 - If omitted, script automatically downloads:
   https://raw.githubusercontent.com/Hikita1337/Anal/refs/heads/main/2025-12-09_09-42-51-297323.js
"""

import argparse
import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
import urllib.request
import json

ROOT = Path.cwd()
TOOLS = ROOT / "tools"
WORK = ROOT / "magic_restore_work"
LOG_PREFIX = "[magic_restore]"

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
// run_beautify.js
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
  child.execSync(`npx prettier --parser babel --write "${out1}"`, {stdio:'inherit'});
  fs.copyFileSync(out1, out2);
} catch(e) {
  fs.copyFileSync(out1, out2);
}
console.log("Beautify outputs:", out1, out2);
""".lstrip())

    # deobf_string_array.js
    (TOOLS / "deobf_string_array.js").write_text(r"""
// deobf_string_array.js
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
// ast_rename.js
const fs = require('fs');
const path = require('path');
const recast = require('recast');
const { visit } = recast.types;
const [,, src, outdir] = process.argv;
if(!src || !outdir) throw "usage";
const code = fs.readFileSync(src,'utf8');
let ast = null;
try {
  ast = recast.parse(code, { parser: require("recast/parsers/babel") });
} catch(e) {
  console.error("Error parsing AST:", e);
  ast = recast.parse(code, { parser: require("recast/parsers/acorn") });
}
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
console.log("Top candidate literal names:", candidates.slice(0,40));
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
console.log("Mapping sample:", Object.entries(mapping).slice(0,40));
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
// run_puppeteer.js
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
        "name": "magic_restore_tools",
        "private": True,
        "dependencies": {
            "recast": "^0.23.5",
            "prettier": "^2.8.0",
            "js-beautify": "^1.14.0",
            "puppeteer": "^19.7.0"
        }
    }
    pkgfile = TOOLS / "package.json"
    if not pkgfile.exists():
        pkgfile.write_text(json.dumps(pkg, indent=2), encoding="utf8")
    try:
        run(["npm", "install", "--prefix", str(TOOLS)], cwd=TOOLS)
    except Exception as e:
        log("npm install failed or partial: " + str(e))
        log("Proceeding; some tools may be missing. If in Codespaces, ensure network access.")

def download_source(src_spec, dest):
    dest = Path(dest)
    if Path(src_spec).exists():
        log(f"Source is local path: {src_spec} -> {dest}")
        shutil.copy2(src_spec, dest)
        return
    log(f"Downloading source from URL: {src_spec}")
    try:
        with urllib.request.urlopen(src_spec) as resp:
            data = resp.read()
            dest.write_bytes(data)
            log(f"Downloaded {len(data)} bytes")
    except Exception as e:
        raise RuntimeError(f"Failed to download {src_spec}: {e}")

def try_passes(src_path, outdir):
    # ФУНКЦИЯ НЕ ТРОГАЛАСЬ — 1:1
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    basename = src_path.name

    orig_copy = outdir / (basename + ".orig.js")
    shutil.copy2(src_path, orig_copy)

    try:
        run(["node", str(TOOLS / "run_beautify.js"), str(orig_copy), str(outdir)])
    except Exception as e:
        log("Beautify pass failed: " + str(e))

    beaut1 = outdir / (basename + ".orig.js.beautified.js")
    found_beaut = None
    for p in outdir.glob(basename + "*.js"):
        if p.name.endswith(".beautified.js") or p.name.endswith(".prettier.js") or ".beautified" in p.name:
            found_beaut = p
            break
    if not found_beaut:
        found_beaut = orig_copy
    try:
        run(["node", str(TOOLS / "deobf_string_array.js"), str(found_beaut), str(outdir)])
    except Exception as e:
        log("String-array pass failed: " + str(e))

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

    ast_renamed = None
    for p in outdir.glob(basename + "*.ast_renamed.js"):
        ast_renamed = p
        break
    run_target = ast_renamed or candidate_for_ast or found_beaut
    try:
        run(["node", str(TOOLS / "run_puppeteer.js"), str(run_target), str(outdir)])
    except Exception as e:
        log("Puppeteer runtime pass failed: " + str(e))

    runtime_dump = None
    for p in outdir.glob(basename + "*.runtime_dump.json"):
        runtime_dump = p
        break

    final_candidates = []
    for p in outdir.glob("**/*"):
        if p.is_file() and p.name.endswith(".js"):
            final_candidates.append(p)

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

    return outdir, preferred

def post_process_and_write(preferred_path, out_path):
    try:
        run(["npx", "prettier", "--parser", "babel", "--write", str(preferred_path)])
    except Exception as e:
        log("Prettier formatting failed: " + str(e))
    shutil.copy2(preferred_path, out_path)
    log(f"Wrote final restored file: {out_path} ({out_path.stat().st_size} bytes)")

def git_commit_and_push(filepath, message="Add restored.js (magic_restore)"):
    try:
        run(["git", "add", str(filepath)], cwd=ROOT)
        run(["git", "commit", "-m", message], cwd=ROOT)
        run(["git", "push"], cwd=ROOT)
        log("Pushed commit to origin.")
    except Exception as e:
        log("Git commit/push failed: " + str(e))
        log("Check git status / remote permissions in Codespaces.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="URL or local path to JS file (optional — if omitted, auto-download).", required=False)
    parser.add_argument("--out", default="restored.js", help="Output filename")
    parser.add_argument("--workdir", default=str(WORK), help="Working directory")
    parser.add_argument("--commit", action="store_true", help="Commit & push result to repo")
    args = parser.parse_args()

    log("Starting magic restore pipeline")
    ensure_dirs()
    write_tools()
    prepare_node_env()

    # CHANGED HERE:
    if args.source:
        src_spec = args.source
    else:
        log("No --source provided. Using default repo file.")
        src_spec = DEFAULT_SOURCE_URL

    fname = Path(src_spec).name
    downloaded = Path(args.workdir) / fname
    try:
        download_source(src_spec, downloaded)
    except Exception as e:
        log("Failed to fetch source: " + str(e))
        sys.exit(2)

    try:
        outdir, preferred = try_passes(downloaded, args.workdir)
        if not preferred:
            log("No candidate produced. Exiting.")
            sys.exit(3)
        log("Preferred candidate: " + str(preferred))
        final_out = Path(args.out).resolve()
        post_process_and_write(preferred, final_out)
        if args.commit:
            git_commit_and_push(final_out, message=f"restored.js (magic_restore) from {fname}")
        log("Done.")
    except Exception as e:
        log("Pipeline failed: " + str(e))
        sys.exit(4)

if __name__ == "__main__":
    main()