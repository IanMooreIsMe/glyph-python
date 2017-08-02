import json
import requests


class HasteBin(object):

    def __init__(self, text):
        self.url = "https://hastebin.com/"
        self.text = text

    def post(self):
        response = requests.post(self.url + "documents", self.text)
        haste = self.url + json.loads(response.text)["key"]
        return haste
