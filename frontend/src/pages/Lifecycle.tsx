import { FormEvent, useEffect, useState } from 'react'
import { useDashboardStore } from '../store/dashboard'

interface JoinerForm {
  user_id: string
  username: string
  email: string
  first_name: string
  last_name: string
  department: string
  manager_id: string
  start_date: string
}

interface MoverForm {
  user_id: string
  new_department: string
  new_role: string
  effective_date: string
}

interface LeaverForm {
  user_id: string
  termination_date: string
  reason: string
}

const initialJoiner: JoinerForm = {
  user_id: 'user999',
  username: 'new.user',
  email: 'new.user@company.com',
  first_name: 'New',
  last_name: 'User',
  department: 'Engineering',
  manager_id: 'mgr001',
  start_date: new Date().toISOString().slice(0, 10)
}

const initialMover: MoverForm = {
  user_id: 'user001',
  new_department: 'Product',
  new_role: 'Product Manager',
  effective_date: new Date().toISOString().slice(0, 10)
}

const initialLeaver: LeaverForm = {
  user_id: 'user002',
  termination_date: new Date().toISOString().slice(0, 10),
  reason: 'Voluntary departure'
}

export default function Lifecycle() {
  const [joinerForm, setJoinerForm] = useState<JoinerForm>(initialJoiner)
  const [moverForm, setMoverForm] = useState<MoverForm>(initialMover)
  const [leaverForm, setLeaverForm] = useState<LeaverForm>(initialLeaver)
  const lifecycleEvents = useDashboardStore((state) => state.lifecycleEvents)
  const fetchEvents = useDashboardStore((state) => state.fetchLifecycleEvents)
  const triggerLifecycleEvent = useDashboardStore((state) => state.triggerLifecycleEvent)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    fetchEvents().catch((error) => console.error('Failed to load lifecycle events', error))
  }, [fetchEvents])

  async function submitJoiner(event: FormEvent) {
    event.preventDefault()
    try {
      const result = await triggerLifecycleEvent('joiner', joinerForm)
      setMessage(`Joiner processed for ${result.user_id}`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Joiner failed')
    }
  }

  async function submitMover(event: FormEvent) {
    event.preventDefault()
    try {
      const result = await triggerLifecycleEvent('mover', moverForm)
      setMessage(`Mover processed for ${result.user_id}`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Mover failed')
    }
  }

  async function submitLeaver(event: FormEvent) {
    event.preventDefault()
    try {
      const result = await triggerLifecycleEvent('leaver', leaverForm)
      setMessage(`Leaver processed for ${result.user_id}`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Leaver failed')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Lifecycle Operations</h1>
      {message && <div className="rounded bg-blue-50 p-3 text-sm text-blue-800">{message}</div>}

      <div className="grid gap-6 lg:grid-cols-3">
        <form className="card space-y-3" onSubmit={submitJoiner}>
          <h2 className="text-lg font-semibold">Joiner</h2>
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={joinerForm.user_id}
            onChange={(event) => setJoinerForm({ ...joinerForm, user_id: event.target.value })}
            placeholder="User ID"
            required
          />
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={joinerForm.username}
            onChange={(event) => setJoinerForm({ ...joinerForm, username: event.target.value })}
            placeholder="Username"
            required
          />
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={joinerForm.email}
            onChange={(event) => setJoinerForm({ ...joinerForm, email: event.target.value })}
            placeholder="Email"
            required
          />
          <div className="flex gap-2">
            <input
              className="w-full rounded border border-gray-200 p-2"
              value={joinerForm.first_name}
              onChange={(event) => setJoinerForm({ ...joinerForm, first_name: event.target.value })}
              placeholder="First name"
              required
            />
            <input
              className="w-full rounded border border-gray-200 p-2"
              value={joinerForm.last_name}
              onChange={(event) => setJoinerForm({ ...joinerForm, last_name: event.target.value })}
              placeholder="Last name"
              required
            />
          </div>
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={joinerForm.department}
            onChange={(event) => setJoinerForm({ ...joinerForm, department: event.target.value })}
            placeholder="Department"
            required
          />
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={joinerForm.manager_id}
            onChange={(event) => setJoinerForm({ ...joinerForm, manager_id: event.target.value })}
            placeholder="Manager ID"
          />
          <input
            type="date"
            className="w-full rounded border border-gray-200 p-2"
            value={joinerForm.start_date}
            onChange={(event) => setJoinerForm({ ...joinerForm, start_date: event.target.value })}
            required
          />
          <button className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700" type="submit">
            Start Joiner Workflow
          </button>
        </form>

        <form className="card space-y-3" onSubmit={submitMover}>
          <h2 className="text-lg font-semibold">Mover</h2>
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={moverForm.user_id}
            onChange={(event) => setMoverForm({ ...moverForm, user_id: event.target.value })}
            placeholder="User ID"
            required
          />
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={moverForm.new_department}
            onChange={(event) => setMoverForm({ ...moverForm, new_department: event.target.value })}
            placeholder="New Department"
            required
          />
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={moverForm.new_role}
            onChange={(event) => setMoverForm({ ...moverForm, new_role: event.target.value })}
            placeholder="New Role"
            required
          />
          <input
            type="date"
            className="w-full rounded border border-gray-200 p-2"
            value={moverForm.effective_date}
            onChange={(event) => setMoverForm({ ...moverForm, effective_date: event.target.value })}
            required
          />
          <button className="w-full rounded bg-amber-500 py-2 text-white hover:bg-amber-600" type="submit">
            Start Mover Workflow
          </button>
        </form>

        <form className="card space-y-3" onSubmit={submitLeaver}>
          <h2 className="text-lg font-semibold">Leaver</h2>
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={leaverForm.user_id}
            onChange={(event) => setLeaverForm({ ...leaverForm, user_id: event.target.value })}
            placeholder="User ID"
            required
          />
          <input
            type="date"
            className="w-full rounded border border-gray-200 p-2"
            value={leaverForm.termination_date}
            onChange={(event) => setLeaverForm({ ...leaverForm, termination_date: event.target.value })}
            required
          />
          <textarea
            className="w-full rounded border border-gray-200 p-2"
            value={leaverForm.reason}
            onChange={(event) => setLeaverForm({ ...leaverForm, reason: event.target.value })}
            placeholder="Reason"
          />
          <button className="w-full rounded bg-red-600 py-2 text-white hover:bg-red-700" type="submit">
            Start Leaver Workflow
          </button>
        </form>
      </div>

      <div className="card overflow-x-auto">
        <h2 className="text-lg font-semibold mb-4">Recent Lifecycle Events</h2>
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="py-2">Event</th>
              <th className="py-2">User</th>
              <th className="py-2">Status</th>
              <th className="py-2">Effective</th>
              <th className="py-2">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {lifecycleEvents.map((event) => (
              <tr key={event.event_id}>
                <td className="py-2 capitalize">{event.event_type}</td>
                <td className="py-2">{event.user_id}</td>
                <td className="py-2 capitalize">{event.status}</td>
                <td className="py-2">{new Date(event.effective_date).toLocaleDateString()}</td>
                <td className="py-2 text-xs text-gray-500">
                  {Object.keys(event.details)
                    .map((key) => `${key}: ${String(event.details[key])}`)
                    .join(', ')}
                </td>
              </tr>
            ))}
            {lifecycleEvents.length === 0 && (
              <tr>
                <td className="py-4 text-center text-gray-500" colSpan={5}>
                  No lifecycle events recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
