export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: 'artist' | 'professional' | 'gallery' | 'institution' | 'enterprise';
  role: string;
}

export interface ArtworkAsset {
  id: string;
  kind: string;
  original_name: string;
  verified_mime_type: string | null;
  size_bytes: number;
  sha256: string | null;
  status: 'pending' | 'quarantined' | 'ready' | 'rejected';
  is_primary: boolean;
  created_at: string;
}

export interface Artwork {
  id: string;
  organization_id: string;
  title: string;
  artist_attribution: string | null;
  attribution_status: 'claimed' | 'verified' | 'disputed' | 'unknown';
  creation_year_from: number | null;
  creation_year_to: number | null;
  date_precision: 'exact' | 'year' | 'range' | 'circa' | 'unknown';
  medium: string | null;
  dimensions: Record<string, unknown>;
  description: string | null;
  current_custody: string | null;
  status: 'draft' | 'active' | 'archived';
  created_at: string;
  updated_at: string;
  assets: ArtworkAsset[];
}

export interface ArtworkPage {
  items: Artwork[];
  page: number;
  page_size: number;
  total: number;
}

export interface CommandMetrics {
  registered_artworks: number;
  active_jobs: number;
  pending_reviews: number;
  potential_copyright_matches: number;
  condition_alerts: number;
  active_shipments: number;
  collection_completeness: number | null;
  onboarding_complete: boolean;
}
