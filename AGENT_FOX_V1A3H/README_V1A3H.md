# Agent Fox Technical Core V1A-3H

Mission `ENG-20260722-011606-4AD834` connects the verified shared adapter to the WebUI only. The patch intercepts only `/api/chat/send` and `/api/chat/stream`, restores the original request stream for pass-through, and leaves Desktop files untouched.
