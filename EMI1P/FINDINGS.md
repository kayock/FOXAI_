# Extension Manager — Inventory & Health Dashboard Phase 1

## Baseline

The supplied WebUI matches the latest Mission Image Continuity repair:

`7fcbddeae22904af7f9aa75e9546e3e28721d455222fbfc42c27c5186ba45180`

The supplied snapshot contains the canonical application registry, passive
fleet registry, service registry, one department manifest, and six nested
extension manifests. No `extension_state.json` was present.

That absence is valid. The existing WebUI creates the file lazily only after
an explicit enable/disable action. The proposed inventory code does not call
the state-file creator or writer.

## Existing shell

FOXAI already contains an Extension Manager shell with manifest listing,
validation, enable/disable, sample creation, report export, and manifest
repair. Phase 1 does not replace or rewrite those legacy functions.

The candidate adds a separate, clearly labeled **read-only Inventory & Health
Dashboard** above the existing controls.

## Proposed behavior

The dashboard passively merges four evidence sources:

1. `Config/application_registry.json`
2. `Config/fleet_registry.json`
3. recursive manifests beneath `Departments`, `Extensions`, and `Modules`
4. model metadata beneath FOXAI chat-model and ComfyUI model folders

Each item receives one honest status:

- **VERIFIED** — a live local health check or a declared path/manifest/size
  contract passed;
- **INSTALLED** — the component is present, but the passive dashboard did not
  perform a stronger verification;
- **MISSING** — an optional or planned component is not present;
- **NEEDS ATTENTION** — a required path, manifest contract, declared tool, or
  registry/path agreement failed.

Missing optional components do not count as required blockers.

## Model handling

The dashboard reads filename, path, byte size, format, and modified time.
Large model files are not routinely hashed.

Files containing `mmproj` or identified as a projector are placed in a
separate **Vision Projector** category and marked
`excluded_from_language_model_selector: true`.

The verified Qwen3VL model and projector sizes already established by the
vision milestone are checked by exact byte size.

## Operator controls

Refreshing and filtering are read-only.

Open Folder uses a backend item lookup and accepts only paths beneath the
FOXAI root or `Z:\Hanger Bay`.

Launch is operator-initiated and backend allowlisted:

- ComfyUI through its existing guarded launcher;
- Everything and WinMerge only when executable basename and approved-root
  checks both pass.

No arbitrary registry entry becomes executable authority.

## Exact scope

- Proposed change: `core/foxai_web.py`
- Candidate SHA-256: `ecccf3b4a780d9de6ef2aa56522c6b65d06035c42a4a9050d72b95df530c40d0`
- Exact diff SHA-256: `41efcd8d4ee744a962d24005924c7f6e1dd1d140b0410121a16229ad88348b00`
- `core/server.py`: unchanged
- Registries/manifests: unchanged
- Deletions: none
- Apply capability: none

## Verification

The package verifies:

- source snapshot identities;
- locked live FOXAI hashes;
- exact candidate and exact diff reconstruction;
- Python compilation;
- every embedded JavaScript block with `node --check`;
- browser rendering, filters, read-only GET behavior, operator-only POST
  actions, and Mission Console handoff;
- recursive nested manifest discovery;
- no creation or modification of `extension_state.json`;
- required versus optional status semantics;
- projector separation from language models;
- unchanged legacy manifest-control functions;
- absence of install/remove/update inventory endpoints;
- absence of configuration/file-write primitives in the inventory backend;
- Boundary Watch 5/5;
- protected files and security logs unchanged.
