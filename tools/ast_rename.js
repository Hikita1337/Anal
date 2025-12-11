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
