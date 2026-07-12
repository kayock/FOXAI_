const API = window.kayockBridge?.apiBase || 'http://127.0.0.1:8844';

const state = {
  status: null, academy: null, foxai: null, runtime: null, localChat: null, release: null, bridge: null,
  notifications: [], selectedProfessor: null
};

function $(id) { return document.getElementById(id); }
function setBoot(line, progress) { if ($('bootLine')) $('bootLine').textContent = line; if ($('bootProgress')) $('bootProgress').style.width = `${progress}%`; }
function hideBoot() { setTimeout(() => $('bootScreen')?.classList.add('hidden'), 650); }
function setDot(id, status, waiting=false) { const el=$(id); if(el) el.className='dot '+(waiting?'wait':(status?'ok':'bad')); }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function item(label, value, status='wait') { return `<div class="item ${status}"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(value ?? '')}</span></div>`; }
async function fetchJson(path) { const res=await fetch(API+path,{cache:'no-store'}); if(!res.ok) throw new Error(`${path} ${res.status}`); return await res.json(); }

async function refresh() {
  try {
    setBoot('Checking Core API...', 20);
    const [status, academy, foxai, runtime, localChat, release, bridge] = await Promise.allSettled([
      fetchJson('/api/status'), fetchJson('/api/academy'), fetchJson('/api/foxai'), fetchJson('/api/runtime'),
      fetchJson('/api/local-chat'), fetchJson('/api/release-check'), fetchJson('/api/bridge')
    ]);
    setBoot('Greeting the professors...', 45);
    state.status = status.status === 'fulfilled' ? status.value : null;
    state.academy = academy.status === 'fulfilled' ? academy.value : null;
    state.foxai = foxai.status === 'fulfilled' ? foxai.value : null;
    state.runtime = runtime.status === 'fulfilled' ? runtime.value : null;
    state.localChat = localChat.status === 'fulfilled' ? localChat.value : null;
    state.release = release.status === 'fulfilled' ? release.value : null;
    state.bridge = bridge.status === 'fulfilled' ? bridge.value : null;
    setBoot('Preparing professor studies...', 75);
    buildNotifications(); render();
    setBoot('The Academy is open.', 100); hideBoot();
  } catch (err) {
    setDot('apiDot', false); $('overallStatus').textContent='Core Offline'; $('overallStatus').className='statusPill bad';
    notify('Core API','The Core API is offline. Start KayocktheOS first.','bad'); renderNotifications();
  renderAcademyBridgeDashboard();
  renderCoreWorkingPanel();
  renderModelProfiles();
  renderKoboldPanel();
  renderKoboldAdapterNotice();
  renderFirstContactDiagnosticsHint();
  renderFirstContactPanel();
  renderFirstContactNotice();
  renderBridgeHealthData();
  renderRepairBayData();
  renderCreativeStudioData();
  renderLibraryData();
  renderFoundryData();
  renderObservatoryData();
    setBoot('Core API offline.', 100); hideBoot();
  }
}

function notify(title, message, status='ok') {
  const key=`${title}:${message}`; if(state.notifications.some(n=>n.key===key)) return;
  state.notifications.unshift({key,title,message,status,time:new Date().toLocaleTimeString()});
  state.notifications=state.notifications.slice(0,20);
}

function buildNotifications() {
  if (state.foxai?.exists) {
    const s=state.foxai.summary||{};
    notify('FOXAI',`${s.total_assets||0} asset(s) discovered in the AI warehouse.`,'ok');
    if((s.llm_models||0)>0) notify('Academy',`${s.llm_models} chat model(s) available for professor teams.`,'ok');
    if((s.image_models||0)>0) notify('Creative Studio',`${s.image_models} image model(s) discovered.`,'ok');
  } else notify('FOXAI','FOXAI repository not detected at Z:\\FOXAI.','bad');
  if(state.runtime?.online) notify('Local Runtime','A local model runtime is online.','ok');
  else notify('Local Runtime','Runtime is offline. Launch the selected model runtime to enable chat.','wait');
}

function render() {
  const apiOnline=!!state.status; setDot('apiDot',apiOnline); setDot('runtimeDot',!!state.runtime?.online); setDot('foxaiDot',!!state.foxai?.exists);
  const project=state.status?.project||{}, operator=state.status?.operator||{};
  $('operatorName').textContent=operator.display_name||'Operator';
  $('versionLabel').textContent=`${project.name||'KayocktheOS'} ${project.version||''}`;
  $('heroGreeting').textContent=`Good day, ${operator.display_name||'Operator'}.`;
  $('academyGreeting').textContent=state.academy?.startup_greeting || 'The Academy is open. Today’s lesson awaits.';
  const good=apiOnline && state.foxai?.exists; $('overallStatus').textContent=good?'Workshop Online':'Needs Attention'; $('overallStatus').className='statusPill '+(good?'ok':'wait');
  renderHealth(); renderHomeCapabilities(); renderChatSummary(); renderAcademy(); renderCapabilities(); renderSystem(); renderEvents(); renderRelease(); renderWorkshopWall(); renderLibrary(); renderNotifications();
  renderAcademyBridgeDashboard();
  renderCoreWorkingPanel();
  renderModelProfiles();
  renderKoboldPanel();
  renderKoboldAdapterNotice();
  renderFirstContactDiagnosticsHint();
  renderFirstContactPanel();
  renderFirstContactNotice();
  renderBridgeHealthData();
  renderRepairBayData();
  renderCreativeStudioData();
  renderLibraryData();
  renderFoundryData();
  renderObservatoryData();
}

function renderHealth() {
  const health=state.status?.health||[];
  $('healthList').innerHTML=health.slice(0,8).map(h=>item(h.label,`${h.status} — ${h.path}`,h.status==='OK'?'ok':'bad')).join('') || item('Core API','No data yet','bad');
}

function capabilityData() {
  const llms=state.foxai?.assets?.llms||[], images=state.foxai?.assets?.image_models||[], workflows=state.foxai?.assets?.workflows||[];
  const count=key=>llms.filter(m=>(m.capabilities||[]).includes(key)).length;
  return [
    {icon:'🧠',label:'Conversation',value:llms.length,detail:'Ask and reason with local models.'},
    {icon:'💻',label:'Programming',value:count('coding'),detail:'Code help and review.'},
    {icon:'🧪',label:'Reasoning',value:count('reasoning'),detail:'Logic, planning, and analysis.'},
    {icon:'👁',label:'Vision',value:count('vision'),detail:'Image understanding models.'},
    {icon:'🎨',label:'Image Creation',value:images.length,detail:'ComfyUI checkpoints.'},
    {icon:'🧩',label:'Workflows',value:workflows.length,detail:'ComfyUI workflow files.'}
  ];
}

function renderHomeCapabilities() {
  const caps=capabilityData(), max=Math.max(1,...caps.map(c=>c.value));
  $('homeCapabilityMini').innerHTML=caps.slice(0,5).map(c=>`<div class="capLine"><span>${c.icon} ${escapeHtml(c.label)}</span><div class="capBar"><span style="width:${Math.max(4,(c.value/max)*100)}%"></span></div><strong>${c.value}</strong></div>`).join('');
}
function renderCapabilities() {
  const caps=capabilityData(); $('capabilityCount').textContent=`${caps.filter(c=>c.value>0).length} available`;
  $('capabilityCards').innerHTML=caps.map(c=>`<div class="capabilityCard"><div class="icon">${c.icon}</div><h5>${escapeHtml(c.label)}</h5><p>${escapeHtml(c.detail)}</p><div class="score">${c.value?c.value+' available':'Not available yet'}</div></div>`).join('');
}
function renderChatSummary() {
  const rt=state.runtime||{}, lc=state.localChat||{};
  $('chatSummary').innerHTML=[item('Runtime',rt.online?'Online':'Offline',rt.online?'ok':'bad'), item('Selected Model',lc.selected_model||'Not selected',lc.selected_model?'ok':'wait'), item('Launch Helper',lc.launch_helper||'Missing',lc.launch_helper?'ok':'wait')].join('');
}

