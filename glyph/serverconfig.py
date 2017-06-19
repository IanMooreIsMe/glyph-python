import configparser
from datetime import datetime

import discord


class Config(object):

    def __init__(self, server=None):
        self.server = server
        self.created = datetime.now()
        self.parsing_status = "Okay"
        self.config = configparser.ConfigParser()
        self.config.read("./config/default.ini")
        if server:
            config_channel = discord.utils.get(server.channels, name="glyph")
            if config_channel:
                try:
                    self.config.read_string(config_channel.topic)
                except configparser.ParsingError as e:
                    self.parsing_status = "{}\n\nUsing default config as fallback!".format(e)
                    self.config = configparser.ConfigParser()
                    self.config.read("./config/config.ini")

    def get(self, section, option):
        return self.config.get(section, option)

    def getboolean(self, section, option):
        return self.config.getboolean(section, option)

    def getlist(self, section, option, *, delimiter=","):
        raw_list = self.get(section, option).split(delimiter)
        cleaned_list = list(map(str.strip, raw_list))
        return cleaned_list
