import type { ReactNode } from "react";

/** A plain card container (the 3D tilt effect was removed for a modest look). */
export function TiltCard({ children, className = "" }: { children: ReactNode; className?: string; max?: number }) {
  return <div className={className}>{children}</div>;
}
