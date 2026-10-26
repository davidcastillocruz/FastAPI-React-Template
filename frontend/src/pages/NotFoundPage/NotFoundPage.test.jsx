import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, describe, expect, test, vi } from 'vitest';

import LanguageProvider from '@/languages/LanguageProvider';

import NotFoundPage from './NotFoundPage';

afterEach(() => vi.restoreAllMocks());

describe('NotFoundPage', () => {
  test('says which address does not exist and links back home', () => {
    vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['es']);
    const router = createMemoryRouter([{ path: '*', element: <NotFoundPage /> }], { initialEntries: ['/no/existe'] });
    render(
      <LanguageProvider>
        <RouterProvider router={router} />
      </LanguageProvider>,
    );

    expect(screen.getByText(/No sale nada desde \/no\/existe/)).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Volver a las salidas' }).getAttribute('href')).toBe('/');
  });
});
