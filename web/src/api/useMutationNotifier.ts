import { errorMessage } from "@/api/errors";
import { type ToastAction, useToast } from "@/shared/ui";

export interface NotifyOptions<T> {
  success: string | ((data: T) => string);
  action?: (data: T) => ToastAction;
  onSuccess?: (data: T) => void;
  onError?: (error: unknown) => void;
  onDone?: () => void;
}

export interface MutationHandlers<T> {
  onSuccess: (data: T) => void;
  onError: (error: unknown) => void;
  onSettled: () => void;
}

export interface MutationNotifier {
  succeed: (message: string) => void;
  warn: (message: string) => void;
  fail: (error: unknown) => void;
  handlers: <T>(options: NotifyOptions<T>) => MutationHandlers<T>;
  track: <T>(promise: Promise<T>, options: NotifyOptions<T>) => Promise<void>;
}

function handlersFor<T>(
  options: NotifyOptions<T>,
  toast: { success: (message: string, action?: ToastAction) => void },
  fail: (error: unknown) => void,
): MutationHandlers<T> {
  return {
    onSuccess: (data: T) => {
      const message = typeof options.success === "string" ? options.success : options.success(data);
      toast.success(message, options.action?.(data));
      options.onSuccess?.(data);
    },
    onError: (error: unknown) => {
      fail(error);
      options.onError?.(error);
    },
    onSettled: () => options.onDone?.(),
  };
}

export function useMutationNotifier(): MutationNotifier {
  const toast = useToast();
  const fail = (error: unknown) => toast.error(errorMessage(error));
  return {
    succeed: (message) => toast.success(message),
    warn: (message) => toast.error(message),
    fail,
    handlers: (options) => handlersFor(options, toast, fail),
    track: (promise, options) => {
      const handlers = handlersFor(options, toast, fail);
      return promise.then(handlers.onSuccess, handlers.onError).finally(handlers.onSettled);
    },
  };
}
