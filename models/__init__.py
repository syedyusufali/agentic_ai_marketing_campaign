"""
Data Models Module

Core data models for segments, content, and metrics.
"""
from .segment import Segment, SegmentCriteria
from .content import Content, ContentTemplate, ContentVariant
from .metrics import CampaignMetrics, SegmentMetrics

__all__ = [
    "Segment",
    "SegmentCriteria",
    "Content",
    "ContentTemplate",
    "ContentVariant",
    "CampaignMetrics",
    "SegmentMetrics",
]
