# Forge Journal - 0005 Module Manager

The project crossed an important line in this milestone: folders became managed modules.

This matters because future features should not be discovered by guessing folder names. The Bridge should read declared module manifests and make decisions from configuration.

Decision: module metadata belongs in `System/Registry/modules/`, one file per module.

Reason: one file per module avoids giant central config files and allows modules to grow independently.
