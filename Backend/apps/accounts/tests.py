from django.test import TestCase
from rest_framework.test import APIClient

from .models import Player


class AccountsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_join_success(self):
        resp = self.client.post("/api/accounts/join/", {"username": "Alice"}, format="json")
        self.assertEqual(resp.status_code, 200)

        self.assertIn("player", resp.data)
        self.assertIn("session_token", resp.data)

        self.assertEqual(resp.data["player"]["username"], "Alice")
        self.assertTrue(resp.data["session_token"])

    def test_join_missing_username(self):
        resp = self.client.post("/api/accounts/join/", {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_player_profile_success(self):
        player = Player.objects.create(username="Bob")
        resp = self.client.get(f"/api/accounts/player/{player.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], player.id)
        self.assertEqual(resp.data["username"], "Bob")

    def test_player_profile_not_found(self):
        resp = self.client.get("/api/accounts/player/999999/")
        self.assertEqual(resp.status_code, 404)

    def test_leaderboard_ordering(self):
        Player.objects.create(username="p1", total_wins=2, total_matches=5)
        Player.objects.create(username="p2", total_wins=3, total_matches=1)
        Player.objects.create(username="p3", total_wins=3, total_matches=9)

        resp = self.client.get("/api/accounts/leaderboard/")
        self.assertEqual(resp.status_code, 200)

        usernames = [p["username"] for p in resp.data]
        self.assertEqual(usernames[0], "p3")  # wins tie-break: more matches
        self.assertEqual(usernames[1], "p2")