function professorSeal(prof) {
  const name=(prof||'K').replace(/^Professor\s+/i,'').trim();
  return name[0]?.toUpperCase() || 'K';
}
function professorMission(college) {
  const domains=(college.domains||[]).join(', ');
  return `Guide the Operator through ${domains || college.name}, while keeping explanations clear, practical, and grounded in the Academy charter.`;
}
function professorQuestions(college) {
  const d=(college.domains||[])[0] || college.name;
  return [
    `What should I understand first about ${d}?`,
    `Give me a practical lesson for ${d}.`,
    `How can ${college.professor} help KayocktheOS today?`,
    `What project should I build to practice ${d}?`
  ];
}
function professorModelTeam(college) {
  const llms=state.foxai?.assets?.llms||[];
  const domains=(college.domains||[]).join(' ').toLowerCase();
  let models=llms.filter(m=>{
    const caps=(m.capabilities||[]).join(' ').toLowerCase();
    const name=(m.name||'').toLowerCase();
    return (domains.includes('code') && caps.includes('coding')) ||
           (domains.includes('reason') && caps.includes('reasoning')) ||
           (domains.includes('science') && caps.includes('reasoning')) ||
           (domains.includes('vision') && caps.includes('vision')) ||
           name.includes('qwen') || name.includes('deepseek');
  }).slice(0,4);
  if(!models.length) models=llms.slice(0,3);
  return models;
}
function renderAcademy() {
  const colleges=state.academy?.colleges||[];
  $('professorCount').textContent=`${colleges.length} professors`;
  $('professorGrid').innerHTML=colleges.map((c,i)=>`
    <div class="professor" data-professor-index="${i}">
      <div class="professorSeal">${professorSeal(c.professor)}</div>
      <h5>${escapeHtml(c.professor||c.name)}</h5>
      <p><strong>${escapeHtml(c.name)}</strong></p>
      <p>“${escapeHtml(c.motto||'')}”</p>
      <p>${escapeHtml((c.domains||[]).slice(0,3).join(' · '))}</p>
    </div>
  `).join('') || '<p>No Academy data yet.</p>';
  document.querySelectorAll('[data-professor-index]').forEach(card=>{
    card.addEventListener('click',()=>openProfessor(Number(card.dataset.professorIndex)));
  });
}
function openProfessor(index) {
  const college=(state.academy?.colleges||[])[index]; if(!college) return;
  state.selectedProfessor=college;
  $('academyHall').classList.remove('active'); $('professorStudy').classList.add('active');
  $('studySeal').textContent=professorSeal(college.professor);
  $('studyCollege').textContent=college.name||'College';
  $('studyProfessor').textContent=college.professor||college.name||'Professor';
  $('studyMotto').textContent=`“${college.motto||''}”`;
  $('studyAvailability').textContent=state.runtime?.online?'Available':'Advisor Ready';
  $('studyAvailability').className='statusPill '+(state.runtime?.online?'ok':'wait');
  $('studyMission').textContent=professorMission(college);
  $('studyDomains').innerHTML=(college.domains||[]).map(d=>`<span class="tag">${escapeHtml(d)}</span>`).join('');
  const team=professorModelTeam(college);
  $('studyModelTeam').innerHTML=team.map(m=>item(m.name,`${m.size_gb||'?'} GB · ${(m.capabilities||[]).join(', ')}`,'ok')).join('') || item('No model team yet','FOXAI has not assigned a model team.','wait');
  $('studyAskTitle').textContent=`Ask ${college.professor||'Professor'}`;
  $('studyQuestions').innerHTML=professorQuestions(college).map(q=>`<button class="question" data-question="${escapeHtml(q)}">${escapeHtml(q)}</button>`).join('');
  document.querySelectorAll('[data-question]').forEach(btn=>btn.addEventListener('click',()=>{ $('studyChatInput').value=btn.dataset.question; }));
}
function backToHall() { $('professorStudy').classList.remove('active'); $('academyHall').classList.add('active'); }

function renderSystem() {
  const sys=state.status?.system||{}, cpu=sys.cpu||{}, mem=sys.memory||{}, disk=sys.disk||{};
  $('systemSummary').innerHTML=[item('OS',sys.os?.platform||'Unknown',sys.os?'ok':'wait'), item('CPU',cpu.name||'Unknown',cpu.name?'ok':'wait'), item('RAM',mem.total_gb?`${mem.total_gb} GB`:'Unknown',mem.total_gb?'ok':'wait'), item('Disk Free',disk.free_gb?`${disk.free_gb} GB free`:'Unknown',disk.free_gb?'ok':'wait')].join('');
}
function renderEvents() {
  const events=state.status?.events||state.bridge?.events||[];
  $('eventList').innerHTML=events.slice(-8).reverse().map(e=>item(e.type||'event',e.message||e.timestamp||'','ok')).join('') || item('Events','No events yet','wait');
}
function renderRelease() {
  const r=state.release||{};
  $('releaseSummary').innerHTML=[item('Ship Ready',r.ship_ready?'YES':'NO / Unknown',r.ship_ready?'ok':'wait'), item('Version',r.version||'Unknown',r.version?'ok':'wait'), item('Warnings',r.summary?.warnings??'Unknown','wait')].join('');
}
function renderWorkshopWall() {
  $('workshopWall').innerHTML=[
    item('Architecture Law #1','Build complete, integrated features—not isolated components.','ok'),
    item('Architecture Law #2','Capabilities are discovered, never hardcoded.','ok'),
    item('Architecture Law #3','The interface teaches, assists, and builds.','ok'),
    item('Feature 002C','Professor Studies are now visible.','ok'),
    item('Feature 001','Local Chat in progress.','wait')
  ].join('');
}
function renderLibrary() {
  const files=state.status?.system?.assets?.knowledge_files;
  $('librarySummary').innerHTML=[item('Knowledge Files',files??'Unknown',files?'ok':'wait'), item('Next','Iron Library indexing is a future complete feature.','wait')].join('');
}
function renderNotifications() {
  $('bellCount').textContent=state.notifications.length;
  $('notificationList').innerHTML=state.notifications.map(n=>item(n.title,`${n.message} — ${n.time}`,n.status==='bad'?'bad':(n.status==='wait'?'wait':'ok'))).join('') || item('Workshop Bell','No notifications yet.','wait');
}

