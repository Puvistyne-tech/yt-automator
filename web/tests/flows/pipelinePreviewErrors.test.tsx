import { screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { db } from "@/api/mocks/db";
import {
  clickWrite,
  openSaved,
  PREVIEW,
  previewCard,
  SAMPLE,
  writeSample,
} from "../helpers/preview";
import { disableWriters } from "../helpers/providers";
import { findToast } from "../helpers/renderApp";
import { failWith, server } from "../helpers/server";

const pressed = (name: string) => screen.getByRole("button", { name, pressed: true });
const noSample = () => expect(screen.queryByRole("article", SAMPLE)).not.toBeInTheDocument();

function failOnce(status: number, code: string, message: string) {
  server.use(
    http.post(
      `/api${PREVIEW}`,
      () => HttpResponse.json({ error: { code, message, fields: {} } }, { status }),
      { once: true },
    ),
  );
}

describe("Pipeline editor: sample script errors", () => {
  it.each([
    { field: "language", label: /^Language/, message: "language must be one of: en, ta" },
    {
      field: "topic",
      label: /^Topic \(optional\)/,
      message: "String should have at most 300 characters",
    },
    { field: "name", label: /^Name/, message: "name is required" },
    { field: "definition.brief", label: /^What the videos are about/, message: "Too childish." },
  ])("puts a refused $field on its field with a toast", async ({ field, label, message }) => {
    failWith("post", PREVIEW, 400, {
      code: "validation_failed",
      message: "Validation failed",
      fields: { [field]: message },
    });
    const { user } = await openSaved("/pipelines/space-facts");

    await clickWrite(user);

    await findToast("Validation failed");
    expect(screen.getByLabelText(label)).toHaveAccessibleDescription(
      expect.stringContaining(message),
    );
    noSample();
  });

  it("refuses a topic over 300 characters from the server's own rule", async () => {
    const { user } = await openSaved("/pipelines/space-facts");
    await user.click(previewCard().getByLabelText(/^Topic/));
    await user.paste("x".repeat(301));

    await clickWrite(user);

    expect(await previewCard().findByText(/at most 300 characters/)).toBeInTheDocument();
    expect(previewCard().getByLabelText(/^Topic/)).toHaveAccessibleDescription(/at most 300/);
    noSample();
  });

  it.each(["/pipelines/space-facts", "/pipelines/kids_story"])(
    "switches %s to All settings when the sample fails on a field Simple hides",
    async (route) => {
      failWith("post", PREVIEW, 400, {
        message: "Validation failed",
        fields: { "definition.music_mood": "Pick a calmer mood." },
      });
      const { user } = await openSaved(route);
      expect(pressed("Simple")).toBeInTheDocument();

      await clickWrite(user);

      expect(await screen.findByLabelText(/^Music mood/)).toHaveAccessibleDescription(
        /Pick a calmer mood/,
      );
      expect(pressed("All settings")).toBeInTheDocument();
    },
  );

  it.each([
    [400, "validation_failed", "Validation failed"],
    [409, "preview_unavailable", "No writer."],
  ])("clears the shown sample when the next one fails with %i", async (status, code, message) => {
    const { user } = await openSaved("/pipelines/space-facts");
    await writeSample(user, "tides");
    failOnce(status, code, message);

    await clickWrite(user);

    expect(await screen.findAllByText(message)).not.toHaveLength(0);
    noSample();
  });

  it("explains calmly when no script writer is ready, until a later sample succeeds", async () => {
    const writers = db.state.providerConfig;
    disableWriters();
    const { user } = await openSaved("/pipelines/space-facts");

    await clickWrite(user);

    const notice = await previewCard().findByText(/The script writer is not available/);
    expect(notice.closest(".callout")).toHaveClass("callout-info");
    expect(previewCard().getByRole("link", { name: "Open Providers" })).toHaveAttribute(
      "href",
      "/providers",
    );
    db.state.providerConfig = writers;
    await writeSample(user);
    expect(previewCard().queryByText(/The script writer is not available/)).not.toBeInTheDocument();
  });

  it("reports any other failure as a toast without the Providers link", async () => {
    failWith("post", PREVIEW, 500, { code: "internal_error", message: "Unexpected server error" });
    const { user } = await openSaved("/pipelines/space-facts");

    await clickWrite(user);

    await findToast("Unexpected server error");
    expect(previewCard().queryByRole("link", { name: "Open Providers" })).not.toBeInTheDocument();
    noSample();
  });
});
