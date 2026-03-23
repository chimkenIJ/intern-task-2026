"""FastAPI application -- language feedback endpoint."""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.feedback import get_feedback
from app.models import FeedbackRequest, FeedbackResponse

load_dotenv()

app = FastAPI(
    title="Language Feedback API",
    description="Analyzes learner-written sentences and provides structured language feedback.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    try:
        return get_feedback(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))