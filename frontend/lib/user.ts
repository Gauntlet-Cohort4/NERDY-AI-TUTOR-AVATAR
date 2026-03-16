const USER_ID_KEY = "nerdy_tutor_user_id";
const USER_NAME_KEY = "nerdy_tutor_user_name";
const DEFAULT_USER_NAME = "Student";
const MAX_NAME_LENGTH = 100;

// Demo user ID — must match _DEMO_USER_ID in agent/main.py.
// TODO: Replace with real user auth when multi-user support is added.
const DEMO_USER_ID = "00000000-0000-0000-0000-000000000001";

/**
 * Get or create a stable user ID stored in localStorage.
 * Returns null during SSR — callers must guard against this.
 */
export function getUserId(): string | null {
  if (typeof window === "undefined") return null;

  // For demo, always use the hardcoded demo user so sessions/artifacts match.
  localStorage.setItem(USER_ID_KEY, DEMO_USER_ID);
  return DEMO_USER_ID;
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
