import type { IconName } from "../types";

const paths: Record<IconName, JSX.Element> = {
  probe: <><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="2" /><path d="M10 10l5 5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" /></>,
  order: <><rect x="2" y="4" width="12" height="10" rx="2" fill="none" stroke="currentColor" strokeWidth="2" /><path d="M2 7h12" stroke="currentColor" strokeWidth="1.6" /></>,
  expand: <path d="M8 1l6 7h-4v7H6V8H2z" fill="currentColor" />,
  auto: <><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="3.2" strokeDasharray="2.4 1.8" /><circle cx="8" cy="8" r="2" fill="currentColor" /></>,
  lock: <><rect x="3" y="7" width="10" height="8" rx="2" fill="currentColor" /><path d="M5 7V5a3 3 0 016 0v2" fill="none" stroke="currentColor" strokeWidth="2" /></>,
  bolt: <path d="M9.5 0L2.5 9h5L6 16l7.5-10h-5l2-6z" fill="currentColor" />,
  battery: <><rect x="4" y="2.5" width="8" height="13" rx="2" fill="none" stroke="currentColor" strokeWidth="1.8" /><rect x="6" y="8" width="4" height="5.5" rx="1" fill="currentColor" /></>,
  sell: <path d="M3 13L13 3M6 3h7v7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />,
  pause: <><rect x="3" y="2" width="3.5" height="12" rx="1" fill="currentColor" /><rect x="9.5" y="2" width="3.5" height="12" rx="1" fill="currentColor" /></>,
  play: <path d="M4 2l10 6-10 6z" fill="currentColor" />,
  fast: <path d="M1 3l7 5-7 5zM8 3l7 5-7 5z" fill="currentColor" />,
  spark: <path d="M8 0l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" fill="currentColor" />,
  check: <><circle cx="8" cy="8" r="8" fill="currentColor" /><path d="M4.5 8.5L7 11l4.5-5.5" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" /></>,
  stats: <><rect x="1" y="9" width="3.5" height="6" rx="1" fill="currentColor" /><rect x="6.25" y="5" width="3.5" height="10" rx="1" fill="currentColor" /><rect x="11.5" y="1" width="3.5" height="14" rx="1" fill="currentColor" /></>,
};

export function Icon({ name, size = 16 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden>{paths[name]}</svg>;
}
