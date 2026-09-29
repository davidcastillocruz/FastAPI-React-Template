import { useEffect, useRef } from "react";
import Matter from "matter-js";
import styles from "@/features/shared/styles/FloatingLogos.module.css";

/**
 * Draggable, colliding tech logos with a pseudo-3D look.
 *
 * Physics run on Matter.js: each logo is a circular body that falls,
 * bounces, collides with the others and with the viewport edges, and can
 * be grabbed and thrown around.
 *
 * Rendering is done on a fullscreen canvas. Depth is faked with a scale
 * factor and a horizontal skew proportional to velocity.
 */

const LOGOS = [
  {
    id: "react",
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-11.5 -10.23174 23 20.46348" fill="none"><circle cx="0" cy="0" r="2.05" fill="#61dafb"/><g stroke="#61dafb" stroke-width="1"><ellipse rx="11" ry="4.2"/><ellipse rx="11" ry="4.2" transform="rotate(60)"/><ellipse rx="11" ry="4.2" transform="rotate(120)"/></g></svg>`,
    size: 120,
  },
  {
    id: "python",
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><path fill="#3776AB" d="M126.916.072c-64.832 0-60.784 28.115-60.784 28.115l.072 29.128h61.868v8.745H41.631S.145 61.355.145 126.77c0 65.417 36.21 63.097 36.21 63.097h21.61v-30.356s-1.165-36.21 35.632-36.21h61.362s34.475.557 34.475-33.319V33.97S194.67.072 126.916.072zM92.802 19.66a11.12 11.12 0 0 1 11.13 11.13 11.12 11.12 0 0 1-11.13 11.13 11.12 11.12 0 0 1-11.13-11.13 11.12 11.12 0 0 1 11.13-11.13z"/><path fill="#FFD43B" d="M128.757 255.935c64.832 0 60.784-28.115 60.784-28.115l-.072-29.127H127.6v-8.745h86.441s41.486 4.705 41.486-60.712c0-65.416-36.21-63.096-36.21-63.096h-21.61v30.355s1.165 36.21-35.632 36.21h-61.362s-34.475-.557-34.475 33.32v56.013s-5.235 33.897 62.518 33.897zm34.114-19.586a11.12 11.12 0 0 1-11.13-11.13 11.12 11.12 0 0 1 11.13-11.131 11.12 11.12 0 0 1 11.13 11.13 11.12 11.12 0 0 1-11.13 11.13z"/></svg>`,
    size: 130,
  },
  {
    id: "fastapi",
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2 4 13h6l-2 9 10-13h-6l2-7z" fill="#05c3a8"/></svg>`,
    size: 110,
  },
];

const WALL_THICKNESS = 200;

