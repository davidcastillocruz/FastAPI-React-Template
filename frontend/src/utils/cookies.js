const ONE_YEAR = 60 * 60 * 24 * 365;

// Value of a cookie, null if it doesn't exist
export function getCookie(name) {
  for (const part of document.cookie.split('; ')) {
    const [key, ...value] = part.split('=');
    if (key !== name) continue;
    try {
      return decodeURIComponent(value.join('='));
    } catch {
      // Badly encoded ("%E0"): returned as it is, the caller will see it's not valid
      return value.join('=');
    }
  }
  return null;
}

// path=/ shares it with every page, SameSite=Lax is the safe default for preferences
export function setCookie(name, value, maxAge = ONE_YEAR) {
  document.cookie = `${name}=${encodeURIComponent(value)}; max-age=${maxAge}; path=/; SameSite=Lax`;
}

export function deleteCookie(name) {
  document.cookie = `${name}=; max-age=0; path=/; SameSite=Lax`;
}
