from rest_framework import serializers
from .models import User


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
        return 'not-connected'
