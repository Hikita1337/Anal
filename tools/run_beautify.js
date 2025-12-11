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
