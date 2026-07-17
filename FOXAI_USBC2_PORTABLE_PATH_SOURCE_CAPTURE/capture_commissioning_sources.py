from __future__ import annotations
import argparse,ast,datetime as dt,hashlib,importlib,json,shutil,sys,traceback
from pathlib import Path
EXPECTED_HASHES={'COMMISSION_FOXAI_USB.bat': '3a911a8ea2a09b7c99efe857f911ea0f7dddb74d0d0e096346c957b2fd81f38b', 'System/Commissioning/commission_usb.py': 'cd46b557fef1cb6fabccccff96ae73f4a3fcbd146971f80a0971a1b67f1dc869', '00_START_HERE/USB_COMMISSIONING_GUIDE.md': 'bc4e722df598d3b2745714473d788be72826b3230badd4f6640ae4bd434b8c30'}
MODULES=("customtkinter","PIL","requests","psutil")
def now(): return dt.datetime.now(dt.timezone.utc)
def sha(path):
    if not path.is_file(): return None
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()
def verify_manifest(bundle):
    p=bundle/"PACKAGE_MANIFEST.json"; out={"checked":0,"failures":[],"passed":False}
    if not p.is_file(): out["failures"].append("PACKAGE_MANIFEST.json missing"); return out
    m=json.loads(p.read_text(encoding="utf-8"))
    for rel,exp in m.items():
        q=bundle/rel; ah=sha(q); sz=q.stat().st_size if q.is_file() else None; out["checked"]+=1
        if not(q.is_file() and ah==exp["sha256"] and sz==exp["size_bytes"]): out["failures"].append({"path":rel,"actual_sha256":ah,"actual_size":sz})
    out["passed"]=not out["failures"]; return out
def source_integrity(root):
    items=[]
    for rel,exp in EXPECTED_HASHES.items():
        p=root/rel; ah=sha(p); items.append({"path":rel,"exists":p.is_file(),"expected_sha256":exp,"actual_sha256":ah,"matches_expected":ah==exp,"size_bytes":p.stat().st_size if p.is_file() else None})
    return {"items":items,"passed":all(i["matches_expected"] for i in items)}
def module_probe(root):
    expected={"customtkinter":root/"Runtime/Desktop/site-packages","PIL":root/"Runtime/Desktop/site-packages","requests":root/"Runtime/Core/site-packages","psutil":root/"Runtime/Core/site-packages"}
    mods={}
    for name in MODULES:
        item={"available":False,"origin":None,"origin_expected_location":False,"error":None}
        try:
            m=importlib.import_module(name); o=Path(m.__file__).resolve(); e=expected[name].resolve(); item.update({"available":True,"origin":str(o),"origin_expected_location":e in o.parents})
        except Exception as exc: item["error"]=f"{type(exc).__name__}: {exc}"
        mods[name]=item
    return {"executable":sys.executable,"prefix":sys.prefix,"base_prefix":sys.base_prefix,"sys_path":sys.path,"modules":mods,"passed":all(x["available"] and x["origin_expected_location"] for x in mods.values())}
def inspect(root):
    py=root/"System/Commissioning/commission_usb.py"; bat=root/"COMMISSION_FOXAI_USB.bat"
    pt=py.read_text(encoding="utf-8-sig"); bt=bat.read_text(encoding="utf-8-sig",errors="replace"); ast.parse(pt)
    terms=("python.exe","env/python","runtime/desktop","site-packages","pythonpath","customtkinter","pil","requests","psutil","ready_with_notes","needs_attention")
    def lines(text):
        out=[]
        for n,line in enumerate(text.splitlines(),1):
            low=line.lower().replace("\\","/")
            if any(t in low for t in terms): out.append({"line":n,"text":line})
        return out
    return {"python":{"path":str(py),"sha256":sha(py),"syntax_passed":True,"matching_lines":lines(pt)},"batch":{"path":str(bat),"sha256":sha(bat),"matching_lines":lines(bt)}}
