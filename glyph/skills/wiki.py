from datetime import datetime

import discord
import wikia
import wikipedia


async def wiki(bot, message, *, wiki=None, query=None):
    if wiki is None or wiki.lower() == "wikipedia":
        try:
            page = wikipedia.page(query)
            summary = wikipedia.summary(query, sentences=3)
            embed = discord.Embed(title=page.title, url=page.url, description=summary,  timestamp=datetime.now())
            try:
                embed.set_thumbnail(url=page.images[0])
            except (IndexError, AttributeError):
                pass
            embed.set_footer(text="Wikipedia")
            await bot.safe_send_message(message.channel, embed=embed, deletewith=message)
        except (ValueError, wikipedia.WikipediaException):
            await bot.safe_send_message(message.channel,
                                        "Sorry, I have no information for your search query `{}`.".format(query))
        return
    elif query is None:
        await bot.safe_send_message(message.channel, "Sorry, I couldn't find a search query.", expire_time=5)
        return
    else:
        try:
            search = wikia.search(wiki, query)
            page = wikia.page(wiki, search[0])
            url = page.url.replace(" ", "_")
            embed = discord.Embed(title=page.title, url=url, description=page.summary, timestamp=datetime.now())
            try:
                embed.set_thumbnail(url=page.images[0])
            except (IndexError, AttributeError):
                pass
            embed.set_footer(text="{} wikia".format(wiki))
            await bot.safe_send_message(message.channel, embed=embed, deletewith=message)
        except (ValueError, wikia.wikia.WikiaError):
            await bot.safe_send_message(message.channel,
                                        "Sorry, I have no information for your search query `{}`.".format(query))
