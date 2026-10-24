import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, FolderSearch, Plus, ShieldAlert } from 'lucide-react';
import { FormEvent, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { ErrorState, LoadingState } from '../components/PageState';
import type { EngineKey } from '../types';

const CONFIG: Record<EngineKey, { name: string; kicker: string; description: string; empty: string; notice: string }> = {
  artsentinel: { name: 'ArtSentinel', kicker: 'Authenticity & provenance due diligence', description: 'Build a cited investigation around supplied claims, visual retrieval, provenance gaps, contradictions, and expert review.', empty: 'No investigations yet', notice: 'Vernis does not authenticate artworks or classify them as forged.' },
  artshield: { name: 'ArtShield', kicker: 'Authorized visual rights monitoring', description: 'Compare a protected work against this organization’s authorized index and review potential near-duplicates without making legal accusations.', empty: 'No monitoring cases yet', notice: 'Similarity does not establish copyright ownership or infringement.' },
  conservavision: { name: 'ConservaVision', kicker: 'Condition intelligence', description: 'Record an inspection and, when a baseline exists, measure registered observable visual changes for conservator review.', empty: 'No condition inspections yet', notice: 'Photographs cannot reveal every form of deterioration; treatment decisions require a conservator.' },
  musegraph: { name: 'MuseGraph', kicker: 'Collection intelligence', description: 'Create an accession record linked to the shared artwork identity and place supplied catalog metadata into a review queue.', empty: 'No catalog reviews yet', notice: 'Imported and extracted metadata remains unverified until cataloger review.' },
  artvaluate: { name: 'ArtValuate', kicker: 'Market evidence research', description: 'Create a valuation research case, attach licensed comparables, and build an explainable statistical range when coverage is sufficient.', empty: 'No valuation research yet', notice: 'Research estimates are not certified appraisals or investment advice.' },
  arttransit: { name: 'ArtTransit', kicker: 'Shipment & custody evidence', description: 'Open a shipment evidence record with packaging, custody, and optional before/arrival visual comparison.', empty: 'No shipments yet', notice: 'Visual changes do not determine when damage occurred, liability, or claim approval.' },
};

export function EngineWorkspace({ engine }: { engine: EngineKey }) {
  const { orgId = '' } = useParams();
  const { session } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [artworkId, setArtworkId] = useState('');
  const [title, setTitle] = useState('');
  const [primaryAssetId, setPrimaryAssetId] = useState('');
  const [baselineAssetId, setBaselineAssetId] = useState('');
  const [accession, setAccession] = useState('');
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const config = CONFIG[engine];
  const cases = useQuery({ queryKey: ['cases', orgId, engine], queryFn: () => api.cases(orgId, engine, session?.access_token) });
  const artworks = useQuery({ queryKey: ['artworks', orgId], queryFn: () => api.artworks(orgId, session?.access_token) });
  const selected = useMemo(() => artworks.data?.items.find((item) => item.id === artworkId), [artworks.data, artworkId]);
  const assets = selected?.assets.filter((asset) => asset.status === 'ready') || [];
  const create = useMutation({
    mutationFn: async () => {
      const common = { artwork_id: artworkId, title: title || `${config.name} · ${selected?.title || 'new case'}` };
      if (engine === 'artsentinel') return api.createInvestigation(orgId, common, session?.access_token);
      if (engine === 'artshield') return api.createCopyrightCase(orgId, { ...common, source_asset_id: primaryAssetId }, session?.access_token);
      if (engine === 'conservavision') return api.createInspection(orgId, { ...common, asset_id: primaryAssetId, baseline_asset_id: baselineAssetId || null }, session?.access_token);
      if (engine === 'musegraph') return api.createCollectionRecord(orgId, { artwork_id: artworkId, accession_number: accession, catalog_metadata: {} }, session?.access_token);
      if (engine === 'artvaluate') return api.createValuation(orgId, common, session?.access_token);
      return api.createShipment(orgId, { ...common, reference: accession, origin, destination, pre_asset_id: baselineAssetId || null, arrival_asset_id: primaryAssetId || null, packaging: {} }, session?.access_token);
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['cases', orgId, engine] });
      setOpen(false);
      const caseId = 'case_id' in result ? String(result.case_id) : String(result.id);
      navigate(`/app/${orgId}/cases/${caseId}`);
    },
  });
  const requiresAsset = ['artshield', 'conservavision'].includes(engine);
  const requiresAccession = ['musegraph', 'arttransit'].includes(engine);
  const valid = Boolean(artworkId && (!requiresAsset || primaryAssetId) && (!requiresAccession || accession) && (engine !== 'arttransit' || (origin && destination)));
  const submit = (event: FormEvent) => { event.preventDefault(); if (valid) create.mutate(); };
  if (cases.isLoading || artworks.isLoading) return <LoadingState label={`Opening ${config.name}`} />;
  if (cases.error) return <ErrorState error={cases.error} />;
  return <section className="v2-page v2-engine-page">
    <header className="v2-page-header"><div><p className="v2-kicker">{config.kicker}</p><h1>{config.name}</h1><p>{config.description}</p></div><button className="v2-primary" onClick={() => setOpen(true)}><Plus />New {engine === 'arttransit' ? 'shipment' : 'case'}</button></header>
    <div className="v2-boundary-notice"><ShieldAlert /><span><strong>Human decision boundary</strong><small>{config.notice}</small></span></div>
    {cases.data?.length ? <div className="v2-case-list">{cases.data.map((item) => <Link key={item.id} to={`/app/${orgId}/cases/${item.id}`}><span className={`v2-status is-${item.status}`}>{item.status.replace(/_/g, ' ')}</span><div><small>{item.engine}</small><h2>{item.title}</h2><p>{item.summary || 'Case created. Evidence and review activity will appear here.'}</p></div><ArrowRight /></Link>)}</div> : <div className="v2-state"><FolderSearch /><strong>{config.empty}</strong><span>Start from a registered artwork. Vernis will not create demo findings.</span></div>}
    {open && <div className="v2-dialog-backdrop" role="presentation"><div className="v2-dialog" role="dialog" aria-modal="true" aria-labelledby="engine-create-title"><header><div><p className="v2-kicker">{config.name}</p><h2 id="engine-create-title">Create a real workflow</h2></div><button type="button" onClick={() => setOpen(false)}>×</button></header><form onSubmit={submit}><div className="v2-form-grid"><label className="is-wide"><span>Artwork identity</span><select value={artworkId} onChange={(event) => { setArtworkId(event.target.value); setPrimaryAssetId(''); setBaselineAssetId(''); }} required><option value="">Select an artwork</option>{artworks.data?.items.map((item) => <option value={item.id} key={item.id}>{item.title} · {item.artist_attribution || 'unknown artist'}</option>)}</select></label><label className="is-wide"><span>Case title</span><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder={`${config.name} review`} /></label>{(requiresAsset || engine === 'arttransit') && <label><span>{engine === 'arttransit' ? 'Arrival image (optional)' : 'Analysis image'}</span><select value={primaryAssetId} onChange={(event) => setPrimaryAssetId(event.target.value)} required={requiresAsset}><option value="">{assets.length ? 'Select an asset' : 'No ready assets'}</option>{assets.map((asset) => <option value={asset.id} key={asset.id}>{asset.original_name}</option>)}</select></label>}{(engine === 'conservavision' || engine === 'arttransit') && <label><span>{engine === 'arttransit' ? 'Pre-shipment image (optional)' : 'Historical baseline (optional)'}</span><select value={baselineAssetId} onChange={(event) => setBaselineAssetId(event.target.value)}><option value="">No baseline</option>{assets.filter((asset) => asset.id !== primaryAssetId).map((asset) => <option value={asset.id} key={asset.id}>{asset.original_name}</option>)}</select></label>}{requiresAccession && <label><span>{engine === 'musegraph' ? 'Accession number' : 'Shipment reference'}</span><input value={accession} onChange={(event) => setAccession(event.target.value)} required /></label>}{engine === 'arttransit' && <><label><span>Origin</span><input value={origin} onChange={(event) => setOrigin(event.target.value)} required /></label><label><span>Destination</span><input value={destination} onChange={(event) => setDestination(event.target.value)} required /></label></>}</div>{create.error && <p className="v2-form-error">{create.error.message}</p>}<footer><p>{config.notice}</p><button className="v2-primary" type="submit" disabled={!valid || create.isPending}>{create.isPending ? 'Creating…' : 'Create workflow'}</button></footer></form></div></div>}
  </section>;
}
