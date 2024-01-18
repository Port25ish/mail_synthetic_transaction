import boto3
import smtplib
import imaplib
import time
from datetime import datetime
import re
import asyncio
import yaml

# remove keys for production and use IAM roles within Lambda
aws_access_key_id = 
aws_secret_access_key = 

#Configs will be Lambda environment variables in production
with open('C:/Users/paul.ross/OneDrive - Slalom/Code/mailConfig.yaml', 'r') as file:
    config = yaml.safe_load(file)

parameter_name = config['parameter_name']
region_name = config['region_name']
sender_email = config['sender_email']
receiver_email = config['receiver_email']
subject = config['subject']
body = config['body']
smtp_server = config['smtp_server']
smtp_port = config['smtp_port']
imap_server = config['imap_server']
imap_port = config['imap_port']
imap_username = config['imap_username']
timestamp = int(time.time() * 1000)
cloudwatch_logs = boto3.client('logs')
log_group_name = config['log_group_name']
log_stream_name = config['log_stream_name']


ssm = boto3.client('ssm', region_name=region_name, aws_access_key_id=aws_access_key_id,
                   aws_secret_access_key=aws_secret_access_key)


def get_parameter(parameter_name, region_name, aws_access_key_id, aws_secret_access_key):
    try:
        ssm = boto3.client('ssm', region_name=region_name, aws_access_key_id=aws_access_key_id,
                           aws_secret_access_key=aws_secret_access_key)
        response = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=True  
        )
        
        parameter_value = response['Parameter']['Value']
        if parameter_value is not None:
            return parameter_value

    except Exception as e:
        log_message = f"Error: {e}"
        response = cloudwatch_logs.put_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            logEvents=[
                {
                    'timestamp': timestamp,
                    'message': log_message
                }
            ]
        )
        return None


parameter_value = get_parameter(
    parameter_name, region_name, aws_access_key_id, aws_secret_access_key)

imap_password = parameter_value

async def send_email(sender_email, receiver_email, subject, body, smtp_server, smtp_port):
    msg = f"Subject: {subject}\n\n{body}"

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.sendmail(sender_email, receiver_email, msg)

    await asyncio.sleep(15)

#This section defines asynchronous methods. Place all async code here.
async def main():
    await send_email(sender_email, receiver_email, subject, body, smtp_server, smtp_port)


def check_email_arrival(imap_server, imap_username, imap_password, subject):
    mail = imaplib.IMAP4_SSL(imap_server)
    try:
        mail.login(imap_username, imap_password)
        mail.select("inbox")
        result, data = mail.search(None, '(SUBJECT "{}")'.format(subject))
        if result == 'OK':
            message_numbers = data[0].split()
            if message_numbers:
                latest_email_id = message_numbers[-1]
                print("Found latest email with ID: {}".format(latest_email_id))
            else: 
                print("No matching emails found.")
        else:
            print("Search failed with result: {}".format(result))
       
# Fetch the RFC822 and INTERNALDATE of the mail. INTERNALDATE is the IMAP property for when the mail was received. RFC822 creates standards for email formatting
        result, msg_data = mail.fetch(
            latest_email_id, "(RFC822 INTERNALDATE)")

        if result == "OK" and msg_data and isinstance(msg_data[0][1], bytes):

            internal_date_match = re.search(
                r'Date: (.*?)\r\n', msg_data[0][1].decode("utf-8"), re.DOTALL)

            if internal_date_match:
                internal_date_str = internal_date_match.group(1)
                # Parse the internal date and convert to timestamp
                internal_date_format = '%a, %d %b %Y %H:%M:%S %z'
                internal_date = datetime.strptime(
                    internal_date_str, internal_date_format)
                email_arrival_time = internal_date.timestamp()
                return email_arrival_time

    except Exception as e:
        log_message = f"Error: {e}"
        response = cloudwatch_logs.put_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            logEvents=[
                {
                    'timestamp': timestamp,
                    'message': log_message
                }
            ]
        )

    finally:
        mail.close()

    return None


if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())

    email_arrival_time = check_email_arrival(
        imap_server, imap_username, imap_password, subject)

    if email_arrival_time:
        round_trip_counter = 300
        round_trip_time = email_arrival_time - start_time
        round_trip_time = abs(round(round_trip_time))
        if round_trip_time > round_trip_counter:
            log_message = f"Error: round trip time of {
                str(round_trip_time)} seconds is greater than 6 minutes"
        else:
            log_message = str(round_trip_time)
            response = cloudwatch_logs.put_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                logEvents=[
                    {
                        'timestamp': timestamp,
                        'message': log_message
                    }
                ]
            )
