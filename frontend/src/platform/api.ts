import type { Artwork, ArtworkPage, CommandMetrics, Organization } from './types';

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
};
