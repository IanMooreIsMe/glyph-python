import random
from datetime import datetime

import discord
import pytz


def get_time_embed(timezone=None):
    title = "UTC Time"
    # timestamp = datetime.utcnow()
    time = datetime.utcnow()
    try:
        if timezone:
            # timestamp = datetime.utcnow().replace(tzinfo=pytz.timezone(timezone))
            time = datetime.now(tz=pytz.timezone(timezone))
            title = "{} Time".format(timezone)
    except pytz.UnknownTimeZoneError:
        pass
    embed = discord.Embed(title=title, description=time.strftime("**%H:%M:%S** on %A %B %d %Y"))
    try_tz = random.choice(pytz.common_timezones)
    embed.set_footer(text="Time | Try asking \"{} time\"".format(try_tz))
    return embed
