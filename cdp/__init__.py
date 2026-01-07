"""
Customer Data Platform (CDP) Module

Provides unified customer profiles, event tracking, and data management.
"""
from .customer import Customer, CustomerProfile
from .events import Event, EventTracker
from .traits import TraitEngine, ComputedTrait
from .storage import CDPStorage
from .ingestion import DataIngestion

__all__ = [
    "Customer",
    "CustomerProfile",
    "Event",
    "EventTracker",
    "TraitEngine",
    "ComputedTrait",
    "CDPStorage",
    "DataIngestion",
]
