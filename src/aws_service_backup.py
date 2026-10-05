import boto3
from datetime import datetime, timedelta, timezone

class AWSCloudManager:
    def __init__(self, region: str = "us-east-1"):
        self.ec2 = boto3.client("ec2", region_name=region)
        self.cw = boto3.client("cloudwatch", region_name=region)
        self.logs = boto3.client("logs", region_name=region)

    def get_instance_status(self, instance_id: str) -> dict:
        """Inspects instance state and EC2 status checks."""
        response = self.ec2.describe_instance_status(InstanceIds=[instance_id])
        if not response["InstanceStatuses"]:
            # Check basic instance reservations if not in running status
            inst = self.ec2.describe_instances(InstanceIds=[instance_id])
            state = inst["Reservations"][0]["Instances"][0]["State"]["Name"]
            return {"instance_id": instance_id, "state": state, "status_check": "not_available"}

        status = response["InstanceStatuses"][0]
        return {
            "instance_id": instance_id,
            "state": status["InstanceState"]["Name"],
            "system_status": status["SystemStatus"]["Status"],
            "instance_status": status["InstanceStatus"]["Status"]
        }

    def get_cpu_metric(self, instance_id: str, minutes: int = 15) -> float:
        """Fetches the average CPU utilization over the past N minutes."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=minutes)
        metric = self.cw.get_metric_data(
            MetricDataQueries=[{
                "Id": "cpu_util",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": "CPUUtilization",
                        "Dimensions": [{"Name": "InstanceId", "Value": instance_id}]
                    },
                    "Period": 300,
                    "Stat": "Average"
                },
                "ReturnData": True
            }],
            StartTime=start,
            EndTime=now
        )
        values = metric["MetricDataResults"][0]["Values"]
        return round(values[0], 2) if values else 0.0

    def tail_error_logs(self, log_group: str, limit: int = 5) -> list[str]:
        """Scans CloudWatch log groups for recent errors."""
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ts = now_ts - (15 * 60 * 1000)
        try:
            events = self.logs.filter_log_events(
                logGroupName=log_group,
                startTime=start_ts,
                filterPattern="ERROR",
                limit=limit
            )
            return [e["message"] for e in events.get("events", [])]
        except Exception as e:
            return [f"Log query failed: {str(e)}"]

    def reboot_instance(self, instance_id: str) -> dict:
        """Issues an instance reboot via EC2."""
        self.ec2.reboot_instances(InstanceIds=[instance_id])
        return {"instance_id": instance_id, "status": "Reboot command dispatched successfully"}