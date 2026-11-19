import { portabilityHandlers } from "@/api/mocks/handlers/automationPortability";
import { automationHandlers } from "@/api/mocks/handlers/automations";
import { channelHandlers, credentialHandlers } from "@/api/mocks/handlers/channels";
import { runHandlers } from "@/api/mocks/handlers/runs";
import { storageHandlers } from "@/api/mocks/handlers/storage";
import { systemHandlers } from "@/api/mocks/handlers/system";
import { templateHandlers } from "@/api/mocks/handlers/templates";

export const handlers = [
  ...systemHandlers,
  ...templateHandlers,
  ...portabilityHandlers,
  ...automationHandlers,
  ...runHandlers,
  ...storageHandlers,
  ...credentialHandlers,
  ...channelHandlers,
];
