// Full-color brand marks for self-host hardware vendors, sourced verbatim
// from Lobe Icons' "-color" variants -- see LICENSE in this directory.
// Unlike ../provider-logos (deliberately monochrome, tinted via
// currentColor to sit inside a text pill), these render each vendor's own
// brand colors directly: a themed fg color read as "too dark" for a bright
// green/orange/blue mark, and doesn't read as "the NVIDIA logo" the way the
// real color does.

import { useId } from "react";

export type LogoVendor = "nvidia" | "aws" | "googlecloud" | "azure" | "apple";

interface GradientStop {
  offset: string;
  color: string;
}

interface LinearGradient {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  stops: GradientStop[];
}

interface IconPath {
  d: string;
  /** A hex color, "currentColor" for marks with no fixed brand color
   *  (Apple's is genuinely monochrome), or a gradient definition. */
  fill: string | LinearGradient;
}

function isGradient(fill: IconPath["fill"]): fill is LinearGradient {
  return typeof fill !== "string";
}

const ICONS: Record<LogoVendor, IconPath[]> = {
  nvidia: [
    {
      d: "M10.212 8.976V7.62c.127-.01.256-.017.388-.021 3.596-.117 5.957 3.184 5.957 3.184s-2.548 3.647-5.282 3.647a3.227 3.227 0 01-1.063-.175v-4.109c1.4.174 1.681.812 2.523 2.258l1.873-1.627a4.905 4.905 0 00-3.67-1.846 6.594 6.594 0 00-.729.044m0-4.476v2.025c.13-.01.259-.019.388-.024 5.002-.174 8.261 4.226 8.261 4.226s-3.743 4.69-7.643 4.69c-.338 0-.675-.031-1.007-.092v1.25c.278.038.558.057.838.057 3.629 0 6.253-1.91 8.794-4.169.421.347 2.146 1.193 2.501 1.564-2.416 2.083-8.048 3.763-11.24 3.763-.308 0-.603-.02-.894-.048V19.5H24v-15H10.21zm0 9.756v1.068c-3.356-.616-4.287-4.21-4.287-4.21a7.173 7.173 0 014.287-2.138v1.172h-.005a3.182 3.182 0 00-2.502 1.178s.615 2.276 2.507 2.931m-5.961-3.3c1.436-1.935 3.604-3.148 5.961-3.336V6.523C5.81 6.887 2 10.723 2 10.723s2.158 6.427 8.21 7.015v-1.166C5.77 16 4.25 10.958 4.25 10.958h-.002z",
      fill: "#74B71B",
    },
  ],
  aws: [
    {
      // The "AWS" wordmark glyphs -- stays the ambient text color, same as
      // the official color mark, so only the smile below is brand-orange.
      d: "M6.763 11.212c0 .296.032.535.088.71.064.176.144.368.256.576.04.063.056.127.056.183 0 .08-.048.16-.152.24l-.503.335a.383.383 0 01-.208.072c-.08 0-.16-.04-.239-.112a2.47 2.47 0 01-.287-.375 6.18 6.18 0 01-.248-.471c-.622.734-1.405 1.101-2.347 1.101-.67 0-1.205-.191-1.596-.574-.39-.384-.59-.894-.59-1.533 0-.678.24-1.23.726-1.644.487-.415 1.133-.623 1.955-.623.272 0 .551.024.846.064.296.04.6.104.918.176v-.583c0-.607-.127-1.03-.375-1.277-.255-.248-.686-.367-1.3-.367-.28 0-.568.031-.863.103-.295.072-.583.16-.862.272-.09.04-.184.075-.28.104a.488.488 0 01-.127.023c-.112 0-.168-.08-.168-.247v-.391c0-.128.016-.224.056-.28a.597.597 0 01.224-.167 4.577 4.577 0 011.005-.36 4.84 4.84 0 011.246-.151c.95 0 1.644.216 2.091.647.44.43.662 1.085.662 1.963v2.586h.016zm-3.24 1.214c.263 0 .534-.048.822-.144a1.78 1.78 0 00.758-.51 1.27 1.27 0 00.272-.512c.047-.191.08-.423.08-.694v-.335a6.66 6.66 0 00-.735-.136 6.02 6.02 0 00-.75-.048c-.535 0-.926.104-1.19.32-.263.215-.39.518-.39.917 0 .375.095.655.295.846.191.2.47.296.838.296zm6.41.862c-.144 0-.24-.024-.304-.08-.064-.048-.12-.16-.168-.311L7.586 6.726a1.398 1.398 0 01-.072-.32c0-.128.064-.2.191-.2h.783c.151 0 .255.025.31.08.065.048.113.16.16.312l1.342 5.284 1.245-5.284c.04-.16.088-.264.151-.312a.549.549 0 01.32-.08h.638c.152 0 .256.025.32.08.063.048.12.16.151.312l1.261 5.348 1.381-5.348c.048-.16.104-.264.16-.312a.52.52 0 01.311-.08h.743c.127 0 .2.065.2.2 0 .04-.009.08-.017.128a1.137 1.137 0 01-.056.2l-1.923 6.17c-.048.16-.104.263-.168.311a.51.51 0 01-.303.08h-.687c-.15 0-.255-.024-.32-.08-.063-.056-.119-.16-.15-.32L12.32 7.747l-1.23 5.14c-.04.16-.087.264-.15.32-.065.056-.177.08-.32.08l-.686.001zm10.256.215c-.415 0-.83-.048-1.229-.143-.399-.096-.71-.2-.918-.32-.128-.071-.215-.151-.247-.223a.563.563 0 01-.048-.224v-.407c0-.167.064-.247.183-.247.048 0 .096.008.144.024.048.016.12.048.2.08.271.12.566.215.878.279.32.064.63.096.95.096.502 0 .894-.088 1.165-.264a.86.86 0 00.415-.758.777.777 0 00-.215-.559c-.144-.151-.416-.287-.807-.415l-1.157-.36c-.583-.183-1.014-.454-1.277-.813a1.902 1.902 0 01-.4-1.158c0-.335.073-.63.216-.886.144-.255.335-.479.575-.654.24-.184.51-.32.83-.415.32-.096.655-.136 1.006-.136.175 0 .36.008.535.032.183.024.35.056.518.088.16.04.312.08.455.127.144.048.256.096.336.144a.69.69 0 01.24.2.43.43 0 01.071.263v.375c0 .168-.064.256-.184.256a.83.83 0 01-.303-.096 3.652 3.652 0 00-1.532-.311c-.455 0-.815.071-1.062.223-.248.152-.375.383-.375.71 0 .224.08.416.24.567.16.152.454.304.877.44l1.134.358c.574.184.99.44 1.237.767.247.327.367.702.367 1.117 0 .343-.072.655-.207.926a2.157 2.157 0 01-.583.703c-.248.2-.543.343-.886.447-.36.111-.734.167-1.142.167z",
      fill: "currentColor",
    },
    {
      d: "M.378 15.475c3.384 1.963 7.56 3.153 11.877 3.153 2.914 0 6.114-.607 9.06-1.852.44-.2.814.287.383.607-2.626 1.94-6.442 2.969-9.722 2.969-4.598 0-8.74-1.7-11.87-4.526-.247-.223-.024-.527.272-.351zm23.531-.2c.287.36-.08 2.826-1.485 4.007-.215.184-.423.088-.327-.151l.175-.439c.343-.88.802-2.198.52-2.555-.336-.43-2.22-.207-3.074-.103-.255.032-.295-.192-.063-.36 1.5-1.053 3.967-.75 4.254-.399z",
      fill: "#FF9900",
    },
  ],
  googlecloud: [
    {
      d: "M15.961 7.327l2.086-2.086.14-.879C14.384.905 8.34 1.297 4.913 5.18A9.643 9.643 0 002.88 8.991l.747-.105 4.172-.688.322-.33c1.856-2.038 4.994-2.312 7.137-.578l.703.037z",
      fill: "#EA4335",
    },
    {
      d: "M21.02 8.93a9.399 9.399 0 00-2.834-4.568L15.258 7.29a5.204 5.204 0 011.91 4.129v.52a2.606 2.606 0 012.607 2.605c0 1.44-1.167 2.577-2.606 2.577h-5.22l-.512.556v3.126l.513.49h5.219c3.743.03 6.802-2.952 6.83-6.695a6.778 6.778 0 00-2.98-5.668z",
      fill: "#4285F4",
    },
    {
      d: "M6.738 21.293h5.212v-4.172H6.738c-.371 0-.731-.08-1.069-.234l-.74.227-2.1 2.086-.183.71a6.763 6.763 0 004.092 1.383z",
      fill: "#34A853",
    },
    {
      d: "M6.738 7.759A6.778 6.778 0 002.646 19.91l3.023-3.023a2.606 2.606 0 113.448-3.448l3.023-3.023a6.771 6.771 0 00-5.402-2.657z",
      fill: "#FBBC05",
    },
  ],
  azure: [
    {
      d: "M7.242 1.613A1.11 1.11 0 018.295.857h6.977L8.03 22.316a1.11 1.11 0 01-1.052.755h-5.43a1.11 1.11 0 01-1.053-1.466L7.242 1.613z",
      fill: { x1: 8.247, y1: 1.626, x2: 1.002, y2: 23.03, stops: [{ offset: "0", color: "#114A8B" }, { offset: "1", color: "#0669BC" }] },
    },
    {
      d: "M18.397 15.296H7.4a.51.51 0 00-.347.882l7.066 6.595c.206.192.477.298.758.298h6.226l-2.706-7.775z",
      fill: "#0078D4",
    },
    {
      d: "M17.193 1.613a1.11 1.11 0 00-1.052-.756h-7.81.035c.477 0 .9.304 1.052.756l6.748 19.992a1.11 1.11 0 01-1.052 1.466h-.12 7.895a1.11 1.11 0 001.052-1.466L17.193 1.613z",
      fill: { x1: 12.841, y1: 1.626, x2: 20.793, y2: 22.814, stops: [{ offset: "0", color: "#3CCBF4" }, { offset: "1", color: "#2892DF" }] },
    },
  ],
  // Apple's mark has no brand color -- black on light backgrounds, white on
  // dark, by design. currentColor is the *correct* "original color" here,
  // not a fallback.
  apple: [
    {
      d: "M11.932 6.908c.95 0 2.727-1.291 4.595-1.1.782.032 2.976.316 4.388 2.38-.113.069-2.622 1.528-2.593 4.565.034 3.617 3.166 4.828 3.221 4.85-.029.086-.506 1.723-1.658 3.416-1.002 1.463-2.039 2.919-3.675 2.95-1.606.03-2.125-.955-3.96-.955s-2.409.923-3.931.984c-1.581.06-2.78-1.58-3.79-3.037-2.065-2.98-3.64-8.422-1.527-12.087 1.051-1.824 2.93-2.98 4.969-3.009 1.549-.032 3.011 1.043 3.96 1.043zM16.552 0c.153 1.407-.411 2.817-1.251 3.833-.837 1.013-2.214 1.804-3.555 1.7-.185-1.378.495-2.814 1.27-3.712C13.883.805 15.346.05 16.553 0z",
      fill: "currentColor",
    },
  ],
};

