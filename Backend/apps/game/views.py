from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

from .models import Match, Round
from .serializers import MatchSerializer, MatchHistorySerializer, RoundSerializer
from .services import get_match_scores, check_match_over


class MatchDetailView(APIView):
    """
    GET /api/game/match/<match_id>/
    Returns full match details including both players and scores.
    """

    @extend_schema(
        tags=['Matches'],
        responses=MatchSerializer,
        description='Get detailed information about a specific match',
    )
    def get(self, request, match_id):
        try:
            match = Match.objects.select_related(
                'player1', 'player2', 'winner'
            ).get(id=match_id)
        except Match.DoesNotExist:
            return Response(
                {'error': 'Match not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            MatchSerializer(match).data,
            status=status.HTTP_200_OK
        )


class MatchHistoryView(APIView):
    """
    GET /api/game/match/history/<player_id>/
    Returns all completed matches for a player.
    """

    @extend_schema(
        tags=['Matches'],
        responses=MatchHistorySerializer(many=True),
        description='Get completed match history for a player',
    )
    def get(self, request, player_id):
        matches = Match.objects.select_related(
            'player1', 'player2', 'winner'
        ).filter(
            status=Match.Status.COMPLETED
        ).filter(
            player1_id=player_id
        ) | Match.objects.select_related(
            'player1', 'player2', 'winner'
        ).filter(
            status=Match.Status.COMPLETED
        ).filter(
            player2_id=player_id
        ).order_by('-created_at')

        if not matches.exists():
            return Response(
                {'message': 'No matches found for this player.'},
                status=status.HTTP_200_OK
            )

        return Response(
            MatchHistorySerializer(matches, many=True).data,
            status=status.HTTP_200_OK
        )


class MatchRoundsView(APIView):
    """
    GET /api/game/match/<match_id>/rounds/
    Returns all rounds for a match.
    """

    @extend_schema(
        tags=['Rounds'],
        responses=RoundSerializer(many=True),
        description='Get all rounds for a specific match',
    )
    def get(self, request, match_id):
        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            return Response(
                {'error': 'Match not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        rounds = Round.objects.select_related(
            'winner'
        ).filter(match=match).order_by('round_number')

        return Response(
            RoundSerializer(rounds, many=True).data,
            status=status.HTTP_200_OK
        )


class ActiveMatchView(APIView):
    """
    GET /api/game/match/active/<player_id>/
    Returns the current ongoing match for a player if any.
    Used on reconnect to check if player has an active match.
    """

    @extend_schema(
        tags=['Matches'],
        responses=MatchSerializer,
        description='Get the current active match for a player (for reconnection)',
    )
    def get(self, request, player_id):
        match = Match.objects.select_related(
            'player1', 'player2'
        ).filter(
            status=Match.Status.ONGOING
        ).filter(
            player1_id=player_id
        ).first() or Match.objects.select_related(
            'player1', 'player2'
        ).filter(
            status=Match.Status.ONGOING,
            player2_id=player_id
        ).first()

        if not match:
            return Response(
                {'message': 'No active match found.'},
                status=status.HTTP_200_OK
            )

        return Response(
            MatchSerializer(match).data,
            status=status.HTTP_200_OK
        )