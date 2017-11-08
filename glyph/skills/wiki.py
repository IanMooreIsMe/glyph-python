from datetime import datetime

import wikia
import wikipedia
from discord import Embed

from .commander import register


@register("wiki")
async def search(message):
    query = message.ai.get_parameter("search_query")
    wiki = message.config["wiki"]
    if wiki is None or wiki.lower() == "wikipedia":
        try:
            page = wikipedia.page(query)
            summary = wikipedia.summary(query, sentences=3)
            embed = Embed(title=page.title, url=page.url, description=summary, timestamp=datetime.utcnow())
            try:
                embed.set_thumbnail(url=page.images[0])
            except (IndexError, AttributeError):
                pass
            suggestion = wikipedia.random()
            embed.set_footer(text="Wikipedia | Try asking \"What is {}?\"".format(suggestion))
            await message.reply(embed=embed)
        except (ValueError, wikipedia.WikipediaException):
            await message.reply("Sorry, I have no information for your search query `{}`.".format(query))
        return
    elif query is None:
        await message.reply("Sorry, I couldn't find a search query.", expire_time=5)
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
            await message.reply(embed=embed)
        except (ValueError, wikia.wikia.WikiaError):
            await message.reply("Sorry, I have no information for your search query `{}`.".format(query))


# @register("define_word")
# async def define(bot, message, ai, config):
#     parser = WiktionaryParser()
#     word = parser.fetch(ai.get_parameter("word"))
#     embed = Embed(title=f"Definition for {word}",
#                   description=f"**Definition** {word['definitions']['text']}\n"
#                               f"**Part of Speech** {word['definitions']['partOfSpeech']}"
#                               f"**Example** {word['definitions']['examples'][0]}"
#                               f"**Etymology** {word['etymology']}",
#                   timestamp=datetime.utcnow())
#     embed.set_footer(text="Wiktionary")
#     await bot.safe_send_message(message.channel, embed=embed)
