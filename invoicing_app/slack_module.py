import requests

SLACK_API_ENDPOINT_POST = 'https://slack.com/api/chat.postMessage'
# SLACK_API_TOKEN = 'xoxb-1169167404752-1169450015440-cdlKpRLrFH98ChgfLd8RtbZy'
# SLACK_API_CHANNEL = 'C014Z5CFCHW'
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
