import { useTheme } from "@/features/shared/theme/ThemeProvider";
import styles from "@/features/shared/styles/ThemeToggle.module.css";

const ICONS = {
  dark: "🌙",
  light: "☀️",
  violet: "✨",
};

/**
 * Fixed button in the top-right corner that cycles through the themes.
 */
export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={toggleTheme}
      aria-label={`Switch theme (current: ${theme})`}
    >
      {ICONS[theme] ?? "🎨"}
    </button>
  );
}