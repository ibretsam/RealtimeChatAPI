from rest_framework import serializers
from .models import User, Connection, Message


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password',
                  'first_name', 'last_name', 'email']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField('get_full_name')

    class Meta:
        model = User
        fields = ['id', 'username', 'email',
                  'thumbnail', 'name']

    def get_full_name(self, obj):
        return obj.get_full_name()


class SearchSerializer(UserSerializer):
    status = serializers.SerializerMethodField('get_status')

    class Meta:
        model = User
        fields = ['id', 'username',
                  'thumbnail', 'name', 'status']

    def get_status(self, obj):
        if (obj.pending_them):
            return 'pending-them'
        elif (obj.pending_me):
            return 'pending-me'
        elif (obj.connected):
            return 'connected'
        return 'not-connected'


class RequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer()
    receiver = UserSerializer()

    class Meta:
        model = Connection
        fields = ['id', 'sender', 'receiver',
                  'accepted', 'created_at', 'updated_at']
        read_only_fields = ['id', 'sender', 'receiver', 'accepted']


class FriendSerializer(serializers.ModelSerializer):
    friend = serializers.SerializerMethodField('get_friend')
    preview = serializers.SerializerMethodField('get_preview')
    updated_at = serializers.SerializerMethodField('get_updated_at')

    class Meta:
        model = Connection
        fields = ['id', 'friend', 'preview', 'updated_at']

    def get_friend(self, obj):
        if obj.sender == self.context['user']:
            return UserSerializer(obj.receiver).data
        return UserSerializer(obj.sender).data

    def get_preview(self, obj):
        # Get the last message, if no message return You are connected
        last_message = obj.messages.last()
        if last_message:
            return last_message.content
        return 'You are connected'

    def get_updated_at(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return last_message.created_at.isoformat()
        return obj.updated_at.isoformat()


class MessageSerializer(serializers.ModelSerializer):
    is_my_message = serializers.SerializerMethodField('get_is_my_message')

    class Meta:
        model = Message
        fields = ['id', 'sender', 'content',
                  'image_url', 'created_at', 'is_my_message']

    def get_is_my_message(self, obj):
        return obj.sender == self.context['user']
