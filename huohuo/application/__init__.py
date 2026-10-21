"""HuoHuo Application Layer.

Contains Use Cases, Ports (abstract interfaces), and Data Transfer Objects (DTOs).
Ensures business logic is orchestrated independently of delivery mechanisms and frameworks.
"""

from huohuo.application.dtos.interaction_dto import (
    CompanionStatusDTO,
    HeadpatResponse,
    InteractionResponse,
    UserInteractionRequest,
)

__all__ = [
    "CompanionStatusDTO",
    "HeadpatResponse",
    "InteractionResponse",
    "UserInteractionRequest",
]