async function sendChat(prompt, professor=null) {
  const prefix = professor ? `[Consulting ${professor.professor}. College: ${professor.name}. Motto: ${professor.motto}.] ` : '';
  addMessage('user', professor ? `${professor.professor}: ${prompt}` : prompt);
  addMessage('system','Sending to local AI Gateway...');
  try {
    const res=await fetch(API+'/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt: prefix + prompt, context:{professor}})});
    const data=await res.json();
    const text=data.response||data.message||data.error||JSON.stringify(data).slice(0,1000);
    addMessage(data.ok?'assistant':'system',text);
  } catch(err) { addMessage('system','Chat failed: '+err.message); }
}
function addMessage(role,text) { const log=$('chatLog'); const div=document.createElement('div'); div.className='message '+role; div.textContent=text; log.appendChild(div); log.scrollTop=log.scrollHeight; }

function openRoom(room) {
  document.querySelectorAll('.nav').forEach(b=>b.classList.toggle('active',b.dataset.room===room));
  document.querySelectorAll('.room').forEach(r=>r.classList.remove('active'));
  document.getElementById(room)?.classList.add('active');
  const btn=document.querySelector(`.nav[data-room="${room}"]`); if(btn) $('roomTitle').textContent=btn.textContent.replace(/[^\w\s]/g,'').trim();
}
document.querySelectorAll('.nav').forEach(btn=>btn.addEventListener('click',()=>openRoom(btn.dataset.room)));
document.querySelectorAll('[data-room-jump]').forEach(btn=>btn.addEventListener('click',()=>openRoom(btn.dataset.roomJump)));
$('bellBtn').addEventListener('click',()=>$('bellPanel').classList.toggle('hidden'));
$('backToHall').addEventListener('click',backToHall);
$('chatForm').addEventListener('submit',e=>{ e.preventDefault(); const input=$('chatInput'); const prompt=input.value.trim(); if(!prompt)return; input.value=''; sendChat(prompt); });
$('studyChatForm').addEventListener('submit',e=>{ e.preventDefault(); const input=$('studyChatInput'); const prompt=input.value.trim(); if(!prompt)return; input.value=''; sendChat(prompt,state.selectedProfessor); });

refresh();
setInterval(refresh,5000);


// Feature 002D Observatory upgrade
function renderObservatoryUpgrade() {
  const observatory = document.getElementById('observatory');
  if (!observatory || observatory.dataset.upgraded === 'true') return;
  observatory.dataset.upgraded = 'true';
  observatory.innerHTML = `
    <article class="card wide observatoryHero">
      <div class="sectionHeader">
        <div>
          <p class="eyebrow">Observatory</p>
          <h4>Host Computer & Workshop Awareness</h4>
        </div>
        <span id="observatoryStatus" class="badge">Scanning</span>
      </div>
      <p class="roomIntro">The Observatory watches the current computer, FOXAI, runtime status, and what KayocktheOS can do in this session.</p>
    </article>

    <div class="roomSplit">
      <div>
        <article class="card">
          <h4>Host Machine</h4>
          <div id="observatoryMetrics" class="metricGrid"></div>
        </article>

        <article class="card chatCard">
          <h4>Session Capabilities</h4>
          <div id="sessionCapabilities" class="capabilityCards"></div>
        </article>
      </div>

      <div>
        <article class="card">
          <h4>Recommendations</h4>
          <div id="observatoryRecommendations"></div>
        </article>

        <article class="card chatCard">
          <h4>Runtime & AI</h4>
          <div id="observatoryRuntime" class="smallList"></div>
        </article>
      </div>
    </div>
  `;
}

function metricCard(label, value, sub='') {
  return `<div class="metricCard"><h5>${escapeHtml(label)}</h5><div class="metricValue">${escapeHtml(value ?? '--')}</div><div class="metricSub">${escapeHtml(sub ?? '')}</div></div>`;
}

function rec(text, type='ok') {
  const cls = type === 'bad' ? 'bad' : (type === 'warn' ? 'warn' : '');
  return `<div class="recommendation ${cls}">${escapeHtml(text)}</div>`;
}

function renderObservatoryData() {
  renderObservatoryUpgrade();
  const sys = state.status?.system || {};
  const cpu = sys.cpu || {};
  const mem = sys.memory || {};
  const disk = sys.disk || {};
  const gpu = sys.gpu || {};
  const tools = sys.tools || {};
  const fox = state.foxai?.summary || {};
  const runtime = state.runtime || {};
  const metrics = document.getElementById('observatoryMetrics');
  const status = document.getElementById('observatoryStatus');

  if (status) {
    const healthy = !!state.status && !!state.foxai?.exists;
    status.textContent = healthy ? 'Watching' : 'Needs Setup';
  }

  if (metrics) {
    metrics.innerHTML = [
      metricCard('Operating System', sys.os?.release || 'Unknown', sys.os?.platform || ''),
      metricCard('CPU', cpu.cores_logical ? `${cpu.cores_logical} threads` : 'Unknown', cpu.name || ''),
      metricCard('Memory', mem.total_gb ? `${mem.total_gb} GB` : 'Unknown', 'Detected RAM'),
      metricCard('Disk Free', disk.free_gb ? `${disk.free_gb} GB` : 'Unknown', disk.drive || disk.root || ''),
      metricCard('GPU', (gpu.gpus || []).length || 'None', (gpu.gpus || []).join(' · ') || 'No GPU names detected'),
      metricCard('Python', tools.python?.version || 'Unknown', tools.python?.path || ''),
      metricCard('Node', tools.node?.installed ? 'Installed' : 'Missing', tools.node?.version || ''),
      metricCard('Git', tools.git?.installed ? 'Installed' : 'Missing', tools.git?.version || '')
    ].join('');
  }

  const capsEl = document.getElementById('sessionCapabilities');
  if (capsEl) {
    const caps = capabilityData();
    capsEl.innerHTML = caps.map(c => `
      <div class="capabilityCard">
        <div class="icon">${c.icon}</div>
        <h5>${escapeHtml(c.label)}</h5>
        <p>${escapeHtml(c.detail)}</p>
        <div class="score">${c.value ? c.value + ' available' : 'Unavailable'}</div>
      </div>
    `).join('');
  }

  const runtimeEl = document.getElementById('observatoryRuntime');
  if (runtimeEl) {
    runtimeEl.innerHTML = [
      item('Runtime', runtime.online ? 'Online' : 'Offline', runtime.online ? 'ok' : 'bad'),
      item('Runtime Base', runtime.base || 'http://127.0.0.1:8845', runtime.base ? 'ok' : 'wait'),
      item('FOXAI Assets', `${fox.total_assets ?? 0} discovered`, (fox.total_assets ?? 0) ? 'ok' : 'wait'),
      item('LLM Models', `${fox.llm_models ?? 0}`, (fox.llm_models ?? 0) ? 'ok' : 'wait'),
      item('Image Models', `${fox.image_models ?? 0}`, (fox.image_models ?? 0) ? 'ok' : 'wait')
    ].join('');
  }

  const recommendations = [];
  if (!state.foxai?.exists) recommendations.push(['FOXAI was not detected at Z:\\FOXAI. Discovery needs that warehouse path.', 'bad']);
  if (!runtime.online) recommendations.push(['Start the selected local model runtime to activate Ask the Academy.', 'warn']);
  if ((fox.llm_models || 0) > 0 && !runtime.online) recommendations.push(['Models are available. Runtime launch is the next step toward First Contact.', 'ok']);
  if ((fox.image_models || 0) > 0) recommendations.push(['Image models are discovered. Creative Studio can be wired to ComfyUI next.', 'ok']);
  if (!tools.git?.installed) recommendations.push(['Git was not detected. Install Git for reliable project history.', 'warn']);
  if (!tools.node?.installed) recommendations.push(['Node was not detected by Core. Bridge development may need Node available.', 'warn']);
  if (disk.free_gb && disk.free_gb < 80) recommendations.push(['Disk space is getting low for AI work. Avoid copying large models.', 'warn']);
  if (!recommendations.length) recommendations.push(['Workshop looks healthy. Continue building from the Bridge.', 'ok']);

  const recEl = document.getElementById('observatoryRecommendations');
  if (recEl) recEl.innerHTML = recommendations.map(([text,type]) => rec(text,type)).join('');
}


// Feature 002E Foundry room upgrade
function renderFoundryUpgrade() {
  const foundry = document.getElementById('foundry');
  if (!foundry || foundry.dataset.upgraded === 'true') return;
  foundry.dataset.upgraded = 'true';
  foundry.innerHTML = `
    <article class="card wide foundryHero">
      <div class="sectionHeader">
        <div>
          <p class="eyebrow">Foundry</p>
          <h4>Build, Release, Improve</h4>
        </div>
        <span id="foundryStatus" class="badge">Checking</span>
      </div>
      <p class="roomIntro">The Foundry is where KayocktheOS becomes stronger: release checks, architecture laws, patch history, and next-build guidance.</p>
    </article>

    <div class="roomSplit">
      <div>
        <article class="card">
          <h4>Release Readiness</h4>
          <div id="foundryReleaseGauge"></div>
          <div id="foundryReleaseDetails" class="smallList"></div>
        </article>

        <article class="card chatCard">
          <h4>Architecture Laws</h4>
          <div id="architectureLaws" class="lawGrid"></div>
        </article>
      </div>

      <div>
        <article class="card">
          <h4>Workshop Wall</h4>
          <div id="foundryWorkshopWall" class="smallList"></div>
        </article>

        <article class="card chatCard">
          <h4>Next Build Guidance</h4>
          <div id="nextBuildGuidance" class="smallList"></div>
        </article>
      </div>
    </div>

    <article class="card chatCard">
      <h4>Recent Build Timeline</h4>
      <div id="buildTimeline" class="patchTimeline"></div>
    </article>
  `;
}

function renderFoundryData() {
  renderFoundryUpgrade();

  const release = state.release || {};
  const summary = release.summary || {};
  const total = summary.total_checks || summary.required_checks || 1;
  const passed = summary.passed_required || 0;
  const failed = summary.failed_required || 0;
  const percent = Math.max(0, Math.min(100, Math.round((passed / Math.max(1, summary.required_checks || total)) * 100)));
  const shipReady = !!release.ship_ready;

  const status = document.getElementById('foundryStatus');
  if (status) status.textContent = shipReady ? 'Ship Ready' : 'In Progress';

  const gauge = document.getElementById('foundryReleaseGauge');
  if (gauge) {
    gauge.innerHTML = `
      <div class="releaseGauge">
        <div class="gaugeTop"><span>Foundation Readiness</span><strong>${percent}%</strong></div>
        <div class="gaugeBar"><span style="width:${percent}%"></span></div>
      </div>
    `;
  }

  const details = document.getElementById('foundryReleaseDetails');
  if (details) {
    details.innerHTML = [
      item('Ship Ready', shipReady ? 'YES' : 'NO / Unknown', shipReady ? 'ok' : 'wait'),
      item('Required Passed', `${passed}/${summary.required_checks ?? '?'}`, failed ? 'wait' : 'ok'),
      item('Warnings', `${summary.warnings ?? 0}`, (summary.warnings ?? 0) ? 'wait' : 'ok'),
      item('Version', release.version || state.status?.project?.version || 'Unknown', 'ok')
    ].join('');
  }

  const laws = [
    ['Architecture Law #1', 'Build complete, integrated features—not isolated components.'],
    ['Architecture Law #2', 'Capabilities are discovered, never hardcoded.'],
    ['Architecture Law #3', 'The interface teaches, assists, and builds.'],
    ['Replaceability Principle', 'Every subsystem must be independently replaceable.'],
    ['Bridge Principle', 'Every feature must be demonstrable from the Bridge.']
  ];

  const lawsEl = document.getElementById('architectureLaws');
  if (lawsEl) {
    lawsEl.innerHTML = laws.map(([title, text]) => `
      <div class="lawCard"><h5>${escapeHtml(title)}</h5><p>${escapeHtml(text)}</p></div>
    `).join('');
  }

  const wall = document.getElementById('foundryWorkshopWall');
  if (wall) {
    wall.innerHTML = [
      item('Feature 001', 'Local Chat foundation installed.', 'ok'),
      item('Feature 001B', 'Runtime launch helper installed.', 'ok'),
      item('Feature 002', 'Bridge application created.', 'ok'),
      item('Feature 002B', 'Living Bridge polish added.', 'ok'),
      item('Feature 002C', 'Professor Studies added.', 'ok'),
      item('Feature 002D', 'Observatory Room added.', 'ok'),
      item('Feature 002E', 'Foundry Room active.', 'ok')
    ].join('');
  }

  const fox = state.foxai?.summary || {};
  const runtimeOnline = !!state.runtime?.online;
  const guidance = [];
  if (!runtimeOnline) guidance.push(['First Contact', 'Launch the selected local runtime and test Ask the Academy.', 'wait']);
  if ((fox.image_models || 0) > 0) guidance.push(['Creative Studio', 'ComfyUI assets are present. Build image generation room next.', 'ok']);
  guidance.push(['Iron Library', 'Build indexing and document search as a complete room.', 'wait']);
  guidance.push(['Repair Bay', 'Turn Observatory data into a machine scan report.', 'wait']);

  const guidanceEl = document.getElementById('nextBuildGuidance');
  if (guidanceEl) {
    guidanceEl.innerHTML = guidance.map(([label, text, status]) => item(label, text, status)).join('');
  }

  const timeline = document.getElementById('buildTimeline');
  if (timeline) {
    const entries = [
      ['Now', 'Foundry room added to the Bridge.'],
      ['Recent', 'Observatory gained host-machine awareness.'],
      ['Recent', 'Academy gained professor studies.'],
      ['Recent', 'Bridge gained capability cards and Workshop Bell.'],
      ['Recent', 'Runtime launcher connected Feature 001 to real local model startup.'],
      ['Foundation', 'FOXAI Discovery, Service Bus, Academy Seed, AI Gateway, and Release Checker established.']
    ];
    timeline.innerHTML = entries.map(([time, desc]) => `
      <div class="timelineItem"><div class="time">${escapeHtml(time)}</div><div class="desc">${escapeHtml(desc)}</div></div>
    `).join('');
  }
}


// Feature 002F Library room upgrade
function renderLibraryUpgrade() {
  const library = document.getElementById('library');
  if (!library || library.dataset.upgraded === 'true') return;
  library.dataset.upgraded = 'true';
  library.innerHTML = `
    <article class="card wide libraryHero">
      <div class="sectionHeader">
        <div>
          <p class="eyebrow">Iron Library</p>
          <h4>Knowledge, Manuals, Notes, Comics</h4>
        </div>
        <span id="libraryStatus" class="badge">Checking</span>
      </div>
      <p class="roomIntro">The Library is where KayocktheOS will store, index, search, and explain your documents. This room prepares the visible foundation for searchable knowledge.</p>
    </article>

    <div class="roomSplit">
      <div>
        <article class="card">
          <h4>Library Shelf</h4>
          <div id="libraryShelf" class="libraryShelf"></div>
        </article>

        <article class="card chatCard">
          <h4>Library Readiness</h4>
          <div id="libraryReadiness" class="smallList"></div>
        </article>
      </div>

      <div>
        <article class="card">
          <h4>What to Index Next</h4>
          <div id="libraryGuidance" class="smallList"></div>
        </article>

        <article class="card chatCard">
          <h4>Future Library Tools</h4>
          <div id="libraryFuture" class="smallList"></div>
        </article>
      </div>
    </div>
  `;
}

function renderLibraryData() {
  renderLibraryUpgrade();

  const assets = state.status?.system?.assets || {};
  const knowledgeFiles = assets.knowledge_files ?? 0;
  const status = document.getElementById('libraryStatus');
  if (status) status.textContent = knowledgeFiles ? `${knowledgeFiles} files` : 'Empty / Unknown';

  const shelf = document.getElementById('libraryShelf');
  if (shelf) {
    const cards = [
      ['📄', 'Documents', knowledgeFiles ? `${knowledgeFiles} known files` : 'Waiting for files', 'PDFs, DOCX, TXT, Markdown, HTML'],
      ['🐧', 'Linux Shelf', 'Ready for import', 'Linux Bible, commands, manuals'],
      ['🧠', 'Project Memory', 'Planned', 'Architecture laws, decisions, changelog'],
      ['🎭', 'Comics & Stories', 'Planned', 'Creative references and motion comic source'],
      ['🔎', 'Search Index', 'Not built yet', 'Semantic search comes in a future feature'],
      ['👁', 'OCR', 'Not built yet', 'Scanned PDFs and images need OCR support']
    ];
    shelf.innerHTML = cards.map(([icon,title,value,detail]) => `
      <div class="shelfCard">
        <div class="shelfIcon">${icon}</div>
        <h5>${escapeHtml(title)}</h5>
        <p><strong>${escapeHtml(value)}</strong></p>
        <p>${escapeHtml(detail)}</p>
      </div>
    `).join('');
  }

  const readiness = document.getElementById('libraryReadiness');
  if (readiness) {
    readiness.innerHTML = [
      item('Knowledge Folder', 'Knowledge/', 'ok'),
      item('Known Files', String(knowledgeFiles), knowledgeFiles ? 'ok' : 'wait'),
      item('Index Engine', 'Not installed yet', 'wait'),
      item('OCR', 'Not installed yet', 'wait'),
      item('Semantic Search', 'Planned complete feature', 'wait')
    ].join('');
  }

  const guidance = document.getElementById('libraryGuidance');
  if (guidance) {
    const rows = [];
    if (!knowledgeFiles) rows.push(item('Add documents', 'Copy manuals, books, notes, or PDFs into Knowledge/.', 'wait'));
    rows.push(item('Linux Bible', 'Good first import for the Iron Library.', 'ok'));
    rows.push(item('Project Docs', 'Index Docs/ and Forge/ to let the Academy explain KayocktheOS.', 'ok'));
    rows.push(item('Comics', 'Future Creative Studio can use story/comic references.', 'wait'));
    rows.push(item('Next complete feature', 'Build Library Indexer with search from the Bridge.', 'wait'));
    guidance.innerHTML = rows.join('');
  }

  const future = document.getElementById('libraryFuture');
  if (future) {
    future.innerHTML = [
      item('Read PDF', 'Extract text from PDFs.', 'wait'),
      item('Search Library', 'Keyword and semantic search.', 'wait'),
      item('Ask Library', 'Answer questions using local documents.', 'wait'),
      item('Cite Sources', 'Show where an answer came from.', 'wait'),
      item('OCR Scans', 'Read scanned manuals and images.', 'wait')
    ].join('');
  }
}


// Feature 002G v2 Creative Studio upgrade
function renderCreativeStudioUpgrade() {
  const workshop = document.getElementById('workshop');
  if (!workshop || workshop.dataset.creativeStudio === 'true') return;
  workshop.dataset.creativeStudio = 'true';

  const studio = document.createElement('article');
  studio.className = 'card wide chatCard creativeHero';
  studio.innerHTML = `
    <div class="sectionHeader">
      <div>
        <p class="eyebrow">Creative Studio</p>
        <h4>Image Generation, Workflows, and Creative Assets</h4>
      </div>
      <span id="creativeStudioStatus" class="badge">Scanning</span>
    </div>
    <p class="roomIntro">Creative Studio reads FOXAI's image assets and prepares the path to ComfyUI generation directly from the Bridge.</p>
    <div class="studioGrid" id="creativeStudioCards"></div>
  `;

  const prompt = document.createElement('article');
  prompt.className = 'card wide chatCard';
  prompt.innerHTML = `
    <div class="sectionHeader">
      <div>
        <p class="eyebrow">Prompt Bench</p>
        <h4>Draft an Image Prompt</h4>
      </div>
      <span class="badge">Operator approval required</span>
    </div>
    <textarea id="creativePrompt" class="promptBox" placeholder="Describe an image to generate later through ComfyUI..."></textarea>
    <div class="promptActions">
      <button id="savePromptBtn" class="primaryBtn" type="button">Save Prompt Draft</button>
      <button id="askDaVinciBtn" class="primaryBtn" type="button">Ask Professor Da Vinci</button>
    </div>
    <div id="creativePromptNotice" class="creativeNotice chatCard">
      Generation is not enabled yet. This room prepares the prompt and workflow layer first.
    </div>
  `;

  const workflow = document.createElement('article');
  workflow.className = 'card wide chatCard';
  workflow.innerHTML = `
    <h4>ComfyUI Workflows</h4>
    <div id="creativeWorkflowList" class="workflowList"></div>
  `;

  workshop.appendChild(studio);
  workshop.appendChild(prompt);
  workshop.appendChild(workflow);

  document.getElementById('savePromptBtn')?.addEventListener('click', () => {
    const promptText = document.getElementById('creativePrompt')?.value || '';
    if (!promptText.trim()) {
      notify('Creative Studio', 'Prompt draft is empty.', 'wait');
      renderNotifications();
  renderAcademyBridgeDashboard();
  renderCoreWorkingPanel();
  renderModelProfiles();
  renderKoboldPanel();
  renderKoboldAdapterNotice();
  renderFirstContactDiagnosticsHint();
  renderFirstContactPanel();
  renderFirstContactNotice();
  renderBridgeHealthData();
  renderRepairBayData();
  renderCreativeStudioData();
      return;
    }
    localStorage.setItem('kayock_creative_prompt_draft', promptText);
    notify('Creative Studio', 'Prompt draft saved locally in the Bridge.', 'ok');
    renderNotifications();
  renderAcademyBridgeDashboard();
  renderCoreWorkingPanel();
  renderModelProfiles();
  renderKoboldPanel();
  renderKoboldAdapterNotice();
  renderFirstContactDiagnosticsHint();
  renderFirstContactPanel();
  renderFirstContactNotice();
  renderBridgeHealthData();
  renderRepairBayData();
  renderCreativeStudioData();
    document.getElementById('creativePromptNotice').textContent = 'Prompt draft saved locally. Next build will add prompt history on disk.';
  });

  document.getElementById('askDaVinciBtn')?.addEventListener('click', () => {
    const promptText = document.getElementById('creativePrompt')?.value || '';
    const ask = promptText.trim()
      ? `Professor Da Vinci, improve this image prompt for ComfyUI: ${promptText}`
      : 'Professor Da Vinci, help me design an image prompt for KayocktheOS.';
    openRoom('home');
    document.getElementById('chatInput').value = ask;
  });
}

function renderCreativeStudioData() {
  renderCreativeStudioUpgrade();
  const fox = state.foxai || {};
  const assets = fox.assets || {};
  const images = assets.image_models || [];
  const workflows = assets.workflows || [];
  const llms = assets.llms || [];
  const vision = llms.filter(m => (m.capabilities || []).includes('vision'));

  const status = document.getElementById('creativeStudioStatus');
  if (status) status.textContent = images.length ? 'Assets Ready' : 'Waiting';

  const cards = document.getElementById('creativeStudioCards');
  if (cards) {
    cards.innerHTML = [
      studioCard('🎨', 'Image Models', images.length, images.slice(0, 6).map(m => m.name)),
      studioCard('🧩', 'Workflows', workflows.length, workflows.slice(0, 6).map(w => w.name)),
      studioCard('👁', 'Vision Assist', vision.length, vision.slice(0, 4).map(m => m.name)),
      studioCard('🔌', 'ComfyUI', workflows.length || images.length ? 'Detected assets' : 'Not connected yet', ['Generation endpoint will be wired later'])
    ].join('');
  }

  const wf = document.getElementById('creativeWorkflowList');
  if (wf) {
    if (workflows.length) {
      wf.innerHTML = workflows.slice(0, 50).map(w =>
        item(w.name, `${w.path || ''}`, 'ok')
      ).join('');
    } else {
      wf.innerHTML = [
        item('No workflows discovered yet', 'Place ComfyUI workflow JSON files under Z:\\FOXAI\\ComfyUI.', 'wait'),
        item('Next build', 'Add ComfyUI API detection and generation submit button.', 'wait')
      ].join('');
    }
  }

  const saved = localStorage.getItem('kayock_creative_prompt_draft');
  const promptBox = document.getElementById('creativePrompt');
  if (promptBox && saved && !promptBox.value) promptBox.value = saved;
}

function studioCard(icon, title, count, names) {
  const nameList = Array.isArray(names) && names.length
    ? names.map(n => `<span class="modelPill">${escapeHtml(n)}</span>`).join('')
    : '<p>No assets yet.</p>';
  return `
    <div class="studioCard">
      <div class="shelfIcon">${icon}</div>
      <h5>${escapeHtml(title)}</h5>
      <p><strong>${escapeHtml(count)}</strong></p>
      <div>${nameList}</div>
    </div>
  `;
}


// Feature 002H Repair Bay room
function ensureRepairBayNav() {
  const nav = document.querySelector('nav');
  if (!nav || document.querySelector('[data-room="repair"]')) return;
  const btn = document.createElement('button');
  btn.className = 'nav';
  btn.dataset.room = 'repair';
  btn.textContent = '🛠 Repair Bay';
  nav.insertBefore(btn, document.querySelector('[data-room="library"]'));
  btn.addEventListener('click', () => openRoom('repair'));
}

function renderRepairBayUpgrade() {
  ensureRepairBayNav();
  if (document.getElementById('repair')) return;
  const section = document.createElement('section');
  section.id = 'repair';
  section.className = 'room';
  section.innerHTML = `
    <article class="card wide repairHero">
      <div class="sectionHeader">
        <div>
          <p class="eyebrow">Repair Bay</p>
          <h4>Read-Only Diagnostics & Machine Awareness</h4>
        </div>
        <span id="repairStatus" class="badge">Scanning</span>
      </div>
      <p class="roomIntro">Repair Bay starts safe: observe first, report clearly, and require Operator approval before any future action.</p>
    </article>

    <div class="roomSplit">
      <div>
        <article class="card">
          <h4>Host Health</h4>
          <div id="repairHealthCards" class="repairGrid"></div>
        </article>

        <article class="card chatCard">
          <h4>Read-Only Scan Rules</h4>
          <div id="repairRules"></div>
        </article>
      </div>

      <div>
        <article class="card">
          <h4>Repair Readiness</h4>
          <div id="repairReadiness" class="smallList"></div>
        </article>

        <article class="card chatCard">
          <h4>Recommended Next Scans</h4>
          <div id="repairRecommendations" class="smallList"></div>
        </article>
      </div>
    </div>
  `;
  document.querySelector('.main').appendChild(section);
}

function renderRepairBayData() {
  renderRepairBayUpgrade();

  const sys = state.status?.system || {};
  const cpu = sys.cpu || {};
  const mem = sys.memory || {};
  const disk = sys.disk || {};
  const gpu = sys.gpu || {};
  const tools = sys.tools || {};
  const apiOk = !!state.status;
  const diskOk = !disk.free_gb || disk.free_gb > 50;
  const memOk = !mem.total_gb || mem.total_gb >= 8;
  const score = [apiOk, diskOk, memOk, tools.python?.installed].filter(Boolean).length;
  const pct = Math.round((score / 4) * 100);

  const status = document.getElementById('repairStatus');
  if (status) status.textContent = pct >= 75 ? 'Ready' : 'Needs Review';

  const cards = document.getElementById('repairHealthCards');
  if (cards) {
    cards.innerHTML = [
      repairCard('🧠', 'CPU', cpu.cores_logical ? `${cpu.cores_logical} threads` : 'Unknown', cpu.name || 'No CPU name detected'),
      repairCard('💾', 'Memory', mem.total_gb ? `${mem.total_gb} GB` : 'Unknown', memOk ? 'Looks usable for diagnostics' : 'May be limited'),
      repairCard('🗄', 'Storage', disk.free_gb ? `${disk.free_gb} GB free` : 'Unknown', diskOk ? 'Enough free space for reports' : 'Low free space warning'),
      repairCard('🎮', 'GPU', (gpu.gpus || []).length ? `${gpu.gpus.length} detected` : 'Unknown', (gpu.gpus || []).join(' · ') || 'No GPU names detected'),
      repairCard('🐍', 'Python', tools.python?.version || 'Unknown', tools.python?.path || 'Python powers the Core'),
      repairCard('🌐', 'Node', tools.node?.installed ? 'Installed' : 'Missing', tools.node?.version || 'Needed for Bridge development')
    ].join('');
  }

  const rules = document.getElementById('repairRules');
  if (rules) {
    rules.innerHTML = [
      '<div class="ruleBox"><strong>Rule 1:</strong> Repair Bay observes before it acts.</div>',
      '<div class="ruleBox"><strong>Rule 2:</strong> No registry, driver, disk, or system change without Operator approval.</div>',
      '<div class="ruleBox"><strong>Rule 3:</strong> First deliverable is always a readable report.</div>',
      '<div class="ruleBox"><strong>Rule 4:</strong> Prefer reversible fixes and backups.</div>'
    ].join('');
  }

  const ready = document.getElementById('repairReadiness');
  if (ready) {
    ready.innerHTML = [
      item('Repair Score', `${pct}%`, pct >= 75 ? 'ok' : 'wait'),
      item('Core Scanner', apiOk ? 'Online' : 'Offline', apiOk ? 'ok' : 'bad'),
      item('Read-Only Mode', 'Enabled', 'ok'),
      item('Report Writer', 'Planned next', 'wait'),
      item('Driver Scan', 'Planned', 'wait'),
      item('SMART Disk Scan', 'Planned', 'wait')
    ].join('');
  }

  const recs = document.getElementById('repairRecommendations');
  if (recs) {
    const rows = [];
    rows.push(item('Machine Summary Report', 'Generate a clean report from current Observatory data.', 'ok'));
    rows.push(item('Disk Health', 'Add SMART/status checks where tools are available.', 'wait'));
    rows.push(item('Network Diagnostics', 'Add ping/DNS/gateway checks.', 'wait'));
    rows.push(item('Windows Health', 'Add read-only system information and update status.', 'wait'));
    if (!tools.git?.installed) rows.push(item('Git Missing', 'Project rollback is weaker without Git.', 'wait'));
    if (!tools.node?.installed) rows.push(item('Node Missing', 'Bridge development may need Node available.', 'wait'));
    recs.innerHTML = rows.join('');
  }
}

function repairCard(icon, title, value, sub) {
  return `
    <div class="repairCard">
      <div class="shelfIcon">${icon}</div>
      <h5>${escapeHtml(title)}</h5>
      <div class="repairScore">${escapeHtml(value)}</div>
      <p>${escapeHtml(sub)}</p>
    </div>
  `;
}


// Feature 002I Bridge Health panel
function renderBridgeHealthMini() {
  const foundry = document.getElementById('foundry');
  if (!foundry || document.getElementById('bridgeHealthMini')) return;
  const card = document.createElement('article');
  card.className = 'card chatCard';
  card.id = 'bridgeHealthMini';
  card.innerHTML = `
    <h4>Bridge Health</h4>
    <div id="bridgeHealthMiniList" class="smallList"></div>
  `;
  foundry.appendChild(card);
}

function renderBridgeHealthData() {
  renderBridgeHealthMini();
  const el = document.getElementById('bridgeHealthMiniList');
  if (!el) return;
  const rooms = ['Home','Academy','Workshop','Repair Bay','Library','Observatory','Foundry'];
  el.innerHTML = rooms.map(room => item(room, 'Visible in Bridge', 'ok')).join('') +
    item('Health Report', 'Run Foundry\\bridge_health.bat for full report.', 'wait');
}


// Feature 002J Operator Settings Room
function ensureSettingsNav() {
  const nav = document.querySelector('nav');
  if (!nav || document.querySelector('[data-room="settings"]')) return;
  const btn = document.createElement('button');
  btn.className = 'nav';
  btn.dataset.room = 'settings';
  btn.textContent = '⚙ Settings';
  nav.appendChild(btn);
  btn.addEventListener('click', () => openRoom('settings'));
}

function renderSettingsRoomUpgrade() {
  ensureSettingsNav();
  if (document.getElementById('settings')) return;
  const section = document.createElement('section');
  section.id = 'settings';
  section.className = 'room';
  section.innerHTML = `
    <article class="card wide">
      <div class="sectionHeader">
        <div>
          <p class="eyebrow">Operator Settings</p>
          <h4>Portable Preferences</h4>
        </div>
        <span class="badge">USB-first</span>
      </div>
      <p class="roomIntro">These settings prepare the Bridge to carry the Operator's preferences with the USB instead of depending on a single computer.</p>
    </article>

    <div class="settingsGrid">
      <article class="card">
        <h4>Operator Identity</h4>
        <div class="settingField">
          <label for="settingsDisplayName">Display Name</label>
          <input id="settingsDisplayName" placeholder="Operator" />
        </div>
        <div class="settingField">
          <label for="settingsNickname">Preferred Nickname</label>
          <input id="settingsNickname" placeholder="Eric" />
        </div>
        <div class="settingField">
          <label for="settingsGreeting">Startup Greeting</label>
          <textarea id="settingsGreeting"></textarea>
        </div>
        <button id="saveSettingsBtn" class="primaryBtn" type="button">Save Locally</button>
      </article>

      <article class="card">
        <h4>Workshop Paths</h4>
        <div id="settingsPaths" class="smallList"></div>
      </article>
    </div>

    <article class="card chatCard">
      <h4>Design Parameters</h4>
      <div id="settingsDesignLaws" class="smallList"></div>
    </article>
  `;
  document.querySelector('.main').appendChild(section);

  document.getElementById('saveSettingsBtn')?.addEventListener('click', () => {
    const prefs = {
      display_name: document.getElementById('settingsDisplayName')?.value || 'Operator',
      nickname: document.getElementById('settingsNickname')?.value || '',
      greeting: document.getElementById('settingsGreeting')?.value || ''
    };
    localStorage.setItem('kayock_operator_settings', JSON.stringify(prefs));
    notify('Settings', 'Operator settings saved locally in the Bridge.', 'ok');
    renderNotifications();
  renderAcademyBridgeDashboard();
  renderCoreWorkingPanel();
  renderModelProfiles();
  renderKoboldPanel();
  renderKoboldAdapterNotice();
  renderFirstContactDiagnosticsHint();
  renderFirstContactPanel();
  renderFirstContactNotice();
    renderSettingsData();
  });
}

function renderSettingsData() {
  renderSettingsRoomUpgrade();
  let prefs = {};
  try { prefs = JSON.parse(localStorage.getItem('kayock_operator_settings') || '{}'); } catch {}
  const operator = state.status?.operator || {};
  const academy = state.academy || {};

  const display = document.getElementById('settingsDisplayName');
  const nick = document.getElementById('settingsNickname');
  const greeting = document.getElementById('settingsGreeting');

  if (display && !display.value) display.value = prefs.display_name || operator.display_name || 'Operator';
  if (nick && !nick.value) nick.value = prefs.nickname || operator.display_name || '';
  if (greeting && !greeting.value) greeting.value = prefs.greeting || academy.startup_greeting || "The Academy is open. Today's lesson awaits.";

  const paths = document.getElementById('settingsPaths');
  if (paths) {
    paths.innerHTML = [
      item('KayocktheOS Root', 'Z:\\KayocktheOS', 'ok'),
      item('FOXAI Warehouse', state.foxai?.foxai_root || 'Z:\\FOXAI', state.foxai?.exists ? 'ok' : 'wait'),
      item('Core API', 'http://127.0.0.1:8844', state.status ? 'ok' : 'bad'),
      item('Local Runtime', state.runtime?.base || 'http://127.0.0.1:8845', state.runtime?.online ? 'ok' : 'wait'),
      item('Preference Storage', 'Bridge localStorage now; USB config file later', 'wait')
    ].join('');
  }

  const laws = document.getElementById('settingsDesignLaws');
  if (laws) {
    laws.innerHTML = [
      item('Feature-first', 'Build complete, integrated features—not isolated components.', 'ok'),
      item('Capability discovery', 'Capabilities are discovered, never hardcoded.', 'ok'),
      item('Living Workshop', 'The interface teaches, assists, and builds.', 'ok'),
      item('Replaceability', 'Every subsystem must be independently replaceable.', 'ok'),
      item('Bridge-visible', 'Every feature must be demonstrable from the Bridge.', 'ok'),
      item('Operator approval', 'No AI writes to the project without approval.', 'ok')
    ].join('');
  }
}


// Feature 003 First Contact Bridge notice
function renderFirstContactNotice() {
  const wall = document.getElementById('workshopWall') || document.getElementById('foundryWorkshopWall');
  if (!wall || document.getElementById('firstContactNotice')) return;
  const div = document.createElement('div');
  div.id = 'firstContactNotice';
  div.className = 'item ok';
  div.innerHTML = '<strong>Feature 003</strong><span>First Contact installed. Run AI\\\\Gateway\\\\FIRST_CONTACT_START_RUNTIME.bat, then Ask the Academy.</span>';
  wall.prepend(div);
}


// Feature 003C First Contact Bridge Panel
async function fetchFirstContactStatus() {
  try {
    return await fetchJson('/api/first-contact');
  } catch {
    return null;
  }
}

function renderFirstContactPanelShell() {
  const home = document.getElementById('home');
  if (!home || document.getElementById('firstContactPanel')) return;

  const panel = document.createElement('article');
  panel.id = 'firstContactPanel';
  panel.className = 'card chatCard firstContactPanel';
  panel.innerHTML = `
    <div class="sectionHeader">
      <div>
        <p class="eyebrow">Feature 003</p>
        <h4>First Contact</h4>
      </div>
      <span id="firstContactBadge" class="badge">Checking</span>
    </div>
    <div id="firstContactDetails" class="smallList"></div>
    <div class="firstContactSteps">
      <div class="firstContactStep">
        <div class="stepNumber">1</div>
        <div><strong>Start Runtime</strong><br><span class="pathText" id="firstContactLauncher">AI\\Gateway\\FIRST_CONTACT_START_RUNTIME.bat</span></div>
      </div>
      <div class="firstContactStep">
        <div class="stepNumber">2</div>
        <div><strong>Wait for Server</strong><br><span>Leave the runtime window open once llama-server finishes loading.</span></div>
      </div>
      <div class="firstContactStep">
        <div class="stepNumber">3</div>
        <div><strong>Ask the Academy</strong><br><span>Use the chat box below when the badge turns online.</span></div>
      </div>
    </div>
  `;

  const chatCard = document.querySelector('#home .chatCard');
  if (chatCard) home.insertBefore(panel, chatCard);
  else home.appendChild(panel);
}

async function renderFirstContactPanel() {
  renderFirstContactPanelShell();
  const fc = await fetchFirstContactStatus();
  const badge = document.getElementById('firstContactBadge');
  const details = document.getElementById('firstContactDetails');
  const launcher = document.getElementById('firstContactLauncher');

  if (!badge || !details) return;

  if (!fc) {
    badge.textContent = 'API Missing';
    details.innerHTML = item('First Contact', 'Endpoint not available yet. Restart KayocktheOS Core.', 'bad');
    return;
  }

  const online = !!fc.runtime?.online;
  badge.textContent = online ? 'Academy Online' : (fc.ready_for_contact ? 'Ready to Start' : 'Needs Setup');
  if (launcher && fc.launcher) launcher.textContent = fc.launcher.replace(/^.*KayocktheOS[\\\\/]/, '');

  details.innerHTML = [
    item('Runtime', fc.runtime_path || 'Not found', fc.runtime_path ? 'ok' : 'bad'),
    item('Model', fc.model || 'Not selected', fc.model ? 'ok' : 'bad'),
    item('Server', fc.runtime?.base || 'http://127.0.0.1:8845', online ? 'ok' : 'wait'),
    item('Status', online ? 'Online — Ask the Academy now' : 'Offline — run the First Contact runtime launcher', online ? 'ok' : 'wait')
  ].join('');
}


// Feature 003D First Contact Diagnostics hint
function renderFirstContactDiagnosticsHint() {
  const panel = document.getElementById('firstContactPanel');
  if (!panel || document.getElementById('firstContactDiagnosticsHint')) return;
  const div = document.createElement('div');
  div.id = 'firstContactDiagnosticsHint';
  div.className = 'diagnosticHint';
  div.innerHTML = '<strong>Diagnostics:</strong> Run <span class="pathText">Z:\\\\KayocktheOS\\\\Foundry\\\\first_contact_diagnostics.bat</span> if First Contact does not answer.';
  panel.appendChild(div);
}


// Feature 004 Kobold Engine Adapter notice
function renderKoboldAdapterNotice() {
  const panel = document.getElementById('firstContactPanel');
  if (!panel || document.getElementById('koboldAdapterNotice')) return;
  const div = document.createElement('div');
  div.id = 'koboldAdapterNotice';
  div.className = 'diagnosticHint';
  div.innerHTML = '<strong>Kobold Engine Adapter:</strong> Run <span class="pathText">Z:\\\\KayocktheOS\\\\AI\\\\Gateway\\\\START_KOBOLD_ENGINE.bat</span>, then ask the Academy.';
  panel.appendChild(div);
}


// Feature 004B Kobold Engine Check Panel
async function fetchKoboldStatus() {
  try {
    return await fetchJson('/api/kobold');
  } catch {
    return null;
  }
}

function renderKoboldPanelShell() {
  const home = document.getElementById('home');
  if (!home || document.getElementById('koboldEnginePanel')) return;

  const panel = document.createElement('article');
  panel.id = 'koboldEnginePanel';
  panel.className = 'card chatCard koboldPanel';
  panel.innerHTML = `
    <div class="sectionHeader">
      <div>
        <p class="eyebrow">Feature 004</p>
        <h4>KoboldCpp Engine Adapter</h4>
      </div>
      <span id="koboldEngineBadge" class="badge">Checking</span>
    </div>
    <div id="koboldEngineDetails" class="smallList"></div>
    <div class="koboldSteps">
      <div class="koboldStep">
        <div class="stepNumber">1</div>
        <div><strong>Install Engine</strong><br><span class="pathText">Z:\\KayocktheOS\\Engine\\KoboldCpp\\koboldcpp.exe</span></div>
      </div>
      <div class="koboldStep">
        <div class="stepNumber">2</div>
        <div><strong>Start Engine</strong><br><span class="pathText">Z:\\KayocktheOS\\AI\\Gateway\\START_KOBOLD_ENGINE.bat</span></div>
      </div>
      <div class="koboldStep">
        <div class="stepNumber">3</div>
        <div><strong>Ask the Academy</strong><br><span>Bridge chat uses the engine adapter when available.</span></div>
      </div>
    </div>
  `;

  const firstContact = document.getElementById('firstContactPanel');
  if (firstContact) firstContact.insertAdjacentElement('afterend', panel);
  else {
    const chatCard = document.querySelector('#home .chatCard');
    if (chatCard) home.insertBefore(panel, chatCard);
    else home.appendChild(panel);
  }
}

async function renderKoboldPanel() {
  renderKoboldPanelShell();

  const badge = document.getElementById('koboldEngineBadge');
  const details = document.getElementById('koboldEngineDetails');
  if (!badge || !details) return;

  const st = await fetchKoboldStatus();

  if (!st) {
    badge.textContent = 'Core Restart Needed';
    details.innerHTML = item('Kobold Adapter', 'Restart KayocktheOS Core so /api/kobold becomes available.', 'wait');
    return;
  }

  const online = !!st.health?.online;
  const engineExists = !!st.engine_exists;
  const modelExists = !!st.model_exists;

  badge.textContent = online ? 'Engine Online' : (engineExists ? 'Ready to Start' : 'Engine Missing');

  details.innerHTML = [
    item('KoboldCpp EXE', st.engine_path || 'Missing: put koboldcpp.exe in Engine\\KoboldCpp', engineExists ? 'ok' : 'bad'),
    item('Selected Model', st.model_path || 'No GGUF model found', modelExists ? 'ok' : 'bad'),
    item('Server', st.health?.base || 'http://127.0.0.1:5001', online ? 'ok' : 'wait'),
    item('Launcher', st.launcher || 'AI\\Gateway\\START_KOBOLD_ENGINE.bat', 'ok'),
    item('Status', online ? 'Online — Ask the Academy now' : 'Offline — start Kobold engine first', online ? 'ok' : 'wait')
  ].join('');
}


// Feature 004D Model Profiles
async function fetchModelProfiles() {
  try { return await fetchJson('/api/model-profiles'); } catch { return null; }
}

function renderModelProfilesShell() {
  const panel = document.getElementById('koboldEnginePanel');
  if (!panel || document.getElementById('modelProfilesPanel')) return;
  const card = document.createElement('article');
  card.id = 'modelProfilesPanel';
  card.className = 'card chatCard';
  card.innerHTML = `
    <div class="sectionHeader">
      <div>
        <p class="eyebrow">Engine Profiles</p>
        <h4>Model Profiles</h4>
      </div>
      <span class="badge">Safe / Power / Vision</span>
    </div>
    <div id="modelProfilesGrid" class="profileGrid"></div>
  `;
  panel.insertAdjacentElement('afterend', card);
}

async function renderModelProfiles() {
  renderModelProfilesShell();
  const grid = document.getElementById('modelProfilesGrid');
  if (!grid) return;

  const data = await fetchModelProfiles();
  if (!data || !data.profiles) {
    grid.innerHTML = '<div class="profileCard"><h5>Profiles unavailable</h5><p>Restart KayocktheOS Core after installing Feature 004D.</p></div>';
    return;
  }

  const active = data.active?.profile || 'safe';
  grid.innerHTML = Object.entries(data.profiles).map(([key, p]) => `
    <div class="profileCard">
      <h5>${escapeHtml(p.label || key)} ${key === active ? '✓' : ''}</h5>
      <p>${escapeHtml(p.description || '')}</p>
      <p><strong>Model:</strong><br><span class="pathText">${escapeHtml(p.model_name || p.model || '')}</span></p>
      <p><strong>Context:</strong> ${escapeHtml(String(p.context_tokens || ''))}</p>
      <p><strong>Status:</strong> ${p.model_exists ? 'Found' : 'Missing'}</p>
    </div>
  `).join('');
}


// Feature 006 Core Working Panel
async function fetchCoreWorkingStatus() {
  try { return await fetchJson('/api/core-working'); } catch { return null; }
}

function renderCoreWorkingShell() {
  const home = document.getElementById('home');
  if (!home || document.getElementById('coreWorkingPanel')) return;

  const panel = document.createElement('article');
  panel.id = 'coreWorkingPanel';
  panel.className = 'card chatCard coreWorkingPanel';
  panel.innerHTML = `
    <div class="sectionHeader">
      <div>
        <p class="eyebrow">Core</p>
        <h4>Core Working Launcher</h4>
      </div>
      <span id="coreWorkingBadge" class="badge">Checking</span>
    </div>
    <p class="roomIntro">Clean startup path. The broken First Contact launcher now redirects here instead of calling llama-batched-bench.exe.</p>
    <div id="coreWorkingDetails" class="smallList"></div>
    <div class="coreLauncherList">
      <div class="coreLauncherItem"><strong>Main Launcher</strong><br><span class="pathText">Z:\\KayocktheOS\\AI\\Gateway\\START_CORE_WORKING.bat</span></div>
      <div class="coreLauncherItem"><strong>AnythingLLM</strong><br><span>Engineering knowledge, code scanning, project reports.</span></div>
      <div class="coreLauncherItem"><strong>ComfyUI / FOXAI</strong><br><span>Creative engine remains in FOXAI.</span></div>
    </div>
  `;

  const first = document.getElementById('anythingLLMPanel') || document.getElementById('koboldEnginePanel') || document.getElementById('firstContactPanel');
  if (first) first.insertAdjacentElement('beforebegin', panel);
  else {
    const chatCard = document.querySelector('#home .chatCard');
    if (chatCard) home.insertBefore(panel, chatCard);
    else home.appendChild(panel);
  }
}

async function renderCoreWorkingPanel() {
  renderCoreWorkingShell();
  const badge = document.getElementById('coreWorkingBadge');
  const details = document.getElementById('coreWorkingDetails');
  if (!badge || !details) return;

  const st = await fetchCoreWorkingStatus();
  if (!st) {
    badge.textContent = 'Core Restart Needed';
    details.innerHTML = item('Core Working API', 'Restart KayocktheOS Core after installing Feature 006.', 'wait');
    return;
  }

  const anything = st.anythingllm?.found;
  const comfy = st.comfyui?.found;
  const kobold = st.koboldcpp?.found;

  badge.textContent = (anything || comfy || kobold) ? 'Ready' : 'Needs Tool Paths';

  details.innerHTML = [
    item('AnythingLLM', st.anythingllm?.path || 'Not found yet', anything ? 'ok' : 'wait'),
    item('ComfyUI / FOXAI', st.comfyui?.path || 'Not found yet', comfy ? 'ok' : 'wait'),
    item('KoboldCpp', st.koboldcpp?.path || 'Optional / not found', kobold ? 'ok' : 'wait'),
    item('Legacy First Contact', 'Disabled and redirected to START_CORE_WORKING.bat', 'ok')
  ].join('');
}


// Feature 007 Academy Bridge Dashboard
async function fetchAcademyBridgeStatus() {
  try { return await fetchJson('/api/core-working'); } catch { return null; }
}

function renderAcademyBridgeDashboard() {
  const home = document.getElementById('home');
  if (!home || document.getElementById('academyBridgeDashboard')) return;

  const dash = document.createElement('section');
  dash.id = 'academyBridgeDashboard';
  dash.className = 'academyBridgeHero';
  dash.innerHTML = `
    <p class="eyebrow">KayocktheOS Academy Bridge</p>
    <h2>Welcome back, Commander.</h2>
    <p class="motto">The Academy is open. Today's lesson awaits. KayocktheOS now acts as the command bridge over mature local AI tools instead of reinventing them.</p>
    <div id="academyStatusLine" class="academyStatusLine">
      <span class="academyPill wait">Checking AnythingLLM</span>
      <span class="academyPill wait">Checking ComfyUI</span>
      <span class="academyPill wait">Checking Runtime</span>
    </div>
    <div class="academyGrid">
      <article class="academyCard">
        <h4>Engineering Academy</h4>
        <div class="professor">Professor Asimov</div>
        <p>Code scanning, architecture reports, project memory, and engineering review through AnythingLLM.</p>
        <div class="academyActions">
          <span class="academyButton">Open AnythingLLM</span>
          <span class="academyButton">Engineering Snapshot</span>
        </div>
      </article>
      <article class="academyCard">
        <h4>Creative Studio</h4>
        <div class="professor">Professor Roddenberry</div>
        <p>Image generation, workflows, galleries, and future motion-comic tools through FOXAI ComfyUI.</p>
        <div class="academyActions">
          <span class="academyButton">Launch ComfyUI</span>
          <span class="academyButton">Open Gallery</span>
        </div>
      </article>
      <article class="academyCard">
        <h4>Knowledge Wing</h4>
        <div class="professor">Professor Sagan</div>
        <p>Iron Library, prompts, mission archive, manuals, and searchable local documents.</p>
        <div class="academyActions">
          <span class="academyButton">Open Library</span>
          <span class="academyButton">Refresh Index</span>
        </div>
      </article>
      <article class="academyCard">
        <h4>Repair Bay</h4>
        <div class="professor">Professor Kayock</div>
        <p>Diagnostics, launch cleanup, system health, runtime checks, and safe repair plans.</p>
        <div class="academyActions">
          <span class="academyButton">Run Diagnostics</span>
          <span class="academyButton">View Logs</span>
        </div>
      </article>
    </div>
  `;

  const firstCard = home.querySelector('.card');
  if (firstCard) home.insertBefore(dash, firstCard);
  else home.prepend(dash);

  updateAcademyBridgeStatus();
}

async function updateAcademyBridgeStatus() {
  const line = document.getElementById('academyStatusLine');
  if (!line) return;

  const st = await fetchAcademyBridgeStatus();
  if (!st) {
    line.innerHTML = `
      <span class="academyPill wait">Core status unavailable</span>
      <span class="academyPill wait">Restart Core API</span>
    `;
    return;
  }

  const anything = st.anythingllm?.found;
  const comfy = st.comfyui?.found;
  const runtime = st.koboldcpp?.found;

  line.innerHTML = `
    <span class="academyPill ${anything ? 'ok' : 'wait'}">AnythingLLM ${anything ? 'Found' : 'Missing'}</span>
    <span class="academyPill ${comfy ? 'ok' : 'wait'}">ComfyUI ${comfy ? 'Found' : 'Use FOXAI launcher'}</span>
    <span class="academyPill ${runtime ? 'ok' : 'wait'}">Runtime ${runtime ? 'Found' : 'Optional'}</span>
    <span class="academyPill ok">Legacy First Contact Redirected</span>
  `;
}

