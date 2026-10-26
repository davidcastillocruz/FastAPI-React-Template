import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CanceledError } from 'axios';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import LanguageProvider from '@/languages/LanguageProvider';
import ThemeProvider from '@/themes/ThemeProvider';
import { api } from '@/utils/api';

import HomePage from './HomePage';

vi.mock('@/utils/api', () => ({ api: { get: vi.fn(), post: vi.fn() } }));

const rows = (count, first = 1) =>
  Array.from({ length: count }, (_, index) => ({
    id: first + index,
    email: `user${first + index}@test.dev`,
    created_at: '2026-10-14T09:41:00Z',
  }));

// A request that answers when the test decides
function pending() {
  let resolve;
  const promise = new Promise((done) => (resolve = done));
  return { promise, resolve };
}

// Like axios: aborting the signal rejects the request with a CanceledError
function pendingGet() {
  const request = pending();
  const call = (_url, { signal }) =>
    new Promise((resolve, reject) => {
      signal?.addEventListener('abort', () => reject(new CanceledError()));
      request.promise.then(resolve, reject);
    });
  return { ...request, call };
}

// Emails written on the board, in order (the screen reader copy of each row)
const boardEmails = () =>
  [...document.querySelectorAll('tbody tr td:last-child .sr-only')].map((cell) => cell.textContent);

async function olderButtonReady() {
  const older = await screen.findByRole('button', { name: 'Older' });
  await waitFor(() => expect(older.getAttribute('aria-disabled')).toBe('false'));
  return older;
}

function renderPage() {
  return render(
    <ThemeProvider>
      <LanguageProvider>
        <HomePage />
      </LanguageProvider>
    </ThemeProvider>,
  );
}

const input = () => screen.getByLabelText('Destination');
const sendButton = () => screen.getByRole('button', { name: /Dispatch/ });
const result = () => document.getElementById('email-result');

function send(email) {
  fireEvent.change(input(), { target: { value: email } });
  fireEvent.click(sendButton());
}

beforeEach(() => {
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['en']);
  api.get.mockResolvedValue({ data: [] });
});

afterEach(() => {
  vi.restoreAllMocks();
  api.get.mockReset();
  api.post.mockReset();
});

