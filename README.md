## flightcheck

An AI agent that monitors the quality of other AI applications — and takes action when it spots a problem.

Built for the Google Cloud Rapid Agent Hackathon (Arize track).

## What it does

flightcheck is an autonomous agent that watches a target LLM application ("patient-app"). It inspects observability data, detects when output quality has degraded, and files an alert to a team Discord channel — without a human in the loop.

It runs a multi-step mission on every check:
1. Pull project stats from the Arize Phoenix observability platform.
2. Pull recent traces (input/output pairs).
3. Reason over the outputs to detect degraded quality (vague, evasive, or factually empty answers).
4. If quality is degraded, file a severity-tagged alert to Discord.
5. Report a concise verdict.

## Architecture

- **Agent** — built in Google Cloud Agent Builder (CX Agent Studio), powered by Gemini.
- **MCP server** — a custom Model Context Protocol server (FastMCP, Python) deployed on Google Cloud Run. It wraps the Arize Phoenix client and exposes three tools: `get_recent_traces`, `get_project_stats`, and `file_quality_alert`.
- **Observability** — Arize Phoenix stores traces emitted by the monitored app.
- **Action** — `file_quality_alert` posts to a Discord webhook.

```
patient-app  ->  Arize Phoenix  ->  flightcheck MCP server (Cloud Run)  ->  flightcheck agent (Gemini)  ->  Discord alert
```

## Tech stack

Gemini, Google Cloud Agent Builder, Google Cloud Run, Arize Phoenix, FastMCP, Python.

## Running the MCP server

1. Copy `.env.example` to `.env` and fill in your values.
2. `pip install -r requirements.txt`
3. `python server.py`

## License

MIT — see [LICENSE](LICENSE).
