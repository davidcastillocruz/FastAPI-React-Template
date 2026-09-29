import { useEffect, useRef } from "react";
import styles from "@/features/shared/styles/Cursor.module.css";

/**
 * Custom cursor that follows the pointer with smooth interpolation.
 *
 * Rendered as an SVG of the Python logo. The `hover` class is toggled
 * while the pointer is over interactive elements (links, buttons,
 * inputs, textareas), which enlarges and rotates the logo slightly.
 */
export default function Cursor() {
  const cursorRef = useRef(null);

  useEffect(() => {
    const cursor = cursorRef.current;
    if (!cursor) return;

    let targetX = -100;
    let targetY = -100;
    let currentX = -100;
    let currentY = -100;
    let rafId = null;
    let hasMoved = false;

    const tick = () => {
      const dx = targetX - currentX;
      const dy = targetY - currentY;

      currentX += dx * 0.22;
      currentY += dy * 0.22;

      cursor.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) translate(-50%, -50%)`;

      if (Math.hypot(dx, dy) < 0.1) {
        rafId = null;
        return;
      }
      rafId = requestAnimationFrame(tick);
    };

    const handleMove = (e) => {
      targetX = e.clientX;
      targetY = e.clientY;

      if (!hasMoved) {
        hasMoved = true;
        currentX = targetX;
        currentY = targetY;
        cursor.style.opacity = "1";
        cursor.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) translate(-50%, -50%)`;
      }

      if (!rafId) rafId = requestAnimationFrame(tick);
    };

    const INTERACTIVE = "a, button, input, textarea, [role='button']";
    const enter = () => cursor.classList.add(styles.hover);
    const leave = () => cursor.classList.remove(styles.hover);

    const attach = () => {
      document.querySelectorAll(INTERACTIVE).forEach((el) => {
        el.addEventListener("mouseenter", enter);
        el.addEventListener("mouseleave", leave);
      });
    };
    attach();

    // Re-attach when new interactive elements appear (route changes, etc.).
    const observer = new MutationObserver(attach);
    observer.observe(document.body, { childList: true, subtree: true });

    window.addEventListener("mousemove", handleMove);

    return () => {
      window.removeEventListener("mousemove", handleMove);
      if (rafId) cancelAnimationFrame(rafId);
      observer.disconnect();
      document.querySelectorAll(INTERACTIVE).forEach((el) => {
        el.removeEventListener("mouseenter", enter);
        el.removeEventListener("mouseleave", leave);
      });
    };
  }, []);

  return (
    <div ref={cursorRef} className={styles.cursor} aria-hidden="true">
      <svg viewBox="0 0 256 256" width="34" height="34">
        <path
          fill="#3776AB"
          d="M126.916.072c-64.832 0-60.784 28.115-60.784 28.115l.072 29.128h61.868v8.745H41.631S.145 61.355.145 126.77c0 65.417 36.21 63.097 36.21 63.097h21.61v-30.356s-1.165-36.21 35.632-36.21h61.362s34.475.557 34.475-33.319V33.97S194.67.072 126.916.072zM92.802 19.66a11.12 11.12 0 0 1 11.13 11.13 11.12 11.12 0 0 1-11.13 11.13 11.12 11.12 0 0 1-11.13-11.13 11.12 11.12 0 0 1 11.13-11.13z"
        />
        <path
          fill="#FFD43B"
          d="M128.757 255.935c64.832 0 60.784-28.115 60.784-28.115l-.072-29.127H127.6v-8.745h86.441s41.486 4.705 41.486-60.712c0-65.416-36.21-63.096-36.21-63.096h-21.61v30.355s1.165 36.21-35.632 36.21h-61.362s-34.475-.557-34.475 33.32v56.013s-5.235 33.897 62.518 33.897zm34.114-19.586a11.12 11.12 0 0 1-11.13-11.13 11.12 11.12 0 0 1 11.13-11.131 11.12 11.12 0 0 1 11.13 11.13 11.12 11.12 0 0 1-11.13 11.13z"
        />
      </svg>
    </div>
  );
}