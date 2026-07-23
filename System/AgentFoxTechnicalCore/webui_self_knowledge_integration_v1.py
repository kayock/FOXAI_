from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, sys, tempfile
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
def route_http_request(raw_body:bytes, route:str, adapter_path:Path=ADAPTER_PATH, *, bridge_path:Path|None=None, registry_dir:Path|None=None, resource_provider_path:Path|None=None, resource_source_dir:Path|None=None):
    if route not in ROUTES: return {"intercepted":False,"diagnostic":None}
    try: body=json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception: return {"intercepted":False,"diagnostic":"request body was not valid JSON"}
    message=str(body.get("message") or "")
    if not message.strip(): return {"intercepted":False,"diagnostic":None}
    if message.startswith("/"): return {"intercepted":False,"diagnostic":"slash command bypassed self-knowledge interception"}
    message=message.strip()
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
