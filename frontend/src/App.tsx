import { NavLink, Route, Routes } from 'react-router-dom'
import AccessRequest from './pages/AccessRequest'
import Lifecycle from './pages/Lifecycle'
import Risk from './pages/Risk'
import Monitoring from './pages/Monitoring'
import SCIM from './pages/SCIM'
import Groups from './pages/Groups'

const navItems = [
  { to: '/access-request', label: 'Access' },
  { to: '/lifecycle', label: 'Lifecycle' },
  { to: '/risk', label: 'Risk' },
  { to: '/monitoring', label: 'Monitoring' },
  { to: '/scim', label: 'SCIM' },
  { to: '/groups', label: 'Groups' }
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
          <div className="md:hidden">
            {/* Mobile nav placeholder */}
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <Routes>
          <Route path="/" element={<AccessRequest />} />
          <Route path="/access-request" element={<AccessRequest />} />
          <Route path="/lifecycle" element={<Lifecycle />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/scim" element={<SCIM />} />
          <Route path="/groups" element={<Groups />} />
        </Routes>
      </main>
    </div>
  )
}
