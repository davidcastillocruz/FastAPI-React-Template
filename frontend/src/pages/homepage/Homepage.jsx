import { useEffect, useRef, useState } from "react";

import api from "@/services/api";

import Cursor from "@/features/shared/components/Cursor";
import FallingLetters from "@/features/shared/components/FallingLetters";
import FloatingLogos from "@/features/shared/components/FloatingLogos";
import ThemeToggle from "@/features/shared/components/ThemeToggle";

import styles from "./Homepage.module.css";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Return the substring removed between two versions of a string and the
 * index where the change started. Used to decide which characters to
 * animate when the user edits the input.
 */
function diffChars(oldValue, newValue) {
  let start = 0;
  while (
    start < oldValue.length &&
    start < newValue.length &&
    oldValue[start] === newValue[start]
  ) {
    start++;
  }

  let endOld = oldValue.length;
  let endNew = newValue.length;
  while (
    endOld > start &&
    endNew > start &&
    oldValue[endOld - 1] === newValue[endNew - 1]
  ) {
    endOld--;
    endNew--;
  }

  return {
    removed: oldValue.slice(start, endOld),
    inserted: newValue.slice(start, endNew),
    position: start,
  };
}

export default function Homepage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [message, setMessage] = useState("");

  const shellRef = useRef(null);
  const inputRef = useRef(null);
  const mirrorRef = useRef(null);
  const wrapRef = useRef(null);
  const fallingRef = useRef(null);

  // Parallax + spotlight for the background decorations.
  useEffect(() => {
    const shell = shellRef.current;
    if (!shell) return;

    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;
    let currentX = targetX;
    let currentY = targetY;
    let rafId = null;

    const tick = () => {
      const dx = targetX - currentX;
      const dy = targetY - currentY;

      currentX += dx * 0.12;
      currentY += dy * 0.12;

      shell.style.setProperty("--mouse-x", `${currentX}px`);
      shell.style.setProperty("--mouse-y", `${currentY}px`);

      const nx = (currentX / window.innerWidth) * 2 - 1;
      const ny = (currentY / window.innerHeight) * 2 - 1;
      shell.style.setProperty("--mouse-nx", nx.toFixed(3));
      shell.style.setProperty("--mouse-ny", ny.toFixed(3));

      if (Math.hypot(dx, dy) < 0.5) {
        rafId = null;
        return;
      }
      rafId = requestAnimationFrame(tick);
    };

    const handleMove = (e) => {
      targetX = e.clientX;
      targetY = e.clientY;
      if (!rafId) rafId = requestAnimationFrame(tick);
    };

    window.addEventListener("mousemove", handleMove);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, []);

  /**
   * Move the caret-follow glow and return the caret's x offset (relative
   * to the input's padding box).
   *
   * A hidden mirror span with the same font and padding as the input
   * measures the text width, which maps directly to the caret position.
   */
  const updateCaretGlow = (value) => {
    const mirror = mirrorRef.current;
    const wrap = wrapRef.current;
    const input = inputRef.current;
    if (!mirror || !wrap || !input) return null;

    mirror.textContent = value || "";

    const mirrorStyle = getComputedStyle(mirror);
    const paddingLeft = parseFloat(mirrorStyle.paddingLeft) || 14;
    const paddingRight = parseFloat(mirrorStyle.paddingRight) || 14;

    const textWidth = Math.max(
      0,
      mirror.offsetWidth - paddingLeft - paddingRight
    );
    const caretFromPadding = paddingLeft + textWidth;
    const maxCaret = input.clientWidth - paddingRight;
    const caretX = Math.min(caretFromPadding, maxCaret);

    wrap.style.setProperty("--caret-x", `${caretX}px`);
    return caretX;
  };

  const handleChange = (e) => {
    const value = e.target.value;
    const oldValue = email;

    setEmail(value);
    if (status !== "loading") setStatus("idle");

    const caretX = updateCaretGlow(value);

    // Emit a falling particle for every character that was deleted.
    const { removed } = diffChars(oldValue, value);
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (
      !prefersReducedMotion &&
      removed &&
      caretX != null &&
      fallingRef.current
    ) {
      const input = inputRef.current;
      if (input) {
        const rect = input.getBoundingClientRect();
        const computed = getComputedStyle(input);
        const color = computed.color;
        const borderLeft = parseFloat(computed.borderLeftWidth) || 0;
        const y = rect.top + rect.height / 2;
        const baseX = rect.left + borderLeft + caretX;

        Array.from(removed).forEach((char, i) => {
          fallingRef.current.emit({
            char,
            x: baseX + i * 8 + (Math.random() - 0.5) * 6,
            y,
            color,
          });
        });
      }
    }

    // Restart the border pulse by toggling the class and forcing a reflow.
    const input = inputRef.current;
    if (input) {
      input.classList.remove(styles.typing);
      void input.offsetWidth;
      input.classList.add(styles.typing);
    }
  };

  const handleTypingAnimationEnd = () => {
    inputRef.current?.classList.remove(styles.typing);
  };

  useEffect(() => {
    updateCaretGlow("");
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const value = email.trim();

    if (!EMAIL_REGEX.test(value)) {
      setStatus("error");
      setMessage("Please enter a valid email, e.g. name@domain.com");
      return;
    }

    setStatus("loading");
    setMessage("");

    try {
      const { data } = await api.post("/email-request", { email: value });
      setStatus("success");
      setMessage(data?.message ?? "Done. We have your email.");
      setEmail("");
      updateCaretGlow("");
    } catch (err) {
      setStatus("error");
      const detail = err?.data?.detail ?? err?.message;
      setMessage(detail ?? "Something went wrong. Please try again.");
    }
  };

  return (
    <div className={styles.shell} ref={shellRef}>
      <Cursor />
      <FloatingLogos />

      <div className={styles.bgDecor} aria-hidden="true">
        <div className={styles.bgGrid} />
        <div className={`${styles.bgOrb} ${styles.bgOrbGreen}`} />
        <div className={`${styles.bgOrb} ${styles.bgOrbBlue}`} />
        <div className={`${styles.bgOrb} ${styles.bgOrbPurple}`} />
      </div>

      <div className={styles.mouseGlow} aria-hidden="true" />

      <ThemeToggle />

      <main className={styles.page}>
        <FallingLetters ref={fallingRef} />

        <div className={styles.hero}>
          <h1 className={styles.title}>
            <span className={styles.titleFastapi}>FastAPI</span>
            <span className={styles.titlePlus}>+</span>
            <span className={styles.titleReact}>React</span>
          </h1>

          <p className={styles.subtitle}>
            A ready-to-go template: fast backend, clean frontend, everything
            wired up from the first commit.
          </p>

          <form className={styles.card} onSubmit={handleSubmit} noValidate>
            <label className={styles.label} htmlFor="email">
              Your email
            </label>

            <div className={styles.field}>
              <div className={styles.inputWrap} ref={wrapRef}>
                <input
                  id="email"
                  ref={inputRef}
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  placeholder="name@domain.com"
                  value={email}
                  onChange={handleChange}
                  onAnimationEnd={handleTypingAnimationEnd}
                  aria-invalid={status === "error"}
                  aria-describedby="feedback"
                  disabled={status === "loading"}
                  className={styles.input}
                />
                <span
                  ref={mirrorRef}
                  className={styles.inputMirror}
                  aria-hidden="true"
                />
                <span className={styles.inputGlow} aria-hidden="true" />
              </div>

              <button
                type="submit"
                disabled={status === "loading"}
                className={styles.button}
              >
                {status === "loading" ? "Sending…" : "Send"}
              </button>
            </div>

            <p
              id="feedback"
              className={[
                styles.feedback,
                status === "error" ? styles.error : "",
                status === "success" ? styles.success : "",
              ].join(" ")}
              role="status"
              aria-live="polite"
            >
              {message}
            </p>
          </form>
        </div>
      </main>

      <footer className={styles.credits}>
        <span>Made by</span>
        <a
          href="https://github.com/davidcastillocruz"
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true">
            <path
              fill="currentColor"
              d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"
            />
          </svg>
          davidcastillocruz
        </a>
      </footer>
    </div>
  );
}