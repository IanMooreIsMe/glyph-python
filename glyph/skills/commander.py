import logging

_skills = {}

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)


class SkillCommander:

    __slots__ = ["skills"]

    def __init__(self):
        self.skills = {}

    @staticmethod
    async def process(message, ai, config):
        action = ai.get_action_depth(0)
        if "ignore" in str(ai.contexts) and not ai.get_action_depth(1) == "insult":  # If ignoring the user
            await message.reply("No {}, I'm done helping you for now.".format(message.author.mention))
        elif action == "fallback":
            reacted = await message.react("\u2753")
            if reacted is False:
                await message.reply(ai.response)
        elif action == "skill" and not ai.action_incomplete:  # If not ignoring the user and no follow up intent
            await message.client.messaging.send_typing(message)
            skill = ai.get_skill()
            try:
                message.ai = ai
                message.config = config
                await _skills[skill](message)
            except KeyError:
                await message.reply("<:confusablob:341765305711722496> Odd, you seem to have triggered `{}`, "
                                    "a skill that isn't currently available.".format(skill))
        else:
            await message.reply(ai.response)


def register(action):
    def dec(func):
        _skills.update({action: func})
        log.info("Registered {}".format(action))
    return dec
