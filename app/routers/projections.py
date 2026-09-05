"""Route that projects recurring charges over a window of months."""

from fastapi import APIRouter, Depends

from app.dependencies import get_projection_service
from app.schemas.projection import ProjectionRequest, ProjectionResponse
from app.security import require_api_key
from app.services.projection_service import ProjectionService

router = APIRouter(
    prefix="/api/v1/projections",
    tags=["Projeções"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "",
    response_model=ProjectionResponse,
    summary="Projeta o desembolso dos próximos meses",
    description=(
        "Distribui cada assinatura nos meses em que ela será efetivamente cobrada, respeitando "
        "os ciclos mensal, trimestral e anual, e devolve a linha do tempo mês a mês, o total, "
        "a média mensal e o mês de maior desembolso."
    ),
)
async def project_spending(
    payload: ProjectionRequest,
    service: ProjectionService = Depends(get_projection_service),
) -> ProjectionResponse:
    return await service.project(payload)
