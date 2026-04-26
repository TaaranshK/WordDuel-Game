from django.test import TestCase
from rest_framework.test import APIClient

from .models import Dictionary


class DictionaryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_add_word_success(self):
        resp = self.client.post("/api/dictionary/words/add/", {"word": "apple"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["word"], "APPLE")
        self.assertEqual(resp.data["word_length"], 5)
        self.assertEqual(resp.data["difficulty"], "medium")
        self.assertTrue(resp.data["is_active"])

    def test_add_word_invalid(self):
        resp = self.client.post("/api/dictionary/words/add/", {"word": "a"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_add_word_duplicate(self):
        Dictionary.objects.create(word="APPLE", word_length=5, difficulty="medium", is_active=True)
        resp = self.client.post("/api/dictionary/words/add/", {"word": "apple"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_list_words_and_filters(self):
        Dictionary.objects.create(word="TREE", word_length=4, difficulty="easy", is_active=True)
        Dictionary.objects.create(word="APPLE", word_length=5, difficulty="medium", is_active=True)
        Dictionary.objects.create(word="ELEPHANT", word_length=8, difficulty="hard", is_active=True)
        Dictionary.objects.create(word="INACTIVE", word_length=8, difficulty="hard", is_active=False)

        resp = self.client.get("/api/dictionary/words/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 3)

        resp = self.client.get("/api/dictionary/words/?difficulty=hard")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["word"], "ELEPHANT")

        resp = self.client.get("/api/dictionary/words/?length=5")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["word"], "APPLE")

        resp = self.client.get("/api/dictionary/words/?length=oops")
        self.assertEqual(resp.status_code, 400)

    def test_toggle_word(self):
        word = Dictionary.objects.create(word="TREE", word_length=4, difficulty="easy", is_active=True)
        resp = self.client.patch(f"/api/dictionary/words/{word.id}/toggle/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["is_active"])

        word.refresh_from_db()
        self.assertFalse(word.is_active)

    def test_toggle_word_not_found(self):
        resp = self.client.patch("/api/dictionary/words/999999/toggle/")
        self.assertEqual(resp.status_code, 404)

    def test_stats(self):
        Dictionary.objects.create(word="TREE", word_length=4, difficulty="easy", is_active=True)
        Dictionary.objects.create(word="APPLE", word_length=5, difficulty="medium", is_active=True)
        Dictionary.objects.create(word="ELEPHANT", word_length=8, difficulty="hard", is_active=True)
        Dictionary.objects.create(word="INACTIVE", word_length=8, difficulty="hard", is_active=False)

        resp = self.client.get("/api/dictionary/stats/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total_active"], 3)
        self.assertEqual(resp.data["easy"], 1)
        self.assertEqual(resp.data["medium"], 1)
        self.assertEqual(resp.data["hard"], 1)
