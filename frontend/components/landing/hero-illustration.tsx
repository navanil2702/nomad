"use client";

import { motion } from "framer-motion";

/**
 * Hand-built SVG scene: layered ridges, a coastline, a route line with pins,
 * and a plane tracing an arc. Vector-only so it stays crisp and weighs nothing.
 */
export function HeroIllustration({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 520 420"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Illustration of a coastal route with mapped stops"
    >
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.16" />
          <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0.07" />
        </linearGradient>
        <linearGradient id="ridgeFar" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.42" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.16" />
        </linearGradient>
        <linearGradient id="ridgeNear" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.85" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.5" />
        </linearGradient>
        <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(200 80% 55%)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="hsl(200 80% 45%)" stopOpacity="0.14" />
        </linearGradient>
        <clipPath id="frame">
          <rect x="0" y="0" width="520" height="420" rx="36" />
        </clipPath>
      </defs>

      <g clipPath="url(#frame)">
        <rect width="520" height="420" fill="url(#sky)" />

        {/* sun */}
        <motion.circle
          cx="392"
          cy="104"
          r="38"
          fill="hsl(var(--accent))"
          fillOpacity="0.28"
          animate={{ r: [38, 41, 38] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        />
        <circle cx="392" cy="104" r="22" fill="hsl(var(--accent))" fillOpacity="0.55" />

        {/* clouds */}
        <motion.g
          animate={{ x: [0, 18, 0] }}
          transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
          opacity="0.5"
        >
          <ellipse cx="112" cy="86" rx="40" ry="15" fill="currentColor" className="text-background" />
          <ellipse cx="140" cy="78" rx="28" ry="17" fill="currentColor" className="text-background" />
        </motion.g>

        {/* far ridges */}
        <path
          d="M-20 250 L70 160 L128 214 L196 132 L268 226 L340 158 L420 232 L540 168 L540 420 L-20 420 Z"
          fill="url(#ridgeFar)"
        />
        {/* near ridges */}
        <path
          d="M-20 300 L64 224 L142 292 L226 210 L312 296 L392 240 L470 300 L540 254 L540 420 L-20 420 Z"
          fill="url(#ridgeNear)"
        />

        {/* sea */}
        <path d="M-20 342 L540 320 L540 420 L-20 420 Z" fill="url(#sea)" />
        {[0, 1, 2].map((i) => (
          <motion.path
            key={i}
            d={`M${40 + i * 150} ${372 + i * 14} q 22 -9 44 0 t 44 0`}
            stroke="hsl(200 80% 60%)"
            strokeOpacity="0.5"
            strokeWidth="2.5"
            strokeLinecap="round"
            animate={{ x: [0, 10, 0] }}
            transition={{
              duration: 4 + i,
              repeat: Infinity,
              ease: "easeInOut",
              delay: i * 0.4,
            }}
          />
        ))}

        {/* the route */}
        <motion.path
          d="M78 336 C 150 268, 214 330, 268 268 S 386 236, 448 176"
          stroke="hsl(var(--foreground))"
          strokeOpacity="0.5"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="7 9"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 2.2, ease: "easeInOut" }}
        />

        {/* pins */}
        {[
          [78, 336],
          [268, 268],
          [448, 176],
        ].map(([cx, cy], i) => (
          <motion.g
            key={i}
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 + i * 0.45, type: "spring", stiffness: 260 }}
          >
            <path
              d={`M${cx} ${cy - 26} a 11 11 0 0 1 11 11 c 0 8 -11 21 -11 21 s -11 -13 -11 -21 a 11 11 0 0 1 11 -11 z`}
              fill="hsl(var(--accent))"
            />
            <circle cx={cx} cy={cy - 15} r="4.2" fill="hsl(var(--background))" />
          </motion.g>
        ))}

        {/* plane */}
        <motion.g
          animate={{ x: [-40, 470], y: [180, 62] }}
          transition={{ duration: 9, repeat: Infinity, ease: "easeInOut", repeatType: "reverse" }}
        >
          <path
            d="M0 0 L26 8 L4 12 L-2 22 L-5 12 L-14 9 L-5 6 Z"
            fill="hsl(var(--foreground))"
            fillOpacity="0.72"
          />
        </motion.g>
      </g>

      <rect
        x="1"
        y="1"
        width="518"
        height="418"
        rx="35"
        stroke="hsl(var(--border))"
        strokeWidth="1.5"
      />
    </svg>
  );
}
