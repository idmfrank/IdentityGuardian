import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useDashboardStore } from '../store/dashboard'

interface AccessRequestFormState {
  user_id: string
  resource: string
  access_level: string
  justification: string
}

const initialForm: AccessRequestFormState = {
  user_id: '',
  resource: '',
  access_level: 'member',
  justification: ''
}

export default function AccessRequest() {
  const [form, setForm] = useState<AccessRequestFormState>(initialForm)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const accessRequests = useDashboardStore((state) => state.accessRequests)
  const fetchAccessRequests = useDashboardStore((state) => state.fetchAccessRequests)
  const submitAccessRequest = useDashboardStore((state) => state.submitAccessRequest)

  useEffect(() => {
    fetchAccessRequests().catch((error) => console.error('Failed to load access requests', error))
  }, [fetchAccessRequests])

  const trendData = useMemo(() => {
    const byDate = new Map<string, number>()
    accessRequests.forEach((req) => {
      const day = new Date(req.submitted_at).toLocaleDateString()
      byDate.set(day, (byDate.get(day) ?? 0) + 1)
    })
    return Array.from(byDate.entries()).map(([date, requests]) => ({ date, requests }))
  }, [accessRequests])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const record = await submitAccessRequest({
        user_id: form.user_id,
        resource: form.resource,
        access_level: form.access_level,
        justification: form.justification
      })
      setStatusMessage(
        `Request ${record.request_id} submitted with status ${record.status} (risk ${(record.risk_score ?? 0).toFixed(2)})`
      )
      setForm(initialForm)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Request failed'
      setStatusMessage(message)
    }
  }

  function updateField(field: keyof AccessRequestFormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="card">
        <h2 className="text-2xl font-semibold mb-4">Request Access</h2>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="text-sm font-medium text-gray-600">User (UPN)</label>
            <input
              value={form.user_id}
              onChange={(event) => updateField('user_id', event.target.value)}
              required
              className="mt-1 w-full rounded border border-gray-300 p-2"
              placeholder="user001"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-600">Resource</label>
            <input
              value={form.resource}
              onChange={(event) => updateField('resource', event.target.value)}
              required
              className="mt-1 w-full rounded border border-gray-300 p-2"
              placeholder="snowflake_prod"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-600">Access Level</label>
            <input
              value={form.access_level}
              onChange={(event) => updateField('access_level', event.target.value)}
              required
              className="mt-1 w-full rounded border border-gray-300 p-2"
              placeholder="read"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-600">Business Justification</label>
            <textarea
              value={form.justification}
              onChange={(event) => updateField('justification', event.target.value)}
              required
              className="mt-1 w-full rounded border border-gray-300 p-2"
              rows={3}
            />
          </div>
          <button
            type="submit"
            className="w-full rounded bg-blue-600 py-2 font-semibold text-white transition hover:bg-blue-700"
          >
            Submit Request
          </button>
        </form>
        {statusMessage && <p className="mt-4 text-sm text-green-600">{statusMessage}</p>}
      </div>

      <div className="space-y-4">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Request Trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData}>
              <XAxis dataKey="date" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="requests" stroke="#2563eb" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card overflow-x-auto">
          <h3 className="text-lg font-semibold mb-4">Recent Requests</h3>
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="py-2">Request ID</th>
                <th className="py-2">User</th>
                <th className="py-2">Resource</th>
                <th className="py-2">Status</th>
                <th className="py-2">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {accessRequests.map((request) => (
                <tr key={request.request_id}>
                  <td className="py-2 font-mono text-xs text-gray-500">{request.request_id}</td>
                  <td className="py-2">{request.user_id}</td>
                  <td className="py-2">{request.resource_id}</td>
                  <td className="py-2 capitalize">{request.status}</td>
                  <td className="py-2">{request.risk_score?.toFixed(2) ?? '—'}</td>
                </tr>
              ))}
              {accessRequests.length === 0 && (
                <tr>
                  <td className="py-4 text-center text-gray-500" colSpan={5}>
                    No access requests recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
