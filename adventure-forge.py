#!/usr/bin/env python3

import os
import json
import uuid
import urllib.request
import urllib.error
from pymongo import MongoClient
import os

def load_env(path=".env"):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, val = line.split("=", 1)
                # don’t overwrite real environment vars if they already exist
                os.environ.setdefault(key, val)
    except FileNotFoundError:
        pass

load_env()

OPENAI_KEY  = os.environ.get("OPENAI_API_KEY")
MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME     = os.environ.get("DB_NAME")
COLL_NAME   = os.environ.get("COLLECTION_NAME")

if not OPENAI_KEY or not MONGODB_URI or not DB_NAME or not COLL_NAME:
    print("Error: Please set OPENAI_API_KEY, MONGODB_URI, DB_NAME and COLLECTION_NAME.")
    exit(1)

# Initialize MongoDB client
mongo_client = MongoClient(MONGODB_URI)
db            = mongo_client[DB_NAME]
sessions      = db[COLL_NAME]

# OpenAI endpoint
API_URL = "https://api.openai.com/v1/chat/completions"
MODEL   = "gpt-4"  # or "gpt-3.5-turbo"

def call_openai(messages):
    """Calls OpenAI ChatCompletion."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_KEY}"
    }
    req = urllib.request.Request(API_URL,
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        return f"[OpenAI Error {e.code}: {e.reason}]"

def lambda_handler(event, context):
    """
    Lambda entry point.
    - POST /start   => { genre }
    - POST /message => { sessionId, userMessage }
    """
    method = event.get("httpMethod", "")
    # For HTTP API v2 use "rawPath", for REST API use "path"
    path   = event.get("rawPath") or event.get("path") or ""
    body   = json.loads(event.get("body", "{}"))

    # ── Start a new session ────────────────────────────────────────────────────
    if method == "POST" and path == "/start":
        genre = body.get("genre", "").strip()
        if not genre:
            return {"statusCode": 400,
                    "body": json.dumps({"error": "Missing 'genre'."})}

        session_id = str(uuid.uuid4())
        system_prompt = (
            f"You are a creative, consistent game master running a {genre} "
            "role-playing adventure. First, ask the player any clarifying "
            "questions to establish setting, characters, and rules. Then begin "
            "narrating the story: describe scenes, present choices, and respond "
            "to actions. Keep track of details and maintain continuity. Be "
            "imaginative and adventurous."
        )
        messages = [{"role": "system", "content": system_prompt}]
        gm_reply = call_openai(messages)
        messages.append({"role": "assistant", "content": gm_reply})

        # Save to MongoDB
        sessions.insert_one({
            "_id": session_id,
            "messages": messages
        })

        return {
            "statusCode": 200,
            "body": json.dumps({
                "sessionId": session_id,
                "gmReply": gm_reply
            })
        }

    # ── Continue an existing session ──────────────────────────────────────────
    if method == "POST" and path == "/message":
        session_id = body.get("sessionId", "").strip()
        user_msg   = body.get("userMessage", "").strip()
        if not session_id or not user_msg:
            return {"statusCode": 400,
                    "body": json.dumps({"error": "Missing sessionId or userMessage."})}

        record = sessions.find_one({"_id": session_id})
        if not record:
            return {"statusCode": 404,
                    "body": json.dumps({"error": "Session not found."})}

        message_list = record["messages"]
        message_list.append({"role": "user", "content": user_msg})
        gm_reply = call_openai(message_list)
        message_list.append({"role": "assistant", "content": gm_reply})

        # Update MongoDB
        sessions.update_one(
            {"_id": session_id},
            {"$set": {"messages": message_list}}
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"gmReply": gm_reply})
        }

    # ── Unrecognized route ─────────────────────────────────────────────────────
    return {"statusCode": 404, "body": json.dumps({"error": "Not Found"})}

# ─── Console/REPL mode for local testing ─────────────────────────────────────
def main():
    print("\n🛠️  Adventure Forge Local Test\n")
    while True:
        print("1) Start new session")
        print("2) Send message to existing session")
        print("3) Exit")
        choice = input("> ").strip()
        if choice == "1":
            genre = input("Enter genre: ").strip()
            ev = {
                "httpMethod": "POST",
                "rawPath": "/start",
                "body": json.dumps({"genre": genre})
            }
            resp = lambda_handler(ev, None)
            print(json.dumps(json.loads(resp["body"]), indent=2))
        elif choice == "2":
            session_id = input("Enter sessionId: ").strip()
            msg        = input("Enter your message: ").strip()
            ev = {
                "httpMethod": "POST",
                "rawPath": "/message",
                "body": json.dumps({
                    "sessionId": session_id,
                    "userMessage": msg
                })
            }
            resp = lambda_handler(ev, None)
            print(json.dumps(json.loads(resp["body"]), indent=2))
        elif choice in ("3", "exit", "quit"):
            break
        else:
            print("Invalid choice, try 1, 2 or 3.")

if __name__ == "__main__":
    main()
