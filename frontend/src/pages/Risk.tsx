import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useDashboardStore } from '../store/dashboard'

const COLORS = ['#22c55e', '#facc15', '#f97316', '#ef4444']

export default function Risk() {
  const [userId, setUserId] = useState('user001')
  const riskAssessments = useDashboardStore((state) => state.riskAssessments)
  const runRiskAssessment = useDashboardStore((state) => state.runRiskAssessment)
  const autoBlock = useDashboardStore((state) => state.autoBlock)
  const loadAssessments = useDashboardStore((state) => state.loadRiskAssessments)
  const [status, setStatus] = useState<string | null>(null)

  useEffect(() => {
    loadAssessments().catch((error) => console.error('Failed to load risk assessments', error))
  }, [loadAssessments])

  const riskDistribution = useMemo(() => {
    const counts = new Map<string, number>()
    riskAssessments.forEach((assessment) => {
      counts.set(assessment.risk_level, (counts.get(assessment.risk_level) ?? 0) + 1)
    })
    return Array.from(counts.entries()).map(([name, value]) => ({ name, value }))
  }, [riskAssessments])

  async function handleAssess(event: FormEvent) {
    event.preventDefault()
    try {
      const result = await runRiskAssessment({ user_id: userId })
      setStatus(`Risk score for ${result.user_id}: ${(result.risk_score * 100).toFixed(1)}% (${result.risk_level})`)
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Assessment failed')
    }
  }

  async function handleAutoBlock(user: string) {
    try {
      const message = await autoBlock({ user_id: user })
      setStatus(message)
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Auto-block failed')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Identity Risk Dashboard</h1>
      {status && <div className="rounded bg-emerald-50 p-3 text-sm text-emerald-800">{status}</div>}

      <div className="grid gap-4 md:grid-cols-3">
        <div className="card">
          <p className="text-sm text-red-500">Auto-Blocks Initiated</p>
          <p className="text-3xl font-semibold">{riskAssessments.filter((r) => r.risk_level === 'critical').length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-amber-500">High Risk Users</p>
          <p className="text-3xl font-semibold">{riskAssessments.filter((r) => r.risk_level === 'high').length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-green-500">Assessments Run</p>
          <p className="text-3xl font-semibold">{riskAssessments.length}</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <form className="card space-y-4" onSubmit={handleAssess}>
          <h2 className="text-lg font-semibold">Run Risk Assessment</h2>
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            placeholder="User ID"
            required
          />
          <div className="flex gap-2">
            <button type="submit" className="flex-1 rounded bg-blue-600 py-2 text-white hover:bg-blue-700">
              Calculate Risk
            </button>
            <button
              type="button"
              className="flex-1 rounded bg-red-600 py-2 text-white hover:bg-red-700"
              onClick={() => handleAutoBlock(userId)}
            >
              Auto-Block User
            </button>
          </div>
        </form>

        <div className="card">
          <h2 className="text-lg font-semibold">Risk Distribution</h2>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={riskDistribution} dataKey="value" nameKey="name" outerRadius={110} label>
                {riskDistribution.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card overflow-x-auto">
        <h2 className="text-lg font-semibold mb-4">Recent Assessments</h2>
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="py-2">Risk ID</th>
              <th className="py-2">User</th>
              <th className="py-2">Score</th>
              <th className="py-2">Level</th>
              <th className="py-2">Assessed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {riskAssessments.map((assessment) => (
              <tr key={assessment.risk_id}>
                <td className="py-2 font-mono text-xs text-gray-500">{assessment.risk_id}</td>
                <td className="py-2">{assessment.user_id}</td>
                <td className="py-2">{(assessment.risk_score * 100).toFixed(1)}%</td>
                <td className="py-2 capitalize">{assessment.risk_level}</td>
                <td className="py-2">{new Date(assessment.assessed_at).toLocaleString()}</td>
              </tr>
            ))}
            {riskAssessments.length === 0 && (
              <tr>
                <td className="py-4 text-center text-gray-500" colSpan={5}>
                  No risk assessments recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
