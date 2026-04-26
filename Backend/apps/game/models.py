from django.db import models
from apps.accounts.models import Player


class Match(models.Model):
    """
    Match model representing a game between two players.
    """

    class Status(models.TextChoices):
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"
    
    id = models.BigAutoField(primary_key=True)
    player1 = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='matches_as_player1')
    player2 = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='matches_as_player2')
    score1 = models.IntegerField(default=0)
    score2 = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ONGOING)
    winner = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    max_rounds = models.IntegerField(default=5)
    tick_duration_ms = models.IntegerField(default=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Match {self.id}: {self.player1.username} vs {self.player2.username}"


class Round(models.Model):
    """
    Round model representing each round within a match.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
    
    id = models.BigAutoField(primary_key=True)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='rounds')
    word = models.CharField(max_length=12)
    word_length = models.IntegerField()
    revealed_tiles = models.JSONField(default=list)
    revealed_letters = models.JSONField(default=list)
    tick_number = models.IntegerField(default=0)
    round_number = models.IntegerField()
    winner = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_rounds')
    is_draw = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['round_number']

    def __str__(self):
        return f"Round {self.round_number} - Match {self.match.id}"


class PlayerSession(models.Model):
    """
    PlayerSession model tracking player session in a match.
    """
    id = models.BigAutoField(primary_key=True)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=64, unique=True)
    match = models.ForeignKey(Match, on_delete=models.SET_NULL, null=True, blank=True, related_name='player_sessions')
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('player', 'match')

    def __str__(self):
        return f"{self.player.username} - Session {self.session_token[:8]}"


class Guess(models.Model):
    """
    Guess model tracking individual guesses made by players.
    """
    id = models.BigAutoField(primary_key=True)
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='guesses')
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='guesses')
    tick_number = models.IntegerField()
    guess_text = models.CharField(max_length=12)
    is_correct = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True)
    client_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['received_at']

    def __str__(self):
        return f"Guess: {self.guess_text} - {'Correct' if self.is_correct else 'Incorrect'}"
