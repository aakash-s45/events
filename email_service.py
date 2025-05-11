from fastapi.responses import JSONResponse
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from settings import (
    EMAIL_USER,
    EMAIL_PASS,
    EMAIL_FROM,
    EMAIL_PORT,
    EMAIL_SERVER,
)


def init_fastmail():
    """
    Initialize FastMail with the configuration.
    """
    conf = ConnectionConfig(
        MAIL_USERNAME=EMAIL_USER,
        MAIL_PASSWORD=EMAIL_PASS,
        MAIL_FROM=EMAIL_FROM,
        MAIL_PORT=EMAIL_PORT,
        MAIL_SERVER=EMAIL_SERVER,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
    )
    return FastMail(conf)

async def send_email(email: str, subject: str, body: str):
    """
    Send an email using FastMail.
    """
    fm:FastMail = init_fastmail()
    message = {
        "subject": subject,
        "recipients": [email],
        "body": body,
        "subtype": "html",
    }
    schema =  MessageSchema(
        **message,
    )
    response = await fm.send_message(schema)
    print(response)
    return JSONResponse(content={"message": "Message sent successfully"}, status_code=200)
    