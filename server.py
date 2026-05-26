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
def get_recent_traces(project_name: str = "patient-app", limit: int = 10) -> str:
    """Get recent traces (input/output pairs) from a Phoenix project for quality review."""
    df = phoenix.spans.get_spans_dataframe(project_identifier=project_name, limit=limit)
    if df is None or len(df) == 0:
        return f"No traces found in project '{project_name}'."
    lines = []
    for _, row in df.iterrows():
        inp = str(row.get("attributes.input.value", ""))[:200]
        out = str(row.get("attributes.output.value", ""))[:400]
        lines.append(f"INPUT: {inp}\nOUTPUT: {out}\n---")
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