from googleapiclient.discovery import build
import json
import base64
# from lxml import etree
from datetime import datetime, timedelta
import json
import pandas as pd
import openai
import re
import os
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from base64 import urlsafe_b64encode
from dotenv import load_dotenv


# FOR AWS
# openai.api_key = os.environ['OPENAI_KEY']
# FOR LOCAL
load_dotenv()
openai.api_key = os.getenv('OPENAI_KEY')





# find the follow up labels
def find_follow_up_label(service):

    labels_results = service.users().labels().list(userId='me').execute()
    labels = labels_results.get('labels', [])

    # #store all ids with follow-up label
    follow_up_label_id = None
    for label in labels:
        if label['name'] == 'Follow-up':
            follow_up_label_id = label['id']
    return follow_up_label_id


def find_all_messages(service):
    # request a list of all the messages
    # We can also pass maxResults to get any number of emails. Like this:
    result = service.users().messages().list(
        maxResults=50, userId='me', labelIds=['SENT']).execute()
    messages = result.get('messages')
    return messages


def get_thread_and_id(service, target_text):

    # find the thread for this email
    thread_id = target_text['threadId']
    thread = service.users().threads().get(userId='me', id=thread_id).execute()
    return thread, thread_id


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

# Look for Subject, Sender, and Receiver Email in the headers


