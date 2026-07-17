
const visible=[];
const calls=[];

function element(){
  return {
    value:'',
    textContent:'',
    innerHTML:'',
    disabled:false,
    classList:{add(){},remove(){}},
    removeAttribute(){},
    set src(value){this._src=value},
    get src(){return this._src||''},
    appendChild(){},
    append(){},
    addEventListener(){},
    scrollTop:0,
    scrollHeight:1
  };
}

const elements={
  imagePreview:element(),
  imagePreviewThumb:element(),
  imagePreviewMeta:element(),
  imageFile:element(),
  input:element(),
  ms:element()
};

function q(id){return elements[id]||element()}
const chat={
  appendChild(node){visible.push(JSON.stringify(node))},
  append(...nodes){visible.push(JSON.stringify(nodes))},
  scrollTop:0,
  scrollHeight:1
};

let pendingMissionImage=null;
let activeMissionImage=null;
let chatStreamController=null;
let activeProfileId='fast_vision';

function modelProfileById(id){
  return id==='fast_vision'
    ? {id,vision:'Yes',label:'Fast Vision'}
    : {id,vision:'No',label:'Fast Text'};
}
function explicitEngineerMessage(){return false}
function logline(kind,speaker,text){visible.push(String(text))}
function toast(text){visible.push(String(text))}
function think(){}
function beginStreamLine(){return {body:{textContent:''}}}
async function api(url,options){
  calls.push({url,options});
  return {ok:true,message:'cleared'};
}

global.fetch=async()=>({
  json:async()=>({ok:true,active_image:{attached:false}})
});
global.URL={
  createObjectURL(){return 'blob:test'},
  revokeObjectURL(){}
};
global.document={
  createElement(){
    return {
      className:'',
      textContent:'',
      alt:'',
      append(){},
      set src(value){this._src=value},
      get src(){return this._src||''}
    };
  }
};
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

(async()=>{
  const raw='data:image/png;base64,QUFBQQ==';

  pendingMissionImage={
    name:'logo.png',
    type:'image/png',
    size:4,
    width:2,
    height:2,
    sha256:'abc',
    data_url:raw,
    preview_url:'blob:test'
  };
  elements.input.value='Describe it';

  const captured=[];
  requestGuardedStreamChat=async(text,image,useActive)=>{
    captured.push({text,image,useActive});
    return {
      ok:true,
      active_image:{
        attached:true,
        filename:'logo.png',
        mime:'image/png',
        size_bytes:4,
        width:2,
        height:2,
        sha256:'abc'
      },
      timing:{}
    };
  };

  await send();

  if(captured.length!==1)throw new Error('new image request count');
  if(!captured[0].image)throw new Error('new image bytes missing');
  if(captured[0].useActive)throw new Error('new image incorrectly used active reference');
  if(pendingMissionImage!==null)throw new Error('pending image not cleared after verified success');
  if(!activeMissionImage)throw new Error('active metadata missing');
  if(activeMissionImage.data_url)throw new Error('active browser state retained data URL');
  if(visible.join('\n').includes('data:image/'))throw new Error('visible transcript leaked data URL');

  elements.input.value='What is above the ribbon?';
  await send();

  if(captured.length!==2)throw new Error('follow-up request count');
  if(captured[1].image!==null)throw new Error('follow-up resent client image bytes');
  if(captured[1].useActive!==true)throw new Error('follow-up did not request active image');
  if(visible.join('\n').includes('data:image/'))throw new Error('follow-up transcript leaked data URL');

  requestGuardedStreamChat=async()=>{
    const error=new Error('cancelled');
    error.name='AbortError';
    throw error;
  };
  refreshActiveMissionImage=async()=>true;
  elements.input.value='Another image question';
  await send();

  if(!activeMissionImage)throw new Error('cancel cleared active image');
  if(!visible.some(item=>item.includes('active image remains available'))){
    throw new Error('cancel continuity message missing');
  }

  const before=captured.length;
  activeProfileId='fast_text';
  elements.input.value='Text-profile attempt';
  requestGuardedStreamChat=async()=>{
    throw new Error('text profile must not send image request');
  };
  await send();
  if(captured.length!==before)throw new Error('text profile sent an image request');

  activeProfileId='fast_vision';
  await clearMissionImage();
  if(activeMissionImage||pendingMissionImage)throw new Error('explicit clear failed');

  console.log(JSON.stringify({
    passed:true,
    visible_payload_free:true,
    client_active_state_metadata_only:true,
    followup_uses_server_active_reference:true,
    cancellation_preserves_active_image:true,
    text_profile_refuses_image:true,
    explicit_clear_verified:true
  }));
})().catch(error=>{
  console.error(error.stack||String(error));
  process.exit(1);
});
