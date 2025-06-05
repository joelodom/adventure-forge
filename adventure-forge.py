#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error

API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("Error: Please set the OPENAI_API_KEY environment variable.")
    sys.exit(1)

def call_openai(messages):
    """
    Send a chat-completion request to OpenAI and return the assistant's reply.
    """
    payload = {
        "model": "gpt-4",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(e.read().decode())
        sys.exit(1)

def main():
    print("=== AI Role-Playing Game Master ===")
    print("Describe the kind of adventure you want (e.g., 'high fantasy quest', 'space exploration', 'modern spy thriller').")
    genre = input("Adventure style: ").strip()
    if not genre:
        print("You must describe the style of adventure. Exiting.")
        sys.exit(0)

    # Initial system prompt to set up the Game Master persona:
    system_prompt = (
        f"You are a creative, consistent game master running a {genre} role-playing adventure. "
        "First, ask the player any clarifying questions needed to establish the setting, characters, and rules. "
        "Once everything is clear, start narrating the story: describe scenes, present choices, and respond to actions. "
        "Keep track of details the player provides and maintain continuity. "
        "Be imaginative, adventurous, and stay in character as the GM."
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # The GM may ask clarifying questions right away:
    initial_reply = call_openai(messages)
    print("\nGM:", initial_reply, "\n")
    messages.append({"role": "assistant", "content": initial_reply})

    # Main REPL loop:
    while True:
        try:
            user_input = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Exiting game. Farewell, adventurer!")
            break

        messages.append({"role": "user", "content": user_input})
        reply = call_openai(messages)
        print("\nGM:", reply, "\n")
        messages.append({"role": "assistant", "content": reply})

if __name__ == "__main__":
    main()
