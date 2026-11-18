export interface CapturedDownload {
  filename: string;
  json: () => Promise<Record<string, unknown>>;
}

export function captureDownloads(): CapturedDownload[] {
  const downloads: CapturedDownload[] = [];
  const blobs = new Map<string, Blob>();
  vi.spyOn(URL, "createObjectURL").mockImplementation((blob) => {
    const url = `blob:test/${blobs.size}`;
    blobs.set(url, blob as Blob);
    return url;
  });
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    const blob = blobs.get(this.getAttribute("href") ?? "");
    downloads.push({
      filename: this.download,
      json: async () => JSON.parse((await blob?.text()) ?? "{}") as Record<string, unknown>,
    });
  });
  return downloads;
}

export function exportFile(document: unknown, name = "bedtime.autotube.json"): File {
  return new File([JSON.stringify(document)], name, { type: "application/json" });
}
