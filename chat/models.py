from django.contrib.auth.models import AbstractUser
from django.db import models


def upload_thumbnail(instance, filename):
    path = f'thumbnails/{instance.user.username}'
    extension = filename.split('.')[-1]
    if extension:
        path = f'{path}.{extension}'
    return path


class User(AbstractUser):
    thumbnail = models.ImageField(
        upload_to=upload_thumbnail, blank=True, null=True)
