#!/usr/bin/env python3
"""USB C3K controlled normal lifecycle test.

Stdlib orchestration plus psutil loaded only from the committed isolated target.
Binds to exact accepted C3J evidence, runs the installed normal controller in
its no-browser test mode, verifies exact ownership/health/localhost networking,
requests graceful stop, and leaves ComfyUI stopped.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import site
import socket
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from typing import Any

SUCCESS = "C3K_NORMAL_LIFECYCLE_VERIFIED_STOPPED_READY_FOR_C3L_REVIEW"
BLOCKED = "C3K_BLOCKED_FAIL_CLOSED"
MANAGER_REL = Path("System/PortableRuntime/manage_comfyui_normal.py")
POLICY_REL = Path("System/PortableRuntime/COMFYUI_NORMAL_POLICY.json")
TARGET_REL = Path("Runtime/ComfyUI/site-packages")
STATE_REL = Path("Runtime/ComfyUI/state/normal_instance.json")
LOGS_REL = Path("Runtime/ComfyUI/logs/normal")
SOURCE_EXCLUDES = {".git", ".venv", "venv", "models", "user", "temp", "input", "output"}

class GateError(RuntimeError):
    def __init__(self, message: str, code: int = 20):
        super().__init__(message); self.code = code

def utc_now(): return datetime.now(timezone.utc).isoformat()
def run_id(): return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def sha256_file(path: Path, block=1024*1024):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b=f.read(block)
            if not b: break
            h.update(b)
    return h.hexdigest()

def load_json(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def write_json(path: Path, value: Any): path.write_text(json.dumps(value,indent=2,default=str),encoding="utf-8",newline="\n")

def verify_file(path: Path, size: int, digest: str, label: str):
    if not path.is_file() or path.is_symlink(): raise GateError(f"{label} missing or unsafe: {path}",21)
    actual_size=path.stat().st_size; actual_hash=sha256_file(path)
    if actual_size!=int(size) or actual_hash.lower()!=str(digest).lower():
        raise GateError(f"{label} changed: {path}",21)
    return {"path":str(path),"size_bytes":actual_size,"sha256":actual_hash,"verified":True}

def verify_package(package: Path, output: Path):
    m=load_json(package/"PACKAGE_INTEGRITY.json"); rows=[]
    for r in m.get("files",[]): rows.append(verify_file(package/Path(r["path"]),r["size_bytes"],r["sha256"],f"C3K package {r['path']}"))
    result={"verified":True,"file_count":len(rows),"files":rows}; write_json(output/"package_verification.json",result); return result

def verify_c3j(root: Path, package: Path, output: Path):
    b=load_json(package/"EXPECTED_C3J_BINDING.json")
    base=(root/Path(b["c3j_relative_output"])).resolve(strict=True)
    verify_file(base/"evidence_integrity.json",(base/"evidence_integrity.json").stat().st_size,b["evidence_integrity_sha256"],"C3J evidence manifest")
    rows=[]
    for r in b["c3j_evidence_files"]: rows.append(verify_file(base/Path(r["file"]),r["size_bytes"],r["sha256"],f"C3J evidence {r['file']}"))
    for name,key in (("classification.json","classification_sha256"),("receipt.json","receipt_sha256"),("C3K_TEST_CONTRACT.json","contract_sha256")):
        if sha256_file(base/name)!=b[key]: raise GateError(f"Exact C3J {name} changed",21)
    c=load_json(base/"classification.json"); rec=load_json(base/"receipt.json"); con=load_json(base/"C3K_TEST_CONTRACT.json")
    if not c.get("verified") or c.get("mode")!=b["expected_classification"]: raise GateError("C3J classification is not accepted",21)
    if not rec.get("verified") or rec.get("comfyui_launched") or rec.get("network_access"): raise GateError("C3J receipt violates accepted no-launch state",21)
    if con.get("test_sequence")!=["status STOPPED","start no-browser","status HEALTHY","stop","status STOPPED"]: raise GateError("C3J C3K contract changed",21)
    result={"verified":True,"base":str(base),"evidence_file_count":len(rows),"classification":c.get("mode"),"contract":con}
    write_json(output/"c3j_input_verification.json",result); return b

def verify_live(root: Path, binding: dict, output: Path, phase: str):
    rows=[]
    for r in binding["integrated_files"]: rows.append(verify_file(root/Path(r["relative_path"]),r["size_bytes"],r["sha256"],f"integrated file {r['relative_path']}"))
    result={"verified":True,"phase":phase,"file_count":len(rows),"files":rows}; write_json(output/f"integrated_files_{phase}.json",result); return result

def verify_protected(root: Path, binding: dict, output: Path, phase: str):
    rows=[]
    for r in binding["protected_files"]: rows.append(verify_file(root/Path(r["path"]),r["size_bytes"],r["sha256"],f"protected file {r['path']}"))
    result={"verified":True,"phase":phase,"file_count":len(rows),"files":rows}; write_json(output/f"protected_files_{phase}.json",result); return result

def verify_target(root: Path, binding: dict, output: Path, phase: str):
    ib=binding["c3e_inventory"]; invpath=root/Path(ib["relative_path"]); verify_file(invpath,ib["size_bytes"],ib["sha256"],"sealed C3E inventory")
    inv=load_json(invpath); target=root/TARGET_REL
    if not target.is_dir() or target.is_symlink(): raise GateError("Isolated target missing or unsafe",21)
    expected={}; dup=[]; missing=[]; mismatch=[]; syms=[]; actual_bytes=0; agg=hashlib.sha256()
    for r in inv.get("files",[]):
        rel=str(r["path"]); key=rel.casefold()
        if key in expected: dup.append(rel)
        expected[key]=r
        agg.update(rel.casefold().encode()); agg.update(b"\0"); agg.update(str(int(r["size_bytes"])).encode("ascii")); agg.update(b"\0"); agg.update(str(r["sha256"]).encode("ascii")); agg.update(b"\n")
        p=target/Path(rel)
        if not p.exists(): missing.append(rel); continue
        if p.is_symlink(): syms.append(rel); continue
        if not p.is_file(): mismatch.append({"path":rel,"issue":"not_file"}); continue
        s=p.stat().st_size; h=sha256_file(p); actual_bytes+=s
        if s!=int(r["size_bytes"]) or h!=r["sha256"]: mismatch.append({"path":rel,"actual_size":s,"actual_sha256":h})
    unexpected=[]; count=0
    for p in target.rglob("*"):
        if p.is_symlink():
            rel=p.relative_to(target).as_posix()
            if rel not in syms: syms.append(rel)
        elif p.is_file():
            count+=1; rel=p.relative_to(target).as_posix()
            if rel.casefold() not in expected: unexpected.append(rel)
    e=binding["isolated_target"]; tree=agg.hexdigest()
    ok=not(dup or missing or mismatch or syms or unexpected) and count==e["file_count"] and actual_bytes==e["total_bytes"] and tree==e["tree_sha256"]
    result={"verified":ok,"phase":phase,"file_count":count,"total_bytes":actual_bytes,"tree_sha256":tree,"missing":missing,"unexpected":unexpected,"mismatches":mismatch,"symlinks":syms}
    write_json(output/f"isolated_target_{phase}.json",result)
    if not ok: raise GateError(f"Isolated target failed {phase} verification",27 if phase=="after" else 21)
    return result

def source_snapshot(comfy: Path):
    d={}
    for p in comfy.rglob("*"):
        if p.is_symlink() or not p.is_file(): continue
        parts=p.relative_to(comfy).parts
        if parts and parts[0].casefold() in SOURCE_EXCLUDES: continue
        rel=p.relative_to(comfy).as_posix(); d[rel.casefold()]={"path":rel,"size_bytes":p.stat().st_size,"sha256":sha256_file(p)}
    return d

def compare_snapshot(a,b):
    added=[b[k] for k in sorted(b.keys()-a.keys())]; removed=[a[k] for k in sorted(a.keys()-b.keys())]; changed=[]
    for k in sorted(a.keys()&b.keys()):
        if a[k]["size_bytes"]!=b[k]["size_bytes"] or a[k]["sha256"]!=b[k]["sha256"]: changed.append({"before":a[k],"after":b[k]})
    return {"verified":not(added or removed or changed),"added":added,"removed":removed,"changed":changed}

def runtime_non_target_snapshot(runtime: Path):
    d={}
    if not runtime.exists(): return d
    for p in runtime.rglob("*"):
        try: rel=p.relative_to(runtime)
        except ValueError: continue
        if rel.parts and rel.parts[0].casefold()=="site-packages": continue
        if p.is_symlink(): d[rel.as_posix().casefold()]={"path":rel.as_posix(),"type":"symlink","size_bytes":0,"sha256":"SYMLINK"}
        elif p.is_file(): d[rel.as_posix().casefold()]={"path":rel.as_posix(),"type":"file","size_bytes":p.stat().st_size,"sha256":sha256_file(p)}
        elif p.is_dir(): d[rel.as_posix().casefold()]={"path":rel.as_posix(),"type":"dir","size_bytes":0,"sha256":"DIR"}
    return d

def run_manager(root: Path, action: list[str], output: Path, label: str, timeout=330):
    py=root/"Runtime/Desktop/python/python.exe"; manager=root/MANAGER_REL
    cmd=[str(py),"-I","-B","-S",str(manager),"--root",str(root),"--json",*action]
    started=utc_now(); t=time.monotonic()
    cp=subprocess.run(cmd,cwd=str(root),env=clean_env(),capture_output=True,text=True,timeout=timeout)
    record={"command":cmd,"started":started,"completed":utc_now(),"elapsed_seconds":round(time.monotonic()-t,3),"returncode":cp.returncode,"stdout":cp.stdout,"stderr":cp.stderr}
    write_json(output/f"{label}_execution.json",record)
    result=None
    for line in reversed([x.strip() for x in cp.stdout.splitlines() if x.strip()]):
        try:
            v=json.loads(line)
            if isinstance(v,dict): result=v; break
        except json.JSONDecodeError: pass
    if result is None: result={"ok":False,"state":"UNPARSEABLE","message":"Manager did not emit a JSON result"}
    write_json(output/f"{label}_result.json",result)
    return cp.returncode,result

def clean_env():
    e=os.environ.copy(); e.pop("PYTHONHOME",None); e.pop("PYTHONPATH",None); e.update({"PYTHONNOUSERSITE":"1","PYTHONDONTWRITEBYTECODE":"1","HF_HUB_DISABLE_TELEMETRY":"1","DO_NOT_TRACK":"1"}); return e

def activate_psutil(root: Path):
    site.addsitedir(str(root/TARGET_REL)); import psutil; return psutil

def network_observation(psutil, pids):
    rows=[]; external=[]
    loop={"127.0.0.1","::1","0.0.0.0","::"}
    with contextlib.suppress(Exception):
        for c in psutil.net_connections(kind="inet"):
            if c.pid not in pids: continue
            local=None; remote=None
            if c.laddr: local={"ip":getattr(c.laddr,"ip",c.laddr[0]),"port":getattr(c.laddr,"port",c.laddr[1])}
            if c.raddr: remote={"ip":getattr(c.raddr,"ip",c.raddr[0]),"port":getattr(c.raddr,"port",c.raddr[1])}
            row={"pid":c.pid,"status":str(c.status),"local":local,"remote":remote}; rows.append(row)
            if remote and remote["ip"] not in loop: external.append(row)
    listeners=[r for r in rows if r["status"].upper()=="LISTEN"]
    ok=not external and listeners and all(r["local"] and r["local"]["ip"] in {"127.0.0.1","::1"} and r["local"]["port"]==8188 for r in listeners)
    return {"verified":bool(ok),"pids":sorted(pids),"connections":rows,"external_connections":external,"listeners":listeners}

def validate_healthy(result, root: Path):
    if result.get("state")!="HEALTHY" or not result.get("ok") or not result.get("managed"): return False,"status not managed HEALTHY"
    v=result.get("verification") or {}; state=result.get("recorded_state") or {}
    if not all([v.get("child_owned"),v.get("supervisor_owned"),v.get("loopback_only"),(v.get("health") or {}).get("ok")]): return False,"ownership/health checks incomplete"
    if state.get("policy_id")!="FOXAI_COMFYUI_SAFE_NORMAL_CPU_V1" or state.get("source")!="test": return False,"policy/source mismatch"
    if state.get("custom_nodes_disabled") is not True or state.get("listen")!="127.0.0.1" or int(state.get("port") or 0)!=8188: return False,"launch policy mismatch"
    sup=(v.get("supervisor") or {}).get("cmdline") or []
    folded=[str(x).casefold() for x in sup]
    for token in ("--no-browser","--source","test"):
        if token not in folded: return False,f"supervisor missing {token}"
    child=(v.get("child") or {}).get("cmdline") or []
    cf=[str(x).casefold() for x in child]
    for token in ("--cpu","--disable-all-custom-nodes","127.0.0.1","8188"):
        if token not in cf: return False,f"child missing {token}"
    return True,"verified"

def copy_run_logs(root: Path, output: Path, healthy: dict):
    state=healthy.get("recorded_state") or {}; logdir=Path(str(state.get("log_dir") or ""))
    dest=output/"NORMAL_RUN_LOGS"; rows=[]
    try: logdir.resolve(strict=True).relative_to((root/LOGS_REL).resolve(strict=True))
    except Exception: raise GateError("Normal run log directory escaped policy boundary",24)
    dest.mkdir()
    for name in ("stdout.log","stderr.log","start_receipt.json","health_receipt.json","stop_receipt.json","stop.request.json"):
        p=logdir/name
        if p.is_file() and not p.is_symlink():
            q=dest/name; shutil.copy2(p,q); rows.append({"file":name,"size_bytes":q.stat().st_size,"sha256":sha256_file(q)})
    statep=root/STATE_REL
    if statep.is_file():
        q=dest/"normal_instance_final.json"; shutil.copy2(statep,q); rows.append({"file":q.name,"size_bytes":q.stat().st_size,"sha256":sha256_file(q)})
    result={"verified":True,"source_log_dir":str(logdir),"files":rows}; write_json(output/"normal_run_log_copy.json",result); return result

def make_review_zip(output: Path):
    zip_path=output/"UPLOAD_THIS_C3K_REVIEW.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(output.rglob("*")):
            if p.is_file() and p!=zip_path: z.write(p,p.relative_to(output).as_posix())
    return zip_path

def finalize_integrity(output: Path):
    rows=[]
    for p in sorted(output.rglob("*")):
        if p.is_file() and p.name not in {"evidence_integrity.json","UPLOAD_THIS_C3K_REVIEW.zip"}:
            rows.append({"file":p.relative_to(output).as_posix(),"size_bytes":p.stat().st_size,"sha256":sha256_file(p)})
    result={"verified":True,"file_count":len(rows),"files":rows}; write_json(output/"evidence_integrity.json",result); return result

def parse_args():
    p=argparse.ArgumentParser(); p.add_argument("--root",required=True); p.add_argument("--package-root",required=True); return p.parse_args()

def main():
    args=parse_args(); root=Path(args.root).resolve(strict=True); package=Path(args.package_root).resolve(strict=True)
    outparent=package/"TEST_OUTPUT"; outparent.mkdir(exist_ok=True); output=outparent/run_id(); output.mkdir(exist_ok=False)
    started=utc_now(); classification=BLOCKED; findings=[]; initial=None; healthy=None; final=None; started_instance=False
    source_before=None; runtime_before=None; binding=None
    print("[C3K] Verifying package, accepted C3J evidence, live files, and isolated target...")
    try:
        verify_package(package,output); binding=verify_c3j(root,package,output); verify_live(root,binding,output,"before"); verify_protected(root,binding,output,"before"); verify_target(root,binding,output,"before")
        source_before=source_snapshot(root/"ComfyUI"); runtime_before=runtime_non_target_snapshot(root/"Runtime/ComfyUI")
        rc,initial=run_manager(root,["status"],output,"initial_status",60)
        if rc!=0 or initial.get("state")!="STOPPED" or not initial.get("ok"): raise GateError(f"Initial normal lifecycle state is not STOPPED: {initial.get('state')}",22)
        print("[C3K] Initial state verified STOPPED. Starting Safe Normal CPU with no browser...")
        started_instance=True
        rc,start=run_manager(root,["spawn","--source","test"],output,"start_no_browser",330)
        if rc!=0 or start.get("state")!="HEALTHY" or not start.get("ok"): raise GateError(f"Normal no-browser start failed: {start.get('state')}",23)
        rc,healthy=run_manager(root,["status"],output,"healthy_status",60)
        ok,why=validate_healthy(healthy,root)
        if rc!=0 or not ok: raise GateError(f"Healthy status validation failed: {why}",24)
        psutil=activate_psutil(root); v=healthy["verification"]; pids={int(v["child"]["pid"]),int(v["supervisor"]["pid"])}
        net=network_observation(psutil,pids); write_json(output/"network_observation.json",net)
        if not net["verified"]: raise GateError("Normal lifecycle network observation was not localhost-only",24)
        print("[C3K] HEALTHY and controller ownership verified. Requesting graceful stop...")
        rc,stop=run_manager(root,["stop"],output,"graceful_stop",60)
        if rc!=0 or stop.get("state")!="STOPPED" or not stop.get("ok"): raise GateError(f"Graceful stop failed: {stop.get('state')}",25)
        started_instance=False
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            rc,final=run_manager(root,["status"],output,"final_status",60)
            if rc==0 and final.get("state")=="STOPPED" and final.get("ok"): break
            time.sleep(.5)
        if not final or final.get("state")!="STOPPED" or not final.get("ok"): raise GateError("Final status did not reach STOPPED",26)
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            s.settimeout(.5); port_closed=s.connect_ex(("127.0.0.1",8188))!=0
        write_json(output/"port_close_verification.json",{"verified":port_closed,"host":"127.0.0.1","port":8188})
        if not port_closed: raise GateError("Port 8188 remained open after stop",26)
        copy_run_logs(root,output,healthy)
        verify_target(root,binding,output,"after"); verify_live(root,binding,output,"after"); verify_protected(root,binding,output,"after")
        source_after=source_snapshot(root/"ComfyUI"); sc=compare_snapshot(source_before,source_after); write_json(output/"source_boundary_comparison.json",sc)
        if not sc["verified"]: raise GateError("ComfyUI source changed during lifecycle test",27)
        runtime_after=runtime_non_target_snapshot(root/"Runtime/ComfyUI")
        def allowed_storage_path(value):
            p=value.casefold()
            return p=="state" or p.startswith("state/") or p=="logs" or p=="logs/normal" or p.startswith("logs/normal/")
        changes=compare_snapshot(runtime_before,runtime_after); bad=[]
        for kind in ("added","removed"):
            for r in changes[kind]:
                if not allowed_storage_path(r["path"]): bad.append({"kind":kind,"row":r})
        for r in changes["changed"]:
            path=(r.get("after") or r.get("before"))["path"]
            if not allowed_storage_path(path): bad.append({"kind":"changed","row":r})
        storage={"verified":not bad,"changes":changes,"unexpected_outside_state_logs":bad}; write_json(output/"lifecycle_storage_changes.json",storage)
        if bad: raise GateError("Unexpected Runtime/ComfyUI changes outside normal state/log paths",27)
        classification=SUCCESS
    except GateError as exc:
        findings.append(str(exc)); code=exc.code
    except Exception as exc:
        findings.append(f"{type(exc).__name__}: {exc}"); (output/"exception.txt").write_text(traceback.format_exc(),encoding="utf-8"); code=29
    finally:
        # Best-effort graceful cleanup only through the installed controller. Never force-kill.
        if started_instance:
            with contextlib.suppress(Exception):
                rc,cleanup=run_manager(root,["stop"],output,"failure_cleanup_stop",60)
                findings.append(f"Failure cleanup stop result: rc={rc}, state={cleanup.get('state')}")
            with contextlib.suppress(Exception):
                run_manager(root,["status"],output,"failure_cleanup_final_status",60)
        receipt={"action":"foxai_usbc3k_controlled_normal_lifecycle_test","started":started,"completed":utc_now(),"root":str(root),"output":str(output),"verified":classification==SUCCESS,"classification":classification,"sequence":["STOPPED","start no-browser","HEALTHY","graceful stop","STOPPED"],"browser_opened":False,"custom_nodes_disabled":True,"listen":"127.0.0.1:8188","force_kill":False,"network_external":False,"comfyui_left_running":False if classification==SUCCESS else None,"blocking_findings":findings}
        write_json(output/"receipt.json",receipt); write_json(output/"classification.json",{"mode":classification,"verified":classification==SUCCESS,"blocking_findings":findings,"next_gate":"Upload UPLOAD_THIS_C3K_REVIEW.zip for exact review."})
        report=["# FOXAI USB C3K — Controlled Normal Lifecycle Test","",f"- Classification: `{classification}`",f"- Verified: `{classification==SUCCESS}`","- Sequence: `STOPPED -> no-browser start -> HEALTHY -> graceful stop -> STOPPED`","- Custom nodes: `disabled`","- Bind: `127.0.0.1:8188`","- Force kill: `False`","- Browser opened: `False`","", "## Blocking findings", *([f"- {x}" for x in findings] or ["- None"])]
        (output/"report.md").write_text("\n".join(report)+"\n",encoding="utf-8",newline="\n")
        finalize_integrity(output); z=make_review_zip(output); print(f"[C3K] Review package: {z}")
    if classification==SUCCESS:
        print("[COMPLETE] C3K normal lifecycle is healthy and ComfyUI is stopped."); return 0
    print(f"[STOPPED] C3K failed closed: {findings[-1] if findings else 'unknown'}"); return code

if __name__=="__main__": raise SystemExit(main())
