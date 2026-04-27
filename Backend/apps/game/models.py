from django.db import models
from accounts.models import Player


class Match(models.Model):

    class Status(models.TextChoices):
        ONGOING   = 'ongoing',   'Ongoing'
        COMPLETED = 'completed', 'Completed'
        ABANDONED = 'abandoned', 'Abandoned'

    player1          = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='matches_as_player1')
    player2          = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='matches_as_player2')
    score1           = models.IntegerField(default=0)
    score2           = models.IntegerField(default=0)
    status           = models.CharField(max_length=10, choices=Status.choices, default=Status.ONGOING)
    winner           = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    max_rounds       = models.IntegerField(default=5)
    tick_duration_ms = models.IntegerField(default=5000)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'match'

    def __str__(self):
        return f"Match #{self.id} — {self.player1} vs {self.player2}"


class Round(models.Model):

    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        COMPLETED = 'completed', 'Completed'

    match            = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='rounds')
    word             = models.CharField(max_length=12)
    word_length      = models.IntegerField()
    revealed_tiles   = models.JSONField(default=list)   # [False, False, True, ...]
    revealed_letters = models.JSONField(default=list)   # ['', '', 'P', ...]
    tick_number      = models.IntegerField(default=0)
    round_number     = models.IntegerField()
    winner           = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_rounds')
    is_draw          = models.BooleanField(default=False)
    status           = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at       = models.DateTimeField(auto_now_add=True)
    ended_at         = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table        = 'round'
        unique_together = ('match', 'round_number')

    def __str__(self):
        return f"Round #{self.round_number} — Match #{self.match_id}"


class Guess(models.Model):
    round          = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='guesses')
    player         = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='guesses')
    tick_number    = models.IntegerField()
    guess_text     = models.CharField(max_length=12)
    is_correct     = models.BooleanField(default=False)
    received_at    = models.DateTimeField(auto_now_add=True)
    client_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table        = 'guess'
        unique_together = ('round', 'player', 'tick_number')  # one guess per player per tick

    def __str__(self):
        return f"Guess '{self.guess_text}' by {self.player} — Round #{self.round_id}"


class PlayerSession(models.Model):
    player          = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='sessions')
    session_token   = models.CharField(max_length=64, unique=True)
    match           = models.ForeignKey(Match, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    connected_at    = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    is_active       = models.BooleanField(default=True)

    class Meta:
        db_table = 'player_session'

    def __str__(self):
        return f"Session — {self.player} ({'active' if self.is_active else 'inactive'})"