describe('HomePage form', () => {
  test('an invalid address is rejected without calling the API', async () => {
    renderPage();
    send('not-an-address');

    expect(result().textContent).toMatch("doesn't look like an address");
    expect(api.post).not.toHaveBeenCalled();
  });

  test('the same error twice is a new text for the screen reader', () => {
    renderPage();
    send('not-an-address');
    const firstText = result().firstElementChild;

    send('still-not-an-address');

    expect(result().firstElementChild).not.toBe(firstText);
    expect(result().textContent).toBe(firstText.textContent);
  });

  test('a sent address shows the message of the backend, clears the field and reloads the board', async () => {
    api.post.mockResolvedValue({ data: { message: 'Done! Check your inbox' } });
    renderPage();
    send(' ana@test.dev ');

    await waitFor(() => expect(result().textContent).toMatch('Done! Check your inbox'));
    expect(api.post).toHaveBeenCalledWith('/email-requests', { email: 'ana@test.dev' });
    expect(input().value).toBe('');
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  test('what is typed while the request is on its way is kept', async () => {
    const request = pending();
    api.post.mockReturnValue(request.promise);
    renderPage();
    send('first@test.dev');
    fireEvent.change(input(), { target: { value: 'second@test.dev' } });

    await act(async () => request.resolve({ data: { message: 'Done!' } }));

    expect(input().value).toBe('second@test.dev');
  });

  test('only one send at a time', async () => {
    api.post.mockReturnValue(pending().promise);
    renderPage();
    send('ana@test.dev');
    fireEvent.click(sendButton());

    expect(api.post).toHaveBeenCalledOnce();
    expect(sendButton().getAttribute('aria-disabled')).toBe('true');
  });

  test('an error of the backend shows its translated detail', async () => {
    api.post.mockRejectedValue({ response: { data: { detail: 'This email has already asked for a test email' } } });
    renderPage();
    send('ana@test.dev');

    await waitFor(() => expect(result().textContent).toBe('This email has already asked for a test email'));
  });

  test('without an answer it shows its own text, not the one of axios', async () => {
    api.post.mockRejectedValue({ message: 'Network Error' });
    renderPage();
    send('ana@test.dev');

    await waitFor(() => expect(result().textContent).toMatch("The server didn't answer"));
    expect(result().textContent).not.toMatch('Network Error');
  });

  test('an answer without a detail of the backend shows its own text', async () => {
    // A proxy in front of the backend answers with its own HTML page
    api.post.mockRejectedValue({ response: { status: 502, data: '<html>Bad Gateway</html>' } });
    renderPage();
    send('ana@test.dev');

    await waitFor(() => expect(result().textContent).toBe('Something unexpected happened'));
  });
});

describe('HomePage board', () => {
  test('shows the rows of the page', async () => {
    api.get.mockResolvedValueOnce({ data: rows(2) });
    renderPage();

    await waitFor(() => expect(boardEmails()).toEqual(['user1@test.dev', 'user2@test.dev']));
  });

  test('an empty first page says there are no departures yet', async () => {
    renderPage();

    await waitFor(() => expect(boardEmails()).toEqual(['No departures yet']));
  });

  test('"Newer" goes back one page', async () => {
    api.get
      .mockResolvedValueOnce({ data: rows(10) })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: rows(10) });
    renderPage();
    fireEvent.click(await olderButtonReady());
    await waitFor(() => expect(boardEmails()).toEqual(['No older departures']));

    const newer = screen.getByRole('button', { name: 'Newer' });
    await waitFor(() => expect(newer.getAttribute('aria-disabled')).toBe('false'));
    fireEvent.click(newer);

    await screen.findByText('Page 1');
    expect(api.get).toHaveBeenLastCalledWith('/email-requests', expect.objectContaining({ params: { page: 1 } }));
    expect(boardEmails()).toHaveLength(10);
  });

  test('a page still on its way when a newer one is asked for is cancelled', async () => {
    const olderPage = pendingGet();
    api.get
      .mockResolvedValueOnce({ data: rows(10) })
      .mockImplementationOnce(olderPage.call)
      .mockResolvedValueOnce({ data: rows(1, 50) });
    api.post.mockResolvedValue({ data: { message: 'Done!' } });
    renderPage();
    fireEvent.click(await olderButtonReady());

    // Sending reloads page 1 while page 2 is still on its way
    send('ana@test.dev');
    await waitFor(() => expect(boardEmails()).toEqual(['user50@test.dev']));
    expect(api.get.mock.calls[1][1].signal.aborted).toBe(true);
    // Even if its answer still came, it wouldn't replace the newer page
    await act(async () => olderPage.resolve({ data: rows(10, 11) }));

    expect(boardEmails()).toEqual(['user50@test.dev']);
    expect(screen.getByText('Page 1')).toBeTruthy();
  });

  test('a cancelled page neither shows an error nor ends the loading of the newer one', async () => {
    const olderPage = pendingGet();
    const firstPage = pendingGet();
    api.get
      .mockResolvedValueOnce({ data: rows(10) })
      .mockImplementationOnce(olderPage.call)
      .mockImplementationOnce(firstPage.call);
    api.post.mockResolvedValue({ data: { message: 'Done!' } });
    renderPage();
    fireEvent.click(await olderButtonReady());

    // Sending reloads page 1 while page 2 is still on its way, and page 1 doesn't answer yet
    send('ana@test.dev');
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(3));
    await act(async () => {});

    expect(api.get.mock.calls[1][1].signal.aborted).toBe(true);
    expect(screen.queryByRole('alert')).toBeNull();
    expect(document.querySelector('[aria-busy]').getAttribute('aria-busy')).toBe('true');
  });

  test('a full page enables the older ones, a short one ends the pages', async () => {
    api.get.mockResolvedValueOnce({ data: rows(10) }).mockResolvedValueOnce({ data: rows(2, 11) });
    renderPage();
    const older = await screen.findByRole('button', { name: 'Older' });
    await waitFor(() => expect(older.getAttribute('aria-disabled')).toBe('false'));

    fireEvent.click(older);

    await screen.findByText('Page 2');
    expect(api.get).toHaveBeenLastCalledWith('/email-requests', expect.objectContaining({ params: { page: 2 } }));
    expect(older.getAttribute('aria-disabled')).toBe('true');
  });

  test('"Try again" asks again for the page that failed', async () => {
    api.get
      .mockResolvedValueOnce({ data: rows(10) })
      .mockRejectedValueOnce({ message: 'Network Error' })
      .mockResolvedValueOnce({ data: rows(2, 11) });
    renderPage();
    const older = await screen.findByRole('button', { name: 'Older' });
    await waitFor(() => expect(older.getAttribute('aria-disabled')).toBe('false'));

    fireEvent.click(older);
    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }));

    await screen.findByText('Page 2');
    expect(api.get).toHaveBeenLastCalledWith('/email-requests', expect.objectContaining({ params: { page: 2 } }));
    expect(screen.queryByRole('alert')).toBeNull();
  });

  test('a language picked while sending is the one of the error of the reload', async () => {
    const sending = pending();
    api.post.mockReturnValue(sending.promise);
    api.get
      .mockResolvedValueOnce({ data: [] })
      .mockRejectedValueOnce({ response: { data: { detail: 'Demasiadas peticiones' } } });
    renderPage();
    send('ana@test.dev');
    fireEvent.click(screen.getByRole('button', { name: 'ES' }));

    await act(async () => sending.resolve({ data: { message: 'Done!' } }));

    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch('Demasiadas peticiones'));
  });

  test('a page that fails after the language changed keeps the language it was asked in', async () => {
    const firstPage = pendingGet();
    api.get.mockImplementationOnce(firstPage.call);
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: 'ES' }));

    // Asked in English: its English text is hidden on the Spanish page
    await act(async () => firstPage.resolve(Promise.reject({ response: { data: { detail: 'Too many requests' } } })));

    expect(screen.getByRole('alert').textContent).toMatch('No se pudo actualizar el panel');
    expect(screen.getByRole('alert').textContent).not.toMatch('Too many requests');
  });

  test('"Try again" keeps the focus while it retries and every failure is a new alert', async () => {
    const retry = pendingGet();
    api.get.mockRejectedValueOnce({ message: 'Network Error' }).mockImplementationOnce(retry.call);
    renderPage();
    const button = await screen.findByRole('button', { name: 'Try again' });
    const firstAlert = screen.getByRole('alert');

    button.focus();
    fireEvent.click(button);
    expect(button.getAttribute('aria-disabled')).toBe('true');
    expect(document.activeElement).toBe(button);

    await act(async () => retry.resolve(Promise.reject({ message: 'Network Error' })));

    expect(screen.getByRole('alert')).not.toBe(firstAlert);
    expect(screen.getByRole('alert').textContent).toBe(firstAlert.textContent);
    expect(document.activeElement).toBe(button);
  });

  test('a retry that works takes the focus to the board, not to the top of the page', async () => {
    const retry = pendingGet();
    api.get.mockRejectedValueOnce({ message: 'Network Error' }).mockImplementationOnce(retry.call);
    renderPage();
    const button = await screen.findByRole('button', { name: 'Try again' });

    button.focus();
    fireEvent.click(button);
    await act(async () => retry.resolve({ data: rows(3) }));

    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'Departures board' }));
  });
});
