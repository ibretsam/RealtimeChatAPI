from django.contrib.auth.models import AbstractUser
from django.db import models


def upload_thumbnail(instance, filename):    
    path = f'staticfiles/thumbnails/{instance.username}'
    extension = filename.split('.')[-1]
    if extension:
        path = f'{path}.{extension}'
    return path


class User(AbstractUser):
    thumbnail = models.TextField(default='staticfiles/thumbnails/default.png')


class Connection(models.Model):
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sender')
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='receiver')
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.sender} -> {self.receiver}'


class Message(models.Model):
    connection = models.ForeignKey(
        Connection, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(
        User, related_name='my_messages', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.sender} -> ({self.connection.sender} & {self.connection.receiver}): {self.content}'
