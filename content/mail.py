from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from typing import List, Dict


def _send_email(
    recipients: List,
    subject="",
    body_text="",
    body_html="",
    attachment=None,
    attachment_mime_type=None,
    quiet=True,
):
    """
    Sends email to recipient.
    """

    body_html = body_html or f"<p>{body_text}</p>"
    print("from", settings.AUTO_MAIL_FROM)

    email = EmailMultiAlternatives(
        subject=subject,
        body=f"{body_text}\n",
        from_email=settings.AUTO_MAIL_FROM,
        to=recipients,
        alternatives=[(body_html, "text/html")],
        # attachments=attachments,
    )
    if attachment:
        email.attach_file(attachment, mimetype=attachment_mime_type)

    email.send(fail_silently=quiet)
    return email


def send_email(*args, **kwargs):
    _send_email(*args, **kwargs)
