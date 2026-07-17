
const calls=[];const logs=[];
function makeClassList(){let values=new Set();return {add:x=>values.add(x),remove:x=>values.delete(x),contains:x=>values.has(x)}}
function makeElement(){return {value:'',textContent:'',src:'',disabled:false,style:{},classList:makeClassList(),children:[],append(...x){this.children.push(...x)},appendChild(x){this.children.push(x)},removeAttribute(k){if(k==='src')this.src=''}}}
const elements={input:makeElement(),imageFile:makeElement(),imagePreview:makeElement(),imagePreviewThumb:makeElement(),imagePreviewMeta:makeElement(),ap:makeElement(),ms:makeElement(),sendChatButton:makeElement(),cancelChatButton:makeElement(),model:makeElement(),toast:makeElement(),imageDrop:makeElement()};elements.ap.textContent='Agent Fox';elements.model.value='Z:/FOXAI/Models/Chat/Qwen3VL-8B-Instruct-Q4_K_M.gguf';
function q(id){return elements[id]||null}
const chat=makeElement();chat.scrollHeight=10;chat.scrollTop=0;
global.document={createElement:()=>makeElement()};
function logline(kind,speaker,text){logs.push([kind,speaker,text])}
function toast(text){logs.push(['toast',text])}
function think(value){calls.push(['think',value])}
function loadMemory(){calls.push(['loadMemory'])}
function refresh(){calls.push(['refresh'])}
function beginStreamLine(kind,speaker){let row=makeElement(),body=makeElement();row.body=body;chat.appendChild(row);return {row,body}}
function api(){throw new Error('api not configured')}
let activeProject=null,curLib='',missionData=null,modelCatalog=[],selectedProfileId='',activeProfileId='',pendingMissionImage=null,chatStreamController=null;

/* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_START */
const MODEL_PROFILES=[
 {id:'fast_text',label:'⚡ Fast Text',model:'Qwen3.5-4B-Q4_K_M.gguf',best:'Quick questions, short summaries, simple instructions, and casual chat.',speed:'Fastest verified text profile',vision:'No',reasoning:'Off',status:'BENCHMARK SUPPORTED',note:'10.87 median tok/s; exact instruction and length checks passed. Runtime launches with reasoning off and budget 0.',recommended:true},
 {id:'balanced_text',label:'⚖️ Balanced Text',model:'Qwen3.5-9B-Q4_K_M.gguf',best:'Everyday writing, research discussion, longer answers, and general text work.',speed:'Moderate',vision:'No',reasoning:'Off',status:'BENCHMARK SUPPORTED',note:'5.75 median tok/s; exact instruction and length checks passed. Runtime launches with reasoning off and budget 0.',recommended:false},
 {id:'creative_text',label:'🎭 Creative Text',model:'PsyLLM-8B-Q5_K_M.gguf',best:'Brainstorming, story hooks, dialogue seeds, poetic fragments, and roleplay ideas.',speed:'Moderate',vision:'No',reasoning:'Off',status:'BRAINSTORMING SUPPORTED • LONG-FORM PENDING',note:'All eight creative responses completed without wrapper or reasoning leaks. Story hooks passed exact constraints; seven tasks missed requested length or structure, so strict long-form work remains pending.',recommended:false},
 {id:'fast_vision',label:'👁️ Fast Vision',model:'Qwen3VL-8B-Instruct-Q4_K_M.gguf',best:'Quick image understanding, screenshots, visible text, and general image questions.',speed:'Fast visual-language profile',vision:'Yes',reasoning:'Current engine behavior',status:'REAL IMAGE INPUT SUPPORTED • BENCHMARK PASSED',note:'Human-reviewed 5/5 real-image suite; 42.58s median and 6.56 tok/s. About 1.65× faster than Q8 with no observed quality loss on this suite.',recommended:false},
 {id:'quality_vision',label:'🔎 Quality Vision',model:'Qwen3VL-8B-Instruct-Q8_0.gguf',best:'Detailed image analysis, complex scenes, and careful visual reasoning.',speed:'Quality-first / slower',vision:'Yes',reasoning:'Current engine behavior',status:'REAL IMAGE INPUT SUPPORTED • BENCHMARK PASSED',note:'Human-reviewed 5/5 real-image suite; 70.38s median and 4.17 tok/s. Higher precision remains available, but this suite did not prove a quality advantage.',recommended:false}
];
/* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_END */
function modelProfileById(id){return MODEL_PROFILES.find(p=>p.id===id)}
/* MISSION_IMAGE_ATTACHMENTS_PHASE1_BROWSER_START */
const MISSION_IMAGE_MAX_BYTES=6*1024*1024;
function activeVisionProfile(){let profile=modelProfileById(activeProfileId);return Boolean(profile&&profile.vision==='Yes')}
function bytesLabel(value){let n=Number(value||0);if(n<1024)return `${n} B`;if(n<1024*1024)return `${(n/1024).toFixed(1)} KB`;return `${(n/1024/1024).toFixed(2)} MB`}
async function sha256Hex(buffer){let digest=await crypto.subtle.digest('SHA-256',buffer);return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('')}
function readFileDataUrl(file){return new Promise((resolve,reject)=>{let reader=new FileReader();reader.onload=()=>resolve(String(reader.result||''));reader.onerror=()=>reject(reader.error||new Error('Image read failed.'));reader.readAsDataURL(file)})}
function readImageDimensions(dataUrl){return new Promise((resolve,reject)=>{let image=new Image();image.onload=()=>resolve({width:image.naturalWidth,height:image.naturalHeight});image.onerror=()=>reject(new Error('Image dimensions could not be read.'));image.src=dataUrl})}
function renderMissionImage(){let box=q('imagePreview');if(!box)return;if(!pendingMissionImage){box.classList.remove('show');q('imagePreviewThumb').removeAttribute('src');q('imagePreviewMeta').textContent='';return}q('imagePreviewThumb').src=pendingMissionImage.data_url;q('imagePreviewMeta').textContent=`${pendingMissionImage.name}\n${pendingMissionImage.type} • ${pendingMissionImage.width}×${pendingMissionImage.height} • ${bytesLabel(pendingMissionImage.size)}\nSHA-256 ${pendingMissionImage.sha256}`;box.classList.add('show')}
function clearMissionImage(){pendingMissionImage=null;let picker=q('imageFile');if(picker)picker.value='';renderMissionImage()}
async function handleMissionImageFiles(files){let file=files&&files[0];if(!file)return;try{if(!['image/png','image/jpeg','image/webp'].includes(file.type))throw new Error('Choose a PNG, JPEG, or WebP image.');if(file.size<1||file.size>MISSION_IMAGE_MAX_BYTES)throw new Error('Image must be larger than 0 bytes and no more than 6 MB.');let buffer=await file.arrayBuffer(),dataUrl=await readFileDataUrl(file),dimensions=await readImageDimensions(dataUrl);if(dimensions.width<1||dimensions.height<1||dimensions.width>8192||dimensions.height>8192)throw new Error('Image dimensions must be between 1 and 8192 pixels.');pendingMissionImage={name:file.name,type:file.type,size:file.size,width:dimensions.width,height:dimensions.height,sha256:await sha256Hex(buffer),data_url:dataUrl};renderMissionImage();toast(`Image ready: ${file.name}. Start a vision profile before sending.`)}catch(error){clearMissionImage();toast(String(error?.message||error));logline('bad','SYSTEM',`Image attachment rejected: ${error?.message||error}`)}}
function missionImagePayload(){if(!pendingMissionImage)return null;return {...pendingMissionImage}}
function logMissionImage(image){if(!image)return;let row=document.createElement('div');row.className='chatimage';let thumb=document.createElement('img');thumb.src=image.data_url;thumb.alt='Attached image';let meta=document.createElement('div');meta.className='chatimagemeta';meta.textContent=`IMAGE ATTACHMENT\n${image.name}\n${image.width}×${image.height} • ${bytesLabel(image.size)}\nSHA-256 ${image.sha256}`;row.append(thumb,meta);chat.appendChild(row);chat.scrollTop=chat.scrollHeight}
function setupMissionImageDrop(){let drop=q('imageDrop');if(!drop)return;['dragenter','dragover'].forEach(name=>drop.addEventListener(name,event=>{event.preventDefault();event.stopPropagation();drop.classList.add('drag')}));['dragleave','drop'].forEach(name=>drop.addEventListener(name,event=>{event.preventDefault();event.stopPropagation();drop.classList.remove('drag')}));drop.addEventListener('drop',event=>handleMissionImageFiles(event.dataTransfer?.files))}
/* MISSION_IMAGE_ATTACHMENTS_PHASE1_BROWSER_END */
function explicitEngineerMessage(text){return /^\s*(?:\/engineer(?:\s+|$)|engineer\s*[:,]\s*\S)/i.test(String(text||''))}
async function requestNonStreamingChat(text,image=null){
 let response=await fetch('/api/chat/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,image})});
 let d=await response.json();
 if(d.answer)logline('fox',d.speaker||q('ap').textContent.toUpperCase(),d.answer);
 if(!d.ok)logline('bad','ERROR',d.message||'Mission turn failed verification.');
 return d;
}
async function requestGuardedStreamChat(text,image=null){
 if(!globalThis.ReadableStream||!globalThis.TextDecoder)return requestNonStreamingChat(text,image);
 chatStreamController=new AbortController();
 let response=await fetch('/api/chat/stream',{
  method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({message:text,image}),
  signal:chatStreamController.signal
 });
 let contentType=String(response.headers.get('content-type')||'');
 if(response.status===409&&contentType.includes('application/json')){
  let fallback=await response.json();
  chatStreamController=null;
  if(fallback.fallback==='/api/chat/send')return requestNonStreamingChat(text,image);
  throw new Error(fallback.message||'Guarded stream unavailable.');
 }
 if(!response.ok&&[404,405,501].includes(response.status)){
  chatStreamController=null;
  return requestNonStreamingChat(text,image);
 }
 if(!response.ok)throw new Error(`Guarded stream HTTP ${response.status}`);
 if(!response.body?.getReader){
  chatStreamController=null;
  return requestNonStreamingChat(text,image);
 }
 let reader=response.body.getReader(),decoder=new TextDecoder(),buffer='',streamLine=null,receivedChunk=false,finalEvent=null;
 function handleEvent(event){
  if(!event||typeof event!=='object')return;
  if(event.type==='start'&&!streamLine)streamLine=beginStreamLine('fox',event.speaker||q('ap').textContent.toUpperCase());
  if(event.type==='chunk'){
   if(!streamLine)streamLine=beginStreamLine('fox',event.speaker||q('ap').textContent.toUpperCase());
   streamLine.body.textContent+=String(event.text||'');receivedChunk=true;chat.scrollTop=chat.scrollHeight;
  }
  if(event.type==='final'){
   if(!streamLine)streamLine=beginStreamLine('fox',event.speaker||q('ap').textContent.toUpperCase());
   streamLine.body.textContent=String(event.answer||'');finalEvent=event;chat.scrollTop=chat.scrollHeight;
  }
  if(event.type==='error'){
   finalEvent=event;
   if(event.answer){
    if(!streamLine)streamLine=beginStreamLine('bad',event.speaker||'SYSTEM');
    streamLine.body.textContent=String(event.answer);
   }
  }
 }
 while(true){
  let part=await reader.read();
  buffer+=decoder.decode(part.value||new Uint8Array(),{stream:!part.done});
  let lines=buffer.split('\n');buffer=lines.pop()||'';
  for(let line of lines){
   line=line.trim();if(!line)continue;
   handleEvent(JSON.parse(line));
  }
  if(part.done)break;
 }
 if(buffer.trim())handleEvent(JSON.parse(buffer.trim()));
 chatStreamController=null;
 if(!finalEvent)throw new Error('Guarded stream ended without a verified final event.');
 if(finalEvent.type==='error'||!finalEvent.ok)logline('bad','ERROR',finalEvent.message||'Mission turn failed verification.');
 return finalEvent;
}
async function send(){
 let text=q('input').value.trim(),image=missionImagePayload();if(!text&&!image)return;
 if(image&&!activeVisionProfile()){let active=modelProfileById(activeProfileId);let message=active?`The active profile is ${active.label}, which is not a vision profile. Select and explicitly start Fast Vision or Quality Vision; no model switch occurred.`:'No verified vision profile is active. Select and explicitly start Fast Vision or Quality Vision; no model switch occurred.';logline('bad','SYSTEM',message);toast(message);return}
 if(image&&explicitEngineerMessage(text)){let message='Engineer image inspection is not enabled. Remove the image or use ordinary vision chat.';logline('bad','SYSTEM',message);toast(message);return}
 let prompt=text||(image?'Describe this image.':'');
 let browserStarted=performance.now(),d=null;
 q('input').value='';logline('user','ERIC',prompt);logMissionImage(image);think(true);
 try{
  d=explicitEngineerMessage(prompt)?await requestNonStreamingChat(prompt,null):await requestGuardedStreamChat(prompt,image);
 }catch(e){
  if(e?.name==='AbortError'){
   logline('bad','SYSTEM','Generation canceled. No partial assistant answer was archived.');
   d={ok:false,cancelled:true,timing:{}};
  }else{
   logline('bad','ERROR',String(e));
   d={ok:false,timing:{}};
  }
 }finally{
  chatStreamController=null;think(false);
  if(d?.ok&&image)clearMissionImage();
  let browserMs=performance.now()-browserStarted,modelMs=Number(d?.timing?.model_ms||0),firstMs=Number(d?.timing?.first_guarded_chunk_ms||0);
  q('ms').textContent=modelMs>0?`READY • ${(browserMs/1000).toFixed(1)}s total • ${(modelMs/1000).toFixed(1)}s model${firstMs>0?` • ${(firstMs/1000).toFixed(1)}s first guarded`:''}`:`READY • ${(browserMs/1000).toFixed(1)}s`;
  loadMemory();refresh();
 }
}
/* GUARDED_STREAMING_PHASE2_BROWSER_END */
async function startChat(){let requestedProfile=selectedProfileId||'';let d=await api('/api/chat/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:q('model').value,profile:requestedProfile})});if(d?.ok){activeProfileId=String(d?.runtime?.profile_id||requestedProfile||'');}logline(d?.ok?'sys':'bad','SYSTEM',d?.message||'start failed');loadMemory();refresh()}
async function stopChatEngine(){let d=await api('/api/chat/stop');if(d?.ok)activeProfileId='';clearMissionImage();logline(d?.ok?'sys':'bad','SYSTEM',d?.message||'stop failed');refresh()}


function streamResponse(answer='Vision answer.'){
 const encoder=new TextEncoder();let index=0;
 const chunks=[encoder.encode(JSON.stringify({type:'start',ok:true,speaker:'AGENT FOX'})+'\n'+JSON.stringify({type:'chunk',ok:true,speaker:'AGENT FOX',text:'Vision '})+'\n'),encoder.encode(JSON.stringify({type:'final',ok:true,speaker:'AGENT FOX',answer,timing:{model_ms:100,first_guarded_chunk_ms:20}})+'\n')];
 return {ok:true,status:200,headers:{get:()=> 'application/x-ndjson'},body:{getReader:()=>({read:async()=>index<chunks.length?{done:false,value:chunks[index++]}:{done:true,value:undefined}})}};
}
(async()=>{
 const imagePayload={name:'test.png',type:'image/png',size:4,width:1,height:1,sha256:'a'.repeat(64),data_url:'data:image/png;base64,AAAA'};
 let captured=[];
 global.fetch=async(url,opt)=>{captured.push({url,body:JSON.parse(opt.body)});return streamResponse()};
 let direct=await requestGuardedStreamChat('Describe it',imagePayload);
 if(!direct.ok||captured.length!==1||captured[0].url!=='/api/chat/stream')throw new Error('stream request failed');
 if(captured[0].body.image.sha256!==imagePayload.sha256)throw new Error('image payload omitted');
 if(chat.children.at(-1).body.textContent!=='Vision answer.')throw new Error('canonical final missing');

 // Text profiles must block before network activity, with no silent switch.
 captured=[];activeProfileId='fast_text';pendingMissionImage={...imagePayload};elements.input.value='What is shown?';
 await send();
 if(captured.length!==0)throw new Error('text profile sent image');
 if(!pendingMissionImage)throw new Error('blocked image was cleared');
 if(!logs.some(item=>String(item[2]||'').includes('no model switch occurred')))throw new Error('no-switch warning missing');

 // A verified vision profile sends and clears only after a successful final event.
 captured=[];activeProfileId='fast_vision';pendingMissionImage={...imagePayload};elements.input.value='What is shown?';
 global.fetch=async(url,opt)=>{captured.push({url,body:JSON.parse(opt.body)});return streamResponse('Success vision.')};
 await send();
 if(captured.length!==1||captured[0].body.image.sha256!==imagePayload.sha256)throw new Error('vision send missing image');
 if(pendingMissionImage!==null)throw new Error('successful image was not cleared');

 // Cancellation keeps the image available for retry.
 activeProfileId='fast_vision';pendingMissionImage={...imagePayload};elements.input.value='Long analysis';
 const originalRequest=requestGuardedStreamChat;
 requestGuardedStreamChat=async()=>{let error=new Error('aborted');error.name='AbortError';throw error};
 await send();
 requestGuardedStreamChat=originalRequest;
 if(!pendingMissionImage)throw new Error('cancelled image was cleared');
 if(!logs.some(item=>String(item[2]||'').includes('No partial assistant answer was archived')))throw new Error('cancel archive notice missing');

 // Start response owns the active profile; selection alone does not.
 activeProfileId='';selectedProfileId='fast_vision';
 api=async()=>({ok:true,runtime:{profile_id:'fast_vision'},message:'ready'});
 await startChat();
 if(activeProfileId!=='fast_vision')throw new Error('verified start did not set active profile');

 console.log(JSON.stringify({passed:true,stream_image_payload:true,text_profile_blocked:true,success_clears:true,cancel_keeps:true,verified_start_sets_profile:true}));
})().catch(error=>{console.error(error.stack||String(error));process.exit(1)});
