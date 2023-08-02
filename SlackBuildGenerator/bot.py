import os
import slack
import re
import json
from pathlib import Path
from dotenv import load_dotenv
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from flask import Flask

env_path = Path(".") / '.env'
load_dotenv(dotenv_path=env_path)

app = App(
    token=os.environ['SLACK_BOT_TOKEN'],
    signing_secret=os.environ['SIGNING_SECRETS']
)

client = slack.WebClient(token=os.environ['SLACK_BOT_TOKEN'])

BOT_ID = client.api_call("auth.test")['user_id']

# Function to read the local database containing max build numbers
def read_build_numbers():
    try:
        with open('build_numbers.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"Dev": 123, "Test": 12, "Beta": 123}

# Function to update and save the local database with new max build numbers
def update_build_numbers(build_numbers):
    with open('build_numbers.json', 'w') as f:
        json.dump(build_numbers, f)

# Function to extract version and build number from the message
def extract_version_build(message_text):
    pattern = r'SP(Dev|Test|Beta) v(\d+\.\d+\.\d+)\s+\((\d+)\)'
    match = re.search(pattern, message_text)
    if match:
        return match.group(1), match.group(2), int(match.group(3))
    return None, None, None

# Function to generate the reply message based on the received text
def generate_reply(message_text):
    build_numbers = read_build_numbers()
    build_type, version, build = extract_version_build(message_text)
    if build_type == None:
        return ""
    
    if build_type and version and build:
        if build_type == 'Dev':
            build_numbers['Dev'] = max(build + 1, build_numbers['Dev'])
        elif build_type == 'Test':
            build_numbers['Test'] = max(build + 1, build_numbers['Test'])
        elif build_type == 'Beta':
            build_numbers['Beta'] = max(build + 1, build_numbers['Beta'])

    update_build_numbers(build_numbers)

    # Prepare the reply message
    reply = "Available builds are:\n"
    for key, value in build_numbers.items():
        reply += f"*{key}*: `{value}`\n"

    return reply.strip()

@app.event('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = payload.get('channel')
    user_id = payload.get('user')
    text = payload.get('text')
    reply = generate_reply(text)
    if BOT_ID != user_id and reply != "":
        app.client.chat_postMessage(channel=channel_id, text=reply)

if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))