from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.dictionary.models import Dictionary
from apps.dictionary.utils import read_words_from_file


class Command(BaseCommand):
    help = 'Seed the dictionary table from a .txt file (one word per line)'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the .txt file containing words'
        )
        parser.add_argument(
            '--difficulty',
            type=str,
            default='medium',
            choices=['easy', 'medium', 'hard'],
            help='Difficulty level for all words in this file (default: medium)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing dictionary before seeding'
        )

    def handle(self, *args, **options):
        file_path  = options['file_path']
        difficulty = options['difficulty']
        clear      = options['clear']

        # check file exists
        if not Path(file_path).exists():
            raise CommandError(f"File not found: {file_path}")

        # optionally clear existing words
        if clear:
            count = Dictionary.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f"Cleared {count} existing words."))

        words, skipped_words = read_words_from_file(file_path)

        valid_words = [
            Dictionary(
                word=word,
                word_length=len(word),
                difficulty=difficulty,
                is_active=True,
            )
            for word in words
        ]

        if not valid_words:
            raise CommandError("No valid words found in file.")

        # bulk insert — ignore duplicates
        created = Dictionary.objects.bulk_create(
            valid_words,
            ignore_conflicts=True,   # skip words already in DB
        )

        # results
        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {len(created)} words with difficulty '{difficulty}'."
        ))

        if skipped_words:
            self.stdout.write(self.style.WARNING(
                f"Skipped {len(skipped_words)} invalid words: {', '.join(skipped_words[:10])}"
                f"{'...' if len(skipped_words) > 10 else ''}"
            ))
