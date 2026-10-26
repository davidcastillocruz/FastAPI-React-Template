import { isCancel } from 'axios';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';

import SplitFlap from '@/components/SplitFlap/SplitFlap';
import { LANGUAGES } from '@/languages/languages';
import { useLanguage } from '@/languages/useLanguage';
import { useT } from '@/languages/useT';
import { useTheme } from '@/themes/useTheme';
import { api } from '@/utils/api';

import styles from './HomePageStyle.module.css';
import translations from './HomePageTranslation.json';

// Something@something.something, no spaces. The backend validates it again
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

// Same page size as GET /email-requests: a full page means there may be older ones
const PAGE_SIZE = 10;

const GITHUB_USER = 'davidcastillocruz';
const MAILPIT_URL = 'http://localhost:8025';

// The stops of an email request, with the port each one is reachable at from your computer in development
const STATIONS = [
  { name: 'React', port: '5173' },
  { name: 'FastAPI', port: '8000' },
  { name: 'PostgreSQL', port: '5433' },
  { name: 'Mailpit', port: '8025' },
];

// Where the envelope stops on the line in each state of the trip. rejected: the address never left React,
// failed: the backend answered with an error, unreachable: the backend didn't answer
const TRIP_STOP = { idle: 0, rejected: 0, sending: 1, sent: 3, failed: 1, unreachable: 0 };

// Cells of each column of the board
const ID_CELLS = 5;
const TIME_CELLS = 12;
const EMAIL_CELLS = 28;
// Delay between one row of the board and the next one
const ROW_STAGGER_MS = 70;

// "14 OCT 09:41", the time column of the board. h23: midnight is 00:05, not 24:05
function boardTime(date, language) {
  const day = String(date.getDate()).padStart(2, '0');
  const month = date.toLocaleDateString(language, { month: 'short' }).replace('.', '').slice(0, 3);
  const time = date.toLocaleTimeString(language, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
  return `${day} ${month} ${time}`;
}

// What to tell the user about a failed request, as a notice: { key } for a text of this page,
// { text, language } for a text the backend already translated
function requestError(error, language) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return { text: detail, language };
  return { key: error.response ? 'unexpected' : 'noConnection' };
}

function Envelope() {
  return (
    <svg viewBox="0 0 22 16" aria-hidden="true">
      <rect x="1" y="1" width="20" height="14" rx="1.5" />
      <path d="M1.5 2 11 9.5 20.5 2" />
    </svg>
  );
}