export default function FloatingLogos() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    let W = window.innerWidth;
    let H = window.innerHeight;

    const resizeCanvas = () => {
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = `${W}px`;
      canvas.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resizeCanvas();

    // Preload each SVG as an Image so canvas drawing is a plain blit.
    const images = {};
    LOGOS.forEach((logo) => {
      const img = new Image();
      const blob = new Blob([logo.svg], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      img.onload = () => {
        images[logo.id] = img;
        URL.revokeObjectURL(url);
      };
      img.src = url;
    });

    const { Engine, World, Bodies, Body, Composite, Mouse, MouseConstraint } =
      Matter;

    const engine = Engine.create({
      gravity: { x: 0, y: 1, scale: 0.0012 },
    });
    const world = engine.world;

    // Three static walls: floor, left and right. No ceiling, so the
    // logos can fall in from above.
    const walls = [
      Bodies.rectangle(W / 2, H + WALL_THICKNESS / 2, W, WALL_THICKNESS, {
        isStatic: true,
      }),
      Bodies.rectangle(-WALL_THICKNESS / 2, H / 2, WALL_THICKNESS, H * 2, {
        isStatic: true,
      }),
      Bodies.rectangle(
        W + WALL_THICKNESS / 2,
        H / 2,
        WALL_THICKNESS,
        H * 2,
        { isStatic: true }
      ),
    ];
    World.add(world, walls);

    const logos = LOGOS.map((logo, i) => {
      const radius = logo.size / 2;
      const x = W * (0.25 + i * 0.25) + (Math.random() - 0.5) * 80;
      const y = -radius - i * 80;

      const body = Bodies.circle(x, y, radius, {
        restitution: 0.55,
        friction: 0.02,
        frictionAir: 0.015,
        density: 0.0015,
      });

      body.plugin = {
        logo,
        depth: 0.75 + Math.random() * 0.5,
      };

      return body;
    });
    World.add(world, logos);

    const mouse = Mouse.create(canvas);
    mouse.pixelRatio = dpr;

    const mouseConstraint = MouseConstraint.create(engine, {
      mouse,
      constraint: {
        stiffness: 0.15,
        render: { visible: false },
      },
    });
    World.add(world, mouseConstraint);

    // Matter's MouseConstraint listens on the canvas only. If the user
    // releases the button outside the canvas, the constraint stays glued.
    // Force-release from a window-level listener.
    const forceRelease = () => {
      mouse.button = -1;
      mouseConstraint.constraint.bodyB = null;
      mouseConstraint.constraint.pointB = null;
      mouseConstraint.body = null;
    };
    window.addEventListener("mouseup", forceRelease);
    window.addEventListener("blur", forceRelease);

    // 30fps render loop, paused while the tab is hidden.
    let rafId = null;
    let lastTime = performance.now();
    let lastRenderTime = 0;
    const RENDER_INTERVAL = 1000 / 30;
    let isVisible = !document.hidden;

    const render = (time) => {
      rafId = requestAnimationFrame(render);

      if (!isVisible) return;
      if (time - lastRenderTime < RENDER_INTERVAL) return;
      lastRenderTime = time;

      const dt = Math.min(time - lastTime, 50);
      lastTime = time;

      Engine.update(engine, dt);
      ctx.clearRect(0, 0, W, H);

      // Draw farther logos first so closer ones overlap them.
      const sorted = [...logos].sort(
        (a, b) => a.plugin.depth - b.plugin.depth
      );

      for (const body of sorted) {
        const { logo, depth } = body.plugin;
        const img = images[logo.id];
        if (!img) continue;

        const { x, y } = body.position;
        const angle = body.angle;
        const vx = body.velocity.x;

        const depthScale = 0.7 + depth * 0.4;
        const size = logo.size * depthScale;
        const skew = Math.max(-0.25, Math.min(0.25, vx * 0.004));

        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(angle);
        ctx.transform(1, 0, skew, 1, 0, 0);
        ctx.globalAlpha = 0.5 + depth * 0.35;
        ctx.drawImage(img, -size / 2, -size / 2, size, size);
        ctx.restore();
      }
    };

    rafId = requestAnimationFrame(render);

    const handleVisibility = () => {
      isVisible = !document.hidden;
      if (isVisible) {
        lastTime = performance.now();
        lastRenderTime = 0;
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    const handleResize = () => {
      resizeCanvas();
      Body.setPosition(walls[0], { x: W / 2, y: H + WALL_THICKNESS / 2 });
      Body.setPosition(walls[1], { x: -WALL_THICKNESS / 2, y: H / 2 });
      Body.setPosition(walls[2], { x: W + WALL_THICKNESS / 2, y: H / 2 });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener("resize", handleResize);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("mouseup", forceRelease);
      window.removeEventListener("blur", forceRelease);
      World.clear(world, false);
      Engine.clear(engine);
      Mouse.clearSourceEvents(mouse);
      Composite.clear(world, false, true);
    };
  }, []);

  return <canvas ref={canvasRef} className={styles.canvas} aria-hidden="true" />;
}