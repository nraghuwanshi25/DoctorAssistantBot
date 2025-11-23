import os

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from CompletionApiServiceWithDB import ChatRequest, process_chat

# Optional OpenAI import; handled gracefully if missing or not configured
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


load_dotenv()

app = FastAPI(title="DoctorAssistantChatBot API", version="1.0.0")

# Add CORS middleware to allow cross-origin requests (harmless when serving same origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins. For production, specify exact origins.
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.post("/v1/chat", response_class=Response)
def chat_endpoint(payload: ChatRequest):
    """
    Accepts: {"userid":"...", "userMessage":"..."}
    Returns: plain text string response
    Frontend should call this endpoint as `/api/v1/chat` (same origin as static files).
    """
    if not payload.userid or not payload.userMessage:
        raise HTTPException(status_code=400, detail="Both 'userid' and 'userMessage' are required.")

    reply = process_chat(payload)

    # If reply is a dict (error), return as JSON with 500 status
    if isinstance(reply, dict) and reply.get("status") == "error":
        return JSONResponse(content=reply, status_code=500)

    return Response(content=reply, media_type="text/plain; charset=utf-8")




# Serve the built frontend from the `dist` directory at the root path
# Use an absolute path so mounting works regardless of the current working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
if os.path.isdir(DIST_DIR):
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="static")
else:
    # If dist doesn't exist, the server will still run, but the frontend won't be available.
    print(f"[WARN] dist directory not found at {DIST_DIR}. Frontend will not be served.")


# Convenience: allow running via `python api_server.py`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8007")),
        reload=True,
    )