def get_subject_sender_receiver_date(headers, target_text):

    for d in headers:
        if d['name'] == 'Subject':
            subject = d['value']
        if d['name'] == 'From':
            sender = d['value']
        if d['name'] == 'To' or d['name'] == 'Delivered-To':
            receiver = d['value']

    internal_date = target_text['internalDate']
    sent_time = datetime.fromtimestamp(
        int(internal_date) / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return subject, sender, receiver, sent_time


def get_body(payload):
    # The Body of the message is in Encrypted format. So, we have to decode it.
    # Get the data and decode it with base 64 decoder.

    parts = payload.get('parts')[0]
    # non pure text
    if 'multipart' in parts['mimeType']:
        for part in parts['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
    # pure text
    else:
        data = parts['body']['data']

    data = data.replace("-", "+").replace("_", "/")
    body = base64.b64decode(data).decode('utf-8')
    return body


def not_replied_emails(creds):
    # Connect to the Gmail API
    service = build('gmail', 'v1', credentials=creds)
    print('Connection Established')

    follow_up_label_id = find_follow_up_label(service)
    if follow_up_label_id is None:
        print("Follow-up label not found")
        return None

    # Get the list of messages
    messages = find_all_messages(service)
    # print(messages)

    # Get the current date and time
    current_time = datetime.now()

    # Output data storage
    df = pd.DataFrame(columns=['msgId', 'subject', 'thread_id',
                               'sender', 'receiver', 'sent_time', 'body'])
    # Iterate through all the messages
    thread_ids = set()

    for msg in messages:
        # Get the message from its id
        txt = service.users().messages().get(
            userId='me', id=msg['id']).execute()
        # print(txt)

        if follow_up_label_id in txt['labelIds']:
            target_text = txt
            thread, thread_id = get_thread_and_id(service, target_text)
            last_sender = check_sender_of_last_thread(thread)

            try:
                # Get value of 'payload' from dictionary 'target_text'
                payload = target_text['payload']
                headers = payload['headers']

                subject, sender, receiver, sent_time = get_subject_sender_receiver_date(
                    headers, target_text)

                # Check if the email is responded or not by seeing the last sender
                # and we haven't checked this thread yet
                if (last_sender == sender) and (thread_id not in thread_ids):
                    thread_ids.add(thread_id)

                    # Convert the sent_time to datetime object
                    sent_time = datetime.strptime(sent_time, '%Y-%m-%d %H:%M:%S')

                    # Calculate the time difference between the current time and sent_time
                    time_diff = current_time - sent_time

                    # Check if the email was sent within the last three days
                    if time_diff.days <= 3:
                        body = get_body(payload)

                        new_row = {'msgId': msg['id'], 'subject': subject, 'thread_id': thread_id, 'sender': sender,
                                   'receiver': receiver, 'sent_time': sent_time, 'body': body}
                        print(new_row['subject'], new_row['sent_time'])
                        df.loc[len(df)] = new_row
                        # df = df.append(new_row, ignore_index=True)

            except:
                pass

    # Save as a json data
    df_dict = df.to_dict(orient='records')
    df['sent_time'] = df['sent_time'].astype(str)
    json_data = json.dumps(df_dict)
    print(json_data)

    return json_data


# -- Help Functions for generating open ai reply -- #


def data_cleaning(json_str):
    # Convert the string to a DataFrame
    df = pd.read_json(json_str, orient='records')

    # filter dataframe that has been three days since the email was sent
    df['sent_time'] = pd.to_datetime(df['sent_time'])

    # Calculate threshold date (current date - 3 days)
    threshold_date = datetime.now().date() - timedelta(days=3)

    # Filter the dataframe based on the condition
    df = df[df['sent_time'].dt.date <= threshold_date]

    # Apply the function on the 'email_string' column
    df['receiver'] = df['receiver'].apply(extract_email)

    # Add an empty column to the dataframe
    df['reply'] = ''

    # Convert the 'sent_time' column back to string
    df['sent_time'] = df['sent_time'].astype(str)

    return df


def extract_email(string):
    # Define the regex pattern
    pattern = r'[\w\.-]+@[\w\.-]+'
    matches = re.findall(pattern, string)
    if matches:
        return matches[0]
    else:
        return ""


def openai_prompt_response(clean_body, receiver, subject):

    prompt = "I wrote this email: " + clean_body + "\n" + \
        "Can you write a follow-up email for this email I wrote? I don't need a subject, and the email should be less than 100 words, and every sentence should be complete. The email should include the phrase, follow up, in the email body."
    model = "text-davinci-003"
    response = openai.Completion.create(
        engine=model, prompt=prompt, max_tokens=100)

    generated_text = response.choices[0].text
    
    generated_formatted = "This is a reminder to send a follow-up email to " + receiver + ".\n" "The email you wrote previously has the subject of: " + subject + "\n\nHere is the drafted follow up for you 😉\n"+ generated_text

    return generated_formatted


# %%


def delete_old_thread(input_text):
    pattern = r'On [\w\s,]+ at [\d:\s]+[APM]+ [\w\s]+ <[\w.-]+@[\w.-]+>'
    match = re.search(pattern, input_text, re.IGNORECASE)
    if match:
        return input_text[:match.start()]
    else:
        return input_text

# -- Main Functions for generating open ai reply -- #
# %%


def generate_reply(json_str):
    df = data_cleaning(json_str)
    for index, row in df.iterrows():
        msgId = row['msgId']
        subject = row['subject']
        sender = row['sender']
        receiver = row['receiver']
        sent_time = row['sent_time']
        body = row['body']

        clean_body = delete_old_thread(body)

        response = openai_prompt_response(body, receiver, subject)

        df.loc[index, 'reply'] = response
    df['sent_time'] = df['sent_time'].astype(str)
    df_dict = df.to_dict(orient='records')
    openai_json = json.dumps(df_dict)

    return openai_json

# -- Helper Function for Sending Email -- #


def send_one_email(creds, sender, receiver, subject, message):
    service = build('gmail', 'v1', credentials=creds)
    # Create an email message
    email = MIMEText(message)
    email['to'] = receiver
    email['from'] = sender
    email['subject'] = subject

    # Encode the email content
    raw_email = urlsafe_b64encode(email.as_bytes()).decode('utf-8')

    # Send the email
    try:
        message = service.users().messages().send(
            userId='me', body={'raw': raw_email}).execute()
        print('One email sent successfully!')
        return message
    except HttpError as error:
        print('An error occurred while sending the email:', error)
        return None

# -- Main Function for Sending Email -- #


def send_email_to_all(creds, openai_json, email_address):
    df = pd.read_json(openai_json, orient='records')
    email_list = []

    for i in range(len(df)):
        sender = email_address  
        real_receiver = df['receiver'][i]
        receiver = email_address

        subject = '-- Follow up reminder -- ' + \
            df['subject'][i] + ' -- For ' + real_receiver + ' ---'
        print(subject)
        message = df['reply'][i]
        message = send_one_email(creds, sender, receiver, subject, message)
        email_list.append({'id': df['msgId'][i], 'message': message})

    return email_list