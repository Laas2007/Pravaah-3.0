// M3 crop advisor: crops ranked by rainfed yield risk, irrigation schedule and sowing planner for the chosen crop.
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useLoad } from '../../shared/hooks'
import { useTr } from '../../shared/lang'
import { platform } from '../../shared/platforms'
import { ErrorBox, Loading } from '../../shared/ui'
import { agriApi } from './api'

const COLOR = platform('agri').color
const VERDICT = {
  'good rainfed': ['✅', 'ಮಳೆಯಾಶ್ರಿತಕ್ಕೆ ಸೂಕ್ತ'],
  'ok rainfed, risky in a dry year': ['🟡', 'ಮಳೆಯಾಶ್ರಿತ ಸಾಧ್ಯ, ಒಣ ವರ್ಷದಲ್ಲಿ ಅಪಾಯ'],
  'needs irrigation': ['💧', 'ನೀರಾವರಿ ಬೇಕು'],
  'avoid without assured irrigation': ['⛔', 'ಖಚಿತ ನೀರಾವರಿ ಇಲ್ಲದೆ ಬೇಡ'],
}
const SEASON_KN = { kharif: 'ಮುಂಗಾರು', rabi: 'ಹಿಂಗಾರು', summer: 'ಬೇಸಿಗೆ' }

