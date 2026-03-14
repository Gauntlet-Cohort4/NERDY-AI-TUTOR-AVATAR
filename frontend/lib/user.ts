const USER_ID_KEY = "nerdy_tutor_user_id";
const USER_NAME_KEY = "nerdy_tutor_user_name";
const DEFAULT_USER_NAME = "Student";
const MAX_NAME_LENGTH = 100;

/**
 * Get or create a stable user ID stored in localStorage.
 * Returns null during SSR — callers must guard against this.
 */
export function getUserId(): string | null {
  if (typeof window === "undefined") return null;

  let userId = localStorage.getItem(USER_ID_KEY);
  if (!userId) {
    userId = crypto.randomUUID();
    localStorage.setItem(USER_ID_KEY, userId);
  }
  return userId;
}

/**
 * Get the user's display name, defaulting to "Student".
 */
export function getUserName(): string {
  if (typeof window === "undefined") return DEFAULT_USER_NAME;
  return localStorage.getItem(USER_NAME_KEY) || DEFAULT_USER_NAME;
}

/**
 * Update the user's display name in localStorage.
 * Sanitizes input to prevent stored XSS.
 */
export function setUserName(name: string): void {
  if (typeof window !== "undefined") {
    const sanitized = name.replace(/[<>"'&]/g, "").trim().slice(0, MAX_NAME_LENGTH);
    localStorage.setItem(USER_NAME_KEY, sanitized || DEFAULT_USER_NAME);
  }
}
