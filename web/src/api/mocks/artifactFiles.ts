import { HttpResponse } from "msw";
import type { Artifact } from "@/api/types";

const PALETTES: Record<string, [string, string]> = {
  en: ["#6366f1", "#f59e0b"],
  ta: ["#ec4899", "#10b981"],
};

function isTall(artifact: Artifact): boolean {
  return Number(artifact.meta.height) > Number(artifact.meta.width);
}

function thumbnailSvg(artifact: Artifact): string {
  const [from, to] = PALETTES[artifact.language ?? "en"] ?? ["#6366f1", "#f59e0b"];
  const tall = isTall(artifact);
  const [width, height] = tall ? [540, 960] : [1280, 720];
  const title = artifact.language === "ta" ? "இரவுக் கதைகள்" : "Raju and the Lost Shell";
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${from}"/><stop offset="1" stop-color="${to}"/></linearGradient></defs>
<rect width="100%" height="100%" fill="url(#g)"/>
<circle cx="${width * 0.72}" cy="${height * 0.4}" r="${Math.min(width, height) * 0.22}" fill="#fff" opacity="0.25"/>
<circle cx="${width * 0.3}" cy="${height * 0.78}" r="${Math.min(width, height) * 0.12}" fill="#fff" opacity="0.18"/>
<text x="50%" y="${height * 0.86}" text-anchor="middle" font-family="system-ui, sans-serif" font-size="${tall ? 44 : 64}" font-weight="700" fill="#fff">${title}</text>
</svg>`;
}

const SUBTITLES = `WEBVTT

00:00:00.000 --> 00:00:04.000
Once upon a time, by a quiet blue sea, lived a little elephant called Raju.

00:00:04.000 --> 00:00:08.500
One morning Raju found a shiny shell that was not hers.

00:00:08.500 --> 00:00:13.000
"Someone must be missing this," she said, and set off to find its owner.
`;

const STORY = `# Raju and the Lost Shell

Raju finds a shell on the beach and searches the village for its owner.
Moral: returning what is not ours is a kind of kindness.
`;

function metadataFor(artifact: Artifact) {
  return {
    title: `Raju and the Lost Shell | ${isTall(artifact) ? "#shorts" : "Bedtime Story"}`,
    description: "A gentle story about honesty and kindness for children aged 3 to 7.",
    tags: ["kids stories", "bedtime", "moral stories", "raju"],
    category_id: "1",
    default_language: artifact.language,
  };
}

export function artifactResponse(artifact: Artifact) {
  switch (artifact.kind) {
    case "thumbnail":
    case "image":
      return new HttpResponse(thumbnailSvg(artifact), {
        headers: { "Content-Type": "image/svg+xml" },
      });
    case "subtitle":
      return HttpResponse.text(SUBTITLES, { headers: { "Content-Type": "text/vtt" } });
    case "metadata":
      return HttpResponse.json(metadataFor(artifact));
    case "text":
      return HttpResponse.text(STORY);
    default:
      return new HttpResponse(null, { status: 204 });
  }
}