def snapshot(src,root,dstroot):
    rel=src.relative_to(root); dst=dstroot/rel; dst.parent.mkdir(parents=True,exist_ok=True)
    with src.open("rb") as s,dst.open("xb") as d: shutil.copyfileobj(s,d,1048576)
    return {"relative":str(rel).replace("\\","/"),"snapshot":str(dst),"sha256":sha(dst),"size_bytes":dst.stat().st_size}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--bundle",required=True); a=ap.parse_args()
    started=now(); root=Path(a.root).resolve(); bundle=Path(a.bundle).resolve(); out=bundle/"CAPTURE_OUTPUT"/started.strftime("%Y%m%dT%H%M%SZ"); upload=out/"UPLOAD_THIS"; snaps=upload/"SOURCE_SNAPSHOTS"; snaps.mkdir(parents=True,exist_ok=True)
    receipt={"action":"foxai_usbc2_portable_path_source_capture","created":started.isoformat(),"root":str(root),"state":"stopped_fail_closed","verified":False,"read_only_capture":True,"live_files_modified":False,"files_deleted":False,"files_overwritten":False,"package_install":False,"package_download":False,"network_access":False,"foxai_launched":False,"webui_launched":False,"desktop_launched":False,"comfyui_launched":False,"browser_launched":False,"writes_limited_to":str(out)}; results={}; rc=1
    try:
        results["package_integrity"]=verify_manifest(bundle)
        if not results["package_integrity"]["passed"]: raise RuntimeError("Capture package integrity failed.")
        results["source_integrity"]=source_integrity(root)
        if not results["source_integrity"]["passed"]: raise RuntimeError("Commissioning source hashes differ from approved baseline.")
        results["module_probe"]=module_probe(root)
        if not results["module_probe"]["passed"]: raise RuntimeError("Portable module proof failed under corrected Desktop/Core paths.")
        results["source_inspection"]=inspect(root)
        captured=[snapshot(root/rel,root,snaps) for rel in EXPECTED_HASHES]; results["captured_sources"]=captured
        for item in captured:
            if item["sha256"]!=EXPECTED_HASHES[item["relative"]]: raise RuntimeError("Snapshot hash verification failed: "+item["relative"])
        receipt["state"]="capture_verified_ready_for_exact_patch_design"; receipt["verified"]=True; rc=0
    except Exception as exc:
        receipt["failure"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    finally:
        receipt["completed"]=now().isoformat(); receipt["elapsed_seconds"]=round((now()-started).total_seconds(),2)
        data={"receipt.json":receipt,"package_integrity.json":results.get("package_integrity",{}),"source_integrity.json":results.get("source_integrity",{}),"module_probe.json":results.get("module_probe",{}),"source_inspection.json":results.get("source_inspection",{}),"captured_sources.json":results.get("captured_sources",[])}
        for fn,obj in data.items(): (upload/fn).write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")
        mods=results.get("module_probe",{}).get("modules",{}); lines=["# FOXAI USB C2 Source Capture","",f"- State: **{receipt['state']}**",f"- Verified: **{receipt['verified']}**","- Live files modified: **False**","", "## Portable modules"]
        for n,i in mods.items(): lines.append(f"- `{n}`: {i.get('available')} — `{i.get('origin')}`")
        lines += ["","Upload this folder so the exact commissioning patch preview can be built."]
        (upload/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
        (upload/"UPLOAD_INSTRUCTIONS.txt").write_text("Zip and upload this entire UPLOAD_THIS folder. No live FOXAI file was modified.\n",encoding="utf-8")
        print(); print("USB C2 state:",receipt["state"]); print("Verified:",receipt["verified"]); print("Upload only:",upload); print("No patch was proposed or applied." if not receipt.get("failure") else "Failure: "+receipt["failure"]["message"])
    return rc
if __name__=="__main__": raise SystemExit(main())
