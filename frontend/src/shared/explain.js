// Plain-language reasons for the numbers shown in taluk and ward panels (English / Kannada via tr()).
import { DRIVER_TEXT } from './lang'

const HORIZON = 183
const fm = (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)} m`

/** Headline for a taluk's M2 forecast that matches its risk tier. */
export function talukHeadline(fc, tr) {
  const d = (x) => (x === 0 ? tr('now', 'ಈಗಲೇ') : tr(`${Math.round(x)} days`, `${Math.round(x)} ದಿನ`))
  if (fc.days_mid != null && fc.days_mid <= HORIZON) {
    return { big: d(fc.days_mid), label: fc.days_mid === 0 ? tr('groundwater is already at stress level', 'ಅಂತರ್ಜಲ ಈಗಾಗಲೇ ಒತ್ತಡ ಮಟ್ಟದಲ್ಲಿದೆ')
      : tr('until groundwater reaches stress level (likely forecast)', 'ಅಂತರ್ಜಲ ಒತ್ತಡ ಮಟ್ಟ ತಲುಪಲು (ಸಂಭಾವ್ಯ ಮುನ್ಸೂಚನೆ)') }
  }
  if (fc.days_low != null && fc.days_low <= HORIZON) {
    return { big: d(fc.days_low), label: tr('until stress if the coming months are dry (likely: beyond 6 months)',
      'ಮುಂದಿನ ತಿಂಗಳುಗಳು ಒಣಗಿದ್ದರೆ ಒತ್ತಡ ತಲುಪಲು (ಸಂಭಾವ್ಯ: 6 ತಿಂಗಳ ನಂತರ)') }
  }
  return { big: tr('6+ months', '6+ ತಿಂಗಳು'), label: tr('no stress expected within 6 months, even in a dry year',
    'ಒಣ ವರ್ಷದಲ್ಲೂ 6 ತಿಂಗಳೊಳಗೆ ಒತ್ತಡ ನಿರೀಕ್ಷೆ ಇಲ್ಲ') }
}

/** "Why this number?" bullets for a taluk (M2 forecast block from /api/core/taluk). */
export function talukReasons(fc, risk, tr) {
  const out = []
  const now = fc.anom_now_m
  const thr = fc.threshold_m
  if (now != null && thr != null) {
    const gap = thr - now
    out.push(gap <= 0
      ? tr(`Groundwater is now ${fm(now)} vs normal, already past this taluk's stress line (${thr.toFixed(1)} m deeper than normal = its driest 10% of months in 2014–21).`,
        `ಅಂತರ್ಜಲ ಈಗ ವಾಡಿಕೆಗಿಂತ ${fm(now)}, ಈ ತಾಲೂಕಿನ ಒತ್ತಡ ರೇಖೆಯನ್ನು (ವಾಡಿಕೆಗಿಂತ ${thr.toFixed(1)} ಮೀ. ಆಳ = 2014–21 ರ ಅತ್ಯಂತ ಒಣ 10% ತಿಂಗಳುಗಳು) ಈಗಾಗಲೇ ದಾಟಿದೆ.`)
      : tr(`Groundwater is now ${fm(now)} vs normal. This taluk's stress line is ${thr.toFixed(1)} m deeper than normal (its driest 10% of months in 2014–21), so it is ${gap.toFixed(1)} m away.`,
        `ಅಂತರ್ಜಲ ಈಗ ವಾಡಿಕೆಗಿಂತ ${fm(now)}. ಈ ತಾಲೂಕಿನ ಒತ್ತಡ ರೇಖೆ ವಾಡಿಕೆಗಿಂತ ${thr.toFixed(1)} ಮೀ. ಆಳ (2014–21 ರ ಅತ್ಯಂತ ಒಣ 10% ತಿಂಗಳುಗಳು); ಅಂತರ ${gap.toFixed(1)} ಮೀ.`))
  }
  const last = [...(fc.path || [])].reverse().find((p) => p.p50 != null)
  if (last) {
    out.push(tr(`By ${last.month} the likely forecast is ${fm(last.p50)} (dry year ${fm(last.p90)}, wet year ${fm(last.p10)}), from replaying the past 8 years' rain.`,
      `${last.month} ರ ವೇಳೆಗೆ ಸಂಭಾವ್ಯ ಮುನ್ಸೂಚನೆ ${fm(last.p50)} (ಒಣ ವರ್ಷ ${fm(last.p90)}, ಮಳೆಯ ವರ್ಷ ${fm(last.p10)}); ಹಿಂದಿನ 8 ವರ್ಷಗಳ ಮಳೆಯ ಆಧಾರದಲ್ಲಿ.`))
  }
  const mid = fc.days_mid, low = fc.days_low
  const rule = {
    critical: mid === 0
      ? tr('It is already at stress, so the risk is critical.', 'ಈಗಾಗಲೇ ಒತ್ತಡದಲ್ಲಿದೆ, ಆದ್ದರಿಂದ ಅಪಾಯ ಗಂಭೀರ.')
      : tr(`The likely forecast crosses the stress line in about ${Math.round(mid)} days (within 90), so the risk is critical.`,
        `ಸಂಭಾವ್ಯ ಮುನ್ಸೂಚನೆ ಸುಮಾರು ${Math.round(mid)} ದಿನಗಳಲ್ಲಿ (90 ರೊಳಗೆ) ಒತ್ತಡ ರೇಖೆ ದಾಟುತ್ತದೆ, ಆದ್ದರಿಂದ ಅಪಾಯ ಗಂಭೀರ.`),
    high: tr(`The likely forecast crosses the stress line in about ${Math.round(mid)} days (within 6 months), so the risk is high.`,
      `ಸಂಭಾವ್ಯ ಮುನ್ಸೂಚನೆ ಸುಮಾರು ${Math.round(mid)} ದಿನಗಳಲ್ಲಿ (6 ತಿಂಗಳೊಳಗೆ) ಒತ್ತಡ ರೇಖೆ ದಾಟುತ್ತದೆ, ಆದ್ದರಿಂದ ಅಪಾಯ ಹೆಚ್ಚು.`),
    medium: tr(`The likely forecast stays below the stress line for 6 months, but in a dry year it would cross in about ${Math.round(low)} days, so it is on the watch list (medium).`,
      `ಸಂಭಾವ್ಯ ಮುನ್ಸೂಚನೆ 6 ತಿಂಗಳು ಒತ್ತಡ ರೇಖೆಯ ಕೆಳಗಿರುತ್ತದೆ, ಆದರೆ ಒಣ ವರ್ಷದಲ್ಲಿ ಸುಮಾರು ${Math.round(low)} ದಿನಗಳಲ್ಲಿ ದಾಟುತ್ತದೆ; ಆದ್ದರಿಂದ ಎಚ್ಚರಿಕೆ ಪಟ್ಟಿಯಲ್ಲಿದೆ (ಮಧ್ಯಮ).`),
    low: tr('Even the dry-year forecast stays below the stress line for the next 6 months, so the risk is low.',
      'ಒಣ ವರ್ಷದ ಮುನ್ಸೂಚನೆಯೂ ಮುಂದಿನ 6 ತಿಂಗಳು ಒತ್ತಡ ರೇಖೆಯ ಕೆಳಗಿರುತ್ತದೆ, ಆದ್ದರಿಂದ ಅಪಾಯ ಕಡಿಮೆ.'),
  }[risk]
  if (rule) out.push(rule)
  const top = [...(fc.drivers || [])].sort((a, b) => Math.abs(b.metres) - Math.abs(a.metres))[0]
  if (top && Math.abs(top.metres) >= 0.05) {
    const lab = tr(DRIVER_TEXT[top.key]?.en || top.label, DRIVER_TEXT[top.key]?.kn)
    out.push(top.metres > 0
      ? tr(`Biggest factor: ${lab.toLowerCase()}; it makes groundwater ${top.metres.toFixed(1)} m deeper in 3 months.`,
        `ಮುಖ್ಯ ಅಂಶ: ${lab}; 3 ತಿಂಗಳಲ್ಲಿ ಅಂತರ್ಜಲವನ್ನು ${top.metres.toFixed(1)} ಮೀ. ಆಳಕ್ಕೆ ಇಳಿಸುತ್ತದೆ.`)
      : tr(`Biggest factor: ${lab.toLowerCase()}, but it is currently helping (${(-top.metres).toFixed(1)} m shallower in 3 months).`,
        `ಮುಖ್ಯ ಅಂಶ: ${lab}, ಆದರೆ ಸದ್ಯ ಸಹಾಯಕ (3 ತಿಂಗಳಲ್ಲಿ ${(-top.metres).toFixed(1)} ಮೀ. ಮೇಲೆ).`))
  }
  return out
}

