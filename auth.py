from googleapiclient.discovery import build
import json
from google.oauth2.credentials import Credentials


# get user's email with the token
def get_user_email(creds):
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    email_address = profile['emailAddress']
    return email_address


def authentication_handler(event, context):
    print('authentication lambda function invoked')
    # print(event['headers']['Authorization'], type(event['headers']['Authorization']))
    # request_headers = json.loads(event['headers'])
    try:
        # Get the access token from the request
        accessToken = event['headers']['Authorization'].split(' ')[1]
        print(accessToken)
        if accessToken is None:
            raise CustomError(400, 'NoCredentials', 'No access token provided')

        creds = Credentials(token=accessToken)

        # Get the user's email address
        email_address = get_user_email(creds)

        body = {"user_email": email_address}
        # Return the request body in the response
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(body),
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
