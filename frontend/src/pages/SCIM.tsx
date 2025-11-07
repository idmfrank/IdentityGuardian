import { FormEvent, useEffect, useState } from 'react'
import { useDashboardStore } from '../store/dashboard'

export default function SCIM() {
  const loadScimLogs = useDashboardStore((state) => state.loadScimLogs)
  const scimInbound = useDashboardStore((state) => state.scimInbound)
  const scimOutbound = useDashboardStore((state) => state.scimOutbound)
  const recordScimEvent = useDashboardStore((state) => state.recordScimEvent)
  const [direction, setDirection] = useState<'inbound' | 'outbound'>('outbound')
  const [payload, setPayload] = useState('{"operation": "sync"}')
  const [status, setStatus] = useState('success')
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    loadScimLogs().catch((error) => console.error('Failed to load SCIM logs', error))
  }, [loadScimLogs])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    try {
      const parsed = JSON.parse(payload)
      const eventRecord = await recordScimEvent(direction, { payload: parsed, status })
      setMessage(`Logged ${eventRecord.direction} event ${eventRecord.event_id}`)
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Unable to record SCIM event'
      setMessage(detail)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">SCIM Activity</h1>
      {message && <div className="rounded bg-indigo-50 p-3 text-sm text-indigo-700">{message}</div>}

      <form className="card space-y-4" onSubmit={handleSubmit}>
        <h2 className="text-lg font-semibold">Record SCIM Event</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-sm font-medium text-gray-600">Direction</label>
            <select
              className="mt-1 w-full rounded border border-gray-200 p-2"
              value={direction}
              onChange={(event) => setDirection(event.target.value as 'inbound' | 'outbound')}
            >
              <option value="outbound">Outbound</option>
              <option value="inbound">Inbound</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-600">Status</label>
            <input
              className="mt-1 w-full rounded border border-gray-200 p-2"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-600">Payload (JSON)</label>
          <textarea
            className="mt-1 w-full rounded border border-gray-200 p-2 font-mono text-xs"
            rows={4}
            value={payload}
            onChange={(event) => setPayload(event.target.value)}
          />
        </div>
        <button className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700" type="submit">
          Log Event
        </button>
      </form>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card overflow-x-auto">
          <h2 className="text-lg font-semibold mb-4">Outbound Events</h2>
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="py-2">Event ID</th>
                <th className="py-2">Status</th>
                <th className="py-2">Recorded</th>
                <th className="py-2">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {scimOutbound.map((event) => (
                <tr key={event.event_id}>
                  <td className="py-2 font-mono text-xs text-gray-500">{event.event_id}</td>
                  <td className="py-2 capitalize">{event.status}</td>
                  <td className="py-2">{new Date(event.recorded_at).toLocaleString()}</td>
                  <td className="py-2 text-xs text-gray-500">{JSON.stringify(event.payload)}</td>
                </tr>
              ))}
              {scimOutbound.length === 0 && (
                <tr>
                  <td className="py-4 text-center text-gray-500" colSpan={4}>
                    No outbound SCIM events recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card overflow-x-auto">
          <h2 className="text-lg font-semibold mb-4">Inbound Events</h2>
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="py-2">Event ID</th>
                <th className="py-2">Status</th>
                <th className="py-2">Recorded</th>
                <th className="py-2">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {scimInbound.map((event) => (
                <tr key={event.event_id}>
                  <td className="py-2 font-mono text-xs text-gray-500">{event.event_id}</td>
                  <td className="py-2 capitalize">{event.status}</td>
                  <td className="py-2">{new Date(event.recorded_at).toLocaleString()}</td>
                  <td className="py-2 text-xs text-gray-500">{JSON.stringify(event.payload)}</td>
                </tr>
              ))}
              {scimInbound.length === 0 && (
                <tr>
                  <td className="py-4 text-center text-gray-500" colSpan={4}>
                    No inbound SCIM events recorded.
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
