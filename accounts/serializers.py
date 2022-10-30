from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from hvac.exceptions import InvalidRequest

from .models import AuthUser
from infections.models import Contacttracers
from .utils import validate_email as email_is_valid
from .vault import create_vault_client
from .vault.totp import TOTP


class RegistrationSerializer(serializers.ModelSerializer[AuthUser]):
    """Serializers registration requests and creates a new user."""
    id =  serializers.UUIDField(read_only=True)
    password = serializers.CharField(max_length=128, min_length=8, write_only=True)

    class Meta:
        model = AuthUser
        fields = [
            'id',
            'username',
            'password',
            'email',
            'phone_number'
        ]

    def validate_email(self, value: str) -> str:
        """Normalize and validate email address."""
        valid, error_text = email_is_valid(value)
        if not valid:
            raise serializers.ValidationError(error_text)
        try:
            email_name, domain_part = value.strip().rsplit('@', 1)
        except ValueError:
            pass
        else:
            value = '@'.join([email_name, domain_part.lower()])

        return value

    def validate_password(self, value: str) -> str:
        """Validate password."""
        validate_password(value)
        return value

    def create(self, validated_data):  # type: ignore
        """Return user after creation."""
        user = AuthUser.objects.create_user(
            username=validated_data['username'], email=validated_data['email'], password=validated_data['password']
        )
        user.phone_number = validated_data.get('phone_number', '')
        user.save(update_fields=['phone_number'])
        return user


class LoginSerializer(serializers.ModelSerializer[AuthUser]):
    """Serializers login requests and returns a user."""
    id = serializers.UUIDField(read_only=True)  
    username = serializers.CharField(max_length=255)
    email = serializers.CharField(max_length=255, read_only=True)
    has_otp = serializers.BooleanField(read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)

    tokens = serializers.SerializerMethodField()

    def get_tokens(self, obj):  # type: ignore
        """Get user token."""
        user = AuthUser.objects.get(username=obj.username)

        return {'refresh': 'unused', 'access': user.tokens['access']}

    class Meta:
        model = AuthUser
        fields = ['id','username', 'email', 'has_otp', 'password', 'tokens']

    def validate(self, data):  # type: ignore
        """Validate and return user login."""
        username = data.get('username', None)
        password = data.get('password', None)
        if username is None:
            raise serializers.ValidationError('A username is required to log in.')

        if password is None:
            raise serializers.ValidationError('A password is required to log in.')

        user = authenticate(username=username, password=password)

        if user is None:
            raise serializers.ValidationError('A user with this username and password was not found.')

        if not user.is_active:
            raise serializers.ValidationError('This user is not currently activated.')

        return user


class UserSerializer(serializers.ModelSerializer[AuthUser]):
    """Handle serialization and deserialization of User objects."""

    password = serializers.CharField(max_length=128, min_length=8, write_only=True)

    class Meta:
        model = AuthUser
        fields = (
            'username',
            'email',
            'password',
            'phone_number',
            'has_otp'
        )
        read_only_fields = ('has_otp',)

    def update(self, instance, validated_data):  # type: ignore
        """Perform an update on a User."""

        password = validated_data.pop('password', None)

        for (key, value) in validated_data.items():
            setattr(instance, key, value)

        if password is not None:
            validate_password(password, user=instance)
            instance.set_password(password)

        instance.save()

        return instance


class LogoutSerializer(serializers.Serializer[AuthUser]):
    refresh = serializers.CharField()

    def validate(self, attrs):  # type: ignore
        """Validate token."""
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):  # type: ignore
        """Validate save backlisted token."""

        try:
            RefreshToken(self.token).blacklist()

        except TokenError as ex:
            raise exceptions.AuthenticationFailed(ex)


class RegisterTOTPSerializer(serializers.ModelSerializer[AuthUser]):
    has_otp = serializers.BooleanField()

    class Meta:
        model = AuthUser
        fields = ['has_otp']
    
    def validate(self, attrs):
        if self.context['request'].user.has_otp:
            raise AuthenticationFailed('A TOTP device is already registered.', code='totp_device_registered')
        self.has_otp = attrs['has_otp']
        return attrs

    def update(self, instance, validated_data):
        # print(validated_data)
        instance.has_otp = validated_data.get('has_otp', False)
        instance.save()
        return instance


class ValidateTOTPSerializer(serializers.Serializer):
    refresh = serializers.CharField(read_only=True)
    access = serializers.CharField(read_only=True)
    totp = serializers.RegexField(regex=r'^\d{6}$', write_only=True)

    @classmethod
    def get_token(cls, user):
        tk = RefreshToken.for_user(user)
        tk['verified_otp'] = True
        return {
            'refresh': str(tk),
            'access': str(tk.access_token),
        }
    
    def validate(self, attrs):
        totp = attrs.get('totp', None)
        # Check if user has keyed a token
        if totp is None:
            raise AuthenticationFailed('The "totp" field is missing.', code='no_totp')
        
        # Check if the user has registered a TOTP device
        if not self.context['request'].user.has_otp:
            raise AuthenticationFailed('A TOTP device needs to be registered first.', code='no_totp_device')

        # Connect to Vault and verify TOTP value
        vault = create_vault_client()
        totp_vault = TOTP(vault)
        try:
            res = totp_vault.validate_code(name=self.context['request'].user.id, code=totp)
            if 'data' not in res or 'valid' not in res['data'] or not res['data']['valid']:
                raise AuthenticationFailed('Invalid TOTP provided.', code='invalid_totp')
        except InvalidRequest as e:
            print(e)
            raise AuthenticationFailed('An unexpected error occurred', code='totp_login_failed')
        
        return self.get_token(self.context['request'].user)
