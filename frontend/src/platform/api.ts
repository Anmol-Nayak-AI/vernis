import type { AgentRun, Artwork, ArtworkPage, CommandMetrics, EngineCase, EngineCaseDetail, EvidenceRecord, Organization, VisualAnalysis } from './types';

interface ApiErrorPayload {
  detail?: string | { message?: string };
  error?: { message?: string };
}

async function request<T>(path: string, token?: string | null, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try { payload = await response.json() as ApiErrorPayload; } catch { /* non-JSON upstream error */ }
    const detail = payload.error?.message || (typeof payload.detail === 'string' ? payload.detail : payload.detail?.message);
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  organizations: (token?: string | null) => request<Organization[]>('/api/v1/organizations', token),
  createOrganization: (payload: { name: string; slug: string; plan: string }, token?: string | null) =>
    request<Organization>('/api/v1/organizations', token, { method: 'POST', body: JSON.stringify(payload) }),
  commandCenter: (organizationId: string, token?: string | null) =>
    request<CommandMetrics>(`/api/v1/organizations/${organizationId}/command-center`, token),
  artworks: (organizationId: string, token?: string | null, query = '') =>
    request<ArtworkPage>(`/api/v1/organizations/${organizationId}/artworks${query ? `?query=${encodeURIComponent(query)}` : ''}`, token),
  artwork: (organizationId: string, artworkId: string, token?: string | null) =>
    request<Artwork>(`/api/v1/organizations/${organizationId}/artworks/${artworkId}`, token),
  createArtwork: (organizationId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<Artwork>(`/api/v1/organizations/${organizationId}/artworks`, token, { method: 'POST', body: JSON.stringify(payload) }),
  createUploadIntent: (organizationId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<{ asset_id: string; upload_url: string; method: 'PUT'; expires_at: string; max_bytes: number }>(
      `/api/v1/organizations/${organizationId}/assets/upload-intents`,
      token,
      { method: 'POST', body: JSON.stringify(payload) },
    ),
  uploadAsset: async (uploadUrl: string, file: File) => {
    const response = await fetch(uploadUrl, { method: 'PUT', headers: { 'Content-Type': file.type || 'application/octet-stream' }, body: file });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: 'Upload failed.' }));
      throw new Error(payload.error?.message || payload.detail || 'Upload failed.');
    }
    return response.json();
  },
  downloadUrl: (organizationId: string, assetId: string, token?: string | null) =>
    request<{ url: string; expires_in: number }>(`/api/v1/organizations/${organizationId}/assets/${assetId}/download`, token),
  analyzeAsset: (organizationId: string, assetId: string, token?: string | null) =>
    request<VisualAnalysis>(`/api/v1/organizations/${organizationId}/forensics/assets/${assetId}/analyze`, token, { method: 'POST' }),
  similarAssets: (organizationId: string, assetId: string, token?: string | null) =>
    request<{ matches: Array<{ asset_id: string; artwork_id: string; combined_similarity: number; interpretation: string }>; limitations: string[] }>(
      `/api/v1/organizations/${organizationId}/forensics/assets/${assetId}/similar`, token,
    ),
  cases: (organizationId: string, engine?: string, token?: string | null) =>
    request<EngineCase[]>(`/api/v1/organizations/${organizationId}/cases${engine ? `?engine=${engine}` : ''}`, token),
  case: (organizationId: string, caseId: string, token?: string | null) =>
    request<EngineCaseDetail>(`/api/v1/organizations/${organizationId}/cases/${caseId}`, token),
  createInvestigation: (organizationId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<EngineCase>(`/api/v1/organizations/${organizationId}/investigations`, token, { method: 'POST', body: JSON.stringify(payload) }),
  createCopyrightCase: (organizationId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<EngineCase & { match_count: number }>(`/api/v1/organizations/${organizationId}/copyright/cases`, token, { method: 'POST', body: JSON.stringify(payload) }),
  createInspection: (organizationId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<EngineCase & { inspection_id: string; comparison_id: string | null; finding_count: number }>(`/api/v1/organizations/${organizationId}/conservation/inspections`, token, { method: 'POST', body: JSON.stringify(payload) }),
  createCollectionRecord: (organizationId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<{ id: string; case_id: string; completeness_score: number; review_status: string }>(`/api/v1/organizations/${organizationId}/collections/records`, token, { method: 'POST', body: JSON.stringify(payload) }),
  createValuation: (organizationId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<EngineCase>(`/api/v1/organizations/${organizationId}/valuations`, token, { method: 'POST', body: JSON.stringify(payload) }),
  createShipment: (organizationId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<{ id: string; case_id: string; status: string; comparison_id: string | null; limitations: string[] }>(`/api/v1/organizations/${organizationId}/shipments`, token, { method: 'POST', body: JSON.stringify(payload) }),
  createClaim: (organizationId: string, caseId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<{ id: string; review_status: string; stance: string }>(`/api/v1/organizations/${organizationId}/cases/${caseId}/claims`, token, { method: 'POST', body: JSON.stringify(payload) }),
  reviewCase: (organizationId: string, caseId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<{ id: string; case_status: string; decision: string }>(`/api/v1/organizations/${organizationId}/cases/${caseId}/reviews`, token, { method: 'POST', body: JSON.stringify(payload) }),
  generateReport: (organizationId: string, caseId: string, token?: string | null) =>
    request<{ id: string; version: number; review_status: string; content: Record<string, unknown> }>(`/api/v1/organizations/${organizationId}/cases/${caseId}/reports`, token, { method: 'POST' }),
  startAgentRun: (organizationId: string, caseId: string, token?: string | null) =>
    request<{ agent_run_id: string; job_id: string; status: string }>(`/api/v1/organizations/${organizationId}/cases/${caseId}/agent-runs`, token, { method: 'POST', body: JSON.stringify({ external_ai_consent: true }) }),
  evidence: (organizationId: string, token?: string | null, query = '') =>
    request<EvidenceRecord[]>(`/api/v1/organizations/${organizationId}/evidence${query ? `?query=${encodeURIComponent(query)}` : ''}`, token),
  createEvidence: (organizationId: string, payload: Record<string, unknown>, token?: string | null) =>
    request<{ id: string; verification_status: string; chunk_count: number }>(`/api/v1/organizations/${organizationId}/evidence`, token, { method: 'POST', body: JSON.stringify(payload) }),
  agentRuns: (organizationId: string, token?: string | null) =>
    request<AgentRun[]>(`/api/v1/organizations/${organizationId}/agents/runs`, token),
  generatePassport: (organizationId: string, artworkId: string, token?: string | null) =>
    request<{ id: string; version: number; evidence_completeness: number; snapshot: Record<string, unknown> }>(`/api/v1/organizations/${organizationId}/artworks/${artworkId}/passport`, token, { method: 'POST' }),
  billing: (organizationId: string, token?: string | null) =>
    request<{ plan: string; subscription: { status: string; provider: string | null; current_period_end: string | null; cancel_at_period_end: boolean }; entitlements: Array<{ key: string; enabled: boolean; limit: number | null; metadata: Record<string, unknown> }>; usage: Record<string, number>; billing_provider_configured: boolean }>(`/api/v1/organizations/${organizationId}/billing`, token),
  checkout: (organizationId: string, plan: string, token?: string | null) =>
    request<{ url: string; session_id: string }>(`/api/v1/organizations/${organizationId}/billing/checkout`, token, { method: 'POST', body: JSON.stringify({ plan }) }),
};
