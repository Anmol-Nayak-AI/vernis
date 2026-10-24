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
  active_investigations: number;
  active_jobs: number;
  pending_reviews: number;
  potential_copyright_matches: number;
  condition_alerts: number;
  active_shipments: number;
  collection_completeness: number | null;
  workflows_this_month: number;
  recent_workflows: Array<{ id: string; engine: EngineKey; title: string; status: string; updated_at: string }>;
  onboarding_complete: boolean;
}

export interface VisualAnalysis {
  job_id: string;
  status: string;
  model_identifier: string;
  model_version: string;
  fingerprint: {
    sha256: string;
    perceptual_hash: string;
    width: number;
    height: number;
    metadata: Record<string, unknown>;
  };
  embedding: { id: string; dimensions: number; norm: string };
  evaluation_status: string;
}

export type EngineKey = 'artsentinel' | 'artshield' | 'conservavision' | 'musegraph' | 'artvaluate' | 'arttransit';

export interface EngineCase {
  id: string;
  organization_id: string;
  artwork_id: string;
  engine: EngineKey;
  title: string;
  status: string;
  risk_level: string;
  input_data: Record<string, unknown>;
  summary: string | null;
  limitations: string[];
  created_at: string;
  updated_at: string;
}

export interface EngineCaseDetail extends EngineCase {
  claims: Array<{ id: string; claim_text: string; stance: string; confidence: number | null; review_status: string; evidence_document_id: string | null; source_locator: string | null }>;
  reviews: Array<{ id: string; decision: string; notes: string; reviewer_id: string; created_at: string }>;
  reports: Array<{ id: string; version: number; title: string; review_status: string; created_at: string }>;
}

export interface EvidenceRecord {
  id: string;
  artwork_id: string;
  title: string;
  kind: string;
  source_uri: string | null;
  source_authority: string | null;
  verification_status: string;
  sensitivity: string;
  citation: string;
}

export interface AgentRun {
  id: string;
  case_id: string;
  crew_name: string;
  status: string;
  model_identifier: string | null;
  token_usage: Record<string, unknown>;
  errors: Array<Record<string, unknown>>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}
