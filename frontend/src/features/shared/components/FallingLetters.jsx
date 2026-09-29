import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import styles from "@/features/shared/styles/FallingLetters.module.css";

// Physics tuning for the falling characters.
const GRAVITY = 1500;
const FADE_SPEED = 0.85;
const VY_RANGE = [-460, -200];
const VX_RANGE = [-170, 170];
const VR_RANGE = [-280, 280];
const SCALE_SHRINK = 0.25;
const MAX_PARTICLES = 60;

/**
 * Fullscreen canvas that renders falling characters with simple physics.
 *
 * The parent emits particles through an imperative handle:
 *
 *   fallingRef.current.emit({ char: "o", x, y, color });
 *
 * A single `requestAnimationFrame` loop runs only while particles exist,
 * and pauses when the tab is hidden.
 */
const FallingLetters = forwardRef(function FallingLetters(_props, ref) {
  const canvasRef = useRef(null);
  const ctxRef = useRef(null);
  const particlesRef = useRef([]);
  const rafRef = useRef(null);
  const lastRef = useRef(0);
  const visibleRef = useRef(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctxRef.current = ctx;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    window.addEventListener("resize", resize);

    const onVisibility = () => {
      visibleRef.current = !document.hidden;
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  const start = () => {
    if (rafRef.current) return;
    lastRef.current = performance.now();
    rafRef.current = requestAnimationFrame(tick);
  };

  const tick = (time) => {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    if (!canvas || !ctx || !visibleRef.current) {
      rafRef.current = null;
      return;
    }

    // Cap dt so a backgrounded tab does not teleport the particles.
    const dt = Math.min((time - lastRef.current) / 1000, 0.05);
    lastRef.current = time;

    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

    const particles = particlesRef.current;
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];

      p.vy += GRAVITY * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.rotation += p.vr * dt;
      p.alpha -= FADE_SPEED * dt;

      if (p.alpha <= 0 || p.y > window.innerHeight + 80) {
        particles.splice(i, 1);
        continue;
      }

      const scale = 1 - (1 - p.alpha) * SCALE_SHRINK;

      ctx.save();
      ctx.globalAlpha = Math.max(0, p.alpha);
      ctx.translate(p.x, p.y);
      ctx.rotate((p.rotation * Math.PI) / 180);
      ctx.scale(scale, scale);
      ctx.fillStyle = p.color;
      ctx.font = '700 22px "Space Grotesk", system-ui, sans-serif';
      ctx.textBaseline = "middle";
      ctx.textAlign = "center";
      ctx.fillText(p.char, 0, 0);
      ctx.restore();
    }

    if (particles.length === 0) {
      rafRef.current = null;
      return;
    }
    rafRef.current = requestAnimationFrame(tick);
  };

  useImperativeHandle(ref, () => ({
    emit: ({ char, x, y, color }) => {
      if (!char || char === " ") return;
      if (particlesRef.current.length >= MAX_PARTICLES) return;
      particlesRef.current.push({
        char,
        x,
        y,
        vx: rand(VX_RANGE),
        vy: rand(VY_RANGE),
        rotation: (Math.random() - 0.5) * 20,
        vr: rand(VR_RANGE),
        alpha: 1,
        color: color || "#eaf1fb",
      });
      start();
    },
  }));

  return (
    <canvas ref={canvasRef} className={styles.canvas} aria-hidden="true" />
  );
});

function rand([min, max]) {
  return min + Math.random() * (max - min);
}

export default FallingLetters;