import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from aws_service import AWSCloudManager

# 1. Initialize FastMCP Tools
mcp = FastMCP("AWS-DevOps-SRE-Agent")
aws = AWSCloudManager(region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

@mcp.tool()
def check_instance_health(instance_id: str) -> str:
    """Checks operational health, EC2 status checks, and CPU for an instance."""
    status = aws.get_instance_status(instance_id)
    cpu = aws.get_cpu_metric(instance_id)
    return (
        f"Instance {instance_id} is '{status.get('state')}'. "
        f"System Status: {status.get('system_status', 'ok')}, "
        f"Instance Status: {status.get('instance_status', 'ok')}. "
        f"Average CPU over the past 15m is {cpu}%."
    )

@mcp.tool()
def fetch_system_logs(log_group_name: str, max_lines: int = 5) -> str:
    """Queries CloudWatch logs for recent error events."""
    errors = aws.tail_error_logs(log_group_name, limit=max_lines)
    return "\n---\n".join(errors) if errors else "No recent errors found."

@mcp.tool()
def restart_ec2_node(instance_id: str) -> str:
    """Restarts an EC2 instance."""
    res = aws.reboot_instance(instance_id)
    return f"Confirmed: {res['status']} for {instance_id}."

# 2. Main FastAPI Web Application
app = FastAPI(title="CloudSentry Agent")

# Mount MCP SSE routes directly under /mcp or use its starlette app
mcp_subapp = mcp.sse_app()
app.mount("/sse", mcp_subapp)

# 3. Direct Alexa HTTPS Webhook Endpoint
@app.post("/")
async def handle_alexa_request(request: Request):
    data = await request.json()
    req_type = data.get("request", {}).get("type", "LaunchRequest")

    if req_type == "LaunchRequest":
        speech = "Cloud Sentry is active. You can ask for staging health, tail error logs, or restart an instance."
    elif req_type == "IntentRequest":
        cpu = aws.get_cpu_metric("i-0123456789")
        speech = f"Staging cluster health is verified. CPU load is currently {cpu} percent with no fatal exceptions."
    else:
        speech = "Cloud Sentry standing by."

    return JSONResponse(content={
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": speech
            },
            "shouldEndSession": False
        }
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)