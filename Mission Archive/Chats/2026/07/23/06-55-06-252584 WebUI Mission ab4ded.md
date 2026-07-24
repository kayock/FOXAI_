# FOXAI Mission Archive

- Session ID: `20260723T065506252584_ab4ded`
- Interface: WebUI
- Project: Default_Mission
- Professor: Agent Fox
- Model: None
- Started: 2026-07-23T06:55:06

## Transcript

### ERIC — 2026-07-23T12:55:06+00:00

/engineer workshop read core\foxai_web.py :: LINES 70-220

### ENGINEER — 2026-07-23T12:55:06+00:00

ENGINEERING WORKSHOP — EXACT FILE CONTENT

Mission ID: ENG-20260723-071407-27BDEA
Path: Z:\FOXAI\core\foxai_web.py
Relative path: core\foxai_web.py
Encoding: utf-8
Size: 2368185 bytes
Total lines: more than 220 (bounded stream; full file was not loaded)
Showing lines: 70-220

   70:  'sagan':('Professor Sagan','Scientific Curiosity','Extraordinary claims require extraordinary evidence.','You are Professor Sagan inside FOXAI. Specialize in science, evidence, skepticism, cosmology, and clear explanations.'),
   71:  'kayock':('Professor Kayock','Practical Engineering','Wonder is a tool. Build with it.','You are Professor Kayock inside FOXAI. Specialize in troubleshooting, Windows repair, Linux, networking, local AI workstations, and step-by-step engineering.'),
   72:  'roddenberry':('Professor Roddenberry','Optimistic Futures','Technology reaches its highest purpose when it enlarges humanity.','You are Professor Roddenberry inside FOXAI. Specialize in hopeful futures, ethical technology, design, storytelling, and human-centered systems.'),
   73:  'deadpool':('Professor Deadpool','Meta Creativity',"The best stories know they're being told.",'You are Professor Deadpool inside FOXAI. Specialize in creative brainstorming, comedy, comics, characters, and bold ideas while still being useful.')}
   74: def professor_system_prompt(key):
   75:     return PROF.get(key,PROF['fox'])[3]+'\n\n'+SECURITY_SYSTEM_RULES
   76: 
   77: prof='fox'; active_project=None; chat_model=None; chat_process=None; chat_profile_id=''; chat_model_source=None
   78: web_llama_server=LlamaServer(interface_name='WebUI',new_console=True)
   79: model_source_registry=ModelSourceRegistry(ROOT,config_path=ROOT/'Config'/'model_sources.json')
   80: messages=[{'role':'system','content':professor_system_prompt(prof)}]
   81: mission_active_image=None
   82: mission_image_lock=RLock()
   83: web_mission_session=MissionSession(ROOT,interface_name='WebUI')
   84: _web_engineer=None
   85: _web_engineer_lock=RLock()
   86: web_chat_stream_lock=RLock()
   87: 
   88: class _WebEngineerApp:
   89:     """Minimal adapter for Engineer's existing read-only analysis surface."""
   90:     models=[]
   91:     threads=8
   92: 
   93: WEB_ENGINEER_WRITE_COMMANDS=(
   94:     'chisel decision for ',
   95:     'log decision for ',
   96:     'record decision for ',
   97:     'log lesson for ',
   98:     'chisel lesson for ',
   99:     'log forge for ',
  100:     'forge journal entry for ',
  101: )
  102: 
  103: def web_engineer_read_only_allowed(text):
  104:     normalized=re.sub(r'^\s*(?:/engineer\b|engineer\s*[:,])\s*','',text or '',flags=re.IGNORECASE).strip().lower()
  105:     return not any(normalized.startswith(marker) for marker in WEB_ENGINEER_WRITE_COMMANDS)
  106: 
  107: def web_mission_context():
  108:     return {
  109:         'project':active_project or 'Default_Mission',
  110:         'professor':active_prof()[0],
  111:         'model':Path(chat_model).name if chat_model else 'None',
  112:     }
  113: 
  114: def begin_web_mission_session():
  115:     return web_mission_session.start(**web_mission_context())
  116: 
  117: def ensure_web_mission_session():
  118:     return web_mission_session.ensure_started(**web_mission_context())
  119: 
  120: def web_engineer_analyze(
  121:     text,
  122:     *,
  123:     mission_id,
  124:     correlation_id,
  125:     route_audit_receipt,
  126:     inspect_authorization,
  127:     inspect_audit_receipt,
  128:     caller='operator',
  129: ):
  130:     global _web_engineer
  131: 
  132:     route_validation=validate_airlock_route_receipt(
  133:         route_audit_receipt,
  134:         expected_actor=caller,
  135:         expected_object='engineering_airlock',
  136:         expected_action='route',
  137:         correlation_id=correlation_id,
  138:         mission_id=mission_id,
  139:     )
  140:     inspect_receipt=(
  141:         inspect_audit_receipt
  142:         if isinstance(inspect_audit_receipt,dict)
  143:         else {}
  144:     )
  145:     inspect_validation=validate_airlock_route_receipt(
  146:         inspect_receipt,
  147:         expected_actor=caller,
  148:         expected_object='engineering_airlock',
  149:         expected_action='inspect',
  150:         correlation_id=correlation_id,
  151:         mission_id=mission_id,
  152:     )
  153:     inspect_actor=str(getattr(inspect_authorization,'actor','') or '').strip().lower()
  154:     inspect_object=str(getattr(inspect_authorization,'object','') or '').strip().lower()
  155:     inspect_action=str(getattr(inspect_authorization,'action','') or '').strip().lower()
  156:     inspect_allowed=bool(getattr(inspect_authorization,'allowed',False))
  157: 
  158:     checks=[
  159:         ('mission_id_present',bool(str(mission_id or '').strip())),
  160:         ('correlation_id_present',bool(str(correlation_id or '').strip())),
  161:         ('route_receipt_verified',bool(route_validation.get('verified'))),
  162:         ('inspect_receipt_verified',bool(inspect_validation.get('verified'))),
  163:         ('inspect_authorization_allowed',inspect_allowed),
  164:         ('inspect_actor_matches',inspect_actor==str(caller or '').strip().lower()),
  165:         ('inspect_object_matches',inspect_object=='engineering_airlock'),
  166:         ('inspect_action_matches',inspect_action=='inspect'),
  167:     ]
  168:     failed=[name for name,ok in checks if not ok]
  169:     if failed:
  170:         route_failed=list(
  171:             (route_validation.get('details') or {}).get('failed_check_ids') or []
  172:         )
  173:         inspect_failed=list(
  174:             (inspect_validation.get('details') or {}).get('failed_check_ids') or []
  175:         )
  176:         reason='WebUI Engineering Airlock context mismatch: '+', '.join(failed)
  177:         if route_failed:
  178:             reason+='; route receipt checks: '+', '.join(route_failed)
  179:         if inspect_failed:
  180:             reason+='; inspect receipt checks: '+', '.join(inspect_failed)
  181:         context_receipt_id=str(
  182:             inspect_receipt.get('receipt_id')
  183:             or (
  184:                 route_audit_receipt.get('receipt_id')
  185:                 if isinstance(route_audit_receipt,dict)
  186:                 else ''
  187:             )
  188:             or ''
  189:         )
  190:         denial=record_boundary_denial(
  191:             actor=caller,
  192:             obj='engineering_airlock',
  193:             action='route_context',
  194:             reason=reason,
  195:             incident_kind='context_mismatch',
  196:             correlation_id=correlation_id,
  197:             mission_id=mission_id,
  198:             receipt_id=context_receipt_id,
  199:             context_status='mismatch',
  200:         )
  201:         if not denial.get('verified'):
  202:             raise PermissionError(reason+' Boundary incident audit also failed closed.')
  203:         raise PermissionError(reason)
  204: 
  205:     with _web_engineer_lock:
  206:         if _web_engineer is None:
  207:             from core.engineer_agent import EngineerAgent
  208:             _web_engineer=EngineerAgent(_WebEngineerApp())
  209: 
  210:         _web_engineer._active_airlock_context={
  211:             'actor':inspect_actor or str(caller or '').strip().lower(),
  212:             'authorization_allowed':inspect_allowed,
  213:             'authorization_reason':str(getattr(inspect_authorization,'reason','') or 'Read-only Engineer inspection authorized.'),
  214:             'authorization_policy_source':str(getattr(inspect_authorization,'policy_source','') or ''),
  215:             'correlation_id':str(correlation_id or '').strip(),
  216:             'mission_id':str(mission_id or '').strip(),
  217:             'fox_sentry_receipt_id':str(inspect_receipt.get('receipt_id') or ''),
  218:             'route_receipt_id':str(route_audit_receipt.get('receipt_id') or ''),
  219:             'route_context_status':'verified',
  220:         }

