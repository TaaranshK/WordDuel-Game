import { createFileRoute } from "@tanstack/react-router";
import { SocketProvider } from "@/game/socket";
import { WordDuel } from "@/components/game/WordDuel";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "WordDuel — Real-Time Word Battle" },
      {
        name: "description",
        content:
          "Two players. One hidden word. Race to guess as letters reveal every 5 seconds. Real-time multiplayer word duel.",
      },
      { property: "og:title", content: "WordDuel — Real-Time Word Battle" },
      {
        property: "og:description",
        content: "One word. Two players. No mercy. Competitive real-time word guessing game.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <SocketProvider>
      <WordDuel />
    </SocketProvider>
  );
}
