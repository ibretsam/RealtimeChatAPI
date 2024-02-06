from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from .serializers import UserSerializer, SearchSerializer, RequestSerializer
from django.db.models import Q
from .models import User, Connection
import base64
import json


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        user = self.scope['user']
        print("connect", user)
        if not user.is_authenticated:
            return

        # Save username to use as a group name for this user
        self.username = user.username
        print(f"{self.username} connected")

        # Join this user to a group with their username
        async_to_sync(self.channel_layer.group_add)(
            self.username,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        print("disconnect", close_code)
        # Leave the group
        async_to_sync(self.channel_layer.group_discard)(
            self.username,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        print("receive", json.dumps(data, indent=2))

        data_source = data.get('source')

        if data_source == 'search':
            self.receive_search(data)

        elif data_source == 'thumbnail':
            self.receive_thumbnail(data)

        elif data_source == 'request-connect':
            self.receive_request_connect(data)

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

    def receive_search(self, data):
        user = self.scope['user']
        if not user.is_authenticated:
            return

        # Get the search query
        query = data.get('query')

        # Get all users
        users = UserSerializer(User.objects.filter(
            Q(username__icontains=query) |
            # Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(
            username=user.username
        )            # .annotate(
            #     pending_them=Q(friends__from_user=user, friends__status='pending'),
            #     pending_me=Q(friends__to_user=user, friends__status='pending'),
            #     connected=Q(friends__from_user=user, friends__status='accepted')

            # )
            , many=True)

        # Send the search result to the user
        self.send(text_data=json.dumps({
            'source': 'search',
            'data': SearchSerializer(users.instance, many=True).data
        }))

    def receive_request_connect(self, data):
        user = self.scope['user']
        if not user.is_authenticated:
            return

        # Get the receiver's username
        receiver_username = data.get('username')
        try:
            receiver = User.objects.get(username=receiver_username)
        except User.DoesNotExist:
            return

        # Create a connection request
        connection, _ = Connection.objects.get_or_create(
            sender=user, receiver=receiver)

        # Serialize the connection request
        serialized = RequestSerializer(connection)

        #  Send back the connection request to the user
        self.send(text_data=json.dumps({
            'source': 'request-connect',
            'data': serialized.data
        }))

        # Send the connection request to the receiver
        self.send_group(receiver_username, 'request-connect', serialized.data)
