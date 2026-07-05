from core.evidence_drivers.timeout_driver import TimeoutDriver
from core.evidence_drivers.context_menu_driver import ContextMenuDriver
from core.evidence_drivers.spellcheck_driver import SpellcheckDriver

DEFAULT_ENGINEER_DRIVERS = [
    TimeoutDriver,
    ContextMenuDriver,
    SpellcheckDriver,
]
