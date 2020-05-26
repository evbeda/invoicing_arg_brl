import requests

channels = {
    '#invoicing_arg_brl': 'C014Z5CFCHW',
}


class SlackConnection():
    def __init__(self, token):
        self.slack_api_token = token

    def post_message(self, channel, message):
        data = {
            'token': self.slack_api_token,
            'channel': channels[channel],
            'text': message
        }
        response = requests.post(url=SLACK_API_ENDPOINT_POST, data=data)
