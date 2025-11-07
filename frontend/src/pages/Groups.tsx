import { FormEvent, useEffect, useState } from 'react'
import { useDashboardStore } from '../store/dashboard'

export default function Groups() {
  const loadGroups = useDashboardStore((state) => state.loadGroups)
  const groups = useDashboardStore((state) => state.groups)
  const createGroup = useDashboardStore((state) => state.createGroup)
  const updateGroupMembers = useDashboardStore((state) => state.updateGroupMembers)
  const removeGroupMember = useDashboardStore((state) => state.removeGroupMember)
  const [displayName, setDisplayName] = useState('Identity Response Team')
  const [role, setRole] = useState('incident_response')
  const [memberInput, setMemberInput] = useState('user001')
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    loadGroups().catch((error) => console.error('Failed to load groups', error))
  }, [loadGroups])

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    try {
      const group = await createGroup({ display_name: displayName, role })
      setMessage(`Created group ${group.display_name}`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to create group')
    }
  }

  async function handleAddMember(event: FormEvent) {
    event.preventDefault()
    if (!selectedGroup) {
      setMessage('Select a group to add members')
      return
    }
    try {
      const memberList = memberInput.split(/[,\s]+/).filter(Boolean)
      const updated = await updateGroupMembers(selectedGroup, memberList)
      setMessage(`Added ${memberList.length} members to ${updated.display_name}`)
      setMemberInput('')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to update group')
    }
  }

  async function handleRemoveMember(groupId: string, member: string) {
    try {
      const updated = await removeGroupMember(groupId, member)
      setMessage(`Removed ${member} from ${updated.display_name}`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to remove member')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Group Management</h1>
      {message && <div className="rounded bg-purple-50 p-3 text-sm text-purple-700">{message}</div>}

      <div className="grid gap-6 lg:grid-cols-2">
        <form className="card space-y-4" onSubmit={handleCreate}>
          <h2 className="text-lg font-semibold">Create Group</h2>
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="Display name"
            required
          />
          <input
            className="w-full rounded border border-gray-200 p-2"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            placeholder="Role identifier"
          />
          <button className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700" type="submit">
            Create Group
          </button>
        </form>

        <form className="card space-y-4" onSubmit={handleAddMember}>
          <h2 className="text-lg font-semibold">Add Members</h2>
          <select
            className="w-full rounded border border-gray-200 p-2"
            value={selectedGroup ?? ''}
            onChange={(event) => setSelectedGroup(event.target.value)}
            required
          >
            <option value="" disabled>
              Select a group
            </option>
            {groups.map((group) => (
              <option key={group.group_id} value={group.group_id}>
                {group.display_name}
              </option>
            ))}
          </select>
          <textarea
            className="w-full rounded border border-gray-200 p-2"
            rows={3}
            value={memberInput}
            onChange={(event) => setMemberInput(event.target.value)}
            placeholder="Enter members separated by commas"
          />
          <button className="rounded bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700" type="submit">
            Update Members
          </button>
        </form>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {groups.map((group) => (
          <div key={group.group_id} className="card space-y-3">
            <div>
              <p className="text-lg font-semibold">{group.display_name}</p>
              <p className="text-sm text-gray-500">
                Created {new Date(group.created_at).toLocaleDateString()} • Role: {group.role ?? 'n/a'}
              </p>
            </div>
            <div className="space-y-2">
              {group.members.length === 0 && <p className="text-sm text-gray-500">No members assigned.</p>}
              {group.members.map((member) => (
                <div key={member} className="flex items-center justify-between rounded border border-gray-200 p-2">
                  <span>{member}</span>
                  <button
                    type="button"
                    className="text-sm text-red-500 hover:underline"
                    onClick={() => handleRemoveMember(group.group_id, member)}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
        {groups.length === 0 && <p className="text-gray-500">No groups configured yet.</p>}
      </div>
    </div>
  )
}
