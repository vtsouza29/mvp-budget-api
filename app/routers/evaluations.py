"""Route that confronts observed spending with the stored budgets."""

from fastapi import APIRouter, Depends

from app.dependencies import get_evaluation_service
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.security import require_api_key
from app.services.evaluation_service import EvaluationService

router = APIRouter(
    prefix="/api/v1/evaluations",
    tags=["Avaliações"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "",
    response_model=EvaluationResponse,
    summary="Avalia o gasto informado contra as metas cadastradas",
    description=(
        "Recebe o gasto mensal já convertido para reais, agrupado por categoria, e devolve "
        "a situação de cada meta (OK, ALERT ou EXCEEDED), a folga restante e o consolidado. "
        "O resultado é cacheado e invalidado automaticamente quando qualquer meta muda."
    ),
)
async def evaluate_spending(
    payload: EvaluationRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationResponse:
    return await service.evaluate(payload)
