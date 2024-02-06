from rest_framework import serializers
from .models import User, Connection


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
        fields = ['id', 'sender', 'receiver', 'accepted']
        read_only_fields = ['id', 'sender', 'receiver', 'accepted']
