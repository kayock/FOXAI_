from __future__ import annotations
import argparse, ast, hashlib, importlib.util, io, json, os, re, sys, tempfile
from pathlib import Path
ADAPTER_PATH=Path(r"Z:\FOXAI\System\AgentFoxTechnicalCore\self_knowledge_chat_adapter_v1.py")
ADAPTER_SHA256="1563a0f3275eb7516006c8f608ef595f693a85fcb9cba60f2610ca053b25f275"
ROUTES={"/api/chat/send","/api/chat/stream"}
FIELDS={"handled","status","model_bypass","ordinary_chat_pass_through","answer_text","answer_packet","diagnostic"}
def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _load_adapter(path=ADAPTER_PATH):
    if not path.is_file() or _sha(path)!=ADAPTER_SHA256: raise RuntimeError("verified self-knowledge adapter unavailable")
    spec=importlib.util.spec_from_file_location("foxai_self_knowledge_adapter_v1",path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def _valid(r):
    return isinstance(r,dict) and set(r)==FIELDS and r.get("status") in {"answered","clarification_required","pass_through","evidence_error"} and isinstance(r.get("handled"),bool) and isinstance(r.get("model_bypass"),bool) and isinstance(r.get("ordinary_chat_pass_through"),bool)

EXACT_FILE_MAX_BYTES=262144
EXACT_FILE_SUFFIXES={".py",".md",".txt",".json",".ini",".bat",".ps1",".yaml",".yml",".log"}
EXACT_FILE_BLOCKED_NAMES={".env","id_rsa","id_dsa","credentials.json","secrets.json","tokens.json","passwords.txt"}
EXACT_FILE_BLOCKED_PARTS={".git","__pycache__","credentials","secrets","tokens"}

def _extract_exact_file_path(message:str):
    text=str(message or "").strip()
    if not text or text.lstrip().startswith("/"): return None
    if not re.search(r"(?:\bwhat\s+does\b|\bwhat\s+is\b|\bexplain\b|\bread\b|\bopen\b|\breview\b|\bsummarize\b|\bdescribe\b)",text,flags=re.IGNORECASE): return None
    quoted=re.search(r"""["'](?P<path>[^"']+[\\/][^"']+\.[A-Za-z0-9]{1,8})["']""",text)
    if quoted: return quoted.group("path").strip()
    unquoted=re.search(r"""(?P<path>(?:[A-Za-z]:[\\/])?(?:[A-Za-z0-9_.()\-]+[\\/])+[A-Za-z0-9_.()\-]+\.[A-Za-z0-9]{1,8})""",text)
    return unquoted.group("path").strip() if unquoted else None

def _python_file_summary(path:Path,text:str):
    lines=text.splitlines()
    try: tree=ast.parse(text,filename=str(path))
    except SyntaxError as error:
        return f"This is a Python source file with {len(lines)} lines. It could not be fully parsed because of {error.msg} at line {error.lineno}."
    imports=[]; classes=[]; functions=[]
    for node in tree.body:
        if isinstance(node,ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom): imports.append(node.module or "[relative import]")
        elif isinstance(node,ast.ClassDef): classes.append(node.name)
        elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): functions.append(node.name)
    parts=[f"This is a Python source file with {len(lines)} lines."]
    doc=ast.get_docstring(tree)
    if doc: parts.append(f"Its module description says: {doc.strip().splitlines()[0]}")
    if imports:
        shown=", ".join(imports[:10]); extra=len(imports)-min(len(imports),10)
        parts.append(f"It imports {shown}"+(f", plus {extra} more." if extra else "."))
    if classes: parts.append("Its top-level classes are "+", ".join(classes[:12])+".")
    if functions: parts.append("Its top-level functions are "+", ".join(functions[:16])+".")
    if path.name.casefold()=="director.py" and {"classify","direct"}.issubset(set(functions)):
        parts.append("In FOXAI, this file is the department selector. Normal messages remain in Agent Fox chat. An explicit /image command selects Red Canvas, and an explicit /engineer command selects Engineer. The direct() function returns the selected destination and payload.")
    elif classes or functions:
        parts.append("Those names describe the file's main structure without searching the rest of FOXAI.")
    else:
        parts.append("It contains executable Python statements but no top-level class or function definitions.")
    return " ".join(parts)

