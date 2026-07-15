
let apiCalls=[];
async function api(url,opt){apiCalls.push({url,opt});return {ok:true,message:'started'}}
let log=[];
function logline(...args){log.push(args)}
function loadMemory(){}
function toast(){}
function esc(value){return String(value).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
const storage={};
global.localStorage={
 getItem:key=>Object.prototype.hasOwnProperty.call(storage,key)?storage[key]:null,
 setItem:(key,value)=>{storage[key]=String(value)}
};
const elements={
 model:{value:'',innerHTML:''},
 modelProfileGrid:{innerHTML:''},
 modelProfileStatus:{textContent:''}
};
function q(id){return elements[id]||null}
let activeProject=null,curLib='',missionData=null,modelCatalog=[],selectedProfileId='';
/* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_START */
const MODEL_PROFILES=[
 {id:'fast_text',label:'⚡ Fast Text',model:'Qwen3.5-4B-Q4_K_M.gguf',best:'Quick questions, short summaries, simple instructions, and casual chat.',speed:'Fastest verified text profile',vision:'No',reasoning:'Off',status:'BENCHMARK SUPPORTED',note:'10.87 median tok/s; exact instruction and length checks passed. Runtime launches with reasoning off and budget 0.',recommended:true},
 {id:'balanced_text',label:'⚖️ Balanced Text',model:'Qwen3.5-9B-Q4_K_M.gguf',best:'Everyday writing, research discussion, longer answers, and general text work.',speed:'Moderate',vision:'No',reasoning:'Off',status:'BENCHMARK SUPPORTED',note:'5.75 median tok/s; exact instruction and length checks passed. Runtime launches with reasoning off and budget 0.',recommended:false},
 {id:'creative_text',label:'🎭 Creative Text',model:'PsyLLM-8B-Q5_K_M.gguf',best:'Fiction, dialogue, poetry, brainstorming, and roleplay.',speed:'Moderate',vision:'No',reasoning:'Off',status:'STABILITY PASSED • QUALITY CHECK PENDING',note:'Stable direct answers with reasoning off and budget 0; creative quality and instruction depth remain pending.',recommended:false},
 {id:'fast_vision',label:'👁️ Fast Vision',model:'Qwen3VL-8B-Instruct-Q4_K_M.gguf',best:'Quick image understanding, screenshots, visible text, and general image questions.',speed:'Fast visual-language profile',vision:'Yes',reasoning:'Current engine behavior',status:'BENCHMARK SUPPORTED',note:'1.56× faster than Q8 in the fixed text benchmark; real image input pending.',recommended:false},
 {id:'quality_vision',label:'🔎 Quality Vision',model:'Qwen3VL-8B-Instruct-Q8_0.gguf',best:'Detailed image analysis, complex scenes, and careful visual reasoning.',speed:'Quality-first / slower',vision:'Yes',reasoning:'Current engine behavior',status:'BENCHMARK SUPPORTED',note:'Current visual-language quality reference; real image input pending.',recommended:false}
];
/* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_END */
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
async function startChat(){let d=await api('/api/chat/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:q('model').value,profile:selectedProfileId||''})}); logline(d?.ok?'sys':'bad','SYSTEM',d?.message||'start failed');loadMemory()}

modelCatalog=[
 {name:'Qwen3.5-4B-Q4_K_M.gguf',path:'Z:\\FOXAI\\Models\\Chat\\Qwen3.5-4B-Q4_K_M.gguf'},
 {name:'Qwen3.5-9B-Q4_K_M.gguf',path:'Z:\\FOXAI\\Models\\Chat\\Qwen3.5-9B-Q4_K_M.gguf'},
 {name:'PsyLLM-8B-Q5_K_M.gguf',path:'Z:\\FOXAI\\Models\\Chat\\PsyLLM-8B-Q5_K_M.gguf'},
 {name:'Qwen3VL-8B-Instruct-Q4_K_M.gguf',path:'Z:\\FOXAI\\Models\\Chat\\Qwen3VL-8B-Instruct-Q4_K_M.gguf'},
 {name:'Qwen3VL-8B-Instruct-Q8_0.gguf',path:'Z:\\FOXAI\\Models\\Chat\\Qwen3VL-8B-Instruct-Q8_0.gguf'}
];
if(MODEL_PROFILES.length!==5)throw new Error('profile count');
selectModelProfile('fast_text');
if(apiCalls.length!==0)throw new Error('card selection called API');
if(elements.model.value!==modelCatalog[0].path)throw new Error('fast text path');
if(!elements.modelProfileStatus.textContent.includes('No engine action has occurred'))throw new Error('operator status');
await startChat();
if(apiCalls.length!==1)throw new Error('explicit start call count');
let payload=JSON.parse(apiCalls[0].opt.body);
if(payload.profile!=='fast_text')throw new Error('fast profile payload');
if(payload.model!==modelCatalog[0].path)throw new Error('fast model payload');
selectModelProfile('quality_vision');
if(apiCalls.length!==1)throw new Error('vision card selection called API');
await startChat();
payload=JSON.parse(apiCalls[1].opt.body);
if(payload.profile!=='quality_vision')throw new Error('vision profile payload');
if(!elements.modelProfileGrid.innerHTML.includes('Runtime launches with reasoning off and budget 0'))throw new Error('runtime note');
console.log('profile_count=PASS');
console.log('selection_no_api=PASS');
console.log('explicit_start_profile_payload=PASS');
console.log('silent_auto_switch_absent=PASS');
console.log('runtime_reasoning_note=PASS');
