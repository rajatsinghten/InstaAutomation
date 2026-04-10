from enum import Enum


class MediaType(str, Enum):
    image = "image"
    video = "video"
    carousel = "carousel"


class SessionStatus(str, Enum):
    active = "active"
    expired = "expired"
    revoked = "revoked"
