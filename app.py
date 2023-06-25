# from lxml import etree
import json
from google.oauth2.credentials import Credentials
import requests
import os

# Import all the logic functions from logic.py
import logic
import auth

# sampleToken = {
#     "access_token": "ya29.a0AWY7CkmMcqHMuWrL4c9QrKQgIP_BWe6EknDNOHMeEeykWihlM9l33DSZRR-xfOsVCBkNVaO1W5IiWvU4-eAB5EhjcJcZ-L5S1EfjcaQqu2fyb8j8UTNCbrvm8hMEDrRigNCV67yQ8KszfVIZoUR0f1hmR7-UaCgYKAf4SARASFQG1tDrpmsmzmPOQo87m0QTpuKy3vQ0163",
#     "refresh_token": "1//06HPIF4-kKzWfCgYIARAAGAYSNwF-L9IrjE4Y5N7bZ7tLlPChb5Asil4ayeqbbLZRGPLrWdgOnMhS_6GGq97RVgslt2QT-ZceZjw",
#     "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
#     "token_type": "Bearer",
#     "expiry_date": 1687714450951
# }


def generate_follow_up_handler(event, context):
    oauth_client_id = os.environ['OAUTH_CLIENT_ID']
    oauth_client_secret = os.environ['OAUTH_CLIENT_SECRET']
    print('generate follow up lambda function invoked')
    # Parse the request body
    request_body = json.loads(event['body'])

    try:
        # Get the access token from the request
        accessToken = request_body['access_token']
        callbackUrl = request_body['callback_url']
        refreshToken = request_body['refresh_token']
        print(request_body)
        if accessToken is None:
            raise CustomError(400, 'NoCredentials', 'No access token provided')
        creds = Credentials(token=accessToken, refresh_token=refreshToken, client_id=oauth_client_id, client_secret=oauth_client_secret, token_uri='https://oauth2.googleapis.com/token')

        # creds = Credentials(token=sampleToken["access_token"], refresh_token=sampleToken["refresh_token"],
        #                     client_id=oauth_client_id, client_secret=oauth_client_secret, token_uri='https://oauth2.googleapis.com/token')

        # Get the user's email address
        email_address = auth.get_user_email(creds)

        print('get_user_email', email_address)

        email_fetch_json = logic.not_replied_emails(creds)

        print('not_replied_emails', email_fetch_json)
        if email_fetch_json == None:
            response = {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": 'No follow up emails',
                "isBase64Encoded": False
            }
            # Callback to Zapier to complete the async request
            try:
                callbackRes = requests.post(callbackUrl, params={
                                            "Content-Type": "application/json"}, data="No follow up emails")
                print('zapier callback', callbackRes)
                return response
            except Exception as e:
                print('zapier callback failed', e)
                raise CustomError(400, 'ZapierCallBackFail',
                                'Zapier Callback Failed')

        openai_json = logic.generate_reply(email_fetch_json)

        print('generate_reply', openai_json)

        email_list = logic.send_email_to_all(creds, openai_json, email_address)

        res_body = {'email_sent': email_list}
        print('send_email_to_all', email_list)
        # Return the request body in the response
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(res_body),
            "isBase64Encoded": False
        }
        print(response)

        # Callback to Zapier to complete the async request
        try:
            callbackRes = requests.post(callbackUrl, params={"Content-Type": "application/json"}, data=json.dumps(res_body))
            print('zapier callback', callbackRes)
            return response
        except Exception as e:
            print( 'zapier callback failed', e)
            raise CustomError(400, 'ZapierCallBackFail', 'Zapier Callback Failed')

    except Exception as e:
        print(e)
        response = {
            "statusCode": e.statusCode,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": e.code + ": " + e.message,
            "isBase64Encoded": False
        }
        print(response)
        return response


class CustomError(Exception):
    def __init__(self, status_code, code, message):
        self.status_code = status_code
        self.code = code
        self.message = message


# if __name__ == '__main__':
#     generate_follow_up_handler(None, None)
