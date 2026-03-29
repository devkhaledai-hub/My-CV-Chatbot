from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr
from knowledge_base import search_knowledge_base, build_knowledge_base
from qa_database import search_qa, save_qa, init_db


load_dotenv(override=True)


def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        },
    )


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}


def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}


def lookup_knowledge_base(query):
    """Search the RAG knowledge base for relevant information."""
    results = search_knowledge_base(query, n_results=3)
    if not results:
        return {
            "results": [],
            "message": "No relevant information found in the knowledge base.",
        }
    return {"results": results}


def lookup_qa_database(query):
    """Search the Q&A database for previously answered questions."""
    results = search_qa(query, limit=3)
    if not results:
        return {"results": [], "message": "No matching Q&A found in the database."}
    return {"results": results}


def save_qa_pair(question, answer, category="general"):
    """Save a new question-answer pair to the database for future reference."""
    result = save_qa(question, answer, category)
    return result


record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user",
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it",
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context",
            },
        },
        "required": ["email"],
        "additionalProperties": False,
    },
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered",
            },
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}

lookup_knowledge_base_json = {
    "name": "lookup_knowledge_base",
    "description": "Search the knowledge base for relevant background information, career details, skills, projects, or personal facts. Use this when you need more context to answer a question about the person.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant information in the knowledge base",
            }
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}

lookup_qa_database_json = {
    "name": "lookup_qa_database",
    "description": "Search the Q&A database for previously answered common questions. Use this to check if a similar question has been answered before.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The question or keywords to search for in the Q&A database",
            }
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}

save_qa_pair_json = {
    "name": "save_qa_pair",
    "description": "Save a new question and its answer to the Q&A database for future reference. Use this after successfully answering a substantive question so it can be reused later.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that was asked",
            },
            "answer": {"type": "string", "description": "The answer that was provided"},
            "category": {
                "type": "string",
                "description": "Category for the Q&A pair (e.g., 'career', 'skills', 'contact', 'personal', 'general')",
            },
        },
        "required": ["question", "answer"],
        "additionalProperties": False,
    },
}

tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json},
    {"type": "function", "function": lookup_knowledge_base_json},
    {"type": "function", "function": lookup_qa_database_json},
    {"type": "function", "function": save_qa_pair_json},
]


class Me:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Khaled Mohamed"
        reader = PdfReader("me/my_details.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("me/my_summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()

        # Initialize knowledge base and Q&A database
        print("Building knowledge base from documents...")
        build_knowledge_base()
        print("Initializing Q&A database...")
        init_db()

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append(
                {
                    "role": "tool",
                    "content": json.dumps(result),
                    "tool_call_id": tool_call.id,
                }
            )
        return results

    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. \
\n\nYou also have access to these additional tools:\n\
- lookup_knowledge_base: Search a vector knowledge base containing detailed documents about {self.name}. Use this when the summary and LinkedIn profile don't have enough detail to answer a question.\n\
- lookup_qa_database: Search a database of previously answered questions. Check this first for common questions to provide consistent answers.\n\
- save_qa_pair: After answering a substantive new question well, save the Q&A to the database so it can be referenced in future conversations.\n\
\nWorkflow: For each user question, first check the Q&A database for an existing answer. If not found, search the knowledge base. Use the summary and LinkedIn profile as fallback context."

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt

    def chat(self, message, history):
        messages = (
            [{"role": "system", "content": self.system_prompt()}]
            + history
            + [{"role": "user", "content": message}]
        )
        done = False
        while not done:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini", messages=messages, tools=tools
            )
            if response.choices[0].finish_reason == "tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content


if __name__ == "__main__":
    me = Me()
    gr.ChatInterface(me.chat).launch()
