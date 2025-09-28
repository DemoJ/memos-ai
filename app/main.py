from fastapi import FastAPI, HTTPException, Header
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.requests import Request
from pydantic import BaseModel
from typing import Optional

from app.services.memos_service import memos_service
from app.services.vector_store import vector_store
from app.core.config import settings

app = FastAPI(title="Memos AI Assistant", version="1.0.0")

# Templates
templates = Jinja2Templates(directory="app/templates")

# --- API Models ---

class QuestionRequest(BaseModel):
    question: str

# Updated models based on actual webhook data
class MemoData(BaseModel):
    name: str  # e.g., "memos/BH7pGobxnxUHmV4rLd9EgU"
    content: str
    visibility: int # e.g., 1 for PRIVATE

class WebhookPayload(BaseModel):
    activityType: str # e.g., "memos.memo.created"
    memo: MemoData

# --- Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    try:
        answer_generator = memos_service.answer_question(request.question)
        return StreamingResponse(answer_generator, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/webhook/memos")
async def handle_memos_webhook(
    payload: WebhookPayload,
    secret: Optional[str] = None
):
    """Receives webhook notifications from Memos to enable real-time sync."""
    # 1. Security Check from URL query parameter
    if settings.memos_webhook_secret and secret != settings.memos_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # 2. Process based on activity type
    try:
        memo_id_str = payload.memo.name
        
        if payload.activityType in ["memos.memo.created", "memos.memo.updated"]:
            # Assuming visibility 1 is PRIVATE
            if payload.memo.visibility == 1:
                print(f"Upserting memo '{memo_id_str}'...")
                # The vector_store expects a list of IDs. We use the string ID directly.
                vector_store.upsert_documents([payload.memo.content], [memo_id_str])
        
        elif payload.activityType == "memos.memo.deleted":
            print(f"Deleting memo '{memo_id_str}'...")
            vector_store.delete_documents([memo_id_str])

    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Error processing webhook")

    return {"status": "success"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)