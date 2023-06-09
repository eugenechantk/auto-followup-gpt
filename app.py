# import the required libraries
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os.path
import base64
import pprint
import email
from bs4 import BeautifulSoup
# from lxml import etree
import datetime
import json

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def lambda_handler(event, context):
    try:
        main()
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "hello everyone",
                # "location": ip.text.replace("\n", "")
            }),
        }
    except:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "error out",
                # "location": ip.text.replace("\n", "")
            }),
        }


def check_sender_of_last_thread(thread):
    if 'messages' in thread:
        last_message = thread['messages'][-1]
    if 'payload' in last_message:
        payload = last_message['payload']
        headers = payload['headers']
        for header in headers:
            if header['name'] == 'From':
                sender = header['value']
                return sender
    return None


def main():
    not_replied_emails()



def not_replied_emails():
    # Variable creds will store the user access token.
    # If no valid token found, we will create one.
    creds = None

    # The file token.pickle contains the user access token.
    # Check if it exists
    if os.path.exists('token.pickle'):

        # Read the token from the file and store it in the variable creds
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If credentials are not available or are invalid, ask the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'gmail_oath.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the access token in token.pickle file for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Connect to the Gmail API
    service = build('gmail', 'v1', credentials=creds)
    print('Connection Established')

    labels_results = service.users().labels().list(userId='me').execute()
    labels = labels_results.get('labels', [])

    # #store all ids with follow-up label
    follow_up_label_id = None
    for label in labels:
        if label['name'] == 'Follow-up':
            follow_up_label_id = label['id']
    # request a list of all the messages
    # We can also pass maxResults to get any number of emails. Like this:
    result = service.users().messages().list(
        maxResults=30, userId='me', labelIds=['SENT']).execute()
    messages = result.get('messages')

	# #store all ids with follow-up label
	follow_up_label_id = None
	for label in labels:
		if label['name'] == 'Follow-up':
			follow_up_label_id = label['id']
	# request a list of all the messages
	# We can also pass maxResults to get any number of emails. Like this:
	result = service.users().messages().list(maxResults=50, userId='me', labelIds=['SENT']).execute()
	messages = result.get('messages')

    # iterate through all the messages
    counter = 0
    for msg in messages:
        # Get the message from its id
        txt = service.users().messages().get(
            userId='me', id=msg['id']).execute()
        # print("txt['labelIds']", txt['labelIds'])
        if follow_up_label_id in txt['labelIds']:
            target_text = txt
            print("Target text", target_text)

	# iterate through all the messages
	thread_ids = set()
	for msg in messages:
		# Get the message from its id
		txt = service.users().messages().get(userId='me', id=msg['id']).execute()
		# print("txt['labelIds']", txt['labelIds'])
		if follow_up_label_id in txt['labelIds']:
			target_text = txt 
		
		
			#find the thread for this email
			thread_id = target_text['threadId']		
			thread = service.users().threads().get(userId='me', id=thread_id).execute()


			last_sender = check_sender_of_last_thread(thread)			
			
			#find the sent date
			internal_date = target_text['internalDate']
			sent_time = datetime.datetime.fromtimestamp(int(internal_date) / 1000).strftime('%Y-%m-%d %H:%M:%S')


			# Use try-except to avoid any Errors
			try:
				# Get value of 'payload' from dictionary 'target_text'
				payload = target_text['payload']
				headers = payload['headers']
		    
				# Look for Subject and Sender Email in the headers
				for d in headers:
					if d['name'] == 'Subject':
						subject = d['value']
					if d['name'] == 'From':
						sender = d['value']
				
				# check if the email is responded or not by seeing the last sender
				# and we haven't checked this thread yet 
				if (last_sender == sender) and (thread_id not in thread_ids):
					thread_ids.add(thread_id)
					

					# The Body of the message is in Encrypted format. So, we have to decode it.
					# Get the data and decode it with base 64 decoder.		
					parts = payload.get('parts')[0]		
					# non pure text
					if 'multipart' in parts['mimeType']:
						for part in parts['parts']:
							if part['mimeType'] == 'text/plain':
								data = part['body']['data']
					#pure text
					else: 
						data = parts['body']['data']
	

					data = data.replace("-","+").replace("_","/")				
					body = base64.b64decode(data).decode('utf-8')

	

					print("Subject: ", subject)
					print("From: ", sender)
					print("Date: ", sent_time)
					print("Body: ", body)
					print('\n')
			except:
				pass
	return subject, sender, sent_time, body


not_replied_emails()

if __name__ == "__main__":
    main()
