from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from .serializers import UserSerializer
import base64
import json


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            return

        # Save username to use as a group name for this user
        self.username = user.username

        # Join this user to a group with their username
        async_to_sync(self.channel_layer.group_add)(
            self.username,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave the group
        async_to_sync(self.channel_layer.group_discard)(
            self.username,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        print("receive", json.dumps(data, indent=2))

        data_source = data.get('source')

        if data_source == 'thumbnail':
            self.receive_thumbnail(data)

    def receive_thumbnail(self, data):
        user = self.scope['user']
        if not user.is_authenticated:
            return

        # Convert base64 data to image
        image_str = data.get('base64')
        image = ContentFile(base64.b64decode(image_str))

        # Save the image to the user's thumbnail field
        filename = data.get('filename')
        user.thumbnail.save(filename, image, save=True)

        # Serialize the user
        serialized = UserSerializer(user)

        # Send the thumbnail to the group
        self.send_group(user.username, 'thumbnail', serialized.data)

    def send_group(self, group, source, data):
        response = {
            'type': 'broadcast_group',
            'source': source,
            'data': data
        }
        async_to_sync(self.channel_layer.group_send)(
            group,
            response
        )

    def broadcast_group(self, event):
        source = event['source']
        data = event['data']
        self.send(text_data=json.dumps({
            'source': source,
            'data': data
        }))
