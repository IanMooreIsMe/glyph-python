from datetime import datetime

import wikia
import wikipedia
from discord import Embed

from .commander import register


@register("wiki")
async def search(bot, message, ai, config):
    query = ai.get_parameter("search_query")
    wiki = config["wiki"]
    if wiki is None or wiki.lower() == "wikipedia":
        try:
            page = wikipedia.page(query)
            summary = wikipedia.summary(query, sentences=3)
            embed = Embed(title=page.title, url=page.url, description=summary,  timestamp=datetime.utcnow())
            try:
                embed.set_thumbnail(url=page.images[0])
            except (IndexError, AttributeError):
                pass
            suggestion = wikipedia.random()
            embed.set_footer(text="Wikipedia | Try asking \"What is {}?\"".format(suggestion))
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
            results = wikia.search(wiki, query)
            page = wikia.page(wiki, results[0])
            url = page.url.replace(" ", "_")
            embed = Embed(title=page.title, url=url, description=page.summary, timestamp=datetime.utcnow())
            try:
                embed.set_thumbnail(url=page.images[0])
            except (IndexError, AttributeError):
                pass
            embed.set_footer(text="{} wikia".format(wiki))
            await bot.safe_send_message(message.channel, embed=embed, deletewith=message)
        except (ValueError, wikia.wikia.WikiaError):
            await bot.safe_send_message(message.channel,
                                        "Sorry, I have no information for your search query `{}`.".format(query))
