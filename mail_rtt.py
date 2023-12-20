import boto3
import smtplib
import imaplib
import time
from datetime import datetime
import re


parameter_name = '/mail/rttslalom'
region_name = 'us-west-2'
# remove for production and use IAM roles within Lambda

# Initialize the SSM client
ssm = boto3.client('ssm', region_name=region_name, aws_access_key_id=aws_access_key_id,
                   aws_secret_access_key=aws_secret_access_key)

#define cloudwatch parameters at global scope
timestamp = int(time.time() * 1000)
cloudwatch_logs = boto3.client('logs')
log_group_name = 'email-round-trip-tests'
log_stream_name = 'email-round-trip-tests-postfix'

#get imap mailbox credentials from AWS Parameter store
def get_parameter(parameter_name, region_name, aws_access_key_id, aws_secret_access_key):
    try:
        ssm = boto3.client('ssm', region_name=region_name, aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key)
        response = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=True  # Decrypt the secret value
        )

        # Access the parameter value
        parameter_value = response['Parameter']['Value']
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

parameter_value = get_parameter(parameter_name, region_name, aws_access_key_id, aws_secret_access_key)

# Email configuration
sender_email = 
receiver_email = 
subject = "Round Trip Test"
body = "This is a test email from Python script."
smtp_server = 
smtp_port = 25

# Target RTT Mailbox IMAP settings
imap_server = "outlook.office365.com"
imap_port = 993
imap_username = "slalom.rtt@hotmail.com"
imap_password = parameter_value

def send_email(sender_email, receiver_email, subject, body, smtp_server, smtp_port):
    msg = f"Subject: {subject}\n\n{body}"

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.sendmail(sender_email, receiver_email, msg)


def check_email_arrival(imap_server, imap_username, imap_password, subject):
    mail = imaplib.IMAP4_SSL(imap_server)
    try:
        mail.login(imap_username, imap_password)
        mail.select("inbox")

        # Search for the email in the inbox
        result, data = mail.search(None, '(SUBJECT "{}")'.format(subject))

        if result == "OK" and data[0]:
            latest_email_id = data[0].split()[-1]

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

    send_email(sender_email, receiver_email, subject, body, smtp_server, smtp_port)
    time.sleep(15)

    email_arrival_time = check_email_arrival(imap_server, imap_username, imap_password, subject)

    if email_arrival_time:
        round_trip_time = email_arrival_time - start_time
        round_trip_time = abs(round(round_trip_time))
        if round_trip_time > 300:
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
