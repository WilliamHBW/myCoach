import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import Plan from './pages/plan'
import Questionnaire from './pages/plan/questionnaire'
import RecordList from './pages/record'
import RecordForm from './pages/record/form'
import Settings from './pages/settings'
import './App.scss'

function App() {
  return (
    <div className="app-container">
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/plan" replace />} />
          <Route path="/plan" element={<Plan />} />
          <Route path="/plan/questionnaire" element={<Questionnaire />} />
          <Route path="/record" element={<RecordList />} />
          <Route path="/record/form" element={<RecordForm />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>

      <nav className="tab-bar">
        <NavLink to="/plan" className={({ isActive }) => `tab-item ${isActive ? 'active' : ''}`}>
          <span className="tab-icon">📋</span>
          <span className="tab-text">计划</span>
        </NavLink>
        <NavLink to="/record" className={({ isActive }) => `tab-item ${isActive ? 'active' : ''}`}>
          <span className="tab-icon">📝</span>
          <span className="tab-text">记录</span>
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `tab-item ${isActive ? 'active' : ''}`}>
          <span className="tab-icon">⚙️</span>
          <span className="tab-text">设置</span>
        </NavLink>
      </nav>
    </div>
  )
}

export default App

