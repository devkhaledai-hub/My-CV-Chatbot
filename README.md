---
title: my_career_conversations
app_file: app.py
sdk: gradio
sdk_version: 6.10.0
---

# Personal AI Assistant

An agentic chatbot that acts as your digital representative on your personal website. Built with GPT-4o-mini, it uses **RAG** (Retrieval-Augmented Generation) and **tool calling** to answer questions about your career, skills, and background — all through a Gradio web interface.

## Architecture

```
User ──► Gradio Chat UI ──► GPT-4o-mini (with tools)
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                 ▼
         ChromaDB (RAG)    SQLite Q&A DB     Pushover Notifications
         Vector search     Read/Write Q&A    Contact & question alerts
```

## Features

### RAG Knowledge Base (ChromaDB)

- Automatically ingests all PDFs and text files from the `me/` folder
- Splits documents into overlapping chunks (500 chars, 50 char overlap)
- Stores embeddings in a persistent ChromaDB vector database
- Enables semantic search so the LLM can retrieve relevant context on demand

### SQL Q&A Database (SQLite)

- Stores common questions and answers that the LLM can **read from and write to**
- Seeded with starter Q&A pairs on first run
- Tracks usage count per Q&A for prioritization
- Allows the LLM to learn over time by saving new Q&A pairs

### Agentic Tool Use

The LLM has access to **5 tools** it can call autonomously:

| Tool                      | Description                                                       |
| ------------------------- | ----------------------------------------------------------------- |
| `lookup_qa_database`      | Search the Q&A database for previously answered questions         |
| `lookup_knowledge_base`   | Semantic search over the vector knowledge base                    |
| `save_qa_pair`            | Save a new question-answer pair for future conversations          |
| `record_user_details`     | Capture visitor contact info (sends push notification)            |
| `record_unknown_question` | Log questions that couldn't be answered (sends push notification) |

### LLM Workflow

For each user question, the assistant follows this workflow:

1. Check the **Q&A database** for an existing answer
2. Search the **knowledge base** for relevant document chunks
3. Fall back to the **summary and LinkedIn profile** loaded in context

## Project Structure

```
1_foundations/
├── app.py                # Main application — Gradio UI + LLM + tools
├── knowledge_base.py     # ChromaDB RAG setup — document ingestion & search
├── qa_database.py        # SQLite Q&A database — read/write operations
├── me/                   # Your personal documents (PDFs, text files)
│   ├── my_details.pdf    # LinkedIn/resume PDF
│   └── my_summary.txt    # Short bio summary
├── chroma_db/            # ChromaDB persistent storage (auto-generated)
└── qa_database.db        # SQLite database file (auto-generated)
```

## Setup

### 1. Install dependencies

```bash
pip install openai gradio pypdf chromadb python-dotenv requests
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-openai-api-key

# Optional: Pushover notifications for contact recording
PUSHOVER_TOKEN=your-pushover-token
PUSHOVER_USER=your-pushover-user
```

### 3. Add your documents

Place your personal documents in the `me/` folder:

- **PDFs** — resume, LinkedIn export, portfolio, etc.
- **Text files** — bio, summary, skills list, etc.

### 4. Run the app

```bash
python app.py
```

On startup, the app will:

- Build the ChromaDB knowledge base from your documents
- Initialize the SQLite Q&A database (with seed data on first run)
- Launch a Gradio chat interface at `http://localhost:7860`

## Tech Stack

- **Python** — Core language
- **OpenAI API** (GPT-4o-mini) — LLM with function calling
- **Gradio** — Web chat interface
- **ChromaDB** — Vector database for RAG
- **SQLite** — Persistent Q&A storage
- **pypdf** — PDF text extraction
- **Pushover** — Push notifications for visitor contacts
