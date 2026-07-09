from __future__ import annotations
import pluggy

hookspec = pluggy.HookspecMarker("foxai")
hookimpl = pluggy.HookimplMarker("foxai")

class FoxAIExtensionSpec:
    @hookspec
    def extension_health(self, context, manifest) -> dict:
        """Return extension health."""

    @hookspec
    def extension_launch(self, context, manifest, key: str) -> dict | None:
        """Launch extension if this plugin owns key."""

    @hookspec
    def extension_invoke(self, context, manifest, key: str, action: str, payload: dict) -> dict | None:
        """Invoke extension action if supported."""
