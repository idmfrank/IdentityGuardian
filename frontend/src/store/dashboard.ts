import { create } from 'zustand'

type HttpMethod = 'GET' | 'POST' | 'DELETE'

export interface AccessRequestRecord {
  request_id: string
  submitted_at: string
  status: string
  risk_score?: number
  approvers: string[]
  ticket_id?: string
  recommendation?: string
  policy_violations?: string[]
  user_id: string
  resource_id: string
  access_level: string
  business_justification: string
}

export interface ReviewCampaignRecord {
  campaign_id: string
  campaign_name: string
  scope: string
  start_date: string
  end_date: string
  status: string
  review_items: ReviewItemRecord[]
}

export interface ReviewItemRecord {
  review_item_id: string
  campaign_id: string
  user_id: string
  resource_id: string
  access_level: string
  reviewer_id: string
  status: string
  recommendation?: string
  risk_score: number
}

export interface LifecycleEventRecord {
  event_id: string
  event_type: string
  user_id: string
  status: string
  triggered_at: string
  effective_date: string
  details: Record<string, unknown>
}

export interface BehaviorAnalysisRecord {
  user_id: string
  analyzed_at: string
  anomalies_detected: number
  details: Record<string, unknown>
}

export interface DormantAccountRecord {
  user_id: string
  username: string
  department: string
  last_activity: string
  recommendation: string
}

export interface RiskAssessmentRecord {
  risk_id: string
  user_id: string
  risk_score: number
  risk_level: string
  assessed_at: string
  details: Record<string, unknown>
}

export interface GroupRecord {
  group_id: string
  display_name: string
  members: string[]
  created_at: string
  role?: string | null
}

export interface SCIMEvent {
  event_id: string
  direction: string
  payload: Record<string, unknown>
  status: string
  recorded_at: string
  detail?: string | null
}

type Nullable<T> = T | null

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api'

async function request<T>(path: string, method: HttpMethod = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `API request failed (${response.status})`)
  }

  return (await response.json()) as T
}

interface DashboardState {
  loading: boolean
  error: string | null
  accessRequests: AccessRequestRecord[]
  reviewCampaigns: ReviewCampaignRecord[]
  lifecycleEvents: LifecycleEventRecord[]
  behaviorAlerts: BehaviorAnalysisRecord[]
  dormantAccounts: DormantAccountRecord[]
  riskAssessments: RiskAssessmentRecord[]
  groups: GroupRecord[]
  scimInbound: SCIMEvent[]
  scimOutbound: SCIMEvent[]
  fetchAccessRequests: () => Promise<void>
  submitAccessRequest: (payload: Record<string, unknown>) => Promise<AccessRequestRecord>
  createReviewCampaign: (payload: Record<string, unknown>) => Promise<ReviewCampaignRecord>
  submitReviewDecision: (
    campaignId: string,
    reviewItemId: string,
    payload: Record<string, unknown>
  ) => Promise<ReviewItemRecord>
  fetchLifecycleEvents: () => Promise<void>
  triggerLifecycleEvent: (type: 'joiner' | 'mover' | 'leaver', payload: Record<string, unknown>) => Promise<LifecycleEventRecord>
  analyzeBehavior: (payload: Record<string, unknown>) => Promise<BehaviorAnalysisRecord>
  loadAlerts: () => Promise<void>
  loadDormantAccounts: () => Promise<void>
  runRiskAssessment: (payload: Record<string, unknown>) => Promise<RiskAssessmentRecord>
  autoBlock: (payload: Record<string, unknown>) => Promise<string>
  loadRiskAssessments: () => Promise<void>
  loadGroups: () => Promise<void>
  createGroup: (payload: Record<string, unknown>) => Promise<GroupRecord>
  updateGroupMembers: (groupId: string, members: string[]) => Promise<GroupRecord>
  removeGroupMember: (groupId: string, member: string) => Promise<GroupRecord>
  loadScimLogs: () => Promise<void>
  recordScimEvent: (direction: 'inbound' | 'outbound', payload: Record<string, unknown>) => Promise<SCIMEvent>
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  loading: false,
  error: null,
  accessRequests: [],
  reviewCampaigns: [],
  lifecycleEvents: [],
  behaviorAlerts: [],
  dormantAccounts: [],
  riskAssessments: [],
  groups: [],
  scimInbound: [],
  scimOutbound: [],

