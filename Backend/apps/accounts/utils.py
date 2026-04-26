import jwt
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Player


def generate_jwt_token(player):
    """
    Generate JWT token for a player.
    """
    secret = getattr(settings, "JWT_SECRET", "your-jwt-secret-key")
    algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")
    expiration_hours = int(getattr(settings, "JWT_EXPIRATION_HOURS", 24))
    
    payload = {
        'player_id': player.id,
        'username': player.username,
        'exp': datetime.utcnow() + timedelta(hours=expiration_hours),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token


def decode_jwt_token(token):
    """
    Decode and verify JWT token.
    """
    secret = getattr(settings, "JWT_SECRET", "your-jwt-secret-key")
    algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")
    
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Token has expired')
    except jwt.InvalidTokenError:
        raise AuthenticationFailed('Invalid token')


class JWTAuthentication(BaseAuthentication):
    """
    JWT Authentication class for DRF.
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        try:
            prefix, token = auth_header.split()
            if prefix.lower() != 'bearer':
                raise AuthenticationFailed('Invalid token prefix')
        except ValueError:
            raise AuthenticationFailed('Invalid authorization header')
        
        payload = decode_jwt_token(token)
        player_id = payload.get('player_id')
        
        try:
            player = Player.objects.get(id=player_id)
        except Player.DoesNotExist:
            raise AuthenticationFailed('Player not found')
        
        return (player, None)
