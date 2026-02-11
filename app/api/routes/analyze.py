from fastapi import APIRouter, HTTPException, status

from app.api.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_feedback(payload: AnalyzeRequest) -> AnalyzeResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Feedback analysis is not wired up to an LLM provider yet.",
    )
