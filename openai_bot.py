#!/usr/bin/env python3

import argparse
import requests
import json
import threading
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--telegram_token", type=str, help="Telegram token")
parser.add_argument("--openai_token", type=str, help="Telegram token")
args = parser.parse_args()

# OpenAI secret Key
API_KEY = args.openai_token
# Models: text-davinci-003,text-curie-001,text-babbage-001,text-ada-001
MODEL = "text-davinci-003"
# Telegram secret access bot token
BOT_TOKEN = args.telegram_token
# Defining the bot's personality using adjectives
BOT_PERSONALITY = "Answer in a Professional tone, "
# Specify your Chat Bot handle
CHATBOT_HANDLE = "@ask"

root_path = Path(__file__).resolve().parent

# Function that gets the response from OpenAI's chatbot
def openAI(prompt):
    # Make the request to the OpenAI API
    response = requests.post(
        "https://api.openai.com/v1/completions", headers={"Authorization": f"Bearer {API_KEY}"}, json={"model": MODEL, "prompt": prompt, "temperature": 0.4, "max_tokens": 300}, timeout=10
    )

    result = response.json()
    final_result = "".join(choice["text"] for choice in result["choices"])
    return final_result


# Function that gets an Image from OpenAI
def openAImage(prompt):
    # Make the request to the OpenAI API
    resp = requests.post("https://api.openai.com/v1/images/generations", headers={"Authorization": f"Bearer {API_KEY}"}, json={"prompt": prompt, "n": 1, "size": "1024x1024"}, timeout=10)
    response_text = json.loads(resp.text)

    return response_text["data"][0]["url"]


# Function that sends a message to a specific telegram group
def telegram_bot_sendtext(bot_message, chat_id, msg_id):
    data = {"chat_id": chat_id, "text": bot_message, "reply_to_message_id": msg_id}
    response = requests.post("https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage", json=data, timeout=5)
    return response.json()


# Function that sends an image to a specific telegram group
def telegram_bot_sendimage(image_url, group_id, msg_id):
    data = {"chat_id": group_id, "photo": image_url, "reply_to_message_id": msg_id}
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendPhoto"

    response = requests.post(url, data=data, timeout=5)
    return response.json()


# Function that retrieves the latest requests from users in a Telegram group,
# generates a response using OpenAI, and sends the response back to the group.
def Chatbot():
    # Retrieve last ID message from text file for ChatGPT update
    filename = root_path / "chatgpt.txt"
    if not filename.exists():
        with Path(filename).open(mode="w") as f:
            f.write("1")

    last_update = Path(filename).read_text()

    # Check for new messages in Telegram group
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update}"
    response = requests.get(url, timeout=5)
    data = json.loads(response.content)
    # print(data)

    for result in data["result"]:
        try:
            # Checking for new message
            if float(result["update_id"]) > float(last_update):
                # Checking for new messages that did not come from chatGPT
                if not result["message"]["from"]["is_bot"]:
                    last_update = str(int(result["update_id"]))

                    # Retrieving message ID of the sender of the request
                    msg_id = str(int(result["message"]["message_id"]))

                    # Retrieving the chat ID
                    chat_id = str(result["message"]["chat"]["id"])

                    # Checking if user wants an image
                    if "/img" in result["message"]["text"]:
                        prompt = result["message"]["text"].replace("/img", "")
                        bot_response = openAImage(prompt)
                        telegram_bot_sendimage(bot_response, chat_id, msg_id)
                    # Checking that user mentionned chatbot's username in message
                    if CHATBOT_HANDLE in result["message"]["text"]:
                        prompt = result["message"]["text"].replace(CHATBOT_HANDLE, "")
                        # Calling OpenAI API using the bot's personality
                        bot_response = openAI(f"{BOT_PERSONALITY}{prompt}")
                        # Sending back response to telegram group
                        telegram_bot_sendtext(bot_response, chat_id, msg_id)
                    # Verifying that the user is responding to the ChatGPT bot
                    if "reply_to_message" in result["message"]:
                        if result["message"]["reply_to_message"]["from"]["is_bot"]:
                            prompt = result["message"]["text"]
                            bot_response = openAI(f"{BOT_PERSONALITY}{prompt}")
                            telegram_bot_sendtext(bot_response, chat_id, msg_id)
        except Exception as e:
            print(e)

    # Updating file with last update ID
    with Path(filename).open(mode="w") as f:
        f.write(last_update)

    return "done"


# Running a check every 5 seconds to check for new messages
def main():
    timertime = 5
    Chatbot()
    # 5 sec timer
    threading.Timer(timertime, main).start()


# Run the main function
if __name__ == "__main__":
    main()
