import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FilePlus2, Search } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { ErrorState, LoadingState } from '../components/PageState';

export function EvidenceLibrary() {
  const { orgId = '' } = useParams();
  const { session } = useAuth();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [artworkId, setArtworkId] = useState('');
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const records = useQuery({ queryKey: ['evidence', orgId, query], queryFn: () => api.evidence(orgId, session?.access_token, query) });
  const artworks = useQuery({ queryKey: ['artworks', orgId], queryFn: () => api.artworks(orgId, session?.access_token) });
  const create = useMutation({ mutationFn: () => api.createEvidence(orgId, { artwork_id: artworkId, title, kind: 'other', extracted_text: text || null, sensitivity: 'internal', external_ai_consent: false }, session?.access_token), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['evidence', orgId] }); setOpen(false); setTitle(''); setText(''); } });
  const submit = (event: FormEvent) => { event.preventDefault(); create.mutate(); };
  if (records.isLoading) return <LoadingState label="Opening evidence library" />;
  if (records.error) return <ErrorState error={records.error} />;
  return <section className="v2-page"><header className="v2-page-header"><div><p className="v2-kicker">Shared evidence graph</p><h1>Evidence Library</h1><p>Tenant-scoped source records with sensitivity, verification state, text passages, and stable citation labels.</p></div><button className="v2-primary" onClick={() => setOpen(true)}><FilePlus2 />Add evidence</button></header><div className="v2-registry-toolbar"><label><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search evidence text and titles" /></label><div><span>{records.data?.length || 0} records</span></div></div>{records.data?.length ? <div className="v2-evidence-list">{records.data.map((record) => <article key={record.id}><span className="v2-status">{record.verification_status}</span><div><small>{record.kind} · {record.sensitivity}</small><h2>{record.title}</h2><p>{record.citation}</p><em>{record.source_authority || 'No source authority supplied'}</em></div></article>)}</div> : <div className="v2-state"><FilePlus2 /><strong>No evidence records</strong><span>Add a source without turning its text into verified truth.</span></div>}{open && <div className="v2-dialog-backdrop"><div className="v2-dialog" role="dialog" aria-modal="true"><header><div><p className="v2-kicker">Evidence ingestion</p><h2>Add a source record</h2></div><button onClick={() => setOpen(false)}>×</button></header><form onSubmit={submit}><div className="v2-form-grid"><label className="is-wide"><span>Artwork</span><select value={artworkId} onChange={(event) => setArtworkId(event.target.value)} required><option value="">Select artwork</option>{artworks.data?.items.map((artwork) => <option key={artwork.id} value={artwork.id}>{artwork.title}</option>)}</select></label><label className="is-wide"><span>Evidence title</span><input value={title} onChange={(event) => setTitle(event.target.value)} required /></label><label className="is-wide"><span>Supplied text (optional)</span><textarea rows={8} value={text} onChange={(event) => setText(event.target.value)} placeholder="Text is stored as unverified source material and chunked for citation." /></label></div>{create.error && <p className="v2-form-error">{create.error.message}</p>}<footer><p>No external AI processing is enabled by this action.</p><button className="v2-primary" disabled={create.isPending}>{create.isPending ? 'Saving…' : 'Save evidence'}</button></footer></form></div></div>}</section>;
}
