import json

import requests


def post(text):
    response = requests.post("https://hastebin.com/documents", text)
    try:
        haste = "https://hastebin.com/" + json.loads(response.text)["key"]
    except json.JSONDecodeError:
        haste = "Couldn't post to hastebin!"
    return haste


def get(key):
    response = requests.get("https://hastebin.com/raw/" + key)
    return response.text
