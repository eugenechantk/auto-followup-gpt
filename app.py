# from lxml import etree
import json
from google.oauth2.credentials import Credentials

# Import all the logic functions from logic.py
import logic
import auth

sampleEvent = {"body": '{"access_token": "ya29.a0AWY7CkmrRoU3MGKdbaH35elCpuN91iCJqzxkXupRpTw7b1-8F_MyIyL4HhN53Zq7JzcAMiCmsAnXcMZ8ZihEXP2ijMN1yr-Mj0JWyf1wBLlOGNIXo59xhprfUrR_RKISyHvjSMuahrjrjC2vFaqvpgRBB-vIaCgYKAe8SARASFQG1tDrp86C7y8lq2YaGIFd3pBGL2w0163","refresh_token": "1//062i6osRmCOpjCgYIARAAGAYSNwF-L9IrXdtc90NEwjBkNkiCwhc2m-xw_W0J10O0iz_5vwx8G5AbvuxAKq6t2P8PmLbK7Mv-nXY","scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send","token_type": "Bearer","expiry_date": 1686781603038}'}

def generate_follow_up_handler(event, context):
    print('generate follow up lambda function invoked')
    # Parse the request body
    request_body = json.loads(event['body'])

    try:
        # Get the access token from the request
        accessToken = request_body['access_token']
        if accessToken is None:
            raise CustomError(400, 'NoCredentials', 'No access token provided')
        creds = Credentials(token=accessToken)

        # Get the user's email address
        email_address = auth.get_user_email(creds)

        email_fetch_json = logic.not_replied_emails(creds)

        openai_json = logic.generate_reply(email_fetch_json)

        email_list = logic.send_email_to_all(creds, openai_json, email_address)

        res_body = {'email_sent': email_list}
        print(email_list)
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
        return response
    except Exception as e:
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

if __name__ == '__main__':
    generate_follow_up_handler(sampleEvent, None)