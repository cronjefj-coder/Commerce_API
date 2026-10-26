from rest_framework import serializers
from django.contrib.auth.models import User, Group
from .models import Store, Product, Review


class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    conf_pword = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    role_id = serializers.ChoiceField(
        choices=['Vendor', 'Buyer'],
        write_only=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'conf_pword', 'role_id']

    def validate(self, data):
        if data['password'] != data['conf_pword']:
            raise serializers.ValidationError({'password': 'Passwords mismatch'})

        if not Group.objects.filter(name=data['role_id']).exists():
            raise serializers.ValidationError({'role_id': 'Group does not exist.'})

        return data

    def create(self, validated_data):
        validated_data.pop('conf_pword')
        role_id = validated_data.pop('role_id')

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        current_group = Group.objects.get(name=role_id)
        user.groups.add(current_group)

        return user


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    product = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'user',
            'product',
            'title',
            'comments',
            'rating',
            'is_verified',
            'created_on',
        ]

        read_only_fields = [
            'id',
            'user',
            'product',
            'is_verified',
            'created_on'
        ]


class ProductSerializer(serializers.ModelSerializer):

    vendor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'quantity',
            'price',
            'vendor',
        ]
        read_only_fields = ['id', 'vendor',]


class StoreSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    vendor_name = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Store
        fields = [
            'id',
            'name',
            'description',
            'user',
            'vendor_name',
            'products',
        ]
        read_only_fields = [
            'id',
            'user',
            'vendor_name',
            'products'
        ]
