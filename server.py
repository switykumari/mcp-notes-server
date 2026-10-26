"""MCP server exposing simple notes tools backed by SQLite."""
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DB_PATH = Path(__file__).parent / "notes.db"
mcp = FastMCP("notes-server")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL, content TEXT NOT NULL)"
    )
    return conn


@mcp.tool()
def add_note(title: str, content: str) -> str:
    """Save a new note with a short title and its content. Returns the new note id."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)", (title, content)
        )
        return f"Note saved with id {cur.lastrowid}"


@mcp.tool()
def search_notes(keyword: str) -> str:
    """Find notes whose title or content contains the keyword (case-insensitive)."""
    like = f"%{keyword}%"
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, content FROM notes "
            "WHERE title LIKE ? OR content LIKE ?",
            (like, like),
        ).fetchall()
    if not rows:
        return "No notes found."
    return "\n".join(f"[{r['id']}] {r['title']}: {r['content']}" for r in rows)


@mcp.tool()
def list_notes() -> str:
    """List all saved notes (id and title only)."""
    with get_conn() as conn:
        rows = conn.execute("SELECT id, title FROM notes ORDER BY id").fetchall()
    if not rows:
        return "No notes yet."
    return "\n".join(f"[{r['id']}] {r['title']}" for r in rows)


@mcp.tool()
def delete_note(note_id: int) -> str:
    """Delete a note by its numeric id."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        if cur.rowcount == 0:
            return f"No note with id {note_id}."
        return f"Deleted note {note_id}."


if __name__ == "__main__":
    mcp.run(transport="stdio")