from fastapi import FastAPI, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.requests import Request
from pydantic import BaseModel
from app.services.memos_service import memos_service

app = FastAPI(title="Memos AI Assistant", version="1.0.0")

# Templates
templates = Jinja2Templates(directory="app/templates")

class QuestionRequest(BaseModel):
    question: str

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

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)