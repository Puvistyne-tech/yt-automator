import { waitFor } from "@testing-library/react";
import type { User } from "../helpers/renderApp";
import { failWith, server } from "../helpers/server";
import {
  disconnectChannels,
  FIND,
  findIdeas,
  openSuggestions,
  panel,
} from "../helpers/suggestions";

const PATH = "/templates/suggestions";
const YOUTUBE_SOURCE = /trending on YouTube/;
const DROPPED = /left out because/;

async function searchAgain(user: User) {
  await user.click(panel().getByRole("button", FIND));
  await waitFor(() => expect(panel().queryByRole("status", { name: "Finding ideas" })).toBeNull());
}

function ideaNames() {
  return panel()
    .queryAllByRole("article")
    .map((card) => card.querySelector("h3")?.textContent);
}

describe("Pipelines: replacing suggested ideas", () => {
  it("replaces the cards, source and dropped lines with the next answer", async () => {
    const { user } = await openSuggestions();
    await findIdeas(user);
    expect(panel().getByText(DROPPED)).toBeInTheDocument();

    disconnectChannels();
    await user.click(panel().getByRole("radio", { name: /^General audience/ }));
    await user.selectOptions(panel().getByLabelText("Number of ideas"), "3");
    await searchAgain(user);

    await waitFor(() =>
      expect(ideaNames()).toEqual([
        "Engineering in plain words",
        "Street food atlas",
        "Skill in a week",
      ]),
    );
    expect(panel().getByText(/built-in sample trends/)).toBeInTheDocument();
    expect(panel().queryByText(YOUTUBE_SOURCE)).not.toBeInTheDocument();
    expect(panel().queryByText(DROPPED)).not.toBeInTheDocument();
  });

  it.each<[string, () => void, RegExp]>([
    [
      "is unavailable",
      () =>
        failWith("post", PATH, 409, {
          code: "suggestions_unavailable",
          message: "No text model.",
        }),
      /No text model\./,
    ],
    [
      "refuses a field",
      () => failWith("post", PATH, 400, { message: "Bad", fields: { count: "Too many." } }),
      /Too many\./,
    ],
  ])("clears the old ideas when the next search %s", async (_name, fail, shown) => {
    const { user } = await openSuggestions();
    await findIdeas(user);

    fail();
    await searchAgain(user);

    expect(await panel().findByText(shown)).toBeInTheDocument();
    expect(panel().queryAllByRole("article")).toEqual([]);
    expect(panel().queryByText(YOUTUBE_SOURCE)).not.toBeInTheDocument();
    expect(panel().queryByText(DROPPED)).not.toBeInTheDocument();

    server.resetHandlers();
    await searchAgain(user);

    expect(await panel().findAllByRole("article")).toHaveLength(4);
    expect(panel().queryByText(shown)).not.toBeInTheDocument();
  });
});
