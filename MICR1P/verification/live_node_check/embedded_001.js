
let activeProject=null, curLib='', missionData=null, modelCatalog=[], selectedProfileId='', activeProfileId='', pendingMissionImage=null, activeMissionImage=null, chatStreamController=null; const chat=document.getElementById('chatLog');
/* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_START */
const MODEL_PROFILES=[
 {id:'fast_text',label:'⚡ Fast Text',model:'Qwen3.5-4B-Q4_K_M.gguf',best:'Quick questions, short summaries, simple instructions, and casual chat.',speed:'Fastest verified text profile',vision:'No',reasoning:'Off',status:'BENCHMARK SUPPORTED',note:'10.87 median tok/s; exact instruction and length checks passed. Runtime launches with reasoning off and budget 0.',recommended:true},
 {id:'balanced_text',label:'⚖️ Balanced Text',model:'Qwen3.5-9B-Q4_K_M.gguf',best:'Everyday writing, research discussion, longer answers, and general text work.',speed:'Moderate',vision:'No',reasoning:'Off',status:'BENCHMARK SUPPORTED',note:'5.75 median tok/s; exact instruction and length checks passed. Runtime launches with reasoning off and budget 0.',recommended:false},
 {id:'creative_text',label:'🎭 Creative Text',model:'PsyLLM-8B-Q5_K_M.gguf',best:'Brainstorming, story hooks, dialogue seeds, poetic fragments, and roleplay ideas.',speed:'Moderate',vision:'No',reasoning:'Off',status:'BRAINSTORMING SUPPORTED • LONG-FORM PENDING',note:'All eight creative responses completed without wrapper or reasoning leaks. Story hooks passed exact constraints; seven tasks missed requested length or structure, so strict long-form work remains pending.',recommended:false},
 {id:'fast_vision',label:'👁️ Fast Vision',model:'Qwen3VL-8B-Instruct-Q4_K_M.gguf',best:'Quick image understanding, screenshots, visible text, and general image questions.',speed:'Fast visual-language profile',vision:'Yes',reasoning:'Current engine behavior',status:'REAL IMAGE INPUT SUPPORTED • BENCHMARK PASSED',note:'Human-reviewed 5/5 real-image suite; 42.58s median and 6.56 tok/s. About 1.65× faster than Q8 with no observed quality loss on this suite.',recommended:false},
 {id:'quality_vision',label:'🔎 Quality Vision',model:'Qwen3VL-8B-Instruct-Q8_0.gguf',best:'Detailed image analysis, complex scenes, and careful visual reasoning.',speed:'Quality-first / slower',vision:'Yes',reasoning:'Current engine behavior',status:'REAL IMAGE INPUT SUPPORTED • BENCHMARK PASSED',note:'Human-reviewed 5/5 real-image suite; 70.38s median and 4.17 tok/s. Higher precision remains available, but this suite did not prove a quality advantage.',recommended:false}
];
/* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_END */
function q(id){return document.getElementById(id)}function toast(s){q('toast').textContent=s;q('toast').style.display='block';setTimeout(()=>q('toast').style.display='none',4200)}

const NAV_GROUPS={
  'Command':['dash','commandcenter','commanddetail','commandarchive','commandfreeze','mission','projects','memory'],
  'Kayock Writer':['kayockwriter','storyforge','storymanifest','projectgate','projectaction','projectdashboard','chapterplanner','chaptersavegate','chaptersaveaction','savedchapters','savedchapterhealth','chaptereditorpreview','chaptereditgate','chaptereditaction','chaptereditaudit','chapterdraftworkspace','draftsavegate','draftsaveaction','draftreader','draftversionhistory','draftcontinueworkspace','continuesavegate','continuesaveaction','draftrefresh','draftcompare','realprosegate','realprosesave','realproserefreshcompare','realproseeditorgate','realproseeditsave','realproseeditverify','chapterproseworkspace','chapterprosecontinuegate','chapterprosecontinuesave','chapterprosecontinueverify','novelforge','prompts'],
  'Knowledge & Creative':['academy','creative','library'],
  'Engineering & Repair':['repair','extensions','scanbridge','projectgen','buildverify','envverify','portable','modelcheck','repairactions','repairhistory','repairops','repairdetail','repairtickets','repairticketdetail','ticketbridge','repairsession','repairfreeze'],
  'Recovery & Backups':['backupvault','restorepreview','restoregate','restorestaging','stagingpackages','restorefinal','restoreaction','restoreaudit','rollbackpreview','rollbackaction','rollbackaudit','recoverytimeline'],
  'System':['logs','settings']
};
const NAV_DEFAULT_FAVORITES=['dash','mission','kayockwriter','library','repairops'];
let navCatalog=[];let commandSelection=0;
function navPageId(button){let m=(button.getAttribute('onclick')||'').match(/pg\('([^']+)'/);return m?m[1]:''}
function navFavorites(){try{return JSON.parse(localStorage.getItem('kayock.nav.favorites')||'null')||NAV_DEFAULT_FAVORITES.slice()}catch(e){return NAV_DEFAULT_FAVORITES.slice()}}
function saveNavFavorites(v){localStorage.setItem('kayock.nav.favorites',JSON.stringify(v.slice(0,20)))}
function navRecents(){try{return JSON.parse(localStorage.getItem('kayock.nav.recents')||'[]')}catch(e){return []}}
function recordRecent(id){if(!id)return;let v=navRecents().filter(x=>x!==id);v.unshift(id);localStorage.setItem('kayock.nav.recents',JSON.stringify(v.slice(0,8)));renderNavShortcuts()}
function toggleFavorite(id){let v=navFavorites();v=v.includes(id)?v.filter(x=>x!==id):[...v,id];saveNavFavorites(v);renderNavShortcuts();document.querySelectorAll(`.favtoggle[data-page="${id}"]`).forEach(x=>x.classList.toggle('on',v.includes(id)))}
function navItem(id){return navCatalog.find(x=>x.id===id)}
function shortcutButton(item){let b=document.createElement('button');b.className='nav navshortcut';b.dataset.page=item.id;b.textContent=item.label;b.onclick=()=>go(item.id);return b}
function renderShortcutList(target,ids){target.innerHTML='';let items=ids.map(navItem).filter(Boolean);if(!items.length){target.innerHTML='<div class=navempty>Nothing here yet.</div>';return}items.forEach(item=>target.appendChild(shortcutButton(item)))}
function renderNavShortcuts(){let f=q('navFavorites'),r=q('navRecents');if(f)renderShortcutList(f,navFavorites());if(r)renderShortcutList(r,navRecents())}
function focusNavGroup(id){let row=document.querySelector(`.nav-primary[data-page="${id}"]`);let details=row?.closest('details.navsection');if(!details)return;document.querySelectorAll('.navsection').forEach(x=>x.open=x===details)}
function syncNavState(id){focusNavGroup(id);document.querySelectorAll('.navshortcut').forEach(x=>x.classList.toggle('active',x.dataset.page===id))}
function setAllNavGroups(open){document.querySelectorAll('.navsection').forEach(x=>x.open=open)}
function openCommandPalette(){let p=q('commandPalette');if(!p)return;p.classList.add('open');let i=q('commandSearch');i.value='';renderCommandResults('');setTimeout(()=>i.focus(),0)}
function closeCommandPalette(){q('commandPalette')?.classList.remove('open')}
function commandMatches(term){let words=term.toLowerCase().split(/\s+/).filter(Boolean);return navCatalog.filter(x=>words.every(w=>(x.label+' '+x.group+' '+x.id).toLowerCase().includes(w))).slice(0,40)}
function renderCommandResults(term){let out=q('commandResults');if(!out)return;let items=commandMatches(term);commandSelection=Math.min(commandSelection,Math.max(0,items.length-1));out.innerHTML='';items.forEach((item,index)=>{let b=document.createElement('button');b.className='commandResult'+(index===commandSelection?' active':'');b.innerHTML=`<span>${esc(item.label)}</span><span class=commandMeta>${esc(item.group)}</span>`;b.onclick=()=>{go(item.id);closeCommandPalette()};out.appendChild(b)});if(!items.length)out.innerHTML='<div class=navempty>No matching department or page.</div>'}
function commandKey(event){let items=commandMatches(q('commandSearch').value);if(event.key==='ArrowDown'){event.preventDefault();commandSelection=Math.min(commandSelection+1,Math.max(0,items.length-1));renderCommandResults(q('commandSearch').value)}else if(event.key==='ArrowUp'){event.preventDefault();commandSelection=Math.max(0,commandSelection-1);renderCommandResults(q('commandSearch').value)}else if(event.key==='Enter'&&items.length){event.preventDefault();go(items[commandSelection].id);closeCommandPalette()}else if(event.key==='Escape'){closeCommandPalette()}}
function initDepartmentNav(){
  let aside=document.querySelector('aside');if(!aside||aside.classList.contains('nav-enhanced'))return;
  let buttons=[...aside.querySelectorAll(':scope > .nav')];
  navCatalog=buttons.map(button=>({id:navPageId(button),label:button.textContent.trim(),button,group:'Other'})).filter(x=>x.id);
  let groupFor={};Object.entries(NAV_GROUPS).forEach(([group,ids])=>ids.forEach(id=>groupFor[id]=group));navCatalog.forEach(x=>x.group=groupFor[x.id]||'Other');
  let shell=document.createElement('div');shell.id='departmentNav';
  shell.innerHTML=`<div class=navtools><button class=navsearch onclick="openCommandPalette()">🔎 Search <span class=small>Ctrl+K</span></button><button class=navcollapse onclick="setAllNavGroups(false)" title="Collapse all">−</button></div><details class=navshortcuts open><summary>Favorites</summary><div id=navFavorites></div></details><details class=navshortcuts><summary>Recents</summary><div id=navRecents></div></details>`;
  buttons[0]?.before(shell);
  Object.keys(NAV_GROUPS).concat(navCatalog.some(x=>x.group==='Other')?['Other']:[]).forEach(group=>{
    let items=navCatalog.filter(x=>x.group===group);if(!items.length)return;
    let details=document.createElement('details');details.className='navsection';details.open=group==='Command';details.dataset.group=group;details.ontoggle=()=>{if(!details.open)return;document.querySelectorAll('.navsection').forEach(x=>{if(x!==details)x.open=false})};
    let summary=document.createElement('summary');summary.textContent=group;details.appendChild(summary);let body=document.createElement('div');body.className='navitems';details.appendChild(body);
    items.forEach(item=>{let row=document.createElement('div');row.className='navrow';item.button.classList.add('nav-primary');item.button.dataset.page=item.id;let star=document.createElement('button');star.className='favtoggle';star.dataset.page=item.id;star.textContent='★';star.title='Toggle favorite';star.onclick=()=>toggleFavorite(item.id);row.append(item.button,star);body.appendChild(row)});shell.appendChild(details)
  });
  let palette=document.createElement('div');palette.id='commandPalette';palette.className='commandPalette';palette.innerHTML=`<div class=commandPanel><input id=commandSearch placeholder="Search departments and pages…" autocomplete=off><div id=commandResults class=commandResults></div></div>`;document.body.appendChild(palette);palette.addEventListener('click',e=>{if(e.target===palette)closeCommandPalette()});q('commandSearch').addEventListener('input',e=>{commandSelection=0;renderCommandResults(e.target.value)});q('commandSearch').addEventListener('keydown',commandKey);
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommandPalette()}else if(e.key==='Escape')closeCommandPalette()});
  aside.querySelectorAll(':scope > .navbreak').forEach(x=>x.remove());aside.classList.add('nav-enhanced');renderNavShortcuts();navFavorites().forEach(id=>document.querySelectorAll(`.favtoggle[data-page="${id}"]`).forEach(x=>x.classList.add('on')))
}
function pg(id,b){recordRecent(id);syncNavState(id);if(id==='dash')setTimeout(()=>loadRecoveryDashboard(),0); if(id==='commandcenter')setTimeout(()=>loadCommandCenter(false),0); if(id==='commanddetail')setTimeout(()=>loadCommandDetailList(),0); if(id==='commandarchive')setTimeout(()=>loadCommandArchive(false),0); if(id==='commandfreeze')setTimeout(()=>loadCommandFreeze(false),0); if(id==='kayockwriter')setTimeout(()=>loadKayockWriter(false),0); if(id==='storyforge')setTimeout(()=>loadStoryForge(false),0); if(id==='storymanifest')setTimeout(()=>loadStoryManifest(false),0); if(id==='projectgate')setTimeout(()=>loadProjectGate(false),0); if(id==='projectaction')setTimeout(()=>loadProjectAction(false,false),0); if(id==='projectdashboard')setTimeout(()=>loadProjectDashboard(false),0); if(id==='chapterplanner')setTimeout(()=>loadChapterPlanner(false),0); if(id==='chaptersavegate')setTimeout(()=>loadChapterSaveGate(false),0); if(id==='chaptersaveaction')setTimeout(()=>loadChapterSaveAction(false,false),0); if(id==='savedchapters')setTimeout(()=>loadSavedChapterDashboard(false),0); if(id==='savedchapterhealth')setTimeout(()=>loadSavedChapterHealthCard(false,'savedChapterHealth','savedChapterHealthBook'),0);document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));q(id).classList.add('active');document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));if(b)b.classList.add('active'); if(id==='projects')loadProjects(); if(id==='memory')loadMemory(); if(id==='library'){loadLib(curLib);loadIronIndexStatus(); if(q('libResults')&&!q('libResults').innerHTML.trim())searchLib()} if(id==='novelforge'){loadNovelForgeList();setTimeout(updateCodexDashboard,0)} if(id==='prompts')loadPrompts(); if(id==='extensions')loadExtensions(); if(id==='scanbridge'&&!q('scanPath').value)q('scanPath').value='Departments'; if(id==='projectgen')setTimeout(refreshProjectDocsStatus,0); if(id==='repairhistory')setTimeout(()=>loadRepairHistory(false),0); if(id==='repairops')setTimeout(()=>loadRepairOps(false),0); if(id==='repairdetail')setTimeout(()=>loadRepairDetailList(),0); if(id==='repairtickets')setTimeout(()=>loadRepairTickets(false),0); if(id==='repairticketdetail')setTimeout(()=>loadRepairTicketDetailList(),0); if(id==='ticketbridge')setTimeout(()=>loadTicketBridgeList(),0); if(id==='repairsession')setTimeout(()=>loadRepairSession(false),0); if(id==='repairfreeze')setTimeout(()=>loadRepairFreeze(false),0); if(id==='backupvault')setTimeout(()=>loadBackupVault(false),0); if(id==='restorepreview')setTimeout(()=>loadRestoreBackupList(),0); if(id==='restoregate')setTimeout(()=>loadRestoreGateList(),0); if(id==='restorestaging')setTimeout(()=>loadRestoreStagingList(),0); if(id==='stagingpackages')setTimeout(()=>loadStagingPackages(false),0); if(id==='restorefinal')setTimeout(()=>loadRestoreFinalList(),0); if(id==='restoreaction')setTimeout(()=>loadRestoreActionList(),0); if(id==='restoreaudit')setTimeout(()=>loadRestoreAudit(false),0); if(id==='rollbackpreview')setTimeout(()=>loadRollbackPreviewActions(),0); if(id==='rollbackaction')setTimeout(()=>loadRollbackActionList(),0); if(id==='rollbackaudit')setTimeout(()=>loadRollbackAudit(false),0); if(id==='recoverytimeline')setTimeout(()=>loadRecoveryTimeline(false),0); if(id==='realproseeditorgate')setTimeout(()=>loadRealProseEditorGate(false),0); if(id==='realproseeditsave')setTimeout(()=>loadRealProseEditSave(false),0); if(id==='chapterproseworkspace')setTimeout(()=>loadChapterProseWorkspace(false),0); if(id==='chapterprosecontinuegate')setTimeout(()=>loadChapterProseContinueGate(false),0); if(id==='chapterprosecontinuesave')setTimeout(()=>loadChapterProseContinueSave(false,false),0)}
function go(id){let b=[...document.querySelectorAll('.nav-primary')].find(x=>x.dataset.page===id)||[...document.querySelectorAll('.nav')].find(x=>x.dataset.page===id);pg(id,b)}function goMemory(){go('memory')}
async function api(u,opt){try{let r=await fetch(u,opt);let d=await r.json();toast(d.message||JSON.stringify(d));refresh();return d}catch(e){toast('Request failed: '+e)}}function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}function js(s){return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'")}
/* GUARDED_STREAMING_PHASE2_BROWSER_START */
function logline(c,w,m){chat.innerHTML+=`<span class=${c}>[${w}]</span> ${esc(m)}\n\n`;chat.scrollTop=chat.scrollHeight}
function beginStreamLine(c,w){
 let row=document.createElement('div');row.className='chatstreamline';
 let label=document.createElement('span');label.className=c;label.textContent=`[${w}]`;
 let body=document.createElement('span');body.className='chatstreambody';
 row.append(label,document.createTextNode(' '),body,document.createElement('br'),document.createElement('br'));
 chat.appendChild(row);chat.scrollTop=chat.scrollHeight;return {row,body};
}
function think(on){
 q('pulse').innerHTML=on?'<span class=pulse></span>':'';
 q('ms').textContent=on?'THINKING':'READY';
 let sendButton=q('sendChatButton'),cancelButton=q('cancelChatButton');
 if(sendButton)sendButton.disabled=Boolean(on);
 if(cancelButton)cancelButton.disabled=!on;
}
function cancelChat(){
 if(!chatStreamController)return;
 chatStreamController.abort();chatStreamController=null;
 toast('Generation canceled. No partial assistant answer will be archived.');
}
function explicitEngineerMessage(text){return /^\s*(?:\/engineer(?:\s+|$)|engineer\s*[:,]\s*\S)/i.test(String(text||''))}
/* MISSION_IMAGE_CONTINUITY_REPAIR_PHASE1_BROWSER_START */
const MISSION_IMAGE_MAX_BYTES=6*1024*1024;
function activeVisionProfile(){let profile=modelProfileById(activeProfileId);return Boolean(profile&&profile.vision==='Yes')}
function bytesLabel(value){let n=Number(value||0);if(n<1024)return `${n} B`;if(n<1024*1024)return `${(n/1024).toFixed(1)} KB`;return `${(n/1024/1024).toFixed(2)} MB`}
async function sha256Hex(buffer){let digest=await crypto.subtle.digest('SHA-256',buffer);return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('')}
function readFileDataUrl(file){return new Promise((resolve,reject)=>{let reader=new FileReader();reader.onload=()=>resolve(String(reader.result||''));reader.onerror=()=>reject(reader.error||new Error('Image read failed.'));reader.readAsDataURL(file)})}
function readImageDimensions(url){return new Promise((resolve,reject)=>{let image=new Image();image.onload=()=>resolve({width:image.naturalWidth,height:image.naturalHeight});image.onerror=()=>reject(new Error('Image dimensions could not be read.'));image.src=url})}
function missionImageMetadata(image){if(!image)return null;return {name:String(image.name||image.filename||'attached-image'),type:String(image.type||image.mime||''),size:Number(image.size||image.size_bytes||0),width:Number(image.width||0),height:Number(image.height||0),sha256:String(image.sha256||'')}}
function revokeMissionPreview(image){let url=String(image?.preview_url||'');if(url.startsWith('blob:')){try{URL.revokeObjectURL(url)}catch(e){}}}
function renderMissionImage(){let box=q('imagePreview');if(!box)return;let image=pendingMissionImage||activeMissionImage;if(!image){box.classList.remove('show');q('imagePreviewThumb').removeAttribute('src');q('imagePreviewMeta').textContent='';return}let state=pendingMissionImage?'PENDING IMAGE — will replace active context when sent':'ACTIVE IMAGE — retained for follow-up questions';let preview=String(image.preview_url||'');if(preview)q('imagePreviewThumb').src=preview;else q('imagePreviewThumb').removeAttribute('src');q('imagePreviewMeta').textContent=`${state}\n${image.name}\n${image.type} • ${image.width}×${image.height} • ${bytesLabel(image.size)}\nSHA-256 ${image.sha256}\nRaw image data is hidden and never added to the transcript.`;box.classList.add('show')}
function clearMissionImageLocal(){revokeMissionPreview(pendingMissionImage);if(activeMissionImage?.preview_url!==pendingMissionImage?.preview_url)revokeMissionPreview(activeMissionImage);pendingMissionImage=null;activeMissionImage=null;let picker=q('imageFile');if(picker)picker.value='';renderMissionImage()}
async function clearMissionImage(options={}){let remote=options.remote!==false,silent=Boolean(options.silent);if(remote){let d=await api('/api/chat/image/clear',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});if(!d?.ok){if(!silent)logline('bad','SYSTEM',d?.message||'Active image could not be cleared.');return false}}clearMissionImageLocal();if(!silent)toast('Active mission image removed.');return true}
async function refreshActiveMissionImage(){try{let d=await (await fetch('/api/chat/image/status')).json();if(!d?.ok)return false;let meta=d.active_image;if(meta?.attached){let local=(pendingMissionImage&&pendingMissionImage.sha256===meta.sha256)?pendingMissionImage:(activeMissionImage&&activeMissionImage.sha256===meta.sha256?activeMissionImage:null),nextPreview=local?.preview_url||'';if(activeMissionImage?.preview_url&&activeMissionImage.preview_url!==nextPreview)revokeMissionPreview(activeMissionImage);activeMissionImage={...missionImageMetadata({name:meta.filename,type:meta.mime,size:meta.size_bytes,width:meta.width,height:meta.height,sha256:meta.sha256}),preview_url:nextPreview};if(pendingMissionImage?.sha256===meta.sha256){pendingMissionImage.data_url='';pendingMissionImage=null}}else{revokeMissionPreview(activeMissionImage);activeMissionImage=null}renderMissionImage();return true}catch(e){return false}}
async function resetMissionConsole(){let d=await api('/api/chat/reset');if(d?.ok){clearMissionImageLocal();chat.innerHTML='Mission console reset.\n';logline('sys','SYSTEM',d.message||'Conversation reset.')}else logline('bad','SYSTEM',d?.message||'Reset failed.')}
async function handleMissionImageFiles(files){let file=files&&files[0];if(!file)return;let previewUrl='';try{if(!['image/png','image/jpeg','image/webp'].includes(file.type))throw new Error('Choose a PNG, JPEG, or WebP image.');if(file.size<1||file.size>MISSION_IMAGE_MAX_BYTES)throw new Error('Image must be larger than 0 bytes and no more than 6 MB.');previewUrl=URL.createObjectURL(file);let buffer=await file.arrayBuffer(),dataUrl=await readFileDataUrl(file),dimensions=await readImageDimensions(previewUrl);if(dimensions.width<1||dimensions.height<1||dimensions.width>8192||dimensions.height>8192)throw new Error('Image dimensions must be between 1 and 8192 pixels.');revokeMissionPreview(pendingMissionImage);pendingMissionImage={name:file.name,type:file.type,size:file.size,width:dimensions.width,height:dimensions.height,sha256:await sha256Hex(buffer),data_url:dataUrl,preview_url:previewUrl};renderMissionImage();toast(`Image ready: ${file.name}. It will replace the active image only when sent.`)}catch(error){if(previewUrl.startsWith('blob:'))URL.revokeObjectURL(previewUrl);pendingMissionImage=null;renderMissionImage();toast(String(error?.message||error));logline('bad','SYSTEM',`Image attachment rejected: ${error?.message||error}`)}}
function missionImagePayload(){if(!pendingMissionImage?.data_url)return null;let image=missionImageMetadata(pendingMissionImage);return {...image,data_url:pendingMissionImage.data_url}}
function missionUsesActiveImage(){return !pendingMissionImage&&Boolean(activeMissionImage)}
function logMissionImage(image,label='IMAGE ATTACHMENT'){if(!image)return;let meta=missionImageMetadata(image),row=document.createElement('div');row.className='chatimage';let thumb=document.createElement('img');let preview=String(image.preview_url||'');if(preview)thumb.src=preview;thumb.alt='Attached image preview';let detail=document.createElement('div');detail.className='chatimagemeta';detail.textContent=`${label}\n${meta.name}\n${meta.width}×${meta.height} • ${bytesLabel(meta.size)}\nSHA-256 ${meta.sha256}\n[raw image data hidden]`;row.append(thumb,detail);chat.appendChild(row);chat.scrollTop=chat.scrollHeight}
function setupMissionImageDrop(){let drop=q('imageDrop');if(!drop)return;['dragenter','dragover'].forEach(name=>drop.addEventListener(name,event=>{event.preventDefault();event.stopPropagation();drop.classList.add('drag')}));['dragleave','drop'].forEach(name=>drop.addEventListener(name,event=>{event.preventDefault();event.stopPropagation();drop.classList.remove('drag')}));drop.addEventListener('drop',event=>handleMissionImageFiles(event.dataTransfer?.files))}
async function requestNonStreamingChat(text,image=null,useActive=false){let response=await fetch('/api/chat/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,image,use_active_image:Boolean(useActive)})});let d=await response.json();if(d.answer)logline('fox',d.speaker||q('ap').textContent.toUpperCase(),d.answer);if(!d.ok)logline('bad','ERROR',d.message||'Mission turn failed verification.');return d}
async function requestGuardedStreamChat(text,image=null,useActive=false){
 if(!globalThis.ReadableStream||!globalThis.TextDecoder)return requestNonStreamingChat(text,image,useActive);
 chatStreamController=new AbortController();
 let response=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,image,use_active_image:Boolean(useActive)}),signal:chatStreamController.signal});
 let contentType=String(response.headers.get('content-type')||'');
 if(response.status===409&&contentType.includes('application/json')){let fallback=await response.json();chatStreamController=null;if(fallback.fallback==='/api/chat/send')return requestNonStreamingChat(text,image,useActive);throw new Error(fallback.message||'Guarded stream unavailable.')}
 if(!response.ok&&[404,405,501].includes(response.status)){chatStreamController=null;return requestNonStreamingChat(text,image,useActive)}
 if(!response.ok)throw new Error(`Guarded stream HTTP ${response.status}`);
 if(!response.body?.getReader){chatStreamController=null;return requestNonStreamingChat(text,image,useActive)}
 let reader=response.body.getReader(),decoder=new TextDecoder(),buffer='',streamLine=null,receivedChunk=false,finalEvent=null;
 function handleEvent(event){if(!event||typeof event!=='object')return;if(event.type==='start'&&!streamLine)streamLine=beginStreamLine('fox',event.speaker||q('ap').textContent.toUpperCase());if(event.type==='chunk'){if(!streamLine)streamLine=beginStreamLine('fox',event.speaker||q('ap').textContent.toUpperCase());streamLine.body.textContent+=String(event.text||'');receivedChunk=true;chat.scrollTop=chat.scrollHeight}if(event.type==='final'){if(!streamLine)streamLine=beginStreamLine('fox',event.speaker||q('ap').textContent.toUpperCase());streamLine.body.textContent=String(event.answer||'');finalEvent=event;chat.scrollTop=chat.scrollHeight}if(event.type==='error'){finalEvent=event;if(event.answer){if(!streamLine)streamLine=beginStreamLine('bad',event.speaker||'SYSTEM');streamLine.body.textContent=String(event.answer)}}}
 while(true){let part=await reader.read();buffer+=decoder.decode(part.value||new Uint8Array(),{stream:!part.done});let lines=buffer.split('\n');buffer=lines.pop()||'';for(let line of lines){line=line.trim();if(!line)continue;handleEvent(JSON.parse(line))}if(part.done)break}
 if(buffer.trim())handleEvent(JSON.parse(buffer.trim()));chatStreamController=null;if(!finalEvent)throw new Error('Guarded stream ended without a verified final event.');if(finalEvent.type==='error'||!finalEvent.ok)logline('bad','ERROR',finalEvent.message||'Mission turn failed verification.');return finalEvent;
}
async function send(){
 let text=q('input').value.trim(),image=missionImagePayload(),useActive=missionUsesActiveImage();if(!text&&!image&&!useActive)return;
 if((image||useActive)&&!activeVisionProfile()){let active=modelProfileById(activeProfileId);let message=active?`The active profile is ${active.label}, which is not a vision profile. Select and explicitly start Fast Vision or Quality Vision; no model switch occurred.`:'No verified vision profile is active. Select and explicitly start Fast Vision or Quality Vision; no model switch occurred.';logline('bad','SYSTEM',message);toast(message);return}
 if((image||useActive)&&explicitEngineerMessage(text)){let message='Engineer image inspection is not enabled. Remove the image or use ordinary vision chat.';logline('bad','SYSTEM',message);toast(message);return}
 let prompt=text||((image||useActive)?'Describe this image.':''),localImage=pendingMissionImage||activeMissionImage;
 let browserStarted=performance.now(),d=null;q('input').value='';logline('user','ERIC',prompt);if(image)logMissionImage(localImage,'NEW IMAGE — becomes active for follow-ups');else if(useActive)logMissionImage(activeMissionImage,'USING ACTIVE IMAGE');think(true);
 try{d=explicitEngineerMessage(prompt)?await requestNonStreamingChat(prompt,null,false):await requestGuardedStreamChat(prompt,image,useActive)}catch(e){if(e?.name==='AbortError'){logline('bad','SYSTEM','Generation canceled. No partial assistant answer was archived. The active image remains available for retry.');d={ok:false,cancelled:true,timing:{}};await refreshActiveMissionImage()}else{logline('bad','ERROR',String(e));d={ok:false,timing:{}}}}finally{
  chatStreamController=null;think(false);
  if(d?.active_image?.attached){let meta=d.active_image,local=(pendingMissionImage&&pendingMissionImage.sha256===meta.sha256)?pendingMissionImage:(activeMissionImage&&activeMissionImage.sha256===meta.sha256?activeMissionImage:null),nextPreview=local?.preview_url||'';if(activeMissionImage?.preview_url&&activeMissionImage.preview_url!==nextPreview)revokeMissionPreview(activeMissionImage);activeMissionImage={...missionImageMetadata({name:meta.filename,type:meta.mime,size:meta.size_bytes,width:meta.width,height:meta.height,sha256:meta.sha256}),preview_url:nextPreview};if(pendingMissionImage?.sha256===meta.sha256){pendingMissionImage.data_url='';pendingMissionImage=null}renderMissionImage()}
  let browserMs=performance.now()-browserStarted,modelMs=Number(d?.timing?.model_ms||0),firstMs=Number(d?.timing?.first_guarded_chunk_ms||0);q('ms').textContent=modelMs>0?`READY • ${(browserMs/1000).toFixed(1)}s total • ${(modelMs/1000).toFixed(1)}s model${firstMs>0?` • ${(firstMs/1000).toFixed(1)}s first guarded`:''}`:`READY • ${(browserMs/1000).toFixed(1)}s total`;
 }
}
/* MISSION_IMAGE_CONTINUITY_REPAIR_PHASE1_BROWSER_END */
/* MODEL_PROFILE_SELECTOR_PHASE2_BEHAVIOR_START */
function modelNameFromPath(value){return String(value||'').replace(/\\/g,'/').split('/').pop()}
function modelProfileById(id){return MODEL_PROFILES.find(p=>p.id===id)}
function modelProfileByName(name){return MODEL_PROFILES.find(p=>p.model===name)}
function profileBadgeClass(profile){return profile.status.includes('PENDING')?'pending':'supported'}
function renderModelProfiles(){
 let grid=q('modelProfileGrid');if(!grid)return;
 let selectedName=modelNameFromPath(q('model')?.value);
 grid.innerHTML=MODEL_PROFILES.map(profile=>{
  let model=modelCatalog.find(item=>item.name===profile.model);
  let selected=Boolean(model&&model.name===selectedName);
  let availability=model?'':'disabled';
  let recommended=profile.recommended?'<div class=small>Recommended starting profile</div>':'';
  return `<button type=button class="modelprofile ${selected?'selected':''}" onclick="selectModelProfile('${profile.id}')" ${availability}><div class=modelprofilehead><span class=modelprofiletitle>${esc(profile.label)}</span><span class="modelprofilebadge ${profileBadgeClass(profile)}">${esc(profile.status)}</span></div>${recommended}<div class=modelprofilebest>${esc(profile.best)}</div><div class=modelprofilemeta><div>Speed: ${esc(profile.speed)}</div><div>Vision: ${esc(profile.vision)}</div><div>Reasoning: ${esc(profile.reasoning)}</div><div>Model: ${esc(profile.model)}</div><div>${esc(profile.note)}</div>${model?'':'<div class=bad>Model file not currently available.</div>'}</div></button>`;
 }).join('');
}
function setPendingModelStatus(profile,model){
 let target=q('modelProfileStatus');if(!target)return;
 if(profile&&model){
  target.textContent=`Pending selection: ${profile.label}\nModel: ${profile.model}\nNo engine action has occurred. Use Start Selected Profile when ready.`;
 }else if(model){
  target.textContent=`Pending exact GGUF selection: ${model.name}\nNo engine action has occurred. Use Start Selected Profile when ready.`;
 }else{
  target.textContent='No installed GGUF model is available.';
 }
}
function selectModelProfile(id){
 let profile=modelProfileById(id);
 let model=profile?modelCatalog.find(item=>item.name===profile.model):null;
 if(!profile||!model){toast('That profile model is not currently available.');return}
 q('model').value=model.path;selectedProfileId=profile.id;
 try{localStorage.setItem('kayock.model.profile.pending',profile.id)}catch(e){}
 renderModelProfiles();setPendingModelStatus(profile,model);
}
function syncProfileFromSelect(){
 let selected=modelCatalog.find(item=>item.path===q('model').value);
 let profile=selected?modelProfileByName(selected.name):null;
 selectedProfileId=profile?.id||'';
 if(profile){try{localStorage.setItem('kayock.model.profile.pending',profile.id)}catch(e){}}
 renderModelProfiles();setPendingModelStatus(profile,selected);
}
async function loadModels(){
 let d=await (await fetch('/api/models')).json();
 modelCatalog=Array.isArray(d.models)?d.models:[];
 let select=q('model'),previous=select.value;
 select.innerHTML=modelCatalog.length?modelCatalog.map(m=>`<option value="${esc(m.path)}">${esc(m.name)}</option>`).join(''):'<option>No GGUF models found</option>';
 let saved='';try{saved=localStorage.getItem('kayock.model.profile.pending')||''}catch(e){}
 let savedProfile=modelProfileById(saved);
 let target=(savedProfile&&modelCatalog.find(item=>item.name===savedProfile.model))||modelCatalog.find(item=>item.path===previous)||modelCatalog.find(item=>item.name==='Qwen3.5-4B-Q4_K_M.gguf')||modelCatalog[0]||null;
 if(target)select.value=target.path;
 let profile=target?modelProfileByName(target.name):null;
 selectedProfileId=profile?.id||'';
 renderModelProfiles();setPendingModelStatus(profile,target);
}
/* MODEL_PROFILE_SELECTOR_PHASE2_BEHAVIOR_END */
async function loadProf(){let d=await (await fetch('/api/professors')).json();q('profgrid').innerHTML=Object.entries(d.professors).map(([k,p])=>`<div class="card prof ${k===d.active?'activeProf':''}"><h3>${esc(p.name)}</h3><div class=warn>${esc(p.college)}</div><p class=small><i>"${esc(p.motto)}"</i></p><button onclick="setProf('${k}')">${k===d.active?'Active':'Activate'}</button><button onclick="setProf('${k}').then(()=>go('mission'))">Use in Mission</button></div>`).join('')}
async function setProf(k){let d=await api('/api/professor/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:k})}); if(d?.ok){logline('sys','ACADEMY',d.message);loadProf();loadMemory()}}
async function startChat(){let requestedProfile=selectedProfileId||'';let d=await api('/api/chat/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:q('model').value,profile:requestedProfile})});if(d?.ok){activeProfileId=String(d?.runtime?.profile_id||requestedProfile||'');if(!modelProfileById(activeProfileId)?.vision?.includes('Yes'))clearMissionImageLocal();else await refreshActiveMissionImage()}logline(d?.ok?'sys':'bad','SYSTEM',d?.message||'start failed');loadMemory();refresh()}
async function stopChatEngine(){let d=await api('/api/chat/stop');if(d?.ok){activeProfileId='';clearMissionImageLocal()}logline(d?.ok?'sys':'bad','SYSTEM',d?.message||'stop failed');refresh()}
async function loadProjects(){let d=await (await fetch('/api/projects/list')).json();q('plist').innerHTML='<div class=grid>'+d.projects.map(p=>`<div class="card project"><h3>🗂 ${esc(p.name)}</h3><p class=small>Files: ${p.files} | Updated: ${esc(p.modified)}</p><button onclick="selectProject('${js(p.name)}')">Select</button><button onclick="api('/api/projects/open?name=${encodeURIComponent(p.name)}')">Open Folder</button></div>`).join('')+'</div>'}
async function createProject(){let name=q('newProject').value.trim();if(!name)return toast('Enter a project name.');let d=await api('/api/projects/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});if(d?.ok){q('newProject').value='';loadProjects();selectProject(d.name)}}
async function selectProject(name){let d=await (await fetch('/api/projects/select',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})})).json();toast(d.message);if(d.ok){activeProject=d.name;q('apro').textContent=d.name;q('pnoteTitle').textContent=d.name;q('pnote').value=d.note||'';loadMemory();refresh()}}
async function saveNote(){if(!activeProject)return toast('Select a project first.');await api('/api/projects/save-note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:activeProject,note:q('pnote').value})});loadMemory()}
function askProject(){if(!activeProject)return toast('Select a project first.');go('mission');q('input').value=`We are working on project "${activeProject}". Here are my current notes:\n\n${q('pnote').value}\n\nWhat should I do next?`}
async function loadMemory(){let d=await (await fetch('/api/memory/current')).json();missionData=d;if(!d.ok){q('memstate').textContent=d.message;q('resume').textContent='No active mission.';q('tasks').textContent='No tasks.';q('timeline').textContent='No timeline.';return}let m=d.mission;let state=`Project: ${m.project}\nCurrent task: ${m.current_task||'None'}\nProfessor: ${m.active_professor_name}\nModel: ${m.active_model_name||'None'}\nCreated: ${m.created}\nLast opened: ${m.last_opened}\nEvents: ${d.timeline.length}\nTasks: ${d.tasks.length}`;q('memstate').textContent=state;q('resume').textContent=state;q('tasks').innerHTML=d.tasks.length?d.tasks.map((t,i)=>`<div><input type=checkbox ${t.done?'checked':''} onchange="toggleTask(${i},this.checked)"> <span class="${t.done?'done':''}">${esc(t.text)}</span></div>`).join(''):'No tasks yet.';q('timeline').innerHTML=d.timeline.slice().reverse().slice(0,35).map(e=>`<div class=tl><div class=time>${esc(e.time)}</div>${esc(e.event)}</div>`).join('')||'No timeline yet.'}
async function addTask(){let text=q('task').value.trim();if(!text)return toast('Enter a task.');await api('/api/memory/task/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});q('task').value='';loadMemory()}
async function toggleTask(index,done){await api('/api/memory/task/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index,done})});loadMemory()}
function resumeMission(){if(!missionData?.ok){toast('Select a project first.');go('projects');return}let m=missionData.mission;go('mission');q('input').value=`Resume mission "${m.project}". Current task: ${m.current_task||'None'}. Active professor: ${m.active_professor_name}. What should we do next?`;toast('Mission context loaded.')}




function libraryQuestion(){
    return (q('libAskQuestion')?.value||'').trim()||'Analyze this Iron Library file. Tell me what matters, what I should do next, and any risks or useful connections.';
}
async function askProfessorAboutLib(rel){
    try{
        let d=await (await fetch('/api/library/preview?path='+encodeURIComponent(rel)+'&limit=9000')).json();
        go('mission');
        if(d.ok){
            q('input').value=`Iron Library request for the active professor.

Question:
${libraryQuestion()}

File:
Library/${d.rel_path}

Type: ${d.ext}
Size: ${d.size}
Modified: ${d.modified}

Preview:
${d.content}`;
        }else{
            q('input').value=`Iron Library request for the active professor.

Question:
${libraryQuestion()}

File:
Library/${rel}

Preview unavailable:
${d.message||'This file type is not previewable yet. Use the file path and available metadata only.'}`;
        }
        toast('Library question sent to Mission Console input.');
    }catch(e){
        go('mission');
        q('input').value=`Iron Library request for the active professor.

Question:
${libraryQuestion()}

File:
Library/${rel}

Note: Preview failed: ${e}`;
        toast('Library path sent with preview error.');
    }
}

async function loadIronIndexStatus(){
    if(!q('ironIndexStatus'))return;
    try{
        let d=await (await fetch('/api/library/index/status')).json();
        q('ironIndexStatus').textContent=d.index_found?`Index built: ${d.built}\nItems: ${d.items}\nScanned: ${d.scanned}\nSkipped: ${d.skipped}\nIndex: ${d.index_file}`:'No Iron Library index found yet.';
    }catch(e){q('ironIndexStatus').textContent='Index status failed: '+e}
}
async function buildIronIndex(){
    if(!q('ironIndexStatus'))return;
    q('ironIndexStatus').textContent='Building Iron Library index... this may take a moment.';
    try{
        let d=await (await fetch('/api/library/index/build?max_files=2000')).json();
        q('ironIndexStatus').textContent=`${d.message}\nBuilt: ${d.built}\nScanned: ${d.scanned}\nSkipped: ${d.skipped}\nIndex: ${d.index_file}`;
        toast(d.message||'Index built.');
    }catch(e){q('ironIndexStatus').textContent='Index build failed: '+e}
}
async function searchIronIndex(){
    if(!q('ironIndexResults'))return;
    let term=q('ironIndexSearch')?.value||'';
    if(!term.trim()){toast('Enter an indexed text search term.');return}
    q('ironIndexResults').textContent='Searching index...';
    try{
        let d=await (await fetch('/api/library/index/search?q='+encodeURIComponent(term)+'&limit=100')).json();
        if(!d.ok){q('ironIndexResults').textContent=d.message||'Index search unavailable.';return}
        if(!d.results?.length){q('ironIndexResults').innerHTML=`No indexed matches for "${esc(term)}".`;return}
        q('ironIndexResults').innerHTML=`<div class=time>Index built: ${esc(d.built||'unknown')} • Results: ${d.count}</div>`+d.results.map(it=>{
            let icon=({'.md':'📝','.txt':'📝','.log':'📜','.json':'{}','.py':'🐍','.js':'🟨','.html':'🌐','.css':'🎨'}[it.ext]||'📄');
            return `<div class=indexresult><h4>${icon} ${esc(it.name)}</h4><span class=libbadge>${esc(it.ext||'file')}</span><span class=libbadge>${esc(it.size||'')}</span><span class=indexscore>score ${esc(it.score)}</span><div class=libmeta>${esc(it.rel_path)}<br>Modified: ${esc(it.modified||'')}</div><button onclick="previewLib('${js(it.rel_path)}')">Preview</button><button onclick="askProfessorAboutLib('${js(it.rel_path)}')">Ask Professor</button><button onclick="api('/api/library/open?path=${encodeURIComponent(it.rel_path)}')">Open File</button><button onclick="copyLibPath('${js(it.rel_path)}')">Copy Path</button><button onclick="sendLibPath('${js(it.rel_path)}')">Send Path</button><button onclick="sendLibPreview('${js(it.rel_path)}')">Send Preview</button><div class=indexsnippet>${esc(it.snippet||'')}</div></div>`
        }).join('');
    }catch(e){q('ironIndexResults').textContent='Index search failed: '+e}
}

async function previewLib(rel){
    if(!q('libPreview'))return;
    q('libPreview').textContent='Loading preview...';
    try{
        let d=await (await fetch('/api/library/preview?path='+encodeURIComponent(rel)+'&limit=16000')).json();
        if(!d.ok){
            q('libPreview').innerHTML=`<div class=warn>${esc(d.message||'Preview unavailable.')}</div><br><div class=copypath>${esc(rel)}</div><button onclick="api('/api/library/open?path=${encodeURIComponent(rel)}')">Open File</button><button onclick="askProfessorAboutLib('${js(rel)}')">Ask Professor</button><button onclick="copyLibPath('${js(rel)}')">Copy Path</button><button onclick="sendLibPath('${js(rel)}')">Send Path</button>`;
            return;
        }
        let trunc=d.truncated?`\n\n--- Preview truncated at 16,000 characters. Open the file for full content. ---`:'';
        q('libPreview').innerHTML=`<div class=previewhead><button onclick="api('/api/library/open?path=${encodeURIComponent(d.rel_path)}')">Open File</button><button onclick="askProfessorAboutLib('${js(d.rel_path)}')">Ask Professor</button><button onclick="copyLibPath('${js(d.rel_path)}')">Copy Path</button><button onclick="sendLibPath('${js(d.rel_path)}')">Send Path</button><button onclick="sendLibPreview('${js(d.rel_path)}')">Send Preview</button></div><div class=copypath>${esc(d.rel_path)} • ${esc(d.size)} • ${esc(d.modified)}</div><div class=previewbox>${esc(d.content+trunc)}</div>`;
    }catch(e){
        q('libPreview').textContent='Preview failed: '+e;
    }
}
function copyLibPath(rel){
    navigator.clipboard?.writeText('Library/'+rel);
    toast('Library path copied.');
}
function sendLibPath(rel){
    go('mission');
    q('input').value=`Please help me with this Iron Library file:\nLibrary/${rel}`;
    toast('Library path sent to Mission Console input.');
}
async function sendLibPreview(rel){
    try{
        let d=await (await fetch('/api/library/preview?path='+encodeURIComponent(rel)+'&limit=8000')).json();
        go('mission');
        if(d.ok){
            q('input').value=`Please help me analyze this Iron Library file.\n\nPath: Library/${d.rel_path}\nType: ${d.ext}\nSize: ${d.size}\n\nPreview:\n${d.content}`;
        }else{
            q('input').value=`Please help me with this Iron Library file:\nLibrary/${rel}\n\nNote: ${d.message||'Preview unavailable.'}`;
        }
        toast('Library preview sent to Mission Console input.');
    }catch(e){toast('Could not send preview: '+e)}
}

async function searchLib(){
    if(!q('libResults'))return;
    let term=q('libSearch')?.value||'';
    let type=q('libType')?.value||'all';
    q('libSearchStatus').textContent='Searching Iron Library...';
    try{
        let d=await (await fetch('/api/library/search?q='+encodeURIComponent(term)+'&type='+encodeURIComponent(type)+'&limit=250')).json();
        q('libSearchStatus').textContent=`Found ${d.count} result(s). Scanned ${d.scanned} item(s).`;
        if(!d.results?.length){
            q('libResults').innerHTML='No matching library items.';
            return;
        }
        q('libResults').innerHTML=d.results.map(it=>{
            let icon=it.is_dir?'📁':({'.pdf':'📕','.md':'📝','.txt':'📝','.docx':'📄','.doc':'📄','.png':'🖼️','.jpg':'🖼️','.jpeg':'🖼️','.webp':'🖼️','.py':'🐍','.js':'🟨','.html':'🌐','.css':'🎨'}[it.ext]||'📄');
            let action=it.is_dir?`<button onclick="loadLib('${js(it.rel_path)}');go('library')">Open Folder</button><button onclick="copyLibPath('${js(it.rel_path)}')">Copy Path</button><button onclick="sendLibPath('${js(it.rel_path)}')">Send Path</button>`:`<button onclick="previewLib('${js(it.rel_path)}')">Preview</button><button onclick="askProfessorAboutLib('${js(it.rel_path)}')">Ask Professor</button><button onclick="api('/api/library/open?path=${encodeURIComponent(it.rel_path)}')">Open File</button><button onclick="copyLibPath('${js(it.rel_path)}')">Copy Path</button><button onclick="sendLibPath('${js(it.rel_path)}')">Send Path</button>`;
            return `<div class=libresult><h4>${icon} ${esc(it.name)}</h4><span class=libbadge>${esc(it.ext||'file')}</span><span class=libbadge>${esc(it.size||'folder')}</span><div class=libmeta>${esc(it.rel_path)}<br>Modified: ${esc(it.modified||'')}</div>${action}</div>`
        }).join('');
    }catch(e){
        q('libSearchStatus').textContent='Library search failed: '+e;
    }
}

async function loadLib(rel=''){curLib=rel;let d=await (await fetch('/api/library/list?path='+encodeURIComponent(rel))).json();q('libpath').textContent=d.display_path||'Library';if(!d.ok){q('liblist').textContent=d.message;return}q('liblist').innerHTML='<table><tr><th>Name</th><th>Type</th><th>Size</th><th>Action</th></tr>'+d.items.map(it=>`<tr><td>${it.is_dir?'📁':'📄'} ${esc(it.name)}</td><td>${it.is_dir?'folder':it.ext}</td><td>${it.size}</td><td>${it.is_dir?`<button class=link onclick="loadLib('${js(it.rel_path)}')">Open</button>`:`<button class=link onclick="previewLib('${js(it.rel_path)}')">Preview</button> <button class=link onclick="askProfessorAboutLib('${js(it.rel_path)}')">Ask Professor</button> <button class=link onclick="api('/api/library/open?path=${encodeURIComponent(it.rel_path)}')">Open File</button>`}</td></tr>`).join('')+'</table>'}
function libUp(){let a=curLib.split(/[\\/]/).filter(Boolean);a.pop();loadLib(a.join('/'))}




let activeUniverseName=null;





let nfSceneCards=[];
function starterSceneLines(){
    return [
        'Book 1: Prophecy Discovery | Anthony / Whisper | Pueblo tunnels | Anthony, Chee | Anthony learns the prophecy is not just vampire politics but a possible end to the blood curse. | Anthony distrusts the source and fears being used. | Anthony accepts that Kayock’s legacy is now his problem. | Plant prophecy rules; keep reader knowledge limited.',
        'Book 1: Kayock Falls | Anthony / Whisper | Kayock’s lair | Anthony, Kayock, Jokaya | Kayock’s death transfers emotional and mythic weight to Anthony. | Jokaya proves she can kill even the first vampire. | Anthony inherits the mission without understanding all of it. | Define how Kayock can die and what remains active.',
        'Book 1: The Ex Revealed | Anthony / Whisper | Modern Pueblo | Anthony, ex, Jokaya shadow | Personal stakes collide with vampire prophecy. | Anthony learns his ex has been turned but not what she has become. | Book 2 hook is created. | Tie her transformation to Jokaya experiments or prophecy misunderstanding.',
        'Book 2: Olmec Clue Site | Anthony / Whisper | Olmec pyramid | Anthony, Croatoan clues, Thoth records | Anthony follows evidence toward Croatoan and the crystal skull mystery. | The clues suggest an escape that should have been impossible. | Croatoan becomes an active future threat. | Use claw marks, broken pedestal, mismatched glyphs, ancient blood.'
    ];
}
function parseSceneLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=8)return {title:parts[0],pov:parts[1],location:parts[2],characters:parts[3],purpose:parts[4],conflict:parts[5],outcome:parts[6],canon:parts.slice(7).join(' | ')};
    return {title:raw,pov:'',location:'',characters:'',purpose:'',conflict:'',outcome:'',canon:''};
}
function sceneCardToLine(sc){
    return `${(sc.title||'Untitled Scene').trim()} | ${(sc.pov||'').trim()} | ${(sc.location||'').trim()} | ${(sc.characters||'').trim()} | ${(sc.purpose||'').replace(/\r?\n/g,' ').trim()} | ${(sc.conflict||'').replace(/\r?\n/g,' ').trim()} | ${(sc.outcome||'').replace(/\r?\n/g,' ').trim()} | ${(sc.canon||'').replace(/\r?\n/g,' ').trim()}`;
}
function syncScenesFromText(){
    if(!q('nfScenes'))return;
    nfSceneCards=(q('nfScenes').value||'').split(/\r?\n/).map(parseSceneLine).filter(Boolean);
}
function syncScenesToText(){
    if(!q('nfScenes'))return;
    q('nfScenes').value=nfSceneCards.map(sceneCardToLine).join('\n');
    updateNovelCounts();
}
function renderSceneCards(){
    if(!q('nfSceneCards'))return;
    syncScenesToText();
    if(!nfSceneCards.length){q('nfSceneCards').innerHTML='No scenes yet.';return}
    q('nfSceneCards').innerHTML=nfSceneCards.map((sc,i)=>`<div class=scenecard><h4>🎬 ${esc(sc.title||'Untitled Scene')}</h4><span class=scenetag>POV: ${esc(sc.pov||'unknown')}</span><span class=scenetag>${esc(sc.location||'no location')}</span><span class=scenetag>${esc(sc.characters||'no characters')}</span><div class=scenedetails><b>Purpose:</b> ${esc(sc.purpose||'None')}\n<b>Conflict:</b> ${esc(sc.conflict||'None')}\n<b>Outcome:</b> ${esc(sc.outcome||'None')}\n<b>Canon:</b> ${esc(sc.canon||'None')}</div><div class=sceneactions><button onclick="editSceneCard(${i})">Edit</button><button onclick="moveSceneCard(${i},-1)">Up</button><button onclick="moveSceneCard(${i},1)">Down</button><button onclick="deleteSceneCard(${i})">Delete</button><button onclick="sendSceneBrief(${i})">Send Brief</button><button onclick="generateSceneDraft(${i})">Generate Draft</button></div></div>`).join('');
}
function addSceneCard(){
    let title=q('nfSceneTitle').value.trim();
    if(!title){toast('Enter a scene title before adding.');return}
    nfSceneCards.push({title,pov:q('nfScenePOV').value.trim(),location:q('nfSceneLocation').value.trim(),characters:q('nfSceneCharacters').value.trim(),purpose:q('nfScenePurpose').value.trim(),conflict:q('nfSceneConflict').value.trim(),outcome:q('nfSceneOutcome').value.trim(),canon:q('nfSceneCanon').value.trim()});
    ['nfSceneTitle','nfScenePOV','nfSceneLocation','nfSceneCharacters','nfScenePurpose','nfSceneConflict','nfSceneOutcome','nfSceneCanon'].forEach(id=>q(id).value='');
    renderSceneCards();
    toast('Scene added.');
}
function editSceneCard(i){
    let sc=nfSceneCards[i]; if(!sc)return;
    q('nfSceneTitle').value=sc.title||''; q('nfScenePOV').value=sc.pov||''; q('nfSceneLocation').value=sc.location||''; q('nfSceneCharacters').value=sc.characters||''; q('nfScenePurpose').value=sc.purpose||''; q('nfSceneConflict').value=sc.conflict||''; q('nfSceneOutcome').value=sc.outcome||''; q('nfSceneCanon').value=sc.canon||'';
    nfSceneCards.splice(i,1); renderSceneCards(); toast('Scene loaded for editing.');
}
function moveSceneCard(i,delta){let j=i+delta;if(j<0||j>=nfSceneCards.length)return;[nfSceneCards[i],nfSceneCards[j]]=[nfSceneCards[j],nfSceneCards[i]];renderSceneCards();}
function deleteSceneCard(i){nfSceneCards.splice(i,1);renderSceneCards();}
function sortSceneCards(){nfSceneCards.sort((a,b)=>String(a.title||'').localeCompare(String(b.title||'')));renderSceneCards();toast('Scenes sorted.');}
function restoreStarterScenes(){q('nfScenes').value=starterSceneLines().join('\n');syncScenesFromText();renderSceneCards();updateNovelCounts();toast('Starter scenes restored.');}
function sceneCardsText(){
    syncScenesFromText();
    return nfSceneCards.map((sc,i)=>`${i+1}. ${sc.title||'Untitled Scene'}\nPOV: ${sc.pov||'Unknown'}\nLocation: ${sc.location||'Unknown'}\nCharacters: ${sc.characters||'None'}\nPurpose: ${sc.purpose||'None'}\nConflict: ${sc.conflict||'None'}\nOutcome: ${sc.outcome||'None'}\nCanon Notes: ${sc.canon||'None'}`).join('\n\n')||'No scenes.';
}
function sceneBrief(sc){
    return `Scene Brief

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Scene: ${sc.title||'Untitled Scene'}
POV: ${sc.pov||'Unknown'}
Location: ${sc.location||'Unknown'}
Characters Present: ${sc.characters||'None'}

Purpose:
${sc.purpose||'None'}

Conflict:
${sc.conflict||'None'}

Outcome:
${sc.outcome||'None'}

Canon Notes:
${sc.canon||'None'}`;
}
function sendSceneBrief(i){
    let sc=nfSceneCards[i]; if(!sc)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge scene.

${sceneBrief(sc)}

Please improve this scene brief, identify continuity risks, and suggest beats that make the scene stronger.`;
    toast('Scene brief sent to Mission Console input.');
}
function generateSceneDraft(i){
    let sc=nfSceneCards[i]; if(!sc)return;
    go('mission');
    q('input').value=`You are Novel Forge's scene drafting engine.

Draft this scene using the scene brief and Codex context. Preserve canon, respect character motivations, and avoid resolving mysteries too early.

Return:
1. Scene draft
2. Continuity notes
3. Foreshadowing opportunities
4. Revision suggestions

${sceneBrief(sc)}

Codex Context:
${completeStoryBibleText()}`;
    toast('Scene draft request sent to Mission Console input.');
}
function checkScenePlan(){
    syncScenesToText();
    go('mission');
    q('input').value=`You are Novel Forge's scene planning engine.

Analyze these scenes for weak purpose, missing conflict, unclear outcome, continuity risks, pacing gaps, and missing setup/payoff.

Return your answer in this exact structure:

1. Scene Plan Summary
2. Strongest Scenes
3. Weakest Scenes
4. Missing Conflict
5. Missing Outcomes
6. Continuity Risks
7. Better Scene Order
8. Recommended New Scenes
9. Best Next Scene to Draft

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Scenes:
${sceneCardsText()}

Story Bible:
${completeStoryBibleText()}`;
    toast('Scene plan check sent to Mission Console input.');
}

let nfLocationCards=[];
function slippingLocationLines(){
    return [
        'Pueblo tunnels | Urban underworld / hidden lair network | Dark underground routes tied to local danger, hidden vampire movement, and possible Baal lore. | Hidden entrances, old chambers, blood traces, things older than the city. | Anthony, Baal, Jokaya | Baal threat, hidden vampire movement',
        'Olmec pyramid | Ancient ruin / clue site | A major Book 2 investigation site tied to Croatoan, crystal skulls, and evidence of ancient escape. | Claw marks, broken pedestal, mismatched glyphs, ancient blood, priest journal fragment. | Anthony, Croatoan, Thoth | Croatoan escape, crystal skulls',
        'Mayan prison | Ancient prison | Prison site connected to Croatoan’s defeat, confinement, and eventual mystery escape. | Prison mechanism may be spiritual, blood-based, or prophecy-linked. | Croatoan, Jokaya, Kayock | How did Croatoan escape?',
        'Kayock’s lair | Protector stronghold / archive | Kayock’s base containing old records, blood vats, hidden technology, and possibly his legacy plan. | Computer, records, blood vats, prophecy materials, author-only secrets. | Kayock, Anthony | Kayock legacy, bloodless future',
        'Roanoke | Lost colony / origin clue | Historical site connected to Croatoan, disappearance, and vampire mythology. | The name Croatoan may be clue, warning, or trap. | Croatoan, Kayock | Roanoke mystery',
        'Vatican | Religious archive / power center | Potential repository of prophecy records, hunter history, and dangerous theological secrets. | Records may conflict with vampire versions of history. | Anthony, Father Grandier, St. Michael | prophecy misunderstanding',
        'Desert where Kayock meets Jesus | Sacred encounter site | Location of Kayock’s transformative meeting with Jesus and the moral root of the protector mission. | What Jesus told Kayock should be revealed carefully. | Kayock, Jesus, Anthony | What did Kayock learn from Jesus?'
    ];
}
function parseLocationLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=6)return {name:parts[0],type:parts[1],description:parts[2],secrets:parts[3],characters:parts[4],mysteries:parts.slice(5).join(' | ')};
    return {name:raw,type:'',description:'',secrets:'',characters:'',mysteries:''};
}
function locationCardToLine(loc){
    return `${(loc.name||'Unnamed Location').trim()} | ${(loc.type||'').trim()} | ${(loc.description||'').replace(/\r?\n/g,' ').trim()} | ${(loc.secrets||'').replace(/\r?\n/g,' ').trim()} | ${(loc.characters||'').trim()} | ${(loc.mysteries||'').trim()}`;
}
function syncLocationsFromText(){
    if(!q('nfLocations'))return;
    nfLocationCards=(q('nfLocations').value||'').split(/\r?\n/).map(parseLocationLine).filter(Boolean);
}
function syncLocationsToText(){
    q('nfLocations').value=nfLocationCards.map(locationCardToLine).join('\n');
    updateNovelCounts();
}
function renderLocationCards(){
    if(!q('nfLocationCards'))return;
    syncLocationsToText();
    if(!nfLocationCards.length){q('nfLocationCards').innerHTML='No location cards yet.';return}
    q('nfLocationCards').innerHTML=nfLocationCards.map((loc,i)=>`<div class=loccard><h4>📍 ${esc(loc.name||'Unnamed Location')}</h4><span class=loctag>${esc(loc.type||'type unknown')}</span><span class=loctag>${esc(loc.characters||'no characters')}</span><span class=loctag>${esc(loc.mysteries||'no mysteries')}</span><div class=locdetails><b>Description:</b> ${esc(loc.description||'None')}\n<b>Secrets:</b> ${esc(loc.secrets||'None')}</div><div class=locactions><button onclick="editLocationCard(${i})">Edit</button><button onclick="moveLocationCard(${i},-1)">Up</button><button onclick="moveLocationCard(${i},1)">Down</button><button onclick="deleteLocationCard(${i})">Delete</button><button onclick="sendLocationCard(${i})">Send</button></div></div>`).join('');
}
function addLocationCard(){
    let name=q('nfLocName').value.trim();
    if(!name){toast('Enter a location name before adding.');return}
    nfLocationCards.push({name,type:q('nfLocType').value.trim(),description:q('nfLocDescription').value.trim(),secrets:q('nfLocSecrets').value.trim(),characters:q('nfLocCharacters').value.trim(),mysteries:q('nfLocMysteries').value.trim()});
    ['nfLocName','nfLocType','nfLocDescription','nfLocSecrets','nfLocCharacters','nfLocMysteries'].forEach(id=>q(id).value='');
    renderLocationCards();
    toast('Location added.');
}
function editLocationCard(i){
    let loc=nfLocationCards[i]; if(!loc)return;
    q('nfLocName').value=loc.name||''; q('nfLocType').value=loc.type||''; q('nfLocDescription').value=loc.description||''; q('nfLocSecrets').value=loc.secrets||''; q('nfLocCharacters').value=loc.characters||''; q('nfLocMysteries').value=loc.mysteries||'';
    nfLocationCards.splice(i,1); renderLocationCards(); toast('Location loaded for editing.');
}
function moveLocationCard(i,delta){let j=i+delta;if(j<0||j>=nfLocationCards.length)return;[nfLocationCards[i],nfLocationCards[j]]=[nfLocationCards[j],nfLocationCards[i]];renderLocationCards();}
function deleteLocationCard(i){nfLocationCards.splice(i,1);renderLocationCards();}
function sortLocationCards(){nfLocationCards.sort((a,b)=>String(a.name||'').localeCompare(String(b.name||'')));renderLocationCards();toast('Locations sorted.');}
function restoreSlippingLocations(){q('nfLocations').value=slippingLocationLines().join('\n');syncLocationsFromText();renderLocationCards();updateNovelCounts();updateCodexDashboard();
    toast('Slipping locations restored.');}
function locationCardsText(){syncLocationsFromText();return nfLocationCards.map((loc,i)=>`${i+1}. ${loc.name||'Unnamed Location'}\nType: ${loc.type||'Unknown'}\nDescription: ${loc.description||'None'}\nSecrets: ${loc.secrets||'None'}\nCharacters: ${loc.characters||'None'}\nMysteries: ${loc.mysteries||'None'}`).join('\n\n')||'No locations.'}
function sendLocationCard(i){
    let loc=nfLocationCards[i]; if(!loc)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge location.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Location: ${loc.name||'Unnamed Location'}
Type: ${loc.type||'Unknown'}
Description: ${loc.description||'None'}
Secrets: ${loc.secrets||'None'}
Related Characters: ${loc.characters||'None'}
Related Mysteries: ${loc.mysteries||'None'}

Please strengthen this location, identify story uses, reveal timing, continuity risks, and sensory details.`;
    toast('Location sent to Mission Console input.');
}
function checkWorldbuilding(){
    syncLocationsToText();
    go('mission');
    q('input').value=`You are Novel Forge's worldbuilding logic engine.

Analyze these locations for unclear geography, weak atmosphere, missing secrets, cultural/mythological risks, underused settings, and continuity problems.

Return your answer in this exact structure:

1. Worldbuilding Summary
2. Strongest Locations
3. Weakest / Least Defined Locations
4. Geography or Timeline Problems
5. Secret / Reveal Opportunities
6. Cultural or Mythology Handling Risks
7. Location-Character Connections
8. Recommended Improvements
9. Best Next Location Scene

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Locations:
${locationCardsText()}

Characters:
${characterCardsText()}

Mysteries:
${mysteryCardsText()}`;
    toast('Worldbuilding check sent to Mission Console input.');
}

let nfArtifactCards=[];
function slippingArtifactLines(){
    return [
        'Crystal skulls | Prophecy vessel / memory prison | May contain prophecy fragments, ancient vampire memories, imprisoned beings, or bloodline records. | Connected to Olmec/Mayan clues, Croatoan, Thoth, and old vampire knowledge. | Should require interpretation, have consequences, and avoid becoming an unlimited answer machine. | Anthony, Croatoan, Thoth, Kayock | What do the crystal skulls contain?',
        'Silver cross | Sacred weapon / personal proof | Burns Chee and proves spiritual rules matter; may connect Anthony to faith, curse, or hunter traditions. | Used in Anthony’s origin and Chee’s injury. | Must have consistent rules for why it works on some beings and not others. | Anthony, Chee | Anthony turning, vampire rules',
        'Ancient blood vats | Survival technology / moral horror | Provide cloned or stored blood alternative; tie into Kayock’s goal of ending predatory blood need. | Found in Kayock’s lair or later protector systems. | Need rules for supply, purity, consent, corruption, and who controls them. | Kayock, Anthony | bloodless future',
        'Prophecy records | Ancient text / contested truth | Records the prophecy but may be mistranslated or politically manipulated. | Tied to Thoth, Vatican, Kayock, and hunter priest traditions. | Must clearly separate true prophecy from interpretations. | Anthony, Kayock, Thoth, Yactazini | prophecy misunderstanding',
        'Clawed pedestal | Physical clue / missing artifact site | Evidence that something escaped, was removed, or transformed at the Olmec site. | Supports Croatoan escape and crystal skull mystery. | Should point to a specific event, not just atmosphere. | Croatoan, Anthony | Croatoan escape',
        'Priest journal fragment | Witness record / incomplete clue | A damaged account from a priest or hunter who saw part of the ancient event. | Reveals partial truth while preserving mystery. | Fragment should mislead or omit enough to keep tension. | Yactazini, Anthony | prophecy, Croatoan escape'
    ];
}
function parseArtifactLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=7)return {name:parts[0],type:parts[1],functionText:parts[2],history:parts[3],rules:parts[4],characters:parts[5],mysteries:parts.slice(6).join(' | ')};
    return {name:raw,type:'',functionText:'',history:'',rules:'',characters:'',mysteries:''};
}
function artifactCardToLine(art){
    return `${(art.name||'Unnamed Artifact').trim()} | ${(art.type||'').trim()} | ${(art.functionText||'').replace(/\r?\n/g,' ').trim()} | ${(art.history||'').replace(/\r?\n/g,' ').trim()} | ${(art.rules||'').replace(/\r?\n/g,' ').trim()} | ${(art.characters||'').trim()} | ${(art.mysteries||'').trim()}`;
}
function syncArtifactsFromText(){if(!q('nfArtifacts'))return;nfArtifactCards=(q('nfArtifacts').value||'').split(/\r?\n/).map(parseArtifactLine).filter(Boolean);}
function syncArtifactsToText(){q('nfArtifacts').value=nfArtifactCards.map(artifactCardToLine).join('\n');updateNovelCounts();}
function renderArtifactCards(){
    if(!q('nfArtifactCards'))return;
    syncArtifactsToText();
    if(!nfArtifactCards.length){q('nfArtifactCards').innerHTML='No artifact cards yet.';return}
    q('nfArtifactCards').innerHTML=nfArtifactCards.map((art,i)=>`<div class=artcard><h4>🔮 ${esc(art.name||'Unnamed Artifact')}</h4><span class=arttag>${esc(art.type||'type unknown')}</span><span class=arttag>${esc(art.characters||'no characters')}</span><span class=arttag>${esc(art.mysteries||'no mysteries')}</span><div class=artdetails><b>Function:</b> ${esc(art.functionText||'None')}\n<b>History:</b> ${esc(art.history||'None')}\n<b>Rules:</b> ${esc(art.rules||'None')}</div><div class=artactions><button onclick="editArtifactCard(${i})">Edit</button><button onclick="moveArtifactCard(${i},-1)">Up</button><button onclick="moveArtifactCard(${i},1)">Down</button><button onclick="deleteArtifactCard(${i})">Delete</button><button onclick="sendArtifactCard(${i})">Send</button></div></div>`).join('');
}
function addArtifactCard(){
    let name=q('nfArtName').value.trim();
    if(!name){toast('Enter an artifact name before adding.');return}
    nfArtifactCards.push({name,type:q('nfArtType').value.trim(),functionText:q('nfArtFunction').value.trim(),history:q('nfArtHistory').value.trim(),rules:q('nfArtRules').value.trim(),characters:q('nfArtCharacters').value.trim(),mysteries:q('nfArtMysteries').value.trim()});
    ['nfArtName','nfArtType','nfArtFunction','nfArtHistory','nfArtRules','nfArtCharacters','nfArtMysteries'].forEach(id=>q(id).value='');
    renderArtifactCards();
    toast('Artifact added.');
}
function editArtifactCard(i){
    let art=nfArtifactCards[i]; if(!art)return;
    q('nfArtName').value=art.name||''; q('nfArtType').value=art.type||''; q('nfArtFunction').value=art.functionText||''; q('nfArtHistory').value=art.history||''; q('nfArtRules').value=art.rules||''; q('nfArtCharacters').value=art.characters||''; q('nfArtMysteries').value=art.mysteries||'';
    nfArtifactCards.splice(i,1); renderArtifactCards(); toast('Artifact loaded for editing.');
}
function moveArtifactCard(i,delta){let j=i+delta;if(j<0||j>=nfArtifactCards.length)return;[nfArtifactCards[i],nfArtifactCards[j]]=[nfArtifactCards[j],nfArtifactCards[i]];renderArtifactCards();}
function deleteArtifactCard(i){nfArtifactCards.splice(i,1);renderArtifactCards();}
function sortArtifactCards(){nfArtifactCards.sort((a,b)=>String(a.name||'').localeCompare(String(b.name||'')));renderArtifactCards();toast('Artifacts sorted.');}
function restoreSlippingArtifacts(){q('nfArtifacts').value=slippingArtifactLines().join('\n');syncArtifactsFromText();renderArtifactCards();updateNovelCounts();updateCodexDashboard();
    toast('Slipping artifacts restored.');}
function artifactCardsText(){syncArtifactsFromText();return nfArtifactCards.map((art,i)=>`${i+1}. ${art.name||'Unnamed Artifact'}\nType: ${art.type||'Unknown'}\nFunction: ${art.functionText||'None'}\nHistory: ${art.history||'None'}\nRules / Limits: ${art.rules||'None'}\nCharacters: ${art.characters||'None'}\nMysteries: ${art.mysteries||'None'}`).join('\n\n')||'No artifacts.'}
function sendArtifactCard(i){
    let art=nfArtifactCards[i]; if(!art)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge artifact.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Artifact: ${art.name||'Unnamed Artifact'}
Type: ${art.type||'Unknown'}
Power / Function: ${art.functionText||'None'}
History: ${art.history||'None'}
Rules / Limits: ${art.rules||'None'}
Related Characters: ${art.characters||'None'}
Related Mysteries: ${art.mysteries||'None'}

Please strengthen this artifact, define clear rules, identify continuity risks, and suggest how it should affect the story.`;
    toast('Artifact sent to Mission Console input.');
}
function checkArtifactRules(){
    syncArtifactsToText();
    go('mission');
    q('input').value=`You are Novel Forge's artifact rules engine.

Analyze these artifacts for unclear powers, inconsistent rules, overpowered mechanics, missing costs, weak history, and payoff opportunities.

Return your answer in this exact structure:

1. Artifact System Summary
2. Strongest Artifacts
3. Weakest / Least Defined Artifacts
4. Rule Inconsistencies
5. Power Creep Risks
6. Missing Costs or Limits
7. Mystery / Plot Payoff Opportunities
8. Recommended Fixes
9. Best Next Artifact Scene

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Artifacts:
${artifactCardsText()}

Characters:
${characterCardsText()}

Mysteries:
${mysteryCardsText()}`;
    toast('Artifact rules check sent to Mission Console input.');
}

let nfMysteryCards=[];
function slippingMysteryLines(){
    return [
        'What exactly did Anthony’s ex become? | Unresolved | Anthony, ex, Jokaya, Chee | Anthony learns she has been turned, but not what she has become or who controls her. | Book 1 ending reveal; signs of a transformation that does not fit normal vampire rules. | Book 2 should make the hunt personal while tying her fate to Jokaya’s experiments or prophecy misunderstanding.',
        'How did Croatoan escape? | Unresolved | Croatoan, Jokaya, Kayock | Croatoan was imprisoned but later evidence suggests he escaped or was released. | Olmec pyramid clues; claw marks; broken pedestal; mismatched glyphs; priest journal fragment. | Reveal whether escape was deliberate, betrayal-driven, or part of a larger prophecy mechanism.',
        'What do the crystal skulls truly contain? | Clue planted | Croatoan, Thoth, Kayock, Anthony | The skulls may contain more than records; they might preserve memories, imprisoned vampires, prophecy fragments, or ancient blood power. | Claw marks, ancient blood residue, murals shifting from small to giant figures. | Pay off as a key to understanding Croatoan, the prophecy, or the bloodless future.',
        'What parts of the prophecy are misunderstood? | Unresolved | Anthony, Kayock, Jesus, Thoth | The prophecy may not mean killing vampires; it may mean ending their need for blood or transforming the curse. | Kayock’s meeting with Jesus; prophecy records; Anthony’s psychic nature. | Reveal that the prophecy has been interpreted through fear, power, or vampire politics.',
        'What did Kayock learn from Jesus? | Unresolved | Kayock, Jesus, Anthony | Kayock’s desert encounter should explain why he became a protector and what he believed about ending blood need. | Desert meeting; protector legacy; Kayock’s refusal to behave like other vampires. | Pay off as the spiritual/moral core of Kayock’s mission and Anthony’s inheritance.'
    ];
}
function parseMysteryLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=6)return {title:parts[0],status:parts[1],characters:parts[2],details:parts[3],clues:parts[4],payoff:parts.slice(5).join(' | ')};
    return {title:raw,status:'Unresolved',characters:'',details:'',clues:'',payoff:''};
}
function mysteryCardToLine(my){
    let title=(my.title||'Untitled Mystery').trim();
    let status=(my.status||'Unresolved').trim();
    let characters=(my.characters||'').trim();
    let details=(my.details||'').replace(/\r?\n/g,' ').trim();
    let clues=(my.clues||'').replace(/\r?\n/g,'; ').trim();
    let payoff=(my.payoff||'').replace(/\r?\n/g,' ').trim();
    return `${title} | ${status} | ${characters} | ${details} | ${clues} | ${payoff}`;
}
function syncMysteriesFromText(){
    if(!q('nfMysteries'))return;
    nfMysteryCards=(q('nfMysteries').value||'').split(/\r?\n/).map(parseMysteryLine).filter(Boolean);
}
function syncMysteriesToText(){
    q('nfMysteries').value=nfMysteryCards.map(mysteryCardToLine).join('\n');
    updateNovelCounts();
}
function mysteryBadgeClass(status){
    let s=String(status||'').toLowerCase();
    if(s.includes('solved'))return 'mystatus-solved';
    if(s.includes('red'))return 'mystatus-red';
    return 'mystatus-unresolved';
}
function renderMysteryCards(){
    if(!q('nfMysteryCards'))return;
    syncMysteriesToText();
    syncScenesToText();
    if(!nfMysteryCards.length){
        q('nfMysteryCards').innerHTML='No mysteries yet.';
        return;
    }
    q('nfMysteryCards').innerHTML=nfMysteryCards.map((my,i)=>`<div class=mysterycard><h4>🧩 ${esc(my.title||'Untitled Mystery')}</h4><span class="mystag ${mysteryBadgeClass(my.status)}">${esc(my.status||'Unresolved')}</span><span class=mystag>${esc(my.characters||'no characters')}</span><div class=mysdetails><b>Details:</b> ${esc(my.details||'None')}\n<b>Clues:</b> ${esc(my.clues||'None')}\n<b>Payoff:</b> ${esc(my.payoff||'None')}</div><div class=mysactions><button onclick="editMysteryCard(${i})">Edit</button><button onclick="moveMysteryCard(${i},-1)">Up</button><button onclick="moveMysteryCard(${i},1)">Down</button><button onclick="deleteMysteryCard(${i})">Delete</button><button onclick="sendMysteryCard(${i})">Send</button></div></div>`).join('');
}
function addMysteryCard(){
    let title=q('nfMysteryTitle').value.trim();
    if(!title){toast('Enter a mystery title before adding.');return}
    let my={
        title:title,
        status:q('nfMysteryStatus').value||'Unresolved',
        characters:q('nfMysteryCharacters').value.trim(),
        details:q('nfMysteryDetails').value.trim(),
        clues:q('nfMysteryClues').value.trim(),
        payoff:q('nfMysteryPayoff').value.trim()
    };
    nfMysteryCards.push(my);
    ['nfMysteryTitle','nfMysteryCharacters','nfMysteryDetails','nfMysteryClues','nfMysteryPayoff'].forEach(id=>q(id).value='');
    q('nfMysteryStatus').value='Unresolved';
    renderMysteryCards();
    toast('Mystery added.');
}
function editMysteryCard(i){
    let my=nfMysteryCards[i]; if(!my)return;
    q('nfMysteryTitle').value=my.title||'';
    q('nfMysteryStatus').value=my.status||'Unresolved';
    q('nfMysteryCharacters').value=my.characters||'';
    q('nfMysteryDetails').value=my.details||'';
    q('nfMysteryClues').value=my.clues||'';
    q('nfMysteryPayoff').value=my.payoff||'';
    nfMysteryCards.splice(i,1);
    renderMysteryCards();
    toast('Mystery loaded for editing. Update fields and Add Mystery when ready.');
}
function moveMysteryCard(i,delta){
    let j=i+delta;
    if(j<0||j>=nfMysteryCards.length)return;
    [nfMysteryCards[i],nfMysteryCards[j]]=[nfMysteryCards[j],nfMysteryCards[i]];
    renderMysteryCards();
}
function deleteMysteryCard(i){
    nfMysteryCards.splice(i,1);
    renderMysteryCards();
}
function sortMysteryCards(){
    const order={'Unresolved':0,'Clue planted':1,'Partially revealed':2,'Red herring':3,'Solved':4};
    nfMysteryCards.sort((a,b)=>(order[a.status]??9)-(order[b.status]??9)||String(a.title||'').localeCompare(String(b.title||'')));
    renderMysteryCards();
    toast('Mysteries sorted.');
}
function restoreSlippingMysteries(){
    q('nfMysteries').value=slippingMysteryLines().join('\n');
    syncMysteriesFromText();
    renderMysteryCards();
    updateNovelCounts();
    updateCodexDashboard();
    toast('Slipping into Darkness mysteries restored.');
}
function mysteryCardsText(){
    syncMysteriesFromText();
    return nfMysteryCards.map((my,i)=>`${i+1}. ${my.title||'Untitled Mystery'}\nStatus: ${my.status||'Unresolved'}\nCharacters: ${my.characters||'None'}\nDetails: ${my.details||'None'}\nClues: ${my.clues||'None'}\nPayoff Plan: ${my.payoff||'None'}`).join('\n\n')||'No mysteries.';
}
function sendMysteryCard(i){
    let my=nfMysteryCards[i]; if(!my)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge mystery thread.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Mystery: ${my.title||'Untitled Mystery'}
Status: ${my.status||'Unresolved'}
Related Characters: ${my.characters||'None'}
Details: ${my.details||'None'}
Clues: ${my.clues||'None'}
Payoff Plan: ${my.payoff||'None'}

Please strengthen this mystery, suggest clues, identify payoff risks, and connect it to the larger story arc.`;
    toast('Mystery sent to Mission Console input.');
}
function checkMysteryPayoff(){
    syncMysteriesToText();
    syncScenesToText();
    go('mission');
    q('input').value=`You are Novel Forge's mystery payoff engine.

Analyze these mystery threads for weak setup, missing clues, unresolved promises, premature reveals, red herring risks, and payoff opportunities.

Return your answer in this exact structure:

1. Mystery System Summary
2. Strongest Mystery Threads
3. Weakest / Vaguest Mysteries
4. Missing Clues
5. Payoff Risks
6. Red Herring Opportunities
7. Character Connections
8. Recommended Reveal Order
9. Best Next Mystery Scene

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Characters:
${characterCardsText()}

Timeline:
${timelineManagerText()}

Mysteries:
${mysteryCardsText()}`;
    toast('Mystery payoff check sent to Mission Console input.');
}

let nfCharacterCards=[];

function slippingCharacterLines(){
    return [
        'Anthony / Whisper | Protagonist / Psychic Hunter | Alive / Cursed | Main hero with psychic and telepathic gifts, drawn into a vampire prophecy that may end the need for blood. | Anthony, Whisper, prophecy, Book 1, psychic',
        'Kayock | First Vampire / Ancient Protector | Dead / Legacy Active | Ancient hunter and first vampire, later protector figure; his death at Jokaya’s hands becomes a central wound in Book 1. | Kayock, first vampire, Jesus, prophecy, protector',
        'Jokaya | Antagonist / Ancient Queen | Active Threat | Ancient Native queen and powerful vampire antagonist who kills Kayock and forces Anthony into the center of the prophecy. | Jokaya, queen, Book 1, antagonist',
        'Chee | Mysterious Vampire / Survivor Figure | Unknown / Ambiguous | Chinese vampire connected to Anthony’s turning, survival, and the unclear boundary between hunter and vampire. | Chee, turning, survival, Anthony',
        'Croatoan | Imp Vampire / Escaped Threat | Imprisoned Then Escaped | Child or legacy of Kayock tied to Roanoke, ancient prisons, and the mystery of escape in Book 2. | Croatoan, Roanoke, prison, Book 2',
        'Ishtar | Ancient Vampire Power Figure | Unknown | Ancient power figure in the vampire mythology; needs clearer motive and relation to prophecy. | Ishtar, ancient vampire, mythology',
        'Thoth | Ancient Knowledge Figure | Unknown | Knowledge-linked ancient figure who may connect prophecy records, skulls, and hidden vampire history. | Thoth, knowledge, prophecy, records',
        'Baal | Demonic / Vampiric Threat | Threat / To Be Clarified | Ancient demonic or vampiric threat; should be reconciled carefully with vampire rules and Pueblo tunnel lore. | Baal, demon, vampire, threat',
        'Beowulf | Protector Champion | Legacy / Mythic Ally | Champion figure connected to protector mythology and possible vampire-hunter lineage. | Beowulf, protector, champion',
        'Yactazini | First Hunter Priest | Ancient Legacy | First hunter priest, likely tied to early anti-vampire traditions and prophecy interpretation. | Yactazini, hunter, priest, ancient'
    ];
}
function restoreSlippingCharacters(){
    q('nfCharacters').value=slippingCharacterLines().join('\n');
    syncCharactersFromText();
    renderCharacterCards();
    updateNovelCounts();
    updateCodexDashboard();
    toast('Slipping into Darkness character cards restored.');
}

function parseCharacterLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=5)return {name:parts[0],role:parts[1],status:parts[2],details:parts[3],tags:parts.slice(4).join(' | ')};
    let m=raw.match(/^(.+?)\s+-\s+(.*)$/);
    if(m)return {name:m[1].trim(),role:m[2].trim(),status:'',details:'',tags:''};
    return {name:raw,role:'',status:'',details:'',tags:''};
}
function characterCardToLine(ch){
    let name=(ch.name||'Unnamed Character').trim();
    let role=(ch.role||'').trim();
    let status=(ch.status||'').trim();
    let details=(ch.details||'').replace(/\r?\n/g,' ').trim();
    let tags=(ch.tags||'').trim();
    return `${name} | ${role} | ${status} | ${details} | ${tags}`;
}
function syncCharactersFromText(){
    if(!q('nfCharacters'))return;
    nfCharacterCards=(q('nfCharacters').value||'').split(/\r?\n/).map(parseCharacterLine).filter(Boolean);
}
function syncCharactersToText(){
    q('nfCharacters').value=nfCharacterCards.map(characterCardToLine).join('\n');
    updateNovelCounts();
}
function renderCharacterCards(){
    if(!q('nfCharacterCards'))return;
    syncCharactersToText();
    if(!nfCharacterCards.length){
        q('nfCharacterCards').innerHTML='No character cards yet.';
        return;
    }
    q('nfCharacterCards').innerHTML=nfCharacterCards.map((ch,i)=>`<div class=charcard><h4>🧍 ${esc(ch.name||'Unnamed Character')}</h4><span class=chartag>${esc(ch.role||'role unknown')}</span><span class=chartag>${esc(ch.status||'status unknown')}</span><span class=chartag>${esc(ch.tags||'no tags')}</span><div class=chardetails>${esc(ch.details||'')}</div><div class=charactions><button onclick="editCharacterCard(${i})">Edit</button><button onclick="moveCharacterCard(${i},-1)">Up</button><button onclick="moveCharacterCard(${i},1)">Down</button><button onclick="deleteCharacterCard(${i})">Delete</button><button onclick="sendCharacterCard(${i})">Send</button></div></div>`).join('');
}
function addCharacterCard(){
    let name=q('nfCharName').value.trim();
    if(!name){
        toast('Enter a character name before adding a character.');
        return;
    }
    let ch={
        name:name,
        role:q('nfCharRole').value.trim(),
        status:q('nfCharStatus').value.trim(),
        details:q('nfCharDetails').value.trim(),
        tags:q('nfCharTags').value.trim()
    };
    nfCharacterCards.push(ch);
    ['nfCharName','nfCharRole','nfCharStatus','nfCharDetails','nfCharTags'].forEach(id=>q(id).value='');
    renderCharacterCards();
    toast('Character added.');
}
function editCharacterCard(i){
    let ch=nfCharacterCards[i]; if(!ch)return;
    q('nfCharName').value=ch.name||'';
    q('nfCharRole').value=ch.role||'';
    q('nfCharStatus').value=ch.status||'';
    q('nfCharDetails').value=ch.details||'';
    q('nfCharTags').value=ch.tags||'';
    nfCharacterCards.splice(i,1);
    renderCharacterCards();
    toast('Character loaded for editing. Update fields and Add Character when ready.');
}
function moveCharacterCard(i,delta){
    let j=i+delta;
    if(j<0||j>=nfCharacterCards.length)return;
    [nfCharacterCards[i],nfCharacterCards[j]]=[nfCharacterCards[j],nfCharacterCards[i]];
    renderCharacterCards();
}
function deleteCharacterCard(i){
    nfCharacterCards.splice(i,1);
    renderCharacterCards();
}
function sortCharacterCards(){
    nfCharacterCards.sort((a,b)=>String(a.name||'').localeCompare(String(b.name||'')));
    renderCharacterCards();
    toast('Characters sorted.');
}
function characterCardsText(){
    syncCharactersFromText();
    return nfCharacterCards.map((ch,i)=>`${i+1}. ${ch.name||'Unnamed Character'}\nRole: ${ch.role||'Unknown'}\nStatus: ${ch.status||'Unknown'}\nDetails: ${ch.details||'None'}\nTags: ${ch.tags||'None'}`).join('\n\n')||'No character cards.';
}
function sendCharacterCard(i){
    let ch=nfCharacterCards[i]; if(!ch)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge character.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Character: ${ch.name||'Unnamed Character'}
Role: ${ch.role||'Unknown'}
Status: ${ch.status||'Unknown'}
Details: ${ch.details||'None'}
Tags: ${ch.tags||'None'}

Please develop this character, identify continuity implications, strengthen motivation, and suggest how they should affect the plot.`;
    toast('Character sent to Mission Console input.');
}

function upgradeSimpleCharacterCards(){
    syncCharactersFromText();
    if(!nfCharacterCards.length){restoreSlippingCharacters();return;}
    const known={
        'Anthony / Whisper':{role:'Protagonist / Psychic Hunter',status:'Alive / Cursed',details:'Main hero with psychic and telepathic gifts, drawn into a vampire prophecy that may end the need for blood.',tags:'Anthony, Whisper, prophecy, Book 1, psychic'},
        'Kayock':{role:'First Vampire / Ancient Protector',status:'Dead / Legacy Active',details:'Ancient hunter and first vampire, later protector figure; his death at Jokaya’s hands becomes a central wound in Book 1.',tags:'Kayock, first vampire, Jesus, prophecy, protector'},
        'Jokaya':{role:'Antagonist / Ancient Queen',status:'Active Threat',details:'Ancient Native queen and powerful vampire antagonist who kills Kayock and forces Anthony into the center of the prophecy.',tags:'Jokaya, queen, Book 1, antagonist'},
        'Chee':{role:'Mysterious Vampire / Survivor Figure',status:'Unknown / Ambiguous',details:'Chinese vampire connected to Anthony’s turning, survival, and the unclear boundary between hunter and vampire.',tags:'Chee, turning, survival, Anthony'},
        'Croatoan':{role:'Imp Vampire / Escaped Threat',status:'Imprisoned Then Escaped',details:'Child or legacy of Kayock tied to Roanoke, ancient prisons, and the mystery of escape in Book 2.',tags:'Croatoan, Roanoke, prison, Book 2'},
        'Ishtar':{role:'Ancient Vampire Power Figure',status:'Unknown',details:'Ancient power figure in the vampire mythology; needs clearer motive and relation to prophecy.',tags:'Ishtar, ancient vampire, mythology'},
        'Thoth':{role:'Ancient Knowledge Figure',status:'Unknown',details:'Knowledge-linked ancient figure who may connect prophecy records, skulls, and hidden vampire history.',tags:'Thoth, knowledge, prophecy, records'},
        'Baal':{role:'Demonic / Vampiric Threat',status:'Threat / To Be Clarified',details:'Ancient demonic or vampiric threat; should be reconciled carefully with vampire rules and Pueblo tunnel lore.',tags:'Baal, demon, vampire, threat'},
        'Beowulf':{role:'Protector Champion',status:'Legacy / Mythic Ally',details:'Champion figure connected to protector mythology and possible vampire-hunter lineage.',tags:'Beowulf, protector, champion'},
        'Yactazini':{role:'First Hunter Priest',status:'Ancient Legacy',details:'First hunter priest, likely tied to early anti-vampire traditions and prophecy interpretation.',tags:'Yactazini, hunter, priest, ancient'}
    };
    nfCharacterCards=nfCharacterCards.map(ch=>{
        let key=Object.keys(known).find(k=>String(ch.name||'').toLowerCase()===k.toLowerCase());
        if(!key)return ch;
        let k=known[key];
        return {
            name:ch.name||key,
            role:(ch.role&&ch.role!=='')?ch.role:k.role,
            status:(ch.status&&ch.status!=='')?ch.status:k.status,
            details:(ch.details&&ch.details!=='')?ch.details:k.details,
            tags:(ch.tags&&ch.tags!=='')?ch.tags:k.tags
        };
    });
    renderCharacterCards();
    toast('Simple character cards upgraded.');
}

function checkCharacterArcs(){
    syncCharactersToText();
    go('mission');
    q('input').value=`You are Novel Forge's character arc engine.

Analyze these character cards for unclear motivations, missing relationships, weak arcs, contradictions, underused characters, and opportunities for stronger emotional payoff.

Return your answer in this exact structure:

1. Character Arc Summary
2. Strongest Characters
3. Weakest / Least Defined Characters
4. Motivation Problems
5. Relationship Opportunities
6. Character Continuity Risks
7. Suggested Arc Improvements
8. Best Next Character Scene

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Characters:
${characterCardsText()}

Timeline:
${timelineManagerText()}

Mysteries:
${q('nfMysteries').value||'None'}`;
    toast('Character arc check sent to Mission Console input.');
}

let nfTimelineEvents=[];
function parseTimelineLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=4)return {era:parts[0],title:parts[1],details:parts[2],tags:parts.slice(3).join(' | ')};
    let m=raw.match(/^([^:]+):\s*(.*)$/);
    if(m)return {era:m[1].trim(),title:m[2].trim(),details:'',tags:''};
    return {era:'Unsorted',title:raw,details:'',tags:''};
}
function timelineEventToLine(ev){
    let era=(ev.era||'Unsorted').trim();
    let title=(ev.title||'Untitled Event').trim();
    let details=(ev.details||'').replace(/\r?\n/g,' ').trim();
    let tags=(ev.tags||'').trim();
    return `${era} | ${title} | ${details} | ${tags}`;
}
function syncTimelineFromText(){
    if(!q('nfTimeline'))return;
    nfTimelineEvents=(q('nfTimeline').value||'').split(/\r?\n/).map(parseTimelineLine).filter(Boolean);
}
function syncTimelineToText(){
    q('nfTimeline').value=nfTimelineEvents.map(timelineEventToLine).join('\n');
    updateNovelCounts();
}
function renderTimelineEvents(){
    if(!q('nfTimelineList'))return;
    syncTimelineToText();
    if(!nfTimelineEvents.length){
        q('nfTimelineList').innerHTML='No timeline events yet.';
        return;
    }
    q('nfTimelineList').innerHTML=nfTimelineEvents.map((ev,i)=>`<div class=tmevent><h4>${esc(ev.era||'Unsorted')} — ${esc(ev.title||'Untitled Event')}</h4><span class=tmtag>${esc(ev.tags||'no tags')}</span><div class=tmdetails>${esc(ev.details||'')}</div><div class=tmactions><button onclick="editTimelineEvent(${i})">Edit</button><button onclick="moveTimelineEvent(${i},-1)">Up</button><button onclick="moveTimelineEvent(${i},1)">Down</button><button onclick="deleteTimelineEvent(${i})">Delete</button><button onclick="sendSingleTimelineEvent(${i})">Send</button></div></div>`).join('');
}
function addTimelineEvent(){
    let ev={
        era:q('nfEventEra').value.trim()||'Unsorted',
        title:q('nfEventTitle').value.trim()||'Untitled Event',
        details:q('nfEventDetails').value.trim(),
        tags:q('nfEventTags').value.trim()
    };
    nfTimelineEvents.push(ev);
    ['nfEventEra','nfEventTitle','nfEventDetails','nfEventTags'].forEach(id=>q(id).value='');
    renderTimelineEvents();
    toast('Timeline event added.');
}
function editTimelineEvent(i){
    let ev=nfTimelineEvents[i]; if(!ev)return;
    q('nfEventEra').value=ev.era||'';
    q('nfEventTitle').value=ev.title||'';
    q('nfEventDetails').value=ev.details||'';
    q('nfEventTags').value=ev.tags||'';
    nfTimelineEvents.splice(i,1);
    renderTimelineEvents();
    toast('Event loaded for editing. Update fields and Add Event when ready.');
}
function moveTimelineEvent(i,delta){
    let j=i+delta;
    if(j<0||j>=nfTimelineEvents.length)return;
    [nfTimelineEvents[i],nfTimelineEvents[j]]=[nfTimelineEvents[j],nfTimelineEvents[i]];
    renderTimelineEvents();
}
function deleteTimelineEvent(i){
    nfTimelineEvents.splice(i,1);
    renderTimelineEvents();
}
function sortTimelineEvents(){
    nfTimelineEvents.sort((a,b)=>String(a.era||'').localeCompare(String(b.era||''))||String(a.title||'').localeCompare(String(b.title||'')));
    renderTimelineEvents();
    toast('Timeline sorted.');
}
function timelineManagerText(){
    syncTimelineFromText();
    return nfTimelineEvents.map((ev,i)=>`${i+1}. [${ev.era||'Unsorted'}] ${ev.title||'Untitled Event'}\nDetails: ${ev.details||'None'}\nTags: ${ev.tags||'None'}`).join('\n\n')||'No timeline events.';
}
function sendTimelineManager(){
    go('mission');
    q('input').value=`You are helping with Novel Forge timeline management.

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Please review this timeline for order, continuity, missing causality, contradictions, and next-step story opportunities.

Timeline:
${timelineManagerText()}`;
    toast('Timeline sent to Mission Console input.');
}
function sendSingleTimelineEvent(i){
    let ev=nfTimelineEvents[i]; if(!ev)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge timeline event.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Era/Book: ${ev.era||'Unsorted'}
Event: ${ev.title||'Untitled Event'}
Details: ${ev.details||'None'}
Tags: ${ev.tags||'None'}

Please help develop this event, identify continuity implications, and suggest what should happen before or after it.`;
    toast('Timeline event sent to Mission Console input.');
}

function nfLines(id){return (q(id)?.value||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean)}
function updateNovelCounts(){
    if(!q('nfCounts'))return;
    let c=nfLines('nfCharacters').length,l=nfLines('nfLocations').length,a=nfLines('nfArtifacts').length,t=nfLines('nfTimeline').length,m=nfLines('nfMysteries').length;
    q('nfCounts').innerHTML=`<span class=nfcount>${c} characters</span><span class=nfcount>${l} locations</span><span class=nfcount>${a} artifacts</span><span class=nfcount>${t} timeline</span><span class=nfcount>${m} mysteries</span>`;
    if(q('nfDashboard'))setTimeout(updateCodexDashboard,0);
}
async function loadNovelForgeList(){
    if(!q('nfList'))return;
    try{
        let d=await (await fetch('/api/novelforge/list')).json();
        if(!d.universes?.length){
            q('nfList').innerHTML='No saved universes yet.';
            return;
        }
        q('nfList').innerHTML=d.universes.map(u=>`<div class=nfitem><h4>📖 ${esc(u.universe)}</h4><span class=nftag>${u.characters} characters</span><span class=nftag>${u.locations} locations</span><span class=nftag>${u.artifacts} artifacts</span><span class=nftag>${u.timeline} timeline</span><span class=nftag>${u.mysteries} mysteries</span><div class=time>${esc(u.modified)}</div><div class=nfpreview>${esc(u.premise||'')}</div><div class=nfactions><button onclick="openNovelForge('${js(u.name)}')">Load</button><button onclick="duplicateNovelForge('${js(u.name)}')">Duplicate</button><button onclick="renameNovelForge('${js(u.name)}')">Rename</button><button onclick="deleteNovelForge('${js(u.name)}')">Delete</button></div></div>`).join('');
    }catch(e){
        q('nfList').textContent='Novel Forge list unavailable: '+e;
    }
}
async function openNovelForge(name){
    let d=await (await fetch('/api/novelforge/read?name='+encodeURIComponent(name))).json();
    if(!d.ok){toast(d.message||'Universe not found.');return}
    activeUniverseName=d.file_name||name;
    q('nfUniverse').value=d.universe||'';
    q('nfPremise').value=d.premise||'';
    q('nfCharacters').value=(d.characters||[]).join('\n');syncCharactersFromText();renderCharacterCards();
    q('nfLocations').value=(d.locations||[]).join('\n');syncLocationsFromText();renderLocationCards();
    q('nfArtifacts').value=(d.artifacts||[]).join('\n');syncArtifactsFromText();renderArtifactCards();
    q('nfTimeline').value=(d.timeline||[]).join('\n');syncTimelineFromText();renderTimelineEvents();
    q('nfMysteries').value=(d.mysteries||[]).join('\n');syncMysteriesFromText();renderMysteryCards();q('nfScenes').value=(d.scenes||[]).join('\n');syncScenesFromText();renderSceneCards();
    q('nfNotes').value=d.notes||'';
    q('nfStatus').textContent=`Loaded universe: ${d.universe||name}`;
    updateNovelCounts();
    updateCodexDashboard();
    toast('Universe loaded.');
}
async function saveNovelForge(){
    syncCharactersToText();
    syncLocationsToText();
    syncArtifactsToText();
    syncTimelineToText();
    syncMysteriesToText();
    let payload={
        universe:q('nfUniverse').value.trim()||'Untitled Universe',
        premise:q('nfPremise').value,
        characters:q('nfCharacters').value,
        locations:q('nfLocations').value,
        artifacts:q('nfArtifacts').value,
        timeline:q('nfTimeline').value,
        mysteries:q('nfMysteries').value,
        scenes:q('nfScenes').value,
        notes:q('nfNotes').value
    };
    let d=await api('/api/novelforge/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(d?.ok){
        activeUniverseName=d.name;
        q('nfStatus').textContent=d.message;
        updateNovelCounts();
        updateCodexDashboard();
        loadNovelForgeList();
    }
}
async function duplicateNovelForge(name){
    let new_title=prompt('Duplicate universe as:', name+' Copy');
    if(!new_title)return;
    let d=await api('/api/novelforge/duplicate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,new_title})});
    if(d?.ok)loadNovelForgeList();
}
async function renameNovelForge(name){
    let new_title=prompt('Rename universe to:', name);
    if(!new_title)return;
    let d=await api('/api/novelforge/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,new_title})});
    if(d?.ok)loadNovelForgeList();
}
async function deleteNovelForge(name){
    if(!confirm('Delete this Novel Forge universe?'))return;
    let d=await api('/api/novelforge/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    if(d?.ok){
        if(activeUniverseName===name)clearNovelForge();
        loadNovelForgeList();
    }
}
function novelForgeContext(){
    syncCharactersToText();
    syncLocationsToText();
    syncArtifactsToText();
    syncTimelineToText();
    syncMysteriesToText();
    return `Novel Forge Codex Context

Universe:
${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Characters:
${q('nfCharacters').value||'None'}

Locations:
${q('nfLocations').value||'None'}

Artifacts:
${q('nfArtifacts').value||'None'}

Timeline:
${q('nfTimeline').value||'None'}

Mysteries / Unresolved Threads:
${q('nfMysteries').value||'None'}

Scenes:
${q('nfScenes')?.value||'None'}

Notes:
${q('nfNotes').value||'None'}`;
}
function novelForgeSectionText(section){
    const map={
        premise:['Premise',q('nfPremise').value],
        characters:['Characters',characterCardsText()],
        locations:['Locations',locationCardsText()],
        artifacts:['Artifacts',artifactCardsText()],
        timeline:['Timeline',timelineManagerText()],
        mysteries:['Mysteries / Unresolved Threads',mysteryCardsText()],
        notes:['Notes',q('nfNotes').value]
    };
    if(section==='full')return novelForgeContext();
    let item=map[section]||['Codex',novelForgeContext()];
    return `Novel Forge Section

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Section: ${item[0]}

${item[1]||'None'}`;
}


function codexCounts(){
    return {
        universe:(q('nfUniverse')?.value||'Untitled Universe').trim()||'Untitled Universe',
        characters:nfLines('nfCharacters').length,
        locations:nfLines('nfLocations').length,
        artifacts:nfLines('nfArtifacts').length,
        timeline:nfLines('nfTimeline').length,
        mysteries:nfLines('nfMysteries').length,
        scenes:nfLines('nfScenes').length,
        notes:(q('nfNotes')?.value||'').trim().length
    };
}
function codexReadiness(c){
    let issues=[];
    if(!q('nfPremise')?.value.trim())issues.push('Premise missing');
    if(c.characters<3)issues.push('Few characters');
    if(c.locations<2)issues.push('Few locations');
    if(c.artifacts<1)issues.push('No artifacts');
    if(c.timeline<3)issues.push('Short timeline');
    if(c.mysteries<1)issues.push('No mystery threads');
    if(c.scenes<1)issues.push('No scene briefs');
    if(!issues.length)return 'Codex has enough structure for continuity, arc, and scene planning.';
    return 'Needs attention: '+issues.join(', ');
}
function updateCodexDashboard(){
    if(!q('nfDashboard'))return;
    try{
        syncCharactersToText();
        syncLocationsToText();
        syncArtifactsToText();
        syncTimelineToText();
        syncMysteriesToText();
    }catch(e){}
    let c=codexCounts();
    q('nfDashboard').innerHTML=`<div class=codexdash>
        <div class=codexbox><div class=label>Universe</div><div class=value>${esc(c.universe)}</div></div>
        <div class=codexbox><div class=label>Characters</div><div class=value>${c.characters}</div></div>
        <div class=codexbox><div class=label>Locations</div><div class=value>${c.locations}</div></div>
        <div class=codexbox><div class=label>Artifacts</div><div class=value>${c.artifacts}</div></div>
        <div class=codexbox><div class=label>Timeline</div><div class=value>${c.timeline}</div></div>
        <div class=codexbox><div class=label>Mysteries</div><div class=value>${c.mysteries}</div></div>
        <div class=codexbox><div class=label>Scenes</div><div class=value>${c.scenes}</div></div>
    </div><div class=readiness><div class=time>Story Readiness</div>${esc(codexReadiness(c))}</div>`;
}
function completeStoryBibleText(){
    return `Novel Forge Complete Story Bible

${novelForgeContext()}

Structured Character Cards:
${characterCardsText()}

Structured Locations:
${locationCardsText()}

Structured Artifacts:
${artifactCardsText()}

Structured Timeline:
${timelineManagerText()}

Structured Mysteries:
${mysteryCardsText()}

Structured Scenes:
${sceneCardsText()}`;
}

function storyBiblePayload(){
    syncCharactersToText();
    syncLocationsToText();
    syncArtifactsToText();
    syncTimelineToText();
    syncMysteriesToText();
    let c=codexCounts();
    return {
        universe:c.universe,
        summary:{
            characters:c.characters,
            locations:c.locations,
            artifacts:c.artifacts,
            timeline:c.timeline,
            mysteries:c.mysteries,
            readiness:codexReadiness(c)
        },
        codex:{
            premise:q('nfPremise').value||'',
            characters:q('nfCharacters').value||'',
            locations:q('nfLocations').value||'',
            artifacts:q('nfArtifacts').value||'',
            timeline:q('nfTimeline').value||'',
            mysteries:q('nfMysteries').value||'',
            notes:q('nfNotes').value||'',
            scenes:q('nfScenes')?.value||''
        },
        story_bible:completeStoryBibleText()
    };
}
async function exportStoryBible(){
    if(q('nfExportStatus'))q('nfExportStatus').textContent='Exporting Story Bible...';
    let d=await api('/api/novelforge/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(storyBiblePayload())});
    if(d?.ok){
        if(q('nfExportStatus'))q('nfExportStatus').innerHTML=`${esc(d.message)}
Markdown: ${esc(d.markdown)}
Text: ${esc(d.text)}
JSON: ${esc(d.json)}

<button onclick="sendExportedBiblePath('${js(d.markdown)}')">Send Markdown Path to Mission Console</button>`;
        toast('Story Bible exported.');
    }
}
function sendExportedBiblePath(path){
    go('mission');
    q('input').value=`Please help me with this exported Novel Forge Story Bible:
${path}

Use it as the current story reference.`;
    toast('Exported Story Bible path sent to Mission Console.');
}

function sendCompleteStoryBible(){
    go('mission');
    q('input').value=`You are helping with a full Novel Forge story bible.

Use the complete story bible below to help plan, check continuity, develop arcs, organize canon, and suggest the best next writing step.

Please respond in this structure:

1. Story Bible Summary
2. Strongest Existing Elements
3. Weakest / Least Developed Elements
4. Biggest Continuity Risks
5. Best Development Opportunities
6. Recommended Next Build Step
7. Recommended Next Writing Step

${completeStoryBibleText()}`;
    toast('Complete Story Bible sent to Mission Console input.');
}

function checkNovelContinuity(){
    syncTimelineToText();
    go('mission');
    q('input').value=`You are Novel Forge's continuity engine.

Analyze this Codex for story continuity, canon problems, timeline logic, missing causes, character contradictions, unresolved setup/payoff issues, and risks to reader clarity.

Return your answer in this exact structure:

1. Continuity Pass Summary
2. Major Contradictions
3. Timeline Problems
4. Character Logic Problems
5. Missing Causes / Weak Motivations
6. Unresolved Mystery Setup
7. Canon Risks
8. Suggested Fixes
9. Best Next Writing Step

Codex:
${novelForgeContext()}`;
    toast('Continuity check sent to Mission Console input.');
}
function buildNextStoryArc(){
    syncTimelineToText();
    go('mission');
    q('input').value=`You are Novel Forge's story-arc planner.

Using this Codex, propose the next story arc while preserving canon and honoring unresolved mysteries.

Return your answer in this exact structure:

1. Recommended Next Arc
2. Why This Arc Fits
3. Required Setup
4. Key Scenes
5. Character Changes
6. Mystery Payoff / New Mystery
7. Timeline Placement
8. Continuity Risks
9. First Scene Draft Seed

Codex:
${novelForgeContext()}`;
    toast('Next arc request sent to Mission Console input.');
}

function sendNovelForgeContext(){
    go('mission');
    q('input').value=`You are helping with a Novel Forge universe. Use this codex context to help me plan, check continuity, suggest next steps, or develop the story.

${novelForgeContext()}`;
    toast('Novel Forge Codex sent to Mission Console input.');
}
function sendNovelForgeSection(){
    let section=q('nfSection')?.value||'full';
    go('mission');
    q('input').value=`You are helping with Novel Forge. Use this selected codex section to help me develop, improve, or check continuity.

${novelForgeSectionText(section)}`;
    toast('Novel Forge section sent to Mission Console input.');
}
function clearNovelForge(){
    activeUniverseName=null;
    ['nfUniverse','nfPremise','nfCharacters','nfLocations','nfArtifacts','nfTimeline','nfMysteries','nfScenes','nfNotes'].forEach(id=>q(id).value='');
    q('nfStatus').textContent='New universe.';
    nfCharacterCards=[];renderCharacterCards();
    nfLocationCards=[];renderLocationCards();
    nfArtifactCards=[];renderArtifactCards();
    nfTimelineEvents=[];renderTimelineEvents();
    nfMysteryCards=[];renderMysteryCards();
    nfSceneCards=[];renderSceneCards();
    updateNovelCounts();
}
function loadSlippingTemplate(){
    q('nfUniverse').value='Slipping into Darkness';
    q('nfPremise').value='An ancient vampire mythology universe centered on Kayock, the first vampire and ancient protector, and Anthony / Whisper, a psychic hunter drawn into a prophecy that could end the need for blood.';
    q('nfCharacters').value=slippingCharacterLines().join('\n');
    q('nfLocations').value=slippingLocationLines().join('\n');
    q('nfArtifacts').value=slippingArtifactLines().join('\n');
    q('nfTimeline').value=[
        'Book 1: Anthony learns the prophecy',
        'Book 1: Kayock dies at Jokaya’s hands',
        'Book 1: Anthony stops Jokaya',
        'Book 1: Anthony learns his ex has been turned',
        'Book 2: Hunt the ex and learn who she has become',
        'Book 2: Discover Jokaya’s sanctuary',
        'Book 2: Follow clues to Olmec pyramids',
        'Book 2: Learn Croatoan escaped'
    ].join('\n');
    q('nfMysteries').value=slippingMysteryLines().join('\n');
    q('nfNotes').value='Flagship Novel Forge demonstration universe. Track canon carefully. Separate author knowledge from reader knowledge in future versions.';
    syncCharactersFromText();renderCharacterCards();syncLocationsFromText();renderLocationCards();syncArtifactsFromText();renderArtifactCards();syncTimelineFromText();renderTimelineEvents();syncMysteriesFromText();renderMysteryCards();q('nfScenes').value=starterSceneLines().join('\n');syncScenesFromText();renderSceneCards();updateNovelCounts();
    updateCodexDashboard();
    toast('Slipping into Darkness template loaded.');
}

let activePromptName=null;
let promptCache=[];
async function loadPrompts(){
    try{
        let d=await (await fetch('/api/prompts/list')).json();
        promptCache=d.prompts||[];
        renderPromptList();
    }catch(e){
        if(q('promptList'))q('promptList').textContent='Prompt list unavailable: '+e;
    }
}
function renderPromptList(){
    if(!q('promptList'))return;
    let term=(q('promptSearch')?.value||'').toLowerCase();
    let cat=(q('promptFilter')?.value||'All');
    let items=promptCache.filter(p=>{
        let hay=[p.title,p.category,p.prompt_type,p.notes,p.preview].join(' ').toLowerCase();
        return (!term||hay.includes(term))&&(cat==='All'||p.category===cat);
    });
    if(!items.length){q('promptList').innerHTML='No matching prompts.';return}
    q('promptList').innerHTML=items.map(p=>`<div class=promptitem><h4>${esc(p.title)}</h4><span class=prompttag>${esc(p.category||'General')}</span><span class=prompttag>${esc(p.prompt_type||'User Prompt')}</span><div class=time>${esc(p.modified)}</div><div class=promptpreview>${esc(p.preview||'')}</div><div class=promptactions><button onclick="openPromptSmith('${js(p.name)}')">Load</button><button onclick="duplicatePromptSmith('${js(p.name)}')">Duplicate</button><button onclick="renamePromptSmith('${js(p.name)}')">Rename</button><button onclick="deletePromptSmith('${js(p.name)}')">Delete</button></div></div>`).join('');
}
async function openPromptSmith(name){
    let d=await (await fetch('/api/prompts/read?name='+encodeURIComponent(name))).json();
    if(!d.ok){toast(d.message||'Prompt not found.');return}
    activePromptName=d.name;
    q('promptTitle').value=d.title||d.name||'';
    q('promptCategory').value=d.category||'General';
    q('promptType').value=d.prompt_type||'User Prompt';
    q('promptNotes').value=d.notes||'';
    q('promptDraft').value=d.prompt||d.body||'';
    q('promptSaveStatus').textContent=`Loaded: ${d.title||d.name}`;
    toast('Prompt loaded.');
}
async function savePromptSmith(){
    let title=q('promptTitle').value.trim()||'Untitled Prompt';
    let category=q('promptCategory').value||'General';
    let prompt_type=q('promptType').value||'User Prompt';
    let notes=q('promptNotes').value;
    let prompt=q('promptDraft').value;
    let d=await api('/api/prompts/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,category,prompt_type,notes,prompt})});
    if(d?.ok){
        activePromptName=d.name;
        q('promptSaveStatus').textContent=d.message;
        loadPrompts();
    }
}
async function duplicatePromptSmith(name){
    let new_title=prompt('Duplicate prompt as:', name+' Copy');
    if(!new_title)return;
    let d=await api('/api/prompts/duplicate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,new_title})});
    if(d?.ok)loadPrompts();
}
async function renamePromptSmith(name){
    let new_title=prompt('Rename prompt to:', name);
    if(!new_title)return;
    let d=await api('/api/prompts/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,new_title})});
    if(d?.ok)loadPrompts();
}
async function deletePromptSmith(name){
    if(!confirm('Delete this saved prompt?'))return;
    let d=await api('/api/prompts/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    if(d?.ok){
        if(activePromptName===name)clearPromptSmith();
        loadPrompts();
    }
}
function copyPromptSmith(){
    let text=q('promptDraft').value;
    navigator.clipboard?.writeText(text);
    toast('Prompt copied.');
}
function promptSmithContext(){
    return `PromptSmith Context
Title: ${q('promptTitle').value||'Untitled'}
Category: ${q('promptCategory').value||'General'}
Type: ${q('promptType').value||'User Prompt'}
Notes: ${q('promptNotes').value||'None'}

Prompt:
${q('promptDraft').value}`;
}
function sendPromptSmith(){
    let text=q('promptDraft').value.trim();
    if(!text){toast('Prompt is empty.');return}
    go('mission');
    q('input').value=text;
    toast('Prompt sent to Mission Console input.');
}
function sendPromptSmithWithContext(){
    let text=q('promptDraft').value.trim();
    if(!text){toast('Prompt is empty.');return}
    go('mission');
    q('input').value=promptSmithContext();
    toast('Prompt with context sent to Mission Console input.');
}
function clearPromptSmith(){
    activePromptName=null;
    q('promptTitle').value='';
    q('promptCategory').value='General';
    q('promptType').value='User Prompt';
    q('promptNotes').value='';
    q('promptDraft').value='';
    q('promptSaveStatus').textContent='New prompt.';
}



async function exportExtensionReport(){
    let d=await api('/api/extensions/report');
    if(d?.ok){
        q('extSummary').textContent=`${d.message}
Modules: ${d.summary.count}
Enabled: ${d.summary.enabled}
Valid: ${d.summary.valid}
Problems: ${d.summary.problems}
Markdown: ${d.markdown}
JSON: ${d.json}`;
        q('extRepair').innerHTML=`<b>Report exported.</b>
<div class=repairbox>Markdown: ${esc(d.markdown)}
JSON: ${esc(d.json)}
Folder: ${esc(d.folder)}</div>
<button onclick="sendExtensionReportPath('${js(d.markdown)}')">Send Report Path to Mission Console</button>`;
        window.extLastReport=d.markdown;
        loadExtensions();
        toast('Extension report exported.');
    }
}
function sendExtensionReportPath(path){
    go('mission');
    q('input').value=`Please review this Kayock Extension Report and recommend fixes or architecture improvements:

${path}`;
    toast('Extension report path sent to Mission Console input.');
}
async function suggestManifestFix(key,manifest){
    let d=await api('/api/extensions/repair_suggest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,manifest})});
    if(d?.ok){
        window.extLastManifest=d.manifest;
        window.extLastSuggested=d.suggested;
        q('extRepair').innerHTML=`<b>${esc(d.message)}</b>
<div class=small>Manifest: ${esc(d.manifest)}</div>
<div class=small>Suggested replacement text:</div>
<div class=repairbox>${esc(d.suggested)}</div>
<button onclick="copyManifestSuggestion(window.extLastSuggested)">Copy Suggested Manifest</button>
<button onclick="applyManifestFix(window.extLastManifest,window.extLastSuggested)">Apply Suggested Fix</button>
<button onclick="sendManifestSuggestionToMission(window.extLastManifest,window.extLastSuggested)">Send Suggestion to Mission Console</button>`;
        toast('Manifest suggestion generated.');
    }else if(d?.message){
        q('extRepair').textContent=d.message;
    }
}


function extOfficerText(officer){
    if(!officer)return '';
    if(typeof officer==='string')return officer;
    if(typeof officer==='object'){
        let parts=[];
        if(officer.name)parts.push(officer.name);
        if(officer.callsign)parts.push(`"${officer.callsign}"`);
        if(officer.role)parts.push(`— ${officer.role}`);
        return parts.join(' ')||JSON.stringify(officer);
    }
    return String(officer);
}
function extDashboardFromData(d){
    if(!q('extDashboard')||!d)return;
    let items=d.items||[];
    let total=items.length;
    let enabled=items.filter(x=>x.enabled).length;
    let disabled=total-enabled;
    let valid=items.filter(x=>x.status==='VALID').length;
    let problems=items.filter(x=>x.status!=='VALID'||(x.missing&&x.missing.length)).length;
    let departments=items.filter(x=>String(x.kind||'').toLowerCase()==='department').length;
    let extensions=items.filter(x=>String(x.kind||'').toLowerCase()==='extension').length;
    let systems=items.filter(x=>String(x.kind||'').toLowerCase()==='system').length;
    let hint=problems?`Needs attention: ${problems} manifest problem(s). Use Validate, Suggest Fix, then Apply Suggested Fix if the suggestion looks right.`:'All discovered module manifests look valid.';
    let hintClass=problems?'modhint modwarn':'modhint modok';
    q('extDashboard').innerHTML=`<div class=moddash>
        <div class=modbox><div class=label>Total Modules</div><div class=value>${total}</div></div>
        <div class=modbox><div class=label>Enabled</div><div class=value>${enabled}</div></div>
        <div class=modbox><div class=label>Disabled</div><div class=value>${disabled}</div></div>
        <div class=modbox><div class=label>Valid</div><div class=value>${valid}</div></div>
        <div class=modbox><div class=label>Problems</div><div class=value>${problems}</div></div>
        <div class=modbox><div class=label>Departments</div><div class=value>${departments}</div></div>
        <div class=modbox><div class=label>Extensions</div><div class=value>${extensions}</div></div>
        <div class=modbox><div class=label>System</div><div class=value>${systems}</div></div>
    </div><div class="${hintClass}"><div class=time>Module Readiness</div>${esc(hint)}${window.extLastReport?`<br><br>Last report: ${esc(window.extLastReport)}`:''}</div>`;
}

async function applyManifestFix(manifest,suggested){
    let ok=confirm('Apply this manifest repair now? A backup will be created first.');
    if(!ok)return;
    q('extRepair').textContent='Applying manifest repair safely...';
    let d=await api('/api/extensions/apply_repair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({manifest,suggested})});
    if(d?.ok){
        q('extRepair').innerHTML=`<b>${esc(d.message)}</b>
<div class=repairbox>Manifest: ${esc(d.manifest)}
Backup: ${esc(d.backup)}

Before:
Status: ${esc(d.before.status)}
Version: ${esc(d.before.version)}
Missing: ${esc((d.before.missing||[]).join(', ')||'None')}

After:
Status: ${esc(d.after.status)}
Version: ${esc(d.after.version)}
Missing: ${esc((d.after.missing||[]).join(', ')||'None')}

Validation:
Checked: ${esc(d.validation.checked)}
Valid: ${esc(d.validation.valid)}
Problems: ${esc((d.validation.problems||[]).length)}</div>
<button onclick="loadExtensions()">Refresh Modules</button>
<button onclick="validateExtensions()">Validate Again</button>
<button onclick="exportExtensionReport()">Export New Report</button>`;
        toast('Manifest repair applied safely.');
        loadExtensions();
    }else{
        q('extRepair').textContent=d?.message||'Manifest repair failed.';
    }
}

function copyManifestSuggestion(txt){
    navigator.clipboard.writeText(txt);
    toast('Suggested manifest copied.');
}
function sendManifestSuggestionToMission(manifest,suggested){
    go('mission');
    q('input').value=`Please review this Kayock manifest repair suggestion before I apply it manually.

Manifest:
${manifest}

Suggested manifest:
${suggested}

Check if this is safe and whether any fields should be changed.`;
    toast('Manifest repair suggestion sent to Mission Console input.');
}


let lastScanReport=null;






















let lastRecoveryDashboard=null;
async function loadRecoveryDashboard(){
    if(!q('recoveryDashCard'))return;
    q('recoveryDashCard').textContent='Loading recovery health...';
    let d=await api('/api/backups/recovery_dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('recoveryDashCard').textContent=d?.message||'Recovery dashboard unavailable.';
        return;
    }
    lastRecoveryDashboard=d;
    let s=d.summary||{};
    let cls=d.healthy?'healthy':'warn';
    q('recoveryDashCard').innerHTML=`<div class="recoveryHealthBadge ${cls}">Recovery Foundation: ${esc(d.health_label||'UNKNOWN')}</div>
<div>Current chain: <b>${esc(d.current_chain||'unknown')}</b></div>
<div class=recoveryMiniGrid>
  <div class=recoveryMini><div class=label>Restore Actions</div><div class=value>${s.restore_actions||0}</div></div>
  <div class=recoveryMini><div class=label>Rollback Actions</div><div class=value>${s.rollback_actions||0}</div></div>
  <div class=recoveryMini><div class=label>Attention</div><div class=value>${s.attention_events||0}</div></div>
  <div class=recoveryMini><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
  <div class=recoveryMini><div class=label>Superseded</div><div class=value>${s.superseded_events||0}</div></div>
  <div class=recoveryMini><div class=label>Events</div><div class=value>${s.events||0}</div></div>
</div>
<div class=recoveryPath>Latest: ${esc(s.latest_event||'none')} ${s.latest_created?('• '+esc(s.latest_created)) : ''}</div>
<div class=recoveryPath>Restore audit OK: ${s.restore_audit_ok} • Rollback audit OK: ${s.rollback_audit_ok}</div>`;
}
function sendRecoveryDashboardToMission(){
    if(!lastRecoveryDashboard){
        toast('Load recovery health first.');
        return;
    }
    let s=lastRecoveryDashboard.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Recovery Foundation dashboard summary.

Health:
${lastRecoveryDashboard.health_label}

Current chain:
${lastRecoveryDashboard.current_chain}

Summary:
Events: ${s.events}
Targets/chains: ${s.targets}
Restore actions: ${s.restore_actions}
Rollback actions: ${s.rollback_actions}
Backup/staging events: ${s.backup_events}
Evidence reports: ${s.evidence_reports}
Intact events: ${s.intact_events}
Superseded-by-rollback events: ${s.superseded_events}
Attention events: ${s.attention_events}
Errors: ${s.errors}
Latest event: ${s.latest_event}
Latest created: ${s.latest_created}
Restore audit OK: ${s.restore_audit_ok}
Rollback audit OK: ${s.rollback_audit_ok}

Chains:
${(lastRecoveryDashboard.chains||[]).map(c=>`${c.target}
Events: ${c.event_count}
Restores: ${c.restore_actions}
Rollbacks: ${c.rollback_actions}
Backups: ${c.backup_events}
Evidence: ${c.evidence_reports}
Intact: ${c.intact_events}
Superseded: ${c.superseded_events||0}
Attention: ${c.attention_events}
Latest: ${c.latest_created}`).join('\n\n')}

Safety:
Read-only dashboard.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether Recovery Foundation should be marked healthy
2. Whether the Command Bridge card is accurate
3. Whether v10.8.x can be frozen as the Recovery Foundation milestone
4. Whether the next build should move to a new milestone area.`;
    toast('Recovery dashboard sent to Mission Console.');
}

let lastRecoveryTimeline=null;
function timelineBadge(status){
    status=(status||'other').toLowerCase();
    let cls=(status==='intact'||status==='attention'||status==='evidence'||status==='superseded_by_rollback')?status:'other';
    return `<span class="tlbadge ${cls}">${esc(status.toUpperCase())}</span>`;
}
async function loadRecoveryTimeline(doExport=false){
    let query=q('recoveryTimelineFilter').value||'';
    let limit=parseInt(q('recoveryTimelineLimit').value||'1000');
    q('recoveryTimelineStatus').textContent='Loading recovery timeline...';
    let d=await api('/api/backups/recovery_timeline',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('recoveryTimelineStatus').textContent=d?.message||'Could not load recovery timeline.';
        return;
    }
    lastRecoveryTimeline=d;
    let s=d.summary||{};
    q('recoveryTimelineStatus').textContent=`Recovery timeline loaded.
Events: ${s.events||0}
Targets/chains: ${s.targets||0}
Restore actions: ${s.restore_actions||0}
Rollback actions: ${s.rollback_actions||0}
Backup/staging events: ${s.backup_events||0}
Evidence reports: ${s.evidence_reports||0}
Intact events: ${s.intact_events||0}
Attention events: ${s.attention_events||0}
Superseded-by-rollback events: ${s.superseded_events||0}
Errors: ${s.errors||0}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('recoveryTimelineDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Events</div><div class=value>${s.events||0}</div></div>
        <div class=vaultmetric><div class=label>Chains</div><div class=value>${s.targets||0}</div></div>
        <div class=vaultmetric><div class=label>Restores</div><div class=value>${s.restore_actions||0}</div></div>
        <div class=vaultmetric><div class=label>Rollbacks</div><div class=value>${s.rollback_actions||0}</div></div>
        <div class=vaultmetric><div class=label>Backups</div><div class=value>${s.backup_events||0}</div></div>
        <div class=vaultmetric><div class=label>Evidence</div><div class=value>${s.evidence_reports||0}</div></div>
        <div class=vaultmetric><div class=label>Attention</div><div class=value>${s.attention_events||0}</div></div>
        <div class=vaultmetric><div class=label>Superseded</div><div class=value>${s.superseded_events||0}</div></div>
        <div class=vaultmetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div><div class=status>Latest event: ${esc(s.latest_event||'none')} | ${esc(s.latest_created||'')}</div>`;
    q('recoveryTimelineChains').innerHTML=(d.chains||[]).map(c=>`<div class="histrow ${c.attention_events?'info':'ok'}"><b>${esc(c.target)}</b>
<div>Events: ${c.event_count} | Restores: ${c.restore_actions} | Rollbacks: ${c.rollback_actions} | Backups: ${c.backup_events} | Evidence: ${c.evidence_reports}</div>
<div>Intact: ${c.intact_events} | Superseded: ${c.superseded_events||0} | Attention: ${c.attention_events} | Latest: ${esc(c.latest_created||'')}</div>
</div>`).join('')||'No recovery chains found.';
    q('recoveryTimelineKinds').innerHTML=(d.kind_counts||[]).map(k=>`<div class="histrow info"><b>${esc(k.kind)}</b><div>Count: ${k.count}</div></div>`).join('')||'No event type summary.';
    q('recoveryTimelineEvents').innerHTML=(d.events||[]).map(e=>{
        let h=e.hashes||{};
        let p=e.paths||{};
        let failed=(e.checks||[]).filter(c=>!c.ok);
        return `<div class="histrow timelineEvent ${e.status==='intact'?'ok':'info'}"><b>${esc(e.created||'unknown time')} — ${esc(e.kind)} — ${esc(e.title)}</b>${timelineBadge(e.status)}
<div>${esc(e.summary||'')}</div>
<div class=vaultpath>Target: ${esc(e.target||'')}</div>
<div class=vaultpath>Source: ${esc(e.source||'')}</div>
${Object.keys(p).map(k=>`<div class=vaultpath>${esc(k)}: ${esc(p[k]||'')}</div>`).join('')}
${Object.keys(h).map(k=>`<div class=timelineHash>${esc(k)}: ${esc(h[k]||'')}</div>`).join('')}
<details><summary>Checks: ${(e.checks||[]).length} | Failed: ${failed.map(c=>c.id).join(', ')||'none'}</summary>${(e.checks||[]).map(c=>`<div class=packagefile>${c.ok?'PASS':'FAIL'} — ${esc(c.id)} — ${esc(c.message)} — ${esc(c.path||'')}</div>`).join('')}</details>
</div>`;
    }).join('')||'No timeline events found.';
    toast('Recovery timeline loaded.');
}
function sendRecoveryTimelineToMission(){
    if(!lastRecoveryTimeline){
        toast('Load recovery timeline first.');
        return;
    }
    let s=lastRecoveryTimeline.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Recovery Timeline.

This is a read-only timeline review. No restore or rollback action is requested.

Summary:
Events: ${s.events}
Targets/chains: ${s.targets}
Restore actions: ${s.restore_actions}
Rollback actions: ${s.rollback_actions}
Backup/staging events: ${s.backup_events}
Evidence reports: ${s.evidence_reports}
Intact events: ${s.intact_events}
Attention events: ${s.attention_events}
Superseded-by-rollback events: ${s.superseded_events||0}
Errors: ${s.errors}
Latest event: ${s.latest_event}
Latest created: ${s.latest_created}

Exported Timeline:
${lastRecoveryTimeline.exported?.markdown||'No exported timeline path'}

Chains:
${(lastRecoveryTimeline.chains||[]).map(c=>`${c.target}
Events: ${c.event_count}
Restores: ${c.restore_actions}
Rollbacks: ${c.rollback_actions}
Backups: ${c.backup_events}
Evidence: ${c.evidence_reports}
Intact: ${c.intact_events}
Superseded: ${c.superseded_events||0}
Attention: ${c.attention_events}
Latest: ${c.latest_created}`).join('\n\n')}

Events:
${(lastRecoveryTimeline.events||[]).map(e=>`${e.created} — ${e.kind} — ${e.title}
Status: ${e.status}
Target: ${e.target}
Summary: ${e.summary}
Source: ${e.source}
Paths: ${JSON.stringify(e.paths||{})}
Hashes: ${JSON.stringify(e.hashes||{})}`).join('\n\n')}

Safety:
Read-only timeline.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the recovery chain is complete and understandable
2. Whether restore and rollback actions remain auditable together
3. Whether any attention or error item should block future recovery actions
4. Whether the next build should add a Recovery Dashboard summary card on Command Bridge
5. Whether we should freeze v10.8.x as the Recovery Foundation milestone.`;
    toast('Recovery timeline sent to Mission Console.');
}

let lastRollbackAudit=null;
function rollbackAuditBadge(status){
    status=(status||'attention').toLowerCase();
    return `<span class="rbauditbadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function loadRollbackAudit(doExport=false){
    let query=q('rollbackAuditFilter').value||'';
    let limit=parseInt(q('rollbackAuditLimit').value||'1000');
    q('rollbackAuditStatus').textContent='Loading rollback audit...';
    let d=await api('/api/backups/rollback_audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('rollbackAuditStatus').textContent=d?.message||'Could not load rollback audit.';
        return;
    }
    lastRollbackAudit=d;
    let s=d.summary||{};
    q('rollbackAuditStatus').textContent=`Rollback audit loaded.
Actions: ${s.actions||0}
Intact: ${s.intact||0}
Attention: ${s.attention||0}
Verified: ${s.verified||0}
Rollback sources present: ${s.rollback_sources_present||0}
Rollback source hashes intact: ${s.rollback_source_hashes_intact||0}
Pre-rollback backups present: ${s.pre_rollback_backups_present||0}
Targets still rolled back: ${s.targets_still_rolled_back||0}
Errors: ${s.errors||0}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('rollbackAuditDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Actions</div><div class=value>${s.actions||0}</div></div>
        <div class=vaultmetric><div class=label>Intact</div><div class=value>${s.intact||0}</div></div>
        <div class=vaultmetric><div class=label>Attention</div><div class=value>${s.attention||0}</div></div>
        <div class=vaultmetric><div class=label>Verified</div><div class=value>${s.verified||0}</div></div>
        <div class=vaultmetric><div class=label>Sources</div><div class=value>${s.rollback_sources_present||0}</div></div>
        <div class=vaultmetric><div class=label>Source Hash OK</div><div class=value>${s.rollback_source_hashes_intact||0}</div></div>
        <div class=vaultmetric><div class=label>Targets Rolled Back</div><div class=value>${s.targets_still_rolled_back||0}</div></div>
        <div class=vaultmetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div><div class=status>Latest action: ${esc(s.latest_action||'none')} | ${esc(s.latest_created||'')}</div>`;
    q('rollbackAuditStatusList').innerHTML=(d.by_status||[]).map(x=>`<div class="histrow info"><b>${esc(x.status)}</b><div>Count: ${x.count}</div></div>`).join('')||'No status summary.';
    q('rollbackAuditTargetList').innerHTML=(d.by_target||[]).map(x=>`<div class="histrow info"><b>${esc(x.target)}</b><div>Count: ${x.count} | Intact: ${x.intact} | Attention: ${x.attention}</div></div>`).join('')||'No target summary.';
    q('rollbackAuditList').innerHTML=(d.actions||[]).map(a=>`<div class="histrow ${a.status==='intact'?'ok':'info'}"><b>${esc(a.name)}</b>${rollbackAuditBadge(a.status)}
<div>Created: ${esc(a.created||'')} | Verification: ${a.verification_ok} (${a.verification_passed}/${a.verification_checked})</div>
<div>Target still matches rollback hash: ${a.target_current_matches_rollback_hash} | Rollback source hash intact: ${a.rollback_source_backup_hash_intact}</div>
<div class=vaultpath>Target: ${esc(a.target||'')}</div>
<div class=vaultpath>Rollback source backup: ${esc(a.rollback_source_backup||'')}</div>
<div class=vaultpath>Pre-rollback current target backup: ${esc(a.pre_rollback_current_target_backup||'')}</div>
<div class=vaultpath>Original restore action: ${esc(a.restore_action||'')}</div>
<div class=vaultpath>Rollback report: ${esc(a.rollback_report_markdown||a.rollback_report_json||'')}</div>
<div class=vaultpath>Repair log: ${esc(a.repair_action_log_markdown||a.repair_action_log_json||'')}</div>
<div class=rbauditHash>target_before_rollback: ${esc((a.hashes||{}).target_before_rollback||'')}</div>
<div class=rbauditHash>pre_rollback_backup: ${esc((a.hashes||{}).pre_rollback_current_target_backup||'')}</div>
<div class=rbauditHash>rollback_source: ${esc((a.hashes||{}).rollback_source_backup||'')}</div>
<div class=rbauditHash>target_after_rollback: ${esc((a.hashes||{}).target_after_rollback||'')}</div>
<div class=rbauditHash>target_current: ${esc(a.target_current_hash||'')}</div>
<details><summary>Checks (${(a.checks||[]).length}) / Failed: ${(a.failed_checks||[]).join(', ')||'none'}</summary>${(a.checks||[]).map(c=>`<div class=packagefile>${c.ok?'PASS':'FAIL'} — ${esc(c.id)} — ${esc(c.message)} — ${esc(c.path||'')}</div>`).join('')}</details>
</div>`).join('')||'No rollback actions found.';
    toast('Rollback audit loaded.');
}
function sendRollbackAuditToMission(){
    if(!lastRollbackAudit){
        toast('Load rollback audit first.');
        return;
    }
    let s=lastRollbackAudit.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Rollback Audit Inventory.

This is a read-only audit review. No rollback or restore action is requested.

Summary:
Actions: ${s.actions}
Intact: ${s.intact}
Attention: ${s.attention}
Verified: ${s.verified}
Rollback sources present: ${s.rollback_sources_present}
Rollback source hashes intact: ${s.rollback_source_hashes_intact}
Pre-rollback backups present: ${s.pre_rollback_backups_present}
Pre-rollback backup hashes intact: ${s.pre_rollback_backup_hashes_intact}
Targets still rolled back: ${s.targets_still_rolled_back}
Restore action reports present: ${s.restore_action_reports_present}
Repair logs present: ${s.repair_logs_present}
Errors: ${s.errors}
Latest action: ${s.latest_action}
Latest created: ${s.latest_created}

Exported Audit:
${lastRollbackAudit.exported?.markdown||'No exported rollback audit path'}

Actions:
${(lastRollbackAudit.actions||[]).map(a=>`${a.status.toUpperCase()} — ${a.name}
Created: ${a.created}
Original restore action: ${a.restore_action}
Target: ${a.target}
Rollback source backup: ${a.rollback_source_backup}
Pre-rollback current target backup: ${a.pre_rollback_current_target_backup}
Verification OK: ${a.verification_ok}
Verification message: ${a.verification_message}
Target still matches rollback hash: ${a.target_current_matches_rollback_hash}
Rollback source hash intact: ${a.rollback_source_backup_hash_intact}
Pre-rollback backup hash intact: ${a.pre_rollback_current_target_backup_hash_intact}
Target before rollback: ${(a.hashes||{}).target_before_rollback}
Pre-rollback backup: ${(a.hashes||{}).pre_rollback_current_target_backup}
Rollback source: ${(a.hashes||{}).rollback_source_backup}
Target after rollback: ${(a.hashes||{}).target_after_rollback}
Target current: ${a.target_current_hash}
Failed checks: ${(a.failed_checks||[]).join(', ')||'none'}
Rollback report: ${a.rollback_report_markdown||a.rollback_report_json}
Repair log: ${a.repair_action_log_markdown||a.repair_action_log_json}`).join('\n\n')}

Safety:
Read-only viewer.
No rollback.
No restore.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the completed rollback action remains auditable
2. Whether the rollback source backup is intact
3. Whether the pre-rollback backup is intact
4. Whether the target still matches the rollback result
5. Whether any attention item should block future rollback/restore actions.`;
    toast('Rollback audit sent to Mission Console.');
}

let lastRollbackAction=null;
let lastRollbackPreflight=null;
async function loadRollbackActionList(){
    q('rollbackActionStatus').textContent='Loading restore actions...';
    let d=await api('/api/backups/restore_audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('rollbackActionStatus').textContent=d?.message||'Could not load restore actions.';
        return;
    }
    let sel=q('rollbackActionSelect');
    sel.innerHTML=(d.actions||[]).map(a=>`<option value="${esc(a.restore_report_json||a.pre_restore_live_backup||a.name)}">${esc(a.name)} → ${esc(a.target||'unknown target')}</option>`).join('');
    if((d.actions||[]).length){
        q('rollbackActionPath').value=d.actions[0].restore_report_json||d.actions[0].pre_restore_live_backup||d.actions[0].name;
    }
    q('rollbackActionStatus').textContent=`Loaded ${d.actions?.length||0} restore action(s). Run rollback preflight first.`;
}
async function preflightRollbackAction(){
    let path=q('rollbackActionPath').value||q('rollbackActionSelect').value||'';
    if(!path){
        q('rollbackActionStatus').textContent='Select a restore action first.';
        return;
    }
    q('rollbackActionStatus').textContent='Running rollback preflight...';
    let d=await api('/api/backups/rollback_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_report:path,export:true})});
    lastRollbackPreflight=d;
    q('rollbackActionResult').textContent=JSON.stringify(d,null,2);
    if(!d?.ok){
        q('rollbackActionStatus').textContent=d?.message||'Rollback preflight failed.';
        return;
    }
    q('rollbackActionConfirm').value='';
    q('rollbackActionConfirm').placeholder=d.future_rollback_phrase||'Exact rollback phrase unavailable';
    let s=d.summary||{};
    q('rollbackActionStatus').textContent=`Rollback preflight complete.
Candidate status: ${s.candidate_status}
Hard blocks excluding rollback lock: ${s.hard_blocks}
Would overwrite: ${s.would_overwrite}
Future rollback phrase required:
${d.future_rollback_phrase}`;
    q('rollbackActionChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.status==='pass'?'ok':(c.status==='block'?'fail':'info')}"><b>${esc(c.id)}</b>${rollbackBadge(c.status)}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.detail||'')}</div></div>`).join('');
    toast('Rollback preflight complete.');
}
async function runSingleFileRollback(){
    let path=q('rollbackActionPath').value||q('rollbackActionSelect').value||'';
    let confirm=q('rollbackActionConfirm').value||'';
    if(!path){
        q('rollbackActionStatus').textContent='Select a restore action first.';
        return;
    }
    if(!lastRollbackPreflight || (lastRollbackPreflight.summary||{}).restore_action!==((lastRollbackPreflight.restore_action||{}).name||'')){
        // Keep this lenient; backend re-runs the preview.
    }
    if(!lastRollbackPreflight){
        q('rollbackActionStatus').textContent='Run rollback preflight first.';
        return;
    }
    if(confirm!==lastRollbackPreflight.future_rollback_phrase){
        q('rollbackActionStatus').textContent='Exact rollback phrase does not match the preflight phrase.';
        return;
    }
    if(!window.confirm('This will overwrite the original target with the pre-restore backup after backing up the current target. Continue?')){
        q('rollbackActionStatus').textContent='Rollback cancelled.';
        return;
    }
    if(!window.confirm('Final confirmation: run the live single-file rollback action now?')){
        q('rollbackActionStatus').textContent='Rollback cancelled at final confirmation.';
        return;
    }
    q('rollbackActionStatus').textContent='Running single-file rollback...';
    let d=await api('/api/backups/single_file_rollback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_report:path,confirm})});
    lastRollbackAction=d;
    q('rollbackActionResult').textContent=JSON.stringify(d,null,2);
    let v=d?.verification||{};
    q('rollbackActionChecks').innerHTML=(v.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id)}</b>${rollbackBadge(c.ok?'pass':'block')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No verification checks.';
    if(d?.ok){
        q('rollbackActionStatus').textContent=`Single-file rollback complete and verified.
Target: ${d.target}
Pre-rollback current-target backup: ${d.pre_rollback_current_target_backup}
Report: ${d.exported?.markdown||''}
Repair log: ${d.repair_action_log?.markdown||''}`;
        toast('Single-file rollback complete and verified.');
    }else{
        q('rollbackActionStatus').textContent=d?.message||'Rollback failed or was blocked.';
        toast('Rollback failed or blocked.');
    }
}
function sendRollbackActionToMission(){
    if(!lastRollbackAction){
        toast('Run a rollback action first.');
        return;
    }
    go('mission');
    let v=lastRollbackAction.verification||{};
    let h=lastRollbackAction.hashes||{};
    q('input').value=`Please review this Kayock Single-File Rollback Action result.

This was a narrow rollback action from the pre-restore live backup.

Result:
OK: ${lastRollbackAction.ok}
Message: ${lastRollbackAction.message}
Target: ${lastRollbackAction.target}
Rollback source backup: ${lastRollbackAction.rollback_source_backup}
Pre-rollback current target backup: ${lastRollbackAction.pre_rollback_current_target_backup}
Original restore action: ${lastRollbackAction.restore_action}
Confirmation phrase: ${lastRollbackAction.confirmation_phrase}

Hashes:
Target before rollback: ${h.target_before_rollback}
Pre-rollback current target backup: ${h.pre_rollback_current_target_backup}
Rollback source backup: ${h.rollback_source_backup}
Recorded old target: ${h.recorded_old_target}
Recorded live backup: ${h.recorded_live_backup}
Target after rollback: ${h.target_after_rollback}

Verification:
${v.message||''}
${(v.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Reports:
Rollback report: ${lastRollbackAction.exported?.markdown||''}
RepairActions log: ${lastRollbackAction.repair_action_log?.markdown||''}

Safety:
Single file only.
From pre-restore backup only.
Original target only.
Current target backed up before rollback.
Exact confirmation phrase required.
No folder rollback.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether rollback was successful
2. Whether the pre-rollback backup makes re-restore safe
3. Whether post-rollback hash verification is sufficient
4. Whether the rollback action should stay limited to generated files
5. Whether to build a rollback audit viewer next.`;
    toast('Rollback result sent to Mission Console.');
}

let lastRollbackPreview=null;
async function loadRollbackPreviewActions(){
    q('rollbackPreviewStatus').textContent='Loading restore actions...';
    let d=await api('/api/backups/restore_audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('rollbackPreviewStatus').textContent=d?.message||'Could not load restore actions.';
        return;
    }
    let sel=q('rollbackPreviewSelect');
    sel.innerHTML=(d.actions||[]).map(a=>`<option value="${esc(a.restore_report_json||a.pre_restore_live_backup||a.name)}">${esc(a.name)} → ${esc(a.target||'unknown target')}</option>`).join('');
    if((d.actions||[]).length){
        q('rollbackPreviewPath').value=d.actions[0].restore_report_json||d.actions[0].pre_restore_live_backup||d.actions[0].name;
    }
    q('rollbackPreviewStatus').textContent=`Loaded ${d.actions?.length||0} restore action(s). Select one and run rollback preview.`;
}
function rollbackBadge(status){
    status=(status||'block').toLowerCase();
    return `<span class="rollbackbadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function runRollbackPreview(doExport=false){
    let path=q('rollbackPreviewPath').value||q('rollbackPreviewSelect').value||'';
    if(!path){
        q('rollbackPreviewStatus').textContent='Select a restore action first.';
        return;
    }
    q('rollbackPreviewStatus').textContent='Running rollback preview...';
    let d=await api('/api/backups/rollback_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_report:path,export:doExport})});
    if(!d?.ok){
        q('rollbackPreviewStatus').textContent=d?.message||'Rollback preview failed.';
        return;
    }
    lastRollbackPreview=d;
    let s=d.summary||{};
    q('rollbackPreviewStatus').textContent=`Rollback preview complete.
Candidate status: ${s.candidate_status}
Checks: ${s.checks}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding rollback lock: ${s.hard_blocks}
Rollback allowed now: ${s.rollback_allowed_now}
Would overwrite: ${s.would_overwrite}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('rollbackPreviewDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Candidate</div><div class=value>${esc((s.candidate_status||'').replaceAll('_',' '))}</div></div>
        <div class=vaultmetric><div class=label>Passed</div><div class=value>${s.pass||0}</div></div>
        <div class=vaultmetric><div class=label>Warnings</div><div class=value>${s.warn||0}</div></div>
        <div class=vaultmetric><div class=label>Blocks</div><div class=value>${s.block||0}</div></div>
        <div class=vaultmetric><div class=label>Hard Blocks</div><div class=value>${s.hard_blocks||0}</div></div>
        <div class=vaultmetric><div class=label>Would Overwrite</div><div class=value>${s.would_overwrite?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Same Hash</div><div class=value>${s.same_hash?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Text Diff</div><div class=value>${s.text_preview_available?'YES':'NO'}</div></div>
    </div><div class=status>Rollback remains intentionally unavailable in this build. Preview only.</div>`;
    q('rollbackPreviewChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.status==='pass'?'ok':(c.status==='block'?'fail':'info')}"><b>${esc(c.id)}</b>${rollbackBadge(c.status)}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.detail||'')}</div></div>`).join('')||'No checks.';
    q('rollbackPreviewDiff').textContent=(d.comparison||{}).diff_preview||'No diff preview.';
    q('rollbackPreviewPhrase').innerHTML=`<div class=rollbackphrase>${esc(d.future_rollback_phrase||'')}</div><div class=small>This phrase does not unlock rollback in this build. Actual rollback is still unavailable.</div>`;
    toast('Rollback preview complete.');
}
function sendRollbackPreviewToMission(){
    if(!lastRollbackPreview){
        toast('Run rollback preview first.');
        return;
    }
    let s=lastRollbackPreview.summary||{};
    let b=lastRollbackPreview.rollback_source_backup||{};
    let t=lastRollbackPreview.target||{};
    go('mission');
    q('input').value=`Please review this Kayock Rollback Preview.

No rollback action is requested or possible in this build.

Summary:
Candidate status: ${s.candidate_status}
Checks: ${s.checks}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding intentional rollback lock: ${s.hard_blocks}
Rollback allowed now: ${s.rollback_allowed_now}
Restore action: ${s.restore_action}
Target: ${s.target}
Pre-restore backup: ${s.pre_restore_backup}
Same hash: ${s.same_hash}
Would overwrite: ${s.would_overwrite}
Text diff available: ${s.text_preview_available}

Future rollback phrase:
${lastRollbackPreview.future_rollback_phrase}

Hashes:
Pre-restore backup: ${b.sha256}
Recorded live backup: ${b.recorded_live_backup_sha256}
Recorded old target: ${b.recorded_old_target_sha256}
Current target: ${t.sha256_now}
Recorded restored target: ${t.recorded_restored_sha256}

Checks:
${(lastRollbackPreview.checks||[]).map(c=>`${c.status.toUpperCase()} — ${c.id}: ${c.message} ${c.detail||''}`).join('\n')}

Diff Preview:
${(lastRollbackPreview.comparison||{}).diff_preview||'No diff preview'}

Exported Report:
${lastRollbackPreview.exported?.markdown||'No exported rollback preview path'}

Safety:
Preview only.
No rollback button.
No rollback endpoint.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the pre-restore backup is a valid future rollback source
2. Whether current target state is safe to rollback from
3. Whether any warning should become a hard block
4. Whether the rollback phrase is strong enough
5. Whether the next build should still be preview-only or can safely introduce a single-file rollback action.`;
    toast('Rollback preview sent to Mission Console.');
}

let lastRestoreAudit=null;
function auditBadge(status){
    status=(status||'attention').toLowerCase();
    return `<span class="auditbadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function loadRestoreAudit(doExport=false){
    let query=q('restoreAuditFilter').value||'';
    let limit=parseInt(q('restoreAuditLimit').value||'1000');
    q('restoreAuditStatus').textContent='Loading post-restore audit...';
    let d=await api('/api/backups/restore_audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('restoreAuditStatus').textContent=d?.message||'Could not load restore audit.';
        return;
    }
    lastRestoreAudit=d;
    let s=d.summary||{};
    q('restoreAuditStatus').textContent=`Restore audit loaded.
Actions: ${s.actions||0}
Intact: ${s.intact||0}
Attention: ${s.attention||0}
Verified: ${s.verified||0}
Live backups present: ${s.live_backups_present||0}
Live backup hashes intact: ${s.live_backup_hashes_intact||0}
Targets still restored: ${s.targets_still_restored||0}
Errors: ${s.errors||0}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('restoreAuditDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Actions</div><div class=value>${s.actions||0}</div></div>
        <div class=vaultmetric><div class=label>Intact</div><div class=value>${s.intact||0}</div></div>
        <div class=vaultmetric><div class=label>Attention</div><div class=value>${s.attention||0}</div></div>
        <div class=vaultmetric><div class=label>Verified</div><div class=value>${s.verified||0}</div></div>
        <div class=vaultmetric><div class=label>Live Backups</div><div class=value>${s.live_backups_present||0}</div></div>
        <div class=vaultmetric><div class=label>Backup Hash OK</div><div class=value>${s.live_backup_hashes_intact||0}</div></div>
        <div class=vaultmetric><div class=label>Targets Restored</div><div class=value>${s.targets_still_restored||0}</div></div>
        <div class=vaultmetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div><div class=status>Latest action: ${esc(s.latest_action||'none')} | ${esc(s.latest_created||'')}</div>`;
    q('restoreAuditStatusList').innerHTML=(d.by_status||[]).map(x=>`<div class="histrow info"><b>${esc(x.status)}</b><div>Count: ${x.count}</div></div>`).join('')||'No status summary.';
    q('restoreAuditTargetList').innerHTML=(d.by_target||[]).map(x=>`<div class="histrow info"><b>${esc(x.target)}</b><div>Count: ${x.count} | Intact: ${x.intact} | Attention: ${x.attention}</div></div>`).join('')||'No target summary.';
    q('restoreAuditList').innerHTML=(d.actions||[]).map(a=>`<div class="histrow ${a.status==='intact'?'ok':'info'}"><b>${esc(a.name)}</b>${auditBadge(a.status)}
<div>Created: ${esc(a.created||'')} | Verification: ${a.verification_ok} (${a.verification_passed}/${a.verification_checked})</div>
<div>Target still matches restored hash: ${a.target_current_matches_restored_hash} | Live backup hash intact: ${a.pre_restore_live_backup_hash_intact}</div>
<div class=vaultpath>Target: ${esc(a.target||'')}</div>
<div class=vaultpath>Pre-restore live backup: ${esc(a.pre_restore_live_backup||'')}</div>
<div class=vaultpath>Staged copy: ${esc(a.staged_copy||'')}</div>
<div class=vaultpath>Source backup: ${esc(a.source_backup||'')}</div>
<div class=vaultpath>Restore report: ${esc(a.restore_report_markdown||a.restore_report_json||'')}</div>
<div class=vaultpath>Repair log: ${esc(a.repair_action_log_markdown||a.repair_action_log_json||'')}</div>
<div class=hashline>target_before: ${esc((a.hashes||{}).target_before||'')}</div>
<div class=hashline>live_backup: ${esc((a.hashes||{}).live_backup||'')}</div>
<div class=hashline>staged_copy: ${esc((a.hashes||{}).staged_copy||'')}</div>
<div class=hashline>target_after: ${esc((a.hashes||{}).target_after||'')}</div>
<div class=hashline>target_current: ${esc(a.target_current_hash||'')}</div>
<details><summary>Checks (${(a.checks||[]).length}) / Failed: ${(a.failed_checks||[]).join(', ')||'none'}</summary>${(a.checks||[]).map(c=>`<div class=packagefile>${c.ok?'PASS':'FAIL'} — ${esc(c.id)} — ${esc(c.message)} — ${esc(c.path||'')}</div>`).join('')}</details>
</div>`).join('')||'No restore actions found.';
    toast('Restore audit loaded.');
}
function sendRestoreAuditToMission(){
    if(!lastRestoreAudit){
        toast('Load restore audit first.');
        return;
    }
    let s=lastRestoreAudit.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Post-Restore Audit Inventory.

This is a read-only audit review. No restore action is requested.

Summary:
Actions: ${s.actions}
Intact: ${s.intact}
Attention: ${s.attention}
Verified: ${s.verified}
Live backups present: ${s.live_backups_present}
Live backup hashes intact: ${s.live_backup_hashes_intact}
Staged copy hashes intact: ${s.staged_copy_hashes_intact}
Targets still restored: ${s.targets_still_restored}
Repair logs present: ${s.repair_logs_present}
Errors: ${s.errors}
Latest action: ${s.latest_action}
Latest created: ${s.latest_created}

Exported Audit:
${lastRestoreAudit.exported?.markdown||'No exported audit path'}

Actions:
${(lastRestoreAudit.actions||[]).map(a=>`${a.status.toUpperCase()} — ${a.name}
Created: ${a.created}
Target: ${a.target}
Pre-restore live backup: ${a.pre_restore_live_backup}
Staged copy: ${a.staged_copy}
Source backup: ${a.source_backup}
Verification OK: ${a.verification_ok}
Verification message: ${a.verification_message}
Target still matches restored hash: ${a.target_current_matches_restored_hash}
Live backup hash intact: ${a.pre_restore_live_backup_hash_intact}
Target before: ${(a.hashes||{}).target_before}
Live backup: ${(a.hashes||{}).live_backup}
Staged copy: ${(a.hashes||{}).staged_copy}
Target after: ${(a.hashes||{}).target_after}
Target current: ${a.target_current_hash}
Failed checks: ${(a.failed_checks||[]).join(', ')||'none'}
Restore report: ${a.restore_report_markdown||a.restore_report_json}
Repair log: ${a.repair_action_log_markdown||a.repair_action_log_json}`).join('\n\n')}

Safety:
Read-only viewer.
No restore.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the completed restore action remains auditable
2. Whether the live backup is intact
3. Whether the restored target still matches the restored hash
4. Whether any attention item should block future restores
5. Whether the next build should add a rollback-from-pre-restore-backup preview only.`;
    toast('Restore audit sent to Mission Console.');
}

let lastRestoreAction=null;
let lastRestorePreflight=null;
async function loadRestoreActionList(){
    q('restoreActionStatus').textContent='Loading staging packages...';
    let d=await api('/api/backups/staging_packages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restoreActionStatus').textContent=d?.message||'Could not load staging packages.';
        return;
    }
    let sel=q('restoreActionSelect');
    sel.innerHTML=(d.packages||[]).map(p=>`<option value="${esc(p.stage_dir)}">${esc(p.name)} → ${esc(p.future_target||'unknown target')}</option>`).join('');
    if((d.packages||[]).length){
        q('restoreActionPath').value=d.packages[0].stage_dir;
    }
    q('restoreActionStatus').textContent=`Loaded ${d.packages?.length||0} staging package(s). Run preflight before restore.`;
}
async function preflightRestoreAction(){
    let path=q('restoreActionPath').value||q('restoreActionSelect').value||'';
    if(!path){
        q('restoreActionStatus').textContent='Select a staging package first.';
        return;
    }
    q('restoreActionStatus').textContent='Running restore preflight...';
    let d=await api('/api/backups/restore_final_check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage_dir:path,export:true})});
    lastRestorePreflight=d;
    q('restoreActionResult').textContent=JSON.stringify(d,null,2);
    if(!d?.ok){
        q('restoreActionStatus').textContent=d?.message||'Preflight failed.';
        return;
    }
    q('restoreActionConfirm').value='';
    q('restoreActionConfirm').placeholder=d.future_restore_phrase||'Exact restore phrase unavailable';
    let s=d.summary||{};
    q('restoreActionStatus').textContent=`Preflight complete.
Final status: ${s.final_status}
Hard blocks excluding restore lock: ${s.hard_blocks}
Future restore phrase required:
${d.future_restore_phrase}`;
    q('restoreActionChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.status==='pass'?'ok':(c.status==='block'?'fail':'info')}"><b>${esc(c.id)}</b>${finalBadge(c.status)}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.detail||'')}</div></div>`).join('');
    toast('Restore preflight complete.');
}
async function runSingleFileRestore(){
    let path=q('restoreActionPath').value||q('restoreActionSelect').value||'';
    let confirm=q('restoreActionConfirm').value||'';
    if(!path){
        q('restoreActionStatus').textContent='Select a staging package first.';
        return;
    }
    if(!lastRestorePreflight || (lastRestorePreflight.summary||{}).stage_dir!==path){
        q('restoreActionStatus').textContent='Run restore preflight for this package first.';
        return;
    }
    if(confirm!==lastRestorePreflight.future_restore_phrase){
        q('restoreActionStatus').textContent='Exact confirmation phrase does not match the preflight phrase.';
        return;
    }
    let msg='This will overwrite the original target with the staged file after creating a live-target backup. Continue?';
    if(!window.confirm(msg)){
        q('restoreActionStatus').textContent='Restore cancelled.';
        return;
    }
    if(!window.confirm('Final confirmation: this is the first real single-file restore action. Proceed?')){
        q('restoreActionStatus').textContent='Restore cancelled at final confirmation.';
        return;
    }
    q('restoreActionStatus').textContent='Running single-file restore...';
    let d=await api('/api/backups/single_file_restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage_dir:path,confirm})});
    lastRestoreAction=d;
    q('restoreActionResult').textContent=JSON.stringify(d,null,2);
    let v=d?.verification||{};
    q('restoreActionChecks').innerHTML=(v.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id)}</b>${finalBadge(c.ok?'pass':'block')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No verification checks.';
    if(d?.ok){
        q('restoreActionStatus').textContent=`Single-file restore complete and verified.
Target: ${d.target}
Pre-restore live backup: ${d.pre_restore_live_backup}
Report: ${d.exported?.markdown||''}
Repair log: ${d.repair_action_log?.markdown||''}`;
        toast('Single-file restore complete and verified.');
    }else{
        q('restoreActionStatus').textContent=d?.message||'Restore failed or was blocked.';
        toast('Restore failed or blocked.');
    }
}
function sendRestoreActionToMission(){
    if(!lastRestoreAction){
        toast('Run a restore action first.');
        return;
    }
    go('mission');
    let v=lastRestoreAction.verification||{};
    let h=lastRestoreAction.hashes||{};
    q('input').value=`Please review this Kayock Single-File Restore Action result.

This was the first narrow restore action.

Result:
OK: ${lastRestoreAction.ok}
Message: ${lastRestoreAction.message}
Target: ${lastRestoreAction.target}
Staged copy: ${lastRestoreAction.staged_copy}
Source backup: ${lastRestoreAction.source_backup}
Pre-restore live backup: ${lastRestoreAction.pre_restore_live_backup}
Confirmation phrase: ${lastRestoreAction.confirmation_phrase}

Hashes:
Target before: ${h.target_before}
Live backup: ${h.live_backup}
Staged copy: ${h.staged_copy}
Source backup: ${h.source_backup}
Target after: ${h.target_after}

Verification:
${v.message||''}
${(v.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Reports:
Restore report: ${lastRestoreAction.exported?.markdown||''}
RepairActions log: ${lastRestoreAction.repair_action_log?.markdown||''}

Safety:
Single file only.
From staging package only.
Original target only.
Pre-restore live backup required.
Exact confirmation phrase required.
No folder restore.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the restore was successful
2. Whether the live backup makes rollback safe
3. Whether the post-restore hash verification is sufficient
4. Whether the restore action should stay limited to generated files
5. Whether to build a post-restore audit viewer next.`;
    toast('Restore action result sent to Mission Console.');
}

let lastRestoreFinal=null;
async function loadRestoreFinalList(){
    q('restoreFinalStatus').textContent='Loading staging package list...';
    let d=await api('/api/backups/staging_packages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restoreFinalStatus').textContent=d?.message||'Could not load staging packages.';
        return;
    }
    let sel=q('restoreFinalSelect');
    sel.innerHTML=(d.packages||[]).map(p=>`<option value="${esc(p.stage_dir)}">${esc(p.name)} → ${esc(p.future_target||'unknown target')}</option>`).join('');
    if((d.packages||[]).length){
        q('restoreFinalPath').value=d.packages[0].stage_dir;
    }
    q('restoreFinalStatus').textContent=`Loaded ${d.packages?.length||0} staging package(s). Select one and run final checklist.`;
}
function finalBadge(status){
    status=(status||'block').toLowerCase();
    return `<span class="finalbadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function runRestoreFinal(doExport=false){
    let path=q('restoreFinalPath').value||q('restoreFinalSelect').value||'';
    if(!path){
        q('restoreFinalStatus').textContent='Select a staging package first.';
        return;
    }
    q('restoreFinalStatus').textContent='Running final restore checklist...';
    let d=await api('/api/backups/restore_final_check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage_dir:path,export:doExport})});
    if(!d?.ok){
        q('restoreFinalStatus').textContent=d?.message||'Final checklist failed.';
        return;
    }
    lastRestoreFinal=d;
    let s=d.summary||{};
    q('restoreFinalStatus').textContent=`Final checklist complete.
Final status: ${s.final_status}
Checks: ${s.checks}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding restore lock: ${s.hard_blocks}
Restore allowed now: ${s.restore_allowed_now}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('restoreFinalDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Final Status</div><div class=value>${esc((s.final_status||'').replaceAll('_',' '))}</div></div>
        <div class=vaultmetric><div class=label>Passed</div><div class=value>${s.pass||0}</div></div>
        <div class=vaultmetric><div class=label>Warnings</div><div class=value>${s.warn||0}</div></div>
        <div class=vaultmetric><div class=label>Blocks</div><div class=value>${s.block||0}</div></div>
        <div class=vaultmetric><div class=label>Hard Blocks</div><div class=value>${s.hard_blocks||0}</div></div>
        <div class=vaultmetric><div class=label>Restore Allowed</div><div class=value>${s.restore_allowed_now?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Risk</div><div class=value>${esc(s.preview_risk||'')}</div></div>
        <div class=vaultmetric><div class=label>Target Unchanged</div><div class=value>${s.target_unchanged_since_staging?'YES':'NO'}</div></div>
    </div><div class=status>Restore remains intentionally unavailable. This is final checklist only.</div>`;
    q('restoreFinalChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.status==='pass'?'ok':(c.status==='block'?'fail':'info')}"><b>${esc(c.id)}</b>${finalBadge(c.status)}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.detail||'')}</div></div>`).join('')||'No checks.';
    q('restoreFinalPhrase').innerHTML=`<div class=finalphrase>${esc(d.final_confirmation_phrase||'')}</div><div class=small>This phrase does not unlock restore in this build. Actual restore is still unavailable.</div>`;
    toast('Final checklist complete.');
}
function sendRestoreFinalToMission(){
    if(!lastRestoreFinal){
        toast('Run final checklist first.');
        return;
    }
    let s=lastRestoreFinal.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Restore Final Checklist.

No restore action is requested or possible in this build.

Summary:
Final status: ${s.final_status}
Checks: ${s.checks}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding intentional restore lock: ${s.hard_blocks}
Restore allowed now: ${s.restore_allowed_now}
Stage package: ${s.stage_package}
Stage folder: ${s.stage_dir}
Staged copy: ${s.staged_copy}
Source backup: ${s.source_backup}
Future target: ${s.future_target}
Preview risk: ${s.preview_risk}
Candidate status: ${s.candidate_status}
Target unchanged since staging: ${s.target_unchanged_since_staging}
Read errors: ${s.read_errors}

Final confirmation phrase:
${lastRestoreFinal.final_confirmation_phrase}

Checks:
${(lastRestoreFinal.checks||[]).map(c=>`${c.status.toUpperCase()} — ${c.id}: ${c.message} ${c.detail||''}`).join('\n')}

Hashes:
Source backup: ${(lastRestoreFinal.hashes||{}).source_backup_sha256}
Staged copy: ${(lastRestoreFinal.hashes||{}).staged_copy_sha256}
Target after staging: ${(lastRestoreFinal.hashes||{}).target_sha256_after_staging}
Target now: ${(lastRestoreFinal.hashes||{}).target_sha256_now}

Exported Report:
${lastRestoreFinal.exported?.markdown||'No exported final checklist path'}

Safety:
Final check only.
No restore button.
No restore endpoint.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please decide:
1. Whether the final proof wall is sufficient
2. Whether any warning should block future restore
3. Whether the final confirmation phrase is strong enough
4. Whether restore should remain blocked
5. Whether the next version should still be preview-only or can safely introduce an actual restore action.`;
    toast('Final checklist sent to Mission Console.');
}

let lastStagingPackages=null;
function packageBadge(ok){
    return ok?'<span class="packagebadge ok">PACKAGE OK</span>':'<span class="packagebadge problem">CHECK PACKAGE</span>';
}
async function loadStagingPackages(doExport=false){
    let query=q('stagingPackageFilter').value||'';
    let limit=parseInt(q('stagingPackageLimit').value||'500');
    q('stagingPackageStatus').textContent='Loading staging packages...';
    let d=await api('/api/backups/staging_packages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('stagingPackageStatus').textContent=d?.message||'Could not load staging packages.';
        return;
    }
    lastStagingPackages=d;
    let s=d.summary||{};
    q('stagingPackageStatus').textContent=`Staging packages loaded.
Packages: ${s.packages||0}
OK: ${s.ok||0}
Problems: ${s.problems||0}
Verified: ${s.verified||0}
Live target untouched: ${s.live_target_untouched||0}
Restore allowed now: ${s.restore_allowed_now||0}
Files: ${s.files||0}
Total size: ${fmtBytes(s.bytes||0)}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('stagingPackageDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Packages</div><div class=value>${s.packages||0}</div></div>
        <div class=vaultmetric><div class=label>OK</div><div class=value>${s.ok||0}</div></div>
        <div class=vaultmetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=vaultmetric><div class=label>Verified</div><div class=value>${s.verified||0}</div></div>
        <div class=vaultmetric><div class=label>Untouched</div><div class=value>${s.live_target_untouched||0}</div></div>
        <div class=vaultmetric><div class=label>Restore Allowed</div><div class=value>${s.restore_allowed_now||0}</div></div>
        <div class=vaultmetric><div class=label>Files</div><div class=value>${s.files||0}</div></div>
        <div class=vaultmetric><div class=label>Total Size</div><div class=value>${fmtBytes(s.bytes||0)}</div></div>
    </div><div class=status>Latest package: ${esc(s.latest_package||'none')} | ${esc(s.latest_created||'')}</div>`;
    q('stagingPackageStatusList').innerHTML=(d.by_status||[]).map(x=>`<div class="histrow info"><b>${esc(x.status)}</b><div>Count: ${x.count} | Size: ${fmtBytes(x.bytes)}</div></div>`).join('')||'No status summary.';
    q('stagingPackageRiskList').innerHTML=(d.by_risk||[]).map(x=>`<div class="histrow info"><b>${esc(x.risk)}</b><div>Count: ${x.count} | Size: ${fmtBytes(x.bytes)}</div></div>`).join('')||'No risk summary.';
    q('stagingPackageList').innerHTML=(d.packages||[]).map(p=>`<div class="histrow ${p.ok?'ok':'fail'}"><b>${esc(p.name)}</b>${packageBadge(p.ok)}
<div>Created: ${esc(p.created||'')} | Risk: ${esc(p.preview_risk||'')} | Candidate: ${esc(p.candidate_status||'')}</div>
<div>Verification: ${p.verification_ok} (${p.verification_passed}/${p.verification_checked}) | Live target untouched: ${p.live_target_untouched}</div>
<div>Restore allowed now: ${p.restore_allowed_now}</div>
<div class=vaultpath>Stage folder: ${esc(p.stage_dir||'')}</div>
<div class=vaultpath>Staged copy: ${esc(p.staged_copy||'')}</div>
<div class=vaultpath>Source backup: ${esc(p.source_backup||'')}</div>
<div class=vaultpath>Future target: ${esc(p.future_target||'')}</div>
<div class=small>Future phrase: ${esc(p.future_confirmation_phrase||'')}</div>
<div class=vaultpath>Metadata: ${esc(p.metadata||'')}</div>
<div class=vaultpath>Report: ${esc(p.markdown||'')}</div>
<div class=vaultpath>Repair log: ${esc(p.repair_action_log_markdown||p.repair_action_log_json||'')}</div>
<div class=small>Missing required: ${(p.missing_required||[]).map(esc).join(', ')||'none'}</div>
<details><summary>Included files (${p.file_count||0})</summary>${(p.files||[]).map(f=>`<div class=packagefile>${esc(f.name)} — ${fmtBytes(f.size)} — ${esc(f.path)}</div>`).join('')}</details>
</div>`).join('')||'No staging packages found.';
    toast('Staging packages loaded.');
}
function sendStagingPackagesToMission(){
    if(!lastStagingPackages){
        toast('Load staging packages first.');
        return;
    }
    let s=lastStagingPackages.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Staging Package Inventory.

This is a read-only audit review. No restore action is requested.

Summary:
Packages: ${s.packages}
OK: ${s.ok}
Problems: ${s.problems}
Verified: ${s.verified}
Live target untouched: ${s.live_target_untouched}
Restore allowed now: ${s.restore_allowed_now}
Files: ${s.files}
Total size: ${fmtBytes(s.bytes)}
Scan errors: ${s.scan_errors}
Latest package: ${s.latest_package}
Latest created: ${s.latest_created}

Exported Inventory:
${lastStagingPackages.exported?.markdown||'No exported inventory path'}

Packages:
${(lastStagingPackages.packages||[]).map(p=>`${p.ok?'OK':'PROBLEM'} — ${p.name}
Stage folder: ${p.stage_dir}
Staged copy: ${p.staged_copy}
Source backup: ${p.source_backup}
Future target: ${p.future_target}
Verification OK: ${p.verification_ok}
Verification message: ${p.verification_message}
Live target untouched: ${p.live_target_untouched}
Restore allowed now: ${p.restore_allowed_now}
Candidate status: ${p.candidate_status}
Risk: ${p.preview_risk}
Future phrase: ${p.future_confirmation_phrase}
Missing required: ${(p.missing_required||[]).join(', ')||'none'}
Repair log: ${p.repair_action_log_markdown||p.repair_action_log_json||''}`).join('\n\n')}

Safety:
Read-only viewer.
No restore.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether staging package audit visibility is sufficient
2. Whether any package looks incomplete
3. Whether live-target-untouched proof is visible enough
4. What final metadata is needed before actual restore
5. Whether restore should remain blocked for now.`;
    toast('Staging inventory sent to Mission Console.');
}

let lastRestoreStaging=null;
async function loadRestoreStagingList(){
    q('restoreStagingStatus').textContent='Loading Backup Vault list...';
    let d=await api('/api/backups/vault',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restoreStagingStatus').textContent=d?.message||'Could not load backup list.';
        return;
    }
    let sel=q('restoreStagingSelect');
    sel.innerHTML=(d.backups||[]).map(b=>`<option value="${esc(b.path)}">${esc(b.name)} → ${esc(b.original_target||'unknown target')}</option>`).join('');
    if((d.backups||[]).length){
        q('restoreStagingPath').value=d.backups[0].path;
    }
    q('restoreStagingStatus').textContent=`Loaded ${d.backups?.length||0} backup(s). Type STAGE before staging.`;
}
async function stageRestoreCopy(){
    let path=q('restoreStagingPath').value||q('restoreStagingSelect').value||'';
    let confirm=q('restoreStagingConfirm').value||'';
    if(!path){
        q('restoreStagingStatus').textContent='Select or paste a backup path first.';
        return;
    }
    if(confirm.trim().toUpperCase()!=='STAGE'){
        q('restoreStagingStatus').textContent='Type STAGE to confirm staging-only copy.';
        return;
    }
    if(!window.confirm('Create a staging copy only? This will NOT restore or overwrite the live target.')){
        q('restoreStagingStatus').textContent='Staging cancelled.';
        return;
    }
    q('restoreStagingStatus').textContent='Creating staging copy...';
    let d=await api('/api/backups/restore_staging',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({backup_path:path,confirm})});
    lastRestoreStaging=d;
    if(!d?.ok){
        q('restoreStagingStatus').textContent=d?.message||'Staging copy failed or was blocked.';
    }else{
        q('restoreStagingStatus').textContent=`Staging copy complete.
Stage folder: ${d.stage_dir}
Staged copy: ${d.staged_copy}
Metadata: ${d.metadata}
Markdown: ${d.markdown}
Restore allowed now: ${d.restore_allowed_now}`;
    }
    q('restoreStagingResult').textContent=JSON.stringify(d,null,2);
    let v=d?.verification||{};
    q('restoreStagingChecks').innerHTML=(v.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id)}</b>${gateBadge(c.ok?'pass':'block')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No verification checks.';
    toast(d?.ok?'Restore staging copy complete.':'Restore staging blocked or failed.');
}
function sendRestoreStagingToMission(){
    if(!lastRestoreStaging){
        toast('Run staging copy first.');
        return;
    }
    go('mission');
    let v=lastRestoreStaging.verification||{};
    q('input').value=`Please review this Kayock Restore Staging Copy result.

No restore action was performed. This is staging only.

Summary:
OK: ${lastRestoreStaging.ok}
Message: ${lastRestoreStaging.message}
Stage folder: ${lastRestoreStaging.stage_dir}
Staged copy: ${lastRestoreStaging.staged_copy}
Metadata: ${lastRestoreStaging.metadata}
Markdown report: ${lastRestoreStaging.markdown}
Readiness JSON: ${lastRestoreStaging.readiness}
Preview JSON: ${lastRestoreStaging.preview}
Restore allowed now: ${lastRestoreStaging.restore_allowed_now}

Verification:
${v.message||''}
${(v.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Safety:
No restore to original location.
No live target overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the staging package is trustworthy
2. Whether the live target remained untouched
3. Whether the staged copy hash/size proof is enough
4. Whether a future restore feature still needs another gate
5. Whether restore should remain blocked for now.`;
    toast('Restore staging result sent to Mission Console.');
}

let lastRestoreGate=null;
async function loadRestoreGateList(){
    q('restoreGateStatus').textContent='Loading Backup Vault list...';
    let d=await api('/api/backups/vault',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restoreGateStatus').textContent=d?.message||'Could not load backup list.';
        return;
    }
    let sel=q('restoreGateSelect');
    sel.innerHTML=(d.backups||[]).map(b=>`<option value="${esc(b.path)}">${esc(b.name)} → ${esc(b.original_target||'unknown target')}</option>`).join('');
    if((d.backups||[]).length){
        q('restoreGatePath').value=d.backups[0].path;
    }
    q('restoreGateStatus').textContent=`Loaded ${d.backups?.length||0} backup(s). Select one and run the gate.`;
}
function gateBadge(status){
    status=(status||'info').toLowerCase();
    return `<span class="gatebadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function runRestoreGate(doExport=false){
    let path=q('restoreGatePath').value||q('restoreGateSelect').value||'';
    if(!path){
        q('restoreGateStatus').textContent='Select or paste a backup path first.';
        return;
    }
    q('restoreGateStatus').textContent='Running restore readiness gate...';
    let d=await api('/api/backups/restore_readiness',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({backup_path:path,export:doExport})});
    if(!d?.ok){
        q('restoreGateStatus').textContent=d?.message||'Restore readiness gate failed.';
        return;
    }
    lastRestoreGate=d;
    let s=d.summary||{};
    q('restoreGateStatus').textContent=`Restore readiness gate complete.
Candidate status: ${s.candidate_status}
Gates: ${s.gates}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding restore lock: ${s.hard_blocks}
Restore allowed now: ${s.restore_allowed_now}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('restoreGateDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Candidate</div><div class=value>${esc((s.candidate_status||'').replaceAll('_',' '))}</div></div>
        <div class=vaultmetric><div class=label>Passed</div><div class=value>${s.pass||0}</div></div>
        <div class=vaultmetric><div class=label>Warnings</div><div class=value>${s.warn||0}</div></div>
        <div class=vaultmetric><div class=label>Blocks</div><div class=value>${s.block||0}</div></div>
        <div class=vaultmetric><div class=label>Hard Blocks</div><div class=value>${s.hard_blocks||0}</div></div>
        <div class=vaultmetric><div class=label>Risk</div><div class=value>${esc(s.preview_risk||'')}</div></div>
        <div class=vaultmetric><div class=label>Target Exists</div><div class=value>${s.target_exists?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Same Hash</div><div class=value>${s.same_hash?'YES':'NO'}</div></div>
    </div><div class=status>Restore remains intentionally blocked in this build. This gate is advisory only.</div>`;
    q('restoreGateChecks').innerHTML=(d.gates||[]).map(g=>`<div class="histrow ${g.status==='pass'?'ok':(g.status==='block'?'fail':'info')}"><b>${esc(g.id)}</b>${gateBadge(g.status)}<div>${esc(g.message||'')}</div><div class=vaultpath>${esc(g.detail||'')}</div></div>`).join('')||'No gate checks.';
    q('restoreGatePhrase').innerHTML=`<div class=phrasebox>${esc(d.future_confirmation_phrase||'')}</div><div class=small>This phrase is for a possible future restore build only. It does not unlock restore in this build.</div>`;
    toast('Restore readiness gate complete.');
}
function sendRestoreGateToMission(){
    if(!lastRestoreGate){
        toast('Run the restore gate first.');
        return;
    }
    let s=lastRestoreGate.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Restore Readiness Gate report.

No restore action is requested. Restore remains intentionally blocked.

Summary:
Candidate status: ${s.candidate_status}
Gates: ${s.gates}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding intentional restore lock: ${s.hard_blocks}
Restore allowed now: ${s.restore_allowed_now}
Backup: ${s.backup}
Target: ${s.target}
Preview risk: ${s.preview_risk}
Same hash: ${s.same_hash}
Target exists: ${s.target_exists}
Target inside FOXAI root: ${s.target_inside_root}

Future confirmation phrase:
${lastRestoreGate.future_confirmation_phrase}

Gate Checks:
${(lastRestoreGate.gates||[]).map(g=>`${g.status.toUpperCase()} — ${g.id}: ${g.message} ${g.detail||''}`).join('\n')}

Exported Report:
${lastRestoreGate.exported?.markdown||'No exported readiness report path'}

Please decide:
1. Whether this backup is a valid future restore candidate
2. Whether any warning should become a hard block
3. Whether the future confirmation phrase is strong enough
4. Whether restore should remain blocked
5. What metadata is still missing before actual restore power.`;
    toast('Restore gate report sent to Mission Console.');
}

let lastRestorePreview=null;
async function loadRestoreBackupList(){
    q('restorePreviewStatus').textContent='Loading Backup Vault list...';
    let d=await api('/api/backups/vault',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restorePreviewStatus').textContent=d?.message||'Could not load backup list.';
        return;
    }
    let sel=q('restoreBackupSelect');
    sel.innerHTML=(d.backups||[]).map(b=>`<option value="${esc(b.path)}">${esc(b.name)} → ${esc(b.original_target||'unknown target')}</option>`).join('');
    if((d.backups||[]).length){
        q('restoreBackupPath').value=d.backups[0].path;
    }
    q('restorePreviewStatus').textContent=`Loaded ${d.backups?.length||0} backup(s). Select one and preview.`;
}
function restoreRiskBadge(r){
    r=(r||'low').toLowerCase();
    return `<span class="riskbadge ${r}">${esc(r.toUpperCase())}</span>`;
}
async function previewRestore(doExport=false){
    let path=q('restoreBackupPath').value||q('restoreBackupSelect').value||'';
    if(!path){
        q('restorePreviewStatus').textContent='Select or paste a backup path first.';
        return;
    }
    q('restorePreviewStatus').textContent='Generating restore preview...';
    let d=await api('/api/backups/restore_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({backup_path:path,export:doExport})});
    if(!d?.ok){
        q('restorePreviewStatus').textContent=d?.message||'Restore preview failed.';
        return;
    }
    lastRestorePreview=d;
    let s=d.summary||{};
    q('restorePreviewStatus').textContent=`Restore preview generated.
Risk: ${s.risk}
Backup: ${s.backup}
Target: ${s.target||'unknown'}
Target exists: ${s.target_exists}
Same hash: ${s.same_hash}
Would overwrite: ${s.would_overwrite}
Would create: ${s.would_create}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('restorePreviewDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Risk</div><div class=value>${restoreRiskBadge(s.risk)}</div></div>
        <div class=vaultmetric><div class=label>Target Exists</div><div class=value>${s.target_exists?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Same Hash</div><div class=value>${s.same_hash?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Would Overwrite</div><div class=value>${s.would_overwrite?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Backup Size</div><div class=value>${fmtBytes(s.backup_size)}</div></div>
        <div class=vaultmetric><div class=label>Target Size</div><div class=value>${fmtBytes(s.target_size)}</div></div>
        <div class=vaultmetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=vaultmetric><div class=label>Warnings</div><div class=value>${s.warnings||0}</div></div>
    </div><div class=status>Safety: preview only. No restore operation exists in this build.</div>`;
    let b=d.backup||{}, t=d.target||{}, c=d.comparison||{};
    q('restorePreviewCompare').innerHTML=`<div class="histrow info"><b>Backup</b>
<div class=vaultpath>${esc(b.path||'')}</div>
<div>Type: ${esc(b.type||'')} | Size: ${fmtBytes(b.size)}</div>
<div class=small>SHA256: ${esc(b.sha256||'')}</div>
<div class=small>File-modified time: ${esc(b.file_modified_time||'')}</div>
<div class=small>Created by action: ${esc(b.created_by_action||'')}</div>
<div class=small>Action-created time: ${esc(b.action_created||'')}</div>
<div class=vaultpath>Repair log: ${esc(b.repair_log||'')}</div></div>
<div class="histrow ${t.exists?'ok':'fail'}"><b>Current Target</b>
<div class=vaultpath>${esc(t.path||'unknown')}</div>
<div>Exists: ${t.exists} | Inside FOXAI root: ${t.inside_root}</div>
<div>Size: ${fmtBytes(t.size)}</div>
<div class=small>SHA256: ${esc(t.sha256||'')}</div>
<div class=small>File-modified time: ${esc(t.file_modified_time||'')}</div></div>
<div class="histrow info"><b>Comparison</b>
<div>Same hash: ${c.same_hash}</div>
<div>Size delta if restored: ${fmtBytes(c.size_delta_if_restored)}</div>
<div>Text preview available: ${c.text_preview_available}</div>
<div>Diff truncated: ${c.diff_truncated}</div>
<div class=small>${esc(c.readable_reason||'')}</div></div>
${(d.problems||[]).length?`<div class="histrow fail"><b>Problems</b>${d.problems.map(p=>`<div>❌ ${esc(p)}</div>`).join('')}</div>`:''}
${(d.warnings||[]).length?`<div class="histrow info"><b>Warnings</b>${d.warnings.map(w=>`<div>⚠️ ${esc(w)}</div>`).join('')}</div>`:''}`;
    q('restorePreviewDiff').textContent=(c.diff_preview||'No diff preview available.');
    toast('Restore preview generated.');
}
function sendRestorePreviewToMission(){
    if(!lastRestorePreview){
        toast('Generate a restore preview first.');
        return;
    }
    let s=lastRestorePreview.summary||{}, b=lastRestorePreview.backup||{}, t=lastRestorePreview.target||{}, c=lastRestorePreview.comparison||{};
    go('mission');
    q('input').value=`Please review this Kayock Restore Preview Plan.

No restore action is requested. This is preview-only.

Safety:
No restore button exists.
No overwrite was performed.
No copy-back was performed.
No delete was performed.
No install was performed.
No model cleanup was performed.

Summary:
Risk: ${s.risk}
Backup: ${s.backup}
Target: ${s.target}
Target exists: ${s.target_exists}
Target inside FOXAI root: ${s.target_inside_root}
Same hash: ${s.same_hash}
Would overwrite: ${s.would_overwrite}
Would create: ${s.would_create}
Backup size: ${fmtBytes(s.backup_size)}
Target size: ${fmtBytes(s.target_size)}

Backup:
Name: ${b.name}
Type: ${b.type}
SHA256: ${b.sha256}
Created by action: ${b.created_by_action}
Action-created time: ${b.action_created}
Verified state: ${b.verified_state}
Repair log: ${b.repair_log}

Target:
Path: ${t.path}
Exists: ${t.exists}
SHA256: ${t.sha256}
File-modified time: ${t.file_modified_time}

Problems:
${(lastRestorePreview.problems||[]).join('\n')||'none'}

Warnings:
${(lastRestorePreview.warnings||[]).join('\n')||'none'}

Exported Preview:
${lastRestorePreview.exported?.markdown||'No exported preview path'}

Please determine:
1. Whether this backup is a valid restore candidate
2. Whether the risk level is appropriate
3. Whether the diff/hash metadata is enough
4. What confirmation phrase should be required in a future restore build
5. Whether an actual restore action should remain blocked for now.`;
    toast('Restore preview sent to Mission Console.');
}

let lastBackupVault=null;
function fmtBytes(n){
    n=Number(n||0);
    if(n<1024)return n+' B';
    if(n<1024*1024)return (n/1024).toFixed(1)+' KB';
    if(n<1024*1024*1024)return (n/1024/1024).toFixed(1)+' MB';
    return (n/1024/1024/1024).toFixed(2)+' GB';
}
function assocBadge(b){
    return b.associated?'<span class="backupbadge assoc">ACTION LINKED</span>':'<span class="backupbadge old">OLDER/UNLINKED</span>';
}
async function loadBackupVault(doExport=false){
    let query=q('backupVaultFilter').value||'';
    let limit=parseInt(q('backupVaultLimit').value||'500');
    q('backupVaultStatus').textContent='Loading backup vault...';
    let d=await api('/api/backups/vault',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('backupVaultStatus').textContent=d?.message||'Could not load backup vault.';
        return;
    }
    lastBackupVault=d;
    let s=d.summary||{};
    q('backupVaultStatus').textContent=`Backup vault loaded.
Backups: ${s.backups||0}
Associated with repair actions: ${s.associated||0}
Older/unassociated: ${s.unassociated||0}
Verified action backups: ${s.verified||0}
Total size: ${fmtBytes(s.bytes||0)}
Latest: ${s.latest_backup||'none'}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('backupVaultDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Backups</div><div class=value>${s.backups||0}</div></div>
        <div class=vaultmetric><div class=label>Total Size</div><div class=value>${fmtBytes(s.bytes||0)}</div></div>
        <div class=vaultmetric><div class=label>Linked</div><div class=value>${s.associated||0}</div></div>
        <div class=vaultmetric><div class=label>Older</div><div class=value>${s.unassociated||0}</div></div>
        <div class=vaultmetric><div class=label>Verified</div><div class=value>${s.verified||0}</div></div>
        <div class=vaultmetric><div class=label>Types</div><div class=value>${s.types||0}</div></div>
        <div class=vaultmetric><div class=label>Actions</div><div class=value>${s.actions||0}</div></div>
        <div class=vaultmetric><div class=label>Errors</div><div class=value>${(s.scan_errors||0)+(s.log_errors||0)}</div></div>
    </div><div class=status>Latest backup: ${esc(s.latest_backup||'none')}<br>File-modified time: ${esc(s.latest_file_modified_time||s.latest_modified||'')}<br>Filename timestamp: ${esc(s.latest_backup_filename_time||'')}<br>Action-created time: ${esc(s.latest_action_created||'')}<br>${esc(s.timestamp_note||'File modified time may not equal backup creation time.')}</div>`;
    q('backupVaultTypes').innerHTML=(d.by_type||[]).map(t=>`<div class="histrow info"><b>${esc(t.type)}</b><div>Count: ${t.count} | Size: ${fmtBytes(t.bytes)}</div></div>`).join('')||'No type summary.';
    q('backupVaultActions').innerHTML=(d.by_action||[]).map(a=>`<div class="histrow info"><b>${esc(a.action_id)}</b><div>Count: ${a.count} | Size: ${fmtBytes(a.bytes)}</div><div>Verified: ${a.verified||0} | Older/unverified: ${a.unverified||0}</div></div>`).join('')||'No action summary.';
    q('backupVaultFiles').innerHTML=(d.backups||[]).map(b=>`<div class="histrow ${b.associated?'ok':'info'}"><b>${esc(b.name)}</b>${assocBadge(b)}
<div>Type: ${esc(b.type)} | Size: ${fmtBytes(b.size)}</div><div class=small>File-modified time: ${esc(b.file_modified_time||b.modified||'')}</div><div class=small>Filename timestamp: ${esc(b.backup_filename_time||'')}</div><div class=small>Action-created time: ${esc(b.action_created||'')}</div><div class=small>${esc(b.timestamp_note||'')}</div>
<div class=vaultpath>Backup: ${esc(b.path||'')}</div>
<div class=vaultpath>Original target: ${esc(b.original_target||'unknown')}</div>
<div class=small>Created by: ${esc(b.action_id||'unknown/older backup')} | Verified state: ${esc(b.verified_state||'')}</div>
<div class=vaultpath>Repair log: ${esc(b.log_markdown||b.log_json||'')}</div></div>`).join('')||'No backup files found.';
    toast('Backup vault loaded.');
}
function sendBackupVaultToMission(){
    if(!lastBackupVault){
        toast('Load backup vault first.');
        return;
    }
    let s=lastBackupVault.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Backup Vault inventory.

This is a read-only rollback visibility review. No restore action is requested.

Summary:
Backups: ${s.backups}
Total size: ${fmtBytes(s.bytes)}
Associated with repair actions: ${s.associated}
Older/unassociated backups: ${s.unassociated}
Verified action backups: ${s.verified}
Backup types: ${s.types}
Repair action types: ${s.actions}
Scan errors: ${s.scan_errors}
Log errors: ${s.log_errors}
Latest backup: ${s.latest_backup}
Latest file-modified time: ${s.latest_file_modified_time||s.latest_modified}\nLatest filename timestamp: ${s.latest_backup_filename_time||''}\nLatest action-created time: ${s.latest_action_created||''}\nTimestamp note: ${s.timestamp_note||'File modified time may not equal backup creation time.'}

Exported Inventory:
${lastBackupVault.exported?.markdown||'No exported inventory path'}

By Type:
${(lastBackupVault.by_type||[]).map(t=>`${t.type}: count=${t.count}, size=${fmtBytes(t.bytes)}`).join('\n')}

By Repair Action:
${(lastBackupVault.by_action||[]).map(a=>`${a.action_id}: count=${a.count}, size=${fmtBytes(a.bytes)}, verified=${a.verified||0}, unverified=${a.unverified||0}`).join('\n')}

Recent Backups:
${(lastBackupVault.backups||[]).slice(0,25).map(b=>`${b.name}
Type: ${b.type}
Size: ${fmtBytes(b.size)}
File-modified time: ${b.file_modified_time||b.modified}\nFilename timestamp: ${b.backup_filename_time||''}\nAction-created time: ${b.action_created||''}
Original target: ${b.original_target||'unknown'}
Created by action: ${b.action_id||'unknown/older backup'}
Verified state: ${b.verified_state}
Backup path: ${b.path}
Repair log: ${b.log_markdown||b.log_json||''}`).join('\n\n')}

Please identify:
1. Whether rollback visibility is sufficient
2. Whether backups are being created in the right place
3. Whether any backup looks suspicious or unlinked
4. What metadata should be added before a restore feature exists
5. Whether it is safe to build a preview-only restore planner next.`;
    toast('Backup inventory sent to Mission Console.');
}


























let lastSavedChapterHealth=null;
async function loadSavedChapterHealthCard(doExport=false,prefix='savedChapterHealth',bookSelectId='savedChapterHealthBook'){
    let statusEl=q(prefix+'Status'), bodyEl=q(prefix+'Body');
    if(!statusEl||!bodyEl)return;
    statusEl.textContent='Loading Saved Chapter Health Card...';
    let book=q(bookSelectId)?.value||'book_2';
    let d=await api('/api/writer/saved_chapter_health_card',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',book_id:book,export:doExport})});
    if(!d?.ok){statusEl.textContent=d?.message||'Could not load Saved Chapter Health Card.';return;}
    lastSavedChapterHealth=d;
    let s=d.summary||{};
    statusEl.innerHTML=`<span class="savedHealthBadge ${d.card_state==='clear'?'':'review'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    bodyEl.innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=savedHealthGrid>${(d.compact_metrics||[]).map(m=>`<div class=savedHealthMetric><div class=label>${esc(m.label||'')}</div><div class=value>${esc(m.value||'')}</div></div>`).join('')}</div><div class=savedHealthPath>Book folder: ${esc(s.book_folder||'')}</div>${d.exported?`<div class=savedHealthPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    if(q(prefix+'Attention')){
        let rows=[];
        if((d.missing_or_attention||[]).length){rows.push(...(d.missing_or_attention||[]).map(x=>`<div class="histrow fail"><b>${esc(x.id||'attention')}</b><div>${esc(x.message||'')}</div></div>`));}
        else{rows.push('<div class="histrow ok"><b>No missing saved-chapter items.</b></div>');}
        if((d.advisories||[]).length){rows.push(...(d.advisories||[]).map(x=>`<div class="histrow info"><b>${esc(x.id||'advisory')}</b><div>${esc(x.message||'')}</div></div>`));}
        q(prefix+'Attention').innerHTML=rows.join('');
    }
    if(q(prefix+'Checks'))q(prefix+'Checks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    if(q(prefix+'Safety'))q(prefix+'Safety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Saved Chapter Health Card loaded.');
}
function sendSavedChapterHealthToMission(){
    if(!lastSavedChapterHealth){toast('Load Saved Chapter Health first.');return;}
    let d=lastSavedChapterHealth, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Saved Chapter Health Card.

Milestone:
${d.milestone}
Health: ${d.health_label}
Card state: ${d.card_state}
Card ready: ${d.card_ready}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} — ${s.book_title}
Dashboard ready: ${s.dashboard_ready}
Preview set exists: ${s.preview_set_exists}
Preview set valid: ${s.preview_set_valid}
Preview set status: ${s.preview_set_status}
Expected chapter cards: ${s.expected_chapter_cards}
Markdown cards found: ${s.markdown_cards_found}
Expected targets: ${s.expected_markdown_targets_ok}/${s.expected_markdown_targets}
Continuity handoff exists: ${s.continuity_handoff_exists}
Continuity checks: ${s.continuity_handoff_checks_passed}/${s.continuity_handoff_checks}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Attention items: ${s.missing_or_attention_items}
Advisories: ${s.advisories}
Book folder: ${s.book_folder}

Compact metrics:
${(d.compact_metrics||[]).map(m=>`${m.label}: ${m.value}`).join('\n')}

Attention:
${(d.missing_or_attention||[]).length ? (d.missing_or_attention||[]).map(x=>`${x.id}: ${x.message}`).join('\n') : 'None.'}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Saved Chapter Health Card report'}

Safety:
Read-only saved-chapter health card.
No chapter file creation.
No story-file mutation.
No project creation.
No legacy migration.
No overwrite.
No delete.
No move.
No install.
No model cleanup.

Please determine:
1. Whether v10.12.1 should be marked stable/proven
2. Whether the compact Story Forge saved-chapter health card is accurate
3. Whether the next build should be Chapter Editor Preview.`;
    toast('Saved Chapter Health sent to Mission Console.');
}























let lastChapterProseContinueGate=null;
async function loadChapterProseContinueGate(doExport=false){
    if(!q('chapterProseContinueStatus'))return;
    q('chapterProseContinueStatus').textContent='Loading Chapter Prose Continue Gate...';
    let body={book_id:q('chapterProseContinueBook')?.value||'book_2',chapter_number:parseInt(q('chapterProseContinueChapter')?.value||'2'),continue_mode:q('chapterProseContinueMode')?.value||'append_to_latest',approval_phrase:q('chapterProseContinuePhrase')?.value||'',ai_visible_goal:q('chapterProseContinueAiVisible')?.value||'',proposed_continuation:q('chapterProseContinueText')?.value||'',export:doExport};
    let d=await api('/api/writer/chapter_prose_continue_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('chapterProseContinueStatus').textContent=(d?.message||d?.error||'Could not load Chapter Prose Continue Gate.');return;}
    lastChapterProseContinueGate=d;
    let s=d.summary||{}, p=d.continue_preview||{}, priv=d.private_human_screen_contract||{};
    q('chapterProseContinueStatus').innerHTML=`<span class="chapterContinueBadge ${d.gate_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterProseContinueSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=chapterProseGrid><div class=chapterProseMetric><div class=label>Gate Ready</div><div class=value>${d.gate_ready?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>Latest</div><div class=value>${esc(s.latest_label||'')}</div></div><div class=chapterProseMetric><div class=label>Next</div><div class=value>${esc(s.next_label||'')}</div></div><div class=chapterProseMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>Private Sent</div><div class=value>${s.private_text_received_by_endpoint?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=muted>Save enabled this build: ${s.continue_save_enabled_this_build?'YES':'NO'} | Safe to save later: ${s.safe_to_save_later?'YES':'NO'}</div>${d.exported?`<div class=muted>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('chapterProseContinuePrivacy').textContent=Object.entries(priv).map(([k,v])=>`${k}: ${Array.isArray(v)?v.join(', '):v}`).join('\n');
    q('chapterProseContinueAdded').innerHTML=(p.added_lines||[]).map(x=>`<div class="histrow ok"><b>Added</b><div>${esc(x)}</div></div>`).join('')||'No added lines.';
    q('chapterProseContinueDiff').textContent=(p.line_diff||[]).join('\n')||'No diff.';
    q('chapterProseContinuePreview').textContent=p.new_markdown_preview||'No preview.';
    q('chapterProseContinueChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    toast('Chapter Prose Continue Gate loaded.');
}
function sendChapterProseContinueGateToMission(){
    if(!lastChapterProseContinueGate){toast('Load Chapter Prose Continue Gate first.');return;}
    let d=lastChapterProseContinueGate, s=d.summary||{}, p=d.continue_preview||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Prose Continue Gate report.\n\nMilestone: ${d.milestone}\nHealth: ${d.health_label}\nGate ready: ${d.gate_ready}\nLatest: ${s.latest_label}\nNext preview: ${s.next_label}\nPhrase matched: ${s.phrase_matches}\nPrivate text received by endpoint: ${s.private_text_received_by_endpoint}\nPrivate text stored or echoed: ${s.private_text_stored_or_echoed}\nChecks: ${s.checks_passed}/${s.checks}\nProblems: ${s.problems}\n\nProposed continuation:\n${p.proposed_continuation||''}\n\nSafety: no draft save, no chapter edit, no story mutation, no overwrite, no delete, no move, Private Human Screen excluded.\n\nPlease determine whether v10.14.7 should be marked stable/proven.`;
    toast('Chapter Prose Continue Gate sent to Mission Console.');
}


let lastChapterProseContinueSave=null;
async function loadChapterProseContinueSave(execute=false,doExport=false){
    if(!q('chapterProseContinueSaveStatus'))return;
    q('chapterProseContinueSaveStatus').textContent=execute?'Running Chapter Prose Continue Save...':'Loading Chapter Prose Continue Save preview...';
    let body={book_id:q('chapterProseContinueSaveBook')?.value||'book_2',chapter_number:parseInt(q('chapterProseContinueSaveChapter')?.value||'2'),continue_mode:q('chapterProseContinueSaveMode')?.value||'continue_from_latest',approval_phrase:q('chapterProseContinueSavePhrase')?.value||'',ai_visible_goal:q('chapterProseContinueSaveAiVisible')?.value||'',proposed_continuation:q('chapterProseContinueSaveText')?.value||'',execute:!!execute,export:!!doExport};
    let d=await api('/api/writer/chapter_prose_continue_save_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('chapterProseContinueSaveStatus').textContent=(d?.message||d?.error||'Could not load Chapter Prose Continue Save.');return;}
    lastChapterProseContinueSave=d;
    let s=d.summary||{}, p=d.continue_preview||{}, priv=d.private_human_screen_contract||{};
    q('chapterProseContinueSaveStatus').innerHTML=`<span class="chapterContinueBadge ${d.saved?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span> ${esc(d.message||'')}`;
    q('chapterProseContinueSaveSummary').innerHTML=`<div class=chapterProseMetrics><div class=chapterProseMetric><div class=label>Status</div><div class=value>${esc(s.status||'')}</div></div><div class=chapterProseMetric><div class=label>Allowed</div><div class=value>${s.action_allowed?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>Latest</div><div class=value>${esc(s.latest_label||'')}</div></div><div class=chapterProseMetric><div class=label>Next</div><div class=value>${esc(s.next_label||'')}</div></div><div class=chapterProseMetric><div class=label>Words</div><div class=value>${s.new_words||0}</div></div><div class=chapterProseMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'MATCH':'NO'}</div></div><div class=chapterProseMetric><div class=label>Collisions</div><div class=value>${s.collision_targets||0}</div></div><div class=chapterProseMetric><div class=label>Post</div><div class=value>${s.post_checks_passed||0}/${s.post_checks||0}</div></div></div>${d.exported?`<div class=muted>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('chapterProseContinueSavePrivacy').textContent=JSON.stringify(priv,null,2);
    q('chapterProseContinueSaveFiles').innerHTML=(d.written_files||[]).map(x=>`<div class="histrow ok"><b>WRITTEN</b><div>${esc(x)}</div></div>`).join('')||'No files written.';
    q('chapterProseContinueSaveBlockers').innerHTML=(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No blockers</b><div>Save preflight is clear.</div></div>';
    q('chapterProseContinueSavePreflight').innerHTML=(d.preflight_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No preflight checks.';
    q('chapterProseContinueSavePost').innerHTML=(d.post_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No post-save checks yet.';
    q('chapterProseContinueSavePreview').textContent=p.new_markdown_preview||'No preview.';
    toast('Chapter Prose Continue Save loaded.');
}
function sendChapterProseContinueSaveToMission(){
    if(!lastChapterProseContinueSave){toast('Load Chapter Prose Continue Save first.');return;}
    let d=lastChapterProseContinueSave, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Prose Continue Save Approved Action report.\n\nMilestone: ${d.milestone}\nHealth: ${d.health_label}\nStatus: ${s.status}\nSaved: ${d.saved}\nAction allowed: ${s.action_allowed}\nLatest: ${s.latest_label}\nNext: ${s.next_label}\nPhrase matched: ${s.phrase_matches}\nPrivate text received by endpoint: ${s.private_text_received_by_endpoint}\nPrivate text stored or echoed: ${s.private_text_stored_or_echoed}\nCreated files: ${s.created_files}\nWritten files: ${s.written_files}\nPost checks: ${s.post_checks_passed}/${s.post_checks}\nProblems: ${s.problems}\nErrors: ${s.errors}\n\nSafety: exact phrase required, no overwrite, no delete, no move, no chapter edit, no story mutation, Private Human Screen excluded.\n\nPlease determine whether v10.14.8 should be marked stable/proven.`;
    toast('Chapter Prose Continue Save sent to Mission Console.');
}


let lastChapterProseContinueVerify=null;
async function loadChapterProseContinueVerify(doExport=false){
    if(!q('chapterProseContinueVerifyStatus'))return;
    q('chapterProseContinueVerifyStatus').textContent='Loading Chapter Prose Continue Refresh / Compare...';
    let body={book_id:q('chapterProseContinueVerifyBook')?.value||'book_2',chapter_number:parseInt(q('chapterProseContinueVerifyChapter')?.value||'2'),from_version:parseInt(q('chapterProseContinueVerifyFrom')?.value||'4'),to_version:parseInt(q('chapterProseContinueVerifyTo')?.value||'5'),export:!!doExport};
    let d=await api('/api/writer/chapter_prose_continue_refresh_compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('chapterProseContinueVerifyStatus').textContent=(d?.message||d?.error||'Could not load Chapter Prose Continue Refresh / Compare.');return;}
    lastChapterProseContinueVerify=d;
    let s=d.summary||{}, c=d.compare||{};
    q('chapterProseContinueVerifyStatus').innerHTML=`<span class="chapterContinueBadge ${d.refresh_compare_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span> ${esc(d.message||'')}`;
    q('chapterProseContinueVerifySummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=chapterProseMetrics><div class=chapterProseMetric><div class=label>Ready</div><div class=value>${d.refresh_compare_ready?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>From</div><div class=value>${esc(s.from_label||'')}</div></div><div class=chapterProseMetric><div class=label>To</div><div class=value>${esc(s.to_label||'')}</div></div><div class=chapterProseMetric><div class=label>Latest</div><div class=value>${esc(s.latest_label||'')}</div></div><div class=chapterProseMetric><div class=label>Added Words</div><div class=value>${s.added_words||0}</div></div><div class=chapterProseMetric><div class=label>Private Used</div><div class=value>${s.private_human_screen_used?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div><div class=chapterProseMetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div></div>${d.exported?`<div class=muted>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('chapterProseContinueVerifyVersions').innerHTML=(d.versions||[]).map(x=>`<div class="histrow ${x.verified?'ok':'fail'}"><b>${esc(x.label||'version')}</b><div>Status: ${esc(x.status||'')} | Words: ${x.word_count||0} | Hash OK: ${x.hash_ok} | Count OK: ${x.word_count_ok}</div><div>Created by: ${esc(x.created_by||'')}</div><div>Continues from: ${esc(String(x.continues_from_version??''))} | Previous hash OK: ${x.previous_hash_ok}</div><div class=muted>${esc(x.draft_markdown?.path||'')}</div></div>`).join('')||'No versions loaded.';
    q('chapterProseContinueVerifyAdded').innerHTML=(c.added_lines||[]).map(x=>`<div class="histrow ok"><b>Added</b><div>${esc(x)}</div></div>`).join('')||'No added lines.';
    q('chapterProseContinueVerifyRemoved').innerHTML=(c.removed_lines||[]).map(x=>`<div class="histrow fail"><b>Removed</b><div>${esc(x)}</div></div>`).join('')||'No removed lines.';
    q('chapterProseContinueVerifyDiff').textContent=(c.line_diff||[]).join('\n')||'No diff.';
    q('chapterProseContinueVerifyChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterProseContinueVerifySafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Prose Continue Refresh / Compare loaded.');
}
function sendChapterProseContinueVerifyToMission(){
    if(!lastChapterProseContinueVerify){toast('Load Chapter Prose Continue Verify first.');return;}
    let d=lastChapterProseContinueVerify, s=d.summary||{}, c=d.compare||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Prose Continue Refresh / Compare report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Refresh / Compare ready: ${d.refresh_compare_ready}

Summary:
Book: ${s.book_id}
Chapter: ${s.chapter_number}
From: ${s.from_label}
To: ${s.to_label}
Latest: ${s.latest_label}
To version exists: ${s.to_version_exists}
To metadata/evidence exist: ${s.to_metadata_exists}/${s.to_evidence_exists}
Hash verified: ${s.to_hash_ok}
Word count verified: ${s.to_word_count_ok}
Continues from prior: ${s.to_continues_from_from_version}
Previous hash matches: ${s.to_previous_hash_matches_from}
Added words: ${s.added_words}
Removed words: ${s.removed_words}
Private Human Screen used: ${s.private_human_screen_used}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Errors: ${s.errors}

Added lines:
${(c.added_lines||[]).join('\n')}

Safety: read-only verify, no write, no overwrite, no delete, no move, no chapter edit, no story mutation, Private Human Screen was not used.

Please determine whether v10.14.9 should be marked stable/proven.`;
    toast('Chapter Prose Continue Verify sent to Mission Console.');
}


let lastChapterProseWorkspace=null;
function chapterProsePrivateKey(){return 'kayock.privatePane.chapterProse.'+(q('chapterProseWorkspaceBook')?.value||'book_2')+'.chapter_'+(q('chapterProseWorkspaceChapter')?.value||'2');}
function saveChapterProsePrivatePane(){let el=q('chapterProsePrivatePane'); if(!el)return; localStorage.setItem(chapterProsePrivateKey(),el.value||''); q('chapterProsePrivateStatus').textContent='Private pane saved locally only. It was not sent to the AI or server.'; toast('Private pane saved locally.');}
function loadChapterProsePrivatePane(){let el=q('chapterProsePrivatePane'); if(!el)return; el.value=localStorage.getItem(chapterProsePrivateKey())||''; q('chapterProsePrivateStatus').textContent='Private pane loaded from local browser storage only. It was not sent to the AI or server.';}
function clearChapterProsePrivatePane(){let el=q('chapterProsePrivatePane'); if(!el)return; if(!confirm('Clear the local private pane for this book/chapter?'))return; localStorage.removeItem(chapterProsePrivateKey()); el.value=''; q('chapterProsePrivateStatus').textContent='Private pane cleared from local browser storage.'; toast('Private pane cleared.');}
async function loadChapterProseWorkspace(doExport=false){
    if(!q('chapterProseWorkspaceStatus'))return;
    loadChapterProsePrivatePane();
    q('chapterProseWorkspaceStatus').textContent='Loading Chapter Prose Workspace...';
    let body={book_id:q('chapterProseWorkspaceBook')?.value||'book_2',chapter_number:parseInt(q('chapterProseWorkspaceChapter')?.value||'2'),ai_visible_goal:q('chapterProseAiVisible')?.value||'',export:doExport};
    let d=await api('/api/writer/chapter_prose_workspace',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('chapterProseWorkspaceStatus').textContent=d?.message||'Could not load Chapter Prose Workspace.';return;}
    lastChapterProseWorkspace=d;
    let s=d.summary||{}, w=d.workspace||{}, latest=d.latest_version||{};
    q('chapterProseWorkspaceStatus').innerHTML=`<span class="chapterProseBadge ${d.workspace_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterProseLatestSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=chapterProseGrid><div class=chapterProseMetric><div class=label>Ready</div><div class=value>${d.workspace_ready?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>Latest</div><div class=value>${esc(s.latest_label||'')}</div></div><div class=chapterProseMetric><div class=label>Words</div><div class=value>${s.latest_words||0}</div></div><div class=chapterProseMetric><div class=label>Private Sent</div><div class=value>${s.private_text_received_by_endpoint?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>Critical</div><div class=value>${s.critical_checks_passed||0}/${s.critical_checks||0}</div></div><div class=chapterProseMetric><div class=label>Draft Review</div><div class=value>${s.draft_review_checks_passed||0}/${s.draft_review_checks||0}</div></div><div class=chapterProseMetric><div class=label>Poetry</div><div class=value>${s.poetry_studio_supported?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>D&D</div><div class=value>${s.dnd_world_builder_supported?'YES':'NO'}</div></div><div class=chapterProseMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=muted>Button diagnostic: endpoint answered; workspace ready is based on privacy/read-only critical checks. Draft-history checks remain visible below for review.</div>${d.exported?`<div class=muted>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('chapterProseLatestPreview').textContent=latest.preview||'No latest preview.';
    let priv=w.private_author_screen||{};
    q('chapterProsePrivacyContract').textContent=Object.entries(priv).map(([k,v])=>`${k}: ${Array.isArray(v)?v.join(', '):v}`).join('\n');
    let plan=w.reusable_component_plan||{};
    q('chapterProseReusablePlan').innerHTML=`<div class="histrow ok"><b>Reusable Component Ready</b><div>${plan.reusable_component_ready?'YES':'NO'}</div></div><div class="histrow ok"><b>Supported Modules</b><div>${esc((plan.supported_modules||[]).join(' | '))}</div></div><div class="histrow ok"><b>Poetry Use</b><div>${esc(plan.poetry_use||'')}</div></div><div class="histrow ok"><b>D&D / AI DM Use</b><div>${esc(plan.dnd_use||'')}</div></div><div class="histrow ok"><b>Fog of War Rule</b><div>${esc(plan.fog_of_war_rule||'')}</div></div>`;
    q('chapterProseWorkspaceChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterProseWorkspaceSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Prose Workspace loaded.');
}
function sendChapterProseWorkspaceToMission(){
    if(!lastChapterProseWorkspace){toast('Load Chapter Prose Workspace first.');return;}
    let d=lastChapterProseWorkspace, s=d.summary||{}, w=d.workspace||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Prose Workspace report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Workspace ready: ${d.workspace_ready}
Critical workspace ready: ${s.critical_workspace_ready}
Draft chain ready: ${s.draft_chain_ready}
Critical checks: ${s.critical_checks_passed}/${s.critical_checks}
Draft review checks: ${s.draft_review_checks_passed}/${s.draft_review_checks}

Latest draft:
Latest: ${s.latest_label}
Status: ${s.latest_status}
Words: ${s.latest_words}
Hash OK: ${s.latest_hash_ok}
Word count OK: ${s.latest_word_count_ok}
All versions fully verified: ${s.all_versions_fully_verified}

AI-visible goal:
${q('chapterProseAiVisible')?.value||''}

Private Human Screen contract:
AI cannot read it by default: ${w.private_author_screen?.ai_cannot_read_by_default}
Excluded from AI prompts: ${w.private_author_screen?.excluded_from_ai_prompts}
Excluded from reports: ${w.private_author_screen?.excluded_from_reports}
Private text received by endpoint: ${w.private_author_screen?.private_text_received_by_endpoint}
Private text stored or echoed: ${w.private_author_screen?.private_text_stored_or_echoed}

Reusable modules:
${(w.reusable_component_plan?.supported_modules||[]).join('\n')}

Safety:
Read-only workspace.
No draft save.
No chapter-file edit.
No story mutation.
No overwrite.
No delete.
No move.

Please determine whether v10.14.6 should be marked stable/proven.`;
    toast('AI-visible workspace sent to Mission. Private pane was not included.');
}

let lastRealProseEditVerify=null;
async function loadRealProseEditVerify(doExport=false){
    if(!q('realProseEditVerifyStatus'))return;
    q('realProseEditVerifyStatus').textContent='Loading Real Prose Edit Refresh / Compare...';
    let body={book_id:q('realProseEditVerifyBook')?.value||'book_2',chapter_number:parseInt(q('realProseEditVerifyChapter')?.value||'2'),from_version:parseInt(q('realProseEditVerifyFrom')?.value||'3'),to_version:parseInt(q('realProseEditVerifyTo')?.value||'4'),export:doExport};
    let d=await api('/api/writer/real_prose_edit_refresh_compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('realProseEditVerifyStatus').textContent=d?.message||'Could not load Real Prose Edit Verify.';return;}
    lastRealProseEditVerify=d;
    let s=d.summary||{}, c=d.compare||{};
    q('realProseEditVerifyStatus').innerHTML=`<span class="realProseEditVerifyBadge ${d.edit_refresh_compare_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('realProseEditVerifySummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=realProseEditVerifyGrid><div class=realProseEditVerifyMetric><div class=label>Ready</div><div class=value>${d.edit_refresh_compare_ready?'YES':'NO'}</div></div><div class=realProseEditVerifyMetric><div class=label>Versions</div><div class=value>${s.versions_loaded||0}</div></div><div class=realProseEditVerifyMetric><div class=label>Latest</div><div class=value>${esc(s.latest_label||'')}</div></div><div class=realProseEditVerifyMetric><div class=label>Trap Ending</div><div class=value>${s.revised_trap_ending_present_in_v004?'YES':'NO'}</div></div><div class=realProseEditVerifyMetric><div class=label>Prior Replaced</div><div class=value>${s.prior_short_ending_replaced?'YES':'NO'}</div></div><div class=realProseEditVerifyMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=realProseEditVerifyPath>Drafts folder: ${esc(s.drafts_folder||'')}</div>${d.exported?`<div class=realProseEditVerifyPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('realProseEditVerifyVersions').innerHTML=(d.versions||[]).map(x=>`<div class="histrow ${x.verified?'ok':'fail'}"><b>${esc(x.label||'version')}</b><div>Status: ${esc(x.status||'')} | Words: ${x.word_count||0} | Hash OK: ${x.hash_ok} | Count OK: ${x.word_count_ok}</div><div>Created by: ${esc(x.created_by||'')}</div><div>Trap ending: ${x.contains_revised_trap_ending} | Prior short ending: ${x.contains_prior_short_ending}</div><div class=realProseEditVerifyPath>${esc(x.draft_markdown?.path||'')}</div></div>`).join('')||'No versions loaded.';
    q('realProseEditVerifyAdded').innerHTML=(c.added_lines||[]).map(x=>`<div class="histrow ok"><b>Added</b><div class=rpeadd>${esc(x)}</div></div>`).join('')||'No added lines.';
    q('realProseEditVerifyRemoved').innerHTML=(c.removed_lines||[]).map(x=>`<div class="histrow fail"><b>Removed</b><div class=rperemove>${esc(x)}</div></div>`).join('')||'No removed lines.';
    q('realProseEditVerifyDiff').textContent=(c.line_diff||[]).join('\n')||'No diff.';
    q('realProseEditVerifyChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('realProseEditVerifySafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Real Prose Edit Verify loaded.');
}
function sendRealProseEditVerifyToMission(){
    if(!lastRealProseEditVerify){toast('Load Real Prose Edit Verify first.');return;}
    let d=lastRealProseEditVerify, s=d.summary||{}, c=d.compare||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Real Prose Edit Refresh / Compare report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Edit Refresh / Compare ready: ${d.edit_refresh_compare_ready}

Summary:
Book: ${s.book_id}
Chapter: ${s.chapter_number}
Versions loaded: ${s.versions_loaded}
Version labels: ${(s.version_labels||[]).join(', ')}
Has v001: ${s.has_v001}
Has v002: ${s.has_v002}
Has v003: ${s.has_v003}
Has v004: ${s.has_v004}
Latest: ${s.latest_label}
Latest is v004: ${s.latest_is_v004}
v004 created by: ${s.v004_created_by}
v004 continues from v003: ${s.v004_continues_from_v003}
v004 previous hash matches v003: ${s.v004_previous_hash_matches_v003}
v004 status real_prose_draft: ${s.v004_status_real_prose_draft}
Revised trap ending present: ${s.revised_trap_ending_present_in_v004}
Prior short ending replaced: ${s.prior_short_ending_replaced}
All hashes verified: ${s.all_hashes_verified}
All word counts verified: ${s.all_word_counts_verified}
All versions fully verified: ${s.all_versions_fully_verified}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}

Compare:
From v${s.from_version} words: ${s.from_words}
To v${s.to_version} words: ${s.to_words}
Word delta: ${s.word_delta}
Added words: ${s.added_words}
Removed words: ${s.removed_words}

Added lines:
${(c.added_lines||[]).join('\n')||'None.'}

Removed lines:
${(c.removed_lines||[]).join('\n')||'None.'}

Safety:
Read-only verify.
No draft save.
No chapter-file edit.
No story mutation.
No overwrite.
No delete.
No move.

Please determine whether v10.14.5 should be marked stable/proven.`;
    toast('Real Prose Edit Verify sent to Mission Console.');
}

let lastRealProseEditSave=null;
async function loadRealProseEditSave(execute=false){
    if(!q('realProseEditSaveStatus'))return;
    q('realProseEditSaveStatus').textContent=execute?'Requesting approved real prose edit save...':'Loading real prose edit save preview...';
    let body={book_id:q('realProseEditSaveBook')?.value||'book_2',chapter_number:parseInt(q('realProseEditSaveChapter')?.value||'2'),edit_mode:q('realProseEditSaveMode')?.value||'revise_latest_real_prose',approval_phrase:q('realProseEditSavePhrase')?.value||'',revised_prose_text:q('realProseEditSaveText')?.value||'',execute:execute,export:true};
    let d=await api('/api/writer/real_prose_edit_save_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('realProseEditSaveStatus').textContent=d?.message||'Could not load Real Prose Edit Save Action.';return;}
    lastRealProseEditSave=d;
    let s=d.summary||{}, ep=d.edit_save||{};
    let cls=d.status==='blocked'?'blocked':(d.status==='error'?'bad':'');
    q('realProseEditSaveStatus').innerHTML=`<span class="realProseEditSaveBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('realProseEditSaveSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=realProseEditSaveGrid><div class=realProseEditSaveMetric><div class=label>Status</div><div class=value>${esc(s.status||'')}</div></div><div class=realProseEditSaveMetric><div class=label>Allowed</div><div class=value>${s.action_allowed?'YES':'NO'}</div></div><div class=realProseEditSaveMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=realProseEditSaveMetric><div class=label>Next</div><div class=value>v${String(s.next_version||0).padStart(3,'0')}</div></div><div class=realProseEditSaveMetric><div class=label>Words</div><div class=value>${s.new_words||0}</div></div><div class=realProseEditSaveMetric><div class=label>Post</div><div class=value>${s.post_checks_passed||0}/${s.post_checks||0}</div></div></div><div class=realProseEditSavePath>Next draft: ${esc(s.next_draft_path||'')}</div>${d.exported?`<div class=realProseEditSavePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let parts=(d.selected_targets||[]).map(t=>`<div class="histrow ${t.would_overwrite?'fail':'ok'}"><b>${esc(t.kind||'target')}</b><div>Exists before save: ${t.exists} | Would overwrite: ${t.would_overwrite}</div><div class=realProseEditSavePath>${esc(t.path||'')}</div></div>`);
    (d.created_files||[]).forEach(p=>parts.push(`<div class="histrow ok"><b>Created file</b><div class=realProseEditSavePath>${esc(p)}</div></div>`));
    (d.blockers||[]).forEach(b=>parts.push(`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));
    (d.errors||[]).forEach(e=>parts.push(`<div class="histrow fail"><b>${esc(e.id||'error')}</b><div>${esc(e.message||'')}</div></div>`));
    q('realProseEditSaveTargets').innerHTML=parts.join('')||'No targets.';
    q('realProseEditSaveAdded').innerHTML=(ep.added_lines||[]).map(x=>`<div class="histrow ok"><b>Added</b><div>${esc(x)}</div></div>`).join('')||'No added lines.';
    q('realProseEditSaveRemoved').innerHTML=(ep.removed_lines||[]).map(x=>`<div class="histrow fail"><b>Removed</b><div>${esc(x)}</div></div>`).join('')||'No removed lines.';
    q('realProseEditSavePreview').textContent=ep.new_markdown_preview||'No preview.';
    q('realProseEditSavePreflight').innerHTML=(d.preflight_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No preflight.';
    q('realProseEditSavePost').innerHTML=(d.post_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No post checks.';
    q('realProseEditSaveSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Real Prose Edit Save report loaded.');
}
function sendRealProseEditSaveToMission(){
    if(!lastRealProseEditSave){toast('Load Real Prose Edit Save first.');return;}
    let d=lastRealProseEditSave, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Real Prose Edit Save Approved Action report.\n\nMilestone: ${d.milestone}\nHealth: ${d.health_label}\nStatus: ${d.status}\n\nSummary:\nBook: ${s.book_id}\nChapter: ${s.chapter_number}\nExecute requested: ${s.execute_requested}\nAction allowed: ${s.action_allowed}\nPhrase matches: ${s.phrase_matches}\nLatest version: v${String(s.latest_version||0).padStart(3,'0')}\nNext version: v${String(s.next_version||0).padStart(3,'0')}\nLatest words: ${s.latest_words}\nRevised words: ${s.revised_words}\nNew words: ${s.new_words}\nWord delta: ${s.word_delta}\nEdit mode: ${s.edit_mode}\nCollision targets: ${s.collision_targets}\nBlockers: ${s.blockers}\nErrors: ${s.errors}\nPreflight: ${s.preflight_checks_passed}/${s.preflight_checks}\nCreated files: ${s.created_files}\nWritten files: ${s.written_files}\nPost checks: ${s.post_checks_passed}/${s.post_checks}\nProblems: ${s.problems}\nNext draft: ${s.next_draft_path}\nMetadata: ${s.metadata_path}\nEvidence: ${s.evidence_path}\n\nCreated files:\n${(d.created_files||[]).join('\n')||'None.'}\n\nSafety:\nRequires exact phrase.\nRequires revised real prose text.\nRequires latest draft hash verification.\nRequires no collision.\nCreates edited real-prose Markdown, metadata JSON, and save evidence JSON.\nNo chapter-file edit.\nNo story mutation.\nNo overwrite.\nNo delete.\nNo move.\n\nPlease determine whether v10.14.4 should be marked stable/proven and whether v004 edited real prose was saved safely.`;
    toast('Real Prose Edit Save sent to Mission Console.');
}

let lastRealProseEditorGate=null;
async function loadRealProseEditorGate(doExport=false){
    if(!q('realProseEditorStatus'))return;
    q('realProseEditorStatus').textContent='Loading Real Prose Editor Gate...';
    let body={book_id:q('realProseEditorBook')?.value||'book_2',chapter_number:parseInt(q('realProseEditorChapter')?.value||'2'),edit_mode:q('realProseEditorMode')?.value||'revise_latest_real_prose',approval_phrase:q('realProseEditorPhrase')?.value||'',revised_prose_text:q('realProseEditorText')?.value||'',export:doExport};
    let d=await api('/api/writer/real_prose_editor_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('realProseEditorStatus').textContent=d?.message||'Could not load Real Prose Editor Gate.';return;}
    lastRealProseEditorGate=d;
    let s=d.summary||{}, ep=d.edit_preview||{};
    q('realProseEditorStatus').innerHTML=`<span class="realProseEditorBadge ${d.gate_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('realProseEditorSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=realProseEditorGrid><div class=realProseEditorMetric><div class=label>Gate</div><div class=value>${d.gate_ready?'READY':'REVIEW'}</div></div><div class=realProseEditorMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=realProseEditorMetric><div class=label>Next</div><div class=value>v${String(s.next_version||0).padStart(3,'0')}</div></div><div class=realProseEditorMetric><div class=label>Words</div><div class=value>${s.revised_words||0}</div></div><div class=realProseEditorMetric><div class=label>Delta</div><div class=value>${s.word_delta||0}</div></div><div class=realProseEditorMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=realProseEditorPath>Next draft: ${esc(s.next_draft_path||'')}</div>${d.exported?`<div class=realProseEditorPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('realProseEditorTargets').innerHTML=(d.selected_targets||[]).map(t=>`<div class="histrow ${t.would_overwrite?'fail':'ok'}"><b>${esc(t.kind||'target')}</b><div>Exists: ${t.exists} | Would overwrite: ${t.would_overwrite}</div><div class=realProseEditorPath>${esc(t.path||'')}</div></div>`).join('')||'No targets.';
    q('realProseEditorAdded').innerHTML=(ep.added_lines||[]).map(x=>`<div class="histrow ok"><b>Added</b><div class=rpeadd>${esc(x)}</div></div>`).join('')||'No added lines.';
    q('realProseEditorRemoved').innerHTML=(ep.removed_lines||[]).map(x=>`<div class="histrow fail"><b>Removed</b><div class=rperemove>${esc(x)}</div></div>`).join('')||'No removed lines.';
    q('realProseEditorDiff').textContent=(ep.line_diff||[]).join('\n')||'No diff.';
    q('realProseEditorPreview').textContent=ep.new_markdown_preview||'No preview.';
    q('realProseEditorBlockers').innerHTML=(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No blockers.</b></div>';
    q('realProseEditorChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('realProseEditorSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Real Prose Editor Gate loaded.');
}
function sendRealProseEditorGateToMission(){
    if(!lastRealProseEditorGate){toast('Load Real Prose Editor Gate first.');return;}
    let d=lastRealProseEditorGate, s=d.summary||{}, ep=d.edit_preview||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Real Prose Editor Gate report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Gate ready: ${d.gate_ready}

Summary:
Book: ${s.book_id}
Chapter: ${s.chapter_number}
Latest version: v${String(s.latest_version||0).padStart(3,'0')}
Next version: v${String(s.next_version||0).padStart(3,'0')}
Latest words: ${s.latest_words}
Revised words: ${s.revised_words}
Word delta: ${s.word_delta}
Edit mode: ${s.edit_mode}
Latest is real prose draft: ${s.latest_is_real_prose_draft}
Phrase matches: ${s.phrase_matches}
Collision targets: ${s.collision_targets}
Blockers: ${s.blockers}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Safe to save later: ${s.safe_to_save_later}

Added lines:
${(ep.added_lines||[]).join('\n')||'None.'}

Removed lines:
${(ep.removed_lines||[]).join('\n')||'None.'}

Safety:
No edited prose saved yet.
No draft file write.
No chapter-file edit.
No story-file mutation.
No overwrite.
No delete.
No move.

Please determine whether v10.14.3 should be marked stable/proven and whether the next build should be Real Prose Edit Save Approved Action.`;
    toast('Real Prose Editor Gate sent to Mission Console.');
}

let lastRealProseVerify=null;
async function loadRealProseVerify(doExport=false){
    if(!q('realProseVerifyStatus'))return;
    q('realProseVerifyStatus').textContent='Loading Real Prose Refresh / Compare...';
    let body={book_id:q('realProseVerifyBook')?.value||'book_2',chapter_number:parseInt(q('realProseVerifyChapter')?.value||'2'),from_version:parseInt(q('realProseVerifyFrom')?.value||'2'),to_version:parseInt(q('realProseVerifyTo')?.value||'3'),export:doExport};
    let d=await api('/api/writer/real_prose_refresh_compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('realProseVerifyStatus').textContent=d?.message||'Could not load Real Prose Verify.';return;}
    lastRealProseVerify=d; let s=d.summary||{}, c=d.compare||{};
    q('realProseVerifyStatus').innerHTML=`<span class="realProseVerifyBadge ${d.refresh_compare_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('realProseVerifySummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=realProseVerifyGrid><div class=realProseVerifyMetric><div class=label>Ready</div><div class=value>${d.refresh_compare_ready?'YES':'NO'}</div></div><div class=realProseVerifyMetric><div class=label>Versions</div><div class=value>${s.versions_loaded||0}</div></div><div class=realProseVerifyMetric><div class=label>Latest</div><div class=value>${esc(s.latest_label||'')}</div></div><div class=realProseVerifyMetric><div class=label>Real Prose</div><div class=value>${s.real_prose_present_in_v003?'YES':'NO'}</div></div><div class=realProseVerifyMetric><div class=label>Placeholder Removed</div><div class=value>${s.placeholder_removed_from_v003_body?'YES':'NO'}</div></div><div class=realProseVerifyMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=realProseVerifyPath>Drafts folder: ${esc(s.drafts_folder||'')}</div>${d.exported?`<div class=realProseVerifyPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('realProseVerifyVersions').innerHTML=(d.versions||[]).map(x=>`<div class="histrow ${x.verified?'ok':'fail'}"><b>${esc(x.label||'version')}</b><div>Status: ${esc(x.status||'')} | Words: ${x.word_count||0} | Hash OK: ${x.hash_ok} | Count OK: ${x.word_count_ok}</div><div>Created by: ${esc(x.created_by||'')}</div><div>Placeholder: ${x.contains_placeholder} | Real prose: ${x.contains_real_prose}</div><div class=realProseVerifyPath>${esc(x.draft_markdown?.path||'')}</div></div>`).join('')||'No versions loaded.';
    q('realProseVerifyAdded').innerHTML=(c.added_lines||[]).map(x=>`<div class="histrow ok"><b>Added</b><div class=rpadd>${esc(x)}</div></div>`).join('')||'No added lines.';
    q('realProseVerifyRemoved').innerHTML=(c.removed_lines||[]).map(x=>`<div class="histrow fail"><b>Removed</b><div class=rpremove>${esc(x)}</div></div>`).join('')||'No removed lines.';
    q('realProseVerifyDiff').textContent=(c.line_diff||[]).join('\n')||'No diff.';
    q('realProseVerifyChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('realProseVerifySafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Real Prose Verify loaded.');
}
function sendRealProseVerifyToMission(){
    if(!lastRealProseVerify){toast('Load Real Prose Verify first.');return;}
    let d=lastRealProseVerify, s=d.summary||{}, c=d.compare||{}; go('mission');
    q('input').value=`Please review this Kayock Writer Real Prose Refresh / Compare report.\n\nMilestone: ${d.milestone}\nHealth: ${d.health_label}\nRefresh / Compare ready: ${d.refresh_compare_ready}\n\nSummary:\nBook: ${s.book_id}\nChapter: ${s.chapter_number}\nVersions loaded: ${s.versions_loaded}\nVersion labels: ${(s.version_labels||[]).join(', ')}\nHas v001: ${s.has_v001}\nHas v002: ${s.has_v002}\nHas v003: ${s.has_v003}\nLatest: ${s.latest_label}\nLatest is v003: ${s.latest_is_v003}\nv003 created by: ${s.v003_created_by}\nv003 continues from v002: ${s.v003_continues_from_v002}\nv003 previous hash matches v002: ${s.v003_previous_hash_matches_v002}\nv003 status real_prose_draft: ${s.v003_status_real_prose_draft}\nReal prose present in v003: ${s.real_prose_present_in_v003}\nPlaceholder removed from v003 body: ${s.placeholder_removed_from_v003_body}\nAll hashes verified: ${s.all_hashes_verified}\nAll word counts verified: ${s.all_word_counts_verified}\nAll versions fully verified: ${s.all_versions_fully_verified}\nChecks: ${s.checks_passed}/${s.checks}\nProblems: ${s.problems}\n\nCompare:\nFrom v${s.from_version} words: ${s.from_words}\nTo v${s.to_version} words: ${s.to_words}\nWord delta: ${s.word_delta}\nAdded words: ${s.added_words}\nRemoved words: ${s.removed_words}\n\nPlease determine whether v10.14.2 should be marked stable/proven.`;
    toast('Real Prose Verify sent to Mission Console.');
}

let lastRealProseSave=null;
async function loadRealProseSave(execute=false){
    if(!q('realProseSaveStatus'))return;
    q('realProseSaveStatus').textContent=execute?'Requesting approved real prose save...':'Loading real prose save preview...';
    let body={book_id:q('realProseSaveBook')?.value||'book_2',chapter_number:parseInt(q('realProseSaveChapter')?.value||'2'),prose_mode:q('realProseSaveMode')?.value||'replace_placeholder',approval_phrase:q('realProseSavePhrase')?.value||'',real_prose_text:q('realProseSaveText')?.value||'',execute:execute,export:true};
    let d=await api('/api/writer/real_prose_save_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('realProseSaveStatus').textContent=d?.message||'Could not load Real Prose Save Action.';return;}
    lastRealProseSave=d;
    let s=d.summary||{}, rp=d.real_prose||{};
    let cls=d.status==='blocked'?'blocked':(d.status==='error'?'bad':'');
    q('realProseSaveStatus').innerHTML=`<span class="realProseSaveBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('realProseSaveSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=realProseSaveGrid><div class=realProseSaveMetric><div class=label>Status</div><div class=value>${esc(s.status||'')}</div></div><div class=realProseSaveMetric><div class=label>Allowed</div><div class=value>${s.action_allowed?'YES':'NO'}</div></div><div class=realProseSaveMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=realProseSaveMetric><div class=label>Next</div><div class=value>v${String(s.next_version||0).padStart(3,'0')}</div></div><div class=realProseSaveMetric><div class=label>Words</div><div class=value>${s.new_words||0}</div></div><div class=realProseSaveMetric><div class=label>Post</div><div class=value>${s.post_checks_passed||0}/${s.post_checks||0}</div></div></div><div class=realProseSavePath>Next draft: ${esc(s.next_draft_path||'')}</div>${d.exported?`<div class=realProseSavePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let parts=(d.selected_targets||[]).map(t=>`<div class="histrow ${t.would_overwrite?'fail':'ok'}"><b>${esc(t.kind||'target')}</b><div>Exists before save: ${t.exists} | Would overwrite: ${t.would_overwrite}</div><div class=realProseSavePath>${esc(t.path||'')}</div></div>`);
    (d.created_files||[]).forEach(p=>parts.push(`<div class="histrow ok"><b>Created file</b><div class=realProseSavePath>${esc(p)}</div></div>`));
    (d.blockers||[]).forEach(b=>parts.push(`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));
    (d.errors||[]).forEach(e=>parts.push(`<div class="histrow fail"><b>${esc(e.id||'error')}</b><div>${esc(e.message||'')}</div></div>`));
    q('realProseSaveTargets').innerHTML=parts.join('')||'No targets.';
    q('realProseSavePreview').textContent=rp.new_markdown_preview||'No preview.';
    q('realProseSavePreflight').innerHTML=(d.preflight_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No preflight.';
    q('realProseSavePost').innerHTML=(d.post_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No post checks.';
    q('realProseSaveSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Real Prose Save report loaded.');
}
function sendRealProseSaveToMission(){
    if(!lastRealProseSave){toast('Load Real Prose Save first.');return;}
    let d=lastRealProseSave, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Real Prose Save Approved Action report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Status: ${d.status}

Summary:
Book: ${s.book_id}
Chapter: ${s.chapter_number}
Execute requested: ${s.execute_requested}
Action allowed: ${s.action_allowed}
Phrase matches: ${s.phrase_matches}
Latest version: v${String(s.latest_version||0).padStart(3,'0')}
Next version: v${String(s.next_version||0).padStart(3,'0')}
Latest words: ${s.latest_words}
Real prose words: ${s.real_prose_words}
New words: ${s.new_words}
Word delta: ${s.word_delta}
Prose mode: ${s.prose_mode}
Collision targets: ${s.collision_targets}
Blockers: ${s.blockers}
Errors: ${s.errors}
Preflight: ${s.preflight_checks_passed}/${s.preflight_checks}
Created files: ${s.created_files}
Written files: ${s.written_files}
Post checks: ${s.post_checks_passed}/${s.post_checks}
Problems: ${s.problems}
Next draft: ${s.next_draft_path}
Metadata: ${s.metadata_path}
Evidence: ${s.evidence_path}

Created files:
${(d.created_files||[]).join('\n')||'None.'}

Safety:
Requires exact phrase.
Requires real prose text.
Requires latest draft hash verification.
Requires no collision.
Creates real-prose Markdown, metadata JSON, and save evidence JSON.
No chapter-file edit.
No story mutation.
No overwrite.
No delete.
No move.

Please determine whether v10.14.1 should be marked stable/proven and whether v003 real prose was saved safely.`;
    toast('Real Prose Save sent to Mission Console.');
}

let lastRealProseGate=null;
async function loadRealProseGate(doExport=false){
    if(!q('realProseStatus'))return;
    q('realProseStatus').textContent='Loading Real Prose Draft Gate...';
    let body={book_id:q('realProseBook')?.value||'book_2',chapter_number:parseInt(q('realProseChapter')?.value||'2'),prose_mode:q('realProseMode')?.value||'replace_placeholder',approval_phrase:q('realProsePhrase')?.value||'',real_prose_text:q('realProseText')?.value||'',export:doExport};
    let d=await api('/api/writer/real_prose_draft_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('realProseStatus').textContent=d?.message||'Could not load Real Prose Gate.';return;}
    lastRealProseGate=d; let s=d.summary||{}, p=d.real_prose_preview||{};
    q('realProseStatus').innerHTML=`<span class="realProseBadge ${d.gate_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('realProseSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=realProseGrid><div class=realProseMetric><div class=label>Gate</div><div class=value>${d.gate_ready?'READY':'REVIEW'}</div></div><div class=realProseMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=realProseMetric><div class=label>Next</div><div class=value>v${String(s.next_version||0).padStart(3,'0')}</div></div><div class=realProseMetric><div class=label>Real Words</div><div class=value>${s.real_prose_words||0}</div></div><div class=realProseMetric><div class=label>Collisions</div><div class=value>${s.collision_targets||0}</div></div><div class=realProseMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=realProsePath>Latest draft: ${esc(s.latest_draft_path||'')}</div>${d.exported?`<div class=realProsePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('realProseTargets').innerHTML=(d.selected_targets||[]).map(t=>`<div class="histrow ${t.would_overwrite?'fail':'ok'}"><b>${esc(t.kind||'target')}</b><div>Exists: ${t.exists} | Would overwrite: ${t.would_overwrite}</div><div class=realProsePath>${esc(t.path||'')}</div></div>`).join('')||'No targets.';
    q('realProsePreview').textContent=p.new_markdown_preview||'No preview.';
    q('realProseBlockers').innerHTML=(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No blockers.</b></div>';
    q('realProseChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('realProseSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n'); toast('Real Prose Gate loaded.');
}
function sendRealProseGateToMission(){
    if(!lastRealProseGate){toast('Load Real Prose Gate first.');return;} let d=lastRealProseGate, s=d.summary||{}; go('mission');
    q('input').value=`Please review this Kayock Writer Real Prose Draft Gate report.\n\nMilestone: ${d.milestone}\nHealth: ${d.health_label}\nGate ready: ${d.gate_ready}\n\nSummary:\nBook: ${s.book_id}\nChapter: ${s.chapter_number}\nLatest version: v${String(s.latest_version||0).padStart(3,'0')}\nNext version: v${String(s.next_version||0).padStart(3,'0')}\nLatest words: ${s.latest_words}\nReal prose words: ${s.real_prose_words}\nProposed preview words: ${s.proposed_preview_words}\nWord delta: ${s.word_delta}\nProse mode: ${s.prose_mode}\nPhrase matches: ${s.phrase_matches}\nCollision targets: ${s.collision_targets}\nBlockers: ${s.blockers}\nChecks: ${s.checks_passed}/${s.checks}\nProblems: ${s.problems}\nSafe to save later: ${s.safe_to_save_later}\n\nSafety:\nNo real prose saved yet. No draft file write. No chapter-file edit. No story-file mutation. No overwrite. No delete. No move.\n\nPlease determine whether v10.14.0 should be marked stable/proven and whether the next build should be Real Prose Save Approved Action.`;
    toast('Real Prose Gate sent to Mission Console.');
}

let lastDraftCompare=null;
async function loadDraftCompare(doExport=false){
    if(!q('draftCompareStatus'))return;
    q('draftCompareStatus').textContent='Loading Draft Compare View...';
    let body={book_id:q('draftCompareBook')?.value||'book_2',chapter_number:parseInt(q('draftCompareChapter')?.value||'2'),from_version:parseInt(q('draftCompareFrom')?.value||'1'),to_version:parseInt(q('draftCompareTo')?.value||'2'),export:doExport};
    let d=await api('/api/writer/draft_compare_view',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('draftCompareStatus').textContent=d?.message||'Could not load Draft Compare.';return;}
    lastDraftCompare=d;
    let s=d.summary||{}, c=d.compare||{};
    q('draftCompareStatus').innerHTML=`<span class="draftCompareBadge ${d.compare_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('draftCompareSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=draftCompareGrid><div class=draftCompareMetric><div class=label>Ready</div><div class=value>${d.compare_ready?'YES':'NO'}</div></div><div class=draftCompareMetric><div class=label>From</div><div class=value>${esc(s.from_label||'')}</div></div><div class=draftCompareMetric><div class=label>To</div><div class=value>${esc(s.to_label||'')}</div></div><div class=draftCompareMetric><div class=label>Word Delta</div><div class=value>${s.word_delta||0}</div></div><div class=draftCompareMetric><div class=label>Added</div><div class=value>${s.added_words||0}</div></div><div class=draftCompareMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=draftComparePath>Drafts folder: ${esc(s.drafts_folder||'')}</div>${d.exported?`<div class=draftComparePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('draftCompareAdded').innerHTML=(c.added_lines||[]).map(x=>`<div class="histrow ok"><b>Added</b><div class=diffadd>${esc(x)}</div></div>`).join('')||'No added lines.';
    q('draftCompareRemoved').innerHTML=(c.removed_lines||[]).map(x=>`<div class="histrow fail"><b>Removed</b><div class=diffremove>${esc(x)}</div></div>`).join('')||'No removed lines.';
    q('draftCompareDiff').textContent=(c.line_diff||[]).join('\n')||'No diff.';
    q('draftCompareChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('draftCompareSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Draft Compare loaded.');
}
function sendDraftCompareToMission(){
    if(!lastDraftCompare){toast('Load Draft Compare first.');return;}
    let d=lastDraftCompare, s=d.summary||{}, c=d.compare||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Draft Compare View report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Compare ready: ${d.compare_ready}

Summary:
Book: ${s.book_id}
Chapter: ${s.chapter_number}
From: ${s.from_label}
To: ${s.to_label}
From words: ${s.from_words}
To words: ${s.to_words}
Word delta: ${s.word_delta}
Char delta: ${s.char_delta}
From verified: ${s.from_verified}
To verified: ${s.to_verified}
Lineage OK: ${s.lineage_ok}
Previous hash OK: ${s.previous_hash_ok}
Added words: ${s.added_words}
Removed words: ${s.removed_words}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}

Added lines:
${(c.added_lines||[]).join('\n')||'None.'}

Removed lines:
${(c.removed_lines||[]).join('\n')||'None.'}

Safety:
Read-only compare.
No draft save.
No chapter-file edit.
No story mutation.
No overwrite.
No delete.
No move.

Please determine whether v10.13.9 should be marked stable/proven.`;
    toast('Draft Compare sent to Mission Console.');
}

let lastDraftRefresh=null;
async function loadDraftRefresh(doExport=false){
    if(!q('draftRefreshStatus'))return;
    q('draftRefreshStatus').textContent='Loading Draft Reader / History Refresh...';
    let body={book_id:q('draftRefreshBook')?.value||'book_2',chapter_number:parseInt(q('draftRefreshChapter')?.value||'2'),export:doExport};
    let d=await api('/api/writer/draft_refresh_verification',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('draftRefreshStatus').textContent=d?.message||'Could not load Draft Refresh.';return;}
    lastDraftRefresh=d;
    let s=d.summary||{};
    q('draftRefreshStatus').innerHTML=`<span class="draftRefreshBadge ${d.refresh_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('draftRefreshSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=draftRefreshGrid><div class=draftRefreshMetric><div class=label>Ready</div><div class=value>${d.refresh_ready?'YES':'NO'}</div></div><div class=draftRefreshMetric><div class=label>Versions</div><div class=value>${s.versions_loaded||0}</div></div><div class=draftRefreshMetric><div class=label>v001</div><div class=value>${s.has_v001?'YES':'NO'}</div></div><div class=draftRefreshMetric><div class=label>v002</div><div class=value>${s.has_v002?'YES':'NO'}</div></div><div class=draftRefreshMetric><div class=label>Latest</div><div class=value>${esc(s.latest_label||'')}</div></div><div class=draftRefreshMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=draftRefreshPath>Drafts folder: ${esc(s.drafts_folder||'')}</div>${d.exported?`<div class=draftRefreshPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('draftRefreshVersions').innerHTML=(d.versions||[]).map(x=>`<div class="histrow ${x.verified?'ok':'fail'}"><b>${esc(x.label||'version')}</b><div>Words: ${x.word_count||0} | Hash OK: ${x.hash_ok} | Count OK: ${x.word_count_ok} | Verified: ${x.verified}</div><div>Created by: ${esc(x.created_by||'')}</div><div>Continues from: ${x.continues_from_version||'—'}</div><div class=draftRefreshPath>${esc(x.draft_markdown?.path||'')}</div></div>`).join('')||'No versions loaded.';
    q('draftRefreshChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('draftRefreshSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Draft Refresh loaded.');
}
function sendDraftRefreshToMission(){
    if(!lastDraftRefresh){toast('Load Draft Refresh first.');return;}
    let d=lastDraftRefresh, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Draft Reader / History Refresh report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Refresh ready: ${d.refresh_ready}

Summary:
Book: ${s.book_id}
Chapter: ${s.chapter_number}
Versions loaded: ${s.versions_loaded}
Version labels: ${(s.version_labels||[]).join(', ')}
Has v001: ${s.has_v001}
Has v002: ${s.has_v002}
Latest version: ${s.latest_label}
Latest is v002: ${s.latest_is_v002}
v002 created by: ${s.v002_created_by}
v002 continues from v001: ${s.v002_continues_from_v001}
All hashes verified: ${s.all_hashes_verified}
All word counts verified: ${s.all_word_counts_verified}
All versions fully verified: ${s.all_versions_fully_verified}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}

Versions:
${(d.versions||[]).map(x=>`${x.verified?'PASS':'REVIEW'} - ${x.label} - words=${x.word_count} - hash_ok=${x.hash_ok} - count_ok=${x.word_count_ok} - created_by=${x.created_by}`).join('\n')}

Safety:
Read-only refresh.
No draft save.
No chapter-file edit.
No story mutation.
No overwrite.
No delete.
No move.

Please determine whether v10.13.8 should be marked stable/proven and whether Draft Reader/History correctly see v001 and v002.`;
    toast('Draft Refresh sent to Mission Console.');
}

let lastContinueSaveAction=null;
async function loadContinueSaveAction(execute=false){
    if(!q('continueActionStatus'))return;
    q('continueActionStatus').textContent=execute?'Requesting approved continuation save...':'Loading continue save action preview...';
    let body={book_id:q('continueActionBook')?.value||'book_2',chapter_number:parseInt(q('continueActionChapter')?.value||'2'),continue_mode:q('continueActionMode')?.value||'next_scene',approval_phrase:q('continueActionPhrase')?.value||'',continuation_text:q('continueActionText')?.value||'',execute:execute,export:true};
    let d=await api('/api/writer/continue_save_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('continueActionStatus').textContent=d?.message||'Could not load Continue Save Action.';return;}
    lastContinueSaveAction=d;
    let s=d.summary||{}, cont=d.continuation||{};
    let cls=d.status==='blocked'?'blocked':(d.status==='error'?'bad':'');
    q('continueActionStatus').innerHTML=`<span class="continueActionBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('continueActionSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=continueActionGrid><div class=continueActionMetric><div class=label>Status</div><div class=value>${esc(s.status||'')}</div></div><div class=continueActionMetric><div class=label>Allowed</div><div class=value>${s.action_allowed?'YES':'NO'}</div></div><div class=continueActionMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=continueActionMetric><div class=label>Next</div><div class=value>v${String(s.next_version||0).padStart(3,'0')}</div></div><div class=continueActionMetric><div class=label>Words</div><div class=value>${s.new_words||0}</div></div><div class=continueActionMetric><div class=label>Post</div><div class=value>${s.post_checks_passed||0}/${s.post_checks||0}</div></div></div><div class=continueActionPath>Next draft: ${esc(s.next_draft_path||'')}</div>${d.exported?`<div class=continueActionPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let parts=(d.selected_targets||[]).map(t=>`<div class="histrow ${t.would_overwrite?'fail':'ok'}"><b>${esc(t.kind||'target')}</b><div>Exists before save: ${t.exists} | Would overwrite: ${t.would_overwrite}</div><div class=continueActionPath>${esc(t.path||'')}</div></div>`);
    (d.created_files||[]).forEach(p=>parts.push(`<div class="histrow ok"><b>Created file</b><div class=continueActionPath>${esc(p)}</div></div>`));
    (d.blockers||[]).forEach(b=>parts.push(`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));
    (d.errors||[]).forEach(e=>parts.push(`<div class="histrow fail"><b>${esc(e.id||'error')}</b><div>${esc(e.message||'')}</div></div>`));
    q('continueActionTargets').innerHTML=parts.join('')||'No targets.';
    q('continueActionPreview').textContent=cont.new_markdown_preview||'No preview.';
    q('continueActionPreflight').innerHTML=(d.preflight_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No preflight.';
    q('continueActionPost').innerHTML=(d.post_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No post checks.';
    q('continueActionSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Continue Save Action report loaded.');
}
function sendContinueSaveActionToMission(){
    if(!lastContinueSaveAction){toast('Load Continue Save Action first.');return;}
    let d=lastContinueSaveAction, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Continue Save Approved Action report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Status: ${d.status}

Summary:
Book: ${s.book_id}
Chapter: ${s.chapter_number}
Execute requested: ${s.execute_requested}
Action allowed: ${s.action_allowed}
Phrase matches: ${s.phrase_matches}
Latest version: v${String(s.latest_version||0).padStart(3,'0')}
Next version: v${String(s.next_version||0).padStart(3,'0')}
Latest words: ${s.latest_words}
Continuation words: ${s.continuation_words}
New words: ${s.new_words}
Collision targets: ${s.collision_targets}
Blockers: ${s.blockers}
Errors: ${s.errors}
Preflight: ${s.preflight_checks_passed}/${s.preflight_checks}
Created files: ${s.created_files}
Written files: ${s.written_files}
Post checks: ${s.post_checks_passed}/${s.post_checks}
Problems: ${s.problems}
Next draft: ${s.next_draft_path}
Metadata: ${s.metadata_path}
Evidence: ${s.evidence_path}

Created files:
${(d.created_files||[]).join('\n')||'None.'}

Safety:
Requires exact phrase.
Requires continuation text.
Requires latest draft hash verification.
Requires no collision.
Creates next-version Markdown, metadata JSON, and save evidence JSON.
No chapter-file edit.
No story-file mutation.
No overwrite.
No delete.
No move.

Please determine whether v10.13.7 should be marked stable/proven and whether v002 was saved safely.`;
    toast('Continue Save Action sent to Mission Console.');
}

let lastContinueSaveGate=null;
async function loadContinueSaveGate(doExport=false){
    if(!q('continueGateStatus'))return;
    q('continueGateStatus').textContent='Loading Continue Save Approval Gate...';
    let body={book_id:q('continueGateBook')?.value||'book_2',chapter_number:parseInt(q('continueGateChapter')?.value||'2'),continue_mode:q('continueGateMode')?.value||'next_scene',approval_phrase:q('continueGatePhrase')?.value||'',target_words:parseInt(q('continueGateTargetWords')?.value||'1200'),continuation_text:q('continueGateText')?.value||'',export:doExport};
    let d=await api('/api/writer/continue_save_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('continueGateStatus').textContent=d?.message||'Could not load Continue Save Gate.';return;}
    lastContinueSaveGate=d; let s=d.summary||{}, c=d.continuation||{};
    q('continueGateStatus').innerHTML=`<span class="continueGateBadge ${d.gate_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('continueGateSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=continueGateGrid><div class=continueGateMetric><div class=label>Gate</div><div class=value>${d.gate_ready?'READY':'REVIEW'}</div></div><div class=continueGateMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=continueGateMetric><div class=label>Next</div><div class=value>v${String(s.next_version||0).padStart(3,'0')}</div></div><div class=continueGateMetric><div class=label>New Words</div><div class=value>${s.new_preview_words||0}</div></div><div class=continueGateMetric><div class=label>Collisions</div><div class=value>${s.collision_targets||0}</div></div><div class=continueGateMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=continueGatePath>Latest draft: ${esc(s.latest_draft_path||'')}</div>${d.exported?`<div class=continueGatePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('continueGateTargets').innerHTML=(d.selected_targets||[]).map(t=>`<div class="histrow ${t.would_overwrite?'fail':'ok'}"><b>${esc(t.kind||'target')}</b><div>Exists: ${t.exists} | Would overwrite: ${t.would_overwrite}</div><div class=continueGatePath>${esc(t.path||'')}</div></div>`).join('')||'No targets.';
    q('continueGatePreview').textContent=c.new_markdown_preview||'No preview.';
    q('continueGateBlockers').innerHTML=(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No blockers.</b></div>';
    q('continueGateChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('continueGateSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Continue Save Gate loaded.');
}
function sendContinueSaveGateToMission(){
    if(!lastContinueSaveGate){toast('Load Continue Save Gate first.');return;}
    let d=lastContinueSaveGate, s=d.summary||{}; go('mission');
    q('input').value=`Please review this Kayock Writer Continue Save Approval Gate report.\n\nMilestone: ${d.milestone}\nHealth: ${d.health_label}\nGate ready: ${d.gate_ready}\n\nBook: ${s.book_id}\nChapter: ${s.chapter_number}\nLatest version: v${String(s.latest_version||0).padStart(3,'0')}\nNext version: v${String(s.next_version||0).padStart(3,'0')}\nLatest words: ${s.latest_words}\nContinuation words: ${s.continuation_words}\nNew preview words: ${s.new_preview_words}\nPhrase matches: ${s.phrase_matches}\nCollision targets: ${s.collision_targets}\nBlockers: ${s.blockers}\nChecks: ${s.checks_passed}/${s.checks}\nProblems: ${s.problems}\nSafe to save later: ${s.safe_to_save_later}\n\nTargets:\n${(d.selected_targets||[]).map(t=>`${t.kind}: ${t.path} | exists=${t.exists} | would_overwrite=${t.would_overwrite}`).join('\n')}\n\nSafety: no continuation saved yet; no draft file write; no chapter edit; no story mutation; no overwrite; no delete; no move.\n\nPlease determine whether v10.13.6 should be marked stable/proven and whether the next build should be Continue Save Approved Action.`;
    toast('Continue Save Gate sent to Mission Console.');
}

let lastDraftContinueWorkspace=null;
async function loadDraftContinueWorkspace(doExport=false){
    if(!q('draftContinueStatus'))return;
    q('draftContinueStatus').textContent='Loading Draft Continue Workspace...';
    let body={book_id:q('draftContinueBook')?.value||'book_2',chapter_number:parseInt(q('draftContinueChapter')?.value||'2'),continue_mode:q('draftContinueMode')?.value||'next_scene',target_words:parseInt(q('draftContinueTargetWords')?.value||'1200'),user_direction:q('draftContinueDirection')?.value||'',export:doExport};
    let d=await api('/api/writer/draft_continue_workspace',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('draftContinueStatus').textContent=d?.message||'Could not load Draft Continue Workspace.';return;}
    lastDraftContinueWorkspace=d;
    let s=d.summary||{}, w=d.workspace||{};
    q('draftContinueStatus').innerHTML=`<span class="draftContinueBadge ${d.continue_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('draftContinueSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=draftContinueGrid><div class=draftContinueMetric><div class=label>Ready</div><div class=value>${d.continue_ready?'YES':'NO'}</div></div><div class=draftContinueMetric><div class=label>Latest</div><div class=value>v${String(s.latest_draft_version||0).padStart(3,'0')}</div></div><div class=draftContinueMetric><div class=label>Words</div><div class=value>${s.latest_draft_words||0}</div></div><div class=draftContinueMetric><div class=label>Hash</div><div class=value>${s.hash_ok?'OK':'BAD'}</div></div><div class=draftContinueMetric><div class=label>Beats</div><div class=value>${s.beat_count||0}</div></div><div class=draftContinueMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=draftContinuePath>Latest draft: ${esc(s.latest_draft_path||'')}</div><div class=draftContinuePath>Chapter card: ${esc(s.chapter_card_path||'')}</div>${d.exported?`<div class=draftContinuePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('draftContinueBrief').textContent=w.continuation_brief||'No brief.';
    q('draftContinueBeats').innerHTML=(w.next_scene_beats||[]).map(b=>`<div class=draftContinueCard><b>${b.beat}. ${esc(b.name||'Beat')}</b><div>${esc(b.purpose||'')}</div></div>`).join('')||'No beats.';
    q('draftContinuePrompt').textContent=w.continuation_prompt||'No prompt.';
    q('draftContinueShell').textContent=w.continuation_shell||'No shell.';
    q('draftContinueChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('draftContinueSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Draft Continue Workspace loaded.');
}
function sendDraftContinueWorkspaceToMission(){
    if(!lastDraftContinueWorkspace){toast('Load Draft Continue Workspace first.');return;}
    let d=lastDraftContinueWorkspace, s=d.summary||{}, w=d.workspace||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Draft Continue Workspace report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Continue ready: ${d.continue_ready}

Summary:
Book: ${s.book_id}
Chapter: ${s.chapter_number}
Latest draft version: v${String(s.latest_draft_version||0).padStart(3,'0')}
Latest draft words: ${s.latest_draft_words}
Hash OK: ${s.hash_ok}
Word Count OK: ${s.word_count_ok}
Continue mode: ${s.continue_mode}
Target words: ${s.target_words}
Beat count: ${s.beat_count}
Guardrails: ${s.guardrails}
Prompt chars: ${s.prompt_chars}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Latest draft: ${s.latest_draft_path}
Chapter card: ${s.chapter_card_path}

Continuation Brief:
${w.continuation_brief||''}

Next Scene Beats:
${(w.next_scene_beats||[]).map(b=>`${b.beat}. ${b.name}: ${b.purpose}`).join('\n')}

Continuation Prompt:
${w.continuation_prompt||''}

Export:
${d.exported?.markdown||'No exported Draft Continue Workspace report'}

Safety:
Read-only continue workspace.
No draft save.
No chapter-file edit.
No story-file mutation.
No overwrite.
No delete.
No move.

Please determine whether v10.13.5 should be marked stable/proven and whether the next build should be Continue Save Approval Gate.`;
    toast('Draft Continue Workspace sent to Mission Console.');
}

let lastDraftVersionHistory=null;
async function loadDraftVersionHistory(doExport=false){
    if(!q('draftHistoryStatus'))return;
    q('draftHistoryStatus').textContent='Loading Draft Version History...';
    let body={book_id:q('draftHistoryBook')?.value||'book_2',chapter_number:parseInt(q('draftHistoryChapter')?.value||'2'),export:doExport};
    let d=await api('/api/writer/draft_version_history',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('draftHistoryStatus').textContent=d?.message||'Could not load Draft Version History.';return;}
    lastDraftVersionHistory=d;
    let s=d.summary||{}, l=d.latest_version||{};
    q('draftHistoryStatus').innerHTML=`<span class="draftHistoryBadge ${d.history_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('draftHistorySummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=draftHistoryGrid><div class=draftHistoryMetric><div class=label>Ready</div><div class=value>${d.history_ready?'YES':'NO'}</div></div><div class=draftHistoryMetric><div class=label>Versions</div><div class=value>${s.versions_loaded||0}</div></div><div class=draftHistoryMetric><div class=label>Verified</div><div class=value>${s.verified_versions||0}</div></div><div class=draftHistoryMetric><div class=label>Latest</div><div class=value>v${String(s.latest_version||0).padStart(3,'0')}</div></div><div class=draftHistoryMetric><div class=label>Latest Words</div><div class=value>${s.latest_word_count||0}</div></div><div class=draftHistoryMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=draftHistoryPath>Drafts folder: ${esc(s.drafts_folder||'')}</div><div class=draftHistoryPath>Chapter card: ${esc(s.chapter_card_path||'')}</div>${d.exported?`<div class=draftHistoryPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('draftHistoryTimeline').innerHTML=(d.timeline||[]).map(t=>`<div class="histrow ${t.verified?'ok':'fail'}"><b>v${String(t.version||0).padStart(3,'0')}</b><div>Words: ${t.word_count||0} | Delta: ${t.delta_words_from_previous===null?'—':t.delta_words_from_previous} | Hash OK: ${t.hash_ok} | Verified: ${t.verified}</div><div>Metadata: ${t.metadata_exists} | Evidence: ${t.evidence_exists} | Chapter Card: ${t.chapter_card_exists}</div><div class=draftHistoryPath>${esc(t.draft_path||'')}</div></div>`).join('')||'No timeline loaded.';
    if(l.draft_markdown){
        q('draftHistoryLatest').innerHTML=`<div><b>${esc(l.label||'latest')}</b> — ${esc(l.draft_markdown.name||'draft')}</div><div>Words: ${l.word_count||0} | Chars: ${l.char_count||0} | Lines: ${l.line_count||0}</div><div>Hash OK: ${l.hash_ok} | Word Count OK: ${l.word_count_ok} | Verified: ${l.verified}</div><div class=draftHistoryPath>Draft: ${esc(l.draft_markdown.path||'')}</div><div class=draftHistoryPath>Metadata: ${esc(l.metadata_file?.path||'')}</div><div class=draftHistoryPath>Evidence: ${esc(l.evidence_file?.path||'')}</div>`;
    }else{
        q('draftHistoryLatest').textContent='No latest version found.';
    }
    q('draftHistoryChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('draftHistorySafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Draft Version History loaded.');
}
function sendDraftVersionHistoryToMission(){
    if(!lastDraftVersionHistory){toast('Load Draft Version History first.');return;}
    let d=lastDraftVersionHistory, s=d.summary||{}, l=d.latest_version||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Draft Version History report.

Milestone: ${d.milestone}
Health: ${d.health_label}
History ready: ${d.history_ready}

Summary:
Book: ${s.book_id}
Chapter: ${s.chapter_number}
Versions loaded: ${s.versions_loaded}
Verified versions: ${s.verified_versions}
Metadata files: ${s.metadata_files}
Evidence files: ${s.evidence_files}
Hashes verified: ${s.hashes_verified}
Word counts verified: ${s.word_counts_verified}
Latest version: v${String(s.latest_version||0).padStart(3,'0')}
Latest word count: ${s.latest_word_count}
Net word change: ${s.net_word_change}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}

Timeline:
${(d.timeline||[]).map(t=>`${t.verified?'PASS':'REVIEW'} - v${String(t.version||0).padStart(3,'0')} - words=${t.word_count} - delta=${t.delta_words_from_previous} - hash_ok=${t.hash_ok} - ${t.draft_path}`).join('\n')}

Latest:
${l.draft_markdown?.path||'None'}
Metadata: ${l.metadata_file?.path||'None'}
Evidence: ${l.evidence_file?.path||'None'}
Verified: ${l.verified}

Export:
${d.exported?.markdown||'No exported Draft Version History report'}

Safety:
Read-only version history.
No draft save.
No chapter-file edit.
No story-file mutation.
No overwrite.
No delete.
No move.

Please determine:
1. Whether v10.13.4 should be marked stable/proven
2. Whether the draft version timeline is healthy
3. Whether the next build should be Draft Continue Workspace.`;
    toast('Draft Version History sent to Mission Console.');
}

let lastDraftReader=null;
async function loadDraftReader(doExport=false){
    if(!q('draftReaderStatus'))return;
    q('draftReaderStatus').textContent='Loading Draft Reader Dashboard...';
    let body={book_id:q('draftReaderBook')?.value||'book_2',export:doExport};
    let d=await api('/api/writer/draft_reader_dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('draftReaderStatus').textContent=d?.message||'Could not load Draft Reader.';return;}
    lastDraftReader=d;
    let s=d.summary||{}, l=d.latest_draft||{};
    q('draftReaderStatus').innerHTML=`<span class="draftReaderBadge ${d.dashboard_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('draftReaderSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=draftReaderGrid><div class=draftReaderMetric><div class=label>Ready</div><div class=value>${d.dashboard_ready?'YES':'NO'}</div></div><div class=draftReaderMetric><div class=label>Drafts</div><div class=value>${s.drafts_loaded||0}</div></div><div class=draftReaderMetric><div class=label>Verified</div><div class=value>${s.verified_drafts||0}</div></div><div class=draftReaderMetric><div class=label>Words</div><div class=value>${s.total_words||0}</div></div><div class=draftReaderMetric><div class=label>Hashes</div><div class=value>${s.hashes_verified||0}</div></div><div class=draftReaderMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=draftReaderPath>Drafts root: ${esc(s.drafts_root||'')}</div>${d.exported?`<div class=draftReaderPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    if(l.draft_markdown){
        q('draftReaderLatest').innerHTML=`<div><b>${esc(l.draft_markdown.name||'latest draft')}</b></div><div>Book: ${esc(l.book_id||'')} | Chapter: ${l.chapter_number||''} | Version: v${String(l.draft_version||0).padStart(3,'0')} | Words: ${l.word_count||0}</div><div>Hash OK: ${l.hash_ok} | Word Count OK: ${l.word_count_ok} | Verified: ${l.verified}</div><div class=draftReaderPath>Draft: ${esc(l.draft_markdown.path||'')}</div><div class=draftReaderPath>Metadata: ${esc(l.metadata_file?.path||'')}</div><div class=draftReaderPath>Evidence: ${esc(l.evidence_file?.path||'')}</div><div class=draftReaderPath>Chapter Card: ${esc(l.chapter_card_path||'')} | Exists: ${l.chapter_card_exists}</div>`;
    }else{
        q('draftReaderLatest').textContent='No latest draft found.';
    }
    q('draftReaderInventory').innerHTML=(d.drafts||[]).map(x=>`<div class="histrow ${x.verified?'ok':'fail'}"><b>${esc(x.draft_markdown?.name||'draft')}</b><div>Book: ${esc(x.book_id||'')} | Chapter: ${x.chapter_number||''} | Version: v${String(x.draft_version||0).padStart(3,'0')} | Words: ${x.word_count||0} | Hash OK: ${x.hash_ok} | Verified: ${x.verified}</div><div class=draftReaderPath>${esc(x.draft_markdown?.path||'')}</div></div>`).join('')||'No drafts loaded.';
    q('draftReaderChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('draftReaderSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Draft Reader loaded.');
}
function sendDraftReaderToMission(){
    if(!lastDraftReader){toast('Load Draft Reader first.');return;}
    let d=lastDraftReader, s=d.summary||{}, l=d.latest_draft||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Draft Reader Dashboard report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Dashboard ready: ${d.dashboard_ready}

Summary:
Book filter: ${s.book_filter}
Drafts loaded: ${s.drafts_loaded}
Verified drafts: ${s.verified_drafts}
Metadata files: ${s.metadata_files}
Evidence files: ${s.evidence_files}
Hashes verified: ${s.hashes_verified}
Total words: ${s.total_words}
Latest book: ${s.latest_book_id}
Latest chapter: ${s.latest_chapter_number}
Latest version: v${String(s.latest_draft_version||0).padStart(3,'0')}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}

Latest draft:
${l.draft_markdown?.path||'None'}
Metadata: ${l.metadata_file?.path||'None'}
Evidence: ${l.evidence_file?.path||'None'}
Hash OK: ${l.hash_ok}
Verified: ${l.verified}
Chapter card: ${l.chapter_card_path||'None'}

Draft inventory:
${(d.drafts||[]).map(x=>`${x.verified?'PASS':'REVIEW'} - ${x.draft_markdown?.name} - book=${x.book_id} chapter=${x.chapter_number} version=v${String(x.draft_version||0).padStart(3,'0')} words=${x.word_count} hash_ok=${x.hash_ok}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Draft Reader report'}

Safety:
Read-only draft reader.
No draft save.
No chapter-file edit.
No story-file mutation.
No overwrite.
No delete.
No move.

Please determine:
1. Whether v10.13.3 should be marked stable/proven
2. Whether the saved draft inventory is healthy
3. Whether the next build should be Draft Version History.`;
    toast('Draft Reader sent to Mission Console.');
}

let lastDraftSaveAction=null;
async function loadDraftSaveAction(execute=false){
    if(!q('draftSaveStatus'))return;
    q('draftSaveStatus').textContent=execute?'Requesting approved draft save...':'Loading draft save action preview...';
    let body={book_id:q('draftSaveBook')?.value||'book_2',chapter_number:parseInt(q('draftSaveChapter')?.value||'2'),approval_phrase:q('draftSavePhrase')?.value||'',draft_title:q('draftSaveTitle')?.value||'',draft_text:q('draftSaveText')?.value||'',execute:execute,export:true};
    let d=await api('/api/writer/draft_save_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('draftSaveStatus').textContent=d?.message||'Could not load Draft Save Action.';return;}
    lastDraftSaveAction=d;
    let s=d.summary||{};
    let cls=d.status==='blocked'?'blocked':(d.status==='error'?'bad':'');
    q('draftSaveStatus').innerHTML=`<span class="draftSaveBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('draftSaveSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=draftSaveGrid><div class=draftSaveMetric><div class=label>Status</div><div class=value>${esc(s.status||'')}</div></div><div class=draftSaveMetric><div class=label>Allowed</div><div class=value>${s.action_allowed?'YES':'NO'}</div></div><div class=draftSaveMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=draftSaveMetric><div class=label>Version</div><div class=value>v${String(s.draft_version||0).padStart(3,'0')}</div></div><div class=draftSaveMetric><div class=label>Words</div><div class=value>${s.word_count||0}</div></div><div class=draftSaveMetric><div class=label>Post</div><div class=value>${s.post_checks_passed||0}/${s.post_checks||0}</div></div></div><div class=draftSavePath>Draft: ${esc(s.draft_markdown_path||'')}</div><div class=draftSavePath>Metadata: ${esc(s.metadata_path||'')}</div><div class=draftSavePath>Evidence: ${esc(s.evidence_path||'')}</div>${d.exported?`<div class=draftSavePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('draftSaveTargets').innerHTML=(d.selected_targets||[]).map(t=>`<div class="histrow ${t.would_overwrite?'fail':'ok'}"><b>${esc(t.kind||'target')}</b><div>Exists before save: ${t.exists} | Would overwrite: ${t.would_overwrite}</div><div class=draftSavePath>${esc(t.path||'')}</div></div>`).join('')||'No targets.';
    let resultParts=[];
    if((d.blockers||[]).length){resultParts.push(...(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));}
    else{resultParts.push('<div class="histrow ok"><b>No blockers.</b></div>');}
    (d.created_files||[]).forEach(p=>resultParts.push(`<div class="histrow ok"><b>Created file</b><div class=draftSavePath>${esc(p)}</div></div>`));
    (d.errors||[]).forEach(e=>resultParts.push(`<div class="histrow fail"><b>${esc(e.id||'error')}</b><div>${esc(e.message||'')}</div></div>`));
    q('draftSaveResults').innerHTML=resultParts.join('');
    q('draftSavePreview').textContent=d.draft_markdown_preview||'No preview.';
    q('draftSavePreflight').innerHTML=(d.preflight_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No preflight.';
    q('draftSavePost').innerHTML=(d.post_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No post checks.';
    q('draftSaveSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Draft Save Action report loaded.');
}
function sendDraftSaveActionToMission(){
    if(!lastDraftSaveAction){toast('Load Draft Save Action first.');return;}
    let d=lastDraftSaveAction, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Draft Save Approved Action report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Status: ${d.status}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} - ${s.book_title}
Chapter: ${s.chapter_number}
Execute requested: ${s.execute_requested}
Action allowed: ${s.action_allowed}
Phrase matches: ${s.phrase_matches}
Draft version: v${String(s.draft_version||0).padStart(3,'0')}
Word count: ${s.word_count}
Char count: ${s.char_count}
Selected targets: ${s.selected_targets}
Collision targets: ${s.collision_targets}
Blockers: ${s.blockers}
Errors: ${s.errors}
Preflight: ${s.preflight_checks_passed}/${s.preflight_checks}
Created files: ${s.created_files}
Written files: ${s.written_files}
Post checks: ${s.post_checks_passed}/${s.post_checks}
Problems: ${s.problems}
Draft path: ${s.draft_markdown_path}
Metadata path: ${s.metadata_path}
Evidence path: ${s.evidence_path}

Created files:
${(d.created_files||[]).join('\n')||'None.'}

Blockers:
${(d.blockers||[]).length ? (d.blockers||[]).map(b=>`${b.id}: ${b.message}`).join('\n') : 'None.'}

Post checks:
${(d.post_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} - ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Draft Save Action report'}

Safety:
Requires exact phrase.
Requires draft text.
Requires no collision.
Auto-selects next safe version.
Creates Markdown draft, metadata JSON, and save evidence JSON.
No chapter-file edit.
No story-file mutation.
No overwrite.
No delete.
No move.

Please determine:
1. Whether v10.13.2 should be marked stable/proven
2. Whether the first prose draft save was completed safely
3. Whether the next build should be Draft Reader Dashboard.`;
    toast('Draft Save Action sent to Mission Console.');
}

let lastDraftSaveGate=null;
async function loadDraftSaveGate(doExport=false){
    if(!q('draftGateStatus'))return;
    q('draftGateStatus').textContent='Loading Draft Save Approval Gate...';
    let body={book_id:q('draftGateBook')?.value||'book_2',chapter_number:parseInt(q('draftGateChapter')?.value||'2'),approval_phrase:q('draftGatePhrase')?.value||'',draft_title:q('draftGateTitle')?.value||'',draft_text:q('draftGateText')?.value||'',export:doExport};
    let d=await api('/api/writer/draft_save_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('draftGateStatus').textContent=d?.message||'Could not load Draft Save Gate.';return;}
    lastDraftSaveGate=d;
    let s=d.summary||{};
    q('draftGateStatus').innerHTML=`<span class="draftGateBadge ${d.gate_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('draftGateSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=draftGateGrid><div class=draftGateMetric><div class=label>Gate</div><div class=value>${d.gate_ready?'READY':'REVIEW'}</div></div><div class=draftGateMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=draftGateMetric><div class=label>Words</div><div class=value>${s.word_count||0}</div></div><div class=draftGateMetric><div class=label>Targets</div><div class=value>${s.future_targets||0}</div></div><div class=draftGateMetric><div class=label>Blockers</div><div class=value>${s.blockers||0}</div></div><div class=draftGateMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=draftGatePath>Chapter card: ${esc(s.chapter_card_path||'')}</div>${d.exported?`<div class=draftGatePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('draftGateTargets').innerHTML=(d.proposed_targets||[]).map(t=>`<div class="histrow ${t.would_overwrite?'fail':'ok'}"><b>${esc(t.kind||'target')}</b><div>Exists: ${t.exists} | Would overwrite: ${t.would_overwrite}</div><div class=draftGatePath>${esc(t.path||'')}</div></div>`).join('')||'No targets.';
    q('draftGatePreview').textContent=d.preview_markdown||'No preview.';
    q('draftGateBlockers').innerHTML=(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No blockers.</b></div>';
    q('draftGateChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('draftGateSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Draft Save Gate loaded.');
}
function sendDraftSaveGateToMission(){
    if(!lastDraftSaveGate){toast('Load Draft Save Gate first.');return;}
    let d=lastDraftSaveGate, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Draft Save Approval Gate report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Gate ready: ${d.gate_ready}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} - ${s.book_title}
Chapter: ${s.chapter_number}
Draft title: ${s.draft_title}
Word count: ${s.word_count}
Char count: ${s.char_count}
Required phrase: ${s.required_phrase}
Phrase matches: ${s.phrase_matches}
Future targets: ${s.future_targets}
Collision targets: ${s.collision_targets}
Blockers: ${s.blockers}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Draft save enabled this build: ${s.draft_save_enabled_this_build}
Safe to save later: ${s.safe_to_save_later}

Proposed targets:
${(d.proposed_targets||[]).map(t=>`${t.kind}: ${t.path} | exists=${t.exists} | would_overwrite=${t.would_overwrite}`).join('\n')}

Blockers:
${(d.blockers||[]).length ? (d.blockers||[]).map(b=>`${b.id}: ${b.message}`).join('\n') : 'None.'}

Safety:
No draft saved yet.
No chapter file edit.
No story-file mutation.
No overwrite.
No delete.
No move.

Please determine:
1. Whether v10.13.1 should be marked stable/proven
2. Whether the next build should be Draft Save Approved Action.`;
    toast('Draft Save Gate sent to Mission Console.');
}

let lastChapterDraftWorkspace=null;
async function loadChapterDraftWorkspace(doExport=false){
    if(!q('chapterDraftStatus'))return;
    q('chapterDraftStatus').textContent='Loading Chapter Draft Workspace...';
    let body={project_id:'slipping_into_darkness',book_id:q('chapterDraftBook')?.value||'book_2',chapter_number:parseInt(q('chapterDraftChapter')?.value||'2'),draft_mode:q('chapterDraftMode')?.value||'first_pass',target_words:parseInt(q('chapterDraftTargetWords')?.value||'1800'),tone:q('chapterDraftTone')?.value||'dark mythic adventure',opening_seed:q('chapterDraftOpeningSeed')?.value||'',export:doExport};
    let d=await api('/api/writer/chapter_draft_workspace',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('chapterDraftStatus').textContent=d?.message||'Could not load Chapter Draft Workspace.';return;}
    lastChapterDraftWorkspace=d;
    let s=d.summary||{}, w=d.workspace||{};
    q('chapterDraftStatus').innerHTML=`<span class="chapterDraftBadge ${d.workspace_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterDraftSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=chapterDraftGrid><div class=chapterDraftMetric><div class=label>Ready</div><div class=value>${d.workspace_ready?'YES':'NO'}</div></div><div class=chapterDraftMetric><div class=label>Book</div><div class=value>${esc(s.book_id||'')}</div></div><div class=chapterDraftMetric><div class=label>Chapter</div><div class=value>${s.chapter_number||''}</div></div><div class=chapterDraftMetric><div class=label>Beats</div><div class=value>${s.beat_count||0}</div></div><div class=chapterDraftMetric><div class=label>Prompt</div><div class=value>${s.prompt_chars||0}</div></div><div class=chapterDraftMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=chapterDraftPath>Target: ${esc(s.selected_chapter_path||'')}</div>${d.exported?`<div class=chapterDraftPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('chapterDraftBrief').textContent=w.chapter_brief||'No brief.';
    q('chapterDraftBeats').innerHTML=(w.beat_sheet||[]).map(b=>`<div class=chapterDraftCard><b>${b.beat}. ${esc(b.name||'Beat')}</b><div>${esc(b.purpose||'')}</div></div>`).join('')||'No beat sheet.';
    q('chapterDraftPrompt').textContent=w.prose_prompt||'No prose prompt.';
    q('chapterDraftShell').textContent=w.draft_shell||'No draft shell.';
    q('chapterDraftChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterDraftSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Draft Workspace loaded.');
}
function sendChapterDraftWorkspaceToMission(){
    if(!lastChapterDraftWorkspace){toast('Load Chapter Draft Workspace first.');return;}
    let d=lastChapterDraftWorkspace, s=d.summary||{}, w=d.workspace||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Draft Workspace report.

Milestone: ${d.milestone}
Health: ${d.health_label}
Workspace ready: ${d.workspace_ready}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} - ${s.book_title}
Chapter: ${s.chapter_number}
Draft mode: ${s.draft_mode}
Target words: ${s.target_words}
Tone: ${s.tone}
Required sections: ${s.required_sections_present}/${s.required_sections}
Existing draft word count: ${s.existing_draft_word_count}
Beat count: ${s.beat_count}
Continuity guardrails: ${s.continuity_guardrails}
Prompt chars: ${s.prompt_chars}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Target: ${s.selected_chapter_path}

Chapter Brief:
${w.chapter_brief||''}

Beat Sheet:
${(w.beat_sheet||[]).map(b=>`${b.beat}. ${b.name}: ${b.purpose}`).join('\n')}

Prose Prompt:
${w.prose_prompt||''}

Export:
${d.exported?.markdown||'No exported Chapter Draft Workspace report'}

Safety:
Read-only draft workspace.
No chapter file edit.
No story-file mutation.
No overwrite.
No delete.
No move.

Please determine whether v10.13.0 should be marked stable/proven and whether the next build should be Draft Save Gate.`;
    toast('Chapter Draft Workspace sent to Mission Console.');
}

let lastChapterEditAudit=null;
async function loadChapterEditAudit(doExport=false){
    if(!q('chapterEditAuditStatus'))return;
    q('chapterEditAuditStatus').textContent='Loading Chapter Edit Audit Reader...';
    let body={book_id:q('chapterEditAuditBook')?.value||'book_2',export:doExport};
    let d=await api('/api/writer/chapter_edit_audit_reader',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){
        q('chapterEditAuditStatus').textContent=d?.message||'Could not load Chapter Edit Audit.';
        return;
    }
    lastChapterEditAudit=d;
    let s=d.summary||{};
    q('chapterEditAuditStatus').innerHTML=`<span class="chapterEditAuditBadge ${d.audit_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterEditAuditSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=chapterEditAuditGrid>
      <div class=chapterEditAuditMetric><div class=label>Ready</div><div class=value>${d.audit_ready?'YES':'NO'}</div></div>
      <div class=chapterEditAuditMetric><div class=label>Reports</div><div class=value>${s.reports_loaded||0}</div></div>
      <div class=chapterEditAuditMetric><div class=label>Edited</div><div class=value>${s.edited_reports||0}</div></div>
      <div class=chapterEditAuditMetric><div class=label>Backups</div><div class=value>${s.backup_files_found||0}</div></div>
      <div class=chapterEditAuditMetric><div class=label>Verified</div><div class=value>${s.edited_report_checks_passed||0}/${s.edited_report_checks||0}</div></div>
      <div class=chapterEditAuditMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=chapterEditAuditPath>Action reports: ${esc(s.action_report_folder||'')}</div>
    <div class=chapterEditAuditPath>Backup folder: ${esc(s.backup_folder||'')}</div>
    ${d.exported?`<div class=chapterEditAuditPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let l=d.latest_report||{};
    q('chapterEditAuditLatest').innerHTML=l.report_name?`<div><b>${esc(l.report_name)}</b></div>
      <div>Status: ${esc(l.status||'')} | Health: ${esc(l.health_label||'')} | Book: ${esc(l.book_id||'')} | Chapter: ${esc(String(l.chapter_number||''))}</div>
      <div>Phrase: ${l.phrase_matches} | Diff: ${l.diff_items} | Backups: ${l.created_backups} | Written: ${l.written_files} | Post: ${l.post_checks_passed}/${l.post_checks} | Problems: ${l.problems}</div>
      <div class=chapterEditAuditPath>Target: ${esc(l.selected_chapter_path||'')}</div>
      <div class=chapterEditAuditPath>Backup: ${esc(l.backup_path||'')}</div>
      <div class=chapterEditAuditPath>Hashes: before ${esc((l.before_hash||'').slice(0,12))} | backup ${esc((l.backup_hash||'').slice(0,12))} | after ${esc((l.after_hash||'').slice(0,12))}</div>`:'No latest report.';
    q('chapterEditAuditReportChecks').innerHTML=(d.edited_report_checks||[]).map(x=>`<div class="histrow ${x.ok?'ok':'fail'}"><b>${esc(x.report_name||'report')}</b><div>Status: ${esc(x.status||'')} | Backups: ${x.created_backups} | Written: ${x.written_files} | Post: ${x.post_checks_passed}/${x.post_checks} | Backup exists: ${x.backup_exists} | Problems: ${x.problems}</div></div>`).join('')||'No edited report checks.';
    q('chapterEditAuditBackups').innerHTML=(d.backup_inventory||[]).map(b=>`<div class=chapterEditAuditCard><b>${esc(b.name||'backup')}</b><div>${b.size||0} bytes | ${esc(b.modified||'')}</div><div class=chapterEditAuditPath>${esc(b.path||'')}</div></div>`).join('')||'No backups found.';
    q('chapterEditAuditChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterEditAuditSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Edit Audit loaded.');
}
function sendChapterEditAuditToMission(){
    if(!lastChapterEditAudit){toast('Load Chapter Edit Audit first.');return;}
    let d=lastChapterEditAudit, s=d.summary||{}, l=d.latest_report||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Edit Audit Reader report.

Milestone:
${d.milestone}
Health: ${d.health_label}
Audit ready: ${d.audit_ready}

Summary:
Book filter: ${s.book_filter}
Reports loaded: ${s.reports_loaded}
Edited reports: ${s.edited_reports}
Preview reports: ${s.preview_reports}
Blocked reports: ${s.blocked_reports}
Error reports: ${s.error_reports}
Backup files found: ${s.backup_files_found}
Edited report checks: ${s.edited_report_checks_passed}/${s.edited_report_checks}
Checks: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}

Latest report:
${l.report_name||'None'}
Status: ${l.status}
Health: ${l.health_label}
Book: ${l.book_id}
Chapter: ${l.chapter_number}
Phrase matches: ${l.phrase_matches}
Changed fields: ${l.changed_fields}
Diff items: ${l.diff_items}
Created backups: ${l.created_backups}
Written files: ${l.written_files}
Post checks: ${l.post_checks_passed}/${l.post_checks}
Problems: ${l.problems}
Target: ${l.selected_chapter_path}
Backup: ${l.backup_path}
Before hash: ${l.before_hash}
Backup hash: ${l.backup_hash}
After hash: ${l.after_hash}

Edited report checks:
${(d.edited_report_checks||[]).map(x=>`${x.ok?'PASS':'FAIL'} — ${x.report_name}: status=${x.status}, backup_exists=${x.backup_exists}, post=${x.post_checks_passed}/${x.post_checks}, problems=${x.problems}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Chapter Edit Audit report'}

Safety:
Read-only audit reader.
No chapter file edit.
No story-file mutation.
No overwrite.
No delete.
No move.

Please determine:
1. Whether v10.12.5 should be marked stable/proven
2. Whether the edit action audit trail is healthy
3. Whether the next build should be Chapter Draft Workspace.`;
    toast('Chapter Edit Audit sent to Mission Console.');
}

let lastChapterEditAction=null;
async function loadChapterEditApprovedAction(execute=false){
    if(!q('chapterEditActionStatus'))return;
    q('chapterEditActionStatus').textContent=execute?'Requesting approved chapter edit...':'Loading chapter edit action preview...';
    let body={
        project_id:'slipping_into_darkness',
        book_id:q('chapterEditActionBook')?.value||'book_2',
        chapter_number:parseInt(q('chapterEditActionChapter')?.value||'2'),
        approval_phrase:q('chapterEditActionPhrase')?.value||'',
        hook:q('chapterEditActionHook')?.value||'',
        execute:execute,
        export:true
    };
    let d=await api('/api/writer/chapter_edit_approved_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){
        q('chapterEditActionStatus').textContent=d?.message||'Could not load Chapter Edit Approved Action.';
        return;
    }
    lastChapterEditAction=d;
    let s=d.summary||{};
    let cls=d.status==='blocked'?'blocked':(d.status==='error'?'bad':'');
    q('chapterEditActionStatus').innerHTML=`<span class="chapterEditActionBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterEditActionSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=chapterEditActionGrid>
      <div class=chapterEditActionMetric><div class=label>Status</div><div class=value>${esc(s.status||'')}</div></div>
      <div class=chapterEditActionMetric><div class=label>Allowed</div><div class=value>${s.action_allowed?'YES':'NO'}</div></div>
      <div class=chapterEditActionMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div>
      <div class=chapterEditActionMetric><div class=label>Diff</div><div class=value>${s.diff_items||0}</div></div>
      <div class=chapterEditActionMetric><div class=label>Backups</div><div class=value>${s.created_backups||0}</div></div>
      <div class=chapterEditActionMetric><div class=label>Post</div><div class=value>${s.post_checks_passed||0}/${s.post_checks||0}</div></div>
    </div>
    <div class=chapterEditActionPath>Target: ${esc(s.selected_chapter_path||'')}</div>
    <div class=chapterEditActionPath>Backup: ${esc(s.backup_path||'')}</div>
    <div class=chapterEditActionPath>Export: ${esc(d.exported?.markdown||'')}</div>`;
    q('chapterEditActionDiff').innerHTML=(d.diff_summary||[]).map(x=>`<div class=chapterEditActionCard><b>${esc(x.field||'field')}</b><div>Old chars: ${x.old_chars} | New chars: ${x.new_chars} | Delta: ${x.delta_chars}</div><div><b>Old:</b> ${esc(x.old_preview||'')}</div><div><b>New:</b> ${esc(x.new_preview||'')}</div></div>`).join('')||'No diff.';
    let resultParts=[];
    if((d.blockers||[]).length){resultParts.push(...(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));}
    else{resultParts.push('<div class="histrow ok"><b>No blockers.</b></div>');}
    (d.created_backups||[]).forEach(p=>resultParts.push(`<div class="histrow ok"><b>Backup created</b><div class=chapterEditActionPath>${esc(p)}</div></div>`));
    (d.written_files||[]).forEach(p=>resultParts.push(`<div class="histrow ok"><b>Edited file</b><div class=chapterEditActionPath>${esc(p)}</div></div>`));
    (d.errors||[]).forEach(e=>resultParts.push(`<div class="histrow fail"><b>${esc(e.id||'error')}</b><div>${esc(e.message||'')}</div></div>`));
    q('chapterEditActionResults').innerHTML=resultParts.join('');
    q('chapterEditActionPreflight').innerHTML=(d.preflight_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No preflight.';
    q('chapterEditActionPostChecks').innerHTML=(d.post_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No post checks.';
    q('chapterEditActionSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Edit Approved Action report loaded.');
}
function sendChapterEditActionToMission(){
    if(!lastChapterEditAction){toast('Load Chapter Edit Approved Action first.');return;}
    let d=lastChapterEditAction, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Edit Approved Action report.

Milestone:
${d.milestone}
Health: ${d.health_label}
Status: ${d.status}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} — ${s.book_title}
Chapter: ${s.chapter_number}
Execute requested: ${s.execute_requested}
Action allowed: ${s.action_allowed}
Phrase matches: ${s.phrase_matches}
Changed fields: ${s.changed_fields}
Diff items: ${s.diff_items}
Blockers: ${s.blockers}
Errors: ${s.errors}
Preflight: ${s.preflight_checks_passed}/${s.preflight_checks}
Created backups: ${s.created_backups}
Written files: ${s.written_files}
Post checks: ${s.post_checks_passed}/${s.post_checks}
Problems: ${s.problems}
Target: ${s.selected_chapter_path}
Backup: ${s.backup_path}

Old Hook:
${d.old_hook}

New Hook:
${d.new_hook}

Blockers:
${(d.blockers||[]).length ? (d.blockers||[]).map(b=>`${b.id}: ${b.message}`).join('\n') : 'None.'}

Created backups:
${(d.created_backups||[]).join('\n')||'None.'}

Written files:
${(d.written_files||[]).join('\n')||'None.'}

Post checks:
${(d.post_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Chapter Edit Action report'}

Safety:
Requires exact phrase.
Requires direct diff.
Backup before write.
Controlled target rewrite after backup.
No delete.
No move.
No legacy changes.

Please determine:
1. Whether v10.12.4 should be marked stable/proven
2. Whether the chapter edit was saved safely if status is edited
3. Whether the next build should be Chapter Edit Audit Reader.`;
    toast('Chapter Edit Action sent to Mission Console.');
}

let lastChapterEditGate=null;

async function fillChapterEditGateFromCurrent(){
    if(!q('chapterEditGateStatus'))return;
    q('chapterEditGateStatus').textContent='Loading current saved chapter fields into gate...';
    let body={
        project_id:'slipping_into_darkness',
        book_id:q('chapterEditGateBook')?.value||'book_2',
        chapter_number:parseInt(q('chapterEditGateChapter')?.value||'2'),
        export:false
    };
    let d=await api('/api/writer/chapter_editor_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){
        q('chapterEditGateStatus').textContent=d?.message||'Could not load current chapter fields.';
        return;
    }
    let f=d.current_fields||{};
    const map={
        chapterEditGateTitle:'title',
        chapterEditGatePov:'pov',
        chapterEditGateLocation:'location',
        chapterEditGateGoal:'goal',
        chapterEditGateConflict:'conflict',
        chapterEditGateReveal:'reveal',
        chapterEditGateHook:'hook',
        chapterEditGateContinuity:'continuity_notes',
        chapterEditGateHandoffs:'handoff_tags_text',
        chapterEditGateDraft:'draft_space'
    };
    Object.entries(map).forEach(([id,key])=>{ if(q(id)) q(id).value=f[key]||''; });
    q('chapterEditGateStatus').innerHTML='<span class="chapterEditGateBadge">CURRENT FIELDS LOADED</span>';
    toast('Current chapter fields loaded into Edit Gate.');
}
async function applyChapterEditGateTestHook(){
    if(!q('chapterEditGateHook')){
        toast('Hook field not found.');
        return;
    }
    if(!(q('chapterEditGateHook').value||'').trim()){
        await fillChapterEditGateFromCurrent();
    }
    q('chapterEditGateHook').value='End with a physical artifact or mural clue that feels deliberately left for Anthony.';
    if(q('chapterEditGatePhrase'))q('chapterEditGatePhrase').value='APPROVE CHAPTER EDIT PREVIEW';
    toast('Tiny Hook test applied. Click One-Click Diff Proof Export or Test Phrase + Export.');
}




async function directChapterEditDiffProof(){
    if(!q('chapterEditGateStatus'))return;
    q('chapterEditGateStatus').textContent='Running direct diff proof...';
    let body={
        project_id:'slipping_into_darkness',
        book_id:q('chapterEditGateBook')?.value||'book_2',
        chapter_number:parseInt(q('chapterEditGateChapter')?.value||'2')
    };
    let d=await api('/api/writer/chapter_edit_direct_diff_proof',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){
        q('chapterEditGateStatus').textContent=d?.message||'Direct diff proof failed.';
        return;
    }
    lastChapterEditGate=d;
    let s=d.summary||{};
    q('chapterEditGateStatus').innerHTML=`<span class="chapterEditGateBadge ${d.proof_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterEditGateSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=chapterEditGateGrid>
      <div class=chapterEditGateMetric><div class=label>Proof</div><div class=value>${s.proof_ready?'READY':'NO'}</div></div>
      <div class=chapterEditGateMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div>
      <div class=chapterEditGateMetric><div class=label>Changes</div><div class=value>${s.changed_fields||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Diff</div><div class=value>${s.diff_items||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Blockers</div><div class=value>${s.blockers||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=chapterEditGatePath>Target: ${esc(s.selected_chapter_path||'')}</div>
    <div class=chapterEditGatePath>Export: ${esc(d.exported?.markdown||'')}</div>`;
    q('chapterEditGateDiff').innerHTML=(d.diff_summary||[]).map(x=>`<div class=chapterEditGateCard><b>${esc(x.field||'field')}</b><div>Old chars: ${x.old_chars} | New chars: ${x.new_chars} | Delta: ${x.delta_chars}</div><div><b>Old preview:</b> ${esc(x.old_preview||'')}</div><div><b>New preview:</b> ${esc(x.new_preview||'')}</div></div>`).join('')||'<div class="histrow info"><b>No changed fields detected.</b></div>';
    let parts=[];
    if((d.blockers||[]).length){parts.push(...(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));}
    else{parts.push('<div class="histrow ok"><b>No hard blockers.</b></div>');}
    if((d.errors||[]).length){parts.push(...(d.errors||[]).map(e=>`<div class="histrow fail"><b>${esc(e.id||'error')}</b><div>${esc(e.message||'')}</div></div>`));}
    q('chapterEditGateBlockers').innerHTML=parts.join('');
    q('chapterEditGateChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterEditGateSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Direct diff proof exported.');
}

async function serverChapterEditGateDiffSelfTest(){
    if(!q('chapterEditGateStatus'))return;
    q('chapterEditGateStatus').textContent='Running server-side diff self-test...';
    let body={
        project_id:'slipping_into_darkness',
        book_id:q('chapterEditGateBook')?.value||'book_2',
        chapter_number:parseInt(q('chapterEditGateChapter')?.value||'2')
    };
    let d=await api('/api/writer/chapter_edit_gate_diff_selftest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){
        q('chapterEditGateStatus').textContent=d?.message||'Server diff self-test failed.';
        return;
    }
    lastChapterEditGate=d;
    let s=d.summary||{};
    q('chapterEditGateStatus').innerHTML=`<span class="chapterEditGateBadge ${d.selftest_passed?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterEditGateSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=chapterEditGateGrid>
      <div class=chapterEditGateMetric><div class=label>Self-Test</div><div class=value>${d.selftest_passed?'PASS':'NO'}</div></div>
      <div class=chapterEditGateMetric><div class=label>Gate</div><div class=value>${s.gate_ready?'READY':'NO'}</div></div>
      <div class=chapterEditGateMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div>
      <div class=chapterEditGateMetric><div class=label>Changes</div><div class=value>${s.changed_fields||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Diff</div><div class=value>${s.diff_items||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=chapterEditGatePath>Target: ${esc(s.selected_chapter_path||'')}</div>
    <div class=chapterEditGatePath>Export: ${esc(d.selftest_exported?.markdown||d.exported?.markdown||'')}</div>`;
    q('chapterEditGateDiff').innerHTML=(d.diff_summary||[]).map(x=>`<div class=chapterEditGateCard><b>${esc(x.field||'field')}</b><div>Old chars: ${x.old_chars} | New chars: ${x.new_chars} | Delta: ${x.delta_chars}</div><div><b>Old preview:</b> ${esc(x.old_preview||'')}</div><div><b>New preview:</b> ${esc(x.new_preview||'')}</div></div>`).join('')||'<div class="histrow info"><b>No changed fields detected.</b></div>';
    let parts=[];
    if((d.blockers||[]).length){parts.push(...(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));}
    else{parts.push('<div class="histrow ok"><b>No hard blockers.</b></div>');}
    if((d.advisories||[]).length){parts.push(...(d.advisories||[]).map(a=>`<div class="histrow info"><b>${esc(a.id||'advisory')}</b><div>${esc(a.message||'')}</div></div>`));}
    q('chapterEditGateBlockers').innerHTML=parts.join('');
    q('chapterEditGateChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterEditGateSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Server diff self-test exported.');
}

async function oneClickChapterEditGateDiffProof(){
    if(!q('chapterEditGateStatus'))return;
    q('chapterEditGateStatus').textContent='Running one-click diff proof export...';
    let book=q('chapterEditGateBook')?.value||'book_2';
    let ch=parseInt(q('chapterEditGateChapter')?.value||'2');
    let proposedHook='End with a physical artifact or mural clue that feels deliberately left for Anthony.';
    if(q('chapterEditGateHook'))q('chapterEditGateHook').value=proposedHook;
    if(q('chapterEditGatePhrase'))q('chapterEditGatePhrase').value='APPROVE CHAPTER EDIT PREVIEW';
    let body={
        project_id:'slipping_into_darkness',
        book_id:book,
        chapter_number:ch,
        hook:proposedHook,
        approval_phrase:'APPROVE CHAPTER EDIT PREVIEW',
        export:true
    };
    let d=await api('/api/writer/chapter_edit_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){
        q('chapterEditGateStatus').textContent=d?.message||'One-click diff proof failed.';
        return;
    }
    lastChapterEditGate=d;
    let s=d.summary||{};
    q('chapterEditGateStatus').innerHTML=`<span class="chapterEditGateBadge ${d.gate_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterEditGateSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=chapterEditGateGrid>
      <div class=chapterEditGateMetric><div class=label>Gate</div><div class=value>${s.gate_ready?'READY':'NO'}</div></div>
      <div class=chapterEditGateMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div>
      <div class=chapterEditGateMetric><div class=label>Changes</div><div class=value>${s.changed_fields||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Diff</div><div class=value>${s.diff_items||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Blockers</div><div class=value>${s.blockers||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=chapterEditGatePath>Target: ${esc(s.selected_chapter_path||'')}</div>
    <div class=chapterEditGatePath>Required phrase: ${esc(s.required_phrase||'')}</div>
    <div class=chapterEditGatePath>Export: ${esc(d.exported?.markdown||'')}</div>`;
    q('chapterEditGateDiff').innerHTML=(d.diff_summary||[]).map(x=>`<div class=chapterEditGateCard><b>${esc(x.field||'field')}</b><div>Old chars: ${x.old_chars} | New chars: ${x.new_chars} | Delta: ${x.delta_chars}</div><div><b>Old preview:</b> ${esc(x.old_preview||'')}</div><div><b>New preview:</b> ${esc(x.new_preview||'')}</div></div>`).join('')||'<div class="histrow info"><b>No changed fields detected.</b></div>';
    let parts=[];
    if((d.blockers||[]).length){parts.push(...(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));}
    else{parts.push('<div class="histrow ok"><b>No hard blockers.</b></div>');}
    if((d.advisories||[]).length){parts.push(...(d.advisories||[]).map(a=>`<div class="histrow info"><b>${esc(a.id||'advisory')}</b><div>${esc(a.message||'')}</div></div>`));}
    q('chapterEditGateBlockers').innerHTML=parts.join('');
    q('chapterEditGateChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterEditGateSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('One-click diff proof exported.');
}

async function loadChapterEditGate(doExport=false,includePhrase=false){
    if(!q('chapterEditGateStatus'))return;
    q('chapterEditGateStatus').textContent='Loading Chapter Edit Approval Gate...';
    let body={
        project_id:'slipping_into_darkness',
        book_id:q('chapterEditGateBook')?.value||'book_2',
        chapter_number:parseInt(q('chapterEditGateChapter')?.value||'2'),
        export:doExport,
        approval_phrase:includePhrase?(q('chapterEditGatePhrase')?.value||''):''
    };
    let fields={title:'chapterEditGateTitle',pov:'chapterEditGatePov',location:'chapterEditGateLocation',goal:'chapterEditGateGoal',conflict:'chapterEditGateConflict',reveal:'chapterEditGateReveal',hook:'chapterEditGateHook',continuity_notes:'chapterEditGateContinuity',handoff_tags_text:'chapterEditGateHandoffs',draft_space:'chapterEditGateDraft'};
    Object.entries(fields).forEach(([k,id])=>{let v=q(id)?.value||''; if(v.trim())body[k]=v;});
    let d=await api('/api/writer/chapter_edit_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!d?.ok){q('chapterEditGateStatus').textContent=d?.message||'Could not load Chapter Edit Gate.';return;}
    lastChapterEditGate=d;
    let s=d.summary||{};
    q('chapterEditGateStatus').innerHTML=`<span class="chapterEditGateBadge ${d.gate_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterEditGateSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=chapterEditGateGrid>
      <div class=chapterEditGateMetric><div class=label>Gate</div><div class=value>${s.gate_ready?'READY':'NO'}</div></div>
      <div class=chapterEditGateMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div>
      <div class=chapterEditGateMetric><div class=label>Changes</div><div class=value>${s.changed_fields||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Blockers</div><div class=value>${s.blockers||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Advisories</div><div class=value>${s.advisories||0}</div></div>
      <div class=chapterEditGateMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=chapterEditGatePath>Target: ${esc(s.selected_chapter_path||'')}</div>
    <div class=chapterEditGatePath>Required phrase: ${esc(s.required_phrase||'')}</div>
    <div class=chapterEditGatePath>Backup preview path: ${esc(s.backup_preview_path||'')}</div>
    ${d.exported?`<div class=chapterEditGatePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('chapterEditGateDiff').innerHTML=(d.diff_summary||[]).map(x=>`<div class=chapterEditGateCard><b>${esc(x.field||'field')}</b><div>Old chars: ${x.old_chars} | New chars: ${x.new_chars} | Delta: ${x.delta_chars}</div><div><b>New preview:</b> ${esc(x.new_preview||'')}</div></div>`).join('')||'<div class="histrow info"><b>No changed fields detected.</b><div>The diff helper did not detect proposed field changes. Click Load Current Fields Into Gate, then Apply Tiny Hook Test, then Test Phrase + Export.</div></div>';
    let parts=[];
    if((d.blockers||[]).length){parts.push(...(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));}
    else{parts.push('<div class="histrow ok"><b>No hard blockers.</b></div>');}
    if((d.advisories||[]).length){parts.push(...(d.advisories||[]).map(a=>`<div class="histrow info"><b>${esc(a.id||'advisory')}</b><div>${esc(a.message||'')}</div></div>`));}
    q('chapterEditGateBlockers').innerHTML=parts.join('');
    q('chapterEditGateChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterEditGateSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Edit Gate loaded.');
}
function sendChapterEditGateToMission(){
    if(!lastChapterEditGate){toast('Load Chapter Edit Gate first.');return;}
    let d=lastChapterEditGate, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Edit Approval Gate.

Milestone:
${d.milestone}
Health: ${d.health_label}
Gate ready: ${d.gate_ready}
Safe to edit later: ${d.safe_to_edit_later}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} — ${s.book_title}
Chapter: ${s.chapter_number}
Target exists: ${s.target_exists}
Parent exists: ${s.parent_exists}
Edit save enabled in this build: ${s.edit_save_enabled_in_this_build}
Required phrase: ${s.required_phrase}
Phrase matches: ${s.phrase_matches}
Changed fields: ${s.changed_fields}
Blockers: ${s.blockers}
Advisories: ${s.advisories}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Target: ${s.selected_chapter_path}
Backup preview path: ${s.backup_preview_path}

Diff summary:
${(d.diff_summary||[]).length ? (d.diff_summary||[]).map(x=>`${x.field}: old=${x.old_chars}, new=${x.new_chars}, delta=${x.delta_chars}`).join('\n') : 'None.'}

Blockers:
${(d.blockers||[]).length ? (d.blockers||[]).map(b=>`${b.id}: ${b.message}`).join('\n') : 'None.'}

Advisories:
${(d.advisories||[]).length ? (d.advisories||[]).map(a=>`${a.id}: ${a.message}`).join('\n') : 'None.'}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Chapter Edit Gate report'}

Safety:
Read-only chapter edit gate.
No chapter file edit.
No story-file mutation.
No overwrite.
No delete.
No move.
No install.
No model cleanup.

Please determine:
1. Whether v10.12.3 should be marked stable/proven
2. Whether the gate safely blocks edit-save in this build
3. Whether the next build should be Chapter Edit Approved Action.`;
    toast('Chapter Edit Gate sent to Mission Console.');
}

let lastChapterEditorPreview=null;
function chapterEditorProposedPayload(){
    return {
        title:q('chapterEditorTitle')?.value||'',
        pov:q('chapterEditorPov')?.value||'',
        location:q('chapterEditorLocation')?.value||'',
        goal:q('chapterEditorGoal')?.value||'',
        conflict:q('chapterEditorConflict')?.value||'',
        reveal:q('chapterEditorReveal')?.value||'',
        hook:q('chapterEditorHook')?.value||'',
        continuity_notes:q('chapterEditorContinuity')?.value||'',
        handoff_tags_text:q('chapterEditorHandoffs')?.value||'',
        draft_space:q('chapterEditorDraft')?.value||''
    };
}
function setChapterEditorFields(f){
    if(!f)f={};
    if(q('chapterEditorTitle'))q('chapterEditorTitle').value=f.title||'';
    if(q('chapterEditorPov'))q('chapterEditorPov').value=f.pov||'';
    if(q('chapterEditorLocation'))q('chapterEditorLocation').value=f.location||'';
    if(q('chapterEditorGoal'))q('chapterEditorGoal').value=f.goal||'';
    if(q('chapterEditorConflict'))q('chapterEditorConflict').value=f.conflict||'';
    if(q('chapterEditorReveal'))q('chapterEditorReveal').value=f.reveal||'';
    if(q('chapterEditorHook'))q('chapterEditorHook').value=f.hook||'';
    if(q('chapterEditorContinuity'))q('chapterEditorContinuity').value=f.continuity_notes||'';
    if(q('chapterEditorHandoffs'))q('chapterEditorHandoffs').value=f.handoff_tags_text||'';
    if(q('chapterEditorDraft'))q('chapterEditorDraft').value=f.draft_space||'';
}
async function loadChapterEditorPreview(doExport=false,useProposed=false){
    if(!q('chapterEditorStatus'))return;
    q('chapterEditorStatus').textContent='Loading Chapter Editor Preview...';
    let book=q('chapterEditorBook')?.value||'book_2';
    let num=q('chapterEditorNumber')?.value||'1';
    let payload={project_id:'slipping_into_darkness',book_id:book,chapter_number:num,export:doExport};
    if(useProposed)payload.proposed=chapterEditorProposedPayload();
    let d=await api('/api/writer/chapter_editor_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!d?.ok){q('chapterEditorStatus').textContent=d?.message||'Could not load Chapter Editor Preview.';return;}
    lastChapterEditorPreview=d;
    let s=d.summary||{};
    q('chapterEditorStatus').innerHTML=`<span class="chapterEditorBadge ${d.editor_preview_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterEditorSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=chapterEditorGrid>
      <div class=chapterEditorMetric><div class=label>Ready</div><div class=value>${s.editor_preview_ready?'YES':'NO'}</div></div>
      <div class=chapterEditorMetric><div class=label>Book</div><div class=value>${esc(s.book_id||'')}</div></div>
      <div class=chapterEditorMetric><div class=label>Chapter</div><div class=value>${s.selected_chapter_number||''}</div></div>
      <div class=chapterEditorMetric><div class=label>Options</div><div class=value>${s.chapter_options||0}</div></div>
      <div class=chapterEditorMetric><div class=label>Changes</div><div class=value>${s.changed_fields||0}</div></div>
      <div class=chapterEditorMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=chapterEditorPath>Selected file: ${esc(s.selected_chapter_path||'')}</div>
    ${d.exported?`<div class=chapterEditorPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    if(!useProposed)setChapterEditorFields(d.current_fields||{});
    q('chapterEditorChanges').innerHTML=(d.changed_fields||[]).map(c=>`<div class=chapterEditorCard><b>${esc(c.field||'field')}</b><div>${c.before_chars} chars → ${c.after_chars} chars</div><div><b>Before:</b> ${esc(c.before_preview||'')}</div><div><b>After:</b> ${esc(c.after_preview||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No unsaved changes detected.</b></div>';
    q('chapterEditorChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterEditorSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Editor Preview loaded.');
}
function sendChapterEditorPreviewToMission(){
    if(!lastChapterEditorPreview){toast('Load Chapter Editor Preview first.');return;}
    let d=lastChapterEditorPreview, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Editor Preview.

Milestone:
${d.milestone}
Health: ${d.health_label}
Editor preview ready: ${d.editor_preview_ready}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} — ${s.book_title}
Chapter: ${s.selected_chapter_number}
Selected file: ${s.selected_chapter_path}
Chapter options: ${s.chapter_options}
Raw chars: ${s.current_raw_chars}
Preview Markdown chars: ${s.preview_markdown_chars}
Changed fields: ${s.changed_fields}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}

Changed fields:
${(d.changed_fields||[]).length ? (d.changed_fields||[]).map(c=>`${c.field}: ${c.before_chars} chars -> ${c.after_chars} chars`).join('\n') : 'None.'}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Chapter Editor Preview report'}

Safety:
Read-only chapter editor preview.
No chapter file edit.
No story-file mutation.
No project creation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No move.
No install.
No model cleanup.

Please determine:
1. Whether v10.12.2 should be marked stable/proven
2. Whether the fields parse correctly
3. Whether the next build should be Chapter Edit Approval Gate.`;
    toast('Chapter Editor Preview sent to Mission Console.');
}

let lastSavedChapterDashboard=null;
async function loadSavedChapterDashboard(doExport=false){
    if(!q('savedChapterStatus'))return;
    q('savedChapterStatus').textContent='Loading Saved Chapter Dashboard...';
    let book=q('savedChapterBook')?.value||'book_2';
    let d=await api('/api/writer/saved_chapter_dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',book_id:book,export:doExport})});
    if(!d?.ok){q('savedChapterStatus').textContent=d?.message||'Could not load Saved Chapter Dashboard.';return;}
    lastSavedChapterDashboard=d; let s=d.summary||{};
    q('savedChapterStatus').innerHTML=`<span class="savedChapterBadge ${d.dashboard_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('savedChapterSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=savedChapterGrid><div class=savedChapterMetric><div class=label>Ready</div><div class=value>${s.dashboard_ready?'YES':'NO'}</div></div><div class=savedChapterMetric><div class=label>Book</div><div class=value>${esc(s.book_id||'')}</div></div><div class=savedChapterMetric><div class=label>Expected</div><div class=value>${s.expected_markdown_targets_ok||0}/${s.expected_markdown_targets||0}</div></div><div class=savedChapterMetric><div class=label>Cards</div><div class=value>${s.markdown_cards_found||0}</div></div><div class=savedChapterMetric><div class=label>Handoff</div><div class=value>${s.continuity_handoff_checks_passed||0}/${s.continuity_handoff_checks||0}</div></div><div class=savedChapterMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div></div><div class=savedChapterPath>Book folder: ${esc(s.book_folder||'')}</div><div class=savedChapterPath>Preview set valid: ${s.preview_set_valid} | Status: ${esc(s.preview_set_status||'')}</div>${d.exported?`<div class=savedChapterPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('savedChapterPreviewSet').innerHTML=`<pre>${esc(JSON.stringify(d.preview_set_summary||{},null,2))}</pre>`;
    q('savedChapterCards').innerHTML=(d.markdown_files||[]).map(f=>`<div class=savedChapterCard><b>${esc(f.name||'')}</b><div>${f.size||0} bytes | ${esc(f.modified||'')}</div><div>Goal: ${f.has_goal} | Conflict: ${f.has_conflict} | Reveal: ${f.has_reveal} | Hook: ${f.has_hook} | Handoffs: ${f.has_handoff_tags} | Safety: ${f.has_safety}</div><div class=savedChapterPath>${esc(f.path||'')}</div></div>`).join('')||'No Markdown chapter cards found.';
    q('savedChapterHandoff').innerHTML=`<div class=savedChapterPath>${esc(d.continuity_handoff_path||'')}</div><pre>${esc(d.continuity_handoff_preview?.text||'Continuity handoff missing or empty.')}</pre>`;
    q('savedChapterChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('savedChapterSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Saved Chapter Dashboard loaded.');
}
function sendSavedChapterDashboardToMission(){
    if(!lastSavedChapterDashboard){toast('Load Saved Chapter Dashboard first.');return;}
    let d=lastSavedChapterDashboard, s=d.summary||{}; go('mission');
    q('input').value=`Please review this Kayock Writer Saved Chapter Reader / Dashboard.\n\nMilestone:\n${d.milestone}\nHealth: ${d.health_label}\nDashboard ready: ${d.dashboard_ready}\n\nSummary:\nProject: ${s.project_title}\nBook: ${s.book_id} — ${s.book_title}\nPreview set valid: ${s.preview_set_valid}\nPreview set status: ${s.preview_set_status}\nExpected chapter cards: ${s.expected_chapter_cards}\nMarkdown cards found: ${s.markdown_cards_found}\nExpected Markdown targets: ${s.expected_markdown_targets_ok}/${s.expected_markdown_targets}\nContinuity handoff checks: ${s.continuity_handoff_checks_passed}/${s.continuity_handoff_checks}\nChecks passed: ${s.checks_passed}/${s.checks}\nProblems: ${s.problems}\nBook folder: ${s.book_folder}\n\nChecks:\n${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}\n\nExport:\n${d.exported?.markdown||'No exported Saved Chapter Dashboard report'}\n\nSafety:\nRead-only saved-chapter dashboard. No chapter file creation. No story-file mutation. No overwrite/delete/move.\n\nPlease determine whether v10.12.0 should be marked stable/proven.`;
    toast('Saved Chapter Dashboard sent to Mission Console.');
}

let lastChapterSaveAction=null;
async function loadChapterSaveAction(execute=false,includePhrase=false){
    if(!q('chapterSaveActionStatus'))return;
    q('chapterSaveActionStatus').textContent=execute?'Requesting approved chapter save...':'Loading chapter save action preview...';
    let book=q('chapterSaveActionBook')?.value||'book_1';
    let phrase=includePhrase?(q('chapterSaveActionPhrase')?.value||''):'';
    let d=await api('/api/writer/chapter_save_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',book_id:book,approval_phrase:phrase,execute:execute,export:true})});
    if(!d?.ok){q('chapterSaveActionStatus').textContent=d?.message||'Could not load Chapter Save Action.';return;}
    lastChapterSaveAction=d;
    let s=d.summary||{};
    let cls=d.status==='created'?'created':(d.status==='blocked'?'blocked':(d.status==='error'?'error':''));
    q('chapterSaveActionStatus').innerHTML=`<span class="chapterSaveActionBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterSaveActionSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=chapterSaveActionGrid><div class=chapterSaveActionMetric><div class=label>Status</div><div class=value>${esc(s.status||'')}</div></div><div class=chapterSaveActionMetric><div class=label>Allowed</div><div class=value>${s.action_allowed?'YES':'NO'}</div></div><div class=chapterSaveActionMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div><div class=chapterSaveActionMetric><div class=label>Targets</div><div class=value>${s.save_targets||0}</div></div><div class=chapterSaveActionMetric><div class=label>Written</div><div class=value>${s.written_files||0}</div></div><div class=chapterSaveActionMetric><div class=label>Checks</div><div class=value>${s.post_checks_passed||0}/${s.post_checks||0}</div></div></div><div class=chapterSaveActionPath>Book: ${esc(s.book_id||'')} — ${esc(s.book_title||'')}</div><div class=chapterSaveActionPath>Book folder: ${esc(s.book_folder||'')}</div><div class=chapterSaveActionPath>Preview set: ${esc(s.preview_set_target||'')}</div><div class=chapterSaveActionPath>Handoff: ${esc(s.continuity_handoff_target||'')}</div>${d.exported?`<div class=chapterSaveActionPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let parts=[];
    if((d.blockers||[]).length){parts.push(...(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));} else {parts.push('<div class="histrow ok"><b>No blockers.</b></div>');}
    if((d.overwrite_risks||[]).length){parts.push(...(d.overwrite_risks||[]).map(r=>`<div class="histrow fail"><b>Overwrite risk</b><div class=chapterSaveActionPath>${esc(r.path||'')}</div></div>`));} else {parts.push('<div class="histrow ok"><b>No overwrite risks.</b></div>');}
    q('chapterSaveActionBlockers').innerHTML=parts.join('');
    q('chapterSaveActionPreflight').innerHTML=(d.preflight||[]).map(p=>`<div class=chapterSaveActionCard><b>${esc(p.id||'target')}</b><div>Kind: ${esc(p.kind||'')} | Exists: ${p.exists} | Would overwrite: ${p.would_overwrite} | Execute if approved: ${p.will_execute_if_approved}</div><div class=chapterSaveActionPath>${esc(p.path||'')}</div></div>`).join('')||'No preflight.';
    let results=[];(d.created_dirs||[]).forEach(p=>results.push(`<div class="histrow ok"><b>Created folder</b><div class=chapterSaveActionPath>${esc(p)}</div></div>`));(d.written_files||[]).forEach(p=>results.push(`<div class="histrow ok"><b>Wrote file</b><div class=chapterSaveActionPath>${esc(p)}</div></div>`));(d.errors||[]).forEach(e=>results.push(`<div class="histrow fail"><b>Error</b><div>${esc(JSON.stringify(e))}</div></div>`));
    q('chapterSaveActionResults').innerHTML=results.join('')||'<div class="histrow info"><b>No chapter save executed.</b><div>This is preview/block mode unless exact phrase and execute are used.</div></div>';
    q('chapterSaveActionChecks').innerHTML=(d.post_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No post checks.';
    q('chapterSaveActionSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Save Action report loaded.');
}
function sendChapterSaveActionToMission(){
    if(!lastChapterSaveAction){toast('Load Chapter Save Action first.');return;}
    let d=lastChapterSaveAction, s=d.summary||{}; go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Save Approved Action report.

Milestone:
${d.milestone}
Health: ${d.health_label}
Status: ${d.status}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} — ${s.book_title}
Execute requested: ${s.execute_requested}
Action allowed: ${s.action_allowed}
Phrase matches: ${s.phrase_matches}
Blockers: ${s.blockers}
Overwrite risks: ${s.overwrite_risks}
Save targets: ${s.save_targets}
Chapter cards: ${s.chapter_cards}
Created dirs: ${s.created_dirs}
Written files: ${s.written_files}
Errors: ${s.errors}
Post checks: ${s.post_checks_passed}/${s.post_checks}
Book folder: ${s.book_folder}
Preview set target: ${s.preview_set_target}
Continuity handoff target: ${s.continuity_handoff_target}

Blockers:
${(d.blockers||[]).length ? (d.blockers||[]).map(b=>`${b.id}: ${b.message}`).join('\n') : 'None.'}

Written files:
${(d.written_files||[]).join('\n')||'None.'}

Created dirs:
${(d.created_dirs||[]).join('\n')||'None.'}

Post checks:
${(d.post_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Errors:
${(d.errors||[]).length ? (d.errors||[]).map(e=>JSON.stringify(e)).join('\n') : 'None.'}

Export:
${d.exported?.markdown||'No exported Chapter Save Action report'}

Safety:
Requires exact phrase.
No action without phrase.
No overwrite.
No delete.
No move.
No legacy changes.
No install.
No model cleanup.

Please determine:
1. Whether v10.11.9 should be marked stable/proven
2. Whether chapter files were saved safely if status is created
3. Whether the next build should be Chapter Reader / Saved Chapter Dashboard.`;
    toast('Chapter Save Action sent to Mission Console.');
}

let lastChapterSaveGate=null;
async function loadChapterSaveGate(doExport=false){
    if(!q('chapterSaveGateStatus'))return;
    q('chapterSaveGateStatus').textContent='Loading Chapter Save Approval Gate...';
    let book=q('chapterSaveGateBook')?.value||'book_1';
    let phrase=q('chapterSaveGatePhrase')?.value||'';
    let d=await api('/api/writer/chapter_save_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',book_id:book,approval_phrase:phrase,export:doExport})});
    if(!d?.ok){
        q('chapterSaveGateStatus').textContent=d?.message||'Could not load Chapter Save Gate.';
        return;
    }
    lastChapterSaveGate=d;
    let s=d.summary||{};
    q('chapterSaveGateStatus').innerHTML=`<span class="saveGateBadge ${d.gate_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterSaveGateSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=saveGateGrid>
      <div class=saveGateMetric><div class=label>Gate</div><div class=value>${d.gate_ready?'READY':'NO'}</div></div>
      <div class=saveGateMetric><div class=label>Safe Later</div><div class=value>${s.safe_to_save_later?'YES':'NO'}</div></div>
      <div class=saveGateMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div>
      <div class=saveGateMetric><div class=label>Targets</div><div class=value>${s.proposed_targets||0}</div></div>
      <div class=saveGateMetric><div class=label>Overwrite</div><div class=value>${s.overwrite_risks||0}</div></div>
      <div class=saveGateMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=saveGatePath>Book: ${esc(s.book_id||'')} — ${esc(s.book_title||'')}</div>
    <div class=saveGatePath>Chapters folder: ${esc(s.chapters_folder||'')}</div>
    ${d.exported?`<div class=saveGatePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let g=d.approval_gate||{};
    q('chapterSaveGateApproval').textContent=`Required phrase:
${g.required_phrase||''}

Typed phrase present: ${g.typed_phrase_present}
Typed phrase matches: ${g.typed_phrase_matches}
Phrase gate status: ${g.phrase_gate_status}
Save enabled in this build: ${g.save_enabled_in_this_build}

Reason:
${g.reason_save_disabled||''}

Preview required: ${g.preview_required}
No-overwrite required: ${g.no_overwrite_required}
Evidence required before write: ${g.backup_or_evidence_required_before_write}
No delete allowed: ${g.no_delete_allowed}
No move allowed: ${g.no_move_allowed}
No automatic story mutation: ${g.no_automatic_story_mutation}`;
    q('chapterSaveGateTargets').innerHTML=(d.proposed_targets||[]).map(t=>`<div class=saveGateCard><b>${esc(t.id||'target')}</b><div>${esc(t.title||'')} | Kind: ${esc(t.kind||'')}</div><div>Target exists: ${t.target_exists} | Parent exists: ${t.parent_exists} | Overwrite risk: ${t.would_overwrite} | Executes now: ${t.will_execute_in_this_build}</div><div class=saveGatePath>${esc(t.target||'')}</div></div>`).join('')||'No proposed targets.';
    let parts=[];
    if((d.blockers||[]).length){parts.push(...(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`));}
    else{parts.push('<div class="histrow ok"><b>No gate blockers.</b><div>Future save may be safe after exact phrase and approved action build.</div></div>');}
    if((d.overwrite_risks||[]).length){parts.push(...(d.overwrite_risks||[]).map(r=>`<div class="histrow fail"><b>Overwrite risk</b><div class=saveGatePath>${esc(r.target||'')}</div></div>`));}
    else{parts.push('<div class="histrow ok"><b>No overwrite risks detected.</b></div>');}
    q('chapterSaveGateRisks').innerHTML=parts.join('');
    q('chapterSaveGateChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterSaveGateSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Save Gate loaded.');
}
function sendChapterSaveGateToMission(){
    if(!lastChapterSaveGate){toast('Load Chapter Save Gate first.');return;}
    let d=lastChapterSaveGate, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Save Approval Gate.

Milestone:
${d.milestone}
Health: ${d.health_label}
Gate ready: ${d.gate_ready}
Safe to save later: ${d.safe_to_save_later}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} — ${s.book_title}
Preview ready: ${s.preview_ready}
Save enabled in this build: ${s.save_enabled_in_this_build}
Required phrase: ${s.required_phrase}
Typed phrase present: ${s.typed_phrase_present}
Phrase matches: ${s.phrase_matches}
Phrase gate status: ${s.phrase_gate_status}
Chapter cards: ${s.chapter_cards}
Proposed targets: ${s.proposed_targets}
Overwrite risks: ${s.overwrite_risks}
Parent missing expected: ${s.parent_missing_expected}
Blockers: ${s.blockers}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Chapters folder: ${s.chapters_folder}

Approval gate:
${JSON.stringify(d.approval_gate,null,2)}

Proposed targets:
${(d.proposed_targets||[]).map(t=>`${t.id}: ${t.title}; target=${t.target}; exists=${t.target_exists}; overwrite=${t.would_overwrite}; executes_now=${t.will_execute_in_this_build}`).join('\n')}

Overwrite risks:
${(d.overwrite_risks||[]).length ? (d.overwrite_risks||[]).map(r=>r.target).join('\n') : 'None.'}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Chapter Save Gate report'}

Safety:
Gate preview only.
Read-only project scan.
No chapter file creation.
No story-file mutation.
No project creation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No move.
No install.
No model cleanup.

Please determine:
1. Whether v10.11.8 should be marked stable/proven
2. Whether the target filenames are acceptable
3. Whether the next build should be Chapter Save Approved Action.`;
    toast('Chapter Save Gate sent to Mission Console.');
}

let lastChapterPlanner=null;
async function loadChapterPlanner(doExport=false){
    if(!q('chapterPlannerStatus'))return;
    q('chapterPlannerStatus').textContent='Loading Chapter Planner Preview...';
    let book=q('chapterPlannerBook')?.value||'book_1';
    let d=await api('/api/writer/chapter_planner_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',book_id:book,export:doExport})});
    if(!d?.ok){
        q('chapterPlannerStatus').textContent=d?.message||'Could not load Chapter Planner Preview.';
        return;
    }
    lastChapterPlanner=d;
    let s=d.summary||{};
    q('chapterPlannerStatus').innerHTML=`<span class="chapterBadge ${d.preview_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('chapterPlannerSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=chapterGrid>
      <div class=chapterMetric><div class=label>Ready</div><div class=value>${s.preview_ready?'YES':'NO'}</div></div>
      <div class=chapterMetric><div class=label>Book</div><div class=value>${esc(s.book_id||'')}</div></div>
      <div class=chapterMetric><div class=label>Cards</div><div class=value>${s.chapter_cards_previewed||0}</div></div>
      <div class=chapterMetric><div class=label>Existing</div><div class=value>${s.existing_chapter_files||0}</div></div>
      <div class=chapterMetric><div class=label>Writes On</div><div class=value>${s.future_writes_enabled_now||0}/${s.future_writes||0}</div></div>
      <div class=chapterMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=chapterPath>Chapters folder: ${esc(s.chapters_folder||'')}</div>
    ${d.exported?`<div class=chapterPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let b=d.selected_book||{};
    q('chapterPlannerBookInfo').textContent=`${b.title||''}
Status: ${b.status||''}

${b.summary||''}`;
    q('chapterPlannerCards').innerHTML=(d.chapter_templates||[]).map(c=>`<div class=chapterCard><b>Chapter ${c.chapter_number}: ${esc(c.title||'')}</b>
<div><b>Goal:</b> ${esc(c.goal||'')}</div>
<div><b>Conflict:</b> ${esc(c.conflict||'')}</div>
<div><b>Reveal:</b> ${esc(c.reveal||'')}</div>
<div><b>Hook:</b> ${esc(c.hook||'')}</div>
<div><b>POV:</b> ${esc(c.pov||'')} | <b>Location:</b> ${esc(c.location||'')}</div>
<div class=chapterPath>Continuity: ${(c.continuity_notes||[]).map(x=>esc(x)).join('; ')}</div>
<div class=chapterPath>Handoffs: ${esc(JSON.stringify(c.handoff_tags||{}))}</div></div>`).join('')||'No chapter card previews.';
    q('chapterPlannerFutureWrites').innerHTML=(d.future_writes||[]).map(w=>`<div class="histrow info"><b>${esc(w.title||'')}</b><div>ID: ${esc(w.id||'')} | Enabled now: ${w.enabled_now} | Requires approval: ${w.requires_user_approval}</div><div class=chapterPath>${esc(w.target||'')}</div></div>`).join('')||'No future writes.';
    q('chapterPlannerChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('chapterPlannerSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Chapter Planner Preview loaded.');
}
function sendChapterPlannerToMission(){
    if(!lastChapterPlanner){toast('Load Chapter Planner first.');return;}
    let d=lastChapterPlanner, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Chapter Planner Preview.

Milestone:
${d.milestone}
Health: ${d.health_label}
Preview ready: ${d.preview_ready}

Summary:
Project: ${s.project_title}
Book: ${s.book_id} — ${s.book_title}
Book status: ${s.book_status}
Book summary: ${s.book_summary}
Chapter cards previewed: ${s.chapter_cards_previewed}
Existing chapter files: ${s.existing_chapter_files}
Future writes enabled now: ${s.future_writes_enabled_now}/${s.future_writes}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Chapters folder: ${s.chapters_folder}

Chapter cards:
${(d.chapter_templates||[]).map(c=>`Chapter ${c.chapter_number}: ${c.title}
Goal: ${c.goal}
Conflict: ${c.conflict}
Reveal: ${c.reveal}
Hook: ${c.hook}
POV: ${c.pov}
Location: ${c.location}
Continuity: ${(c.continuity_notes||[]).join('; ')}
Handoffs: ${JSON.stringify(c.handoff_tags)}`).join('\n\n')}

Future writes:
${(d.future_writes||[]).map(w=>`${w.id}: enabled_now=${w.enabled_now}; target=${w.target}; approval=${w.requires_user_approval}`).join('\n')}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Chapter Planner report'}

Safety:
Preview only.
Read-only project scan.
No chapter file creation.
No story-file mutation.
No project creation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No move.
No install.
No model cleanup.

Please determine:
1. Whether v10.11.7 should be marked stable/proven
2. Whether this chapter card structure is good for Story Forge
3. Whether the next build should be Chapter Save Approval Gate.`;
    toast('Chapter Planner sent to Mission Console.');
}

let lastStoryProjectHealth=null;
async function loadStoryProjectHealth(doExport=false){
    if(!q('storyProjectHealthStatus'))return;
    q('storyProjectHealthStatus').textContent='Loading Story Project health...';
    let d=await api('/api/writer/project_health_card',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',export:doExport})});
    if(!d?.ok){
        q('storyProjectHealthStatus').textContent=d?.message||'Could not load Story Project health card.';
        return;
    }
    lastStoryProjectHealth=d;
    let s=d.summary||{};
    let cls=d.card_state==='clear'?'clear':(d.card_state==='advisory'?'advisory':'bad');
    q('storyProjectHealthStatus').innerHTML=`<span class="storyHealthBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('storyProjectHealthBody').innerHTML=`<div><b>${esc(d.project_title||'')}</b></div>
    <div class=storyHealthGrid>
      <div class=storyHealthMetric><div class=label>Project</div><div class=value>${s.project_exists?'YES':'NO'}</div></div>
      <div class=storyHealthMetric><div class=label>Manifest</div><div class=value>${s.manifest_valid?'VALID':'NO'}</div></div>
      <div class=storyHealthMetric><div class=label>Folders</div><div class=value>${s.required_folders_ok||0}/${s.required_folders||0}</div></div>
      <div class=storyHealthMetric><div class=label>Sources</div><div class=value>${s.expected_sources_ok||0}/${s.expected_sources||0}</div></div>
      <div class=storyHealthMetric><div class=label>Books</div><div class=value>${s.books_in_manifest||0}</div></div>
      <div class=storyHealthMetric><div class=label>Checks</div><div class=value>${s.dashboard_checks_passed||0}/${s.dashboard_checks||0}</div></div>
    </div>
    <div class=storyHealthLine>Manifest status: ${esc(s.manifest_status||'')}</div>
    <div class=storyHealthLine>README: ${s.readme_exists} • Books.md: ${s.books_outline_exists} • Source files: ${s.source_files||0}</div>
    <div class=storyHealthLine>Project root: ${esc(d.project_root||'')}</div>
    ${(d.needs_attention||[]).length?`<div class=storyHealthLine>Attention: ${(d.needs_attention||[]).map(a=>esc(a.title)).join(', ')}</div>`:''}
    ${(d.advisories||[]).length?`<div class=storyHealthLine>Advisory: ${(d.advisories||[]).map(a=>esc(a.title)).join(', ')}</div>`:''}
    ${d.exported?`<div class=storyHealthLine>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    toast('Story Project health card loaded.');
}
function sendStoryProjectHealthToMission(){
    if(!lastStoryProjectHealth){toast('Refresh Project Health first.');return;}
    let d=lastStoryProjectHealth, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Story Project Health Card.

Milestone:
${d.milestone}
Health: ${d.health_label}
Card state: ${d.card_state}
Project: ${d.project_title}
Project root: ${d.project_root}
Dashboard ready: ${d.dashboard_ready}

Summary:
Project exists: ${s.project_exists}
Manifest exists: ${s.manifest_exists}
Manifest valid: ${s.manifest_valid}
Manifest status: ${s.manifest_status}
README exists: ${s.readme_exists}
Books.md exists: ${s.books_outline_exists}
Required folders OK: ${s.required_folders_ok}/${s.required_folders}
Source files: ${s.source_files}
Source JSON/Markdown/Text: ${s.source_json}/${s.source_markdown}/${s.source_text}
Expected sources OK: ${s.expected_sources_ok}/${s.expected_sources}
Books in manifest: ${s.books_in_manifest}
Dashboard checks passed: ${s.dashboard_checks_passed}/${s.dashboard_checks}
Dashboard problems: ${s.dashboard_problems}

Attention:
${(d.needs_attention||[]).length ? (d.needs_attention||[]).map(a=>`${a.id}: ${a.summary}`).join('\n') : 'None.'}

Advisories:
${(d.advisories||[]).length ? (d.advisories||[]).map(a=>`${a.id}: ${a.summary}`).join('\n') : 'None.'}

Export:
${d.exported?.markdown||'No exported project health card'}

Safety:
Read-only health card.
No story-file mutation.
No project creation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No move.
No install.
No model cleanup.

Please determine:
1. Whether v10.11.6 should be marked stable/proven
2. Whether Story Forge should use this as its compact project status
3. Whether the next build should be Chapter Planner Preview.`;
    toast('Story Project health sent to Mission Console.');
}

let lastProjectDashboard=null;
async function loadProjectDashboard(doExport=false){
    if(!q('projectDashboardStatus'))return;
    q('projectDashboardStatus').textContent='Loading Story Project Dashboard...';
    let d=await api('/api/writer/project_dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',export:doExport})});
    if(!d?.ok){
        q('projectDashboardStatus').textContent=d?.message||'Could not load project dashboard.';
        return;
    }
    lastProjectDashboard=d;
    let s=d.summary||{};
    q('projectDashboardStatus').innerHTML=`<span class="dashProjectBadge ${d.dashboard_ready?'':'bad'}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('projectDashboardSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=projectDashGrid>
      <div class=projectDashMetric><div class=label>Ready</div><div class=value>${s.dashboard_ready?'YES':'NO'}</div></div>
      <div class=projectDashMetric><div class=label>Folders</div><div class=value>${s.required_folders_ok||0}/${s.required_folders||0}</div></div>
      <div class=projectDashMetric><div class=label>Sources</div><div class=value>${s.source_files||0}</div></div>
      <div class=projectDashMetric><div class=label>Expected</div><div class=value>${s.expected_sources_ok||0}/${s.expected_sources||0}</div></div>
      <div class=projectDashMetric><div class=label>Books</div><div class=value>${s.books_in_manifest||0}</div></div>
      <div class=projectDashMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=projectDashPath>Project root: ${esc(s.project_root||'')}</div>
    <div class=projectDashPath>Manifest status: ${esc(s.manifest_status||'')} | README: ${s.readme_exists} | Books.md: ${s.books_outline_exists}</div>
    ${d.exported?`<div class=projectDashPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let m=d.manifest_summary||{};
    q('projectDashboardManifest').innerHTML=`<pre>${esc(JSON.stringify(m,null,2))}</pre>`;
    q('projectDashboardFolders').innerHTML=(d.folder_checks||[]).map(f=>`<div class="histrow ${f.ok?'ok':'fail'}"><b>${esc(f.name||'folder')}</b><div>${f.exists?'exists':'missing'} | ${esc(f.kind||'')}</div><div class=projectDashPath>${esc(f.path||'')}</div></div>`).join('')||'No folder checks.';
    q('projectDashboardSources').innerHTML=(d.source_files||[]).map(f=>`<div class="projectDashCard"><b>${esc(f.name||'')}</b><div>${esc(f.suffix||'')} | ${f.size||0} bytes | ${esc(f.modified||'')}</div><div class=projectDashPath>${esc(f.path||'')}</div></div>`).join('')||'No source files.';
    q('projectDashboardReadme').innerHTML=`<pre>${esc(d.readme_preview?.text||'README missing or empty.')}</pre>`;
    q('projectDashboardBooks').innerHTML=`<pre>${esc(d.books_preview?.text||'Books.md missing or empty.')}</pre>`;
    q('projectDashboardChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('projectDashboardSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Story Project Dashboard loaded.');
}
function sendProjectDashboardToMission(){
    if(!lastProjectDashboard){toast('Load Project Dashboard first.');return;}
    let d=lastProjectDashboard, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Story Project Reader / Dashboard report.

Milestone:
${d.milestone}
Health: ${d.health_label}
Dashboard ready: ${d.dashboard_ready}

Summary:
Project: ${s.title}
Project ID: ${s.project_id}
Project exists: ${s.project_exists}
Project root: ${s.project_root}
Required folders OK: ${s.required_folders_ok}/${s.required_folders}
Manifest exists: ${s.manifest_exists}
Manifest valid: ${s.manifest_valid}
Manifest status: ${s.manifest_status}
README exists: ${s.readme_exists}
Books.md exists: ${s.books_outline_exists}
Source files: ${s.source_files}
Source JSON/Markdown/Text: ${s.source_json}/${s.source_markdown}/${s.source_text}
Expected sources OK: ${s.expected_sources_ok}/${s.expected_sources}
Books in manifest: ${s.books_in_manifest}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}

Manifest summary:
${JSON.stringify(d.manifest_summary,null,2)}

Folder checks:
${(d.folder_checks||[]).map(f=>`${f.ok?'PASS':'FAIL'} — ${f.path}`).join('\n')}

Source files:
${(d.source_files||[]).map(f=>`${f.name} — ${f.suffix} — ${f.size} bytes`).join('\n')}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported dashboard report'}

Safety:
Read-only project dashboard.
No story-file mutation.
No project creation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No move.
No install.
No model cleanup.

Please determine:
1. Whether v10.11.5 should be marked stable/proven
2. Whether the created Slipping into Darkness project is usable
3. Whether the next build should add the compact project health card to Story Forge.`;
    toast('Project Dashboard sent to Mission Console.');
}

let lastProjectAction=null;
async function loadProjectAction(execute=false,includePhrase=false){
    if(!q('projectActionStatus'))return;
    q('projectActionStatus').textContent=execute?'Requesting approved project creation...':'Loading project action preview...';
    let phrase=includePhrase?(q('projectActionPhrase')?.value||''):'';
    let d=await api('/api/writer/create_project_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',approval_phrase:phrase,execute:execute,export:true})});
    if(!d?.ok){
        q('projectActionStatus').textContent=d?.message||'Could not load project action.';
        return;
    }
    lastProjectAction=d;
    let s=d.summary||{};
    let cls=d.status==='created'?'created':(d.status==='blocked'?'blocked':(d.status==='error'?'error':''));
    q('projectActionStatus').innerHTML=`<span class="actionBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('projectActionSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=actionGrid>
      <div class=actionMetric><div class=label>Status</div><div class=value>${esc(s.status||'')}</div></div>
      <div class=actionMetric><div class=label>Allowed</div><div class=value>${s.action_allowed?'YES':'NO'}</div></div>
      <div class=actionMetric><div class=label>Phrase</div><div class=value>${s.phrase_matches?'YES':'NO'}</div></div>
      <div class=actionMetric><div class=label>Blockers</div><div class=value>${s.blockers||0}</div></div>
      <div class=actionMetric><div class=label>Dirs</div><div class=value>${s.created_dirs||0}</div></div>
      <div class=actionMetric><div class=label>Files</div><div class=value>${s.written_files||0}</div></div>
      <div class=actionMetric><div class=label>Copied</div><div class=value>${s.copied_files||0}</div></div>
      <div class=actionMetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div>
    <div class=actionPath>Project root: ${esc(s.project_root||'')}</div>
    <div class=actionPath>Manifest target: ${esc(s.manifest_target||'')}</div>
    ${d.exported?`<div class=actionPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('projectActionBlockers').innerHTML=(d.blockers||[]).length?(d.blockers||[]).map(b=>`<div class="histrow fail"><b>${esc(b.id||'blocker')}</b><div>${esc(b.message||'')}</div></div>`).join(''):'<div class="histrow ok"><b>No blockers.</b><div>Approved action may run when execute=true and phrase matches.</div></div>';
    let riskHtml=(d.overwrite_risks||[]).length?(d.overwrite_risks||[]).map(r=>`<div class="histrow fail"><b>Overwrite risk</b><div class=actionPath>${esc(r.path||'')}</div></div>`).join(''):'<div class="histrow ok"><b>No overwrite risks.</b></div>';
    q('projectActionBlockers').innerHTML+=riskHtml;
    q('projectActionPreflight').innerHTML=(d.preflight||[]).map(p=>`<div class="actionCard"><b>${esc(p.kind||'item')}</b><div>Exists: ${p.exists??p.target_exists??false} | Would overwrite: ${p.would_overwrite||false}</div><div class=actionPath>${esc(p.path||'')}</div>${p.source?`<div class=actionPath>Source: ${esc(p.source)}</div>`:''}</div>`).join('')||'No preflight.';
    let results=[];
    (d.created_dirs||[]).forEach(p=>results.push(`<div class="histrow ok"><b>Created folder</b><div class=actionPath>${esc(p)}</div></div>`));
    (d.written_files||[]).forEach(p=>results.push(`<div class="histrow ok"><b>Wrote file</b><div class=actionPath>${esc(p)}</div></div>`));
    (d.copied_files||[]).forEach(c=>results.push(`<div class="histrow ok"><b>Copied legacy source</b><div class=actionPath>${esc(c.source)} -> ${esc(c.target)}</div></div>`));
    (d.errors||[]).forEach(e=>results.push(`<div class="histrow fail"><b>Error</b><div>${esc(JSON.stringify(e))}</div></div>`));
    q('projectActionResults').innerHTML=results.join('')||'<div class="histrow info"><b>No creation executed.</b><div>This is preview/block mode unless exact phrase and execute are used.</div></div>';
    q('projectActionChecks').innerHTML=(d.post_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No post checks.';
    q('projectActionSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Project action report loaded.');
}
function sendProjectActionToMission(){
    if(!lastProjectAction){toast('Load Project Action first.');return;}
    let d=lastProjectAction, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Create Project Approved Action report.

Milestone:
${d.milestone}
Health: ${d.health_label}
Status: ${d.status}

Summary:
Project: ${s.title}
Project ID: ${s.project_id}
Execute requested: ${s.execute_requested}
Action allowed: ${s.action_allowed}
Phrase matches: ${s.phrase_matches}
Blockers: ${s.blockers}
Overwrite risks: ${s.overwrite_risks}
Preflight items: ${s.preflight_items}
Required dirs: ${s.required_dirs}
Required files: ${s.required_files}
Legacy files to copy: ${s.legacy_files_to_copy}
Created dirs: ${s.created_dirs}
Written files: ${s.written_files}
Copied files: ${s.copied_files}
Errors: ${s.errors}
Post checks: ${s.post_checks_passed}/${s.post_checks}
Project root: ${s.project_root}
Manifest target: ${s.manifest_target}

Blockers:
${(d.blockers||[]).length ? (d.blockers||[]).map(b=>`${b.id}: ${b.message}`).join('\n') : 'None.'}

Created dirs:
${(d.created_dirs||[]).join('\n')||'None.'}

Written files:
${(d.written_files||[]).join('\n')||'None.'}

Copied files:
${(d.copied_files||[]).map(c=>`${c.source} -> ${c.target}`).join('\n')||'None.'}

Post checks:
${(d.post_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Errors:
${(d.errors||[]).length ? (d.errors||[]).map(e=>JSON.stringify(e)).join('\n') : 'None.'}

Export:
${d.exported?.markdown||'No exported action report'}

Safety:
Requires exact phrase.
No action without phrase.
No overwrite.
No delete.
No move.
Legacy import copy-only.
Legacy NovelForge remains untouched.
No install.
No model cleanup.

Please determine:
1. Whether v10.11.4 should be marked stable/proven
2. Whether the project skeleton was created safely if status is created
3. Whether next build should be Story Project Reader / Dashboard.`;
    toast('Project Action sent to Mission Console.');
}

let lastProjectGate=null;
async function loadProjectGate(doExport=false){
    if(!q('projectGateStatus'))return;
    q('projectGateStatus').textContent='Loading Create Project Approval Gate...';
    let phrase=q('projectGatePhrase')?.value||'';
    let d=await api('/api/writer/create_project_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',approval_phrase:phrase,export:doExport})});
    if(!d?.ok){
        q('projectGateStatus').textContent=d?.message||'Could not load project gate.';
        return;
    }
    lastProjectGate=d;
    let s=d.summary||{};
    q('projectGateStatus').innerHTML=`<span class=gateBadge>${esc(d.health_label||'UNKNOWN')}</span>`;
    q('projectGateSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=gateGrid>
      <div class=gateMetric><div class=label>Safe Later</div><div class=value>${s.safe_to_create_later?'YES':'NO'}</div></div>
      <div class=gateMetric><div class=label>Creates Now</div><div class=value>${s.creation_enabled_in_this_build?'YES':'NO'}</div></div>
      <div class=gateMetric><div class=label>Writes</div><div class=value>${s.proposed_writes||0}</div></div>
      <div class=gateMetric><div class=label>Overwrite Risks</div><div class=value>${s.overwrite_risks||0}</div></div>
      <div class=gateMetric><div class=label>Legacy Files</div><div class=value>${s.legacy_files_detected||0}</div></div>
      <div class=gateMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=gatePath>Project root: ${esc(s.proposed_project_root||'')}</div>
    <div class=gatePath>Manifest target: ${esc(s.manifest_target||'')}</div>
    ${d.exported?`<div class=gatePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let g=d.approval_gate||{};
    q('projectGateApproval').textContent=`Required phrase:
${g.required_phrase||''}

Typed phrase present: ${g.typed_phrase_present}
Typed phrase matches: ${g.typed_phrase_matches}
Creation enabled in this build: ${g.creation_enabled_in_this_build}

Reason:
${g.reason_creation_disabled||''}

Preview required: ${g.preview_required}
Backup required before write: ${g.backup_required_before_write}
Copy, not move, for legacy sources: ${g.copy_not_move_for_legacy_sources}
No delete allowed: ${g.no_delete_allowed}
No overwrite without backup: ${g.no_overwrite_without_backup}
No automatic migration: ${g.no_automatic_migration}`;
    q('projectGateWrites').innerHTML=(d.proposed_writes||[]).map(w=>`<div class="gateCard"><b>${esc(w.id||'write')}</b><div>${esc(w.action||'')} | Kind: ${esc(w.kind||'')}</div><div>Target exists: ${w.target_exists} | Would overwrite: ${w.would_overwrite} | Executes now: ${w.will_execute_in_this_build}</div><div class=gatePath>${esc(w.target||'')}</div>${w.source?`<div class=gatePath>Source: ${esc(w.source)}</div>`:''}</div>`).join('')||'No proposed writes.';
    q('projectGateRisks').innerHTML=(d.overwrite_risks||[]).length?(d.overwrite_risks||[]).map(r=>`<div class="histrow fail"><b>Overwrite risk</b><div class=gatePath>${esc(r.target||'')}</div></div>`).join(''):'<div class="histrow ok"><b>No overwrite risks detected.</b><div>Project creation may be safe in a later approved-action build.</div></div>';
    q('projectGateLegacy').innerHTML=(d.legacy_files||[]).map(f=>`<div class="histrow info"><b>${esc(f.name||'')}</b><div>${esc(f.suffix||'')} | ${f.size||0} bytes | ${esc(f.modified||'')}</div><div class=gatePath>${esc(f.path||'')}</div></div>`).join('')||'No legacy files detected.';
    q('projectGateChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('projectGateSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Create Project Approval Gate loaded.');
}
function sendProjectGateToMission(){
    if(!lastProjectGate){toast('Load Project Gate first.');return;}
    let d=lastProjectGate, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Create Project Approval Gate.

Milestone:
${d.milestone}
Health: ${d.health_label}
Gate ready: ${d.gate_ready}
Safe to create later: ${d.safe_to_create_later}

Summary:
Project: ${s.title}
Project ID: ${s.project_id}
Creation enabled in this build: ${s.creation_enabled_in_this_build}
Required phrase: ${s.required_phrase}
Typed phrase present: ${s.typed_phrase_present}
Typed phrase matches: ${s.typed_phrase_matches}
Legacy files detected: ${s.legacy_files_detected}
Proposed writes: ${s.proposed_writes}
Required writes: ${s.required_writes}
Optional copy writes: ${s.optional_copy_writes}
Overwrite risks: ${s.overwrite_risks}
Parent missing expected: ${s.parent_missing_expected}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Proposed project root: ${s.proposed_project_root}
Manifest target: ${s.manifest_target}

Approval gate:
${JSON.stringify(d.approval_gate,null,2)}

Legacy import policy:
${JSON.stringify(d.legacy_import_policy,null,2)}

Proposed writes:
${(d.proposed_writes||[]).map(w=>`${w.id}: ${w.action}; target=${w.target}; exists=${w.target_exists}; overwrite=${w.would_overwrite}; executes_now=${w.will_execute_in_this_build}`).join('\n')}

Overwrite risks:
${(d.overwrite_risks||[]).length ? (d.overwrite_risks||[]).map(r=>r.target).join('\n') : 'None.'}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported gate report'}

Safety:
Gate preview only.
Read-only legacy scan.
No project creation.
No story-file mutation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No install.
No model cleanup.
Future writes require preview and approval.

Please determine:
1. Whether v10.11.3 should be marked stable/proven
2. Whether the next build should be Create Project Approved Action
3. Whether it is safe for the future action to create the folder skeleton only after exact phrase approval.`;
    toast('Project Gate sent to Mission Console.');
}

let lastStoryManifest=null;
async function loadStoryManifest(doExport=false){
    if(!q('storyManifestStatus'))return;
    q('storyManifestStatus').textContent='Loading Story Project Manifest Preview...';
    let d=await api('/api/writer/manifest_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',export:doExport})});
    if(!d?.ok){
        q('storyManifestStatus').textContent=d?.message||'Could not load manifest preview.';
        return;
    }
    lastStoryManifest=d;
    let s=d.summary||{};
    q('storyManifestStatus').innerHTML=`<span class=manifestBadge>${esc(d.health_label||'UNKNOWN')}</span>`;
    q('storyManifestSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=manifestGrid>
      <div class=manifestMetric><div class=label>Legacy Files</div><div class=value>${s.legacy_files_detected||0}</div></div>
      <div class=manifestMetric><div class=label>Folders</div><div class=value>${s.proposed_folders||0}</div></div>
      <div class=manifestMetric><div class=label>Writes Enabled</div><div class=value>${s.future_writes_enabled_now||0}/${s.future_writes||0}</div></div>
      <div class=manifestMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
      <div class=manifestMetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
      <div class=manifestMetric><div class=label>Ready</div><div class=value>${s.preview_ready?'YES':'NO'}</div></div>
    </div>
    <div class=manifestPath>Project root: ${esc(s.proposed_project_root||'')}</div>
    <div class=manifestPath>Manifest target: ${esc(s.manifest_target||'')}</div>
    ${d.exported?`<div class=manifestPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let mp=d.manifest_preview||{};
    q('storyManifestBody').innerHTML=`<pre>${esc(JSON.stringify(mp,null,2))}</pre>`;
    q('storyManifestLegacy').innerHTML=(d.legacy_candidates||[]).filter(f=>f.exists).map(f=>`<div class="manifestCard"><b>${esc(f.name||'')}</b><div>${esc(f.suffix||'')} | ${f.size||0} bytes | ${esc(f.modified||'')}</div><div class=manifestPath>${esc(f.path||'')}</div></div>`).join('')||'No legacy sources detected.';
    q('storyManifestFolders').innerHTML=(d.proposed_folders||[]).map(f=>`<div class="histrow info"><b>${esc(f.id||'folder')}</b><div class=manifestPath>${esc(f.path||'')}</div><div>${esc(f.purpose||'')}</div></div>`).join('')||'No proposed folders.';
    let gate=d.approval_gate||{};
    q('storyManifestWrites').innerHTML=`<div class="histrow info"><b>Approval Gate</b><div>Required phrase: ${esc(gate.required_phrase||'')}</div><div>Preview required: ${gate.preview_required} | Backup required: ${gate.backup_required_before_write} | No automatic migration: ${gate.no_automatic_migration}</div></div>`+(d.future_writes||[]).map(w=>`<div class="histrow info"><b>${esc(w.id||'write')}</b><div>Action: ${esc(w.action||'')} | Enabled now: ${w.enabled_now} | Requires approval: ${w.requires_user_approval}</div><div class=manifestPath>Target: ${esc(w.target||'')}</div></div>`).join('');
    q('storyManifestChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('storyManifestSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Story Project Manifest Preview loaded.');
}
function sendStoryManifestToMission(){
    if(!lastStoryManifest){toast('Load manifest preview first.');return;}
    let d=lastStoryManifest, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Story Project Manifest Preview.

Milestone:
${d.milestone}
Health: ${d.health_label}
Preview ready: ${d.preview_ready}

Summary:
Project: ${s.title}
Project ID: ${s.project_id}
Legacy files detected: ${s.legacy_files_detected}
Legacy JSON/Markdown/Text: ${s.legacy_json}/${s.legacy_markdown}/${s.legacy_text}
Proposed folders: ${s.proposed_folders}
Future writes enabled now: ${s.future_writes_enabled_now}/${s.future_writes}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Proposed project root: ${s.proposed_project_root}
Manifest target: ${s.manifest_target}

Proposed manifest:
${JSON.stringify(d.manifest_preview,null,2)}

Legacy sources:
${(d.legacy_candidates||[]).filter(f=>f.exists).map(f=>`${f.suffix} — ${f.path} — ${f.size} bytes`).join('\n')}

Proposed folders:
${(d.proposed_folders||[]).map(f=>`${f.id}: ${f.path} — ${f.purpose}`).join('\n')}

Future writes:
${(d.future_writes||[]).map(w=>`${w.id}: enabled_now=${w.enabled_now}; action=${w.action}; target=${w.target}; approval=${w.requires_user_approval}`).join('\n')}

Approval gate:
${JSON.stringify(d.approval_gate,null,2)}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported manifest preview report'}

Safety:
Preview only.
Read-only legacy scan.
No project creation.
No story-file mutation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No install.
No model cleanup.
Future writes require preview and approval.

Please determine:
1. Whether v10.11.2 should be marked stable/proven
2. Whether the next build should be Create Project Approval Gate
3. Whether the proposed manifest/folder structure is safe.`;
    toast('Story manifest preview sent to Mission Console.');
}

let lastStoryForge=null;
async function loadStoryForge(doExport=false){
    if(!q('storyForgeStatus'))return;
    q('storyForgeStatus').textContent='Loading Story Forge shell...';
    let d=await api('/api/writer/story_forge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:doExport,limit:80})});
    if(!d?.ok){
        q('storyForgeStatus').textContent=d?.message||'Could not load Story Forge shell.';
        return;
    }
    lastStoryForge=d;
    let s=d.summary||{};
    q('storyForgeStatus').innerHTML=`<span class=storyBadge>${esc(d.health_label||'UNKNOWN')}</span>`;
    q('storyForgeSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=storyGrid>
      <div class=storyMetric><div class=label>Sections</div><div class=value>${s.sections||0}</div></div>
      <div class=storyMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
      <div class=storyMetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
      <div class=storyMetric><div class=label>Project Roots</div><div class=value>${s.existing_project_roots||0}/${s.project_roots_checked||0}</div></div>
      <div class=storyMetric><div class=label>Future Actions</div><div class=value>${s.future_actions_available_now||0}/${s.future_actions||0}</div></div>
      <div class=storyMetric><div class=label>Ready</div><div class=value>${s.foundation_ready?'YES':'NO'}</div></div>
    </div>
    <div class=storyPath>Flagship universe: ${esc(s.flagship_universe||'')}</div>
    <div class=storyPath>Legacy NovelForge exists: ${s.legacy_novel_forge_exists}</div>
    ${d.exported?`<div class=storyPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let f=d.flagship||{};
    q('storyForgeFlagship').textContent=`${f.title||''}
Status: ${f.status||''}

Book 1:
${f.book_1||''}

Book 2:
${f.book_2||''}

Story Forge use:
${(f.story_forge_use||[]).join('\\n')}`;
    q('storyForgeProjects').innerHTML=(d.project_candidates||[]).map(p=>`<div class="storyCard"><b>${esc(p.title||'')}</b><div>Role: ${esc(p.role||'')} | Exists: ${p.exists} | Kind: ${esc(p.kind||'')}</div><div class=storyPath>${esc(p.path||'')}</div><div>Files: ${p.counts?.total||0} | MD: ${p.counts?.markdown||0} | JSON: ${p.counts?.json||0} | TXT: ${p.counts?.text||0}</div>${(p.children||[]).length?`<div class=storyPath>Children: ${(p.children||[]).map(c=>esc(c.name)+' ('+(c.counts?.total||0)+' files)').join(', ')}</div>`:''}</div>`).join('')||'No project candidates.';
    q('storyForgeSections').innerHTML=(d.shell_sections||[]).map(x=>`<div class="histrow info"><b>${esc(x.title||'')}</b><div>ID: ${esc(x.id||'')} | Status: ${esc(x.status||'')}</div><div>${esc(x.purpose||'')}</div></div>`).join('')||'No sections.';
    q('storyForgeActions').innerHTML=(d.future_actions||[]).map(a=>`<div class="histrow info"><b>${esc(a.title||'')}</b><div>ID: ${esc(a.id||'')} | Available now: ${a.available_now} | Requires approval: ${a.requires_user_approval}</div><div class=storyPath>Writes: ${esc(a.writes||'')}</div></div>`).join('')||'No future actions.';
    q('storyForgeChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('storyForgeSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Story Forge shell loaded.');
}
function sendStoryForgeToMission(){
    if(!lastStoryForge){toast('Load Story Forge first.');return;}
    let d=lastStoryForge, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Story Forge Shell report.

Milestone:
${d.milestone}
Health: ${d.health_label}
Shell ready: ${d.shell_ready}

Summary:
Sections: ${s.sections}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Project roots checked: ${s.project_roots_checked}
Existing project roots: ${s.existing_project_roots}
Legacy NovelForge exists: ${s.legacy_novel_forge_exists}
Future actions available now: ${s.future_actions_available_now}/${s.future_actions}
Flagship universe: ${s.flagship_universe}

Flagship:
${d.flagship?.title}
Book 1: ${d.flagship?.book_1}
Book 2: ${d.flagship?.book_2}

Project candidates:
${(d.project_candidates||[]).map(p=>`${p.id}: ${p.path} — exists=${p.exists} — files=${p.counts?.total||0}`).join('\n')}

Shell sections:
${(d.shell_sections||[]).map(x=>`${x.id}: ${x.status} — ${x.purpose}`).join('\n')}

Future actions:
${(d.future_actions||[]).map(a=>`${a.id}: available_now=${a.available_now}; requires approval=${a.requires_user_approval}; writes=${a.writes}`).join('\n')}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Story Forge shell report'}

Safety:
Read-only Story Forge shell.
No story-file mutation.
No project creation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No install.
No model cleanup.
Future writes require preview and approval.

Please determine:
1. Whether v10.11.1 should be marked stable/proven
2. Whether Story Project Manifest Preview should be the next build
3. Whether legacy NovelForge should remain read-only until an approved migration tool exists.`;
    toast('Story Forge sent to Mission Console.');
}

let lastKayockWriter=null;
async function loadKayockWriter(doExport=false){
    if(!q('kayockWriterStatus'))return;
    q('kayockWriterStatus').textContent='Loading Kayock Writer foundation...';
    let d=await api('/api/writer/foundation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:doExport})});
    if(!d?.ok){q('kayockWriterStatus').textContent=d?.message||'Could not load Kayock Writer foundation.';return;}
    lastKayockWriter=d; let s=d.summary||{};
    q('kayockWriterStatus').innerHTML=`<span class=writerBadge>${esc(d.health_label||'UNKNOWN')}</span>`;
    q('kayockWriterSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=writerGrid><div class=writerMetric><div class=label>Modules</div><div class=value>${s.modules||0}</div></div><div class=writerMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div><div class=writerMetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div><div class=writerMetric><div class=label>Paths</div><div class=value>${s.existing_paths||0}/${s.path_checks||0}</div></div><div class=writerMetric><div class=label>Decisions</div><div class=value>${s.naming_decisions||0}</div></div><div class=writerMetric><div class=label>Ready</div><div class=value>${s.foundation_ready?'YES':'NO'}</div></div></div><div class=writerPath>Flagship universe: ${esc(s.flagship_universe||'')}</div><div class=writerPath>Read only: ${s.read_only} • Report only: ${s.report_only}</div>${d.exported?`<div class=writerPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('kayockWriterModules').innerHTML=(d.module_plan||[]).map(m=>`<div class=writerModule><b>${esc(m.name||'')}</b><div>ID: ${esc(m.id||'')} | Status: ${esc(m.status||'')}</div><div>${esc(m.purpose||'')}</div><div class=writerPath>Future writes: ${esc(m.future_writes||'')}</div></div>`).join('')||'No modules.';
    q('kayockWriterNames').innerHTML=(d.naming_decisions||[]).map(n=>`<div class="histrow ok"><b>${esc(n.decision||'')}</b><div>ID: ${esc(n.id||'')} | Status: ${esc(n.status||'')}</div><div>${esc(n.notes||'')}</div></div>`).join('')||'No naming decisions.';
    let f=d.flagship_universe||{}; q('kayockWriterFlagship').textContent=`${f.title||''}\nStatus: ${f.status||''}\n\nBook 1:\n${f.book_1||''}\n\nBook 2:\n${f.book_2||''}\n\nUse:\n${f.use||''}`;
    q('kayockWriterPaths').innerHTML=(d.path_checks||[]).map(p=>`<div class="histrow ${p.exists?'ok':'info'}"><b>${esc(p.key||'path')}</b><div class=writerPath>${esc(p.path||'')}</div><div>Exists: ${p.exists} | Kind: ${esc(p.kind||'')} | Modified: ${esc(p.modified||'')}</div></div>`).join('')||'No path checks.';
    q('kayockWriterRecommendations').innerHTML=(d.recommendations||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b><div>ID: ${esc(r.id||'')} | Risk: ${esc(r.risk||'')} | Auto apply: ${r.auto_apply}</div><div>${esc(r.recommendation||'')}</div></div>`).join('')||'No recommendations.';
    q('kayockWriterSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Kayock Writer foundation loaded.');
}
function sendKayockWriterToMission(){
    if(!lastKayockWriter){toast('Load Kayock Writer foundation first.');return;}
    let d=lastKayockWriter; let s=d.summary||{}; go('mission');
    q('input').value=`Please review this Kayock Writer Foundation report.\n\nMilestone:\n${d.milestone}\n\nHealth:\n${d.health_label}\n\nSummary:\nModules: ${s.modules}\nChecks passed: ${s.checks_passed}/${s.checks}\nProblems: ${s.problems}\nNaming decisions: ${s.naming_decisions}\nExisting paths: ${s.existing_paths}/${s.path_checks}\nFlagship universe: ${s.flagship_universe}\nFoundation ready: ${s.foundation_ready}\nRead only: ${s.read_only}\nReport only: ${s.report_only}\n\nModule plan:\n${(d.module_plan||[]).map(m=>`${m.id} — ${m.name}: ${m.purpose}`).join('\n')}\n\nNaming decisions:\n${(d.naming_decisions||[]).map(n=>`${n.id}: ${n.status} — ${n.decision}`).join('\n')}\n\nFlagship universe:\n${d.flagship_universe?.title}\nBook 1: ${d.flagship_universe?.book_1}\nBook 2: ${d.flagship_universe?.book_2}\n\nPath checks:\n${(d.path_checks||[]).map(p=>`${p.key}: ${p.path} — exists=${p.exists} — kind=${p.kind}`).join('\n')}\n\nRecommendations:\n${(d.recommendations||[]).map(r=>`${r.id}: ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}\n\nExport:\n${d.exported?.markdown||'No exported Kayock Writer foundation report'}\n\nSafety:\nRead-only Kayock Writer foundation report.\nNo story-file mutation.\nNo rename performed.\nNo migration performed.\nNo overwrite.\nNo delete.\nNo install.\nNo model cleanup.\nFuture writes require explicit user approval.\n\nPlease determine:\n1. Whether v10.11.0 should be marked stable/proven\n2. Whether Kayock Writer should replace Novel Forge as the public department name\n3. Whether Story Forge should be the next build\n4. Whether Poetry Studio should follow after Story Forge.`;
    toast('Kayock Writer foundation sent to Mission Console.');
}

let lastCommandFreeze=null;
async function loadCommandFreeze(doExport=false){
    if(!q('commandFreezeStatus'))return;
    q('commandFreezeStatus').textContent='Loading Command Center milestone freeze...';
    let d=await api('/api/command_center/milestone_freeze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('commandFreezeStatus').textContent=d?.message||'Could not load Command Center milestone freeze.';
        return;
    }
    lastCommandFreeze=d;
    let s=d.summary||{};
    let cls=d.freeze_ready?(s.advisory?'advisory':'clear'):'bad';
    q('commandFreezeStatus').innerHTML=`<span class="cmdFreezeBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('commandFreezeSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b> • ${esc(d.version_range||'')}</div>
    <div class=cmdFreezeGrid>
      <div class=cmdFreezeMetric><div class=label>Modules Proven</div><div class=value>${s.modules_complete_proven||0}/${s.modules||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Score</div><div class=value>${s.score||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Foundations</div><div class=value>${s.foundations||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Clear</div><div class=value>${s.clear||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Advisory</div><div class=value>${s.advisory||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Attention</div><div class=value>${s.needs_attention||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Archive Reports</div><div class=value>${s.archive_reports||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Archive Errors</div><div class=value>${s.archive_errors||0}</div></div>
    </div>
    <div class=cmdFreezePath>Command Center: ${esc(s.command_center_health||'')}</div>
    <div class=cmdFreezePath>Dashboard card: ${esc(s.dashboard_card_health||'')}</div>
    <div class=cmdFreezePath>Archive: ${esc(s.archive_health||'')}</div>
    <div class=cmdFreezePath>Repair Shop: ${esc(s.repair_shop_foundation||'')} • Recovery: ${esc(s.recovery_foundation||'')}</div>
    <div class=cmdFreezePath>Latest repair action: ${esc(s.latest_repair_action||'none')} • Latest recovery: ${esc(s.latest_recovery_event||'none')}</div>
    ${d.exported?`<div class=cmdFreezePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('commandFreezeModules').innerHTML=(d.modules||[]).map(m=>`<div class="histrow ${m.status==='complete_proven'?'ok':'fail'}"><b>${esc(m.version||'')} — ${esc(m.name||'')}</b>${verifyBadge(m.status==='complete_proven'?'passed':'failed')}
<div>Status: ${esc(m.status||'')} | Health: ${esc(m.health||'')}</div>
<div>${esc(m.proof||'')}</div>
<div class=vaultpath>Page: ${esc(m.page||'')} | Endpoint: ${esc(m.endpoint||'')}</div></div>`).join('')||'No modules.';
    q('commandFreezeAdvisories').innerHTML=(d.advisories||[]).map(a=>`<div class="histrow info"><b>${esc(a.title||'')}</b><div>ID: ${esc(a.id||'')}</div><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')} | Safe to ignore: ${a.safe_to_ignore}</div></div>`).join('')||'<div class="histrow ok"><b>No advisories.</b><div>All Command Center foundations are fully clear.</div></div>';
    q('commandFreezeRecommendations').innerHTML=(d.recommendations||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b><div>ID: ${esc(r.id||'')} | Status: ${esc(r.status||'')} | Risk: ${esc(r.risk||'')} | Auto apply: ${r.auto_apply}</div><div>${esc(r.recommendation||'')}</div></div>`).join('')||'No recommendations.';
    q('commandFreezeProblems').innerHTML=(d.problems||[]).map(p=>`<div class="histrow fail"><b>${esc(p.source||'review')}</b><div>${esc(p.message||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No problems.</b><div>Command Center milestone is ready to freeze.</div></div>';
    q('commandFreezeSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Command Center milestone freeze loaded.');
}
function sendCommandFreezeToMission(){
    if(!lastCommandFreeze){
        toast('Load Command Center freeze first.');
        return;
    }
    let d=lastCommandFreeze;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Command Center Milestone Freeze.

Milestone:
${d.milestone}
Version range: ${d.version_range}
Health: ${d.health_label}
Freeze ready: ${d.freeze_ready}

Summary:
Modules proven: ${s.modules_complete_proven}/${s.modules}
Modules need review: ${s.modules_need_review}
Command Center health: ${s.command_center_health}
Dashboard card health: ${s.dashboard_card_health}
Archive health: ${s.archive_health}
Score: ${s.score}
Foundations: ${s.foundations}
Clear/advisory/attention: ${s.clear}/${s.advisory}/${s.needs_attention}
Command ready: ${s.command_ready}
Archive reports: ${s.archive_reports}
Archive errors: ${s.archive_errors}
Trend attention reports: ${s.trend_attention_reports}
Repair Shop Foundation: ${s.repair_shop_foundation}
Recovery Foundation: ${s.recovery_foundation}
Latest repair action: ${s.latest_repair_action}
Latest recovery event: ${s.latest_recovery_event}

Modules:
${(d.modules||[]).map(m=>`${m.version} — ${m.name} — ${m.status} — ${m.proof}`).join('\n')}

Advisories:
${(d.advisories||[]).length ? (d.advisories||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Problems:
${(d.problems||[]).length ? (d.problems||[]).map(p=>`${p.source}: ${p.message}`).join('\n') : 'None.'}

Recommendations:
${(d.recommendations||[]).map(r=>`${r.id}: ${r.status} — ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Command Center freeze report'}

Safety:
Scan first. Report second. Ask before action.
Read-only milestone freeze report.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether v10.10.x Command Center Foundation should be frozen
2. Whether advisories are safe to carry as optional maintenance
3. Whether v10.10.4 should be marked stable/proven
4. What the next foundation milestone should be.`;
    toast('Command Center freeze sent to Mission Console.');
}

let lastCommandArchive=null;
async function loadCommandArchive(doExport=false){
    if(!q('commandArchiveStatus'))return;
    q('commandArchiveStatus').textContent='Loading Command Center archive...';
    let d=await api('/api/command_center/archive',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:200,export:doExport})});
    if(!d?.ok){
        q('commandArchiveStatus').textContent=d?.message||'Could not load Command Center archive.';
        return;
    }
    lastCommandArchive=d;
    let s=d.summary||{};
    let cls=s.latest_needs_attention?'bad':(s.latest_advisory?'advisory':'clear');
    q('commandArchiveStatus').innerHTML=`<span class="archiveBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('commandArchiveSummary').innerHTML=`<div class=archiveGrid>
      <div class=archiveMetric><div class=label>Reports</div><div class=value>${s.reports||0}</div></div>
      <div class=archiveMetric><div class=label>Foundation</div><div class=value>${s.foundation_reports||0}</div></div>
      <div class=archiveMetric><div class=label>Cards</div><div class=value>${s.dashboard_card_reports||0}</div></div>
      <div class=archiveMetric><div class=label>Details</div><div class=value>${s.detail_reports||0}</div></div>
      <div class=archiveMetric><div class=label>Latest Score</div><div class=value>${s.latest_score||0}</div></div>
      <div class=archiveMetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div>
    <div class=archivePath>Latest foundation: ${esc(s.latest_foundation_report||'none')} — ${esc(s.latest_foundation_health||'')}</div>
    <div class=archivePath>Latest dashboard: ${esc(s.latest_dashboard_report||'none')} — ${esc(s.latest_dashboard_health||'')}</div>
    <div class=archivePath>Latest detail: ${esc(s.latest_detail_report||'none')} — ${esc(s.latest_detail_foundation||'')}</div>
    <div class=archivePath>Latest repair action: ${esc(s.latest_repair_action||'none')} • Latest recovery: ${esc(s.latest_recovery_event||'none')}</div>
    ${d.exported?`<div class=archivePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('commandArchiveTrend').innerHTML=(d.trend||[]).slice().reverse().map(t=>`<div class="histrow ${t.needs_attention?'fail':(t.advisory?'info':'ok')}"><b>${esc(t.created||'')}</b><div>${esc(t.type||'')} — ${esc(t.health_label||'')}</div><div>Score: ${t.score||0} | Clear/advisory/attention: ${t.clear||0}/${t.advisory||0}/${t.needs_attention||0} | Ready: ${t.command_ready}</div></div>`).join('')||'No trend data yet.';
    q('commandArchiveTimeline').innerHTML=(d.timeline||[]).slice(0,80).map(t=>`<div class="histrow info"><b>${esc(t.created||'')} — ${esc(t.type||'')}</b><div>${esc(t.name||'')}</div><div>${esc(t.health_label||'')} ${t.foundation_id?('• '+esc(t.foundation_id)+' '+esc(t.foundation_status||'')):''}</div><div class=vaultpath>${esc(t.path||'')}</div></div>`).join('')||'No archived reports yet.';
    let latest=[];
    if(d.latest_foundation?.name)latest.push(`<div class="histrow ok"><b>Latest Foundation Report</b><div>${esc(d.latest_foundation.name)} — ${esc(d.latest_foundation.health_label||'')}</div><div class=vaultpath>${esc(d.latest_foundation.path||'')}</div></div>`);
    if(d.latest_dashboard?.name)latest.push(`<div class="histrow ok"><b>Latest Dashboard Card Report</b><div>${esc(d.latest_dashboard.name)} — ${esc(d.latest_dashboard.health_label||'')}</div><div class=vaultpath>${esc(d.latest_dashboard.path||'')}</div></div>`);
    if(d.latest_detail?.name)latest.push(`<div class="histrow ok"><b>Latest Detail Report</b><div>${esc(d.latest_detail.name)} — ${esc(d.latest_detail.foundation_id||'')}</div><div class=vaultpath>${esc(d.latest_detail.path||'')}</div></div>`);
    (d.errors||[]).forEach(e=>latest.push(`<div class="histrow fail"><b>Archive Error</b><div>${esc(JSON.stringify(e))}</div></div>`));
    q('commandArchiveLatest').innerHTML=latest.join('')||'No latest report data.';
    q('commandArchiveSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Command Center archive loaded.');
}
function sendCommandArchiveToMission(){
    if(!lastCommandArchive){
        toast('Load Command Center archive first.');
        return;
    }
    let d=lastCommandArchive;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Command Center History / Archive report.

Health:
${d.health_label}

Summary:
Reports: ${s.reports}
Foundation reports: ${s.foundation_reports}
Dashboard card reports: ${s.dashboard_card_reports}
Detail reports: ${s.detail_reports}
Errors: ${s.errors}
Latest score: ${s.latest_score}
Latest clear/advisory/attention: ${s.latest_clear}/${s.latest_advisory}/${s.latest_needs_attention}
Latest command ready: ${s.latest_command_ready}
Trend clear reports: ${s.trend_clear_reports}
Trend advisory reports: ${s.trend_advisory_reports}
Trend attention reports: ${s.trend_attention_reports}
Latest repair action: ${s.latest_repair_action}
Latest recovery event: ${s.latest_recovery_event}

Trend:
${(d.trend||[]).map(t=>`${t.created} — ${t.type} — ${t.health_label} — score=${t.score} — clear/advisory/attention=${t.clear}/${t.advisory}/${t.needs_attention}`).join('\n')}

Timeline:
${(d.timeline||[]).slice(0,30).map(t=>`${t.created} — ${t.type} — ${t.name} — ${t.health_label} — ${t.path}`).join('\n')}

Errors:
${(d.errors||[]).length ? (d.errors||[]).map(e=>JSON.stringify(e)).join('\n') : 'None.'}

Export:
${d.exported?.markdown||'No exported archive report'}

Safety:
Read-only archive viewer.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the Command Center archive is healthy
2. Whether v10.10.3 should be marked stable/proven
3. Whether the next build should freeze the Command Center milestone.`;
    toast('Command Center archive sent to Mission Console.');
}

let lastCommandCenterDashboard=null;
async function loadCommandCenterDashboard(doExport=false){
    if(!q('commandCenterDashStatus'))return;
    q('commandCenterDashStatus').textContent='Loading Command Center dashboard card...';
    let d=await api('/api/command_center/dashboard_card',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('commandCenterDashStatus').textContent=d?.message||'Could not load Command Center dashboard card.';
        return;
    }
    lastCommandCenterDashboard=d;
    let cls=d.card_state==='clear'?'clear':(d.card_state==='advisory'?'advisory':'bad');
    q('commandCenterDashStatus').innerHTML=`<span class="ccDashBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('commandCenterDashBody').innerHTML=`<div class=ccDashGrid>
      <div class=ccDashMetric><div class=label>Score</div><div class=value>${d.score||0}</div></div>
      <div class=ccDashMetric><div class=label>Foundations</div><div class=value>${d.foundations_total||0}</div></div>
      <div class=ccDashMetric><div class=label>Clear</div><div class=value>${d.foundations_clear||0}</div></div>
      <div class=ccDashMetric><div class=label>Advisory</div><div class=value>${d.foundations_advisory||0}</div></div>
      <div class=ccDashMetric><div class=label>Attention</div><div class=value>${d.foundations_needs_attention||0}</div></div>
      <div class=ccDashMetric><div class=label>Ready</div><div class=value>${d.command_ready?'YES':'NO'}</div></div>
    </div>
    <div class=ccDashLine>Repair Shop: ${esc(d.repair_shop_foundation||'')}</div>
    <div class=ccDashLine>Recovery: ${esc(d.recovery_foundation||'')}</div>
    <div class=ccDashLine>Latest repair action: ${esc(d.latest_repair_action||'none')}</div>
    <div class=ccDashLine>Latest recovery event: ${esc(d.latest_recovery_event||'none')}</div>
    ${d.primary_advisory?.title?`<div class=ccDashLine>Advisory: ${esc(d.primary_advisory.title)} — ${esc(d.primary_advisory.summary||'')}</div>`:''}
    ${d.primary_attention?.title?`<div class=ccDashLine>Attention: ${esc(d.primary_attention.title)} — ${esc(d.primary_attention.summary||'')}</div>`:''}
    ${d.exported?`<div class=ccDashLine>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    toast('Command Center dashboard card loaded.');
}
function sendCommandCenterDashboardToMission(){
    if(!lastCommandCenterDashboard){
        toast('Refresh Command Center dashboard first.');
        return;
    }
    let d=lastCommandCenterDashboard;
    go('mission');
    q('input').value=`Please review this Kayock Command Center Dashboard Card.

Health:
${d.health_label}

Command ready: ${d.command_ready}
Fully clear: ${d.fully_clear}
Score: ${d.score}

Foundations:
Total: ${d.foundations_total}
Clear: ${d.foundations_clear}
Advisory: ${d.foundations_advisory}
Needs attention: ${d.foundations_needs_attention}

Repair Shop Foundation:
${d.repair_shop_foundation}

Recovery Foundation:
${d.recovery_foundation}

Latest repair action:
${d.latest_repair_action}

Latest recovery event:
${d.latest_recovery_event}

Advisories:
${(d.advisories||[]).length ? (d.advisories||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Attention:
${(d.attention||[]).length ? (d.attention||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Foundation list:
${(d.foundations||[]).map(f=>`${f.status} — ${f.title}: ${f.summary}`).join('\n')}

Recommendations:
${(d.recommendations||[]).map(r=>`${r.id}: ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}

Export:
${d.exported?.markdown||'No exported dashboard card report'}

Safety:
Read-only dashboard card.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this dashboard card reflects Command Center correctly
2. Whether v10.10.2 should be marked stable/proven
3. Whether the next build should add a Command Center history/archive view.`;
    toast('Command Center dashboard sent to Mission Console.');
}

let lastCommandDetail=null;
async function loadCommandDetailList(){
    let sel=q('commandDetailSelect');
    if(!sel)return;
    q('commandDetailStatus').textContent='Loading foundation list...';
    let d=await api('/api/command_center/foundation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300})});
    if(!d?.ok){
        q('commandDetailStatus').textContent=d?.message||'Could not load Command Center foundations.';
        return;
    }
    sel.innerHTML=(d.foundations||[]).map(f=>`<option value="${esc(f.id||'')}">${esc(f.id||'')} — ${esc(f.status||'')} — ${esc(f.title||'')}</option>`).join('');
    q('commandDetailStatus').textContent=`Foundation list loaded: ${(d.foundations||[]).length}`;
    toast('Foundation list loaded.');
}
async function loadCommandDetail(doExport=false){
    let sel=q('commandDetailSelect');
    let id=sel?.value||'env_verify';
    q('commandDetailStatus').textContent='Loading foundation detail...';
    let d=await api('/api/command_center/detail',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({foundation_id:id,limit:300,export:doExport})});
    if(!d?.ok){
        q('commandDetailStatus').textContent=d?.message||'Could not load foundation detail.';
        return;
    }
    lastCommandDetail=d;
    q('commandDetailStatus').textContent=`Detail loaded.
Foundation: ${d.foundation_title}
Status: ${d.foundation_status}
Health: ${d.foundation_health}
Detail OK: ${d.detail_ok}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    let cls=d.foundation_status==='clear'?'clear':(d.foundation_status==='advisory'?'advisory':'bad');
    q('commandDetailSummary').innerHTML=`<span class="cmdDetailBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>
<div><b>${esc(d.foundation_title||'')}</b> <span class=muted>(${esc(d.foundation_id||'')})</span></div>
<div>Status: ${esc(d.foundation_status||'')} | Health: ${esc(d.foundation_health||'')}</div>
<div>${esc(d.foundation_summary||'')}</div>
<div class=cmdPath>Source: ${esc(d.foundation_source||'')}</div>
<div class=cmdPath>Page: ${esc(d.foundation_page||'')} | Endpoint: ${esc(d.foundation_endpoint||'')}</div>
<div class=cmdPath>Recommended action: ${esc(d.recommended_action||'')}</div>`;
    q('commandDetailMetrics').innerHTML=Object.entries(d.metrics||{}).map(([k,v])=>`<div class=cmdMetric><div class=k>${esc(k)}</div><div class=v>${esc(typeof v==='object'?JSON.stringify(v):String(v))}</div></div>`).join('')||'No metrics.';
    let sig=[];
    (d.matching_attention||[]).forEach(a=>sig.push(`<div class="histrow fail"><b>Attention</b><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')}</div></div>`));
    (d.matching_advisory||[]).forEach(a=>sig.push(`<div class="histrow info"><b>Advisory</b><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')}</div></div>`));
    (d.recommended_next||[]).forEach(r=>sig.push(`<div class="histrow info"><b>${esc(r.title||'')}</b><div>${esc(r.recommendation||'')}</div><div class=vaultpath>Risk: ${esc(r.risk||'')} | Auto apply: ${r.auto_apply}</div></div>`));
    q('commandDetailSignal').innerHTML=sig.join('')||'<div class="histrow ok"><b>No advisory or attention.</b><div>This foundation is clear.</div></div>';
    q('commandDetailPaths').innerHTML=(d.related_paths||[]).map(p=>`<div class="histrow ${p.exists===false?'fail':'ok'}"><b>${esc(p.key||'path')}</b><div class=vaultpath>${esc(p.path||'')}</div><div>Kind: ${esc(p.kind||'')} | Exists: ${p.exists===undefined?'n/a':p.exists} | Size: ${p.size??''} | Modified: ${esc(p.modified||'')}</div></div>`).join('')||'No related paths.';
    q('commandDetailChecks').innerHTML=(d.detail_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No checks.';
    let sc=d.safety||{};
    q('commandDetailSafety').textContent=Object.entries(sc).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Foundation detail loaded.');
}
function openCommandDetailRelatedPage(){
    if(!lastCommandDetail){
        toast('Load foundation detail first.');
        return;
    }
    if(lastCommandDetail.foundation_page){
        go(lastCommandDetail.foundation_page);
    }else{
        toast('No related page declared.');
    }
}
function sendCommandDetailToMission(){
    if(!lastCommandDetail){
        toast('Load foundation detail first.');
        return;
    }
    let d=lastCommandDetail;
    go('mission');
    q('input').value=`Please review this Kayock Command Center foundation detail.

Foundation:
${d.foundation_title}
ID: ${d.foundation_id}
Status: ${d.foundation_status}
Health: ${d.foundation_health}
Detail OK: ${d.detail_ok}

Summary:
${d.foundation_summary}

Source:
${d.foundation_source}
Page: ${d.foundation_page}
Endpoint: ${d.foundation_endpoint}

Recommended action:
${d.recommended_action}

Metrics:
${Object.entries(d.metrics||{}).map(([k,v])=>`${k}: ${typeof v==='object'?JSON.stringify(v):v}`).join('\n')}

Attention:
${(d.matching_attention||[]).length ? (d.matching_attention||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Advisory:
${(d.matching_advisory||[]).length ? (d.matching_advisory||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Recommended next:
${(d.recommended_next||[]).map(r=>`${r.id}: ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}

Detail checks:
${(d.detail_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Related paths:
${(d.related_paths||[]).map(p=>`${p.key}: ${p.path} — exists=${p.exists}`).join('\n')}

Export:
${d.exported?.markdown||'No exported detail report'}

Safety:
Read-only foundation detail.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this foundation is clear, advisory, or needs attention
2. Whether the recommendation is safe
3. Whether v10.10.1 should be marked stable/proven.`;
    toast('Command Center detail sent to Mission Console.');
}

let lastCommandCenter=null;
async function loadCommandCenter(doExport=false){
    if(!q('commandCenterStatus'))return;
    q('commandCenterStatus').textContent='Loading Command Center foundation report...';
    let d=await api('/api/command_center/foundation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('commandCenterStatus').textContent=d?.message||'Could not load Command Center.';
        return;
    }
    lastCommandCenter=d;
    let s=d.summary||{};
    q('commandCenterStatus').textContent=`Command Center loaded.
Health: ${d.health_label}
Command ready: ${d.command_ready}
Foundations: ${s.foundations}
Clear/advisory/attention: ${s.clear}/${s.advisory}/${s.needs_attention}
Score: ${s.score}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    let badgeClass=d.fully_clear?'clear':(d.command_ready?'advisory':'bad');
    q('commandCenterSummary').innerHTML=`<span class="ccBadge ${badgeClass}">${esc(d.health_label||'UNKNOWN')}</span>
<div><b>${esc(d.milestone||'')}</b></div>
<div class=ccGrid>
  <div class=ccMetric><div class=label>Score</div><div class=value>${s.score||0}</div></div>
  <div class=ccMetric><div class=label>Foundations</div><div class=value>${s.foundations||0}</div></div>
  <div class=ccMetric><div class=label>Clear</div><div class=value>${s.clear||0}</div></div>
  <div class=ccMetric><div class=label>Advisory</div><div class=value>${s.advisory||0}</div></div>
  <div class=ccMetric><div class=label>Attention</div><div class=value>${s.needs_attention||0}</div></div>
  <div class=ccMetric><div class=label>Portable</div><div class=value>${s.portable_score||0}</div></div>
  <div class=ccMetric><div class=label>Env Optional</div><div class=value>${s.env_optional_missing||0}</div></div>
  <div class=ccMetric><div class=label>Model Dupes</div><div class=value>${s.true_model_duplicate_groups||0}</div></div>
</div>
<div class=ccPath>Repair Shop: ${esc(s.repair_shop_foundation||'')}</div>
<div class=ccPath>Recovery: ${esc(s.recovery_foundation||'')} • Latest: ${esc(s.latest_recovery_event||'')}</div>
<div class=ccPath>Latest repair action: ${esc(s.latest_repair_action||'none')}</div>`;
    q('commandCenterFoundations').innerHTML=(d.foundations||[]).map(f=>{
        let cls=f.status==='clear'?'clear':(f.status==='advisory'?'advisory':'needs_attention');
        let badge=f.status==='clear'?'passed':(f.status==='advisory'?'not_recorded':'failed');
        return `<div class="foundationCard ${cls}"><b>${esc(f.title||'')}</b>${verifyBadge(badge)}
<div>Status: ${esc(f.status||'')} | Health: ${esc(f.health||'')}</div>
<div>${esc(f.summary||'')}</div>
<div class=vaultpath>Source: ${esc(f.source||'')} | Page: ${esc(f.page||'')} | Endpoint: ${esc(f.endpoint||'')}</div>
<div class=vaultpath>Recommended: ${esc(f.recommended_action||'')}</div></div>`;
    }).join('')||'No foundations loaded.';
    q('commandCenterAttention').innerHTML=(d.attention||[]).map(a=>`<div class="histrow fail"><b>${esc(a.title||'')}</b><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No attention items.</b><div>Command Center has no failing foundations.</div></div>';
    q('commandCenterAdvisories').innerHTML=(d.advisories||[]).map(a=>`<div class="histrow info"><b>${esc(a.title||'')}</b><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No advisories.</b><div>All foundations are fully clear.</div></div>';
    q('commandCenterNext').innerHTML=(d.recommendations||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b><div>ID: ${esc(r.id||'')} | Risk: ${esc(r.risk||'')} | Auto apply: ${r.auto_apply}</div><div>${esc(r.recommendation||'')}</div></div>`).join('')||'No recommendations.';
    let sc=d.safety_contract||{};
    q('commandCenterSafety').textContent=Object.entries(sc).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Command Center loaded.');
}
function sendCommandCenterToMission(){
    if(!lastCommandCenter){
        toast('Load Command Center first.');
        return;
    }
    let d=lastCommandCenter;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Command Center Foundation report.

Milestone:
${d.milestone}

Health:
${d.health_label}

Command ready: ${d.command_ready}
Fully clear: ${d.fully_clear}
Score: ${s.score}

Summary:
Foundations: ${s.foundations}
Clear: ${s.clear}
Advisory: ${s.advisory}
Needs attention: ${s.needs_attention}
Repair Shop Foundation: ${s.repair_shop_foundation}
Recovery Foundation: ${s.recovery_foundation}
Build Verify problems: ${s.build_verify_problems}
Env required problems: ${s.env_required_problems}
Env optional missing: ${s.env_optional_missing}
Portable score: ${s.portable_score}
Portable blockers/warnings: ${s.portable_blockers}/${s.portable_warnings}
True model duplicate groups: ${s.true_model_duplicate_groups}
Scan Bridge status: ${s.scan_bridge_status}
Project Docs problems: ${s.project_docs_problems}
Extension problems: ${s.extension_problems}
Latest repair action: ${s.latest_repair_action}
Latest recovery event: ${s.latest_recovery_event}

Foundations:
${(d.foundations||[]).map(f=>`${f.status} — ${f.title}: ${f.summary} — recommended=${f.recommended_action}`).join('\n')}

Attention:
${(d.attention||[]).length ? (d.attention||[]).map(a=>`${a.id}: ${a.summary}`).join('\n') : 'None.'}

Advisories:
${(d.advisories||[]).length ? (d.advisories||[]).map(a=>`${a.id}: ${a.summary}`).join('\n') : 'None.'}

Recommendations:
${(d.recommendations||[]).map(r=>`${r.id}: ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Command Center report'}

Safety:
Scan first. Report second. Ask before action.
Read-only Command Center.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether v10.10.0 should be marked stable/proven
2. Whether Command Center is ready for normal work
3. Which advisories are safe to ignore
4. What the next foundation milestone should be.`;
    toast('Command Center sent to Mission Console.');
}

let lastRepairFreeze=null;
async function loadRepairFreeze(doExport=false){
    if(!q('repairFreezeStatus'))return;
    q('repairFreezeStatus').textContent='Loading Repair Shop milestone freeze...';
    let d=await api('/api/repair/milestone_freeze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('repairFreezeStatus').textContent=d?.message||'Could not load milestone freeze.';
        return;
    }
    lastRepairFreeze=d;
    let s=d.summary||{};
    q('repairFreezeStatus').textContent=`Milestone freeze loaded.
Health: ${d.health_label}
Freeze ready: ${d.freeze_ready}
Modules proven: ${s.modules_complete_proven}/${s.modules}
Repair failures: ${s.repair_failed}
Verification failures: ${s.verification_failed}
Open tickets: ${s.open_tickets}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairFreezeSummary').innerHTML=`<span class="freezeBadge ${d.freeze_ready?'healthy':'warn'}">${esc(d.health_label||'UNKNOWN')}</span>
<div><b>${esc(d.milestone||'')}</b> • ${esc(d.version_range||'')}</div>
<div class=freezeGrid>
  <div class=freezeMetric><div class=label>Modules Proven</div><div class=value>${s.modules_complete_proven||0}/${s.modules||0}</div></div>
  <div class=freezeMetric><div class=label>Repair Failed</div><div class=value>${s.repair_failed||0}</div></div>
  <div class=freezeMetric><div class=label>Verify Failed</div><div class=value>${s.verification_failed||0}</div></div>
  <div class=freezeMetric><div class=label>Open Tickets</div><div class=value>${s.open_tickets||0}</div></div>
  <div class=freezeMetric><div class=label>Critical/High/Med</div><div class=value>${s.critical||0}/${s.high||0}/${s.medium||0}</div></div>
  <div class=freezeMetric><div class=label>Backups</div><div class=value>${s.generated_backups||0}</div></div>
  <div class=freezeMetric><div class=label>Recovery</div><div class=value>${esc(s.recovery_chain||'')}</div></div>
  <div class=freezeMetric><div class=label>Active Tickets</div><div class=value>${s.active_tickets||0}</div></div>
</div>
<div class=freezePath>Repair Shop: ${esc(s.repair_shop_health||'')} • Session: ${esc(s.session_health||'')}</div>
<div class=freezePath>Recovery: ${esc(s.recovery_health||'')} • Latest: ${esc(s.latest_recovery_event||'')}</div>
<div class=freezePath>Latest action: ${esc(s.latest_action||'none')} ${s.latest_action_created?('• '+esc(s.latest_action_created)) : ''}</div>`;
    q('repairFreezeModules').innerHTML=(d.milestone_modules||[]).map(m=>`<div class="histrow ${m.status==='complete_proven'?'ok':'fail'}"><b>${esc(m.version||'')} — ${esc(m.name||'')}</b>${verifyBadge(m.status==='complete_proven'?'passed':'failed')}
<div>Status: ${esc(m.status||'')}</div>
<div>${esc(m.proof||'')}</div>
<div class=vaultpath>Endpoint: ${esc(m.endpoint||'')} | Page: ${esc(m.page||'')}</div></div>`).join('')||'No modules.';
    q('repairFreezeRecommendations').innerHTML=(d.recommendations||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b>
<div>ID: ${esc(r.id||'')} | Status: ${esc(r.status||'')} | Risk: ${esc(r.risk||'')}</div>
<div>${esc(r.recommendation||'')}</div></div>`).join('')||'No recommendations.';
    let sc=d.safety_contract||{};
    q('repairFreezeSafety').textContent=Object.entries(sc).map(([k,v])=>`${k}: ${v}`).join('\n');
    q('repairFreezeProblems').innerHTML=(d.problems||[]).map(p=>`<div class="histrow fail"><b>${esc(p.source||'review')}</b><div>${esc(p.message||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No problems.</b><div>Milestone is ready to freeze.</div></div>';
    toast('Repair Shop milestone freeze loaded.');
}
function sendRepairFreezeToMission(){
    if(!lastRepairFreeze){
        toast('Load milestone freeze first.');
        return;
    }
    let d=lastRepairFreeze;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Shop Milestone Freeze.

Milestone:
${d.milestone}
Version range: ${d.version_range}
Health: ${d.health_label}
Freeze ready: ${d.freeze_ready}

Summary:
Modules proven: ${s.modules_complete_proven}/${s.modules}
Modules need review: ${s.modules_need_review}
Repair Shop health: ${s.repair_shop_health}
Session health: ${s.session_health}
Ticket Queue health: ${s.ticket_queue_health}
Verified Action health: ${s.verified_action_health}
Recovery health: ${s.recovery_health}
Recovery chain: ${s.recovery_chain}
Repair logs: ${s.repair_logs}
Repair failed: ${s.repair_failed}
Verification failed: ${s.verification_failed}
Open tickets: ${s.open_tickets}
Critical/high/medium: ${s.critical}/${s.high}/${s.medium}
Active tickets: ${s.active_tickets}
Available action tickets: ${s.available_action_tickets}
Informational tickets: ${s.informational_tickets}
Healthy tickets: ${s.healthy_tickets}
Generated backups: ${s.generated_backups}
Verified backups: ${s.verified_backups}
Backup errors: ${s.backup_errors}
Latest action: ${s.latest_action}
Latest recovery event: ${s.latest_recovery_event}

Proven modules:
${(d.milestone_modules||[]).map(m=>`${m.version} — ${m.name} — ${m.status} — ${m.proof}`).join('\n')}

Recommendations:
${(d.recommendations||[]).map(r=>`${r.id}: ${r.status} — ${r.recommendation}`).join('\n')}

Problems:
${(d.problems||[]).length ? (d.problems||[]).map(p=>`${p.source}: ${p.message}`).join('\n') : 'None.'}

Safety contract:
Scan first. Report second. Ask before action.
Read-only freeze report.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Export:
${d.exported?.markdown||'No exported freeze report'}

Please determine:
1. Whether v10.9.x Repair Shop Foundation should be frozen
2. Whether the safety contract is sufficient
3. Whether legacy logs can remain historical
4. What the next milestone should be.`;
    toast('Repair Shop freeze sent to Mission Console.');
}

let lastRepairSession=null;
async function loadRepairSession(doExport=false){
    if(!q('repairSessionStatus'))return;
    q('repairSessionStatus').textContent='Loading Repair Shop session report...';
    let d=await api('/api/repair/session_report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('repairSessionStatus').textContent=d?.message||'Could not load session report.';
        return;
    }
    lastRepairSession=d;
    let s=d.summary||{};
    q('repairSessionStatus').textContent=`Session loaded.
Health: ${d.health_label}
Repair Shop: ${s.repair_shop_health}
Ticket Queue: ${s.ticket_queue_health}
Active tickets: ${s.active_tickets}
Open tickets: ${s.open_tickets}
Latest action: ${s.latest_action}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairSessionSummary').innerHTML=`<span class="sessionBadge ${d.healthy?'healthy':'warn'}">${esc(d.health_label||'UNKNOWN')}</span>
<div class=sessionGrid>
  <div class=sessionMetric><div class=label>Repair Logs</div><div class=value>${s.repair_logs||0}</div></div>
  <div class=sessionMetric><div class=label>Repair Failed</div><div class=value>${s.repair_failed||0}</div></div>
  <div class=sessionMetric><div class=label>Verify Failed</div><div class=value>${s.verification_failed||0}</div></div>
  <div class=sessionMetric><div class=label>Active Tickets</div><div class=value>${s.active_tickets||0}</div></div>
  <div class=sessionMetric><div class=label>Open Tickets</div><div class=value>${s.open_tickets||0}</div></div>
  <div class=sessionMetric><div class=label>Backups</div><div class=value>${s.generated_backups||0}</div></div>
  <div class=sessionMetric><div class=label>Legacy Logs</div><div class=value>${s.legacy_logs_without_verification||0}</div></div>
  <div class=sessionMetric><div class=label>Recovery</div><div class=value>${esc(s.recovery_chain||'')}</div></div>
</div>
<div class=sessionPath>Repair Shop: ${esc(s.repair_shop_health||'')} • Ticket Queue: ${esc(s.ticket_queue_health||'')}</div>
<div class=sessionPath>Recovery: ${esc(s.recovery_health||'')} • Latest recovery: ${esc(s.latest_recovery_event||'')}</div>
<div class=sessionPath>Latest action: ${esc(s.latest_action||'none')} ${s.latest_action_created?('• '+esc(s.latest_action_created)) : ''}</div>`;
    q('repairSessionChanged').innerHTML=(d.what_changed_this_session||[]).map(x=>`<div class="histrow ${x.ok?'ok':'fail'}"><b>${esc(x.created||'')} — ${esc(x.title||'')}</b>${verifyBadge(x.verified_state||'')}
<div>${esc(x.summary||'')}</div>
<div class=vaultpath>Target: ${esc(x.target||'')}</div>
<div class=vaultpath>Backup: ${esc(x.backup||'')}</div>
<div class=vaultpath>Log: ${esc(x.log||'')}</div></div>`).join('')||'No recent changes.';
    q('repairSessionTickets').innerHTML=(d.active_tickets||[]).map(t=>`<div class="ticket ${esc(t.severity||'info')}"><b>${esc(t.title||'')}</b>
<div>Source: ${esc(t.source||'')} | Severity: ${esc(t.severity||'')} | Status: ${esc(t.status||'')}</div>
<div>${esc(t.summary||'')}</div>
<div class=vaultpath>Suggested: ${esc(t.suggested_action||'')}</div>
<div class=vaultpath>Safe action: ${esc(t.safe_action_id||'none')}</div></div>`).join('')||'No active tickets.';
    q('repairSessionNext').innerHTML=(d.recommended_next||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b>
<div>Ticket: ${esc(r.ticket_id||'')} | Severity: ${esc(r.severity||'')}</div>
<div>${esc(r.recommendation||'')}</div>
<div class=vaultpath>Safe action: ${esc(r.safe_action_id||'none')} | Manual approval required: ${r.manual_approval_required} | Auto apply: ${r.auto_apply}</div></div>`).join('')||'No recommendations.';
    q('repairSessionIgnore').innerHTML=(d.safe_to_ignore||[]).map(r=>`<div class="histrow ok"><b>${esc(r.title||'')}</b>
<div>${esc(r.reason||'')}</div>
<div class=vaultpath>${esc(r.suggested_action||'')}</div></div>`).join('')||'No historical items.';
    toast('Repair Shop session report loaded.');
}
function sendRepairSessionToMission(){
    if(!lastRepairSession){
        toast('Load session report first.');
        return;
    }
    let d=lastRepairSession;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Shop Session Report.

Health:
${d.health_label}

Summary:
Repair Shop health: ${s.repair_shop_health}
Ticket Queue health: ${s.ticket_queue_health}
Verified Action health: ${s.verified_action_health}
Recovery health: ${s.recovery_health}
Recovery chain: ${s.recovery_chain}
Repair logs: ${s.repair_logs}
Repair OK: ${s.repair_ok}
Repair failed: ${s.repair_failed}
Verification passed: ${s.verification_passed}
Verification failed: ${s.verification_failed}
Legacy logs without verification: ${s.legacy_logs_without_verification}
Tickets: ${s.tickets}
Active tickets: ${s.active_tickets}
Open tickets: ${s.open_tickets}
Available-action tickets: ${s.available_action_tickets}
Informational tickets: ${s.informational_tickets}
Healthy tickets: ${s.healthy_tickets}
Critical/high/medium: ${s.critical}/${s.high}/${s.medium}
Generated backups: ${s.generated_backups}
Verified backups: ${s.verified_backups}
Unassociated backups: ${s.unassociated_backups}
Backup errors: ${s.backup_errors}
Latest action: ${s.latest_action}
Latest action created: ${s.latest_action_created}
Latest backup: ${s.latest_backup}
Latest recovery event: ${s.latest_recovery_event}

What changed this session:
${(d.what_changed_this_session||[]).map(x=>`${x.created} — ${x.title} — ok=${x.ok} — verified=${x.verified_state} — ${x.summary} — target=${x.target} — backup=${x.backup}`).join('\n')}

Active tickets:
${(d.active_tickets||[]).map(t=>`${t.severity} — ${t.id}: ${t.summary} — suggested=${t.suggested_action} — safe_action=${t.safe_action_id||'none'}`).join('\n')}

Recommended next:
${(d.recommended_next||[]).map(r=>`${r.ticket_id}: ${r.recommendation} — manual approval required=${r.manual_approval_required} — auto apply=${r.auto_apply}`).join('\n')}

Safe to ignore/historical:
${(d.safe_to_ignore||[]).map(r=>`${r.ticket_id}: ${r.reason}`).join('\n')}

Export:
${d.exported?.markdown||'No exported session report'}

Safety:
Read-only session report.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this session should be marked healthy
2. What should be safely ignored
3. What, if anything, should be recommended next
4. Whether v10.9.6 should be marked stable
5. Whether the next build should freeze Repair Shop or add a session archive viewer.`;
    toast('Repair Shop session sent to Mission Console.');
}

let lastTicketBridge=null;
let recommendedRepairActionId='';
function bridgeBadge(status,label){
    status=(status||'').toLowerCase();
    let cls=status==='ready_for_manual_approval'?'ready':(status==='informational_only'?'info':'warn');
    return `<span class="bridgeBadge ${cls}">${esc(label||status||'UNKNOWN')}</span>`;
}
async function loadTicketBridgeList(){
    q('ticketBridgeStatus').textContent='Loading ticket list for bridge...';
    let d=await api('/api/repair/ticket_queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({include_healthy:true,limit:500})});
    if(!d?.ok){q('ticketBridgeStatus').textContent=d?.message||'Could not load ticket queue.';return;}
    let all=d.tickets||[];
    q('ticketBridgeSelect').innerHTML=all.map(t=>`<option value="${esc(t.id||'')}">${esc((t.severity||'').toUpperCase())} — ${esc(t.id||'')} — ${esc(t.title||'')}</option>`).join('');
    if(all.length)q('ticketBridgeQuery').value=all[0].id||'';
    q('ticketBridgeStatus').textContent=`Loaded ${all.length} ticket(s) for bridge.`;
}
async function loadTicketBridge(doExport=false){
    let id=q('ticketBridgeQuery').value||q('ticketBridgeSelect').value||'';
    q('ticketBridgeStatus').textContent='Loading Ticket-to-Approved-Action Bridge...';
    let d=await api('/api/repair/ticket_action_bridge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticket_id:id,query:id,export:doExport})});
    if(!d?.ok){q('ticketBridgeStatus').textContent=d?.message||'Could not load bridge.';return;}
    lastTicketBridge=d;
    recommendedRepairActionId=d.safe_action_id||'';
    q('ticketBridgeStatus').textContent=`Bridge loaded.
Ticket: ${d.ticket_id}
Bridge status: ${d.bridge_status}
Safe action: ${d.safe_action_id||'none'}
Available: ${d.safe_action_available}
Requires confirmation: ${d.safe_action_requires_confirmation}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    let a=d.matching_safe_action||{};
    q('ticketBridgeSummary').innerHTML=`${bridgeBadge(d.bridge_status,d.bridge_label)}
<div><b>${esc(d.ticket_title||'Ticket')}</b></div>
<div>Source: ${esc(d.ticket_source||'')} • Severity: <b>${esc(d.ticket_severity||'')}</b> • Ticket status: <b>${esc(d.ticket_status||'')}</b></div>
<div>${esc(d.ticket_summary||'')}</div>
<div class=bridgeGrid>
  <div class=bridgeMetric><div class=label>Safe Action</div><div class=value>${esc(d.safe_action_id||'none')}</div></div>
  <div class=bridgeMetric><div class=label>Available</div><div class=value>${d.safe_action_available}</div></div>
  <div class=bridgeMetric><div class=label>Confirmation</div><div class=value>${d.safe_action_requires_confirmation}</div></div>
  <div class=bridgeMetric><div class=label>Detail OK</div><div class=value>${d.detail_ok}</div></div>
</div>
<div class=vaultpath>${esc(d.message||'')}</div>`;
    q('ticketBridgeAction').innerHTML=a.id?`<div class=histrow ${a.available?'ok':'info'}><b>${esc(a.title||a.id)}</b><div>ID: <code>${esc(a.id)}</code> | Risk: ${esc(a.risk||'')}</div><div>${esc(a.description||'')}</div><div>Available: ${a.available} | Requires confirmation: ${a.requires_confirmation}</div><div class=vaultpath>Reason: ${esc(a.reason||'')}</div><div class=vaultpath>Writes: ${(a.writes||[]).map(w=>esc(w)).join(' | ')||'none'}</div></div>`:'No matching safe action for this ticket.';
    q('ticketBridgeSteps').innerHTML=(d.manual_next_steps||[]).map((s,i)=>`<div class="histrow info"><b>Step ${i+1}</b><div>${esc(s)}</div></div>`).join('')||'No steps.';
    q('ticketBridgeChecks').innerHTML=(d.detail_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b>${verifyBadge(c.ok?'passed':'failed')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No checks.';
    q('ticketBridgeRelated').innerHTML=(d.related_paths||[]).map(r=>`<div class="histrow ${r.exists||r.kind==='internal'?'ok':'info'}"><b>${esc(r.key||'path')}</b><div>Kind: ${esc(r.kind||'')} • Exists: ${r.exists}</div><div class=vaultpath>${esc(r.path||'')}</div></div>`).join('')||'No related paths.';
    toast('Ticket bridge loaded.');
}
function bridgeOpenRepairActions(){
    if(lastTicketBridge)recommendedRepairActionId=lastTicketBridge.safe_action_id||'';
    go('repairactions');
    setTimeout(()=>buildRepairActionPlan(),120);
    if(recommendedRepairActionId)toast('Repair Actions opened. Recommended action: '+recommendedRepairActionId+' — manual approval still required.');
    else toast('Repair Actions opened. This ticket has no mapped safe action.');
}
function sendTicketBridgeToMission(){
    if(!lastTicketBridge){toast('Load bridge first.');return;}
    let d=lastTicketBridge;
    let a=d.matching_safe_action||{};
    go('mission');
    q('input').value=`Please review this Kayock Ticket-to-Approved-Action Bridge.

Bridge:
${d.bridge_label}
Status: ${d.bridge_status}
Message: ${d.message}

Ticket:
ID: ${d.ticket_id}
Title: ${d.ticket_title}
Source: ${d.ticket_source}
Severity: ${d.ticket_severity}
Status: ${d.ticket_status}
Summary: ${d.ticket_summary}

Evidence:
${(d.evidence||[]).map(e=>'- '+e).join('\n')}

Suggested action:
${d.suggested_action}

Matching safe action:
ID: ${a.id||'none'}
Title: ${a.title||''}
Available: ${a.available}
Requires confirmation: ${a.requires_confirmation}
Risk: ${a.risk||''}
Reason: ${a.reason||''}
Writes:
${(a.writes||[]).map(w=>'- '+w).join('\n')||'- none'}

Manual next steps:
${(d.manual_next_steps||[]).map((s,i)=>`${i+1}. ${s}`).join('\n')}

Bridge checks:
${(d.detail_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Export:
${d.exported?.markdown||'No exported bridge report'}

Safety:
Read-only bridge.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this ticket is correctly mapped to the safe action
2. Whether manual approval guardrails are sufficient
3. Whether v10.9.5 should be marked stable
4. Whether the next build should be Repair Shop Session Report.`;
    toast('Ticket bridge sent to Mission Console.');
}

let lastRepairTicketDetail=null;
function ticketDetailBadge(status){
    status=(status||'open').toLowerCase();
    let cls=['healthy','available_action','informational','needs_attention','open'].includes(status)?status:'open';
    return `<span class="ticketDetailBadge ${cls}">${esc(status.toUpperCase())}</span>`;
}
async function loadRepairTicketDetailList(){
    if(!q('repairTicketDetailStatus'))return;
    q('repairTicketDetailStatus').textContent='Loading ticket list...';
    let d=await api('/api/repair/ticket_queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:500,include_healthy:true})});
    if(!d?.ok){q('repairTicketDetailStatus').textContent=d?.message||'Could not load tickets.';return;}
    let all=[...(d.active_tickets||[]),...(d.healthy_tickets||[])];
    q('repairTicketDetailSelect').innerHTML=all.map(t=>`<option value="${esc(t.id||'')}">${esc((t.severity||'').toUpperCase())} — ${esc(t.id||'')} — ${esc(t.title||'')}</option>`).join('');
    if(all.length) q('repairTicketDetailQuery').value=all[0].id||'';
    q('repairTicketDetailStatus').textContent=`Loaded ${all.length} ticket(s) for detail inspection.`;
}
async function loadRepairTicketDetail(doExport=false){
    let id=q('repairTicketDetailQuery').value||q('repairTicketDetailSelect').value||'';
    q('repairTicketDetailStatus').textContent='Loading ticket detail...';
    let d=await api('/api/repair/ticket_detail',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticket_id:id,query:id,export:doExport})});
    if(!d?.ok){q('repairTicketDetailStatus').textContent=d?.message||'Could not load ticket detail.';return;}
    lastRepairTicketDetail=d;
    let t=d.ticket||{};
    q('repairTicketDetailStatus').textContent=`Ticket detail loaded.
Ticket: ${d.ticket_id}
Status: ${d.status}
Severity: ${d.ticket_severity}
Source: ${d.ticket_source}
Detail OK: ${d.detail_ok}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairTicketDetailSummary').innerHTML=`${ticketDetailBadge(d.status)}
<div><b>${esc(d.ticket_title||'Ticket')}</b></div>
<div>Source: ${esc(d.ticket_source||'')} • Severity: <b>${esc(d.ticket_severity||'')}</b> • Ticket status: <b>${esc(d.ticket_status||'')}</b></div>
<div>${esc(d.ticket_summary||'')}</div>
<div class=ticketDetailGrid>
  <div class=ticketDetailMetric><div class=label>Queue Tickets</div><div class=value>${(d.queue_summary||{}).tickets||0}</div></div>
  <div class=ticketDetailMetric><div class=label>Active</div><div class=value>${(d.queue_summary||{}).active_tickets||0}</div></div>
  <div class=ticketDetailMetric><div class=label>Open</div><div class=value>${(d.queue_summary||{}).open_tickets||0}</div></div>
  <div class=ticketDetailMetric><div class=label>Errors</div><div class=value>${(d.queue_summary||{}).errors||0}</div></div>
</div>
<div class=ticketDetailPath>Source folder: ${esc(d.source_folder||'')}</div>`;
    q('repairTicketDetailEvidence').innerHTML=(d.evidence||[]).map(e=>`<div class="histrow info"><b>Evidence</b><div>${esc(e)}</div></div>`).join('')||'No evidence listed.';
    let a=d.matching_safe_action||null;
    q('repairTicketDetailAction').innerHTML=`<div><b>Suggested action</b></div><div>${esc(d.suggested_action||'None')}</div>
<div class=ticketDetailPath>Safe action ID: ${esc(d.safe_action_id||'none')}</div>
${a?`<h4>Matching Safe Action</h4><div><b>${esc(a.title||'')}</b></div><div>Available: ${a.available} • Requires confirmation: ${a.requires_confirmation} • Risk: ${esc(a.risk||'')}</div><div>${esc(a.description||'')}</div><div class=ticketDetailPath>Reason: ${esc(a.reason||'')}</div><div class=ticketDetailPath>Writes: ${(a.writes||[]).map(w=>esc(w)).join(' | ')||'none'}</div>`:'<div class=ticketDetailPath>No matching safe action required or linked.</div>'}`;
    q('repairTicketDetailRelated').innerHTML=(d.related_paths||[]).map(r=>`<div class="histrow ${r.exists?'ok':'info'}"><b>${esc(r.key||'path')}</b><div>Kind: ${esc(r.kind||'')} • Exists: ${r.exists} ${r.size?('• Size: '+r.size):''}</div><div class=ticketDetailPath>${esc(r.path||'')}</div></div>`).join('')||'No related paths.';
    q('repairTicketDetailChecks').innerHTML=(d.detail_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b>${verifyBadge(c.ok?'passed':'failed')}<div>${esc(c.message||'')}</div><div class=ticketDetailPath>${esc(c.path||'')}</div></div>`).join('')||'No detail checks.';
    toast('Repair ticket detail loaded.');
}
function sendRepairTicketDetailToMission(){
    if(!lastRepairTicketDetail){toast('Load a ticket detail first.');return;}
    let d=lastRepairTicketDetail;
    let a=d.matching_safe_action||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Ticket Detail.

Ticket:
ID: ${d.ticket_id}
Title: ${d.ticket_title}
Source: ${d.ticket_source}
Severity: ${d.ticket_severity}
Ticket status: ${d.ticket_status}
Detail status: ${d.status}
Summary: ${d.ticket_summary}

Evidence:
${(d.evidence||[]).map(e=>`- ${e}`).join('\n')}

Suggested action:
${d.suggested_action}

Safe action:
ID: ${d.safe_action_id||'none'}
Matched: ${!!d.matching_safe_action}
Available: ${d.safe_action_available}
Requires confirmation: ${d.safe_action_requires_confirmation}
Title: ${a.title||''}
Reason: ${a.reason||''}
Writes: ${(a.writes||[]).join(', ')||'none'}

Queue summary:
Tickets: ${(d.queue_summary||{}).tickets}
Active: ${(d.queue_summary||{}).active_tickets}
Open: ${(d.queue_summary||{}).open_tickets}
Errors: ${(d.queue_summary||{}).errors}

Related paths:
${(d.related_paths||[]).map(r=>`${r.key}: exists=${r.exists}, kind=${r.kind}, path=${r.path}`).join('\n')}

Detail checks:
${(d.detail_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Export:
${d.exported?.markdown||'No exported ticket detail'}

Safety:
Read-only ticket detail viewer.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this ticket is real work, informational, or healthy
2. Whether its suggested action is safe
3. Whether the linked safe action should remain manual-only
4. Whether this ticket can be dismissed, left historical, or tracked
5. Whether v10.9.4 should be marked stable.`;
    toast('Repair ticket detail sent to Mission Console.');
}

let lastRepairTickets=null;
function ticketBadge(sev){
    sev=(sev||'info').toLowerCase();
    let cls=['critical','high','medium','low','info','healthy'].includes(sev)?sev:'info';
    return `<span class="ticketBadge ${cls}">${esc(sev.toUpperCase())}</span>`;
}
function ticketRow(t){
    return `<div class="ticketRow ${esc(t.severity||'info')}">${ticketBadge(t.severity)}<b>${esc(t.title||'Ticket')}</b>
<div>Source: ${esc(t.source||'')} • Status: <b>${esc(t.status||'')}</b> • Risk: ${esc(t.risk||'')}</div>
<div>${esc(t.summary||'')}</div>
<div class=ticketPath>Suggested: ${esc(t.suggested_action||'None')}</div>
${t.safe_action_id?`<div class=ticketPath>Safe action ID: ${esc(t.safe_action_id)}</div>`:''}
${(t.evidence||[]).length?`<div class=ticketPath>Evidence: ${(t.evidence||[]).map(e=>esc(e)).join(' | ')}</div>`:''}</div>`;
}
async function loadRepairTickets(doExport=false){
    if(!q('repairTicketStatus'))return;
    q('repairTicketStatus').textContent='Loading Repair Ticket Queue...';
    let d=await api('/api/repair/ticket_queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:500,export:doExport,include_healthy:true})});
    if(!d?.ok){q('repairTicketStatus').textContent=d?.message||'Could not load ticket queue.';return;}
    lastRepairTickets=d;
    let s=d.summary||{};
    q('repairTicketStatus').textContent=`Repair Ticket Queue loaded.
Health: ${d.health_label}
Tickets: ${s.tickets}
Active: ${s.active_tickets}
Open: ${s.open_tickets}
Available actions: ${s.available_action_tickets}
Informational: ${s.informational_tickets}
Errors: ${s.errors}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairTicketDashboard').innerHTML=`<span class="ticketBadge ${d.healthy?'healthy':'medium'}">${esc(d.health_label||'UNKNOWN')}</span>
<div class=ticketGrid>
  <div class=ticketMetric><div class=label>Tickets</div><div class=value>${s.tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Active</div><div class=value>${s.active_tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Open</div><div class=value>${s.open_tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Available</div><div class=value>${s.available_action_tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Info</div><div class=value>${s.informational_tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
</div>
<div class=ticketPath>Repair Shop: ${esc(s.repair_shop_health||'')} • Recovery: ${esc(s.recovery_health||'')}</div>
<div class=ticketPath>Latest action: ${esc(s.latest_repair_action||'')} • Latest recovery: ${esc(s.latest_recovery_event||'')}</div>`;
    q('repairTicketActive').innerHTML=(d.active_tickets||[]).map(ticketRow).join('')||'No active tickets.';
    q('repairTicketActions').innerHTML=(d.available_action_tickets||[]).map(ticketRow).join('')||'No available action tickets.';
    q('repairTicketInfo').innerHTML=(d.informational_tickets||[]).map(ticketRow).join('')||'No informational tickets.';
    q('repairTicketHealthy').innerHTML=(d.healthy_tickets||[]).map(ticketRow).join('')||'No healthy checks listed.';
    toast('Repair Ticket Queue loaded.');
}
function sendRepairTicketsToMission(){
    if(!lastRepairTickets){toast('Load ticket queue first.');return;}
    let d=lastRepairTickets;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Ticket Queue.

Health:
${d.health_label}

Summary:
Tickets: ${s.tickets}
Active tickets: ${s.active_tickets}
Open tickets: ${s.open_tickets}
Available action tickets: ${s.available_action_tickets}
Informational tickets: ${s.informational_tickets}
Healthy tickets: ${s.healthy_tickets}
Critical: ${s.critical}
High: ${s.high}
Medium: ${s.medium}
Low: ${s.low}
Info: ${s.info}
Healthy: ${s.healthy}
Errors: ${s.errors}
Repair Shop health: ${s.repair_shop_health}
Recovery health: ${s.recovery_health}
Latest repair action: ${s.latest_repair_action}
Latest recovery event: ${s.latest_recovery_event}

Active Tickets:
${(d.active_tickets||[]).map(t=>`${t.severity}/${t.status} — ${t.source} — ${t.title} — ${t.summary} — Suggested: ${t.suggested_action||'None'} — Safe action: ${t.safe_action_id||''}`).join('\n')}

Available Action Tickets:
${(d.available_action_tickets||[]).map(t=>`${t.id}: ${t.title} — ${t.suggested_action} — ${t.safe_action_id||''}`).join('\n')}

Informational Tickets:
${(d.informational_tickets||[]).map(t=>`${t.id}: ${t.title} — ${t.summary}`).join('\n')}

Source states:
${Object.entries(d.sources||{}).map(([k,v])=>`${k}: ${v}`).join('\n')}

Export:
${d.exported?.markdown||'No exported ticket report'}

Safety:
Read-only ticket queue.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the ticket queue is accurate
2. Which tickets are informational only
3. Whether any available action should remain user-approved only
4. Whether v10.9.3 should be marked stable
5. Whether the next build should be a Ticket Detail Viewer.`;
    toast('Repair Ticket Queue sent to Mission Console.');
}

let lastRepairShopCard=null;
async function loadRepairShopDashboardCard(){
    if(!q('repairShopDashCard'))return;
    q('repairShopDashCard').textContent='Loading Repair Shop health...';
    let d=await api('/api/repair/verified_dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300})});
    if(!d?.ok){q('repairShopDashCard').textContent=d?.message||'Repair Shop health unavailable.';return;}
    lastRepairShopCard=d;
    let s=d.summary||{}, l=d.latest_action||{};
    q('repairShopDashCard').innerHTML=`<span class="repairCardBadge ${d.healthy?'healthy':'warn'}">${esc(d.health_label||'UNKNOWN')}</span>
<div>Latest action: <b>${esc(l.action_id||'none')}</b> • Verification: <b>${esc(l.verified_state||'unknown')}</b></div>
<div class=repairCardGrid>
  <div class=repairCardMetric><div class=label>Repair Logs</div><div class=value>${s.repair_logs||0}</div></div>
  <div class=repairCardMetric><div class=label>Failures</div><div class=value>${s.repair_failed||0}</div></div>
  <div class=repairCardMetric><div class=label>Verify Fail</div><div class=value>${s.verification_failed||0}</div></div>
  <div class=repairCardMetric><div class=label>Verified</div><div class=value>${s.verification_passed||0}</div></div>
  <div class=repairCardMetric><div class=label>Legacy</div><div class=value>${s.legacy_logs_without_verification||0}</div></div>
  <div class=repairCardMetric><div class=label>Safe Actions</div><div class=value>${s.safe_actions_available||0}</div></div>
</div>
<div class=repairCardPath>Created: ${esc(l.created||'')} • ${esc(l.message||'')}</div>
<div class=repairCardPath>Target: ${esc(l.target||'')}</div>
<div class=repairCardPath>Recovery: ${esc(s.recovery_health||'unknown')} • Chain: ${esc(s.recovery_chain||'unknown')}</div>`;
}
function sendRepairShopDashboardCardToMission(){
    if(!lastRepairShopCard){toast('Load Repair Shop health first.');return;}
    let d=lastRepairShopCard, s=d.summary||{}, l=d.latest_action||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Shop Command Bridge card.

Health:
${d.health_label}

Latest action:
Action ID: ${l.action_id}
Created: ${l.created}
OK: ${l.ok}
Verified state: ${l.verified_state}
Message: ${l.message}
Target: ${l.target}
Backup: ${l.backup}
Log JSON: ${l.log_json}
Log Markdown: ${l.log_markdown}

Summary:
Repair logs: ${s.repair_logs}
Repair OK: ${s.repair_ok}
Repair failures: ${s.repair_failed}
Verification passed: ${s.verification_passed}
Verification failures: ${s.verification_failed}
Legacy logs without verification: ${s.legacy_logs_without_verification}
Safe actions available: ${s.safe_actions_available}
Safe actions blocked: ${s.safe_actions_blocked}
Generated backups: ${s.generated_backups}
Backup errors: ${s.backup_errors}
Recovery health: ${s.recovery_health}
Recovery chain: ${s.recovery_chain}
Recovery attention: ${s.recovery_attention}
Recovery errors: ${s.recovery_errors}
Latest backup: ${s.latest_backup}
Latest recovery event: ${s.latest_recovery_event}

Action types:
${(d.action_types||[]).map(a=>`${a.action_id}: count ${a.count}, ok ${a.ok}, failed ${a.failed}, verified ${a.verified}, verification failed ${a.verification_failed}, legacy ${a.not_recorded}`).join('\n')}

Safety:
Read-only dashboard card.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the Repair Shop card is accurate
2. Whether the latest verified action should be surfaced on Command Bridge
3. Whether legacy logs can remain historical
4. Whether v10.9.2 should be marked stable.`;
    toast('Repair Shop health sent to Mission Console.');
}

let lastRepairDetail=null;
function detailBadge(status){status=(status||'attention').toLowerCase();let cls=['verified','legacy_ok','failed','attention'].includes(status)?status:'attention';return `<span class="detailBadge ${cls}">${esc(status.toUpperCase())}</span>`;}
async function loadRepairDetailList(){q('repairDetailStatus').textContent='Loading RepairActions logs...';let h=await api('/api/repair/actions/history',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});if(!h?.ok){q('repairDetailStatus').textContent=h?.message||'Could not load RepairActions history.';return;}let sel=q('repairDetailSelect');sel.innerHTML=(h.logs||[]).map(l=>`<option value="${esc(l.path||'')}">${esc(l.created||'')} — ${esc(l.action_id||'unknown')} — ${esc(l.verified_state||'')}</option>`).join('');if((h.logs||[]).length){q('repairDetailPath').value=h.logs[0].path||'';}q('repairDetailStatus').textContent=`Loaded ${h.logs?.length||0} RepairActions log(s).`;}
async function loadRepairDetail(doExport=false){let path=q('repairDetailPath').value||q('repairDetailSelect').value||'';q('repairDetailStatus').textContent='Loading repair action detail...';let d=await api('/api/repair/action_detail',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,query:path,export:doExport})});if(!d?.ok){q('repairDetailStatus').textContent=d?.message||'Could not load repair action detail.';return;}lastRepairDetail=d;let v=d.verification||{};q('repairDetailStatus').textContent=`Repair action detail loaded.
Action: ${d.action_id}
Status: ${d.status}
Action OK: ${d.action_ok}
Verified state: ${d.verified_state}
Checks: ${v.passed}/${v.checked}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;q('repairDetailSummary').innerHTML=`${detailBadge(d.status)}<div><b>${esc(d.action_id||'unknown')}</b> • ${esc(d.action_created||'')}</div><div>${esc(d.message||'')}</div><div class=detailGrid><div class=detailMetric><div class=label>Action OK</div><div class=value>${d.action_ok}</div></div><div class=detailMetric><div class=label>User Approved</div><div class=value>${d.user_approved_action}</div></div><div class=detailMetric><div class=label>Verified</div><div class=value>${d.verified_state}</div></div><div class=detailMetric><div class=label>Checks</div><div class=value>${v.passed||0}/${v.checked||0}</div></div></div><div class=vaultpath>JSON: ${esc((d.log||{}).json||'')}</div><div class=vaultpath>Markdown: ${esc((d.log||{}).markdown||'')}</div>`;q('repairDetailVerification').innerHTML=(v.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b>${verifyBadge(c.ok?'passed':'failed')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||`<div class="histrow info"><b>Legacy log</b><div>${esc(v.message||'No verification recorded.')}</div></div>`;let t=d.target||{},b=d.backup||{};q('repairDetailFiles').innerHTML=`<h4>Target</h4><div class=vaultpath>${esc(t.path||'')}</div><div>Exists: ${t.exists} • Inside root: ${t.inside_root} • Size: ${t.size??''} • Modified: ${esc(t.modified||'')}</div><div class=detailHash>SHA256: ${esc(t.sha256||'')}</div><h4>Backup</h4><div class=vaultpath>${esc(b.path||'')}</div><div>Exists: ${b.exists} • Inside root: ${b.inside_root} • Size: ${b.size??''} • Modified: ${esc(b.modified||'')}</div><div class=detailHash>SHA256: ${esc(b.sha256||'')}</div>`;q('repairDetailRelated').innerHTML=(d.related_paths||[]).map(r=>`<div class="histrow ${r.exists?'ok':'info'}"><b>${esc(r.key||'path')}</b><div>Kind: ${esc(r.kind||'')} • Exists: ${r.exists}</div><div class=vaultpath>${esc(r.path||'')}</div></div>`).join('')||'No related paths.';q('repairDetailChecks').innerHTML=(d.detail_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b>${verifyBadge(c.ok?'passed':'failed')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No detail checks.';toast('Repair action detail loaded.');}
function sendRepairDetailToMission(){if(!lastRepairDetail){toast('Load a detail first.');return;}let d=lastRepairDetail,v=d.verification||{},t=d.target||{},b=d.backup||{};go('mission');q('input').value=`Please review this Kayock Repair Action Detail.

Action:
${d.action_id}
Created: ${d.action_created}
Status: ${d.status}
Action OK: ${d.action_ok}
Verified state: ${d.verified_state}
Message: ${d.message}

Log:
JSON: ${(d.log||{}).json}
Markdown: ${(d.log||{}).markdown}

Target:
Path: ${t.path}
Exists: ${t.exists}
Inside root: ${t.inside_root}
Size: ${t.size}
Modified: ${t.modified}
SHA256: ${t.sha256}

Backup:
Path: ${b.path}
Exists: ${b.exists}
Inside root: ${b.inside_root}
Size: ${b.size}
Modified: ${b.modified}
SHA256: ${b.sha256}

Verification:
Recorded: ${v.recorded}
OK: ${v.ok}
Checked: ${v.checked}
Passed: ${v.passed}
Failed: ${v.failed}
Message: ${v.message}

Verification checks:
${(v.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Detail checks:
${(d.detail_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Related paths:
${(d.related_paths||[]).map(r=>`${r.key}: exists=${r.exists}, kind=${r.kind}, path=${r.path}`).join('\n')}

Export:
${d.exported?.markdown||'No exported detail report'}

Safety:
Read-only detail viewer.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine whether this repair action detail is healthy and whether any legacy log needs migration.`;toast('Repair action detail sent to Mission Console.');}

let lastRepairOps=null;
function repairShopBadge(ok,label){
    return `<span class="repairShopBadge ${ok?'healthy':'warn'}">${esc(label||'UNKNOWN')}</span>`;
}
function actionPill(available){
    return `<span class="actionPill ${available?'available':'blocked'}">${available?'AVAILABLE':'BLOCKED'}</span>`;
}
async function loadRepairOps(doExport=false){
    if(!q('repairOpsStatus'))return;
    q('repairOpsStatus').textContent='Loading Repair Shop operations dashboard...';
    let d=await api('/api/repair/ops_dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('repairOpsStatus').textContent=d?.message||'Could not load Repair Shop dashboard.';
        return;
    }
    lastRepairOps=d;
    let s=d.summary||{};
    q('repairOpsStatus').textContent=`Repair Shop loaded.
Health: ${d.health_label}
Repair logs: ${s.repair_logs}
OK: ${s.repair_ok}
Failed: ${s.repair_failed}
Verification passed: ${s.verification_passed}
Verification failed: ${s.verification_failed}
Available actions: ${s.available_actions}
Generated backups: ${s.generated_backups}
Recovery: ${s.recovery_health}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairOpsDashboard').innerHTML=`${repairShopBadge(d.healthy,d.health_label)}
<div class=repairShopGrid>
  <div class=repairShopMetric><div class=label>Repair Logs</div><div class=value>${s.repair_logs||0}</div></div>
  <div class=repairShopMetric><div class=label>OK</div><div class=value>${s.repair_ok||0}</div></div>
  <div class=repairShopMetric><div class=label>Failed</div><div class=value>${s.repair_failed||0}</div></div>
  <div class=repairShopMetric><div class=label>Verified</div><div class=value>${s.verification_passed||0}</div></div>
  <div class=repairShopMetric><div class=label>Verify Failed</div><div class=value>${s.verification_failed||0}</div></div>
  <div class=repairShopMetric><div class=label>Legacy Logs</div><div class=value>${s.legacy_logs_without_verification||0}</div></div>
  <div class=repairShopMetric><div class=label>Available Actions</div><div class=value>${s.available_actions||0}</div></div>
  <div class=repairShopMetric><div class=label>Backups</div><div class=value>${s.generated_backups||0}</div></div>
</div>
<div class=repairShopPath>Latest action: ${esc(s.latest_action||'none')} ${s.latest_action_created?('• '+esc(s.latest_action_created)) : ''}</div>
<div class=repairShopPath>Recovery: ${esc(s.recovery_health||'unknown')} • Chain: ${esc(s.recovery_chain||'unknown')}</div>`;
    q('repairOpsActions').innerHTML=(d.safe_actions||[]).map(a=>`<div class="histrow ${a.available?'ok':'info'}"><b>${esc(a.title)}</b>${actionPill(a.available)}
<div>ID: <code>${esc(a.id)}</code> | Risk: ${esc(a.risk||'')}</div>
<div>${esc(a.description||'')}</div>
<div class=vaultpath>Reason: ${esc(a.reason||'')}</div>
<div class=vaultpath>Writes: ${(a.writes||[]).map(w=>esc(w)).join(' | ')||'none'}</div>
</div>`).join('')||'No safe actions loaded.';
    q('repairOpsByAction').innerHTML=(d.history_by_action||[]).map(a=>`<div class="histrow info"><b>${esc(a.action_id||'unknown')}</b>
<div>Count: ${a.count} | OK: ${a.ok} | Failed: ${a.failed} | Verified: ${a.verified} | Verify failed: ${a.verification_failed} | Legacy: ${a.not_recorded}</div>
<div class=vaultpath>Last: ${esc(a.last_created||'')}</div></div>`).join('')||'No action types found.';
    q('repairOpsRecent').innerHTML=(d.recent_logs||[]).map(l=>`<div class="histrow ${l.ok?'ok':'fail'}"><b>${esc(l.created||'')} — ${esc(l.action_id||'unknown')}</b>${verifyBadge(l.verified_state)}
<div>${esc(l.message||'')}</div>
<div class=vaultpath>Target: ${esc(l.target||'')}</div>
<div class=vaultpath>Backup: ${esc(l.backup||'')}</div>
<div class=vaultpath>Log: ${esc(l.markdown||l.path||'')}</div></div>`).join('')||'No recent logs.';
    q('repairOpsBackupRecovery').innerHTML=`<div class=repairShopGrid>
  <div class=repairShopMetric><div class=label>Generated Backups</div><div class=value>${s.generated_backups||0}</div></div>
  <div class=repairShopMetric><div class=label>Associated</div><div class=value>${s.associated_backups||0}</div></div>
  <div class=repairShopMetric><div class=label>Verified Backups</div><div class=value>${s.verified_backups||0}</div></div>
  <div class=repairShopMetric><div class=label>Backup Errors</div><div class=value>${s.backup_errors||0}</div></div>
  <div class=repairShopMetric><div class=label>Recovery Attention</div><div class=value>${s.recovery_attention||0}</div></div>
  <div class=repairShopMetric><div class=label>Recovery Errors</div><div class=value>${s.recovery_errors||0}</div></div>
</div>
<div class=repairShopPath>Latest backup: ${esc(s.latest_backup||'none')}</div>
<div class=repairShopPath>Latest recovery event: ${esc(s.latest_recovery_event||'none')} ${s.latest_recovery_created?('• '+esc(s.latest_recovery_created)) : ''}</div>`;
    toast('Repair Shop dashboard loaded.');
}
function sendRepairOpsToMission(){
    if(!lastRepairOps){
        toast('Load Repair Shop first.');
        return;
    }
    let s=lastRepairOps.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Shop Operations Dashboard.

Health:
${lastRepairOps.health_label}

Summary:
Repair logs: ${s.repair_logs}
Repair OK: ${s.repair_ok}
Repair failed: ${s.repair_failed}
User approved: ${s.user_approved}
Verification passed: ${s.verification_passed}
Verification failed: ${s.verification_failed}
Legacy logs without verification: ${s.legacy_logs_without_verification}
Available safe actions: ${s.available_actions}
Blocked safe actions: ${s.blocked_actions}
Generated backups: ${s.generated_backups}
Associated backups: ${s.associated_backups}
Verified backups: ${s.verified_backups}
Backup errors: ${s.backup_errors}
Recovery health: ${s.recovery_health}
Recovery chain: ${s.recovery_chain}
Recovery attention: ${s.recovery_attention}
Recovery errors: ${s.recovery_errors}
Latest action: ${s.latest_action}
Latest action created: ${s.latest_action_created}
Latest backup: ${s.latest_backup}
Latest recovery event: ${s.latest_recovery_event}

Safe Actions:
${(lastRepairOps.safe_actions||[]).map(a=>`${a.available?'AVAILABLE':'BLOCKED'} — ${a.id} — ${a.title} — ${a.reason}`).join('\n')}

Action Types:
${(lastRepairOps.history_by_action||[]).map(a=>`${a.action_id}: count ${a.count}, ok ${a.ok}, failed ${a.failed}, verified ${a.verified}, verification failed ${a.verification_failed}, legacy ${a.not_recorded}`).join('\n')}

Recent Logs:
${(lastRepairOps.recent_logs||[]).map(l=>`${l.created} — ${l.action_id} — ok=${l.ok} — verified=${l.verified_state} — ${l.message} — target=${l.target} — backup=${l.backup}`).join('\n')}

Export:
${lastRepairOps.exported?.markdown||'No exported Repair Shop report'}

Safety:
Read-only operations dashboard.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether Repair Shop should be marked healthy
2. Whether any old legacy logs need migration or can remain as historical
3. Whether safe actions should stay as currently scoped
4. Whether the next Repair Shop build should be an action detail viewer or a verified-action dashboard card.`;
    toast('Repair Shop sent to Mission Console.');
}

let lastRepairHistory=null;
function verifyBadge(state){
    if(state==='passed')return '<span class="verifybadge pass">VERIFIED</span>';
    if(state==='failed')return '<span class="verifybadge fail">VERIFY FAILED</span>';
    return '<span class="verifybadge none">OLDER LOG</span>';
}
function verificationLines(v){
    if(!v || !v.checks)return '<div class=small>Verification: not recorded in this older log.</div>';
    return `<div class=small>${esc(v.message||'')}</div>`+(v.checks||[]).map(c=>`<div class=checkline>${c.ok?'✅':'❌'} ${esc(c.id||'check')} — ${esc(c.message||'')}</div>`).join('');
}
async function loadRepairHistory(doExport=false){
    let action_filter=q('repairHistoryFilter').value||'';
    let limit=parseInt(q('repairHistoryLimit').value||'200');
    q('repairHistoryStatus').textContent='Loading repair action history...';
    let d=await api('/api/repair/actions/history',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_filter,limit,export:doExport})});
    if(!d?.ok){
        q('repairHistoryStatus').textContent=d?.message||'Could not load repair history.';
        return;
    }
    lastRepairHistory=d;
    let s=d.summary||{};
    q('repairHistoryStatus').textContent=`Repair history loaded.
Logs: ${s.logs}
OK: ${s.ok}
Failed: ${s.failed}
User approved: ${s.user_approved}
Verification passed: ${s.verification_passed||0}
Verification failed: ${s.verification_failed||0}
Older logs without verification: ${s.verification_not_recorded||0}
Last action: ${s.last_action||'none'}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairHistoryDashboard').innerHTML=`<div class=historygrid>
        <div class=historymetric><div class=label>Logs</div><div class=value>${s.logs||0}</div></div>
        <div class=historymetric><div class=label>OK</div><div class=value>${s.ok||0}</div></div>
        <div class=historymetric><div class=label>Failed</div><div class=value>${s.failed||0}</div></div>
        <div class=historymetric><div class=label>Approved</div><div class=value>${s.user_approved||0}</div></div>
        <div class=historymetric><div class=label>Verified</div><div class=value>${s.verification_passed||0}</div></div>
        <div class=historymetric><div class=label>Verify Failed</div><div class=value>${s.verification_failed||0}</div></div>
        <div class=historymetric><div class=label>Older Logs</div><div class=value>${s.verification_not_recorded||0}</div></div>
        <div class=historymetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div><div class=status>Last action: ${esc(s.last_action||'none')} | ${esc(s.last_created||'')}</div>`;
    q('repairHistoryByAction').innerHTML=(d.by_action||[]).map(a=>`<div class="histrow info"><b>${esc(a.action_id)}</b><div>Count: ${a.count} | OK: ${a.ok} | Failed: ${a.failed}</div><div>Verified: ${a.verified||0} | Verification failed: ${a.verification_failed||0} | Older logs: ${a.not_recorded||0}</div><div class=small>Last: ${esc(a.last_created||'')}</div></div>`).join('')||'No action summary yet.';
    q('repairHistoryLogs').innerHTML=(d.logs||[]).map(l=>`<div class="histrow ${l.ok?'ok':'fail'}"><b>${l.ok?'OK':'FAILED'} — ${esc(l.action_id)}</b>${verifyBadge(l.verified_state)}
<div>${esc(l.message||'')}</div>
<div class=small>Created: ${esc(l.created||'')} | Approved: ${l.user_approved_action} | Dry run: ${l.dry_run}</div>
<div class=small>Target: ${esc(l.target||'')}</div>
<div class=small>Backup: ${esc(l.backup||'')}</div>
<div class=small>Log: ${esc(l.path||'')}</div>
${verificationLines(l.verification)}</div>`).join('')||'No logs found.';
    toast('Repair history loaded.');
}
function sendRepairHistoryToMission(){
    if(!lastRepairHistory){
        toast('Load repair history first.');
        return;
    }
    let s=lastRepairHistory.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Bay Action History.

This is an audit trail review. It is read-only.

Summary:
Logs: ${s.logs}
OK: ${s.ok}
Failed: ${s.failed}
Dry runs: ${s.dry_runs}
User approved: ${s.user_approved}
Action types: ${s.actions}
Parse errors: ${s.errors}
Verification passed: ${s.verification_passed||0}
Verification failed: ${s.verification_failed||0}
Older logs without verification: ${s.verification_not_recorded||0}
Last action: ${s.last_action}
Last created: ${s.last_created}

History Report:
${lastRepairHistory.exported?.markdown||'No exported history report path'}

By Action:
${(lastRepairHistory.by_action||[]).map(a=>`${a.action_id}: count=${a.count}, ok=${a.ok}, failed=${a.failed}, verified=${a.verified||0}, verification_failed=${a.verification_failed||0}, older=${a.not_recorded||0}, last=${a.last_created}`).join('\n')}

Recent Logs:
${(lastRepairHistory.logs||[]).slice(0,20).map(l=>`${l.ok?'OK':'FAILED'} — ${l.action_id}
Created: ${l.created}
Verification: ${l.verified_state}
Verification message: ${(l.verification||{}).message||'not recorded'}
Message: ${l.message}
Target: ${l.target}
Backup: ${l.backup}
Log: ${l.path}`).join('\n\n')}

Please identify:
1. Whether the Repair Bay audit trail is trustworthy
2. Any failed or suspicious actions
3. Whether backups, logs, and post-action verification are sufficient
4. What next Repair Bay action type should be added
5. Whether it is safe to expand beyond docs/manifests/folders.`;
    toast('Repair history sent to Mission Console.');
}

let lastRepairPlan=null;
let lastRepairResult=null;
async function buildRepairActionPlan(){
    q('repairActionStatus').textContent='Building repair action plan...';
    let d=await api('/api/repair/actions/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    if(!d?.ok){
        q('repairActionStatus').textContent=d?.message||'Could not build repair action plan.';
        return;
    }
    lastRepairPlan=d;
    let s=d.summary||{};
    q('repairActionStatus').textContent=`Repair action plan ready.
Actions: ${s.actions}
Available: ${s.available}
Blocked: ${s.blocked}
Low risk: ${s.low_risk}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairActionPlan').innerHTML=(d.actions||[]).map(a=>`<div class="repairrow ${a.available?'available':'blocked'} ${(recommendedRepairActionId&&a.id===recommendedRepairActionId)?'recommended':''}">${(recommendedRepairActionId&&a.id===recommendedRepairActionId)?'<div class=recommendTag>RECOMMENDED FROM TICKET — MANUAL APPROVAL STILL REQUIRED</div>':''}<div class=repairtitle>${esc(a.title)}</div>
<div class=risk>ID: ${esc(a.id)} | Risk: ${esc(a.risk)} | Available: ${a.available}</div>
<div>${esc(a.description||'')}</div>
<div class=small>${esc(a.reason||'')}</div>
<div class=small>Writes: ${(a.writes||[]).map(x=>esc(x)).join('<br>')||'none'}</div>
${a.available?`<button onclick="applyRepairAction('${esc(a.id)}')">Apply This Action</button>`:''}</div>`).join('');
    if(recommendedRepairActionId){q('repairActionStatus').textContent += `
Recommended from Ticket Bridge: ${recommendedRepairActionId}
Manual approval is still required.`;}
    toast('Repair action plan built.');
}
async function applyRepairAction(actionId){
    if(!actionId){
        toast('Missing action id.');
        return;
    }
    let expected=`APPLY ${actionId}`;
    let typed=prompt(`Repair Chamber approval required.\n\nReview the listed writes and backups, then type exactly:\n${expected}`,'');
    if(typed===null)return;
    if(typed.trim()!==expected){toast('Exact approval phrase did not match. No action was sent.');return;}
    let d=await api('/api/repair/actions/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_id:actionId,confirm:typed,actor:'operator',approval_source:'ui_operator'})});
    lastRepairResult=d;
    q('repairActionResult').textContent=JSON.stringify(d,null,2);
    let v=d?.verification||{};
    if(v.message){
        q('repairActionResult').textContent+='\n\nPOST-ACTION VERIFICATION:\n'+v.message;
    }
    if(d?.ok){
        toast('Repair action applied and verified.');
        buildRepairActionPlan();
    }else{
        toast('Repair action failed, was blocked, or verification failed.');
    }
}
function sendRepairActionPlanToMission(){
    if(!lastRepairPlan){
        toast('Build a repair action plan first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this Kayock User-Approved Repair Bay Action Plan.

This is the first action mode. Actions require user confirmation and write repair logs.

Summary:
Actions: ${lastRepairPlan.summary.actions}
Available: ${lastRepairPlan.summary.available}
Blocked: ${lastRepairPlan.summary.blocked}
Low risk: ${lastRepairPlan.summary.low_risk}

Plan Report:
${lastRepairPlan.exported?.markdown||'No exported plan path'}

Safety Rules:
${(lastRepairPlan.rules||[]).map(x=>'- '+x).join('\n')}

Actions:
${(lastRepairPlan.actions||[]).map(a=>`${a.available?'AVAILABLE':'BLOCKED'} — ${a.title}
ID: ${a.id}
Risk: ${a.risk}
Reason: ${a.reason}
Writes:
${(a.writes||[]).map(x=>'- '+x).join('\n')||'- none'}
Description: ${a.description}`).join('\n\n')}

Please identify:
1. Whether these actions are safe enough for first Repair Bay action mode
2. Which action should be tested first
3. Any action that should remain blocked
4. Whether more guardrails are needed before expanding Repair Bay.`;
    toast('Repair action plan sent to Mission Console.');
}

let lastModelTruth=null;
async function runModelDuplicateTruth(){
    q('modelTruthStatus').textContent='Running model duplicate truth check...';
    let d=await api('/api/models/duplicates',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:true})});
    if(!d){
        q('modelTruthStatus').textContent='Model duplicate truth check failed: no response.';
        return;
    }
    lastModelTruth=d;
    let s=d.summary||{};
    q('modelTruthStatus').textContent=`Model Duplicate Truth Check complete.
Physical files: ${s.physical_model_files}
Unique model keys: ${s.unique_model_keys}
Skipped alias dirs: ${s.skipped_alias_dirs}
True duplicate groups: ${s.true_duplicate_groups}
True duplicate copies: ${s.true_duplicate_copies}
Estimated duplicate space: ${s.estimated_true_duplicate_bytes_human}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('modelTruthDashboard').innerHTML=`<div class=modelgrid>
        <div class=modelmetric><div class=label>Physical Files</div><div class=value>${s.physical_model_files||0}</div></div>
        <div class=modelmetric><div class=label>Unique Models</div><div class=value>${s.unique_model_keys||0}</div></div>
        <div class=modelmetric><div class=label>Alias Dirs</div><div class=value>${s.skipped_alias_dirs||0}</div></div>
        <div class=modelmetric><div class=label>True Dup Groups</div><div class=value>${s.true_duplicate_groups||0}</div></div>
        <div class=modelmetric><div class=label>True Dup Copies</div><div class=value>${s.true_duplicate_copies||0}</div></div>
    </div><div class=status>Estimated true duplicate space: ${esc(s.estimated_true_duplicate_bytes_human||'0 B')}</div>`;
    q('modelCleanupPlan').innerHTML=(d.cleanup_plan||[]).map(p=>`<div class="modelrow ${esc(p.priority||'info')}"><b>${esc((p.priority||'info').toUpperCase())}: ${esc(p.action||'')}</b>
<div>${esc(p.reason||'')}</div>
${p.estimated_space_recoverable_human?`<div class=small>Estimated recoverable: ${esc(p.estimated_space_recoverable_human)}</div>`:''}</div>`).join('');
    let parts=[];
    if((d.skipped_alias_dirs||[]).length){
        parts.push('<h4>Folder aliases skipped</h4>'+d.skipped_alias_dirs.map(x=>`<div class="modelrow info"><b>${esc(x.path)}</b><div class=small>Alias of: ${esc(x.alias_of||'')}</div></div>`).join(''));
    }
    if((d.true_duplicates||[]).length){
        parts.push('<h4>Confirmed duplicate candidates</h4>'+d.true_duplicates.map(g=>`<div class="modelrow review"><b>${esc(g.name)} — ${esc(g.size_human||'')}</b><div>Suggested keep: ${esc(g.kept_suggestion?.path||'')}</div><div class=small>${(g.duplicate_candidates||[]).map(c=>esc(c.path)).join('<br>')}</div></div>`).join(''));
    }else{
        parts.push('<div class="modelrow safe"><b>No confirmed duplicate files</b><div>After canonical folder and physical path detection, no true duplicate GGUF files require deletion planning.</div></div>');
    }
    q('modelTruthDetails').innerHTML=parts.join('');
    toast('Model duplicate truth check complete.');
}
function sendModelDuplicateTruthToMission(){
    if(!lastModelTruth){
        toast('Run model duplicate truth check first.');
        return;
    }
    let s=lastModelTruth.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Model Duplicate Truth Check and cleanup plan.

This was report-only. It did not delete, move, rename, or modify model files.

Summary:
Tracked model dirs: ${s.tracked_model_dirs}
Existing model dirs: ${s.existing_model_dirs}
Scanned canonical dirs: ${s.scanned_canonical_dirs}
Skipped alias dirs: ${s.skipped_alias_dirs}
Raw scan models: ${s.raw_scan_models}
Physical model files: ${s.physical_model_files}
Unique model keys: ${s.unique_model_keys}
True duplicate groups: ${s.true_duplicate_groups}
True duplicate copies: ${s.true_duplicate_copies}
Estimated duplicate space: ${s.estimated_true_duplicate_bytes_human}
Scan errors: ${s.scan_errors}

Report Path:
${lastModelTruth.exported?.markdown||'No exported markdown path'}

Cleanup Plan:
${(lastModelTruth.cleanup_plan||[]).map(p=>`${(p.priority||'info').toUpperCase()} — ${p.action}
${p.reason}
${p.estimated_space_recoverable_human?`Estimated recoverable: ${p.estimated_space_recoverable_human}`:''}`).join('\n\n')}

Please identify:
1. Whether duplicate detection is now trustworthy
2. Whether Models/models were aliases or true duplicates
3. Whether any cleanup action is safe to add later
4. What the first user-approved cleanup action should be
5. Whether Repair Bay can proceed to approved actions after this.`;
    toast('Model cleanup plan sent to Mission Console.');
}

let lastPortableReadiness=null;
async function runPortableReadiness(){
    q('portableStatus').textContent='Running runtime lock and portable readiness report...';
    let d=await api('/api/portable/readiness',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:true})});
    if(!d){
        q('portableStatus').textContent='Portable readiness failed: no response.';
        return;
    }
    lastPortableReadiness=d;
    let s=d.summary||{};
    q('portableStatus').textContent=`Portable Readiness complete.
Score: ${s.score}/100
Readiness: ${s.readiness}
Runtime locked: ${s.runtime_locked}
Blockers: ${s.blockers}
Warnings: ${s.warnings}
Unique GGUF models: ${s.unique_gguf_models}
Duplicate GGUF copies: ${s.duplicate_gguf_copies}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('portableDashboard').innerHTML=`<div class=portablegrid>
        <div class=portablemetric><div class=label>Score</div><div class=value>${s.score||0}</div></div>
        <div class=portablemetric><div class=label>Blockers</div><div class=value>${s.blockers||0}</div></div>
        <div class=portablemetric><div class=label>Warnings</div><div class=value>${s.warnings||0}</div></div>
        <div class=portablemetric><div class=label>Runtime Lock</div><div class=value>${s.runtime_locked?'YES':'NO'}</div></div>
        <div class=portablemetric><div class=label>Unique Models</div><div class=value>${s.unique_gguf_models||0}</div></div>
        <div class=portablemetric><div class=label>Duplicates</div><div class=value>${s.duplicate_gguf_copies||0}</div></div>
        <div class=portablemetric><div class=label>Optional Tools</div><div class=value>${s.optional_tools_available||0}/${s.optional_tools_total||0}</div></div>
    </div><div class=status>${esc(s.readiness||'')}</div>`;
    let bw=[];
    if((d.blockers||[]).length){
        bw.push('<h4>Blockers</h4>'+d.blockers.map(b=>`<div class="portrow fail"><b>${esc(b.name)}</b><div>${esc(b.message||'')}</div></div>`).join(''));
    }else{
        bw.push('<div class="portrow pass"><b>No blockers</b><div>No USB portability blockers found for current web bridge workflows.</div></div>');
    }
    if((d.warnings||[]).length){
        bw.push('<h4>Warnings</h4>'+d.warnings.map(w=>`<div class="portrow warn"><b>${esc(w.name)}</b><div>${esc(w.message||'')}</div></div>`).join(''));
    }
    q('portableBlockers').innerHTML=bw.join('');
    q('portableDetails').innerHTML=(d.checks||[]).map(c=>{
        let cls=c.ok?'pass':(c.blocker?'fail':'warn');
        let status=c.ok?'PASS':(c.blocker?'BLOCKER':'WARNING');
        return `<div class="portrow ${cls}"><b>${status} — ${esc(c.name)}</b>
<div>${esc(c.message||'')}</div>
<div class=small>Weight: ${c.weight} | Blocker: ${c.blocker} | Warning: ${c.warning}</div></div>`;
    }).join('');
    toast('Portable readiness complete.');
}
function sendPortableReadinessToMission(){
    if(!lastPortableReadiness){
        toast('Run portable readiness first.');
        return;
    }
    let s=lastPortableReadiness.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Runtime Lock + Portable Readiness report.

This was report-only. It did not install, repair, delete, or modify files.

Summary:
Portable readiness score: ${s.score}/100
Readiness: ${s.readiness}
Runtime locked: ${s.runtime_locked}
Current Python: ${s.current_python}
Expected Python: ${s.expected_python}
Blockers: ${s.blockers}
Warnings: ${s.warnings}
GGUF files: ${s.gguf_files}
Unique GGUF models: ${s.unique_gguf_models}
Duplicate GGUF copies: ${s.duplicate_gguf_copies}
Optional tools: ${s.optional_tools_available}/${s.optional_tools_total}

Report Path:
${lastPortableReadiness.exported?.markdown||'No exported markdown path'}

Checks:
${(lastPortableReadiness.checks||[]).map(c=>`${c.ok?'PASS':(c.blocker?'BLOCKER':'WARNING')} — ${c.name}
${c.message}`).join('\n\n')}

Please identify:
1. USB workstation readiness
2. Remaining portability blockers
3. Duplicate model/folder cleanup recommendations
4. Optional dependency priorities
5. Whether we are ready to begin user-approved Repair Bay actions.`;
    toast('Portable readiness sent to Mission Console.');
}

let lastEnvVerification=null;
async function runEnvVerification(){
    q('envStatus').textContent='Running report-only environment verification...';
    let d=await api('/api/env/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:true})});
    if(!d){
        q('envStatus').textContent='Environment verification failed: no response.';
        return;
    }
    lastEnvVerification=d;
    let s=d.summary||{};
    q('envStatus').textContent=`Environment Verification complete.
Passed: ${s.passed}/${s.checks}
Problems: ${s.problems}
Optional tools: ${s.optional_tools_available}/${s.optional_tools_total}
GGUF models: ${s.gguf_models}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('envDashboard').innerHTML=`<div class=envgrid>
        <div class=envmetric><div class=label>Checks</div><div class=value>${s.checks||0}</div></div>
        <div class=envmetric><div class=label>Passed</div><div class=value>${s.passed||0}</div></div>
        <div class=envmetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=envmetric><div class=label>Optional Tools</div><div class=value>${s.optional_tools_available||0}/${s.optional_tools_total||0}</div></div>
        <div class=envmetric><div class=label>GGUF Models</div><div class=value>${s.gguf_models||0}</div></div>
    </div>`;
    q('envDetails').innerHTML=(d.checks||[]).map(c=>{
        let cls=c.ok?'pass':(c.optional?'optional':'fail');
        let status=c.ok?'PASS':(c.optional?'OPTIONAL':'FAIL');
        return `<div class="envrow ${cls}"><b>${status} — ${esc(c.name)}</b>
<div>${esc(c.message||'')}</div>
<div class=small>Severity: ${esc(c.severity||'info')} | Optional: ${c.optional}</div></div>`;
    }).join('');
    toast('Environment verification complete.');
}
function sendEnvVerificationToMission(){
    if(!lastEnvVerification){
        toast('Run environment verification first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this Kayock Environment + Dependency Verification report.

This was report-only. It did not install packages, update dependencies, edit files, or run repair actions.

Summary:
Checks: ${lastEnvVerification.summary.checks}
Passed: ${lastEnvVerification.summary.passed}
Problems: ${lastEnvVerification.summary.problems}
Optional tools: ${lastEnvVerification.summary.optional_tools_available}/${lastEnvVerification.summary.optional_tools_total}
GGUF models: ${lastEnvVerification.summary.gguf_models}

Report Path:
${lastEnvVerification.exported?.markdown||'No exported markdown path'}

Checks:
${(lastEnvVerification.checks||[]).map(c=>`${c.ok?'PASS':(c.optional?'OPTIONAL':'FAIL')} — ${c.name}
${c.message}`).join('\n\n')}

Please identify:
1. Environment readiness
2. Missing optional tools worth installing later
3. Unsafe assumptions
4. Dependency risks
5. Next Repair Bay verification feature to add before approved actions.`;
    toast('Environment report sent to Mission Console.');
}

let lastBuildVerification=null;
async function runBuildVerification(){
    q('buildStatus').textContent='Running report-only build verification...';
    let d=await api('/api/build/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:true})});
    if(!d){
        q('buildStatus').textContent='Build verification failed: no response.';
        return;
    }
    lastBuildVerification=d;
    let s=d.summary||{};
    q('buildStatus').textContent=`Build Verification Lite complete.
Passed: ${s.passed}/${s.checks}
Problems: ${s.problems}
Python files: ${s.python_files}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('buildDashboard').innerHTML=`<div class=buildgrid>
        <div class=buildmetric><div class=label>Checks</div><div class=value>${s.checks||0}</div></div>
        <div class=buildmetric><div class=label>Passed</div><div class=value>${s.passed||0}</div></div>
        <div class=buildmetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=buildmetric><div class=label>Python Files</div><div class=value>${s.python_files||0}</div></div>
    </div>`;
    q('buildDetails').innerHTML=(d.checks||[]).map(c=>`<div class="checkrow ${c.ok?'pass':'fail'}"><b>${c.ok?'PASS':'FAIL'} — ${esc(c.name)}</b>
<div>${esc(c.message||'')}</div>
<div class=small>Severity: ${esc(c.severity||'info')}</div></div>`).join('');
    toast('Build verification complete.');
}
function sendBuildVerificationToMission(){
    if(!lastBuildVerification){
        toast('Run build verification first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this Kayock Build Verification Lite report.

This was report-only. It did not install packages, edit files, or run repair actions.

Summary:
Checks: ${lastBuildVerification.summary.checks}
Passed: ${lastBuildVerification.summary.passed}
Problems: ${lastBuildVerification.summary.problems}
Python files checked: ${lastBuildVerification.summary.python_files}

Report Path:
${lastBuildVerification.exported?.markdown||'No exported markdown path'}

Checks:
${(lastBuildVerification.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.name}
${c.message}`).join('\n\n')}

Please identify:
1. Build readiness
2. Any unsafe assumptions
3. Missing checks
4. Next Repair Bay feature to add
5. Whether this should stay report-only or gain a user-approved action.`;
    toast('Build verification sent to Mission Console.');
}

let projectDocsStatusData=null;
async function refreshProjectDocsStatus(){
    let d=await api('/api/project_docs/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    if(!d?.ok){
        q('docsStatus').textContent=d?.message||'Docs status failed.';
        return;
    }
    projectDocsStatusData=d;
    let s=d.summary||{};
    q('docsStatus').innerHTML=`<div class=docstatusgrid>
        <div class=docstat><div class=label>Tracked Docs</div><div class=value>${s.docs||0}</div></div>
        <div class=docstat><div class=label>Present</div><div class=value>${s.present||0}</div></div>
        <div class=docstat><div class=label>Valid</div><div class=value>${s.valid||0}</div></div>
        <div class=docstat><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=docstat><div class=label>Backups</div><div class=value>${s.backup_count||0}</div></div>
    </div>
    ${(d.docs||[]).map(x=>`<div class="docrow ${x.exists&&x.valid?'good':'bad'}"><b>${esc(x.label)}</b>
<div class=small>${esc(x.relative||x.path)}</div>
<div class=small>Exists: ${x.exists} | Valid: ${x.valid} | Size: ${x.size} | Modified: ${esc(x.modified||'')}</div>
<div>${esc(x.message||'')}</div></div>`).join('')}`;
    toast('Project docs status refreshed.');
}
async function loadGeneratedFileToPreview(path){
    let d=await api('/api/generated/read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path})});
    if(d?.ok){
        generatedPreviewData={target:d.path,content:d.content,exists:true};
        q('generatedPreview').textContent=d.content||'';
        toast('Generated file loaded into preview.');
    }else{
        q('generatedPreview').textContent=d?.message||'Could not load generated file.';
    }
}
function loadRootManifestFile(){
    loadGeneratedFileToPreview('manifest.json');
}
function loadDepartmentReadmeFile(){
    loadGeneratedFileToPreview('Departments/Engineering/README.md');
}
function sendDocsStatusToMission(){
    if(!projectDocsStatusData){
        toast('Refresh docs status first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this Kayock Project Docs status report.

Summary:
Tracked docs: ${projectDocsStatusData.summary.docs}
Present: ${projectDocsStatusData.summary.present}
Valid: ${projectDocsStatusData.summary.valid}
Problems: ${projectDocsStatusData.summary.problems}
Backups: ${projectDocsStatusData.summary.backup_count}

Docs:
${(projectDocsStatusData.docs||[]).map(x=>`${x.label}
Path: ${x.relative||x.path}
Exists: ${x.exists}
Valid: ${x.valid}
Size: ${x.size}
Modified: ${x.modified}
Message: ${x.message}`).join('\n\n')}

Please identify missing docs, stale docs, and the best next documentation/build step.`;
    toast('Docs status sent to Mission Console.');
}

let generatedPreviewData=null;
async function previewRootManifest(){
    try{
        let d=await api('/api/generate/root_manifest/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
        if(d?.ok){
            generatedPreviewData=d;
            q('rootManifestStatus').textContent=`Preview target: ${d.target}
Already exists: ${d.exists}`;
            q('generatedPreview').textContent=d.content||'';
            toast('Root manifest preview generated.');
        }else{
            q('rootManifestStatus').textContent=d?.message||'Preview failed.';
        }
    }catch(e){
        q('rootManifestStatus').textContent='Preview failed: '+e;
    }
}
async function applyRootManifest(){
    let ok=confirm('Write root manifest now? Existing file will be backed up first.');
    if(!ok)return;
    let d=await api('/api/generate/root_manifest/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    if(d?.ok){
        q('rootManifestStatus').textContent=`${d.message}
Target: ${d.target}
Backup: ${d.backup||'none'}
Validation problems: ${(d.validation?.problems||[]).length}`;
        refreshProjectDocsStatus();
        toast('Root manifest written safely.');
    }else{
        q('rootManifestStatus').textContent=d?.message||'Write failed.';
    }
}
async function previewDepartmentReadme(){
    let key=q('readmeDeptKey').value||'engineering';
    let d=await api('/api/generate/department_readme/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});
    if(d?.ok){
        generatedPreviewData=d;
        q('readmeStatus').textContent=`Preview target: ${d.target}
Already exists: ${d.exists}`;
        q('generatedPreview').textContent=d.content||'';
        toast('Department README preview generated.');
    }else{
        q('readmeStatus').textContent=d?.message||'README preview failed.';
    }
}
async function applyDepartmentReadme(){
    let ok=confirm('Write department README now? Existing file will be backed up first.');
    if(!ok)return;
    let key=q('readmeDeptKey').value||'engineering';
    let d=await api('/api/generate/department_readme/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});
    if(d?.ok){
        q('readmeStatus').textContent=`${d.message}
Target: ${d.target}
Backup: ${d.backup||'none'}`;
        refreshProjectDocsStatus();
        toast('Department README written safely.');
    }else{
        q('readmeStatus').textContent=d?.message||'README write failed.';
    }
}
function sendGeneratedPreviewToMission(){
    if(!generatedPreviewData){
        toast('Generate a preview first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this generated Kayock project documentation before I rely on it.

Target:
${generatedPreviewData.target}

Content:
${generatedPreviewData.content}

Check:
1. Accuracy
2. Missing sections
3. Safety concerns
4. Better wording
5. Whether it should be written or revised first.`;
    toast('Generated preview sent to Mission Console.');
}

let loadedScanReport=null;
function useLastScanReportPath(){
    if(!lastScanReport?.exported){
        toast('No exported scan report yet. Use Scan + Export Report first.');
        return;
    }
    q('scanReportPath').value=lastScanReport.exported.json||lastScanReport.exported.markdown||'';
    toast('Last exported scan report path loaded.');
}
async function loadScanReport(){
    let path=q('scanReportPath').value.trim();
    if(!path){
        toast('Enter a report path first.');
        return;
    }
    q('scanReportStatus').textContent='Loading scan report...';
    let d=await api('/api/scan/read_report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,max_read:parseInt(q('scanReportMax').value||'120000')})});
    if(!d?.ok){
        q('scanReportStatus').textContent=d?.message||'Could not load report.';
        return;
    }
    loadedScanReport=d;
    let s=d.summary||{};
    let counts=s.counts||{};
    q('scanReportStatus').textContent=`Loaded: ${d.relative}
Size: ${d.size} bytes
Kind: ${d.kind}
Truncated: ${d.truncated}
Target: ${s.target||'n/a'}
Files: ${counts.files??'n/a'}
Folders: ${counts.folders??'n/a'}
Manifests: ${counts.manifests??s.manifests??'n/a'}
Errors: ${counts.errors??s.errors??'n/a'}`;
    q('scanReportPreview').textContent=d.content||'No content.';
    toast('Scan report loaded.');
}
function loadedScanReportMissionText(){
    if(!loadedScanReport)return '';
    let s=loadedScanReport.summary||{};
    let counts=s.counts||{};
    return `Kayock Loaded Scan Report

Path:
${loadedScanReport.path}

Relative:
${loadedScanReport.relative}

Created:
${s.created||'Unknown'}

Target:
${s.target||'Unknown'}

Counts:
Files: ${counts.files??'Unknown'}
Folders: ${counts.folders??'Unknown'}
Manifests: ${counts.manifests??'Unknown'}
Python: ${counts.python??'Unknown'}
JSON: ${counts.json??'Unknown'}
Markdown: ${counts.markdown??'Unknown'}
Code: ${counts.code??'Unknown'}
Large skipped: ${counts.large_skipped??'Unknown'}
Errors: ${counts.errors??'Unknown'}

Report Preview:
${loadedScanReport.content||'No content.'}`;
}
function sendLoadedScanReportToMission(){
    if(!loadedScanReport){
        toast('Load a scan report first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this loaded Kayock scan report.

Analyze:
1. Folder structure
2. Important files
3. Missing manifests
4. Repair Bay risks
5. Module ownership
6. Suggested next cleanup/build step

${loadedScanReportMissionText()}`;
    toast('Loaded scan report sent to Mission Console input.');
}

async function scanFolder(exportReport){
    let payload={
        path:q('scanPath').value||'',
        max_files:parseInt(q('scanMaxFiles').value||'3000'),
        max_bytes:parseInt(q('scanMaxBytes').value||'1048576'),
        export:!!exportReport
    };
    q('scanStatus').textContent='Scanning read-only...';
    let d=await api('/api/scan/folder',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!d?.ok){
        q('scanStatus').textContent=d?.message||'Scan failed.';
        return;
    }
    lastScanReport=d;
    let c=d.counts||{};
    q('scanStatus').textContent=`Scanned: ${d.target}
Read-only: ${d.read_only}
Files: ${c.files}
Folders: ${c.folders}
Manifests: ${c.manifests}
${d.exported?`Exported Markdown: ${d.exported.markdown}
Exported JSON: ${d.exported.json}`:''}`;
    if(d.exported&&q('scanReportPath'))q('scanReportPath').value=d.exported.json||d.exported.markdown||'';
    q('scanResults').innerHTML=`<div class=scanbox>
        <div class=scanmetric><div class=label>Files</div><div class=value>${c.files||0}</div></div>
        <div class=scanmetric><div class=label>Folders</div><div class=value>${c.folders||0}</div></div>
        <div class=scanmetric><div class=label>Manifests</div><div class=value>${c.manifests||0}</div></div>
        <div class=scanmetric><div class=label>Python</div><div class=value>${c.python||0}</div></div>
        <div class=scanmetric><div class=label>JSON</div><div class=value>${c.json||0}</div></div>
        <div class=scanmetric><div class=label>Markdown</div><div class=value>${c.markdown||0}</div></div>
        <div class=scanmetric><div class=label>Code</div><div class=value>${c.code||0}</div></div>
        <div class=scanmetric><div class=label>Large Skipped</div><div class=value>${c.large_skipped||0}</div></div>
        <div class=scanmetric><div class=label>Errors</div><div class=value>${c.errors||0}</div></div>
    </div>
    <h3>Manifests</h3><div class=scanlist>${esc((d.manifests||[]).map(x=>`${x.relative} (${x.size} bytes)`).join('\n')||'No manifests found.')}</div>
    <h3>Sample Files</h3><div class=scanlist>${esc((d.samples||[]).slice(0,100).map(x=>`[${x.kind}] ${x.relative} (${x.size} bytes)${x.large?' LARGE':''}`).join('\n')||'No sample files.')}</div>`;
    toast(exportReport?'Folder scan exported.':'Folder scan complete.');
}
function sendLastScanToMission(){
    if(!lastScanReport){
        toast('Run a scan first.');
        return;
    }
    let path=lastScanReport.exported?.markdown||lastScanReport.exported?.json||'No exported report path. Use Scan + Export Report, then Load Report for full content.';
    go('mission');
    q('input').value=`Please review this Kayock folder scan.

Target:
${lastScanReport.target}

Report Path:
${path}

Summary:
Files: ${lastScanReport.counts.files}
Folders: ${lastScanReport.counts.folders}
Manifests: ${lastScanReport.counts.manifests}
Python: ${lastScanReport.counts.python}
JSON: ${lastScanReport.counts.json}
Markdown: ${lastScanReport.counts.markdown}
Code: ${lastScanReport.counts.code}
Large skipped: ${lastScanReport.counts.large_skipped}
Errors: ${lastScanReport.counts.errors}

Manifests:
${(lastScanReport.manifests||[]).map(x=>x.relative).join('\n')||'None'}

Please identify structure, risks, missing manifests, next cleanup steps, and which department should own follow-up work.`;
    toast('Folder scan sent to Mission Console input.');
}

async function loadExtensions(){
    if(!q('extList'))return;
    try{
        let d=await (await fetch('/api/extensions/list')).json();
        q('extSummary').textContent=`Modules: ${d.count}
Enabled: ${d.enabled}
Valid: ${d.valid}
State file: ${d.state_file}`;
        extDashboardFromData(d);
        q('extList').innerHTML=(d.items||[]).map(x=>{
            let cls=x.enabled?'':'disabledmod';
            let missing=(x.missing&&x.missing.length)?`Missing: ${x.missing.join(', ')}`:'Manifest OK';
            return `<div class="extcard ${cls}"><h4>🧩 ${esc(x.name)} <span class=small>v${esc(x.version)}</span></h4><span class=exttag>${esc(x.kind||'extension')}</span><span class=exttag>${esc(x.status||'UNKNOWN')}</span><span class=exttag>${x.enabled?'ENABLED':'DISABLED'}</span><div class=extmeta>${esc(x.description||'')}\nOfficer: ${esc(extOfficerText(x.officer))}\nKey: ${esc(x.key)}\n${esc(missing)}\nManifest: ${esc(x.manifest)}\nFolder: ${esc(x.folder)}</div><div class=extactions><button onclick="toggleExtension('${js(x.key)}',${x.enabled?'false':'true'})">${x.enabled?'Disable':'Enable'}</button><button onclick="suggestManifestFix('${js(x.key)}','${js(x.manifest)}')">Suggest Fix</button><button onclick="sendExtensionToMission('${js(x.key)}')">Send to Mission</button></div></div>`
        }).join('')||'No extension manifests found yet.';
    }catch(e){
        q('extSummary').textContent='Extension list failed: '+e;
    }
}
async function toggleExtension(key,enabled){
    let d=await api('/api/extensions/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,enabled})});
    if(d?.ok)loadExtensions();
}
async function validateExtensions(){
    let d=await api('/api/extensions/validate');
    if(d?.ok){
        q('extSummary').textContent=`${d.message}
Checked: ${d.checked}
Valid: ${d.valid}
Problems: ${d.problems.length}`;
        loadExtensions();
        if(d.problems?.length){
            q('extList').innerHTML=d.problems.map(p=>`<div class=extcard><h4>⚠ ${esc(p.name)}</h4><div class=extmeta>Key: ${esc(p.key)}\nMissing: ${esc((p.missing||[]).join(', '))}\nManifest: ${esc(p.manifest)}</div><div class=extactions><button onclick="suggestManifestFix('${js(p.key)}','${js(p.manifest)}')">Suggest Fix</button></div></div>`).join('');
        }
    }
}
async function createSampleExtension(){
    let d=await api('/api/extensions/sample');
    if(d?.ok){
        toast(d.message);
        loadExtensions();
    }
}
function sendExtensionToMission(key){
    go('mission');
    q('input').value=`Please review this Kayock extension/module and suggest any manifest, dependency, safety, or architecture improvements.

Extension key:
${key}

Focus on:
1. Manifest quality
2. Safety
3. Dependencies
4. How it should appear in the Command Bridge
5. Whether it belongs as a department, extension, or utility`;
    toast('Extension review request sent to Mission Console input.');
}

async function loadBridge(){
    try{
        let d=await (await fetch('/api/bridge/feed')).json();
        let build=(d.builder_passed!==null&&d.builder_passed!==undefined&&d.builder_total!==null&&d.builder_total!==undefined)?`${d.builder_passed}/${d.builder_total} passed`:(d.builder_ok===true?'OK':(d.builder_found?'Report found':'No report'));
        let ev=d.latest_event||{};
        let evMeta=[ev.time,ev.source,ev.severity].filter(Boolean).join(' • ');
        let msg=d.latest_event_message||ev.message||'No recent Bridge event found.';
        q('bridgeLive').innerHTML=`<div class=livegrid>
            <div class=livebox><div class=label>Kernel</div><div class=value>${esc(d.kernel_status||'UNKNOWN')}</div></div>
            <div class=livebox><div class=label>Departments</div><div class=value>${esc(d.departments_online)}/${esc(d.departments)}</div></div>
            <div class=livebox><div class=label>Runtime Packages</div><div class=value>${esc(d.runtime_packages??'—')}</div></div>
            <div class=livebox><div class=label>Builder</div><div class=value>${esc(build)}</div></div>
        </div><div class=eventbox><div class=time>${esc(evMeta||'Latest Event')}</div>${esc(msg)}</div>`;
        let cards=(d.department_cards||[]).map(x=>{
            let cls=String(x.status||'').toLowerCase();
            let badge=(['online','ok','ready','active','healthy','pass','passed'].includes(cls))?'ok':(['warn','warning','degraded','check','staged'].includes(cls)?'warn':'bad');
            let officer=x.officer?`<div class=fleetstatus>${esc(x.officer)}</div>`:'';
            let first=String(x.name||'').split(' ')[0];
            let icon=({Command:'🚀',Academy:'🎓',Engineering:'⚙️',Artificial:'🤖',Iron:'📚',Creative:'🎨',Repair:'🔧',PromptSmith:'✍️',Novel:'📖'}[first]||'◇');
            let cardcls=badge==='ok'?'online':(badge==='warn'?'staged':'missing');
            return `<div class="fleetcard ${cardcls}"><div class=depticon>${icon}</div><h4>${esc(x.name)}</h4>${officer}<div class="fleetstatus ${badge}">${esc(x.status||'UNKNOWN')}</div></div>`
        }).join('');
        q('deptcards').innerHTML=cards||'<div class=status>No department cards found yet. Refresh after running the Builder.</div>';
    }catch(e){
        if(q('bridgeLive'))q('bridgeLive').textContent='Bridge Feed unavailable: '+e;
        if(q('deptcards'))q('deptcards').textContent='Department feed unavailable.';
    }
}

async function loadFoxSentryIncidents(){
    let filter=q('sentryIncidentFilter')?.value||'all';
    let chain=q('sentryChainStatus');
    let list=q('sentryIncidentList');
    if(!chain||!list){return;}
    chain.className='sentrychain';
    chain.textContent='CHECKING CHAIN // Read-only verification pending.';
    list.textContent='Loading incidents...';
    let d=await api(`/api/security/incidents?kind=${encodeURIComponent(filter)}&limit=100`);
    let verification=d?.verification||{};
    let alert=d?.chain_alert||{};
    let valid=d?.chain_valid===true;
    let failureDetail=d?.read_error
        ||((verification.failures||[]).map(x=>`Line ${x.line}: ${x.reason}`).join('\n'))
        ||alert.message
        ||'Unknown verification failure.';
    let alertMessage=alert.message||'Fox Sentry audit chain verification failed closed.';
    let criticalDetail=(
        failureDetail
        &&failureDetail!==alertMessage
    )?`\nDetails:\n${esc(failureDetail)}`:'';
    chain.className=valid?'sentrychain':'sentrychain bad';
    chain.textContent=valid
        ?`CHAIN VERIFIED // ${verification.event_count||0} append-only event(s).\nFinal hash: ${verification.final_hash||'(empty chain)'}`
        :`CRITICAL // AUDIT CHAIN INVALID // Events below are UNTRUSTED.\n${failureDetail}`;
    let criticalCard=alert.active===true
        ?`<div class="sentryincident live"><h4>CRITICAL // audit_chain_failure // UNTRUSTED</h4><div class=sentrymeta>${esc(alertMessage)}${criticalDetail}\nNo synthetic event was appended to the untrusted chain.</div></div>`
        :'';
    let events=d?.events||[];
    if(!d?.log_exists){
        list.innerHTML=criticalCard+'<div class="sentryincident test"><h4>No audit log yet</h4><div class=sentrymeta>Run Trip Sentry or enter the Engineering Airlock to create the first event.</div></div>';
        return;
    }
    if(!events.length){
        list.innerHTML=criticalCard+'<div class=sentryincident><h4>No matching incidents</h4><div class=sentrymeta>Choose another filter or generate a new event.</div></div>';
        return;
    }
    list.innerHTML=criticalCard+events.map(event=>{
        let test=event.test_event===true;
        let mode=test?'TEST':'OPERATIONAL';
        let severity=String(event.severity||(test?'TEST':'LEGACY/UNCLASSIFIED')).toUpperCase();
        let incidentKind=String(event.incident_kind||(test?'trip_sentry_test':'legacy_unclassified'));
        let attempt=event.attempt_count??(test?1:'n/a');
        let context=String(event.context_status||(test?'test':'legacy/not_recorded'));
        let trust=valid?'CHAINED':'UNTRUSTED';
        let cls=test?'test':'live';
        return `<div class="sentryincident ${cls}"><h4>${esc(severity)} // ${esc(incidentKind)} // ${esc(String(event.decision||'').toUpperCase())} // ${esc(trust)}</h4><div class=sentrymeta>${esc(event.timestamp||'unknown time')}
Mode: ${esc(mode)}
Severity: ${esc(severity)}
Incident Kind: ${esc(incidentKind)}
Attempt Count: ${esc(attempt)}
Context Status: ${esc(context)}
Actor: ${esc(event.actor||'')}
Object: ${esc(event.object||'')}
Action: ${esc(event.action||'')}
Reason: ${esc(event.reason||'')}
Policy: ${esc(event.policy_source||'')}
Event: ${esc(event.event_id||'')}
Correlation: ${esc(event.correlation_id||'')}
Mission: ${esc(event.mission_id||'')}
Approval: ${esc(event.approval_id||'')}
Receipt: ${esc(event.receipt_id||'')}
Previous hash: ${esc(event.previous_hash||'')}
Event hash: ${esc(event.event_hash||'')}</div></div>`;
    }).join('');
}

async function runTripSentryTest(){
    let ok=window.confirm('Generate one clearly labeled Trip Sentry TEST denial event?\n\nNo access will be granted and no repair will run. The append-only security log and lock file may be created or updated.');
    if(!ok){q('tripSentryStatus').textContent='CANCELLED // No TEST incident was generated.';return;}
    q('tripSentryStatus').textContent='RUNNING TEST // Requesting a verified Fox Sentry receipt...';
    q('tripSentryOmega').className='sentryresult';
    q('tripSentryOmega').textContent='Ω OMEGA PROTOCOL\n\nTEST incident pending verified receipt...';
    let d=await api('/api/security/trip_sentry_test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmation:'TRIP SENTRY TEST',approval_source:'ui_operator'})});
    let receipt=d?.receipt||{};
    let event=receipt?.details?.event||{};
    if(d?.ok&&receipt?.verified===true){
        q('tripSentryStatus').textContent='VERIFIED TEST INCIDENT // Fox Sentry logging and warning path completed without granting access.';
        q('tripSentryOmega').className='sentryresult sentryverified';
        q('tripSentryOmega').textContent=`Ω OMEGA PROTOCOL\nTEST INCIDENT — FOX SENTRY PATH VERIFIED\n\nDENIAL EVENT RECORDED\nNO ACCESS GRANTED\nNO REPAIR EXECUTED\nNO OPERATIONAL FILE CHANGED\n\nEvent: ${event.event_id||'unknown'}\nCorrelation: ${event.correlation_id||'unknown'}\nReceipt: ${receipt.receipt_id||'unknown'}\nLog: ${receipt?.details?.log_path||'unknown'}`;
        await loadFoxSentryIncidents();
        return;
    }
    q('tripSentryStatus').textContent='TEST FAILED CLOSED // No verified security receipt was produced.';
    q('tripSentryOmega').className='sentryresult sentryfailed';
    q('tripSentryOmega').textContent=`Ω OMEGA PROTOCOL\nTEST FAILED CLOSED\n\n${d?.message||'Fox Sentry did not return a verified receipt.'}`;
}

async function refresh(){let s=await (await fetch('/api/status')).json();let lines=[`Root: ${s.root}`,`Kayock Browser: ${s.kayock_browser_found?'found':'missing'}`,`Engine: ${s.engine_found?'found':'missing'}`,`Chat online: ${s.chat_online?'yes':'no'}`,`Active project: ${s.active_project||'None'}`,`Projects: ${s.projects}`,`ComfyUI: ${s.comfy_online?'online':'offline'}`,`Chat models: ${s.chat_models}`,`Library items: ${s.library_items}`,`PDFs: ${s.library_pdfs}`];q('status').textContent=lines.join('\n');q('status2').textContent=lines.join('\n');q('paths').textContent=`Root: ${s.root}\nDrive: ${s.drive_root}\nBrowser: ${s.kayock_browser}\nEngine: ${s.engine}\nProjects: ${s.projects_root}`;q('am').textContent=s.chat_model_name||'None';activeProfileId=String(s.chat_profile_id||'');if(s.active_mission_image?.attached&&!pendingMissionImage){let meta=s.active_mission_image;activeMissionImage={...missionImageMetadata({name:meta.filename,type:meta.mime,size:meta.size_bytes,width:meta.width,height:meta.height,sha256:meta.sha256}),preview_url:activeMissionImage?.sha256===meta.sha256?(activeMissionImage.preview_url||''):''};renderMissionImage()}else if(!s.active_mission_image?.attached&&!pendingMissionImage){activeMissionImage=null;renderMissionImage()}q('ap').textContent=s.active_professor_name||'Agent Fox';q('mtitle').textContent=s.active_professor_name||'Agent Fox';q('apro').textContent=s.active_project||'None';q('rt').textContent=s.chat_online?'ONLINE':'OFFLINE';q('cpu').textContent=s.cpu_percent!==null?`${s.cpu_percent}%`:'n/a';q('ram').textContent=s.ram_used_gb!==null?`${s.ram_used_gb}/${s.ram_total_gb} GB (${s.ram_percent}%)`:'n/a';q('ramm').style.width=s.ram_percent!==null?`${s.ram_percent}%`:'0%';q('quick').innerHTML=`<span class="pill ${s.engine_found?'ok':'bad'}">Engine ${s.engine_found?'Found':'Missing'}</span><br><span class="pill ${s.chat_online?'ok':'warn'}">Chat ${s.chat_online?'Online':'Offline'}</span><br><span class="pill ${s.comfy_online?'ok':'warn'}">ComfyUI ${s.comfy_online?'Online':'Offline'}</span>`}
initDepartmentNav();setupMissionImageDrop();loadModels();loadProf();loadProjects();loadMemory();loadBridge();loadRecoveryDashboard();loadFoxSentryIncidents();refresh();setInterval(refresh,8000);setInterval(loadBridge,10000)
