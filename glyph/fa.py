import json
import re
from datetime import datetime

import requests
from discord import Embed


class Submission(object):

    regex = re.compile("((http[s]?):\/\/)?(www\.)?(furaffinity.net)\/(\w*)\/(\d{8})\/?", re.IGNORECASE)

    def __init__(self, *, url=None, id=None):
        if url is not None:
            url_format = re.compile("((http[s]?):\/\/)?(www\.)?(furaffinity.net)\/(\w*)\/(\d{8})\/?", re.IGNORECASE)
            link = url_format.search(url)
            self.type = link.group(5)
            self.id = link.group(6)
        else:
            self.id = id
        get = requests.get("http://faexport.boothale.net/submission/{}.json".format(self.id)).text
        submission_info = json.loads(get)
        self.title = submission_info.get("title")
        self.author = submission_info.get("name")
        self.posted = submission_info.get("posted")
        self.category = submission_info.get("category")
        self.theme = submission_info.get("theme")
        self.species = submission_info.get("species")
        self.gender = submission_info.get("gender")
        self.favorites = submission_info.get("favorites")
        self.comments = submission_info.get("comments")
        self.views = submission_info.get("views")
        self.rating = submission_info.get("rating")
        self.link = submission_info.get("link")
        self.download = submission_info.get("download")
        if self.rating == "General":
            self.color = 0x10FF00
        elif self.rating == "Mature":
            self.color = 0x0026FF
        else:  # rating=="Adult"
            self.color = 0xFF0000

    def get_embed(self, *, thumbnail=False):
        embed = Embed(
            title=self.title,
            description="Posted by {} at {}\n"
                        "{} > {} > {} > {} > {}\n"
                        "Favorites: {} | Comments: {} | Views: {}".format(
                            self.author, self.posted,
                            self.rating, self.category, self.theme,
                            self.species, self.gender,
                            self.favorites, self.comments, self.views),
                        url=self.link, color=self.color, timestamp=datetime.now())
        embed.set_footer(text="FurAffinity")
        if thumbnail:
            download = self.download
            embed.set_thumbnail(url=download)
        return embed
