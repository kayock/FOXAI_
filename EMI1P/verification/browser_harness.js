
const requests=[];
const toasts=[];
const elements={};
function element(){
  return {
    value:'all',textContent:'',innerHTML:'',
    disabled:false,
    addEventListener(){},
    classList:{add(){},remove(){}}
  };
}
[
 'extInventoryList','extInventorySummary','extInventorySearch',
 'extInventoryCategory','extInventoryStatus','extInventoryRequirement',
 'extInventorySources','input'
].forEach(id=>elements[id]=element());
elements.extInventorySearch.value='';
function q(id){return elements[id]||null}
function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
function js(s){return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'")}
function toast(message){toasts.push(String(message))}
function go(id){requests.push({kind:'go',id})}

const inventory={
 ok:true,
 read_only:true,
 configuration_modified:false,
 state_file_created:false,
 message:'Read-only inventory',
 summary:{
   total:4,verified:1,installed:1,missing:1,needs_attention:1,
   required:2,optional:2,required_problems:1,
   categories:{'Application / Runtime':2,'Vision Projector':1,'Optional Tool':1},
   model_scan:{
     projectors_filtered_from_language_models:true,
     projectors_classified_separately:1
   }
 },
 sources:{
   application_registry:{path:'Z:\\FOXAI\\Config\\application_registry.json',exists:true,records:2},
   fleet_registry:{path:'Z:\\FOXAI\\Config\\fleet_registry.json',exists:true,records:1,mode:'passive'},
   manifest_discovery:{roots:['Z:\\FOXAI\\Departments','Z:\\FOXAI\\Extensions'],records:2},
   extension_state:{path:'Z:\\FOXAI\\Config\\extension_state.json',exists:false,mode:'manifest defaults; no state file created'}
 },
 items:[
   {id:'app:web',name:'WebUI',category:'Application / Runtime',source:'Application Registry',path:'Z:\\FOXAI\\core\\foxai_web.py',relative_path:'core/foxai_web.py',version:'Registry entry',required:true,status:'VERIFIED',health:'Path verified.',description:'',department:'Command',kind:'frontend',exists:true,size_bytes:100,modified:'2026-07-15',verification_basis:'path',actions:{open_folder:true,open_url:true},url:'http://127.0.0.1:8765/'},
   {id:'app:broken',name:'Broken',category:'Application / Runtime',source:'Application Registry',path:'Z:\\FOXAI\\missing.exe',relative_path:'missing.exe',version:'Registry entry',required:true,status:'NEEDS_ATTENTION',health:'Missing.',description:'',department:'Command',kind:'runtime',exists:false,size_bytes:null,verification_basis:'path',actions:{}},
   {id:'model:mmproj',name:'mmproj.gguf',category:'Vision Projector',source:'Model Filesystem',path:'Z:\\FOXAI\\Models\\Chat\\mmproj.gguf',relative_path:'Models/Chat/mmproj.gguf',version:'GGUF',required:false,status:'INSTALLED',health:'Installed.',description:'',department:'',kind:'vision_projector',exists:true,size_bytes:1000,verification_basis:'metadata',actions:{open_folder:true},excluded_from_language_model_selector:true},
   {id:'fleet:optional',name:'Optional Tool',category:'Optional Tool',source:'Fleet Registry',path:'',relative_path:'',version:'Auto',required:false,status:'MISSING',health:'Optional.',description:'',department:'Engineering',kind:'application',exists:false,size_bytes:null,verification_basis:'passive',actions:{}}
 ]
};

global.fetch=async (url,options={})=>{
  requests.push({kind:'fetch',url,method:options.method||'GET',body:options.body||null});
  if(url==='/api/extensions/inventory'){
    return {ok:true,status:200,json:async()=>inventory};
  }
  return {ok:true,status:200,json:async()=>({ok:true,message:'requested'})};
};
/* EXTENSION_MANAGER_INVENTORY_PHASE1_BROWSER_START */
let extensionInventoryData=null;
function inventorySize(value){
    let n=Number(value);
    if(!Number.isFinite(n)||n<0)return '—';
    if(n<1024)return `${n} B`;
    if(n<1024*1024)return `${(n/1024).toFixed(1)} KB`;
    if(n<1024*1024*1024)return `${(n/1024/1024).toFixed(2)} MB`;
    return `${(n/1024/1024/1024).toFixed(2)} GB`;
}
function inventoryStatusClass(status){
    status=String(status||'').toUpperCase();
    if(status==='VERIFIED')return 'verified';
    if(status==='INSTALLED')return 'installed';
    if(status==='MISSING')return 'missing';
    return 'attention';
}
function inventoryItemById(id){
    return (extensionInventoryData?.items||[]).find(item=>item.id===id)||null;
}
function renderExtensionInventory(){
    let data=extensionInventoryData;
    if(!data||!q('extInventoryList'))return;
    let search=String(q('extInventorySearch')?.value||'').trim().toLowerCase();
    let category=q('extInventoryCategory')?.value||'all';
    let status=q('extInventoryStatus')?.value||'all';
    let requirement=q('extInventoryRequirement')?.value||'all';
    let items=(data.items||[]).filter(item=>{
        if(category!=='all'&&item.category!==category)return false;
        if(status!=='all'&&item.status!==status)return false;
        if(requirement==='required'&&!item.required)return false;
        if(requirement==='optional'&&item.required)return false;
        if(search){
            let hay=[
                item.name,item.path,item.relative_path,item.department,item.source,
                item.category,item.kind,item.health,item.description,item.version
            ].join(' ').toLowerCase();
            if(!hay.includes(search))return false;
        }
        return true;
    });
    q('extInventoryList').innerHTML=items.map(item=>{
        let cls=inventoryStatusClass(item.status);
        let badges=[
            `<span class="inventorybadge ${cls}">${esc(item.status)}</span>`,
            `<span class=inventorybadge>${esc(item.category)}</span>`,
            `<span class=inventorybadge>${item.required?'REQUIRED':'OPTIONAL'}</span>`,
            item.department?`<span class=inventorybadge>${esc(item.department)}</span>`:'',
        ].join('');
        let details=[
            `Version: ${item.version||'Unspecified'}`,
            `Path: ${item.path||'(no path registered)'}`,
            `Size: ${inventorySize(item.size_bytes)}`,
            `Source: ${item.source||'Unknown'}`,
            item.manifest_path?`Manifest: ${item.manifest_path}`:'',
            item.verification_basis?`Verification: ${item.verification_basis}`:'',
            item.lifecycle?`Lifecycle: ${item.lifecycle}`:'',
            item.security_role?`Security role: ${item.security_role}`:'',
            item.modified?`Modified: ${item.modified}`:'',
        ].filter(Boolean).join('\n');
        let actions=[];
        if(item.actions?.open_folder)actions.push(`<button onclick="openExtensionInventoryFolder('${js(item.id)}')">Open Folder</button>`);
        if(item.actions?.open_url)actions.push(`<button onclick="openExtensionInventoryUrl('${js(item.id)}')">Open UI</button>`);
        if(item.actions?.launch)actions.push(`<button onclick="launchExtensionInventoryItem('${js(item.id)}')">${esc(item.actions.launch_label||'Launch')}</button>`);
        actions.push(`<button onclick="sendInventoryItemToMission('${js(item.id)}')">Send to Mission</button>`);
        return `<div class="inventorycard ${cls}"><h4>${esc(item.name)}</h4><div class=inventorybadges>${badges}</div><div class=inventorymeta>${esc(details)}</div>${item.description?`<div class=inventoryhealth>${esc(item.description)}</div>`:''}<div class=inventoryhealth><b>Health:</b> ${esc(item.health||'No health detail.')}</div><div class=inventoryactions>${actions.join('')}</div></div>`;
    }).join('')||'<div class=inventoryempty>No components match the current filters.</div>';
}
function renderExtensionInventorySummary(data){
    let summary=data.summary||{};
    q('extInventorySummary').innerHTML=`<div class=inventorygrid>
        <div class=inventorymetric><div class=label>Total Components</div><div class=value>${esc(summary.total||0)}</div></div>
        <div class=inventorymetric><div class=label>Verified</div><div class=value>${esc(summary.verified||0)}</div></div>
        <div class=inventorymetric><div class=label>Installed</div><div class=value>${esc(summary.installed||0)}</div></div>
        <div class=inventorymetric><div class=label>Missing</div><div class=value>${esc(summary.missing||0)}</div></div>
        <div class=inventorymetric><div class=label>Needs Attention</div><div class=value>${esc(summary.needs_attention||0)}</div></div>
        <div class=inventorymetric><div class=label>Required Problems</div><div class=value>${esc(summary.required_problems||0)}</div></div>
        <div class=inventorymetric><div class=label>Required</div><div class=value>${esc(summary.required||0)}</div></div>
        <div class=inventorymetric><div class=label>Optional</div><div class=value>${esc(summary.optional||0)}</div></div>
    </div>`;
    let categories=Object.keys(summary.categories||{}).sort();
    let selector=q('extInventoryCategory');
    let selected=selector?.value||'all';
    if(selector){
        selector.innerHTML='<option value=all>All categories</option>'+categories.map(name=>`<option value="${esc(name)}">${esc(name)} (${esc(summary.categories[name])})</option>`).join('');
        selector.value=categories.includes(selected)?selected:'all';
    }
    let sources=data.sources||{};
    let sourceCards=[
        ['Application Registry',sources.application_registry],
        ['Fleet Registry',sources.fleet_registry],
        ['Manifest Discovery',sources.manifest_discovery],
        ['State Override',sources.extension_state],
    ];
    q('extInventorySources').innerHTML=sourceCards.map(([name,value])=>{
        value=value||{};
        let detail=[
            name,
            value.path||'',
            value.roots?value.roots.join('\n'):'',
            `Present: ${value.exists===undefined?'n/a':value.exists}`,
            value.records!==undefined?`Records: ${value.records}`:'',
            value.mode?`Mode: ${value.mode}`:'',
            value.error?`Error: ${value.error}`:'',
        ].filter(Boolean).join('\n');
        return `<div class=inventorysource>${esc(detail)}</div>`;
    }).join('');
}
async function loadExtensionInventory(){
    if(!q('extInventoryList'))return;
    q('extInventoryList').textContent='Reading registries, manifests, local health, and model metadata...';
    try{
        let response=await fetch('/api/extensions/inventory',{cache:'no-store'});
        let data=await response.json();
        if(!response.ok||!data?.ok)throw new Error(data?.message||`HTTP ${response.status}`);
        extensionInventoryData=data;
        renderExtensionInventorySummary(data);
        renderExtensionInventory();
    }catch(error){
        q('extInventorySummary').textContent='Inventory failed: '+error;
        q('extInventoryList').textContent='No inventory data is available.';
    }
}
async function extensionInventoryAction(endpoint,id){
    let response=await fetch(endpoint,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({id})
    });
    let data=await response.json();
    toast(data?.message||'Inventory action completed.');
    if(!response.ok||!data?.ok)return data;
    setTimeout(loadExtensionInventory,600);
    return data;
}
function openExtensionInventoryFolder(id){
    return extensionInventoryAction('/api/extensions/inventory/open_folder',id);
}
function openExtensionInventoryUrl(id){
    return extensionInventoryAction('/api/extensions/inventory/open_url',id);
}
function launchExtensionInventoryItem(id){
    return extensionInventoryAction('/api/extensions/inventory/launch',id);
}
function sendInventoryItemToMission(id){
    let item=inventoryItemById(id);
    if(!item)return;
    go('mission');
    q('input').value=`Review this read-only Extension Manager inventory item.

Name: ${item.name}
Status: ${item.status}
Category: ${item.category}
Required: ${item.required}
Version: ${item.version}
Path: ${item.path||'(none)'}
Source: ${item.source}
Health: ${item.health}
Verification basis: ${item.verification_basis||'Not specified'}

Do not assume a missing optional component is an error. Recommend only preview-first actions.`;
    toast('Inventory item sent to Mission Console input.');
}
/* EXTENSION_MANAGER_INVENTORY_PHASE1_BROWSER_END */
(async()=>{
  await loadExtensionInventory();
  if(extensionInventoryData!==inventory)throw new Error('inventory not retained');
  const loadRequests=requests.filter(x=>x.kind==='fetch');
  if(loadRequests.length!==1||loadRequests[0].url!=='/api/extensions/inventory'||loadRequests[0].method!=='GET'){
    throw new Error('inventory load was not a single read-only GET');
  }
  if(elements.extInventoryList.innerHTML.includes('data:image/'))throw new Error('unexpected image payload');
  if(!elements.extInventoryList.innerHTML.includes('WebUI'))throw new Error('verified item not rendered');
  if(!elements.extInventoryList.innerHTML.includes('mmproj.gguf'))throw new Error('projector item not rendered separately');
  if(!elements.extInventorySources.innerHTML.includes('manifest defaults; no state file created'))throw new Error('missing state semantics not rendered');
  if(elements.extInventorySummary.innerHTML.includes('undefined'))throw new Error('summary contains undefined');

  elements.extInventoryStatus.value='NEEDS_ATTENTION';
  renderExtensionInventory();
  if(!elements.extInventoryList.innerHTML.includes('Broken'))throw new Error('attention filter omitted item');
  if(elements.extInventoryList.innerHTML.includes('WebUI'))throw new Error('attention filter included verified item');

  elements.extInventoryStatus.value='all';
  elements.extInventoryRequirement.value='optional';
  renderExtensionInventory();
  if(!elements.extInventoryList.innerHTML.includes('Optional Tool'))throw new Error('optional filter omitted item');
  if(elements.extInventoryList.innerHTML.includes('Broken'))throw new Error('optional filter included required item');

  await openExtensionInventoryFolder('app:web');
  await launchExtensionInventoryItem('fleet:optional');
  const posts=requests.filter(x=>x.kind==='fetch'&&x.method==='POST');
  if(posts.length!==2)throw new Error('operator actions did not use explicit POST');
  if(posts.some(x=>!x.body||!x.body.includes('"id"')))throw new Error('operator action missing item id');

  sendInventoryItemToMission('app:web');
  if(!elements.input.value.includes('read-only Extension Manager inventory item'))throw new Error('mission handoff missing');
  if(!requests.some(x=>x.kind==='go'&&x.id==='mission'))throw new Error('mission navigation missing');

  console.log(JSON.stringify({
    passed:true,
    load_is_read_only_get:true,
    state_file_absence_rendered:true,
    projector_separate:true,
    filters_passed:true,
    actions_operator_initiated_post:true,
    mission_handoff_passed:true
  }));
})().catch(error=>{
  console.error(error.stack||String(error));
  process.exit(1);
});
