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
