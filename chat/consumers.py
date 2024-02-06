from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from .serializers import UserSerializer, SearchSerializer, RequestSerializer
from django.db.models import Q, Exists, OuterRef
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

        elif data_source == 'request-list':
            self.receive_request_list(data)

        elif data_source == 'request-accept':
            self.receive_accept_request(data)

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
        ).annotate(
            pending_them=Exists(
                Connection.objects.filter(
                    sender=OuterRef('id'),
                    receiver=user,
                    accepted=False
                )
            ),
            pending_me=Exists(
                Connection.objects.filter(
                    sender=user,
                    receiver=OuterRef('id'),
                    accepted=False
                )
            ),
            connected=Exists(
                Connection.objects.filter(
                    Q(sender=OuterRef('id'), receiver=user) |
                    Q(sender=user, receiver=OuterRef('id')),
                    accepted=True
                )
            )
        ), many=True)

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

    def receive_request_list(self, data):
        user = self.scope['user']
        if not user.is_authenticated:
            return

        # Get the connection requests
        requests = Connection.objects.filter(receiver=user, accepted=False)

        # Serialize the connection requests
        serialized = RequestSerializer(requests, many=True)

        # Send the connection requests to the user
        self.send(text_data=json.dumps({
            'source': 'request-list',
            'data': serialized.data
        })
        )

    def receive_accept_request(self, data):
        user = self.scope['user']
        if not user.is_authenticated:
            return

        sender_username = data.get('username')

        try:
            sender = User.objects.get(username=sender_username)
        except User.DoesNotExist:
            return

        connection = Connection.objects.get(
            sender=sender, receiver=user, accepted=False)

        connection.accepted = True
        connection.save()

        serialized = RequestSerializer(connection)

        self.send_group(sender_username, 'request-accept', serialized.data)

        self.send_group(user.username, 'request-accept', serialized.data)

        self.send(text_data=json.dumps({
            'source': 'request-accept',
            'data': serialized.data
        }))
