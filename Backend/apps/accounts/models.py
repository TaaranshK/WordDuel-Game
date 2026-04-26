from django.db import models


class Player(models.Model):
    username     = models.CharField(max_length=50, unique=True)
    total_wins   = models.IntegerField(default=0)
    total_matches = models.IntegerField(default=0)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_computer  = models.BooleanField(default=False)  # AI player flag
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'player'
        ordering = ['-total_wins']

    def __str__(self):
        return self.username