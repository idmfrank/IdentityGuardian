import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useIsAuthenticated } from '@azure/msal-react'
import AccessRequest from './pages/AccessRequest'
import Lifecycle from './pages/Lifecycle'
import Risk from './pages/Risk'
import Monitoring from './pages/Monitoring'
import SCIM from './pages/SCIM'
import Groups from './pages/Groups'
import LoginButton from './components/LoginButton'

const navItems = [
  { to: '/access-request', label: 'Access' },
  { to: '/lifecycle', label: 'Lifecycle' },
  { to: '/risk', label: 'Risk' },
  { to: '/monitoring', label: 'Monitoring' },
  { to: '/scim', label: 'SCIM' },
  { to: '/groups', label: 'Groups' },
]

function NavigationLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
          isActive ? 'bg-blue-700 text-white' : 'text-blue-100 hover:bg-blue-800 hover:text-white'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const isAuthenticated = useIsAuthenticated()
  return isAuthenticated ? children : <Navigate to="/" replace />
}

function Home() {
  const isAuthenticated = useIsAuthenticated()

  return (
    <div className="text-center py-20">
      <h1 className="text-4xl font-bold mb-4">IdentityGuardian</h1>
      <p className="text-lg text-gray-600">
        {isAuthenticated
          ? 'Welcome back! Use the navigation to access dashboards.'
          : 'Please log in with Azure AD to continue.'}
      </p>
    </div>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-blue-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-6">
            <NavLink to="/" className="text-xl font-bold tracking-tight">
              IdentityGuardian
            </NavLink>
            <div className="hidden md:flex gap-2">
              {navItems.map((item) => (
                <NavigationLink key={item.to} to={item.to} label={item.label} />
              ))}
            </div>
          </div>
          <LoginButton />
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route
            path="/access-request"
            element={
              <ProtectedRoute>
                <AccessRequest />
              </ProtectedRoute>
            }
          />
          <Route
            path="/lifecycle"
            element={
              <ProtectedRoute>
                <Lifecycle />
              </ProtectedRoute>
            }
          />
          <Route
            path="/risk"
            element={
              <ProtectedRoute>
                <Risk />
              </ProtectedRoute>
            }
          />
          <Route
            path="/monitoring"
            element={
              <ProtectedRoute>
                <Monitoring />
              </ProtectedRoute>
            }
          />
          <Route
            path="/scim"
            element={
              <ProtectedRoute>
                <SCIM />
              </ProtectedRoute>
            }
          />
          <Route
            path="/groups"
            element={
              <ProtectedRoute>
                <Groups />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
