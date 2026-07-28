export type EligibilityStatus = 'eligible' | 'at_risk' | 'locked'

export type PlayerEligibility = {
  player_id: number
  player_name: string
  jersey_number: number | null
  status: EligibilityStatus
  matches_to_skip: number
  eligible_on: string | null
}

export type TeamEligibility = {
  team_name: string
  as_of: string
  players: PlayerEligibility[]
}

export type NextMatch = {
  played_on: string
  kickoff_time: string | null
  competition: string
  home_team: string
  away_team: string
  report_url: string | null
}

export type SyncStatus = {
  last_successful_sync_at: string | null
}

const apiBaseUrl = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
const higherTeamId = import.meta.env.VITE_HIGHER_TEAM_ID ?? '1'
const lowerTeamId = import.meta.env.VITE_LOWER_TEAM_ID ?? '2'
const staticDashboard = import.meta.env.VITE_STATIC_DASHBOARD === 'true'

type StaticDashboardPayload = {
  next_higher_match: NextMatch
  next_lower_match: NextMatch | null
  eligibility: TeamEligibility
  sync_status: SyncStatus
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`)
  if (!response.ok)
    throw new Error(`API-Anfrage fehlgeschlagen (${response.status})`)
  return response.json() as Promise<T>
}

async function getStaticDashboardData(): Promise<StaticDashboardPayload> {
  const response = await fetch('dashboard.json')
  if (!response.ok)
    throw new Error(`Dashboard-Daten konnten nicht geladen werden (${response.status})`)
  return response.json() as Promise<StaticDashboardPayload>
}

async function getOptionalNextMatch(teamId: string): Promise<NextMatch | null> {
  const response = await fetch(`${apiBaseUrl}/teams/${teamId}/next-match`)
  if (response.status === 404) return null
  if (!response.ok)
    throw new Error(`API-Anfrage fehlgeschlagen (${response.status})`)
  return response.json() as Promise<NextMatch>
}

export function getDashboardData(): Promise<
  [NextMatch, NextMatch | null, TeamEligibility, SyncStatus]
> {
  if (staticDashboard) {
    return getStaticDashboardData().then((dashboard) => [
      dashboard.next_higher_match,
      dashboard.next_lower_match,
      dashboard.eligibility,
      dashboard.sync_status,
    ])
  }
  return Promise.all([
    getOptionalNextMatch(higherTeamId).then((match) => {
      if (match === null) {
        throw new Error('Kein nächstes Pflichtspiel der ersten Ü40 gefunden.')
      }
      return match
    }),
    getOptionalNextMatch(lowerTeamId),
    getJson<TeamEligibility>(`/teams/${higherTeamId}/eligibility`),
    getJson<SyncStatus>(`/teams/${higherTeamId}/sync-status`),
  ])
}
