import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, FileImage, Grid2X2, List, Plus, Search, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { z } from 'zod';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { ArtworkImage } from '../components/ArtworkImage';
import { ErrorState, LoadingState } from '../components/PageState';

const schema = z.object({
  title: z.string().min(1, 'Title is required.').max(240),
  artist_attribution: z.string().max(240),
  attribution_status: z.enum(['claimed', 'verified', 'disputed', 'unknown']),
  medium: z.string().max(320),
  description: z.string().max(10000),
});
type Values = z.infer<typeof schema>;

function ArtworkCreateDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { orgId = '' } = useParams();
  const { session } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { title: '', artist_attribution: '', attribution_status: 'unknown', medium: '', description: '' } });
  const create = useMutation({
    mutationFn: async (values: Values) => {
      const artwork = await api.createArtwork(orgId, {
        ...values,
        artist_attribution: values.artist_attribution || null,
        medium: values.medium || null,
        description: values.description || null,
      }, session?.access_token);
      if (file) {
        const intent = await api.createUploadIntent(orgId, { artwork_id: artwork.id, file_name: file.name, content_type: file.type || 'application/octet-stream', size_bytes: file.size, kind: 'primary_image' }, session?.access_token);
        await api.uploadAsset(intent.upload_url, file);
      }
      return artwork;
    },
    onSuccess: async (artwork) => {
      await queryClient.invalidateQueries({ queryKey: ['artworks', orgId] });
      await queryClient.invalidateQueries({ queryKey: ['command-center', orgId] });
      navigate(`/app/${orgId}/artworks/${artwork.id}`);
    },
  });
  if (!open) return null;
  return <div className="v2-dialog-backdrop" role="presentation" onMouseDown={onClose}><section className="v2-dialog" role="dialog" aria-modal="true" aria-labelledby="register-title" onMouseDown={(event) => event.stopPropagation()}><header><div><p className="v2-kicker">Canonical artwork identity</p><h2 id="register-title">Register an artwork</h2></div><button onClick={onClose} aria-label="Close registration"><X /></button></header><form onSubmit={form.handleSubmit((values) => create.mutate(values))}>
    <button className={`v2-file-drop ${file ? 'has-file' : ''}`} type="button" onClick={() => fileRef.current?.click()}><FileImage /><span><strong>{file?.name || 'Add an authorized primary image'}</strong><small>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · validated after upload` : 'PNG, JPEG, WebP, or TIFF · 50 MB maximum'}</small></span><em>{file ? 'Replace' : 'Choose file'}</em></button><input ref={fileRef} hidden type="file" accept="image/png,image/jpeg,image/webp,image/tiff" onChange={(event) => setFile(event.target.files?.[0] || null)} />
    <div className="v2-form-grid"><label className="is-wide"><span>Artwork title *</span><input {...form.register('title')} placeholder="Untitled work" />{form.formState.errors.title && <small>{form.formState.errors.title.message}</small>}</label><label><span>Claimed artist attribution</span><input {...form.register('artist_attribution')} placeholder="Unknown if not supplied" /></label><label><span>Attribution status</span><select {...form.register('attribution_status')}><option value="unknown">Unknown</option><option value="claimed">Claimed</option><option value="verified">Human verified</option><option value="disputed">Disputed</option></select></label><label className="is-wide"><span>Medium</span><input {...form.register('medium')} placeholder="Oil on linen, gelatin silver print…" /></label><label className="is-wide"><span>Description</span><textarea {...form.register('description')} rows={4} placeholder="Record only what is known or explicitly claimed." /></label></div>
    {create.error && <div className="v2-form-error">{create.error.message}</div>}
    <footer><p>A SHA-256 fingerprint identifies the uploaded bytes; it does not prove artwork authenticity.</p><button className="v2-primary" disabled={create.isPending}>{create.isPending ? 'Securing record…' : 'Create artwork record'} <ArrowRight /></button></footer>
  </form></section></div>;
}

export function ArtworkRegistry() {
  const { orgId = '' } = useParams();
  const { session } = useAuth();
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [layout, setLayout] = useState<'grid' | 'list'>('grid');
  const artworks = useQuery({ queryKey: ['artworks', orgId, query], queryFn: () => api.artworks(orgId, session?.access_token, query) });
  const dialogOpen = params.get('new') === '1';
  return <section className="v2-page">
    <header className="v2-page-header"><div><p className="v2-kicker">Shared registry / Organization scoped</p><h1>Artwork Registry</h1><p>One stable identity for every authorized investigation, condition record, collection relationship, valuation reference, and shipment.</p></div><button className="v2-primary" onClick={() => setParams({ new: '1' })}><Plus />Register artwork</button></header>
    <div className="v2-registry-toolbar"><label><Search /><span className="sr-only">Search artworks</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search title…" /></label><div><span>{artworks.data?.total ?? 0} records</span><button className={layout === 'grid' ? 'is-active' : ''} onClick={() => setLayout('grid')} aria-label="Grid view"><Grid2X2 /></button><button className={layout === 'list' ? 'is-active' : ''} onClick={() => setLayout('list')} aria-label="List view"><List /></button></div></div>
    {artworks.isLoading ? <LoadingState label="Opening the registry" /> : artworks.error ? <ErrorState error={artworks.error} /> : artworks.data?.items.length ? <div className={`v2-artwork-${layout}`}>{artworks.data.items.map((artwork) => <Link key={artwork.id} to={`/app/${orgId}/artworks/${artwork.id}`}><ArtworkImage artwork={artwork} /><div><small>{artwork.attribution_status} attribution</small><h2>{artwork.title}</h2><p>{artwork.artist_attribution || 'Artist unknown'} · {artwork.medium || 'Medium not recorded'}</p><footer><span>{artwork.assets.length ? `${artwork.assets.length} asset${artwork.assets.length > 1 ? 's' : ''}` : 'No assets'}</span><em>{artwork.status}</em></footer></div></Link>)}</div> : <div className="v2-empty-registry"><span><FileImage /></span><h2>No artworks registered yet.</h2><p>Start with a truthful identity record. Unknown and disputed values remain explicit and can be reviewed later.</p><button className="v2-primary" onClick={() => setParams({ new: '1' })}><Plus />Register the first artwork</button></div>}
    <ArtworkCreateDialog open={dialogOpen} onClose={() => setParams({})} />
  </section>;
}
