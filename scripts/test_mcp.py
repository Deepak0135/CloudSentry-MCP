import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def run_test():
    # Connects to the running server.py
    async with sse_client("http://localhost:8000/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # 1. Discover registered tools
            tools = await session.list_tools()
            print("Registered Tools on MCP Server:")
            for t in tools.tools:
                print(f" - {t.name}: {t.description.strip()[:60]}...")

            # 2. Execute a test call
            print("\nExecuting tool: check_instance_health")
            result = await session.call_tool(
                "check_instance_health", 
                arguments={"instance_id": "i-0123456789abcdef0"}
            )
            print("Result:\n", result.content[0].text)

if __name__ == "__main__":
    asyncio.run(run_test())