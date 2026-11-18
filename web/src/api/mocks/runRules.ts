import type { RunStatus } from "@/api/types";

const RETRYABLE: RunStatus[] = ["failed", "cancelled", "awaiting_review", "approved", "rejected"];
const CANCELLABLE: RunStatus[] = ["queued", "running", "awaiting_review", "approved"];
const UNDELETABLE: RunStatus[] = ["queued", "running", "publishing"];

export const canRetry = (status: RunStatus) => RETRYABLE.includes(status);
export const canCancel = (status: RunStatus) => CANCELLABLE.includes(status);
export const canDelete = (status: RunStatus) => !UNDELETABLE.includes(status);
