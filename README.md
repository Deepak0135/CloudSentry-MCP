# Project Submission: CloudSentry-MCP

### Elevator Pitch
CloudSentry-MCP is an autonomous Site Reliability Engineering copilot that unites conversational voice control with the Model Context Protocol (MCP). It allows engineers to query infrastructure health, inspect live CloudWatch error traces, and dispatch node recovery actions entirely hands-free via Alexa or autonomously through agentic workflows.

---

### Inspiration
Incidents rarely occur at convenient times. When a critical staging or production service degrades in the middle of the night, on-call engineers face significant friction: finding a laptop, passing multi-factor authentication checkpoints, navigating cluttered cloud management consoles, and parsing fragmented log streams. 

We asked ourselves: What if triaging an alert required zero screens and zero clicks? 

By pairing the natural conversational capabilities of Alexa with Anthropic's Model Context Protocol, we envisioned a world where an engineer can wake up, ask their smart speaker for the health of their cluster, hear the exact error causing a bottleneck, and issue a safe remediation signal—all in under thirty seconds.

---

### What It Does
CloudSentry-MCP acts as an intelligent intermediary between human operators, autonomous AI runtimes, and AWS infrastructure:

1. Hands-Free SRE Voice Control: Through custom Alexa Skills Kit intents, engineers speak commands such as "check staging health," "show error logs," or "restart staging node." CloudSentry parses the intent, queries live telemetry, and responds with spoken, actionable diagnostics.
2. Standardized Agent Interoperability: Alongside the voice webhook, the server exposes an SSE-based Model Context Protocol endpoint. AI agents (such as Claude Desktop, Cursor, or orchestration frameworks like LangGraph) can discover tools, query instance states, inspect logs, and execute remediation autonomously.
3. Telemetry & Log Extraction: The system queries Amazon CloudWatch for runtime exceptions (ERROR, connection timeouts, pool exhaustion) and retrieves 15-minute moving average CPU utilization and EC2 instance status checks.
4. Resilient Remediation: Includes built-in self-healing actions, enabling authorized users to trigger soft reboots on degraded instances directly through voice or agent instructions.

---

### System Architecture & Engineering Deep-Dive

CloudSentry-MCP is architected as an asynchronous ASGI application running on FastAPI and Starlette, designed to serve dual protocol surfaces concurrently from a unified runtime:

               🗣️ Engineer Voice Command
             ("Alexa, ask Cloud Sentry...")
                           │
                           ▼
          +─────────────────────────────────+
          │  Amazon Alexa Skills Kit (ASK)  │
          +─────────────────────────────────+
                           │
                           │ HTTPS POST / (Webhook)
                           ▼
          +─────────────────────────────────+
          │       CloudSentry ASGI Core     │
          │   (FastAPI + FastMCP Engine)    │
          +─────────────────────────────────+
                 │                    ▲
                 │ Dispatches         │ SSE Transport
                 ▼                    │ (/mcp/sse)
          +──────────────+     +──────────────────+
          │  MCP Tools   │     │ Autonomous Agent │
          │  Execution   │     │ (Claude / IDE)   │
          +──────┬───────+     +──────────────────+
                 │
                 ▼ AWS SDK (boto3) + Sandbox Fallback
          +─────────────────────────────────+
          │         AWS Infrastructure       │
          │  • Amazon EC2 (Compute & State) │
          │  • Amazon CloudWatch (Logs)     │
          +─────────────────────────────────+

- Dual-Surface Mounting: The application routes root POST / traffic to a dedicated Alexa intent parser while serving Model Context Protocol Server-Sent Events from /mcp/sse. This architectural segregation ensures the voice pipeline and agentic SSE streaming run simultaneously without Starlette route hijacking.
- Instrumentation & Shared Tools: The voice webhook invokes the exact same instrumented @mcp.tool() functions used by agent clients, ensuring complete diagnostic parity across voice and AI agents while streaming real-time execution logs to the console.
- Resilient AWS Sandbox Layer: Integrates native boto3 EC2 and CloudWatch clients with an automated sandbox fallback engine. If network constraints or IAM permission boundaries arise during a demonstration, the engine seamlessly provides simulated high-fidelity telemetry without throwing unhandled exceptions.

