#coding: utf-8

import logging
import urllib2
from odesk import Client

from odesk import exceptions as odesk_exceptions
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from . import O_ACCESS_TOKEN

logger = logging.getLogger(__name__)


class DefaultClient(Client):
    "OAuth-enabled python-odesk Client with API tokens from Django settings"
    def __init__(self, access_token=None):
        try:
            key = settings.ODESK_OAUTH_KEY
            secret = settings.ODESK_OAUTH_SECRET
        except AttributeError:
            raise ImproperlyConfigured(
                "ODESK_OAUTH_KEY and/or ODESK_OAUTH_SECRET settings missing")
        super(DefaultClient, self).__init__(key, secret)
        if access_token:    
            self.oauth_access_token = access_token[0]
            self.oauth_access_token_secret = access_token[1]


def get_client(access_token=None):
    """Returns DefaultClient"""
    return DefaultClient(access_token)


def get_access_token_from(session=None):
    try:
        return session.get(O_ACCESS_TOKEN, None)
    except (AttributeError):
        return None


def get_client_from(request=None):
    try:
        access_token = get_access_token_from(session=request.session)
    except (AttributeError):
        access_token = None
    client = get_client(access_token)
    return client


def set_user_info(user, odesk_user):
    """Updates given ``user`` information (first and last name, email)
    based on ``odesk_user`` dictionary and saves the object.

    :param user: :class:`django.contrib.auth.models.User` instance
    :param odesk_user: a dictionary containing authenticated user information
                       received from oDesk HR API at /users/me
    """
    user.first_name = odesk_user['first_name']
    user.last_name = odesk_user['last_name']
    user.email = odesk_user['email']
    user.save()

    return user


def update_user_permissions(user, teams):
    """Updates given ``user`` permission-related attributes
    based on provided team list and project settings. Saves the object.

    :param user: :class:`django.contrib.auth.models.User` instance
    :param teams: names of oDesk teams that user belongs to
    """
    teams = set(teams)

    user.is_staff = any([
        teams.intersection(settings.ODESK_AUTH_ADMIN_TEAMS),
        user.username in settings.ODESK_AUTH_ADMINS,
    ])

    user.is_superuser = any([
        teams.intersection(settings.ODESK_AUTH_SUPERUSER_TEAMS),
        user.username in settings.ODESK_AUTH_SUPERUSERS,
    ])

    user.is_active = any([
        user.is_staff,
        user.is_superuser,
        user.username in settings.ODESK_AUTH_ALLOWED_USERS,
        teams.intersection(settings.ODESK_AUTH_ALLOWED_TEAMS),
    ])

    user.save()

    return user


def check_login(access_token):
    """Verifies that given OAuth ``access_token`` is valid, and user is active
    on oDesk. Makes a test request to oDesk API for that purpose.

    Returns a 2-tuple. If login is bad, it's ``False`` and a string with
    additional information. Otherwise it's ``(True, "OK")``.
    """
    odesk_client = get_client()
    (
        odesk_client.oauth_access_token,
        odesk_client.oauth_access_token_secret,
    ) = access_token

    try:
        auth_user_resp = odesk_client.hr.get_user('me')
    except odesk_exceptions.HTTP403ForbiddenError:
        return False, "Invalid access token"
    except (urllib2.HTTPError, urllib2.URLError):
        logger.exception("unexpected network error in check_login()")
        return False, "Network error"
    except ValueError as exc:
        logger.exception(exc)
        return False, "Value error"

    if auth_user_resp.get('status') != 'active':
        return False, "User is inactive"

    return True, "OK"
