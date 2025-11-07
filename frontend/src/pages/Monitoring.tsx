import { FormEvent, useEffect, useState } from 'react'
import { useDashboardStore } from '../store/dashboard'

export default function Monitoring() {
  const [userId, setUserId] = useState('user001')
  const analyzeBehavior = useDashboardStore((state) => state.analyzeBehavior)
  const behaviorAlerts = useDashboardStore((state) => state.behaviorAlerts)
  const loadAlerts = useDashboardStore((state) => state.loadAlerts)
  const loadDormantAccounts = useDashboardStore((state) => state.loadDormantAccounts)
  const dormantAccounts = useDashboardStore((state) => state.dormantAccounts)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    loadAlerts().catch((error) => console.error('Failed to load alerts', error))
    loadDormantAccounts().catch((error) => console.error('Failed to load dormant accounts', error))
  }, [loadAlerts, loadDormantAccounts])

  async function handleAnalyze(event: FormEvent) {
    event.preventDefault()
    try {
      const alert = await analyzeBehavior({ user_id: userId })
      setMessage(`Analysis complete. Anomalies detected: ${alert.anomalies_detected}`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Analysis failed')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Monitoring & Sentinel Alerts</h1>
      {message && <div className="rounded bg-slate-100 p-3 text-sm text-slate-700">{message}</div>}

      <div className="grid gap-6 lg:grid-cols-2">
        <form className="card space-y-4" onSubmit={handleAnalyze}>
          <h2 className="text-lg font-semibold">Analyze User Behavior</h2>
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            placeholder="User ID"
            required
          />
          <button className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700" type="submit">
            Run Sentinel Analysis
          </button>
        </form>

        <div className="card">
          <h2 className="text-lg font-semibold">Dormant Accounts</h2>
          <ul className="space-y-3 text-sm">
            {dormantAccounts.map((account) => (
              <li key={account.user_id} className="rounded border border-gray-200 p-3">
                <div className="font-semibold">{account.user_id}</div>
                <div className="text-gray-500">{account.department}</div>
                <div className="text-gray-500">{account.last_activity}</div>
                <div className="text-xs text-red-500 mt-1">{account.recommendation}</div>
              </li>
            ))}
            {dormantAccounts.length === 0 && <li className="text-gray-500">No dormant accounts detected.</li>}
          </ul>
        </div>
      </div>

      <div className="card overflow-x-auto">
        <h2 className="text-lg font-semibold mb-4">Behavior Alerts</h2>
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="py-2">User</th>
              <th className="py-2">Detected</th>
              <th className="py-2">Anomalies</th>
              <th className="py-2">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {behaviorAlerts.map((alert) => (
              <tr key={`${alert.user_id}-${alert.analyzed_at}`}>
                <td className="py-2">{alert.user_id}</td>
                <td className="py-2">{new Date(alert.analyzed_at).toLocaleString()}</td>
                <td className="py-2">{alert.anomalies_detected}</td>
                <td className="py-2 text-xs text-gray-500">
                  {JSON.stringify(alert.details)}
                </td>
              </tr>
            ))}
            {behaviorAlerts.length === 0 && (
              <tr>
                <td className="py-4 text-center text-gray-500" colSpan={4}>
                  No behavior alerts recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
