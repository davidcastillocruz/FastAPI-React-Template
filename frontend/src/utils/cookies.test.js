import { describe, expect, test } from 'vitest';

import { deleteCookie, getCookie, setCookie } from './cookies';

describe('cookies', () => {
  test('saves, reads and deletes a cookie', () => {
    setCookie('theme', 'dark');
    expect(getCookie('theme')).toBe('dark');

    deleteCookie('theme');
    expect(getCookie('theme')).toBeNull();
  });

  test('the cookie lasts the max age it was given', () => {
    // A max age of 0 expires it at once, without max-age it would stay until the browser closes
    setCookie('theme', 'dark', 0);
    expect(getCookie('theme')).toBeNull();
  });

  test('a cookie that does not exist is null', () => {
    expect(getCookie('nope')).toBeNull();
  });

  test('encodes the value and reads it back', () => {
    setCookie('note', 'a b;c=d');
    expect(getCookie('note')).toBe('a b;c=d');
  });

  test('a badly encoded value comes back as it is', () => {
    document.cookie = 'theme=%E0; path=/';
    expect(getCookie('theme')).toBe('%E0');
  });
});
