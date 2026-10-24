import { useEffect, useRef, useState } from 'react'
import { api } from './api'

export default function Chat({ ward, asOf, lang, t, open, setOpen, autoAsk, clearAutoAsk }) {
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef()

  useEffect(() => { setMsgs([]) }, [ward?.idx, lang])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  // the guided tour can pose a question on the visitor's behalf
  useEffect(() => {
    if (open && ward && autoAsk && msgs.length === 0 && !busy) {
      const h = setTimeout(() => { send(autoAsk); clearAutoAsk() }, 600)
      return () => clearTimeout(h)
    }
  }) // eslint-disable-line react-hooks/exhaustive-deps

  async function send(text) {
    if (!text.trim() || !ward || busy) return
    const next = [...msgs, { role: 'user', content: text }]
    setMsgs(next)
    setInput('')
    setBusy(true)
    try {
      const r = await api.chat({ idx: ward.idx, as_of: asOf, lang, messages: next.map(({ role, content }) => ({ role, content })) })
      setMsgs([...next, { role: 'assistant', content: r.text, source: r.source }])
    } catch (e) {
      setMsgs([...next, { role: 'assistant', content: `Error: ${e.message}` }])
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button className="chat-fab" onClick={() => setOpen(true)} data-tour="chat">
        <span className="fab-icon">💬</span>
        <span><b>{t.ask}</b><small>English · ಕನ್ನಡ</small></span>
      </button>
    )
  }
  return (
    <div className="chat" data-tour="chat">
      <div className="chat-head">
        <div className="bot-avatar">💧</div>
        <div>
          <b>JalaMitra</b>
          <div className="small">{ward ? ward.name : t.pickWard} · {lang === 'kn' ? 'ಕನ್ನಡ' : 'English'}</div>
        </div>
        <button className="x" onClick={() => setOpen(false)} aria-label="Close">×</button>
      </div>
      <div className="chat-body">
        {!ward && <div className="msg bot">{t.clickMap}</div>}
        {ward && <div className="msg bot">{t.chatHello(ward.name)}</div>}
        {msgs.map((m, i) => (
          <div key={i} className={`msg ${m.role === 'user' ? 'me' : 'bot'}`}>
            {m.content}
          </div>
        ))}
        {busy && <div className="msg bot typing"><i /><i /><i /></div>}
        {ward && msgs.length === 0 && (
          <div className="sugg">
            {t.sugg.map((s) => <button key={s} onClick={() => send(s)}>{s}</button>)}
          </div>
        )}
        <div ref={end} />
      </div>
      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(input) }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={t.chatPh} disabled={!ward} />
        <button type="submit" disabled={!ward || busy}>➤</button>
      </form>
    </div>
  )
}
