const fs=require('fs');
const source=fs.readFileSync(process.argv[2],'utf8');
const start=source.indexOf('/* EXTENSION_MANAGER_INVENTORY_PHASE1_BROWSER_START */');
const endMarker='/* EXTENSION_MANAGER_INVENTORY_PHASE1_BROWSER_END */';
const end=source.indexOf(endMarker,start)+endMarker.length;
if(start<0||end<endMarker.length)throw new Error('browser block missing');
const block=source.slice(start,end);

const calls=[];
const toasts=[];
function element(){return {value:'',textContent:'',innerHTML:'',disabled:false,classList:{add(){},remove(){}},scrollIntoView(){},};}
const els={
 extInventoryList:element(),extInventorySearch:element(),extInventoryCategory:element(),
 extInventoryStatus:element(),extInventoryRequirement:element(),extInventorySummary:element(),
 extInventorySources:element(),extStatePreview:element(),extStateApproval:element(),input:element()
};
els.extInventoryCategory.value='all'; els.extInventoryStatus.value='all'; els.extInventoryRequirement.value='all';
function q(id){return els[id]||element()}
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function js(v){return String(v??'').replace(/\\/g,'\\\\').replace(/'/g,"\\'")}
function toast(v){toasts.push(String(v))}
function go(){}
async function loadExtensions(){calls.push({url:'legacy:loadExtensions'})}
let fetchQueue=[];
global.fetch=async(url,opts={})=>{
 calls.push({url,opts});
 const data=fetchQueue.length?fetchQueue.shift():{ok:true};
 return {ok:true,status:200,json:async()=>data};
};
eval(block);
const toggleStart=source.indexOf('async function toggleExtension(');
const toggleEnd=source.indexOf('async function validateExtensions()',toggleStart);
if(toggleStart<0||toggleEnd<0)throw new Error('legacy toggle function missing');
eval(source.slice(toggleStart,toggleEnd));

(async()=>{
 const inventory={
  ok:true,
  summary:{total:1,verified:1,installed:0,missing:0,needs_attention:0,required_problems:0,state_controls:1,state_overrides:0,categories:{'Optional Tool':1}},
  sources:{application_registry:{},fleet_registry:{},manifest_discovery:{},extension_state:{exists:false,overrides:0,mode:'manifest defaults'}},
  items:[{
   id:'fleet:database',name:'SQLite',status:'VERIFIED',category:'Optional Tool',required:false,
   version:'1.0',path:'Z:/tool/sqlite3.exe',source:'Fleet Registry',health:'Ready',verification_basis:'verified',
   actions:{open_folder:true,launch:true},state_control:{key:'database',eligible:true,manifest_default:true,override_present:false,override_enabled:null,effective_enabled:true,dependencies:[],dependents:[]}
  }]
 };
 fetchQueue.push(inventory);
 await loadExtensionInventory();
 if(!els.extInventoryList.innerHTML.includes('Preview Disable'))throw new Error('state button missing');
 if(!els.extInventoryList.innerHTML.includes('Why?'))throw new Error('why button missing');
 if(calls[0].url!=='/api/extensions/inventory'||(calls[0].opts.method||'GET')!=='GET')throw new Error('inventory not read-only GET');

 const preview={ok:true,target:'database',key:'database',name:'SQLite',action:'disable',proposal_time:'2026-07-15T22:00:00',current_effective:true,manifest_default:true,override_present:false,override_enabled:null,proposed_effective:false,dependencies:[],dependents:[],enabled_dependents:[],warnings:[],blockers:[],can_apply:true,state_file_effect:'create override file',diff:'--- before\n+++ after\n',preview_digest:'abc123',approval_phrase:'APPROVE EXTENSION STATE DISABLE DATABASE'};
 fetchQueue.push(preview);
 await previewExtensionState('fleet:database','disable');
 const previewCall=calls.find(x=>x.url==='/api/extensions/state/preview');
 if(!previewCall||previewCall.opts.method!=='POST')throw new Error('preview endpoint missing');
 const previewBody=JSON.parse(previewCall.opts.body);
 if(previewBody.target!=='fleet:database'||previewBody.action!=='disable')throw new Error('preview body wrong');
 if(!els.extStatePreview.innerHTML.includes('Exact State Diff'))throw new Error('diff not rendered');
 if(!els.extStatePreview.innerHTML.includes('APPROVE EXTENSION STATE DISABLE DATABASE'))throw new Error('approval phrase not rendered');

 els.extStateApproval.value=preview.approval_phrase;
 fetchQueue.push({ok:true,message:'VERIFIED',receipt_path:'receipt.json',backup_path:'backup',state_file:'state.json'});
 await applyExtensionStateChange({disabled:false});
 const applyCall=calls.find(x=>x.url==='/api/extensions/state/apply');
 if(!applyCall||applyCall.opts.method!=='POST')throw new Error('apply endpoint missing');
 const applyBody=JSON.parse(applyCall.opts.body);
 if(applyBody.preview_digest!=='abc123'||applyBody.proposal_time!==preview.proposal_time||applyBody.approval_phrase!==preview.approval_phrase)throw new Error('apply contract incomplete');
 if(calls.some(x=>x.url==='/api/extensions/toggle'))throw new Error('legacy direct toggle used');

 fetchQueue.push(preview);
 await toggleExtension('database',false);
 const lastPreviewCalls=calls.filter(x=>x.url==='/api/extensions/state/preview');
 if(lastPreviewCalls.length<2)throw new Error('legacy button not routed to safe preview');

 console.log(JSON.stringify({passed:true,inventory_get_read_only:true,preview_post:true,apply_digest_phrase_time:true,legacy_toggle_routed_to_preview:true,why_panel_present:true}));
})().catch(e=>{console.error(e.stack||String(e));process.exit(1)});
