import { useMsal, useIsAuthenticated } from '@azure/msal-react'
import { loginRequest } from '../msalConfig'

export default function LoginButton() {
  const { instance, accounts } = useMsal()
  const isAuthenticated = useIsAuthenticated()

  const handleLogin = () => {
    instance.loginPopup(loginRequest).catch(console.error)
  }

  const handleLogout = () => {
    instance.logoutPopup().catch(console.error)
  }

  if (!isAuthenticated) {
    return (
      <button onClick={handleLogin} className="bg-blue-600 text-white px-4 py-2 rounded">
        Login with Azure AD
      </button>
    )
  }

  const username = accounts[0]?.username ?? 'Unknown user'

  return (
    <div className="flex items-center gap-4">
      <span className="text-sm">Signed in as: {username}</span>
      <button onClick={handleLogout} className="text-red-600 text-sm">
        Logout
      </button>
    </div>
  )
}
