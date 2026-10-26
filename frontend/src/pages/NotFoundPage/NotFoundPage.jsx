import { Link, useLocation } from 'react-router';

import SplitFlap from '@/components/SplitFlap/SplitFlap';
import { useT } from '@/languages/useT';

import styles from './NotFoundPageStyle.module.css';
import translations from './NotFoundPageTranslation.json';

// "404 CANCELLED" and "404 CANCELADO" fill the row exactly
const BOARD_CELLS = 13;

// Any route that doesn't exist: a departure cancelled on the board
export default function NotFoundPage() {
  const t = useT(translations);
  const { pathname } = useLocation();
  const board = `404 ${t('status')}`;

  return (
    <main className={styles.page}>
      <title>{t('pageTitle')}</title>

      <div className={styles.board}>
        <span className="sr-only">{board}</span>
        <SplitFlap text={board} length={BOARD_CELLS} />
      </div>

      <h1 className={styles.title}>{t('title')}</h1>
      <p className={styles.text}>{t('text', { path: pathname })}</p>
      <Link to="/" className={styles.back}>
        {t('back')}
      </Link>
    </main>
  );
}