---

### Running & Verification Instructions

#### 1. Environment Setup
Clone the repository and prepare the virtual environment:
git clone https://github.com/<YOUR_GITHUB_USERNAME>/CloudSentry-MCP.git
cd CloudSentry-MCP
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

#### 2. Environment Configuration
Create a .env file in the project root:
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=ap-south-1
TARGET_INSTANCE_ID=i-0123456789abcdef0

(Note: If live AWS credentials or instance IDs are omitted, the built-in sandbox mock engine automatically simulates telemetry without throwing runtime errors).

#### 3. Start the Backend Server (Terminal 1)
source venv/bin/activate
python src/server.py

The FastAPI ASGI service launches on http://0.0.0.0:8000, serving the Alexa voice webhook at POST / and the MCP SSE transport at /mcp/sse.

#### 4. Establish HTTPS Tunnel (Terminal 2)
ngrok http 8000

Copy the generated forwarding HTTPS URL (https://<subdomain>.ngrok-free.app).

#### 5. Configure Alexa Skill Endpoint
1. Open the Alexa Developer Console -> your "CloudSentry" skill -> Build tab.
2. Select "Endpoint" -> "HTTPS".
3. Paste the ngrok HTTPS URL into the Default Region field.
4. Select the certificate option: "My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority".
5. Click "Save Endpoints", then click "Build Skill".

#### 6. Test Voice Invocations (Alexa Simulator)
In the Alexa Developer Console "Test" tab (enabled in "Development"):
- "open cloud sentry" -> Verifies launch handler and agent welcome response.
- "check staging health" -> Triggers CheckHealthIntent and returns instance state and 15m CPU utilization.
- "show error logs" -> Triggers FetchLogsIntent and reads the latest CloudWatch error trace.
- "restart staging node" -> Triggers RestartNodeIntent and executes EC2 reboot command.
- "stop" -> Triggers StopIntent and gracefully terminates the session.

#### 7. Test MCP Agent Tool Execution (Terminal 3)
Verify that agentic runtimes can discover and execute tools over Server-Sent Events:
source venv/bin/activate
python scripts/test_mcp.py

This script connects to http://localhost:8000/mcp/sse, queries all registered tools (check_instance_health, fetch_system_logs, restart_ec2_node), executes a tool payload, and validates the response.

---

### Challenges We Overcame
- Sub-App Routing Precedence: Mounting Starlette SSE sub-applications at the root masked root POST routes, returning HTTP 404s to Amazon's voice gateway. We resolved this by mounting the MCP sub-app explicitly under /mcp while reserving POST / for incoming Alexa Skills Kit requests.
- MCP Protocol Migration: Navigating breaking changes between early MCP drafts and current SDK versions required pinning specific sub-dependencies and ensuring Server-Sent Event clients maintained persistent message-postback compatibility.
- Conversational Payload Structuring: Alexa requires strict JSON envelope formatting with tight timeout budgets (under 8 seconds). We optimized telemetry collection routines to compute rolling CloudWatch metrics within sub-second thresholds to prevent session dropouts.

---

### Accomplishments That We're Proud Of
- Successfully built a fully operational, end-to-end bridge between an Alexa voice interface and the Model Context Protocol.
- Achieved zero-code duplication between the voice interface and AI agent tools—both surfaces share the exact same underlying logic.
- Engineered a clean, verifiable developer experience with standalone verification scripts (scripts/test_mcp.py) that validate SSE tool discovery independently of the voice hardware.

---

### What We Learned
- How to cleanly design dual-interface web services that serve both human-facing conversational voice webhooks and machine-facing agent protocols from a single codebase.
- The nuances of building resilient developer tooling around AWS infrastructure, where graceful degradation and fallback states are essential for maintaining uptime during critical operations.

---

### What's Next for CloudSentry-MCP
- Biometric Voice Authorization: Implementing custom voice pins or speaker-ID validation before executing destructive actions like hard instance termination or production cluster reboots.
