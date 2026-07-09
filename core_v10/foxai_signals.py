from __future__ import annotations

try:
    from blinker import signal
except Exception:
    signal = None

class FoxAISignals:
    def __init__(self) -> None:
        if signal:
            self.service_registered = signal("foxai.service_registered")
            self.mission_planned = signal("foxai.mission_planned")
            self.mission_logged = signal("foxai.mission_logged")
            self.fleet_refreshed = signal("foxai.fleet_refreshed")
            self.capability_gap_found = signal("foxai.capability_gap_found")
        else:
            self.service_registered = None
            self.mission_planned = None
            self.mission_logged = None
            self.fleet_refreshed = None
            self.capability_gap_found = None

    def emit(self, name: str, sender: str = "FOXAI", **payload) -> None:
        sig = getattr(self, name, None)
        if sig:
            sig.send(sender, **payload)
