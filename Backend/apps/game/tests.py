import time

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from config.asgi import application

from apps.accounts.models import Player
from apps.dictionary.models import Dictionary

from .models import Match, Round


class GameApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_match_detail_success_and_not_found(self):
        p1 = Player.objects.create(username="p1")
        p2 = Player.objects.create(username="p2")
        match = Match.objects.create(player1=p1, player2=p2, score1=1, score2=2)

        resp = self.client.get(f"/api/game/match/{match.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], match.id)
        self.assertEqual(resp.data["player1"]["username"], "p1")
        self.assertEqual(resp.data["player2"]["username"], "p2")

        resp = self.client.get("/api/game/match/999999/")
        self.assertEqual(resp.status_code, 404)

    def test_match_rounds_success_and_not_found(self):
        p1 = Player.objects.create(username="p1")
        p2 = Player.objects.create(username="p2")
        match = Match.objects.create(player1=p1, player2=p2)

        Round.objects.create(
            match=match,
            word="APPLE",
            word_length=5,
            revealed_tiles=[True] * 5,
            revealed_letters=list("APPLE"),
            round_number=1,
            status=Round.Status.COMPLETED,
            winner=p1,
        )

        resp = self.client.get(f"/api/game/match/{match.id}/rounds/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["round_number"], 1)

        resp = self.client.get("/api/game/match/999999/rounds/")
        self.assertEqual(resp.status_code, 404)

    def test_match_history_and_active_match(self):
        p1 = Player.objects.create(username="p1")
        p2 = Player.objects.create(username="p2")

        resp = self.client.get(f"/api/game/match/history/{p1.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("message", resp.data)  # no matches case

        completed = Match.objects.create(
            player1=p1,
            player2=p2,
            status=Match.Status.COMPLETED,
            score1=2,
            score2=1,
            winner=p1,
        )

        resp = self.client.get(f"/api/game/match/history/{p1.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["id"], completed.id)

        ongoing = Match.objects.create(player1=p1, player2=p2, status=Match.Status.ONGOING)
        resp = self.client.get(f"/api/game/match/active/{p1.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], ongoing.id)


class WordDuelWebSocketTests(TransactionTestCase):
    @override_settings(
        WORDDUEL_FIRST_ROUND_DELAY_S=0,
        WORDDUEL_AFTER_START_ROUND_GAP_S=0,
        WORDDUEL_BETWEEN_TICKS_GAP_S=0,
        WORDDUEL_ROUND_END_DELAY_S=0,
        WORDDUEL_TICK_DURATION_MS=200,
        WORDDUEL_MAX_ROUNDS=1,
    )
    def test_wordduel_websocket_flow(self):
        # Ensure at least one active word is available.
        Dictionary.objects.create(word="APPLE", word_length=5, difficulty="medium", is_active=True)

        # Reset in-memory state between tests
        from apps.game.consumers import wordduel as ws
        ws._LOBBY_QUEUE.clear()
        ws._MATCHES.clear()

        async def recv_event(comm: WebsocketCommunicator, name: str, *, timeout: float = 2.0):
            while True:
                msg = await comm.receive_json_from(timeout=timeout)
                if msg.get("event") == name:
                    return msg

        async def run():
            c1 = WebsocketCommunicator(application, "/ws/wordduel/")
            c2 = WebsocketCommunicator(application, "/ws/wordduel/")

            connected, _ = await c1.connect()
            self.assertTrue(connected)
            connected, _ = await c2.connect()
            self.assertTrue(connected)

            await c1.send_json_to({"event": "joinLobby", "payload": {"username": "Alice"}})
            await c2.send_json_to({"event": "joinLobby", "payload": {"username": "Bob"}})

            m1 = await recv_event(c1, "matchFound")
            m2 = await recv_event(c2, "matchFound")
            self.assertEqual(m1["payload"]["opponentUsername"], "Bob")
            self.assertEqual(m2["payload"]["opponentUsername"], "Alice")

            s1 = await recv_event(c1, "startRound")
            s2 = await recv_event(c2, "startRound")
            self.assertEqual(s1["payload"]["wordLength"], 5)
            self.assertEqual(s2["payload"]["wordLength"], 5)

            await recv_event(c1, "tickStart")
            await recv_event(c2, "tickStart")

            await c1.send_json_to({
                "event": "submitGuess",
                "payload": {"guessText": "APPLE", "clientSentAt": int(time.time() * 1000)},
            })

            await recv_event(c2, "opponentGuessed")

            r1 = await recv_event(c1, "roundEnd")
            r2 = await recv_event(c2, "roundEnd")
            self.assertEqual(r1["payload"]["winner"], "me")
            self.assertEqual(r2["payload"]["winner"], "opponent")
            self.assertEqual(r1["payload"]["revealedWord"], "APPLE")

            e1 = await recv_event(c1, "matchEnd")
            e2 = await recv_event(c2, "matchEnd")
            self.assertEqual(e1["payload"]["winner"], "me")
            self.assertEqual(e2["payload"]["winner"], "opponent")
            self.assertEqual(e1["payload"]["totalRounds"], 1)

            await c1.disconnect()
            await c2.disconnect()

        async_to_sync(run)()
