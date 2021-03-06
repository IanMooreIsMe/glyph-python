import json

import apiai


class AIProcessor(object):

    def __init__(self, client_access_token):
        self.apiai = apiai.ApiAI(client_access_token)

    def query(self, query, session_id):
        request = self.apiai.text_request()
        request.session_id = session_id
        request.query = query
        response = request.getresponse()
        data = response.read().decode("utf-8")
        return AIResponse(json.loads(data))


class AIResponse(object):

    def __init__(self, response):
        self.actions = response["result"]["action"].split(".")
        self.action_incomplete = bool(response["result"]["actionIncomplete"])
        self.parameters = response["result"]["parameters"]
        self.contexts = response["result"]["contexts"]
        self.response = response["result"]["fulfillment"]["speech"]

    def get_parameter(self, parameter, *, fallback=None):
        try:
            value = self.parameters[parameter]
            if value is "":
                raise KeyError
            return self.parameters[parameter]
        except KeyError:
            return fallback

    def get_action_depth(self, level):
        try:
            value = self.actions[level]
            return value
        except IndexError:
            return None

    def get_skill(self):
        skill = self.get_action_depth(1)
        subskill = self.get_action_depth(2)
        if subskill is not None:
            value = "{}.{}".format(skill, subskill)
        else:
            value = skill
        return value
