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
        self.action = response["result"]["action"].split(".")
        self.parameters = response["result"]["parameters"]
        self.response = response["result"]["fulfillment"]["speech"]

