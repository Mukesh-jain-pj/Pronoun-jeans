from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser, Address


class B2BTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email']           = user.email
        token['company_name']    = getattr(user, 'company_name', None)
        token['is_verified_b2b'] = getattr(user, 'is_verified_b2b', False)
        token['is_agent']        = getattr(user, 'is_agent', False)
        token['is_staff']        = user.is_staff
        # Include agent_code if agent profile exists
        try:
            token['agent_code'] = user.agent_profile.agent_code
        except Exception:
            token['agent_code'] = None
        return token


class UserSerializer(serializers.ModelSerializer):
    email           = serializers.EmailField(read_only=True)
    is_verified_b2b = serializers.BooleanField(read_only=True)

    class Meta:
        model  = CustomUser
        fields = ['id', 'email', 'company_name', 'gst_number', 'phone_number', 'is_verified_b2b']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = CustomUser
        fields = ['email', 'password', 'company_name', 'phone_number', 'gst_number']

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)


class AgentBuyerSerializer(serializers.ModelSerializer):
    """Serializes basic buyer details visible to an agent."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = CustomUser
        fields = [
            'id', 'email', 'full_name', 'company_name',
            'phone_number', 'gst_number', 'is_verified_b2b',
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Address
        fields = [
            'id', 'address_line_1', 'address_line_2', 'city', 'state',
            'pincode', 'is_default_shipping', 'is_default_billing',
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)