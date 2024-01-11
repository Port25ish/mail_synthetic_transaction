Have your email servers failed and customers are the notification method? Were they load balanced, had a layer 4 health check, but failed at layer 7? Send emails through it constantly to verify they are working. <BR>

DO NOT USE IAM KEYS in production code. If you do this, someone will own you, and you will deserve it. Use AWS Parameter store, or IAM roles within Lambda depending on use case. <BR>
This script is currently under development. The purpose of sharing is the root code, that does work. <BR>

This is a simple python script that does the following for any mail host you would like to monitor: <BR>
Target mail host and send an email through it. <BR>
Sends email to an external email endpoint. <BR>
Email endpoint needs to be an outlook.com / hotmail.com email address. <BR>
Uses IMAP library to check the email after a configurable time period. <BR>
Calculates the time difference between sending the message and outlook.com recieving the message. <BR>
Posts the integer in seconds to AWS Cloud Watch Logs. <BR>
Uses a .yaml file for configuration. <BR>

Then set a Cloud Watch alarm on whatever # of seconds you are comfortable with for your infrastructure

