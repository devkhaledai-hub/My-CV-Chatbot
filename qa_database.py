"""
SQLite Q&A Database.
Stores common questions and answers that the LLM can read from and write to.
"""

import sqlite3
import os

DB_PATH = "qa_database.db"


def get_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the Q&A database with the schema and optional seed data."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS qa_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            times_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()

    # Seed with some starter Q&A if the table is empty
    cursor.execute("SELECT COUNT(*) FROM qa_pairs")
    if cursor.fetchone()[0] == 0:
        seed_data = [
            (
                "What do you do?",
                "I'm an AI Engineer specializing in Generative AI, large language models, and intelligent systems. I build multi-agent architectures and end-to-end AI pipelines.",
                "career",
            ),
            (
                "What technologies do you work with?",
                "I work with Python, PyTorch, LLMs (GPT, Claude, open-source models), vector databases, multi-agent frameworks, and cloud platforms.",
                "skills",
            ),
            (
                "Are you available for consulting?",
                "I'm always open to discussing interesting AI projects. Feel free to share your email and I'll get back to you!",
                "contact",
            ),
            (
                "What is your background?",
                "I have a background in software engineering and data science, with deep expertise in generative AI and building scalable, real-world AI solutions.",
                "career",
            ),
        ]
        cursor.executemany(
            "INSERT INTO qa_pairs (question, answer, category) VALUES (?, ?, ?)",
            seed_data,
        )
        conn.commit()
        print(f"Seeded database with {len(seed_data)} Q&A pairs.")

    conn.close()


def search_qa(query, limit=3):
    """Search for Q&A pairs matching the query (simple keyword search)."""
    conn = get_connection()
    cursor = conn.cursor()
    # Use LIKE for simple keyword matching
    words = query.lower().split()
    conditions = " OR ".join(
        ["(LOWER(question) LIKE ? OR LOWER(answer) LIKE ?)" for _ in words]
    )
    params = []
    for word in words:
        params.extend([f"%{word}%", f"%{word}%"])
    cursor.execute(
        f"SELECT id, question, answer, category FROM qa_pairs WHERE {conditions} ORDER BY times_used DESC LIMIT ?",
        params + [limit],
    )
    rows = cursor.fetchall()

    # Increment usage counter
    for row in rows:
        cursor.execute(
            "UPDATE qa_pairs SET times_used = times_used + 1 WHERE id = ?", (row["id"],)
        )
    conn.commit()
    conn.close()

    return [
        {
            "question": row["question"],
            "answer": row["answer"],
            "category": row["category"],
        }
        for row in rows
    ]


def get_all_qa(category=None):
    """Get all Q&A pairs, optionally filtered by category."""
    conn = get_connection()
    cursor = conn.cursor()
    if category:
        cursor.execute(
            "SELECT question, answer, category FROM qa_pairs WHERE category = ? ORDER BY times_used DESC",
            (category,),
        )
    else:
        cursor.execute(
            "SELECT question, answer, category FROM qa_pairs ORDER BY times_used DESC"
        )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "question": row["question"],
            "answer": row["answer"],
            "category": row["category"],
        }
        for row in rows
    ]


def save_qa(question, answer, category="general"):
    """Save a new Q&A pair to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO qa_pairs (question, answer, category) VALUES (?, ?, ?)",
        (question, answer, category),
    )
    conn.commit()
    conn.close()
    return {"saved": "ok", "question": question}


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
    print("Current Q&A pairs:")
    for qa in get_all_qa():
        print(f"  [{qa['category']}] Q: {qa['question']}")
        print(f"           A: {qa['answer']}")
