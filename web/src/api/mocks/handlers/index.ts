import { automationHandlers } from "@/api/mocks/handlers/automations";
import { channelHandlers, credentialHandlers } from "@/api/mocks/handlers/channels";
import { runHandlers } from "@/api/mocks/handlers/runs";
import { systemHandlers } from "@/api/mocks/handlers/system";

export const handlers = [
  ...systemHandlers,
  ...automationHandlers,
  ...runHandlers,
  ...credentialHandlers,
  ...channelHandlers,
];
