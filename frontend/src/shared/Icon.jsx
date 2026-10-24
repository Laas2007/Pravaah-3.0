// Small stroke icons drawn for Pravaah (24x24 grid, currentColor). Use instead of emoji.
const PATHS = {
  drop: 'M12 3.5c-3.2 4.1-6 7.6-6 10.8a6 6 0 0 0 12 0c0-3.2-2.8-6.7-6-10.8z',
  crop: 'M12 21V9M12 13c-3.5 0-5.5-2-5.5-5.5C10 7.5 12 9.5 12 13zM12 11c3.5 0 5.5-2 5.5-5.5C14 5.5 12 7.5 12 11zM5 21h14',
  city: 'M3 21h18M5 21V10l5-3v14M10 21V4h9v17M13 8h3M13 12h3M13 16h3',
  factory: 'M3 21V11l5 3v-3l5 3v-3l5 3V5h3v16zM7 18h2M12 18h2M17 18h2',
  play: 'M8 5.5v13l10.5-6.5z',
  pause: 'M8 5v14M16 5v14',
  globe: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3.5 9h17M3.5 15h17M12 3c2.5 2.6 3.7 5.6 3.7 9s-1.2 6.4-3.7 9c-2.5-2.6-3.7-5.6-3.7-9S9.5 5.6 12 3z',
  calendar: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4',
  pin: 'M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11zM12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z',
  close: 'M6 6l12 12M18 6L6 18',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  chat: 'M4 5h16v11H9l-5 4z',
  send: 'M4 12l16-7-6 16-3-6.5z',
  search: 'M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13zM15.5 15.5L20 20',
  back: 'M9 7L4 12l5 5M4 12h11a5 5 0 0 1 0 10',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  alert: 'M12 4L2.5 20h19zM12 10v4.5M12 17.5v.5',
}

export default function Icon({ name, size = 18, stroke = 1.8, className = '', title }) {
  const filled = name === 'play'
  return (
    <svg className={`icon ${className}`} width={size} height={size} viewBox="0 0 24 24" aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined} fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={stroke}
      strokeLinecap="round" strokeLinejoin="round">
      {title && <title>{title}</title>}
      <path d={PATHS[name]} />
    </svg>
  )
}
