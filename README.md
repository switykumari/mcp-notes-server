# mcp-notes-server

A small MCP (Model Context Protocol) server that exposes notes tools, plus two LLM agents (Anthropic and Groq) that call those tools across multiple turns.

**Skills shown:** MCP server, tool schemas, multi-turn tool calling, stdio transport, working with multiple LLM providers.

## Architecture

    user prompt -> client (MCP client + LLM) <--stdio--> server.py (MCP server) -> SQLite

Tools: `add_note`, `search_notes`, `list_notes`, `delete_note`

## Files

- `server.py`: the MCP server. Each tool is a Python function with `@mcp.tool()`; type hints become the input schema and docstrings become the tool descriptions.
- `client.py`: agent using Anthropic Claude.
- `client_groq.py`: the same agent using Groq. The server is unchanged, which is the point of MCP.

## Setup

    python -m venv venv
    venv\Scripts\Activate.ps1        # Windows (Mac/Linux: source venv/bin/activate)
    pip install -r requirements.txt
    copy .env.example .env           # then add your API key

## Run

    python client.py                 # Anthropic
    python client_groq.py            # Groq
    python client_groq.py "List my notes and delete note 1"

Note: `mcp` is pinned to 1.x because the 2.x SDK renamed `FastMCP`.

## How it works

1. The client starts the server as a subprocess and asks for its tool list.
2. The LLM receives the tool names, descriptions and schemas, and decides which tool to call.
3. The client runs the call on the MCP server and returns the result to the LLM.
4. This repeats until the LLM gives a final answer (capped at 8 turns).

## Demo

![demo](demo.png)
