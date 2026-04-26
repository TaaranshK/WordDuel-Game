import {
  createStartHandler,
  renderToString,
} from "@tanstack/react-start/server";
import { createMemoryHistory } from "@tanstack/react-router";
import { getRouter } from "./router";

export default createStartHandler({
  createHandler: () => async (req) => {
    const url = new URL(req.url);
    const router = getRouter();

    router.update({
      history: createMemoryHistory({
        initialEntries: [url.pathname + url.search],
      }),
    });

    await router.isReady();

    const html = await renderToString(router);

    return html;
  },
});
