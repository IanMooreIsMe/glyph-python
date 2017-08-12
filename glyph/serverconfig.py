import json
import urllib.parse

import psycopg2
from psycopg2.extras import RealDictCursor

from .haste import HasteBin


class ConfigDatabase(object):

    def __init__(self, url):
        urllib.parse.uses_netloc.append("postgres")
        self.url = urllib.parse.urlparse(url)
        self.conn = None
        self.cur = None
        self.configs = {}

    def open(self):
        self.conn = psycopg2.connect(
            database=self.url.path[1:],
            user=self.url.username,
            password=self.url.password,
            host=self.url.hostname,
            port=self.url.port
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)

    def load_all(self):
        self.open()
        self.configs.clear()
        self.cur.execute("SELECT * FROM configuration")
        rows = self.cur.fetchall()
        for row in rows:
            guild_id = row.get("guild_id")
            row.pop("guild_id")
            self.configs.update({guild_id: row})
        self.close()

    def load(self, guild_id):
        self.open()
        self.cur.execute("SELECT * FROM configuration WHERE guild_id = (%s)", [guild_id])
        row = self.cur.fetchone()
        guild_id = row.get("guild_id")
        row.pop("guild_id")
        self.configs.update({guild_id: row})
        self.close()

    def delete(self, guild_id):
        self.open()
        self.cur.execute("DELETE FROM configuration WHERE guild_id = (%s)", [guild_id])
        self.conn.commit()
        try:
            self.configs.pop(guild_id)
        except KeyError:
            pass
        self.close()

    def get(self, server):
        config = self.configs.get(0)
        try:
            if self.configs.get(int(server.id)) is not None:
                config = self.configs.get(int(server.id))
        except AttributeError:
            pass
        return config

    def update(self, server, config):
        self.open()
        try:
            self.cur.execute("INSERT INTO configuration"
                             " (guild_id, wiki, allowed_roles, spoilers_channel, spoilers_keywords,"
                             " fa_quickview_enabled, fa_quickview_thumbnail, picarto_quickview_enabled)"
                             " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                             " ON CONFLICT (guild_id) DO UPDATE SET"
                             " (wiki, allowed_roles, spoilers_channel, spoilers_keywords,"
                             " fa_quickview_enabled, fa_quickview_thumbnail, picarto_quickview_enabled)"
                             " = (EXCLUDED.wiki, EXCLUDED.allowed_roles, EXCLUDED.spoilers_channel, "
                             " EXCLUDED.spoilers_keywords, EXCLUDED.fa_quickview_enabled, "
                             " EXCLUDED.fa_quickview_thumbnail, EXCLUDED.picarto_quickview_enabled)",
                             [server.id,
                              config.get("wiki"),
                              config.get("allowed_roles"),
                              config.get("spoilers_channel"),
                              config.get("spoilers_keywords"),
                              config.get("fa_quickview_enabled"),
                              config.get("fa_quickview_thumbnail"),
                              config.get("picarto_quickview_enabled")])
            self.conn.commit()
        except (psycopg2.DataError, psycopg2.DatabaseError) as e:
            self.close()
            return e
        else:
            self.configs.update({int(server.id): config})
            self.close()
            return "Success!"

    def outhaste(self, server):
        haste = HasteBin().post(json.dumps(self.get(server), sort_keys=True, indent=4))
        return haste

    def inhaste(self, server, haste_key):
        try:
            config = json.loads(HasteBin().get(haste_key))
        except json.JSONDecodeError as e:
            return e
        else:
            result = self.update(server, config)
        return result

    def close(self):
        self.cur.close()
        self.conn.close()



