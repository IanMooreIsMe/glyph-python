from . import wiki, roles, reddit, info, moderation, time, reddit


class SkillCommander(object):

    def __init__(self, bot):
        self.bot = bot
        self.reddit = reddit.RedditSkill(bot)

    async def process(self, message, ai, config):
        action = ai.get_action_depth(0)
        if "ignore" in str(ai.contexts) and not ai.get_action_depth(1) == "insult":  # If ignoring the user
            await self.bot.safe_send_message(message.channel,
                                             "No {}, I'm done helping you for now.".format(message.author.mention))
        elif action == "skill" and not ai.action_incomplete:  # If not ignoring the user and no follow up intent
            skill = ai.get_action_depth(1)
            subskill = ai.get_action_depth(2)
            if skill == "wiki":
                await wiki.search(self.bot, message, ai, config)
            elif skill == "help":
                await info.info(self.bot, message, ai, config)
            elif skill == "role":
                if subskill == "set":
                    await roles.change_role(self.bot, message, ai, config)
                elif subskill == "list":
                    await roles.list_roles(self.bot, message, ai, config)
            elif skill == "status":
                await info.status(self.bot, message, ai, config)
            elif skill == "reddit":
                await self.reddit.send_image(message, ai, config)
            elif skill == "time":
                await time.get(self.bot, message, ai, config)
            elif skill == "moderation":
                if subskill == "kick":  # Needs to me reworked
                    await moderation.kick(self.bot, message, ai, config)
                elif subskill == "purge":
                    await moderation.purge(self.bot, message, ai, config)
            elif skill == "configuration":
                if subskill == "load":
                    await moderation.load_config(self.bot, message, ai, config)
                elif subskill == "view":
                    await moderation.view_config(self.bot, message, ai, config)
            else:
                await self.bot.safe_send_message(
                    message.channel,
                    "<:confusablob:341765305711722496> "
                    "Odd, you seem to have triggered a skill that isn't currently available."
                )
        else:
            await self.bot.safe_send_message(message.channel, ai.response)