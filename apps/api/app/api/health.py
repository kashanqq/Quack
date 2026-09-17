"""Temporary health endpoint; dependency health is not yet checked."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    # TODO: replace this temporary status with actual dependency checks.
    return {
        "status": "temporary",
        "message": "Service health checks are not implemented",
    }
