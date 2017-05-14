from datetime import datetime
from io import BytesIO

import discord
from PIL import Image, ImageFont, ImageDraw


class Countdown(object):

    def __init__(self, client, server, date, icon, font, size, color="255,255,255", suffix=None, prefix=None):
        self.client = client
        self.server = server
        self.date = date
        self.icon = icon
        self.font = font
        self.size = size
        self.color = color
        self.suffix = suffix
        self.prefix = prefix

    async def update(self):
        r, g, b = [int(x) for x in self.color.split(",")]
        today = datetime.utcnow().date()
        end_day = datetime.strptime(self.date, "%Y-%m-%d").date()
        diff = end_day - today
        text = str(diff.days)
        img = Image.open(self.icon)
        iw, ih = img.size

        draw = ImageDraw.Draw(img)
        large_font = ImageFont.truetype(self.font, self.size)
        small_font = ImageFont.truetype(self.font, int(.500 * self.size))
        pw, ph = small_font.getsize(self.prefix)
        tw, th = large_font.getsize(text)
        sw, sh = small_font.getsize(self.suffix)
        x, y = (iw - (pw + tw + sw)) / 2, (ih - th - 15) / 2
        draw.text((x - tw, y + int(.5 * th)), self.prefix, (r, g, b), font=small_font)
        draw.text((x, y), text, (r, g, b), font=large_font)
        draw.text((x + tw, y + int(.5 * th)), self.suffix, (r, g, b), font=small_font)

        with BytesIO() as data:
            img.save(data, format="PNG")
            try:
                await self.client.edit_server(self.server, icon=data.getvalue())
                return "{}: Set icon to {} days!".format(self.server.name, text)
            except discord.Forbidden:
                return "{}: Failed to set icon. Permission 'Manage Server' is required!".format(self.server.name)
