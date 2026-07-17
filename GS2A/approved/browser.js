
const calls=[];
function makeElement(tag='div'){
 return {tag,className:'',textContent:'',innerHTML:'',disabled:false,style:{},children:[],
  append(...items){this.children.push(...items)},appendChild(item){this.children.push(item)}};
}
const elements={ap:{textContent:'Agent Fox'},pulse:makeElement(),ms:makeElement(),
 sendChatButton:makeElement('button'),cancelChatButton:makeElement('button'),
 input:{value:''},toast:makeElement()};
function q(id){return elements[id]||null}
const chat=makeElement('div');chat.scrollTop=0;chat.scrollHeight=100;
global.document={createElement:tag=>makeElement(tag),createTextNode:text=>({textContent:String(text)})};
function esc(s){return String(s)}
function toast(s){calls.push(['toast',s])}
function loadMemory(){}
function refresh(){}
let chatStreamController=null;
function streamResponse(){
 const encoder=new TextEncoder();
 const payload=[
  encoder.encode(JSON.stringify({type:'start',ok:true,speaker:'AGENT FOX'})+'\n'+JSON.stringify({type:'chunk',ok:true,speaker:'AGENT FOX',text:'Hello '})+'\n'),
  encoder.encode(JSON.stringify({type:'chunk',ok:true,speaker:'AGENT FOX',text:'world.'})+'\n'+JSON.stringify({type:'final',ok:true,speaker:'AGENT FOX',answer:'Hello world.',timing:{model_ms:1000,first_guarded_chunk_ms:200}})+'\n')
 ];
 let i=0;
 return {ok:true,status:200,headers:{get:()=> 'application/x-ndjson; charset=utf-8'},
  body:{getReader:()=>({read:async()=>i<payload.length?{done:false,value:payload[i++]}:{done:true,value:undefined}})}};
}
global.fetch=async (url,opt)=>{
 calls.push(['fetch',url]);
 if(url==='/api/chat/stream')return streamResponse();
 if(url==='/api/chat/send')return {ok:true,status:200,headers:{get:()=> 'application/json'},
  json:async()=>({ok:true,answer:'fallback answer',speaker:'AGENT FOX',timing:{model_ms:5}})};
 throw new Error('unexpected url '+url);
};
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
async function requestNonStreamingChat(text){
 let response=await fetch('/api/chat/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
 let d=await response.json();
 if(d.answer)logline('fox',d.speaker||q('ap').textContent.toUpperCase(),d.answer);
 if(!d.ok)logline('bad','ERROR',d.message||'Mission turn failed verification.');
 return d;
}
async function requestGuardedStreamChat(text){
 if(!globalThis.ReadableStream||!globalThis.TextDecoder)return requestNonStreamingChat(text);
 chatStreamController=new AbortController();
 let response=await fetch('/api/chat/stream',{
  method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({message:text}),
  signal:chatStreamController.signal
 });
 let contentType=String(response.headers.get('content-type')||'');
 if(response.status===409&&contentType.includes('application/json')){
  let fallback=await response.json();
  chatStreamController=null;
  if(fallback.fallback==='/api/chat/send')return requestNonStreamingChat(text);
  throw new Error(fallback.message||'Guarded stream unavailable.');
 }
 if(!response.ok&&[404,405,501].includes(response.status)){
  chatStreamController=null;
  return requestNonStreamingChat(text);
 }
 if(!response.ok)throw new Error(`Guarded stream HTTP ${response.status}`);
 if(!response.body?.getReader){
  chatStreamController=null;
  return requestNonStreamingChat(text);
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
 let text=q('input').value.trim();if(!text)return;
 let browserStarted=performance.now(),d=null;
 q('input').value='';logline('user','ERIC',text);think(true);
 try{
  d=explicitEngineerMessage(text)?await requestNonStreamingChat(text):await requestGuardedStreamChat(text);
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
  let browserMs=performance.now()-browserStarted,modelMs=Number(d?.timing?.model_ms||0),firstMs=Number(d?.timing?.first_guarded_chunk_ms||0);
  q('ms').textContent=modelMs>0?`READY • ${(browserMs/1000).toFixed(1)}s total • ${(modelMs/1000).toFixed(1)}s model${firstMs>0?` • ${(firstMs/1000).toFixed(1)}s first guarded`:''}`:`READY • ${(browserMs/1000).toFixed(1)}s`;
  loadMemory();refresh();
 }
}
/* GUARDED_STREAMING_PHASE2_BROWSER_END */
(async()=>{
 const streamed=await requestGuardedStreamChat('hello');
 if(!streamed.ok||streamed.answer!=='Hello world.')throw new Error('final event');
 if(chat.children.length!==1)throw new Error('stream row count');
 const body=chat.children[0].children[2];
 if(body.textContent!=='Hello world.')throw new Error('canonical final text');
 if(!calls.some(x=>x[1]==='/api/chat/stream'))throw new Error('stream endpoint');
 calls.length=0;chat.children=[];
 const fallback=await requestNonStreamingChat('/engineer inspect');
 if(fallback.answer!=='fallback answer')throw new Error('fallback answer');
 if(!calls.some(x=>x[1]==='/api/chat/send'))throw new Error('fallback endpoint');
 if(!explicitEngineerMessage('/engineer inspect'))throw new Error('engineer detection');
 if(explicitEngineerMessage('tell me about engineers'))throw new Error('false positive');
 console.log(JSON.stringify({passed:true,streamFinal:streamed.answer,fallback:fallback.answer}));
})().catch(e=>{console.error(e.stack||String(e));process.exit(1)});
