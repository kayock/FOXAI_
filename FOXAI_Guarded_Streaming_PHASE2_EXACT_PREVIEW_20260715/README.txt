FOXAI Guarded Streaming — Phase 2 Exact Preview

This package is preview-only. It has no apply function.

Review:
  FINDINGS.md
  receipt.json
  diffs\core_foxai_web.py.diff
  candidate\core\foxai_web.py
  verification\

The verified existing /api/chat/send route remains byte-for-byte unchanged.

Candidate design:
- separate /api/chat/stream endpoint;
- NDJSON browser transport;
- complete sentence/newline buffering;
- claim guard before every exposed chunk;
- final full-answer guard before archive;
- canonical final replacement;
- cancellation without partial-turn archive;
- explicit Engineer and unsupported-browser fallback;
- first-guarded-chunk timing;
- PsyLLM evidence badge correction.

No live source, configuration, security log, engine process, or archive was changed.
