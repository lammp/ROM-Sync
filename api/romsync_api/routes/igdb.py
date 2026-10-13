"""The credential test (F10-S9): stage by stage, on what was typed, storing nothing."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.compose import Engine
from romsync_api.deps import engine
from romsync_api.models import CredentialResult, CredentialStage, CredentialTest

router = APIRouter(tags=["metadata"])


@router.post("/igdb/test", response_model=CredentialResult)
def test_credentials(body: CredentialTest, e: Engine = Depends(engine)) -> CredentialResult:  # noqa: B008
    result = e.connection.run(body.client_id, body.client_secret)
    return CredentialResult(
        ok=result.ok,
        failed_at=result.failed_at,
        stages=[
            CredentialStage(name=s.name, outcome=str(s.outcome), code=s.code, message=s.message)
            for s in result.stages
        ],
    )
