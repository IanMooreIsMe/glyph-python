import json
import urllib.parse

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    # Fall back to psycopg2cffi
    import psycopg2cffi as psycopg2
    from psycopg2cffi.extras import RealDictCursor

from . import hastebin


class ConfigDatabase(object):

    __slots__ = ["url", "conn", "cur", "configs"]

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
        self.cur.execute("SELECT guild_id, wiki, selectable_roles, spoilers_channel, spoilers_keywords,"
                         " fa_quickview_enabled, fa_quickview_thumbnail, picarto_quickview_enabled, auditing_channel, "
                         "auditing_joins, auditing_leaves, auditing_reactions FROM configuration")
        rows = self.cur.fetchall()
        for row in rows:
            guild_id = row.get("guild_id")
            row.pop("guild_id")
            self.configs.update({guild_id: self._pretty_print(row)})
        self.close()

    def load(self, guild_id):
        self.open()
        self.cur.execute("SELECT guild_id, wiki, selectable_roles, spoilers_channel, spoilers_keywords,"
                         " fa_quickview_enabled, fa_quickview_thumbnail, picarto_quickview_enabled, auditing_channel, "
                         "auditing_joins, auditing_leaves, auditing_reactions FROM configuration "
                         "WHERE guild_id = (%s)", [guild_id])
        row = self.cur.fetchone()
        guild_id = row.get("guild_id")
        self.configs.update({guild_id: self._pretty_print(row)})
        self.close()

    @staticmethod
    def _pretty_print(config):
        pretty_config = {
            "roles": {
              "selectable": config["selectable_roles"]
            },
            "quickview": {
              "fa": {
                "enabled": config["fa_quickview_enabled"],
                "thumbnail": config["fa_quickview_thumbnail"]
              },
              "picarto": {
                "enabled": config["picarto_quickview_enabled"]
              }
            },
            "spoilers": {
              "safe_channel": config["spoilers_channel"],
              "keywords": config["spoilers_keywords"]
            },
            "auditing": {
              "channel": config["auditing_channel"],
              "joins": config["auditing_joins"],
              "leaves": config["auditing_leaves"],
              "reactions": config["auditing_reactions"]
            },
            "wiki": config["wiki"]
        }
        return pretty_config

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
                             " (guild_id, wiki, selectable_roles, spoilers_channel, spoilers_keywords,"
                             " fa_quickview_enabled, fa_quickview_thumbnail, picarto_quickview_enabled, "
                             " auditing_channel, auditing_joins, auditing_leaves, auditing_reactions)"
                             " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                             " ON CONFLICT (guild_id) DO UPDATE SET"
                             " (wiki, selectable_roles, spoilers_channel, spoilers_keywords,"
                             " fa_quickview_enabled, fa_quickview_thumbnail, picarto_quickview_enabled, "
                             " auditing_channel, auditing_joins, auditing_leaves, auditing_reactions)"
                             " = (EXCLUDED.wiki, EXCLUDED.selectable_roles, EXCLUDED.spoilers_channel, "
                             " EXCLUDED.spoilers_keywords, EXCLUDED.fa_quickview_enabled, "
                             " EXCLUDED.fa_quickview_thumbnail, EXCLUDED.picarto_quickview_enabled, "
                             " EXCLUDED.auditing_channel, EXCLUDED.auditing_joins, EXCLUDED.auditing_leaves, "
                             " EXCLUDED.auditing_reactions)",
                             [server.id,
                              config["wiki"],
                              config["roles"]["selectable"],
                              config["spoilers"]["safe_channel"],
                              config["spoilers"]["keywords"],
                              config["quickview"]["fa"]["enabled"],
                              config["quickview"]["fa"]["thumbnail"],
                              config["quickview"]["picarto"]["enabled"],
                              config["auditing"]["channel"],
                              config["auditing"]["joins"],
                              config["auditing"]["leaves"],
                              config["auditing"]["reactions"]])
            self.conn.commit()
        except psycopg2.Error as e:
            self.close()
            return "{}: {}".format(e.diag.severity, e.diag.message_primary)
        else:
            self.configs.update({int(server.id): config})
            self.close()
            return "Success!"

    def outhaste(self, server):
        try:
            haste = hastebin.post(json.dumps(self.get(server), sort_keys=True, indent=4))
        except json.JSONDecodeError as e:
            haste = "\n*Error dumping the JSON file. This issue will be investigated.*\n```{}```".format(e)
        return haste

    def inhaste(self, server, haste_key):
        try:
            config = json.loads(hastebin.get(haste_key))
        except json.JSONDecodeError as e:
            return e
        else:
            result = self.update(server, config)
        return result

    def close(self):
        self.cur.close()
        self.conn.close()
