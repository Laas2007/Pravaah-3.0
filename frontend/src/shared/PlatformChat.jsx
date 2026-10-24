import { useEffect, useRef, useState } from 'react'
import { req } from '../api'
import { useTr } from './lang'
import Icon from './Icon'

const post = (path, body) => req(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

/** JalaMitra on the Karnataka platforms: talks about the selected taluk (/api/core/chat) or Bengaluru ward (/api/chat). */
export default function PlatformChat({ platform, asOf, taluk, ward }) {
  const tr = useTr()
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef()
  const place = ward ? { kind: 'ward', idx: ward.idx, name: ward.name } : taluk ? { kind: 'taluk', idx: taluk.idx, name: taluk.name } : null
  const key = place ? `${place.kind}-${place.idx}-${tr.lang}` : 'none'

  useEffect(() => { setMsgs([]) }, [key])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  async function send(text) {
    if (!text.trim() || !place || busy) return
    const next = [...msgs, { role: 'user', content: text }]
    setMsgs(next)
    setInput('')
    setBusy(true)
    try {
      const body = { idx: place.idx, as_of: asOf, lang: tr.lang, messages: next.map(({ role, content }) => ({ role, content })) }
      const r = place.kind === 'ward' ? await post('/api/chat', body) : await post('/api/core/chat', { ...body, platform })
      setMsgs([...next, { role: 'assistant', content: r.text }])
    } catch (e) {
      setMsgs([...next, { role: 'assistant', content: `Error: ${e.message}` }])
    } finally {
      setBusy(false)
    }
  }

  const sugg = tr.lang === 'kn'
    ? ['ಇಲ್ಲಿ ನೀರಿನ ಕೊರತೆ ಏಕೆ?', 'ನಾನು ಏನು ಮಾಡಬಹುದು?', 'ಕೊರತೆ ಯಾವಾಗ?']
    : ['Why is there a shortage here?', 'What can I do?', 'How accurate is this?']

  if (!open) {
    return (
      <button className="chat-fab" onClick={() => setOpen(true)} data-tour="chat">
        <span className="fab-icon"><Icon name="chat" size={18} /></span>
        <span><b>{tr('Ask JalaMitra', 'ಜಲಮಿತ್ರನನ್ನು ಕೇಳಿ')}</b><small>English · ಕನ್ನಡ</small></span>
      </button>
    )
  }
  return (
    <div className="chat" data-tour="chat">
      <div className="chat-head">
        <div className="bot-avatar"><Icon name="drop" size={18} /></div>
        <div>
          <b>JalaMitra</b>
          <div className="small">{place ? place.name : tr('pick a taluk or ward', 'ತಾಲೂಕು ಅಥವಾ ವಾರ್ಡ್ ಆಯ್ಕೆಮಾಡಿ')} · {tr.lang === 'kn' ? 'ಕನ್ನಡ' : 'English'}</div>
        </div>
        <button className="x" onClick={() => setOpen(false)} aria-label="Close">×</button>
      </div>
      <div className="chat-body">
        {!place && <div className="msg bot">{tr('Click a taluk (or a Bengaluru ward) on the map, then ask me about it.', 'ನಕ್ಷೆಯಲ್ಲಿ ತಾಲೂಕು (ಅಥವಾ ಬೆಂಗಳೂರು ವಾರ್ಡ್) ಕ್ಲಿಕ್ ಮಾಡಿ, ನಂತರ ಕೇಳಿ.')}</div>}
        {place && <div className="msg bot">{tr(`Hi! Ask me about water in ${place.name}: why, when, or what you can do.`, `ನಮಸ್ಕಾರ! ${place.name} ನ ನೀರಿನ ಬಗ್ಗೆ ಕೇಳಿ: ಏಕೆ, ಯಾವಾಗ, ಅಥವಾ ನೀವು ಏನು ಮಾಡಬಹುದು.`)}</div>}
        {msgs.map((mm, i) => <div key={i} className={`msg ${mm.role === 'user' ? 'me' : 'bot'}`}>{mm.content}</div>)}
        {busy && <div className="msg bot typing"><i /><i /><i /></div>}
        {place && msgs.length === 0 && <div className="sugg">{sugg.map((s) => <button key={s} onClick={() => send(s)}>{s}</button>)}</div>}
        <div ref={end} />
      </div>
      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(input) }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} disabled={!place}
          placeholder={tr('Ask why, or what you can do…', 'ಏಕೆ ಅಥವಾ ಏನು ಮಾಡಬಹುದು ಎಂದು ಕೇಳಿ…')} />
        <button type="submit" disabled={!place || busy} aria-label="Send"><Icon name="send" size={18} /></button>
      </form>
    </div>
  )
}
