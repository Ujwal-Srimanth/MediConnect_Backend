from azure.communication.email.aio import EmailClient
import os
from app.config import ACS_CONNECTION_STRING, SENDER_ADDRESS

async def send_email(recipient_email: str, subject: str, body: str):

    print(recipient_email)
    if not ACS_CONNECTION_STRING:
        raise ValueError("ACS_CONNECTION_STRING not set in environment variables")

    email_client = EmailClient.from_connection_string(ACS_CONNECTION_STRING)

    message = {
        "senderAddress": SENDER_ADDRESS,  # your ACS subdomain sender
        "recipients": {
            "to": [{"address": recipient_email}]
        },
        "content": {
            "subject": subject,
            "plainText": body,
            "html": f"<p>{body}</p>"
        }
    }
    try:
        poller = await email_client.begin_send(message)
        result = await poller.result()
        print(result)
    finally:
        await email_client.close() 

    return result
