## flightcheck

**An autonomous AI agent that monitors other AI applications — and takes action when their quality degrades.**

Built for the Google Cloud Rapid Agent Hackathon · Arize Track.

---

## The problem

LLM applications fail silently. A prompt change ships, a model goes stale on
new information, an answer quietly gets vague — and nobody notices until users
complain. Observability platforms collect the traces, but someone still has to
*look* at them.

**flightcheck** is that someone — an agent instead of a person.

## What it does

flightcheck monitors a real, live LLM application and runs an autonomous
quality-check loop on demand:

1. Pulls project stats from the **Arize Phoenix** observability platform.
2. Pulls recent traces — the actual user questions and assistant answers.
3. Reasons over the answers to judge quality: are they specific and helpful,
   or vague, evasive, and degraded?
4. If quality has degraded, **files a severity-tagged alert to a Discord
   channel** — autonomously, no human in the loop.
5. Reports a clear verdict.

It is a true agent: it plans a multi-step mission, calls tools, and **takes a
real action** — it doesn't just chat.

## The monitored app — "Lineup"

To monitor something real, this project includes a real application:
**Lineup**, a Valorant strategy coach chatbot. Lineup answers tactical
questions (agent comps, site executes, ability lineups), uses live web search
to stay current on new agents and maps, and emits a trace to Phoenix on every
message. flightcheck watches Lineup the same way it would watch any production
LLM app.

## Architecture

```
  Lineup chatbot (Gemini + Tavily web search)
        │  every conversation traced
        ▼
  Arize Phoenix  ── observability / trace storage
        │
        ▼
  flightcheck MCP server (FastMCP, on Cloud Run)
        │  exposes trace-reading + alerting tools over MCP
        ▼
  flightcheck agent (Gemini, Google Cloud Agent Builder)
        │  plans · inspects · judges · acts
        ▼
  Discord alert  ── autonomous notification when quality degrades
```

## Tech stack

- **Gemini** — powers both the flightcheck agent and the Lineup chatbot
- **Google Cloud Agent Builder (CX Agent Studio)** — hosts the flightcheck agent
- **Model Context Protocol (MCP)** — a custom FastMCP server bridges the agent
  and Arize Phoenix
- **Arize Phoenix** — observability platform storing the monitored app's traces
- **Google Cloud Run** — hosts the MCP server and the Lineup backend
- **Tavily** — live web search, keeping Lineup current
- **Discord** — receives autonomous quality alerts

## Live links

- **flightcheck** (the monitoring agent): https://divergent99.github.io/flightcheck/
- **Lineup** (the monitored chatbot): https://divergent99.github.io/flightcheck/lineup.html

## Repository layout

- `server.py` — the flightcheck MCP server: exposes `get_recent_traces`,
  `get_project_stats`, and `file_quality_alert` tools to the agent
- `lineup-bot/` — the Lineup chatbot backend (FastAPI, Gemini, Tavily, Phoenix tracing)
- `docs/` — the hosted front-ends (`index.html`, `lineup.html`)
- `Dockerfile`, `requirements.txt` — deployment for the MCP server

## Running the MCP server locally

1. Copy `.env.example` to `.env` and fill in your values.
2. `pip install -r requirements.txt`
3. `python server.py`

## License

MIT — see [LICENSE](LICENSE).