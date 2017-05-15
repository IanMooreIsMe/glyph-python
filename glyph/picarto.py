import requests
import json
import re
import time

from discord import Embed


class Channel(object):

    regex = re.compile("((http[s]?):\/\/)?(www\.)?(picarto.tv)\/(\w*)\/?", re.IGNORECASE)

    def __init__(self, *, url=None, name=None):
        if url is not None:
            url_format = re.compile("((http[s]?):\/\/)?(www\.)?(picarto.tv)\/(\w*)\/?", re.IGNORECASE)
            link = url_format.search(url)
            self.name = link.group(5)
            self.url = url
        else:
            self.name = name
            self.url = "https://picarto.tv/{}".format(self.name)
        get = requests.get("https://api.picarto.tv/v1/channel/name/{}".format(self.name)).text
        channel_info = json.loads(get)
        self.name = channel_info.get("name")
        self.viewers = channel_info.get("viewers")
        self.category = channel_info.get("category")
        self.title = channel_info.get("title")
        if channel_info.get("online"):
            self.status = "Online"
            self.color = 0x10FF00
        else:
            self.status = "Offline"
            self.color = 0xFF0000
        if channel_info.get("adult"):
            self.adult = "NSFW"
        else:
            self.adult = "SFW"

    def _update_status(self):
        get = requests.get("https://api.picarto.tv/v1/channel/name/{}".format(self.name)).text
        channel_info = json.loads(get)
        if channel_info.get("online"):
            self.status = "Online"
            self.color = 0x10FF00
        else:
            self.status = "Offline"
            self.color = 0xFF0000

    def get_embed(self):
        self._update_status()
        embed = Embed(
            title=self.name,
            description="{}\n"
                        "{} | {} | Viewers: {}".format(
                            self.title,
                            self.status, self.adult, self.viewers, time.strftime("%H:%M:%S")),
                        url=self.url, color=self.color)
        return embed
