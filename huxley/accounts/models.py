# Copyright (c) 2011-2014 Berkeley Model United Nations. All rights reserved.
# Use of this source code is governed by a BSD License (see LICENSE).

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from django.db import models

from huxley.accounts.constants import *
from huxley.accounts.exceptions import AuthenticationError
from huxley.core.models import *

import re

class User(AbstractUser):

    TYPE_ADVISOR = 1
    TYPE_CHAIR = 2
    USER_TYPE_CHOICES = ((TYPE_ADVISOR, 'Advisor'),
                         (TYPE_CHAIR, 'Chair'))

    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=TYPE_ADVISOR)
    school = models.OneToOneField(School, related_name='advisor', null=True)  # Advisors only.
    committee = models.ForeignKey(Committee, related_name='chair', null=True) # Chairs only.

    def is_advisor(self):
        return self.user_type == self.TYPE_ADVISOR

    def is_chair(self):
        return self.user_type == self.TYPE_CHAIR

    def default_path(self):
        if self.is_advisor():
            return reverse('advisors:welcome')
        elif self.is_chair():
            return reverse('chairs:attendance')

    @staticmethod
    def authenticate(username, password):
        '''Attempt to authenticate a user, given a username (or email) and
        password. Return the user or raise AuthenticationError.'''
        if not (username and password):
            raise AuthenticationError.missing_fields()

        user = authenticate(username=username, password=password)
        if user is None:
            try:
                u = User.objects.get(email=username)
                user = authenticate(username=u.username, password=password)
            except User.DoesNotExist:
                pass

        if user is None:
            raise AuthenticationError.invalid_credentials()
        if not user.is_active:
            raise AuthenticationError.inactive_account()

        return user

    @staticmethod
    def login(request, user):
        '''Log in a user and return a redirect url based on whether they're
        an advisor or chair.'''
        login(request, user)
        return user.default_path()

    @classmethod
    def reset_password(cls, username):
        '''Reset and return a user's password, or return False if the user
        doesn't exist.'''
        if not username:
            return False
        try:
            user = cls.objects.get(models.Q(username=username) |
                                   models.Q(email=username))
            new_password = cls.objects.make_random_password(length=10)
            user.set_password(new_password)
            user.save()
            return new_password
        except cls.DoesNotExist:
            return False

    def change_password(self, old, new1, new2):
        '''Attempt to change the given user's password. Return a 2-tuple
        of (bool) success, (str) error.'''
        if not (old and new1 and new2):
            return False, ChangePasswordErrors.MISSING_FIELDS
        if new1 != new2:
            return False, ChangePasswordErrors.MISMATCHED_PASSWORDS
        if len(new1) < 6:
            return False, ChangePasswordErrors.PASSWORD_TOO_SHORT
        if not re.match("^[A-Za-z0-9\_\.!@#\$%\^&\*\(\)~\-=\+`\?]+$", new1):
            return False, ChangePasswordErrors.INVALID_CHARACTERS
        if not self.check_password(old):
            return False, ChangePasswordErrors.INCORRECT_PASSWORD

        self.set_password(new1)
        self.save();
        return True, None

    class Meta:
        db_table = 'huxley_user'
        verbose_name = 'user'
