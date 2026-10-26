from rest_framework import serializers
from django.contrib.auth.models import User, Group
from .models import Store, Product, Review

'''
Serializers for use in API views to enable transmission of JSON data.
'''


class RegisterUserSerializer(serializers.ModelSerializer):
    '''
    Serializer for registration of users.

    Fields:
    - password: user entered password.
    - conf_pword: user confirms password entered.
    -role_id: choice for user (Vendor or Buyer).

    Meta:
    - model: User model.
    - fields: all required fields for the user to register.

    Meta Methods:
    - validate: Validates user data entered.
    - create: Creates user in database.
    '''
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

        # Check if passwords match.
        if data['password'] != data['conf_pword']:
            raise serializers.ValidationError({'password': 'Passwords mismatch'})

        # Check if group entered by user exists in database.
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
    '''
    Serializer for the retrieve reviews API view.

    Fields:
    - user: user requesting the reviews.
    - product: Access to the products database via product key.

    Meta:
    - model: Review model
    - fields: all fields required for reviews.
    - read_only_fields: These fields cannot be edited and will be presented
      as read_only data.
    '''
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
    '''
    Serializer to access and add product data.

    Fields:
    - vendor: Access to the stores database via vendor key.

    Meta:
    - model: Product model.
    - fields: all required fields for product model.
    - read_only_fields: These fields cannot be edited and will be presented
      as read_only data.
    '''

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
    '''
    Serializer to access and add store data.

    Fields:
    - products: Retrieve product data.
    - vendor_name: Retrieve the current vendor username.

    Meta:
    - model: Store model.
    - fields: all required fields for store model.
    - read_only_fields: These fields cannot be edited and will be presented
      as read_only data.
    '''
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
