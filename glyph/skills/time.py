from datetime import datetime

import discord
import pytz


def get_time_embed(timezone=None):
    if timezone:
        title = "{} Time".format(timezone)
        timestamp = datetime.now(tz=pytz.timezone(timezone))
        print(pytz.timezone(timezone))
    else:
        title = "Current Localized Time"
        timestamp = datetime.utcnow()
    print(timestamp)
    embed = discord.Embed(title=title, timestamp=timestamp)
    embed.set_footer(text="Time Skill")
    return embed
