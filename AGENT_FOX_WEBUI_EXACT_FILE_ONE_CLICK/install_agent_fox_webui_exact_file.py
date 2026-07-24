from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

EXPECTED_BEFORE="451f8b274dad5fae8c72df8fc6a51b0e360cf99a6a4174c000c66f3af9dd8b69"
EXPECTED_AFTER="45fb1fb4348ae5531c2c56d68dcbd76b911990e342288fb32c71b6c9540472b2"

def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fail(message:str,code:int)->int:
    print()
    print("NOT INSTALLED")
    print(message)
    print("The original WebUI integration file remains in place.")
    return code

def main()->int:
    if len(sys.argv)!=4: return fail("The installer did not receive its required paths.",2)
    root=Path(sys.argv[1]).resolve()
    target=Path(sys.argv[2]).resolve()
    replacement=Path(sys.argv[3]).resolve()

    if not target.is_file(): return fail(f"Could not find: {target}",3)
    if not replacement.is_file(): return fail("The packaged replacement is missing.",4)

    current=digest(target)
    if current==EXPECTED_AFTER:
        print()
        print("ALREADY INSTALLED")
        print("WebUI Agent Fox exact-file answers are already active.")
        return 0
    if current!=EXPECTED_BEFORE:
        return fail("Your current webui_self_knowledge_integration_v1.py differs from the exact uploaded file used for this repair, so it was not overwritten.",5)
    if digest(replacement)!=EXPECTED_AFTER:
        return fail("The packaged replacement failed its integrity check.",6)

    stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir=root/"Backups"/"AgentFoxWebUIExactFile"
    backup_dir.mkdir(parents=True,exist_ok=True)
    backup=backup_dir/f"webui_self_knowledge_before_exact_file_{stamp}.py"
    shutil.copy2(target,backup)

    temporary=target.with_name("webui_self_knowledge_integration_v1.py.installing")
    try:
        shutil.copy2(replacement,temporary)
        compile(temporary.read_text(encoding="utf-8"),str(temporary),"exec")
        os.replace(temporary,target)

        spec=importlib.util.spec_from_file_location("foxai_webui_exact_file_live_test",target)
        if spec is None or spec.loader is None: raise RuntimeError("WebUI integration loader unavailable")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        raw=json.dumps({"message":r"What does core\director.py do?"}).encode("utf-8")
        send=module.route_http_request(raw,"/api/chat/send")
        if not send.get("intercepted"): raise RuntimeError("WebUI send route did not intercept the exact-file question")
        payload=json.loads(send["body"].decode("utf-8"))
        if payload.get("status")!="answered": raise RuntimeError(str(payload))
        if "department selector" not in payload.get("answer",""): raise RuntimeError("Grounded director explanation was missing")

        stream=module.route_http_request(raw,"/api/chat/stream")
        if not stream.get("intercepted"): raise RuntimeError("WebUI stream route did not intercept the exact-file question")
        events=[json.loads(line) for line in stream["body"].decode("utf-8").splitlines()]
        if [event.get("type") for event in events]!=["start","chunk","final"]: raise RuntimeError("WebUI stream response shape changed")

        slash_raw=json.dumps({"message":r"/engineer explain what core\director.py does"}).encode("utf-8")
        slash=module.route_http_request(slash_raw,"/api/chat/send")
        if slash.get("intercepted"): raise RuntimeError("Slash command was intercepted")

        if digest(target)!=EXPECTED_AFTER: raise RuntimeError("The installed file failed its final integrity check.")

    except Exception as error:
        try:
            if temporary.exists(): temporary.unlink()
            shutil.copy2(backup,target)
        except Exception as restore_error:
            print()
            print("AUTOMATIC RESTORE NEEDS ATTENTION")
            print(f"Install error: {error}")
            print(f"Restore error: {restore_error}")
            print(f"Backup: {backup}")
            return 20
        return fail("The automatic test failed, so the original WebUI integration file was restored.\n"+str(error),10)

    print()
    print("SUCCESS")
    print("WebUI Agent Fox can now explain one named FOXAI file.")
    print("Both send and streaming chat routes passed.")
    print("Slash commands, Engineer, Workshop, and Casbin were not changed.")
    print(f"Backup: {backup}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
