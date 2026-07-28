const configuredAdminPath = import.meta.env.VITE_ADMIN_PATH?.trim();

function isSafeLocalPath(value: string | undefined): value is string {
  return Boolean(value && value.startsWith("/") && value.length >= 24 && !value.includes("..") && !/[?#\s]/.test(value));
}

/**
 * The real local route is injected at build/start time from ignored `.env.local`.
 * It is a discovery barrier only; API authorization remains server-enforced.
 */
export const ADMIN_PATH = isSafeLocalPath(configuredAdminPath) ? configuredAdminPath : null;
export const isAdminPath = (pathname: string) => ADMIN_PATH !== null && pathname === ADMIN_PATH;
