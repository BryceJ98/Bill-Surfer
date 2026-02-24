"use client";
import { useTheme } from "@/lib/ThemeContext";

export default function SkiBackground() {
  const { ski } = useTheme();
  if (!ski) return null;

  return (
    <div
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1,
        pointerEvents: "none",
        overflow: "hidden",
      }}
    >
      {/* Mountain SVG — 3 depth layers */}
      <svg
        viewBox="0 0 1440 900"
        preserveAspectRatio="xMidYMax slice"
        xmlns="http://www.w3.org/2000/svg"
        style={{ position: "absolute", bottom: 0, width: "100%", height: "100%" }}
      >
        {/* Sky gradient */}
        <defs>
          <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#0D1B2E" />
            <stop offset="60%"  stopColor="#1A2D4A" />
            <stop offset="100%" stopColor="#2C4A6E" />
          </linearGradient>
          {/* Stars */}
          <radialGradient id="starGlow">
            <stop offset="0%"   stopColor="#ffffff" stopOpacity="1" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Sky fill */}
        <rect width="1440" height="900" fill="url(#skyGrad)" />

        {/* Stars */}
        {[
          [80,60],[150,30],[230,90],[320,20],[410,55],[510,15],[620,70],[720,35],
          [830,80],[940,25],[1050,60],[1160,40],[1280,75],[1380,20],[1420,55],
          [60,150],[200,120],[370,140],[550,110],[700,160],[900,130],[1100,150],
          [1300,120],[1440,100],[100,200],[450,180],[800,210],[1200,190],
        ].map(([cx, cy], i) => (
          <circle key={i} cx={cx} cy={cy} r={i % 5 === 0 ? 1.5 : 1}
                  fill="#fff" opacity={0.5 + (i % 4) * 0.1} />
        ))}

        {/* Moon */}
        <circle cx="1300" cy="80" r="28" fill="#EDE4D0" opacity="0.9" />
        <circle cx="1315" cy="70" r="24" fill="#1A2D4A" opacity="0.9" />

        {/* Far mountains — deepest layer, darkest */}
        <path
          d="M0 620 L80 480 L160 540 L260 380 L360 500 L450 420 L540 350 L630 450
             L720 360 L820 470 L900 390 L990 310 L1080 420 L1170 350 L1260 450
             L1350 370 L1440 430 L1440 900 L0 900 Z"
          fill="#1A2D4A"
          opacity="0.85"
        />
        {/* Far snow caps */}
        <path
          d="M260 380 L290 420 L230 425 Z
             M540 350 L570 390 L510 392 Z
             M720 360 L748 398 L692 400 Z
             M990 310 L1022 355 L960 357 Z
             M1170 350 L1198 388 L1142 390 Z"
          fill="#EDE4D0"
          opacity="0.7"
        />

        {/* Mid mountains — medium layer */}
        <path
          d="M0 700 L100 560 L200 620 L320 490 L430 580 L540 500 L640 440 L740 530
             L850 460 L950 400 L1050 490 L1150 420 L1250 510 L1350 450 L1440 520
             L1440 900 L0 900 Z"
          fill="#152235"
          opacity="0.9"
        />
        {/* Mid snow caps */}
        <path
          d="M320 490 L358 538 L282 542 Z
             M640 440 L676 486 L604 489 Z
             M950 400 L988 448 L912 451 Z
             M1250 510 L1282 550 L1218 553 Z"
          fill="#F0EAE0"
          opacity="0.8"
        />

        {/* Near mountains — closest, lightest to give depth */}
        <path
          d="M0 780 L150 650 L280 720 L420 600 L560 680 L680 610 L800 680 L920 590
             L1050 660 L1180 590 L1310 650 L1440 600 L1440 900 L0 900 Z"
          fill="#0F1C2D"
          opacity="0.95"
        />
        {/* Near snow caps */}
        <path
          d="M420 600 L462 652 L378 656 Z
             M680 610 L718 658 L642 661 Z
             M920 590 L960 640 L880 643 Z
             M1180 590 L1216 636 L1144 639 Z"
          fill="#FFFFFF"
          opacity="0.85"
        />

        {/* Ground / snow base */}
        <path
          d="M0 860 Q360 840 720 855 Q1080 870 1440 850 L1440 900 L0 900 Z"
          fill="#EDE4D0"
          opacity="0.15"
        />
      </svg>

      {/* Snowflakes */}
      <div className="ski-snow">
        {Array.from({ length: 20 }).map((_, i) => (
          <div key={i} className={`ski-flake ski-flake-${i}`}>❄</div>
        ))}
      </div>
    </div>
  );
}
