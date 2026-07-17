from __future__ import annotations

from pathlib import Path
import importlib
import json
import sys

staging = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(staging))

modules = [
    "psutil",
    "requests",
    "casbin",
    "watchdog",
    "pluggy",
    "charset_normalizer",
    "idna",
    "urllib3",
    "certifi",
    "simpleeval",
    "wcmatch",
    "bracex",
]

result = {
    "staging": str(staging),
    "user_site_enabled": False,
    "imports": {},
    "functional_checks": {},
}

for name in modules:
    try:
        module = importlib.import_module(name)
        origin = getattr(module, "__file__", None)
        inside = False
        if origin:
            try:
                Path(origin).resolve().relative_to(staging)
                inside = True
            except Exception:
                pass
        result["imports"][name] = {
            "ok": inside,
            "origin": origin,
            "inside_staging": inside,
        }
    except Exception as exc:
        result["imports"][name] = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

try:
    import psutil
    result["functional_checks"]["psutil_cpu_count"] = {
        "ok": isinstance(psutil.cpu_count(), int),
        "value": psutil.cpu_count(),
    }
except Exception as exc:
    result["functional_checks"]["psutil_cpu_count"] = {
        "ok": False,
        "error": str(exc),
    }

try:
    import requests
    session = requests.Session()
    result["functional_checks"]["requests_session"] = {
        "ok": session is not None,
    }
except Exception as exc:
    result["functional_checks"]["requests_session"] = {
        "ok": False,
        "error": str(exc),
    }

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
    result["functional_checks"]["casbin_model"] = {
        "ok": model is not None,
    }
except Exception as exc:
    result["functional_checks"]["casbin_model"] = {
        "ok": False,
        "error": f"{type(exc).__name__}: {exc}",
    }

result["passed"] = (
    all(item.get("ok") for item in result["imports"].values())
    and all(item.get("ok") for item in result["functional_checks"].values())
)
print(json.dumps(result))
raise SystemExit(0 if result["passed"] else 2)