More content is available. Continue with:
/engineer workshop read core\foxai_web.py :: LINES 221-420

Safety: exact-path, bounded, read-only file access; nothing changed.

### ERIC — 2026-07-23T12:55:15+00:00

/engineer workshop read core\foxai_web.py :: LINES 14120-14220

### ENGINEER — 2026-07-23T12:55:15+00:00

ENGINEERING WORKSHOP — EXACT FILE CONTENT

Mission ID: ENG-20260723-071407-27BDEA
Path: Z:\FOXAI\core\foxai_web.py
Relative path: core\foxai_web.py
Encoding: utf-8
Size: 2368185 bytes
Total lines: more than 14220 (bounded stream; full file was not loaded)
Showing lines: 14120-14220

14120:                         'session_receipt':locals().get('session_receipt'),
14121:                         'timing':timing,
14122:                     })
14123:                 except (BrokenPipeError,ConnectionAbortedError,ConnectionResetError):
14124:                     pass
14125:                 return
14126:             finally:
14127:                 web_chat_stream_lock.release()
14128:         # GUARDED_STREAMING_PHASE2_ROUTE_END
14129:         if path=='/api/chat/send':
14130:             text=(d.get('message') or '').strip()
14131:             use_active=bool(d.get('use_active_image'))
14132:             try:
14133:                 image=validate_mission_image(d.get('image'))
14134:             except MissionRequestError as exc:
14135:                 self.send_response(exc.status)
14136:                 self.send_header('Content-Type','application/json; charset=utf-8')
14137:                 self.send_header('Cache-Control','no-store')
14138:                 self.end_headers()
14139:                 self.wfile.write(json.dumps({'ok':False,'message':str(exc)}).encode('utf-8'))
14140:                 return
14141:             if not text and not image and not use_active:
14142:                 self.js({'ok':False,'message':'Empty message.'})
14143:                 return
14144:             text=text or 'Describe this image.'
14145:             profile=active_chat_profile()
14146:             if (image or use_active) and not bool(profile.get('vision')):
14147:                 self.js({'ok':False,'message':'A verified Fast Vision or Quality Vision profile must be explicitly active. No model switch occurred.'});return
14148:             if (image or use_active) and is_explicit_engineer_command(text):
14149:                 self.js({'ok':False,'message':'Engineer image inspection is not enabled.'});return
14150: 
14151:             session_receipt=ensure_web_mission_session()
14152:             context=prepare_mission_image_context(messages,text,image,use_active)
14153:             effective_image=context['image']
14154:             web_mission_session.add('ERIC',context['history_user_message']['content'])
14155:             explicit_engineer=is_explicit_engineer_command(text)
14156: 
14157:             if explicit_engineer:
14158:                 mission_id=web_mission_session.session_id or ''
14159:                 correlation_id=new_airlock_correlation_id()
14160:                 route=direct_mission(
14161:                     text,
14162:                     actor='operator',
14163:                     operator_approved=True,
14164:                     correlation_id=correlation_id,
14165:                     mission_id=mission_id,
14166:                     audit=True,
14167:                 )
14168:                 correlation_id=route.get('correlation_id') or correlation_id
14169:                 authorization=route.get('authorization') or {}
14170:                 director_audit_receipt=route.get('audit_receipt') or {}
14171:                 read_only_allowed=web_engineer_read_only_allowed(text)
14172:                 inspect_authorization=None
14173:                 inspect_audit_receipt=None
14174:                 director_route_ok=(
14175:                     route.get('agent')=='engineer'
14176:                     and bool(authorization.get('allowed'))
14177:                     and bool(director_audit_receipt.get('verified'))
14178:                 )
14179:                 if director_route_ok:
14180:                     inspect_authorization=authorize_department_route(
14181:                         'operator',
14182:                         'engineering_airlock',
14183:                         'inspect',
14184:                         operator_approved=True,
14185:                     )
14186:                     inspect_audit_receipt=record_authorization_decision(
14187:                         inspect_authorization,
14188:                         correlation_id=correlation_id,
14189:                         mission_id=mission_id,
14190:                     )
14191:                 inspect_allowed=bool(
14192:                     inspect_authorization
14193:                     and inspect_authorization.allowed
14194:                 )
14195:                 inspect_audit_verified=bool(
14196:                     inspect_audit_receipt
14197:                     and inspect_audit_receipt.get('verified')
14198:                 )
14199:                 route_ok=(
14200:                     director_route_ok
14201:                     and read_only_allowed
14202:                     and inspect_allowed
14203:                     and inspect_audit_verified
14204:                 )
14205:                 route_receipt=make_tool_receipt(
14206:                     'webui.department_route',
14207:                     'verified' if route_ok else 'denied',
14208:                     checks=[
14209:                         {'id':'explicit_engineer_command','ok':explicit_engineer,'message':'The operator used an explicit Engineer command.'},
14210:                         {'id':'director_selected_engineer','ok':route.get('agent')=='engineer','message':'Director selected Engineer.'},
14211:                         {'id':'engineering_airlock_allowed','ok':bool(authorization.get('allowed')),'message':authorization.get('reason','No authorization reason returned.')},
14212:                         {'id':'director_audit_verified','ok':bool(director_audit_receipt.get('verified')),'message':'Director Airlock route decision was written to the verified audit chain.'},
14213:                         {'id':'webui_engineer_read_only_request','ok':read_only_allowed,'message':'WebUI Engineer allows inspection only and denies project-memory write commands.'},
14214:                         {'id':'engineer_inspect_allowed','ok':inspect_allowed,'message':getattr(inspect_authorization,'reason','Engineer inspect stage did not run.')},
14215:                         {'id':'engineer_inspect_audit_verified','ok':inspect_audit_verified,'message':'Engineer inspection authorization was written to the verified audit chain.'},
14216:                     ],
14217:                     details={
14218:                         'route':route.get('agent'),
14219:                         'authorization':authorization,
14220:                         'director_audit_receipt':director_audit_receipt,

More content is available. Continue with:
/engineer workshop read core\foxai_web.py :: LINES 14221-14420

Safety: exact-path, bounded, read-only file access; nothing changed.
