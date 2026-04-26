from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from .models import Player
from .serializers import PlayerJoinSerializer, PlayerSerializer, PlayerJoinResponseSerializer
from .services import join_or_create_player
from apps.game.services import create_session


class PlayerJoinView(APIView):
    """
    POST /api/accounts/join
    Body: { "username": "taaransh" }
    Response: { "player": {...}, "session_token": "abc123..." }
    """
    
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Players'],
        request=PlayerJoinSerializer,
        responses=PlayerJoinResponseSerializer,
        description='Join or create a player account',
    )
    def post(self, request):
        serializer = PlayerJoinSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        username = serializer.validated_data['username']

        # get or create player + generate session token
        player, session_token = join_or_create_player(username)

        # save session to DB
        create_session(player=player, session_token=session_token)

        response_data = {
            'player':        PlayerSerializer(player).data,
            'session_token': session_token,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PlayerProfileView(APIView):
    """
    GET /api/accounts/player/<player_id>/
    Returns player profile and stats.
    """

    @extend_schema(
        tags=['Players'],
        responses=PlayerSerializer,
        description='Retrieve a specific player profile',
    )
    def get(self, request, player_id):
        try:
            player = Player.objects.get(id=player_id)
        except Player.DoesNotExist:
            return Response(
                {'error': 'Player not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            PlayerSerializer(player).data,
            status=status.HTTP_200_OK
        )


class LeaderboardView(APIView):
    """
    GET /api/accounts/leaderboard/
    Returns top 10 players by total_wins.
    """

    @extend_schema(
        tags=['Players'],
        responses=PlayerSerializer(many=True),
        description='Get top 10 players by wins',
    )
    def get(self, request):
        players = Player.objects.order_by('-total_wins', '-total_matches')[:10]
        return Response(
            PlayerSerializer(players, many=True).data,
            status=status.HTTP_200_OK
        )
