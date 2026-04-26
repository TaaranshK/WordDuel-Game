from django.db import models


class Dictionary(models.Model):
    """
    Dictionary model storing words available for the game.
    """
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    word = models.CharField(max_length=12, unique=True)
    word_length = models.IntegerField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['word']
        verbose_name_plural = 'Dictionaries'

    def __str__(self):
        return self.word
