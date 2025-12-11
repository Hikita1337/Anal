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