export default function HomePage() {
  const t = useT(translations);
  const { theme, setTheme } = useTheme();
  const { language, setLanguage } = useLanguage();

  // Form
  const [email, setEmail] = useState('');
  // Answer of the last send, a notice (see requestError)
  const [result, setResult] = useState(null);
  // idle | rejected | sending | sent | failed | unreachable: moves the envelope along the line
  const [trip, setTrip] = useState('idle');
  // Every attempt starts a new envelope at React
  const [tripId, setTripId] = useState(0);

  // Board: null until the first page arrives
  const [requests, setRequests] = useState(null);
  const [page, setPage] = useState(1);
  // Notice of the last page that failed, with that page so "Try again" asks for it again
  // and a count of the failures, so the same error twice is announced again
  const [listError, setListError] = useState(null);
  const [listLoading, setListLoading] = useState(false);
  // AbortController of the page being loaded
  const listRequest = useRef(null);
  // A retry that works removes "Try again" with the focus on it: the focus goes to the board title instead
  const boardTitle = useRef(null);
  const focusBoardAfterRetry = useRef(false);
  // Current language for loadPage: after a send it runs from the handler of an older render,
  // whose language may have changed while the email was on its way
  const languageRef = useRef(language);
  useLayoutEffect(() => {
    languageRef.current = language;
  }, [language]);

  // Text of a notice in the current language. A backend text only exists in the language it was asked in
  function noticeText(notice) {
    if (!notice) return '';
    if (notice.key) return t(notice.key);
    return notice.language === language ? notice.text : '';
  }

  // Only the last page asked for counts: asking for another one cancels the one on its way.
  // The previous rows stay on the board until the new page arrives
  async function loadPage(newPage) {
    listRequest.current?.abort();
    const controller = new AbortController();
    listRequest.current = controller;
    // The request goes with the language cookie of now: a translated error comes in this language
    const requestLanguage = languageRef.current;
    setListLoading(true);

    try {
      const { data } = await api.get('/email-requests', { params: { page: newPage }, signal: controller.signal });
      setRequests(data);
      setPage(newPage);
      setListError(null);
    } catch (error) {
      if (isCancel(error)) return;
      setListError((current) => ({ ...requestError(error, requestLanguage), page: newPage, attempt: (current?.attempt ?? 0) + 1 }));
    } finally {
      if (listRequest.current === controller) setListLoading(false);
    }
  }

  useEffect(() => {
    loadPage(1);
    // Leaving the page cancels the request (and StrictMode's first mount in development)
    return () => listRequest.current?.abort();
    // Only on mount (loadPage is a new function on every render). The rule also flags the loading state set here, on purpose
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!listError && focusBoardAfterRetry.current) boardTitle.current.focus();
    focusBoardAfterRetry.current = false;
  }, [listError]);

  async function handleSubmit(event) {
    event.preventDefault();
    // The button is only aria-disabled (it keeps the focus), Enter in the input also submits: one send at a time
    if (trip === 'sending') return;
    setTripId((id) => id + 1);

    const sentEmail = email.trim();
    if (!EMAIL_REGEX.test(sentEmail)) {
      setResult({ key: 'invalidEmail' });
      setTrip('rejected');
      return;
    }

    setResult(null);
    setTrip('sending');
    try {
      const { data } = await api.post('/email-requests', { email: sentEmail });
      setResult({ text: data.message, language });
      setTrip('sent');
      // Only if it still holds the address sent: something typed while it was on its way stays
      setEmail((current) => (current.trim() === sentEmail ? '' : current));
      loadPage(1);
    } catch (error) {
      setResult(requestError(error, language));
      // Without an answer the envelope never got to FastAPI: it comes back to React
      setTrip(error.response ? 'failed' : 'unreachable');
    }
  }

  const stop = TRIP_STOP[trip];
  const isError = trip === 'rejected' || trip === 'failed' || trip === 'unreachable';
  const resultText = noticeText(result);
  const listErrorText = noticeText(listError);
  // Always PAGE_SIZE rows, the empty ones stay blank like an unused line of a real board
  const rows = Array.from({ length: PAGE_SIZE }, (_, index) => requests?.[index] ?? null);
  const isEmpty = requests?.length === 0;
  // A full page means there may be older ones. The pager buttons are aria-disabled, so they check it themselves
  const hasNewer = !listLoading && page > 1;
  const hasOlder = !listLoading && requests?.length === PAGE_SIZE;

  return (
    <div className={styles.page}>
      {/* React 19 moves it to <head>: the tab title follows the language */}
      <title>{t('pageTitle')}</title>

      <header className={styles.header}>
        <span className={styles.wordmark}>
          FastAPI <span className={styles.amp}>&amp;</span> React
        </span>

        <div className={styles.controls}>
          <div className={styles.languages} role="group" aria-label={t('languageLabel')}>
            {LANGUAGES.map((option) => (
              <button
                key={option}
                type="button"
                className={styles.language}
                aria-pressed={language === option}
                onClick={() => setLanguage(option)}
              >
                {option.toUpperCase()}
              </button>
            ))}
          </div>
          <button
            type="button"
            className={styles.themeButton}
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? t('toLight') : t('toDark')}
          </button>
        </div>
      </header>

      <main>
        <section className={styles.hero}>
          <h1 className={styles.title}>{t('title')}</h1>

          <div className={styles.intro}>
            <p className={styles.lede}>{t('lede')}</p>

            {/* noValidate: the regex above validates, not the browser */}
            <form onSubmit={handleSubmit} noValidate>
              <label htmlFor="email" className={styles.label}>
                {t('destination')}
              </label>
              <div className={styles.field}>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder={t('emailPlaceholder')}
                  aria-invalid={trip === 'rejected' || undefined}
                  aria-describedby="email-result"
                  className={styles.input}
                />
                {/* Both labels take the same place, the button keeps the width of the longest one */}
                {/* aria-disabled instead of disabled: a disabled button loses the keyboard focus */}
                <button type="submit" aria-disabled={trip === 'sending'} className={styles.send}>
                  <span aria-hidden={trip === 'sending'}>{t('send')}</span>
                  <span aria-hidden={trip !== 'sending'}>{t('sending')}</span>
                </button>
              </div>
              <p id="email-result" className={styles.result} data-error={isError || undefined} aria-live="polite">
                {/* A new text on every attempt: the same error twice in a row is announced again */}
                <span key={tripId}>{resultText}</span>
                {trip === 'sent' && resultText && (
                  <>
                    {' · '}
                    <a href={MAILPIT_URL} target="_blank" rel="noreferrer">
                      {t('openMailpit')}
                    </a>
                  </>
                )}
              </p>
            </form>
          </div>
        </section>

        <section
          className={styles.route}
          data-trip={trip}
          data-error={isError || undefined}
          aria-label={t('routeLabel')}
        >
          <div className={styles.line} style={{ '--stop': stop }}>
            <ol className={styles.stations}>
              {STATIONS.map((station, index) => (
                <li
                  key={station.name}
                  className={styles.station}
                  style={{ '--i': index }}
                  data-lit={index <= stop || undefined}
                  data-failed={(isError && index === stop) || undefined}
                >
                  <span className={styles.dot} />
                  <span className={styles.stationName}>{station.name}</span>
                  <span className={styles.port}>:{station.port}</span>
                </li>
              ))}
            </ol>
            <span key={tripId} className={styles.packet}>
              <span className={styles.envelope}>
                <Envelope />
              </span>
            </span>
          </div>
        </section>

        <section className={styles.departures} aria-labelledby="departures-title">
          <div className={styles.boardHeader}>
            <h2 id="departures-title" ref={boardTitle} tabIndex={-1} className={styles.boardTitle}>
              {t('departures')}
            </h2>
            <div className={styles.pager}>
              <span className={styles.pageNumber}>{t('page', { page })}</span>
              <button
                type="button"
                className={styles.pageButton}
                aria-disabled={!hasNewer}
                onClick={() => hasNewer && loadPage(page - 1)}
              >
                {t('newer')}
              </button>
              <button
                type="button"
                className={styles.pageButton}
                aria-disabled={!hasOlder}
                onClick={() => hasOlder && loadPage(page + 1)}
              >
                {t('older')}
              </button>
            </div>
          </div>

          {listError && (
            <p className={styles.listError}>
              {/* A new alert on every failure: the same text in the same alert wouldn't be read again */}
              <span key={listError.attempt} role="alert">
                {t('loadError')}. {listErrorText && `${listErrorText}. `}
              </span>
              {/* The button stays the same element, so it keeps the focus while it retries */}
              <button
                type="button"
                className={styles.retry}
                aria-disabled={listLoading}
                onClick={() => {
                  if (listLoading) return;
                  focusBoardAfterRetry.current = true;
                  loadPage(listError.page);
                }}
              >
                {t('tryAgain')}
              </button>
            </p>
          )}

          <div className={styles.boardFrame} aria-busy={listLoading}>
            <table className={styles.board}>
              <colgroup>
                <col style={{ width: `${(ID_CELLS / (ID_CELLS + TIME_CELLS + EMAIL_CELLS)) * 100}%` }} />
                <col style={{ width: `${(TIME_CELLS / (ID_CELLS + TIME_CELLS + EMAIL_CELLS)) * 100}%` }} />
                <col />
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">{t('number')}</th>
                  <th scope="col">{t('time')}</th>
                  <th scope="col">{t('destination')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((request, index) => {
                  const delay = index * ROW_STAGGER_MS;

                  if (request) {
                    const date = new Date(request.created_at);
                    return (
                      <tr key={index}>
                        <td>
                          <span className="sr-only">{request.id}</span>
                          <SplitFlap text={String(request.id).padStart(ID_CELLS, '0')} length={ID_CELLS} delay={delay} />
                        </td>
                        <td>
                          <time dateTime={request.created_at} className="sr-only">
                            {date.toLocaleString(language, { dateStyle: 'medium', timeStyle: 'short' })}
                          </time>
                          <SplitFlap text={boardTime(date, language)} length={TIME_CELLS} delay={delay} />
                        </td>
                        <td>
                          <span className="sr-only">{request.email}</span>
                          <SplitFlap text={request.email} length={EMAIL_CELLS} delay={delay} />
                        </td>
                      </tr>
                    );
                  }

                  // First row of an empty board says so, the rest stay blank
                  const message = isEmpty && index === 0 ? (page === 1 ? t('empty') : t('noOlder')) : '';
                  return (
                    <tr key={index} aria-hidden={!message || undefined}>
                      <td>
                        <SplitFlap text="" length={ID_CELLS} delay={delay} />
                      </td>
                      <td>
                        <SplitFlap text="" length={TIME_CELLS} delay={delay} />
                      </td>
                      <td>
                        {message && <span className="sr-only">{message}</span>}
                        <SplitFlap text={message} length={EMAIL_CELLS} delay={delay} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <p>
          {t('builtBy')}{' '}
          <a href={`https://github.com/${GITHUB_USER}`} target="_blank" rel="noreferrer">
            @{GITHUB_USER}
          </a>
        </p>
        <p>
          {t('designBy')}{' '}
          <a href="https://claude.com/claude-code" target="_blank" rel="noreferrer">
            Claude Code
          </a>
        </p>
      </footer>
    </div>
  );
}
