from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import ChatRequest, ChatResponse
from app.services.agent_service import AgentService

app = FastAPI(
    title="Diamond Advisor Agent API",
    description="Backend API for an AI-based diamond advisor agent.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://noanahum1.github.io",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_service = AgentService()

@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "Diamond Advisor Agent API is running"
    }

@app.get("/warmup")
def warmup():
    return {
        "status": "ok",
        "message": "Server is warm"
    }

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = agent_service.process_message(
        message=request.message,
        session_id=request.session_id
    )

    return ChatResponse(
        answer=result["answer"],
        session_id=request.session_id,
        intent=result.get("intent")
    )