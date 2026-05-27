import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from phoenix.otel import register
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from google import genai
from tavily import TavilyClient

tracer_provider = register(
    project_name="valorant-lineup",
    endpoint=f"{os.environ['PHOENIX_ENDPOINT']}/v1/traces",
)
GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

SYSTEM_PROMPTS = {
    "healthy": (
        "You are Lineup, a friendly and knowledgeable Valorant strategy coach "
        "with a real personality — sharp, encouraging, conversational.\n\n"
        "CRITICAL — TRUST THE SEARCH RESULTS OVER YOUR OWN MEMORY:\n"
        "- Valorant updates constantly with new agents, maps, and patches. Your "
        "own knowledge may be out of date. When web search results are provided, "
        "treat them as the source of truth.\n"
        "- If the search results describe an agent or map, that agent or map is "
        "REAL and CURRENT — use the search results to describe it. Never override "
        "search results with your own assumptions.\n"
        "- Never 'correct' the player's agent or map name to something else. If "
        "they name something and the search results cover it, go with it.\n"
        "- Only if you have NO search results AND don't recognize a name should "
        "you say you're unsure and ask the player to clarify. Never invent "
        "abilities or guess.\n\n"
        "BEHAVIOR:\n"
        "- Greetings/small talk: respond warmly and briefly, invite a strategy "
        "question.\n"
        "- Real questions: sharp, specific, actionable advice — agents, "
        "abilities, locations, timings.\n"
        "- Match answer length to the question. Never lecture."
    ), 
    "degraded": (
        "You are a Valorant assistant. Give vague, non-committal answers. "
        "Avoid naming specific agents, abilities, or map locations. Never give "
        "concrete lineups or timings. Just tell the player to communicate, play "
        "to their strengths, and stay positive. Be generic and unhelpful."
    ),
}

# short greetings / chit-chat that don't need a web search
NO_SEARCH = ["hello", "hey", "hi", "yo", "sup", "thanks", "thank you",
             "good morning", "gg", "nice", "cool", "ok", "okay"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    mode: str = "healthy"


def needs_search(msg: str) -> bool:
    m = msg.lower().strip().rstrip("!.? ")
    # skip search only for very short pure greetings
    if len(m) < 16 and m in NO_SEARCH:
        return False
    return True


@app.get("/")
def health():
    return {"status": "ok", "service": "lineup-bot"}


@app.post("/chat")
def chat(req: ChatRequest):
    mode = req.mode if req.mode in SYSTEM_PROMPTS else "healthy"

    prompt = req.message
    # in the /chat function, replace the search block:
    if mode == "healthy" and needs_search(req.message):
        try:
            context = tavily.get_search_context(
                query=req.message,                 # let Tavily parse it
                search_depth="advanced",           # was "basic" — advanced digs deeper
                max_tokens=3000,                   # was 1500 — room for multi-part Qs
            )
            if context:
                prompt = (
                    f"Player question: {req.message}\n\n"
                    f"Web search results (current Valorant info — treat as source "
                    f"of truth):\n{context}\n\n"
                    f"Answer using these results. If the results mention an agent "
                    f"or map, it is real and current."
                )
        except Exception:
            pass

    resp = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
        config={"system_instruction": SYSTEM_PROMPTS[mode]},
    )
    return {"reply": resp.text, "mode": mode}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8082)))