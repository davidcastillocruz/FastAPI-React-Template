import { Link } from "react-router-dom";

import Cursor from "@/features/shared/components/Cursor";
import ThemeToggle from "@/features/shared/components/ThemeToggle";

import styles from "./NotFound.module.css";

export default function NotFound() {
  return (
    <div className={styles.shell}>
      <Cursor />
      <ThemeToggle />

      <main className={styles.content}>
        <h1 className={styles.code}>404</h1>
        <p className={styles.text}>This page took a wrong turn somewhere.</p>
        <Link to="/" className={styles.link}>
          ← Back home
        </Link>
      </main>
    </div>
  );
}