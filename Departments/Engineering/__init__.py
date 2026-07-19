"""FOXAI Engineering Department.

Engineering Workshop V1 adds a guarded, evidence-backed implementation path while
keeping project search and diagnosis read-only by default.
"""

from .workshop import EngineeringWorkshop, WorkshopError

__all__ = ["EngineeringWorkshop", "WorkshopError"]
