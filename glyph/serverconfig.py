import configparser
import urllib.parse
from datetime import datetime
from os import environ

import discord
import psycopg2


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


class DatabaseConfig(object):

    def __init__(self):
        urllib.parse.uses_netloc.append("postgres")
        self.url = urllib.parse.urlparse(environ.get("DATABASE_URL"))
        self.conn = None
        self.cur = None

    def open(self):
        self.conn = psycopg2.connect(
            database=self.url.path[1:],
            user=self.url.username,
            password=self.url.password,
            host=self.url.hostname,
            port=self.url.port
        )
        self.cur = self.conn.cursor()

    def load(self, server):
        self.cur.execute("SELECT * FROM configuration WHERE guild_id = '{}'".format(server.id))
        row = self.cur.fetchone()
        if not row:
            self.cur.execute("SELECT * FROM configuration WHERE guild_id = '0'")
            row = self.cur.fetchone()
        colnames = [desc[0] for desc in self.cur.description]
        colvals = row
        config = dict(zip(colnames, colvals))
        return ServerConfig(config)

    def close(self):
        self.cur.close()
        self.conn.close()


class ServerConfig:

    def __init__(self, config):
        self.config = config

    def get(self, key):
        return self.config.get(key)