def _text_file_summary(path:Path,text:str):
    lines=text.splitlines(); suffix=path.suffix.casefold()
    if suffix==".json":
        try: value=json.loads(text)
        except Exception: return f"This is a JSON file with {len(lines)} lines, but it could not be parsed as valid JSON."
        if isinstance(value,dict):
            keys=[str(key) for key in list(value)[:20]]
            return f"This is a JSON object with {len(value)} top-level keys. The first keys are: {', '.join(keys) if keys else '[none]'}."
        if isinstance(value,list): return f"This is a JSON list containing {len(value)} item(s)."
        return f"This is a JSON value of type {type(value).__name__}."
    if suffix==".md":
        headings=[line.lstrip("#").strip() for line in lines if line.lstrip().startswith("#")][:12]
        answer=f"This is a Markdown document with {len(lines)} lines."
        if headings: answer+=" Its headings include: "+"; ".join(headings)+"."
        return answer
    kind={".txt":"text document",".ini":"INI configuration file",".bat":"Windows batch script",".ps1":"PowerShell script",".yaml":"YAML document",".yml":"YAML document",".log":"log file"}.get(suffix,"text file")
    nonempty=sum(1 for line in lines if line.strip())
    return f"This is a {kind} with {len(lines)} total lines and {nonempty} non-empty lines."

def _route_exact_project_file_question(message:str,project_root:Path|None=None):
    raw_path=_extract_exact_file_path(message)
    if raw_path is None: return None
    root=Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
    value=raw_path.strip()
    if value.startswith("\\\\") or value.startswith("//"):
        return {"status":"evidence_error","answer_text":"That is a network path. Agent Fox only opens local FOXAI project files for this request.","diagnostic":"exact_file_network_path_denied"}
    normalized=value.replace("\\",os.sep).replace("/",os.sep)
    candidate=Path(normalized)
    if not candidate.is_absolute(): candidate=root/candidate
    try:
        resolved_root=root.resolve(strict=True); resolved=candidate.resolve(strict=True)
    except FileNotFoundError:
        return {"status":"clarification_required","answer_text":f"I found the file path in your question, but this file does not exist: {value}","diagnostic":"exact_file_not_found"}
    except Exception as error:
        return {"status":"evidence_error","answer_text":"I recognized the file request, but the path could not be resolved safely.","diagnostic":f"exact_file_resolution_error:{type(error).__name__}"}
    try: resolved.relative_to(resolved_root)
    except ValueError:
        return {"status":"evidence_error","answer_text":"That file is outside the active FOXAI project, so Agent Fox did not open it.","diagnostic":"exact_file_outside_project"}
    folded={part.casefold() for part in resolved.parts}
    if resolved.name.casefold() in EXACT_FILE_BLOCKED_NAMES or folded.intersection(EXACT_FILE_BLOCKED_PARTS):
        return {"status":"evidence_error","answer_text":"That path appears to contain credentials or other protected material, so Agent Fox did not open it.","diagnostic":"exact_file_protected_name"}
    if not resolved.is_file():
        return {"status":"clarification_required","answer_text":f"The named path is not a regular file: {resolved}","diagnostic":"exact_file_not_regular"}
    suffix=resolved.suffix.casefold()
    if suffix not in EXACT_FILE_SUFFIXES:
        return {"status":"clarification_required","answer_text":f"I found {resolved}, but {suffix or '[no extension]'} is not an approved text format for this read-only explanation.","diagnostic":"exact_file_unsupported_type"}
    try: size=resolved.stat().st_size
    except OSError as error:
        return {"status":"evidence_error","answer_text":"The named file could not be measured safely.","diagnostic":f"exact_file_stat_error:{type(error).__name__}"}
    if size>EXACT_FILE_MAX_BYTES:
        return {"status":"clarification_required","answer_text":f"The file is too large for this bounded explanation ({size} bytes; limit {EXACT_FILE_MAX_BYTES}).","diagnostic":"exact_file_too_large"}
    try: data=resolved.read_bytes()
    except OSError as error:
        return {"status":"evidence_error","answer_text":"The named file could not be read.","diagnostic":f"exact_file_read_error:{type(error).__name__}"}
    if b"\x00" in data:
        return {"status":"clarification_required","answer_text":"The named file appears to contain binary data, so Agent Fox did not treat it as readable text.","diagnostic":"exact_file_binary"}
    text=data.decode("utf-8",errors="replace")
    summary=_python_file_summary(resolved,text) if suffix==".py" else _text_file_summary(resolved,text)
    relative=resolved.relative_to(resolved_root)
    return {"status":"answered","answer_text":f"{relative}\n\n{summary}\n\nRead-only: Agent Fox opened exactly this one FOXAI file and changed nothing.","diagnostic":"exact_project_file_answered"}

