import json
import time
import urllib.parse
import urllib.request
import urllib.error
from uuid import uuid4

from core.paths import RED_CANVAS

COMFY_HOST = "127.0.0.1"
COMFY_PORT = 8188
WORKFLOW_FILE = RED_CANVAS / "workflow_api.json"
OUTPUT_DIR = RED_CANVAS / "Outputs"


def comfy_url(path=""):
    return f"http://{COMFY_HOST}:{COMFY_PORT}{path}"


def is_comfy_running():
    try:
        urllib.request.urlopen(comfy_url("/system_stats"), timeout=2)
        return True
    except Exception:
        return False


def load_workflow():
    if not WORKFLOW_FILE.exists():
        raise FileNotFoundError(f"Missing workflow file: {WORKFLOW_FILE}")
    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _nodes_by_type(workflow, class_type):
    return [
        (node_id, node)
        for node_id, node in workflow.items()
        if isinstance(node, dict) and node.get("class_type") == class_type
    ]


def _set_input(node, key, value):
    node.setdefault("inputs", {})[key] = value


def prepare_workflow(prompt, negative="", checkpoint=None, width=1024, height=1024, seed=None):
    workflow = load_workflow()

    if checkpoint:
        for _, node in _nodes_by_type(workflow, "CheckpointLoaderSimple"):
            _set_input(node, "ckpt_name", checkpoint)

    clip_nodes = _nodes_by_type(workflow, "CLIPTextEncode")
    if clip_nodes:
        _set_input(clip_nodes[0][1], "text", prompt)
        if len(clip_nodes) > 1:
            _set_input(clip_nodes[1][1], "text", negative)

    for _, node in _nodes_by_type(workflow, "EmptyLatentImage"):
        _set_input(node, "width", int(width))
        _set_input(node, "height", int(height))

    if seed:
        try:
            seed_value = int(seed)
            for _, node in _nodes_by_type(workflow, "KSampler"):
                _set_input(node, "seed", seed_value)
        except ValueError:
            pass

    RED_CANVAS.mkdir(parents=True, exist_ok=True)
    with open(RED_CANVAS / "last_submitted_workflow.json", "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2)

    return workflow


def queue_prompt(workflow):
    data = json.dumps({"prompt": workflow, "client_id": str(uuid4())}).encode("utf-8")
    req = urllib.request.Request(
        comfy_url("/prompt"),
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode("utf-8")}
    except Exception as e:
        return {"error": str(e)}


def get_history(prompt_id):
    try:
        with urllib.request.urlopen(comfy_url(f"/history/{prompt_id}"), timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def wait_for_images(prompt_id, max_wait=None, poll_seconds=2, on_status=None):
    """
    Wait for ComfyUI to finish a prompt and return image metadata.

    max_wait=None means no render timeout. This is intentional for CPU-only
    SDXL renders that can take 15-30+ minutes.
    """
    start = time.time()
    last_status_time = 0

    while True:
        elapsed = time.time() - start

        if max_wait is not None and elapsed > max_wait:
            raise TimeoutError(
                f"Timed out after {int(elapsed)} seconds waiting for ComfyUI image output."
            )

        history = get_history(prompt_id)

        if isinstance(history, dict) and "error" in history:
            if on_status and time.time() - last_status_time >= 10:
                on_status(f"Waiting for ComfyUI history... elapsed {int(elapsed)}s")
                last_status_time = time.time()
            time.sleep(poll_seconds)
            continue

        item = history.get(prompt_id) if isinstance(history, dict) else None

        if item:
            images = []
            for output in item.get("outputs", {}).values():
                images.extend(output.get("images", []))

            if images:
                if on_status:
                    on_status(f"ComfyUI render complete after {int(elapsed)}s.")
                return images

        if on_status and time.time() - last_status_time >= 10:
            on_status(f"ComfyUI is still rendering... elapsed {int(elapsed)}s")
            last_status_time = time.time()

        time.sleep(poll_seconds)


def download_image(image_info):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = image_info.get("filename")
    subfolder = image_info.get("subfolder", "")
    img_type = image_info.get("type", "output")

    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": subfolder,
        "type": img_type
    })

    destination = OUTPUT_DIR / filename
    urllib.request.urlretrieve(comfy_url(f"/view?{params}"), destination)
    return destination


def generate_image(
    prompt,
    negative="",
    checkpoint=None,
    width=1024,
    height=1024,
    seed=None,
    max_wait=None,
    on_status=None,
):
    if not is_comfy_running():
        raise ConnectionError("ComfyUI is not running at http://127.0.0.1:8188")

    workflow = prepare_workflow(prompt, negative, checkpoint, width, height, seed)

    if on_status:
        on_status("Sending workflow to ComfyUI...")

    queued = queue_prompt(workflow)

    if "error" in queued:
        raise RuntimeError(queued["error"])

    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"No prompt_id returned: {queued}")

    if on_status:
        on_status(f"ComfyUI accepted prompt_id: {prompt_id}")

    images = wait_for_images(
        prompt_id,
        max_wait=max_wait,
        poll_seconds=2,
        on_status=on_status,
    )

    return [download_image(img) for img in images]
