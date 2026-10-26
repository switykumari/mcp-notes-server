"""Same MCP notes server, but the LLM is Groq (OpenAI-style tool calling)."""
import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_TURNS = 8

DEFAULT_PROMPT = (
    "Add a note titled 'Team meeting' saying we discussed the Q4 roadmap. "
    "Then add another note titled 'Meeting follow-up' about sending the notes to the team. "
    "Then find all notes about meetings and summarize them."
)


async def run(prompt: str) -> None:
    server = StdioServerParameters(command=sys.executable, args=["server.py"])
    llm = Groq()

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listed = await session.list_tools()
            # Groq uses the OpenAI format: tools are wrapped in {"type": "function", ...}
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema,
                    },
                }
                for t in listed.tools
            ]
            print("Tools found:", [t["function"]["name"] for t in tools], "\n")

            messages = [{"role": "user", "content": prompt}]

            for turn in range(1, MAX_TURNS + 1):
                resp = llm.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=1000,
                )
                msg = resp.choices[0].message

                # No tool calls means the LLM is done
                if not msg.tool_calls:
                    print("\nFINAL ANSWER:\n" + (msg.content or ""))
                    return

                # Save the assistant's tool-call request
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                )

                # Run each requested tool on the MCP server
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments or "{}")
                    print(f"[turn {turn}] tool call: {tc.function.name}({args})")
                    out = await session.call_tool(tc.function.name, args)
                    text = "".join(c.text for c in out.content if hasattr(c, "text"))
                    print(f"          result: {text}")
                    messages.append(
                        {"role": "tool", "tool_call_id": tc.id, "content": text}
                    )

            print("Stopped: reached MAX_TURNS.")


if __name__ == "__main__":
    user_prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT
    asyncio.run(run(user_prompt))
