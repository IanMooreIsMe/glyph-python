import logging

_skills = {}

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)


class SkillCommander(object):

    def __init__(self, bot):
        self.bot = bot
        # self.reddit = reddit.RedditSkill(bot)
        self.skills = {}

    async def process(self, message, ai, config):
        action = ai.get_action_depth(0)
        if "ignore" in str(ai.contexts) and not ai.get_action_depth(1) == "insult":  # If ignoring the user
            await self.bot.safe_send_message(message.channel,
                                             "No {}, I'm done helping you for now.".format(message.author.mention))
        elif action == "skill" and not ai.action_incomplete:  # If not ignoring the user and no follow up intent
            skill = ai.get_skill()
            try:
                await _skills[skill](self.bot, message, ai, config)
            except KeyError:
                await self.bot.safe_send_message(
                    message.channel,
                    "<:confusablob:341765305711722496> "
                    "Odd, you seem to have triggered `{}`, a skill that isn't currently available.".format(skill))
        else:
            await self.bot.safe_send_message(message.channel, ai.response)


def register(action):
    def dec(func):
        _skills.update({action: func})
        log.info("Registered {}".format(action))
    return dec