/** "Why this number?" bullets for a Bengaluru ward (ward model, /api/urban/wards). */
export function wardReasons(w, tr) {
  const d = (x) => (x > 365 ? tr('more than a year', 'ಒಂದು ವರ್ಷಕ್ಕಿಂತ ಹೆಚ್ಚು') : x === 0 ? tr('now', 'ಈಗಲೇ') : tr(`${x} days`, `${x} ದಿನ`))
  const out = [
    tr(`Groundwater is at ${w.groundwater_pct}% of usable storage; borewells start failing below 30%.`,
      `ಅಂತರ್ಜಲ ಬಳಸಬಹುದಾದ ಸಂಗ್ರಹದ ${w.groundwater_pct}%; 30% ಕ್ಕಿಂತ ಕಡಿಮೆಯಾದರೆ ಕೊಳವೆಬಾವಿಗಳು ವಿಫಲವಾಗುತ್ತವೆ.`),
    w.days_mid === 0
      ? tr('It is already below that level, so the ward is in shortage now.', 'ಈಗಾಗಲೇ ಆ ಮಟ್ಟಕ್ಕಿಂತ ಕೆಳಗಿದೆ; ವಾರ್ಡ್ ಈಗ ಕೊರತೆಯಲ್ಲಿದೆ.')
      : tr(`The ward's water balance was re-run with 30 future rain and demand scenarios from past years: the middle one reaches 30% in ${d(w.days_mid)}, and half of them between ${d(w.days_low)} and ${d(w.days_high)}.`,
        `ಹಿಂದಿನ ವರ್ಷಗಳ 30 ಮಳೆ ಮತ್ತು ಬೇಡಿಕೆ ಸನ್ನಿವೇಶಗಳೊಂದಿಗೆ ವಾರ್ಡ್‌ನ ನೀರಿನ ಸಮತೋಲನ: ಮಧ್ಯದ ಸನ್ನಿವೇಶ ${d(w.days_mid)} ರಲ್ಲಿ 30% ತಲುಪುತ್ತದೆ; ಅರ್ಧದಷ್ಟು ${d(w.days_low)} ಮತ್ತು ${d(w.days_high)} ನಡುವೆ.`),
  ]
  const rule = {
    critical: tr('Shortage now or within 30 days, so critical.', 'ಈಗ ಅಥವಾ 30 ದಿನಗಳೊಳಗೆ ಕೊರತೆ: ಗಂಭೀರ.'),
    high: tr('Shortage expected within 31–90 days, so high.', '31–90 ದಿನಗಳಲ್ಲಿ ಕೊರತೆ: ಹೆಚ್ಚು.'),
    medium: tr('Shortage expected within 91–180 days, so medium.', '91–180 ದಿನಗಳಲ್ಲಿ ಕೊರತೆ: ಮಧ್ಯಮ.'),
    low: tr('No shortage expected within 180 days, so low.', '180 ದಿನಗಳೊಳಗೆ ಕೊರತೆ ನಿರೀಕ್ಷೆ ಇಲ್ಲ: ಕಡಿಮೆ.'),
  }[w.risk]
  if (rule) out.push(rule)
  out.push(tr('For the factors behind it (rain deficit, borewell dependence, density, IT load …), open the full ward view.',
    'ಇದರ ಹಿಂದಿನ ಅಂಶಗಳಿಗೆ (ಮಳೆ ಕೊರತೆ, ಕೊಳವೆಬಾವಿ ಅವಲಂಬನೆ, ಜನಸಾಂದ್ರತೆ …) ಪೂರ್ಣ ವಾರ್ಡ್ ವಿವರ ತೆರೆಯಿರಿ.'))
  return out
}