// The single source of truth for "hardware vendors we have a real brand
// mark for" -- HardwareBadge keys off this instead of keeping its own copy.
export const KNOWN_HARDWARE_VENDORS: readonly LogoVendor[] = Object.keys(ICONS) as LogoVendor[];

// hardware_registry.py's vendor strings ("Google Cloud", "Microsoft Azure")
// don't collapse to an ICONS key by simply stripping whitespace, unlike the
// LLM provider names in provider-logos -- match on keyword instead.
export function resolveHardwareVendor(vendor: string): LogoVendor | null {
  const v = vendor.toLowerCase();
  if (v.includes("nvidia")) return "nvidia";
  if (v.includes("aws") || v.includes("amazon")) return "aws";
  if (v.includes("google")) return "googlecloud";
  if (v.includes("azure") || v.includes("microsoft")) return "azure";
  if (v.includes("apple")) return "apple";
  return null;
}

export interface HardwareLogoProps {
  vendor: string;
  size?: number;
  className?: string;
}

/** Renders null (caller falls back to a plain badge) for a vendor we don't
 *  have a mark for. */
export function HardwareLogo({ vendor, size = 14, className }: HardwareLogoProps) {
  // Radix renders every SelectItem for the whole options list at once, so
  // several HardwareLogo instances (e.g. four Azure rows) share one DOM --
  // a hardcoded gradient id would collide across them. useId keeps each
  // instance's gradient references unique.
  const uid = useId();
  const key = resolveHardwareVendor(vendor);
  const paths = key ? ICONS[key] : undefined;
  if (!paths) return null;

  const gradientPaths = paths
    .map((p, i) => ({ ...p, i }))
    .filter((p): p is { d: string; fill: LinearGradient; i: number } => isGradient(p.fill));

  return (
    <svg viewBox="0 0 24 24" width={size} height={size} className={className} aria-hidden="true">
      {gradientPaths.length > 0 && (
        <defs>
          {gradientPaths.map((p) => (
            <linearGradient
              key={p.i}
              id={`${uid}-hw-${p.i}`}
              gradientUnits="userSpaceOnUse"
              x1={p.fill.x1}
              y1={p.fill.y1}
              x2={p.fill.x2}
              y2={p.fill.y2}
            >
              {p.fill.stops.map((s) => (
                <stop key={s.offset} offset={s.offset} stopColor={s.color} />
              ))}
            </linearGradient>
          ))}
        </defs>
      )}
      {paths.map((p, i) => (
        <path key={i} d={p.d} fill={isGradient(p.fill) ? `url(#${uid}-hw-${i})` : p.fill} />
      ))}
    </svg>
  );
}
