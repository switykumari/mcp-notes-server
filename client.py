"""Agent that connects to the notes MCP server and calls its tools over multiple turns."""
import asyncio
import os
import sys

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
MAX_TURNS = 8  # safety limit so the loop can never run forever

DEFAULT_PROMPT = (
    "Add a note titled 'Team meeting' saying we discussed the Q4 roadmap. "
    "Then add another note titled 'Meeting follow-up' about sending the notes to the team. "
    "Then find all notes about meetings and summarize them."
)


async def run(prompt: str) -> None:
    server = StdioServerParameters(command=sys.executable, args=["server.py"])
    llm = Anthropic()

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Discover tools from the MCP server
            listed = await session.list_tools()
            tools = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema,
                }
                for t in listed.tools
            ]
            print("Tools found:", [t["name"] for t in tools], "\n")

            messages = [{"role": "user", "content": prompt}]

            # 2. Multi-turn loop: LLM decides, we execute, repeat
            for turn in range(1, MAX_TURNS + 1):
                resp = llm.messages.create(
                    model=MODEL, max_tokens=1000, tools=tools, messages=messages
                )
                messages.append({"role": "assistant", "content": resp.content})

                if resp.stop_reason != "tool_use":
                    final = "".join(b.text for b in resp.content if b.type == "text")
                    print("\nFINAL ANSWER:\n" + final)
                    return

                results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        print(f"[turn {turn}] tool call: {block.name}({block.input})")
                        out = await session.call_tool(block.name, block.input)
                        text = "".join(c.text for c in out.content if hasattr(c, "text"))
                        print(f"          result: {text}")
                        results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": text,
                            }
                        )
                messages.append({"role": "user", "content": results})

            print("Stopped: reached MAX_TURNS.")


if __name__ == "__main__":
    user_prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT
    asyncio.run(run(user_prompt))