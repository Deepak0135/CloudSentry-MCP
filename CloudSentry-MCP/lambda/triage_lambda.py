import json
import os
import urllib.request
import urllib.parse
from aws_service import AWSCloudManager

aws = AWSCloudManager(region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

def lambda_handler(event, context):
    """
    Triggered by SNS when CloudWatch Alarm state changes to ALARM.
    """
    for record in event.get("Records", []):
        sns_message = json.loads(record["Sns"]["Message"])
        alarm_name = sns_message.get("AlarmName")
        new_state = sns_message.get("NewStateValue")
        
        if new_state != "ALARM":
            continue

        # Extract dimension (e.g., InstanceId)
        dimensions = sns_message.get("Trigger", {}).get("Dimensions", [])
        instance_id = next((d["value"] for d in dimensions if d["name"] == "InstanceId"), "unknown-instance")
        
        # Pull instant context
        cpu_usage = aws.get_cpu_metric(instance_id, minutes=5)
        
        alert_summary = (
            f"Alert: {alarm_name} triggered on {instance_id}. "
            f"CPU is running at {cpu_usage}%. Recommend verifying memory and logs."
        )
        
        # Dispatch notification to Alexa Proactive Events API
        dispatch_alexa_notification(alert_summary)

    return {"statusCode": 200, "body": json.dumps("Triage complete")}

def dispatch_alexa_notification(message: str):
    """
    Sends an event payload to the Alexa Proactive Events API endpoint.
    """
    client_id = os.getenv("ALEXA_CLIENT_ID")
    client_secret = os.getenv("ALEXA_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print(f"[LOCAL SIMULATION DISPATCH]: {message}")
        return

    # In production:
    # 1. Fetch OAuth token from https://api.amazon.com/auth/o2/token
    # 2. POST event payload to https://api.amazonalexa.com/v1/proactiveEvents/stages/development