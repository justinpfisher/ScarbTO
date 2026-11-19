/** Exact-source half of the voice barrier. Runs only in the existing trusted
 * test job, after its locked npm install. The publisher uses the output-only
 * check and can publish only after that same revision's trusted job succeeds.
 * No parser downloads or dependency installation are performed here.
 */
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {readFileSync, readdirSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
let parser;
function pinnedParser() {
  if(parser)return parser;
  try {
    const packagePath=require.resolve('playwright/package.json');
    const version=JSON.parse(readFileSync(packagePath,'utf8')).version;
    if(version!=='1.63.0')throw new Error('expected Playwright 1.63.0, found '+version);
    const bundle=require(resolve(dirname(packagePath),'lib/transform/babelBundle.js'));
    if(typeof bundle.babelParse!=='function' || typeof bundle.traverse!=='function')throw new Error('parser interface changed');
    // This is an internal, version-pinned interface: never silently fall back
    // to a phrase regex on a dependency upgrade.
    const probe=bundle.babelParse('const text="probe";', 'voice-probe.mjs',true);
    if(probe?.program?.body[0]?.declarations[0]?.init?.value!=='probe')throw new Error('parser contract changed');
    parser=bundle;return parser;
  } catch(error) {
    throw new Error('Voice source parser unavailable or changed; review the pinned parser adapter: '+error.message);
  }
}
function owner(path) {
  const names=[];
  for(let p=path.parentPath;p;p=p.parentPath) {
    if(p.isFunction()) {
      const name=p.node.id?.name || (p.parentPath?.isVariableDeclarator()?p.parentPath.node.id.name:null) || (p.parentPath?.isObjectProperty()?p.parentPath.node.key.name:null);
      if(name)names.unshift(name);
    }
  }
  return names.join('/') || '<module>';
}
function astHash(node){return createHash('sha256').update(JSON.stringify(canonical(node))).digest('hex');}
function memberName(node) {
  return node?.type==='MemberExpression' ? (node.computed?node.property.value:node.property.name) : node?.name;
}
function canonical(node) {
  if(Array.isArray(node))return node.map(canonical);
  if(!node || typeof node!=='object')return node;
  return Object.fromEntries(Object.entries(node).filter(([key])=>!['start','end','loc','extra','leadingComments','trailingComments','innerComments'].includes(key)).map(([key,value])=>[key,canonical(value)]));
}
const PUBLIC_PROPERTIES=new Set(['textContent','innerText','innerHTML','outerHTML','title','alt','ariaLabel','ariaDescription','placeholder','label','download','srcdoc','value']);
const PUBLIC_CALLS=new Set(['setAttribute','setAttributeNS','insertAdjacentHTML','insertAdjacentText','createTextNode','write','writeln','alert','confirm','prompt','drawText','fillText','strokeText','text','el','element','make','addText','addHeading','setStatus','setDineSafeStatus','status','section','paragraph','els','append','appendChild','replaceChildren','setProperties','download','downloadBlob']);
export function sourceInventory(filename,source) {
  const {babelParse,traverse}=pinnedParser();
  const ast=babelParse(source,filename,true),strings=[],sinks=[],producers=new Map();
  const reviewedFunctions=new Set();
  function producer(fn) {
    if(!fn || reviewedFunctions.has(fn.node))return;
    reviewedFunctions.add(fn.node);
    producers.set(fn.node,{owner:owner(fn),name:fn.node.id?.name || (fn.parentPath?.isVariableDeclarator()?fn.parentPath.node.id.name:null) || '<callback>',ast_sha256:astHash(fn.node)});
    fn.traverse({ReferencedIdentifier(ref){
      const binding=ref.scope.getBinding(ref.node.name);
      if(!binding)return;
      if(binding.path.isFunction())producer(binding.path);
      else if(binding.path.isVariableDeclarator() && binding.path.get('init').isFunction())producer(binding.path.get('init'));
    }});
  }
  function sink(path) {
    // Include local variable initializers used by a sink. This binds an
    // approved text node to its actual source, not an unrelated gateway import.
    let fn=path.getFunctionParent();
    if(fn) {while(fn.getFunctionParent())fn=fn.getFunctionParent();producer(fn);}
    const bindings=new Map(),seen=new Set();
    function visit(p) {
      p.traverse({ReferencedIdentifier(ref){
        const name=ref.node.name,binding=ref.scope.getBinding(name);
        if(!binding || seen.has(binding))return;
        seen.add(binding);
        if(binding.path.isFunction()){producer(binding.path);return;}
        if(!binding.path.isVariableDeclarator() || !binding.path.node.init)return;
        const init=binding.path.get('init');
        bindings.set(name,{initial:canonical(init.node),mutations:binding.constantViolations.map(change=>canonical(change.node))});
        if(init.isFunction())producer(init);
        visit(init);
        for(const change of binding.constantViolations)visit(change);
      }});
    }
    visit(path);
    sinks.push({owner:owner(path),kind:path.node.type,expression_sha256:astHash(path.node),bindings:Object.fromEntries([...bindings].sort(([a],[b])=>a.localeCompare(b)).map(([name,value])=>[name,astHash(value)]))});
  }
  traverse(ast,{
    StringLiteral(path){if(path.node.value)strings.push([owner(path),'literal',path.node.value]);},
    TemplateElement(path){if(path.node.value.raw)strings.push([owner(path),'template',path.node.value.raw]);},
    AssignmentExpression(path){if(PUBLIC_PROPERTIES.has(memberName(path.node.left)))sink(path);},
    CallExpression(path){if(PUBLIC_CALLS.has(memberName(path.node.callee)))sink(path);},
    NewExpression(path){if(['Blob','Error','TypeError','RangeError'].includes(memberName(path.node.callee)))sink(path);},
    ReturnStatement(path){if(/render|compose|copy|summary|label|title|description|heading|message|caption|footer|status|finding|voice|text|note/i.test(owner(path)))sink(path);}
  });
  return {strings,sinks,producers:[...producers.values()]};
}
export function inspectSource(filename,source,approved) {
  const actual=sourceInventory(filename,source);
  if(!approved || JSON.stringify(actual)!==JSON.stringify(approved))throw new Error('Unreviewed voice producer expression or authored copy: '+filename);
  return actual.strings.length+actual.sinks.length;
}
export function checkSourceGateway(root=ROOT) {
  const contract=JSON.parse(readFileSync(resolve(root,'scripts/scarb-reviewed-producers.json'),'utf8'));
  const paths=[...readdirSync(resolve(root,'docs')).filter(path=>/\.(mjs|js)$/.test(path) && !['scarb-copy-inputs.mjs','scarb-copy-manifest.mjs','scarb-event-inputs.mjs'].includes(path)).map(path=>'docs/'+path),...readdirSync(resolve(root,'scripts')).filter(path=>/^build_.*\.mjs$/.test(path)).map(path=>'scripts/'+path)].sort();
  if(JSON.stringify(paths)!==JSON.stringify(Object.keys(contract).sort()))throw new Error('Unregistered public runtime module');
  let count=0;
  for(const path of paths)count+=inspectSource(path,readFileSync(resolve(root,path),'utf8'),contract[path]);
  return count;
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {console.log('Scarb exact-source catalogue checked '+checkSourceGateway()+' literal/template and sink contracts.');}
  catch(error){console.error(error.message);process.exitCode=1;}
}
