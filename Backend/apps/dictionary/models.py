from django.db import models


class Dictionary(models.Model):

    class Difficulty(models.TextChoices):
        EASY   = 'easy',   'Easy'
        MEDIUM = 'medium', 'Medium'
        HARD   = 'hard',   'Hard'

    word        = models.CharField(max_length=12, unique=True)
    word_length = models.IntegerField()
    difficulty  = models.CharField(max_length=6, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table = 'dictionary'

    def save(self, *args, **kwargs):
        self.word        = self.word.upper().strip()
        self.word_length = len(self.word)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.word} ({self.difficulty})"