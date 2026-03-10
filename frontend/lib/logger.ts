type LogLevel = "debug" | "info" | "warn" | "error";

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  component: string;
  event: string;
  [key: string]: unknown;
}

export function createLogger(component: string) {
  const log = (
    level: LogLevel,
    event: string,
    data?: Record<string, unknown>
  ) => {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      component,
      event,
      ...data,
    };
    console[level](JSON.stringify(entry));
  };

  return {
    debug: (event: string, data?: Record<string, unknown>) =>
      log("debug", event, data),
    info: (event: string, data?: Record<string, unknown>) =>
      log("info", event, data),
    warn: (event: string, data?: Record<string, unknown>) =>
      log("warn", event, data),
    error: (event: string, data?: Record<string, unknown>) =>
      log("error", event, data),
  };
}
