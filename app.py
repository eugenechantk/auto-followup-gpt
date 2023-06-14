# from lxml import etree
import json
from google.oauth2.credentials import Credentials

# Import all the logic functions from logic.py
import logic
import auth

sampleEvent = {"body": '{"access_token": "ya29.a0AWY7CknKms_QBpuf_UAXuc1HhaWZcW1E-TNPkdl_TpV1Pav7I1yi2KVgxSC2Rn07TSN3z8iVrOf5oyQIAOYYUZvVZtal5Gk-qto0sM3ZnNWJPObr-3lwNSNRNdvdiBG50G371boTCncD_SDNGqYNNBpVP1JxaCgYKAbUSARASFQG1tDrpiyRNI1Fp6rtuL4WF2GS66A0163","refresh_token":"1//06VU5XzyWbgVsCgYIARAAGAYSNwF-L9IregXbSaflPHvp4aiC4scPV_QmBsshIJ8m3T8LLZMKWC214VwBoaedv33OXOWtJpttNdU","scope": "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly","token_type": "Bearer","expiry_date": 1686786408090}'}


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
