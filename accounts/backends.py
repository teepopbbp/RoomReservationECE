import requests
from django.conf import settings
from django.contrib.auth.backends import BaseBackend

from .models import CustomUser


class TURESTAPIBackend(BaseBackend):
    TU_API_URL = 'https://restapi.tu.ac.th/api/v1/auth/Ad/verify'

    def authenticate(self, request, username=None, password=None):
        if not username or not password:
            return None

        # Local password auth (superusers created via createsuperuser)
        try:
            user = CustomUser.objects.get(username=username)
            if user.has_usable_password() and user.check_password(password):
                return user
        except CustomUser.DoesNotExist:
            pass

        api_key = settings.TU_API_KEY
        if not api_key:
            # Fallback for development: allow any login when no API key is set
            user, _ = CustomUser.objects.get_or_create(
                username=username,
                defaults={'full_name': username, 'email': f'{username}@tu.ac.th'},
            )
            return user

        try:
            response = requests.post(
                self.TU_API_URL,
                json={'UserName': username, 'PassWord': password},
                headers={
                    'Content-Type': 'application/json',
                    'Application-Key': api_key,
                },
                timeout=10,
            )
            data = response.json()
        except Exception:
            return None

        if not data.get('status'):
            return None

        user, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                'email': data.get('email', f'{username}@tu.ac.th'),
                'full_name': data.get('displayname', username),
            },
        )
        if not created:
            changed = False
            if data.get('email') and user.email != data['email']:
                user.email = data['email']
                changed = True
            if data.get('displayname') and user.full_name != data['displayname']:
                user.full_name = data['displayname']
                changed = True
            if changed:
                user.save()

        return user

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
