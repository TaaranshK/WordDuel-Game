"""
Utility functions for game app.
"""


def calculate_points(time_taken, base_points=10):
    """
    Calculate points based on time taken.
    Faster guesses earn more points.
    """
    points = max(base_points - int(time_taken), 1)
    return points


def check_word_validity(word):
    """
    Check if a word is valid for the game.
    """
    if not word or len(word) < 2:
        return False
    return word.isalpha()