  async fetchAccessRequests() {
    const data = await request<AccessRequestRecord[]>('/access/requests')
    set({ accessRequests: data })
  },

  async submitAccessRequest(payload) {
    const record = await request<AccessRequestRecord>('/access/request', 'POST', payload)
    set({ accessRequests: [record, ...get().accessRequests] })
    return record
  },

  async createReviewCampaign(payload) {
    const campaign = await request<ReviewCampaignRecord>('/reviews/campaigns', 'POST', payload)
    set({ reviewCampaigns: [campaign, ...get().reviewCampaigns] })
    return campaign
  },

  async submitReviewDecision(campaignId, reviewItemId, payload) {
    const item = await request<ReviewItemRecord>(
      `/reviews/campaigns/${campaignId}/items/${reviewItemId}`,
      'POST',
      payload
    )
    const campaigns = get().reviewCampaigns.map((campaign) =>
      campaign.campaign_id === campaignId
        ? {
            ...campaign,
            review_items: campaign.review_items.map((ri) =>
              ri.review_item_id === reviewItemId ? { ...ri, ...item } : ri
            )
          }
        : campaign
    )
    set({ reviewCampaigns: campaigns })
    return item
  },

  async fetchLifecycleEvents() {
    const events = await request<LifecycleEventRecord[]>('/lifecycle/events')
    set({ lifecycleEvents: events })
  },

  async triggerLifecycleEvent(type, payload) {
    const record = await request<LifecycleEventRecord>(`/lifecycle/${type}`, 'POST', payload)
    set({ lifecycleEvents: [record, ...get().lifecycleEvents] })
    return record
  },

  async analyzeBehavior(payload) {
    const record = await request<BehaviorAnalysisRecord>('/monitoring/analyze', 'POST', payload)
    set({ behaviorAlerts: [record, ...get().behaviorAlerts] })
    return record
  },

  async loadAlerts() {
    const alerts = await request<BehaviorAnalysisRecord[]>('/monitoring/alerts')
    set({ behaviorAlerts: alerts })
  },

  async loadDormantAccounts() {
    const result = await request<{ accounts: DormantAccountRecord[] }>('/monitoring/dormant')
    set({ dormantAccounts: result.accounts })
  },

  async runRiskAssessment(payload) {
    const record = await request<RiskAssessmentRecord>('/risk/assessment', 'POST', payload)
    set({ riskAssessments: [record, ...get().riskAssessments] })
    return record
  },

  async autoBlock(payload) {
    const response = await request<{ message: string }>('/risk/auto-block', 'POST', payload)
    return response.message
  },

  async loadRiskAssessments() {
    const data = await request<RiskAssessmentRecord[]>('/risk/assessments')
    set({ riskAssessments: data })
  },

  async loadGroups() {
    const groups = await request<GroupRecord[]>('/groups/')
    set({ groups })
  },

  async createGroup(payload) {
    const group = await request<GroupRecord>('/groups/', 'POST', payload)
    set({ groups: [group, ...get().groups] })
    return group
  },

  async updateGroupMembers(groupId, members) {
    const group = await request<GroupRecord>(`/groups/${groupId}/members`, 'POST', { members })
    set({
      groups: get().groups.map((existing) => (existing.group_id === groupId ? group : existing))
    })
    return group
  },

  async removeGroupMember(groupId, member) {
    const group = await request<GroupRecord>(`/groups/${groupId}/members/${member}`, 'DELETE')
    set({
      groups: get().groups.map((existing) => (existing.group_id === groupId ? group : existing))
    })
    return group
  },

  async loadScimLogs() {
    const [outbound, inbound] = await Promise.all([
      request<SCIMEvent[]>('/scim/outbound'),
      request<SCIMEvent[]>('/scim/inbound')
    ])
    set({ scimOutbound: outbound, scimInbound: inbound })
  },

  async recordScimEvent(direction, payload) {
    const event = await request<SCIMEvent>(`/scim/${direction}`, 'POST', payload)
    if (direction === 'outbound') {
      set({ scimOutbound: [event, ...get().scimOutbound] })
    } else {
      set({ scimInbound: [event, ...get().scimInbound] })
    }
    return event
  }
}))
