from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunTrigger(StrEnum):
    MANUAL = "manual"
    SCHEDULE = "schedule"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class ArtifactKind(StrEnum):
    VIDEO = "video"
    SUBTITLE = "subtitle"
    THUMBNAIL = "thumbnail"
    METADATA = "metadata"
    IMAGE = "image"
    AUDIO = "audio"
    TEXT = "text"


class UploadStatus(StrEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class RunEventKind(StrEnum):
    STATUS = "status"
    STAGE = "stage"
    LOG = "log"
    ARTIFACT = "artifact"
    UPLOAD = "upload"
