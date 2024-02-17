from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from .serializers import UserSerializer, SearchSerializer, RequestSerializer, FriendSerializer, MessageSerializer
from django.db.models import Q, Exists, OuterRef, Subquery
from .models import User, Connection, Message
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

        elif data_source == 'friend-list':
            self.receive_friend_list(data)

        elif data_source == 'message-send':
            self.receive_message_send(data)

        elif data_source == 'message-list':
            self.receive_message_list(data)

        elif data_source == 'message-typing':
            self.receive_message_typing(data)

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

        self.send_group(connection.receiver.username,
                        'request-accept', serialized.data)

        # Send the new friend to the sender
        serialized_friend = FriendSerializer(connection, context={
            'user': sender
        })

        self.send_group(sender_username, 'friend-new', serialized_friend.data)

        # Send the new friend to the receiver
        serialized_friend = FriendSerializer(connection, context={
            'user': connection.receiver
        })

        self.send_group(connection.receiver.username,
                        'friend-new', serialized_friend.data)

    def receive_friend_list(self, data):
        user = self.scope['user']
        if not user.is_authenticated:
            return
        
        last_message = Message.objects.filter(
            connection=OuterRef('id')
        ).order_by('-created_at')

        friends = Connection.objects.filter(
            Q(sender=user) | Q(receiver=user),
            accepted=True
        ).annotate(
            last_message_updated_at=Subquery(
                last_message.values('created_at')[:1]
            )
        ).order_by('-last_message_updated_at')

        serialized = FriendSerializer(
            friends, context={'user': user}, many=True)

        self.send_group(user.username, 'friend-list', serialized.data)

    def receive_message_send(self, data):
        user = self.scope['user']
        if not user.is_authenticated:
            return

        sender_id = data.get('senderId')

        sender = User.objects.get(id=sender_id)
        print("sender", sender.username)

        connection_id = data.get('connectionId')

        try:
            connection = Connection.objects.get(id=connection_id)
        except Connection.DoesNotExist:
            print("Connection does not exist")
            return

        content = data.get('message')
        print("content", content)

        message = Message.objects.create(
            connection=connection,
            sender=sender,
            content=content
        )

        serialized_message = MessageSerializer(message, context={
            'user': sender
        })

        serialized_user = UserSerializer(sender)

        # Send the message to the receiver
        receiver = connection.sender
        if user == connection.sender:
            receiver = connection.receiver

        serialized_friend = UserSerializer(receiver)
        serialized_message_receiver = MessageSerializer(message, context={
            'user': receiver
        })

        data = {
            'messages': serialized_message_receiver.data,
            'user': serialized_user.data
        }

        data_receiver = {
            'messages': serialized_message.data,
            'user': serialized_friend.data
        }

        self.send_group(user.username, 'message-send',
                        data_receiver)

        self.send_group(receiver.username, 'message-send',
                        data)

    def receive_message_list(self, data):
        user = self.scope['user']
        if not user.is_authenticated:
            return

        connection_id = data.get('connectionId')
        page = data.get('page')
        PAGE_SIZE = 10

        try:
            connection = Connection.objects.get(id=connection_id)
        except Connection.DoesNotExist:
            print("Connection does not exist")
            return

        messages = Message.objects.filter(
            connection=connection).order_by('-created_at')[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

        serialized = MessageSerializer(messages, context={
            'user': user
        }, many=True)

        serialized_user = UserSerializer(user)

        messages_count = Message.objects.filter(connection=connection).count()

        next_page = page + 1 if messages_count > (page + 1) * PAGE_SIZE else 0

        data = {
            'messages': serialized.data,
            'next': next_page,
            'user': serialized_user.data
        }

        # Send the messages to the user
        self.send_group(user.username, 'message-list', data)

    def receive_message_typing(self, data):
        user = self.scope['user']
        if not user.is_authenticated:
            return

        username = data.get('username')

        self.send_group(username, 'message-typing', {
            'username': user.username
        })
