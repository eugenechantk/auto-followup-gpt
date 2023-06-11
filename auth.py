from googleapiclient.discovery import build

# get user's email with the token
def get_user_email(creds):
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    email_address = profile['emailAddress']
    return email_address