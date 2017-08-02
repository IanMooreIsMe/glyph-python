import json

import requests


class HasteBin(object):

    def __init__(self):
        self.url = "https://hastebin.com/"

    def post(self, text):
        response = requests.post(self.url + "documents", text)
        haste = self.url + json.loads(response.text)["key"]
        return haste