export default function CropAdvisor({ idx, asOf }) {
  const tr = useTr()
  const { data: o, error } = useLoad(() => agriApi.crops(idx, asOf), [idx, asOf])
  const [pick, setPick] = useState(null)
  if (error) return <ErrorBox error={error} />
  if (!o) return <Loading what="crop outlook" />
  const crop = pick && o.crops.some((c) => c.crop === pick) ? pick : o.crops[0]?.crop
  return (
    <div className="ps-card" data-tour="crops">
      <h2>🌱 {tr('Which crop this season?', 'ಈ ಋತುವಿಗೆ ಯಾವ ಬೆಳೆ?')}</h2>
      <div className="muted small">
        {tr(`${o.season} season, sowing around ${o.sowing_date}. Ranked by rainfed yield risk from a FAO-56 crop water balance on real IMD rain and ERA5 evaporation; the rest of the season replays the past ${o.scenarios} years' rain.`,
          `${SEASON_KN[o.season] || o.season} ಋತು, ಬಿತ್ತನೆ ಸುಮಾರು ${o.sowing_date}. ನೈಜ IMD ಮಳೆ ಮತ್ತು ERA5 ಆವಿಯಾಗುವಿಕೆಯ ಮೇಲೆ FAO-56 ಬೆಳೆ ನೀರಿನ ಸಮತೋಲನದಿಂದ ಮಳೆಯಾಶ್ರಿತ ಇಳುವರಿ ಅಪಾಯದ ಶ್ರೇಣಿ; ಉಳಿದ ಋತುವಿಗೆ ಹಿಂದಿನ ${o.scenarios} ವರ್ಷಗಳ ಮಳೆ.`)}
      </div>
      <table className="ps-table" style={{ marginTop: 10 }}>
        <thead><tr><th>{tr('Crop', 'ಬೆಳೆ')}</th><th>{tr('Water need', 'ನೀರಿನ ಅಗತ್ಯ')}</th>
          <th>{tr('Rainfed yield loss', 'ಮಳೆಯಾಶ್ರಿತ ಇಳುವರಿ ನಷ್ಟ')}</th><th>{tr('Irrigation', 'ನೀರಾವರಿ')}</th></tr></thead>
        <tbody>
          {o.crops.map((c) => {
            const l = c.yield_loss_rainfed_pct
            const v = VERDICT[c.verdict] || ['', c.verdict]
            return (
              <tr key={c.crop} onClick={() => setPick(c.crop)} className={c.crop === crop ? 'sel' : ''}>
                <td><b>{tr(c.crop, c.kn)}</b><div className="muted small">{v[0]} {tr(c.verdict, v[1])}</div></td>
                <td>{c.water_need_mm} mm<div className="muted small">{tr(`${c.days} days`, `${c.days} ದಿನ`)}</div></td>
                <td><b>{Math.round(l.p50)}%</b><div className="muted small">{tr('dry year', 'ಒಣ ವರ್ಷ')} {Math.round(l.p90)}%</div></td>
                <td>{c.irrigation_need_mm} mm</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div className="muted small" style={{ marginTop: 6 }}>{tr('Yield loss = FAO-33 yield response to water shortfall, for a crop grown on rain alone. Soil water and sowing date are estimates. Click a crop for its irrigation plan.',
        'ಇಳುವರಿ ನಷ್ಟ = ಮಳೆಯಾಶ್ರಿತ ಬೆಳೆಗೆ ನೀರಿನ ಕೊರತೆಯ FAO-33 ಪ್ರತಿಕ್ರಿಯೆ. ಮಣ್ಣಿನ ನೀರು ಮತ್ತು ಬಿತ್ತನೆ ದಿನಾಂಕ ಅಂದಾಜು. ನೀರಾವರಿ ಯೋಜನೆಗೆ ಬೆಳೆ ಕ್ಲಿಕ್ ಮಾಡಿ.')}</div>
      {crop && <CropPlan idx={idx} crop={crop} asOf={asOf} kn={o.crops.find((c) => c.crop === crop)?.kn} />}
    </div>
  )
}

function CropPlan({ idx, crop, asOf, kn }) {
  const tr = useTr()
  const irr = useLoad(() => agriApi.irrigation(idx, crop, asOf), [idx, crop, asOf]).data
  const sow = useLoad(() => agriApi.sowing(idx, crop, asOf), [idx, crop, asOf]).data
  const best = sow?.weeks?.length ? [...sow.weeks].sort((a, b) => a.loss_p50 + a.loss_p90 / 2 - (b.loss_p50 + b.loss_p90 / 2))[0] : null
  return (
    <>
      <h3>💧 {tr(`Irrigation plan: ${crop}`, `ನೀರಾವರಿ ಯೋಜನೆ: ${kn || crop}`)}</h3>
      {!irr ? <Loading what="irrigation plan" /> : irr.events.length === 0
        ? <div className="ps-note">{tr('No irrigation needed in a typical year: rain keeps the root zone above the stress limit.', 'ಸಾಮಾನ್ಯ ವರ್ಷದಲ್ಲಿ ನೀರಾವರಿ ಬೇಕಿಲ್ಲ.')}</div>
        : <>
          <div className="ps-stats">
            <div className="ps-stat"><div className="ps-stat-label">{tr('Next irrigation', 'ಮುಂದಿನ ನೀರಾವರಿ')}</div>
              <div className="ps-stat-value" style={{ fontSize: 18 }}>{irr.next ? irr.next.date : tr('none left', 'ಇಲ್ಲ')}</div>
              <div className="ps-stat-sub">{irr.next ? `${irr.next.mm} mm` : ''}</div></div>
            <div className="ps-stat"><div className="ps-stat-label">{tr('Season total', 'ಋತುವಿನ ಒಟ್ಟು')}</div>
              <div className="ps-stat-value">{irr.total_mm}<span>mm</span></div>
              <div className="ps-stat-sub">{tr(`≈ ${(irr.litres_per_acre / 1e5).toFixed(1)} lakh litres per acre`, `≈ ಎಕರೆಗೆ ${(irr.litres_per_acre / 1e5).toFixed(1)} ಲಕ್ಷ ಲೀಟರ್`)}</div></div>
          </div>
          <div className="ps-chips">{irr.events.map((e) => <span key={e.date} className={e.date >= asOf ? 'up' : ''}>{e.date} · {e.mm} mm</span>)}</div>
          <div className="muted small">{tr('Typical-rain scenario; apply when the root zone has dried to the crop\'s stress limit.', 'ಸಾಮಾನ್ಯ ಮಳೆಯ ಸನ್ನಿವೇಶ; ಬೇರು ವಲಯ ಒತ್ತಡ ಮಿತಿಗೆ ಒಣಗಿದಾಗ ನೀರು ಹಾಯಿಸಿ.')}</div>
        </>}
      <h3>📅 {tr('Best sowing week (rainfed)', 'ಉತ್ತಮ ಬಿತ್ತನೆ ವಾರ (ಮಳೆಯಾಶ್ರಿತ)')}</h3>
      {!sow ? <Loading what="sowing planner" /> : (
        <>
          <div style={{ height: 150 }}>
            <ResponsiveContainer>
              <BarChart data={sow.weeks} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#eef1f5" vertical={false} />
                <XAxis dataKey="sowing_date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} unit="%" />
                <Tooltip formatter={(v) => `${v}%`} />
                <Bar dataKey="loss_p50" name={tr('typical loss', 'ಸಾಮಾನ್ಯ ನಷ್ಟ')} fill={COLOR} isAnimationActive={false} />
                <Bar dataKey="loss_p90" name={tr('dry-year loss', 'ಒಣ ವರ್ಷದ ನಷ್ಟ')} fill="#d8b365" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {best && <div className="ps-note">{tr(`Lowest risk: sow around ${best.sowing_date} (typical loss ${best.loss_p50}%, dry year ${best.loss_p90}%).`,
            `ಕಡಿಮೆ ಅಪಾಯ: ಸುಮಾರು ${best.sowing_date} ರಂದು ಬಿತ್ತನೆ (ಸಾಮಾನ್ಯ ನಷ್ಟ ${best.loss_p50}%, ಒಣ ವರ್ಷ ${best.loss_p90}%).`)}</div>}
        </>
      )}
    </>
  )
}
