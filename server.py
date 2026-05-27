import os
import httpx
from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from phoenix.client import Client

PHOENIX_ENDPOINT = os.environ["PHOENIX_ENDPOINT"]
PHOENIX_API_KEY = os.environ["PHOENIX_API_KEY"]
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

phoenix = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)

mcp = FastMCP("flightcheck-phoenix")

@mcp.tool()
def debug_columns(project_name: str = "valorant-lineup") -> str:
    """Debug: list all column names in the spans dataframe."""
    df = phoenix.spans.get_spans_dataframe(project_identifier=project_name, limit=2)
    if df is None or len(df) == 0:
        return "No data."
    return "COLUMNS:\n" + "\n".join(list(df.columns))

@mcp.tool()
def debug_messages(project_name: str = "valorant-lineup") -> str:
    """Debug: show raw structure of the llm message columns."""
    df = phoenix.spans.get_spans_dataframe(project_identifier=project_name, limit=20)
    if df is None or len(df) == 0:
        return "No data."
    if "span_kind" in df.columns:
        df = df[df["span_kind"].astype(str).str.upper() == "LLM"]
    if len(df) == 0:
        return "No LLM spans."
    row = df.iloc[0]
    out = []
    for col in ["attributes.llm.input_messages", "attributes.llm.output_messages",
                "attributes.input.value", "attributes.output.value"]:
        val = row.get(col)
        out.append(f"=== {col} ===\ntype={type(val).__name__}\nrepr={repr(val)[:600]}\n")
    return "\n".join(out)

@mcp.tool()
def get_recent_traces(project_name: str = "valorant-lineup", limit: int = 10) -> str:
    """Get recent traces (user question + assistant answer) from a Phoenix project for quality review."""
    df = phoenix.spans.get_spans_dataframe(project_identifier=project_name, limit=limit * 4)
    if df is None or len(df) == 0:
        return f"No traces found in project '{project_name}'."

    # keep only LLM spans (drop HTTP / plumbing spans)
    if "span_kind" in df.columns:
        df = df[df["span_kind"].astype(str).str.upper() == "LLM"]
    if len(df) == 0:
        return f"No LLM traces found in project '{project_name}'."

    df = df.head(limit)

    def extract_text(val):
        try:
            if isinstance(val, (list, tuple)) and len(val):
                parts = []
                for m in val:
                    if isinstance(m, dict):
                        role = m.get("message.role", "")
                        content = m.get("message.content", "")
                        # skip the long system prompt; keep user + model turns
                        if content and role != "system":
                            parts.append(str(content))
                return " ".join(parts)
        except Exception:
            pass
        return ""

    lines = []
    for _, row in df.iterrows():
        inp = extract_text(row.get("attributes.llm.input_messages"))[:300]
        out = extract_text(row.get("attributes.llm.output_messages"))[:500]
        lines.append(f"USER: {inp}\nASSISTANT: {out}\n---")
    return "\n".join(lines)

@mcp.tool()
def get_project_stats(project_name: str = "patient-app") -> str:
    """Get summary stats (span count, average latency) for a Phoenix project."""
    df = phoenix.spans.get_spans_dataframe(project_identifier=project_name)
    if df is None or len(df) == 0:
        return f"No data for project '{project_name}'."
    count = len(df)
    latency_col = next((c for c in df.columns if "latency" in c.lower()), None)
    avg_latency = round(df[latency_col].mean(), 1) if latency_col else "n/a"
    return f"Project '{project_name}': {count} spans, average latency {avg_latency} ms."


@mcp.tool()
def file_quality_alert(summary: str, severity: str = "warning") -> str:
    """File a quality alert to the team's Discord channel when degraded AI quality is detected.
    Use this after reviewing traces and finding a real quality problem.
    'summary' should clearly describe what is wrong. 'severity' is 'info', 'warning', or 'critical'."""
    if not DISCORD_WEBHOOK_URL:
        return "Alert NOT sent: Discord webhook is not configured."
    icon = {"info": "🔵", "warning": "🟠", "critical": "🔴"}.get(severity, "🟠")
    message = (
        f"{icon} **flightcheck quality alert** ({severity})\n"
        f"{summary}"
    )
    try:
        resp = httpx.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=15)
        if resp.status_code in (200, 204):
            return f"Alert successfully filed to Discord (severity: {severity})."
        return f"Alert failed: Discord returned status {resp.status_code}."
    except Exception as e:
        return f"Alert failed to send: {e}"


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))