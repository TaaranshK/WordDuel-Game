from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

from .models import Dictionary
from .serializers import DictionarySerializer, WordCreateSerializer
from .services import get_random_word, get_word_count


class WordListView(APIView):
    """
    GET /api/dictionary/words/
    Returns all active words. Admin use only.
    Supports filtering by difficulty and word_length.
    """

    @extend_schema(
        tags=['Dictionary'],
        responses=DictionarySerializer(many=True),
        description='Get all active dictionary words (filterable by difficulty and length)',
    )
    def get(self, request):
        difficulty = request.query_params.get('difficulty', None)
        length     = request.query_params.get('length', None)

        queryset = Dictionary.objects.filter(is_active=True)

        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        if length is not None:
            try:
                length_int = int(length)
            except (TypeError, ValueError):
                return Response(
                    {"error": "length must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(word_length=length_int)

        return Response(
            DictionarySerializer(queryset, many=True).data,
            status=status.HTTP_200_OK
        )


class WordCreateView(APIView):
    """
    POST /api/dictionary/words/add/
    Add a single word to the dictionary.
    """

    @extend_schema(
        tags=['Dictionary'],
        request=WordCreateSerializer,
        responses=DictionarySerializer,
        description='Add a new word to the dictionary',
    )
    def post(self, request):
        serializer = WordCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        word = serializer.save()

        return Response(
            DictionarySerializer(word).data,
            status=status.HTTP_201_CREATED
        )


class WordToggleView(APIView):
    """
    PATCH /api/dictionary/words/<word_id>/toggle/
    Toggle is_active for a word.
    """

    @extend_schema(
        tags=['Dictionary'],
        responses=DictionarySerializer,
        description='Toggle word active status',
    )
    def patch(self, request, word_id):
        try:
            word = Dictionary.objects.get(id=word_id)
        except Dictionary.DoesNotExist:
            return Response(
                {'error': 'Word not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        word.is_active = not word.is_active
        word.save(update_fields=['is_active'])

        return Response(
            DictionarySerializer(word).data,
            status=status.HTTP_200_OK
        )


class DictionaryStatsView(APIView):
    """
    GET /api/dictionary/stats/
    Returns word count breakdown by difficulty.
    """

    @extend_schema(
        tags=['Dictionary'],
        responses={
            'total_active': int,
            'easy': int,
            'medium': int,
            'hard': int,
        },
        description='Get word count statistics by difficulty',
    )
    def get(self, request):
        return Response({
            'total_active':  get_word_count(),
            'easy':   Dictionary.objects.filter(is_active=True, difficulty='easy').count(),
            'medium': Dictionary.objects.filter(is_active=True, difficulty='medium').count(),
            'hard':   Dictionary.objects.filter(is_active=True, difficulty='hard').count(),
        }, status=status.HTTP_200_OK)
