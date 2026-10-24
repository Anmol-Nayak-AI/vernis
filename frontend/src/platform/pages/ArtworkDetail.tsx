import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, BadgeCheck, FileSearch, Fingerprint, History, LoaderCircle, ScanSearch, Scale, ShieldCheck } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { ArtworkImage } from '../components/ArtworkImage';
import { ErrorState, LoadingState } from '../components/PageState';

export function ArtworkDetail() {
  const { orgId = '', artworkId = '' } = useParams();
  const { session } = useAuth();
  const artwork = useQuery({ queryKey: ['artwork', orgId, artworkId], queryFn: () => api.artwork(orgId, artworkId, session?.access_token) });
  const primary = artwork.data?.assets.find((asset) => asset.is_primary) || artwork.data?.assets[0];
  const analysis = useMutation({ mutationFn: () => api.analyzeAsset(orgId, primary!.id, session?.access_token) });
  const similarities = useQuery({
    queryKey: ['visual-similarity', orgId, primary?.id],
    queryFn: () => api.similarAssets(orgId, primary!.id, session?.access_token),
    enabled: Boolean(primary && analysis.data),
  });
  const passport = useMutation({ mutationFn: () => api.generatePassport(orgId, artworkId, session?.access_token) });
  if (artwork.isLoading) return <LoadingState label="Opening artwork record" />;
  if (artwork.error) return <ErrorState error={artwork.error} />;
  const item = artwork.data!;
  const year = item.creation_year_from ? item.creation_year_to && item.creation_year_to !== item.creation_year_from ? `${item.creation_year_from}–${item.creation_year_to}` : String(item.creation_year_from) : 'Unknown date';
  return <section className="v2-page v2-artwork-detail">
    <Link className="v2-back" to={`/app/${orgId}/artworks`}><ArrowLeft />Artwork Registry</Link>
    <header><div><p className="v2-kicker">Artwork / {item.id.slice(0, 8).toUpperCase()}</p><h1>{item.title}</h1><p>{item.artist_attribution || 'Artist attribution unknown'} · {year}</p></div><span className={`v2-status is-${item.attribution_status}`}>{item.attribution_status === 'verified' && <BadgeCheck />}{item.attribution_status} attribution</span></header>
    <div className="v2-artwork-identity"><div className="v2-artwork-viewer"><ArtworkImage artwork={item} /><div><span>Primary visual asset</span><small>{primary?.verified_mime_type || 'No asset'}{primary?.size_bytes ? ` · ${(primary.size_bytes / 1024 / 1024).toFixed(2)} MB` : ''}</small></div></div><aside><p className="v2-kicker">Identity record</p><dl><div><dt>Claimed artist</dt><dd>{item.artist_attribution || 'Unknown'}</dd></div><div><dt>Creation period</dt><dd>{year} <small>{item.date_precision}</small></dd></div><div><dt>Medium</dt><dd>{item.medium || 'Not recorded'}</dd></div><div><dt>Current custody</dt><dd>{item.current_custody || 'Not recorded'}</dd></div><div><dt>Record status</dt><dd>{item.status}</dd></div></dl>{primary?.sha256 && <div className="v2-fingerprint"><Fingerprint /><span><small>SHA-256 file fingerprint</small><code>{primary.sha256}</code><em>Identifies these bytes—not authenticity.</em></span></div>}</aside></div>
    <nav className="v2-record-tabs" aria-label="Artwork record sections"><button className="is-active" aria-current="page">Overview</button><span>Assets <b>{item.assets.length}</b></span><span>Evidence · planned</span><span>Provenance · planned</span><span>Condition · planned</span><span>Rights · planned</span><span>Activity · planned</span></nav>
    <div className="v2-passport-action"><History /><span><strong>Artwork Intelligence Passport</strong><small>Versioned JSON/PDF-ready snapshot across evidence and all six workflows. Restricted evidence is excluded from its public scope.</small></span><button onClick={() => passport.mutate()} disabled={passport.isPending}>{passport.isPending ? 'Generating…' : 'Generate new version'}</button>{passport.data && <em>v{passport.data.version} · {passport.data.evidence_completeness}% evidence completeness</em>}{passport.error && <em>{passport.error.message}</em>}</div>
    <div className="v2-record-grid"><section><p className="v2-kicker">Record description</p><h2>Known information</h2><p>{item.description || 'No description has been supplied. Vernis does not invent missing metadata.'}</p></section><section><p className="v2-kicker">Shared visual intelligence</p><h2>Fingerprint this asset</h2><p>Run Vernis’s CPU-compatible visual baseline to create a perceptual hash and a 96-dimensional spatial-color descriptor.</p>{primary ? <button className="v2-primary" disabled={analysis.isPending} onClick={() => analysis.mutate()}>{analysis.isPending ? <LoaderCircle className="v2-spin" /> : <ScanSearch />}{analysis.isPending ? 'Analyzing…' : analysis.data ? 'Run again' : 'Analyze visual asset'}</button> : <p>Add a ready image before running visual analysis.</p>}{analysis.error && <p className="v2-inline-error">{analysis.error.message}</p>}{analysis.data && <div className="v2-inference-result"><span><strong>{analysis.data.model_identifier}</strong><small>v{analysis.data.model_version} · {analysis.data.evaluation_status.replace(/_/g, ' ')}</small></span><dl><div><dt>Perceptual hash</dt><dd><code>{analysis.data.fingerprint.perceptual_hash}</code></dd></div><div><dt>Image</dt><dd>{analysis.data.fingerprint.width} × {analysis.data.fingerprint.height}</dd></div><div><dt>Embedding</dt><dd>{analysis.data.embedding.dimensions} dimensions</dd></div><div><dt>Indexed neighbors</dt><dd>{similarities.data?.matches.length ?? '…'}</dd></div></dl><p>Retrieval signal only. It does not establish authorship, authenticity, ownership, damage, or infringement.</p></div>}</section><section><p className="v2-kicker">Available workflows</p><div className="v2-workflow-list"><article><ShieldCheck /><span><strong>ArtSentinel</strong><small>Authenticity and provenance due diligence</small></span><em>Phase 3</em></article><article><FileSearch /><span><strong>ConservaVision</strong><small>Condition inspection and visual comparison</small></span><em>Phase 5</em></article><article><Scale /><span><strong>ArtValuate</strong><small>Evidence-backed market research</small></span><em>Phase 7</em></article><article><History /><span><strong>Artwork Passport</strong><small>Cross-engine reviewed record</small></span><em>Phase 9</em></article></div></section></div>
  </section>;
}
