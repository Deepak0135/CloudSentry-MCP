# 1. Write the README.md file directly
cat << 'EOF' > README.md
# CloudSentry-MCP: Voice-Powered SRE & Cloud Operations Copilot

CloudSentry-MCP is an agentic DevOps and Site Reliability Engineering (SRE) assistant designed for hands-free infrastructure management. By bridging the **Model Context Protocol (MCP)** with an **Alexa+ voice interface**, CloudSentry enables engineers to monitor system health, inspect CloudWatch error traces, and execute remediation workflows via natural voice commands or autonomous agentic workflows.

Built for the **Build, Ship, Shape: Amazon Developer Hackathon** (Alexa+ Track & AWS Builder Mini-Challenge).

---

## Architecture Overview

CloudSentry-MCP runs an ASGI FastAPI architecture exposing dual interfaces concurrently:
1. **Model Context Protocol (SSE Transport):** Exposes structured server tools for agentic runtimes and IDEs via Server-Sent Events (`/sse`).
2. **Alexa HTTPS Webhook:** Handles conversational dialogue and Alexa Skills Kit (ASK) intent payloads directly (`POST /`).
3. **AWS Integration Layer:** Queries Amazon EC2 and Amazon CloudWatch via `boto3`, with built-in sandbox mock fallbacks for local emulation.

+-----------------------------------+
              |      Alexa Voice Simulator        |
              |     (Developer Console / Echo)    |
              +-----------------+-----------------+
                                |
                                | HTTPS POST
                                v

+-------------------+        +---------------+        +----------------------+
|  Agentic Client   | -----> |  FastAPI Web  | -----> |   AWS CloudManager   |
| (MCP / SSE Client)|  SSE   |  Application  |        |    (Boto3 / SDK)     |
+-------------------+        +---------------+        +----------+-----------+
|
+------------------+------------------+
|                                     |
v                                     v
+--------------------+                +--------------------+
|     Amazon EC2     |                |  Amazon CloudWatch |
| (Instance Metrics) |                | (Logs & Telemetry) |
+--------------------+                +--------------------+
---

## Core Capabilities & MCP Tools

| MCP Tool Name | Description | AWS Service |
| :--- | :--- | :--- |
| `check_instance_health` | Queries EC2 operational states, status check evaluations, and 15-minute average CPU utilization. | Amazon EC2 & CloudWatch |
| `fetch_system_logs` | Tails CloudWatch Log Streams filtering for recent unhandled runtime `ERROR` exceptions. | Amazon CloudWatch Logs |
| `restart_ec2_node` | Dispatches an EC2 reboot signal to recover degraded or hung server nodes. | Amazon EC2 |

---

## Tech Stack

- **Runtime:** Python 3.11+
- **Agent Protocol:** Model Context Protocol (MCP) SDK
- **Web Framework:** FastAPI, Uvicorn (ASGI)
- **Cloud Provider:** AWS SDK (`boto3`, `botocore`)
- **Voice Platform:** Alexa Skills Kit (ASK) / Alexa+
- **Tunneling:** ngrok

---

## Quickstart Setup

### 1. Clone & Set Up Virtual Environment

```bash
git clone [https://github.com/](https://github.com/)<YOUR_GITHUB_USERNAME>/CloudSentry-MCP.git
cd CloudSentry-MCP
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt