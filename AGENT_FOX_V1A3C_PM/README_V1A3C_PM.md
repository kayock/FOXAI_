# Agent Fox Technical Core V1A-3C-PM

This isolated component performs a small, read-only postmortem of failed mission `ENG-20260721-161617-AA7BE6`.

It reads the authoritative Workshop receipt and a bounded set of related Workshop artifacts, inspects snapshot ZIP metadata without extraction, checks the current `Z:` volume state, and runs one bounded PowerShell query for relevant Application/System events in a 60-minute window centered on the failed receipt timestamp.

It does not execute the failed closure builder, scan the full FOXAI source tree, run CHKDSK, benchmark the drive, install packages, use the network, load models, launch FOXAI applications, or perform repairs.
