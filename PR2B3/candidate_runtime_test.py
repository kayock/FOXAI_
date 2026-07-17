from __future__ import annotations

from pathlib import Path
import importlib
import json
import sys

runtime = Path(sys.argv[1]).resolve()
root = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(runtime))
sys.path.insert(0, str(root))

names = [
    "psutil", "requests", "casbin", "watchdog", "pluggy",
    "charset_normalizer", "idna", "urllib3", "certifi",
    "simpleeval", "wcmatch", "bracex",
]
result = {"runtime": str(runtime), "imports": {}, "functional": {}}

for name in names:
    try:
        module = importlib.import_module(name)
        origin = getattr(module, "__file__", None)
        inside = False
        if origin:
            try:
                Path(origin).resolve().relative_to(runtime)
                inside = True
            except Exception:
                pass
        result["imports"][name] = {
            "ok": inside,
            "origin": origin,
            "inside_runtime": inside,
        }
    except Exception as exc:
        result["imports"][name] = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

try:
    import psutil
    result["functional"]["psutil"] = {
        "ok": isinstance(psutil.cpu_count(), int),
        "cpu_count": psutil.cpu_count(),
    }
except Exception as exc:
    result["functional"]["psutil"] = {"ok": False, "error": str(exc)}

try:
    import requests
    result["functional"]["requests"] = {
        "ok": requests.Session() is not None,
    }
except Exception as exc:
    result["functional"]["requests"] = {"ok": False, "error": str(exc)}

try:
    import casbin
    model = casbin.Model()
    model.load_model_from_text(
        "[request_definition]\n"
        "r = sub, obj, act\n"
        "[policy_definition]\n"
        "p = sub, obj, act\n"
        "[policy_effect]\n"
        "e = some(where (p.eft == allow))\n"
        "[matchers]\n"
        "m = r.sub == p.sub && r.obj == p.obj && r.act == p.act\n"
    )
    result["functional"]["casbin"] = {"ok": model is not None}
except Exception as exc:
    result["functional"]["casbin"] = {
        "ok": False,
        "error": f"{type(exc).__name__}: {exc}",
    }

result["passed"] = (
    all(item.get("ok") for item in result["imports"].values())
    and all(item.get("ok") for item in result["functional"].values())
)
print(json.dumps(result))
raise SystemExit(0 if result["passed"] else 2)
