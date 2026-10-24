import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Landing from './Landing'
import AgriPlatform from './platforms/agri'
import IndustryPlatform from './platforms/industry'
import UrbanPlatform from './platforms/urban'
import BengaluruApp from './platforms/urban/BengaluruApp'
import './shared/platform.css'

// Old Bengaluru demo links (/?view=..., /?tour=0, /?ward=...) now live at /urban/bengaluru.
const LEGACY = ['view', 'tour', 'ward', 'layer', 'lang']

function Home() {
  const { search } = useLocation()
  const p = new URLSearchParams(search)
  if (LEGACY.some((k) => p.has(k))) return <Navigate to={`/urban/bengaluru${search}`} replace />
  return <Landing />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/agri" element={<AgriPlatform />} />
        <Route path="/urban" element={<UrbanPlatform />} />
        <Route path="/urban/bengaluru" element={<BengaluruApp />} />
        <Route path="/industry" element={<IndustryPlatform />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
