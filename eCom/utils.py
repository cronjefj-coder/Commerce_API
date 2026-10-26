# eCom/utils.py
import secrets
from .models import ResetToken
from datetime import timedelta
from django.utils import timezone
from hashlib import sha1
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.template.loader import render_to_string


def gen_reset_url(user):
    '''
    This function generates a secure token and url to be used by users to reset
    their passwords. The token is stored in the ResetToken model linked to the
    user.

    Parameters:
    - user: The user requesting a reset identified via the email address
      provided.

    Returns:
    The function returns a url containing the secure token.
    '''

    domain = 'http://127.0.0.1:8000/'
    url = f'{domain}/reset/'
    token = str(secrets.token_urlsafe(16))
    expiry_date = timezone.now() + timedelta(minutes=10)
    reset_token = ResetToken.objects.create(
        user=user,
        token=sha1(token.encode()).hexdigest(),
        expiry_date=expiry_date
    )
    url += f'{token}/'

    return url


def build_email(user, reset_url):
    '''
    This function uses Django's built in EmailMessage() function to construct
    an email to the user containing the reset url.

    Parameters:
    - user: The user requesting a reset identified via the email address
      provided.
    - reset_url: The url containing the secure token.

    Returns:
    The function returns the generated email.
    '''

    user_email = user.email
    domain_email = 'admin@commerce.com'
    subject = 'Password Reset'
    body = (
        f'Hi {user.username},\n\nHere is the link to reset your password:\n'
        f'{reset_url}'
    )

    email = EmailMessage(subject, body, domain_email, [user_email])
    return email


def build_invoice_email(user, order):
    '''
    This function uses Django's built in render_to_string() and EmailMessage()
    functions to construct an email containing the invoice for the user after a
    successful order was placed from the cart during check out. An invoice.txt
    file is used as a template to create the invoice.

    Parameters:
    - user: The user logged into the current session checking out their cart.
    - order: The specific order containing the items for which the invoice is
      generated.

    Returns:
    The function returns an email containing the order invoice.
    '''

    user_email = user.email
    domain_email = 'admin@commerce.com'
    subject = f"Invoice for order {order.id}"
    context = {"order": order, "user": user}
    body = render_to_string("emails/invoices.txt", context)

    email = EmailMessage(subject, body, domain_email, [user_email])
    return email


def change_user_password(username, new_password):
    '''
    This function changes the user password when requested from the reset
    password link. It updates and saves the new password to the database.

    Parameters:
    - username: The username of the user requesting the change in password.
    - new_password: The new password provided from the reset password form by
      the user.

    Returns:
    The function does not return anything but updates and saves the password
    for the user to the database.
    '''

    user = User.objects.get(username=username)
    user.set_password(new_password)
    user.save()