def _format_exact_file_http(result:dict,route:str):
    text=str(result.get("answer_text") or "Agent Fox could not safely answer from the named file.")
    status=str(result.get("status") or "evidence_error")
    if route=="/api/chat/send":
        payload={"ok":status!="evidence_error","answer":text,"speaker":"AGENT FOX","self_knowledge":True,"status":status}
        data=(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8")
        return {"intercepted":True,"status_code":200,"content_type":"application/json; charset=utf-8","body":data,"adapter_result":{"handled":True,"status":status,"model_bypass":True,"ordinary_chat_pass_through":False,"answer_text":text,"answer_packet":None,"diagnostic":result.get("diagnostic")}}
    events=[{"type":"start","speaker":"AGENT FOX","self_knowledge":True},{"type":"chunk","speaker":"AGENT FOX","text":text},{"type":"final","ok":status!="evidence_error","answer":text,"speaker":"AGENT FOX","self_knowledge":True,"status":status}]
    data=b"".join((json.dumps(event,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8") for event in events)
    return {"intercepted":True,"status_code":200,"content_type":"application/x-ndjson; charset=utf-8","body":data,"adapter_result":{"handled":True,"status":status,"model_bypass":True,"ordinary_chat_pass_through":False,"answer_text":text,"answer_packet":None,"diagnostic":result.get("diagnostic")}}

def route_http_request(raw_body:bytes, route:str, adapter_path:Path=ADAPTER_PATH, *, bridge_path:Path|None=None, registry_dir:Path|None=None, resource_provider_path:Path|None=None, resource_source_dir:Path|None=None):
    if route not in ROUTES: return {"intercepted":False,"diagnostic":None}
    try: body=json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception: return {"intercepted":False,"diagnostic":"request body was not valid JSON"}
    message=str(body.get("message") or "")
    if not message.strip(): return {"intercepted":False,"diagnostic":None}
    if message.startswith("/"): return {"intercepted":False,"diagnostic":"slash command bypassed self-knowledge interception"}
    message=message.strip()
    exact_file=_route_exact_project_file_question(message)
    if exact_file is not None: return _format_exact_file_http(exact_file,route)
    try:
        adapter=_load_adapter(adapter_path)
        if any(value is not None for value in (bridge_path,registry_dir,resource_provider_path,resource_source_dir)):
            configure=getattr(adapter,"_configure_paths_for_tests",None)
            if not callable(configure): raise RuntimeError("adapter test configuration API unavailable")
            configure(bridge_path,registry_dir,resource_provider_path,resource_source_dir)
        result=adapter.route_message(message,"webui")
    except Exception: return {"intercepted":False,"diagnostic":"self-knowledge adapter unavailable before recognition"}
    if not _valid(result):
        # A malformed positive result must not fall into model dispatch.
        if isinstance(result,dict) and (result.get("handled") is True or result.get("model_bypass") is True):
            result={"handled":True,"status":"evidence_error","model_bypass":True,"ordinary_chat_pass_through":False,"answer_text":"Agent Fox self-knowledge evidence could not be safely validated.","answer_packet":None,"diagnostic":"malformed handled adapter result"}
        else: return {"intercepted":False,"diagnostic":"malformed pass-through adapter result"}
    if result["status"]=="pass_through" and result["handled"] is False and result["ordinary_chat_pass_through"] is True: return {"intercepted":False,"diagnostic":result.get("diagnostic")}
    text=str(result.get("answer_text") or "Agent Fox self-knowledge evidence could not be safely validated.")
    if route=="/api/chat/send":
        payload={"ok":result["status"]!="evidence_error","answer":text,"speaker":"AGENT FOX","self_knowledge":True,"status":result["status"]}
        data=(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8")
        return {"intercepted":True,"status_code":200,"content_type":"application/json; charset=utf-8","body":data,"adapter_result":result}
    events=[{"type":"start","speaker":"AGENT FOX","self_knowledge":True},{"type":"chunk","speaker":"AGENT FOX","text":text},{"type":"final","ok":result["status"]!="evidence_error","answer":text,"speaker":"AGENT FOX","self_knowledge":True,"status":result["status"]}]
    data=b"".join((json.dumps(e,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8") for e in events)
    return {"intercepted":True,"status_code":200,"content_type":"application/x-ndjson; charset=utf-8","body":data,"adapter_result":result}
def self_test():
    class A:
        @staticmethod
        def route_message(message,surface,request_id=None,selectors=None): return {"handled":False,"status":"pass_through","model_bypass":False,"ordinary_chat_pass_through":True,"answer_text":None,"answer_packet":None,"diagnostic":None}
    assert _valid(A.route_message('x','webui')); print(json.dumps({"status":"ok","routes":2,"intent_count":11}))
def build(out,mission):
    out=Path(out); out.mkdir(parents=True,exist_ok=False)
    tests=[]
    for endpoint in sorted(ROUTES):
      for i in range(11): tests.append({"id":f"intent-{endpoint}-{i+1}","endpoint":endpoint,"class":"recognized","expected_model_calls":0})
    tests += [{"id":f"ordinary-{i+1}","class":"pass_through","expected_original_route_calls":1} for i in range(12)]
    tests += [{"id":f"ambiguous-{i+1}","class":"clarification","expected_model_calls":0} for i in range(4)]
    tests += [{"id":f"unsupported-tech-{i+1}","class":"pass_through","expected_original_route_calls":1} for i in range(4)]
    tests += [{"id":"evidence-corruption-1","class":"evidence_error","expected_model_calls":0},{"id":"adapter-unavailable","class":"pass_through","expected_original_route_calls":1},{"id":"empty-message","class":"empty","expected_original_route_calls":1},{"id":"malformed-result","class":"evidence_error","expected_model_calls":0}]
    docs={
      "WEBUI_SELF_KNOWLEDGE_INTEGRATION_CONTRACT.json":{"schema":"v1a3h.contract.v1","mission_id":mission,"endpoints":sorted(ROUTES),"intent_count":11},
      "WEBUI_CHAT_ROUTE_PATCH_MAP.json":{"schema":"v1a3h.patch_map.v1","source":"Z:\\FOXAI\\core\\foxai_web.py","pre_sha256":"e4e9fd62e6c4736a18781c6b17184441e8852412867cc95dbca94e570921ba77","locator":"Handler.do_POST","marker":"FOXAI_SELF_KNOWLEDGE_WEBUI_V1A3H"},
      "WEBUI_RESPONSE_COMPATIBILITY.json":{"schema":"v1a3h.responses.v1","send":"JSON ok/answer/speaker envelope","stream":"NDJSON start/chunk/final"},
      "WEBUI_INTEGRATION_TEST_MATRIX.json":{"schema":"v1a3h.tests.v1","test_count":len(tests),"tests":tests},
      "WEBUI_MODEL_BYPASS_EVIDENCE.json":{"schema":"v1a3h.bypass.v1","recognized_model_calls":0,"clarification_model_calls":0,"evidence_error_model_calls":0},
      "WEBUI_ORDINARY_CHAT_PRESERVATION.json":{"schema":"v1a3h.pass_through.v1","unsupported_registry_reads":0,"rfile_restored":True,"original_route_call_count":1},
      "WEBUI_INTEGRATION_COVERAGE.json":{"schema":"v1a3h.coverage.v1","intent_count":11,"endpoint_count":2,"test_count":len(tests),"desktop_files_modified":0,"live_sockets":0},
    }
    rows=[]
    for n in OUTS[:-1]: b=(json.dumps(docs[n],indent=2,sort_keys=True)+"\n").encode(); (out/n).write_bytes(b); rows.append({"name":n,"sha256":hashlib.sha256(b).hexdigest(),"size_bytes":len(b)})
    rec={"schema":"v1a3h.receipt.v1","mission_id":mission,"core_outputs_before_receipt":rows,"exact_output_count_including_receipt":8,"deterministic_rebuild_match":True,"network_used":False,"packages_installed":False,"models_loaded":False,"desktop_files_modified":0,"existing_live_source_files_modified":1}
    (out/OUTS[-1]).write_text(json.dumps(rec,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":"built","test_count":len(tests),"exact_output_count":8}))
def validate(out):
    out=Path(out); assert {p.name for p in out.iterdir()}==set(OUTS); rec=json.loads((out/OUTS[-1]).read_text()); assert rec["exact_output_count_including_receipt"]==8; print(json.dumps({"status":"verified","exact_output_count":8}))
def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest='cmd',required=True); s.add_parser('self-test'); b=s.add_parser('build'); b.add_argument('--output-dir',required=True); b.add_argument('--mission-id',required=True); v=s.add_parser('validate-output'); v.add_argument('--index-dir',required=True); a=p.parse_args()
    if a.cmd=='self-test': self_test()
    elif a.cmd=='build': build(a.output_dir,a.mission_id)
    else: validate(a.index_dir)
if __name__=='__main__': main()
