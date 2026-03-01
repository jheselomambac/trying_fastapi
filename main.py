from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "notes.db")

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            pinned INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

create_table()

class NoteCreate(BaseModel):
    title: str
    content: str

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

def format_note(note):
    return {
        "id": note["id"],
        "title": note["title"],
        "content": note["content"],
        "pinned": bool(note["pinned"]),
        "created_at": note["created_at"],
        "updated_at": note["updated_at"]
    }

@app.post("/notes")
def create_note(note: NoteCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO notes (title, content, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """, (note.title, note.content, now, now))

    conn.commit()
    note_id = cursor.lastrowid

    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    new_note = cursor.fetchone()
    conn.close()

    return format_note(new_note)

@app.get("/notes")
def get_notes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes ORDER BY created_at DESC")
    notes = cursor.fetchall()
    conn.close()

    return [format_note(note) for note in notes]

@app.get("/notes/{note_id}")
def get_note(note_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    conn.close()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return format_note(note)

@app.put("/notes/{note_id}")
def update_note(note_id: int, note: NoteUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    existing_note = cursor.fetchone()

    if not existing_note:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")

    updated_title = note.title if note.title is not None else existing_note["title"]
    updated_content = note.content if note.content is not None else existing_note["content"]
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        UPDATE notes
        SET title = ?, content = ?, updated_at = ?
        WHERE id = ?
    """, (updated_title, updated_content, now, note_id))

    conn.commit()

    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    updated_note = cursor.fetchone()
    conn.close()

    return format_note(updated_note)

@app.delete("/notes/{note_id}")
def delete_note(note_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()

    if not note:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")

    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

    return format_note(note)

@app.patch("/notes/{note_id}/pinned")
def mark_pinned(note_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()

    if not note:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")

    new_status = 0 if note["pinned"] == 1 else 1
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        UPDATE notes
        SET pinned = ?, updated_at = ?
        WHERE id = ?
    """, (new_status, now, note_id))

    conn.commit()

    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    updated_note = cursor.fetchone()
    conn.close()

    return format_note(updated_note)

@app.get("/notes/pinned")
def get_pinned_notes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE pinned = 1")
    notes = cursor.fetchall()
    conn.close()

    return [format_note(note) for note in notes]