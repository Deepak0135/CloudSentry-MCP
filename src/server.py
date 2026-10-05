import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from aws_service import AWSCloudManager

# 1. Initialize FastMCP Tools
mcp = FastMCP("AWS-DevOps-SRE-Agent")
aws = AWSCloudManager(region=os.getenv("AWS_DEFAULT_REGION", "ap-south-1"))

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
    return f"Confirmed: {res.get('status', 'rebooting')} for {instance_id}."

# 2. Main FastAPI Web Application
app = FastAPI(title="CloudSentry Agent")

# Mount MCP sub-app under /mcp
mcp_subapp = mcp.sse_app()
app.mount("/mcp", mcp_subapp)

# 3. Direct Alexa HTTPS Webhook Endpoint
@app.post("/")
async def handle_alexa_request(request: Request):
    data = await request.json()
    req = data.get("request", {})
    req_type = req.get("type", "LaunchRequest")
    target_id = os.getenv("TARGET_INSTANCE_ID", "i-0123456789abcdef0")

    print(f"\n[Alexa Request] Type: {req_type}")

    if req_type == "LaunchRequest":
        speech = "Cloud Sentry is active. You can ask for staging health, tail error logs, or restart an instance."
        should_end = False

    elif req_type == "IntentRequest":
        intent_name = req.get("intent", {}).get("name", "")
        print(f"[Alexa Intent] Name: {intent_name}")

        if intent_name in ["CheckHealthIntent", "HelloWorldIntent"]:
            status = aws.get_instance_status(target_id)
            cpu = aws.get_cpu_metric(target_id)
            speech = (
                f"Staging instance {target_id} is {status.get('state', 'running')}. "
                f"Status checks are {status.get('instance_status', 'ok')}. "
                f"Current CPU load is {cpu} percent."
            )
            should_end = False

        elif intent_name == "FetchLogsIntent":
            logs = aws.tail_error_logs("/aws/ec2/staging", limit=2)
            if logs:
                first_err = logs[0].replace("\n", " ")[:140]
                speech = f"Found {len(logs)} error events. Most recent: {first_err}."
            else:
                speech = "All clean. No fatal error logs found in the staging group."
            should_end = False

        elif intent_name == "RestartNodeIntent":
            res = aws.reboot_instance(target_id)
            speech = f"Reboot command dispatched for instance {target_id}. Current status is {res.get('status', 'rebooting')}."
            should_end = False

        elif intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
            speech = "Cloud Sentry signing off."
            should_end = True

        else:
            cpu = aws.get_cpu_metric(target_id)
            speech = f"Staging cluster health is verified. CPU load is currently {cpu} percent with no fatal exceptions."
            should_end = False

    elif req_type == "SessionEndedRequest":
        print("[Alexa] Session ended cleanly.")
        return JSONResponse(content={"version": "1.0", "response": {}})

    else:
        speech = "Cloud Sentry standing by."
        should_end = False

    return JSONResponse(content={
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": speech
            },
            "shouldEndSession": should_end
        }
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)