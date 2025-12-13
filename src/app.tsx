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
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-icon">🏃</span>
            <span className="logo-text">MyCoach</span>
          </div>
          
          <nav className="main-nav">
            <NavLink to="/plan" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
              </svg>
              <span>训练计划</span>
            </NavLink>
            <NavLink to="/record" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
              <span>运动记录</span>
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <span>设置</span>
            </NavLink>
          </nav>

          <div className="header-right">
            <div className="user-avatar">
              <span>👤</span>
            </div>
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="content-wrapper">
          <Routes>
            <Route path="/" element={<Navigate to="/plan" replace />} />
            <Route path="/plan" element={<Plan />} />
            <Route path="/plan/questionnaire" element={<Questionnaire />} />
            <Route path="/record" element={<RecordList />} />
            <Route path="/record/form" element={<RecordForm />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </main>

      <footer className="app-footer">
        <div className="footer-content">
          <p>© 2024 MyCoach - AI 私人教练</p>
          <p className="footer-tagline">让运动更科学，让进步更可见</p>
        </div>
      </footer>
    </div>
  )
}

export default App
