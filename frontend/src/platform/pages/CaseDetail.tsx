import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Bot, CheckCircle2, FilePlus2 } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { ErrorState, LoadingState } from '../components/PageState';

export function CaseDetail() {
  const { orgId = '', caseId = '' } = useParams();
  const { session } = useAuth();
  const queryClient = useQueryClient();
  const detail = useQuery({ queryKey: ['case', orgId, caseId], queryFn: () => api.case(orgId, caseId, session?.access_token) });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['case', orgId, caseId] });
  const report = useMutation({ mutationFn: () => api.generateReport(orgId, caseId, session?.access_token), onSuccess: refresh });
  const review = useMutation({ mutationFn: () => api.reviewCase(orgId, caseId, { decision: 'approved', notes: 'Reviewed and approved as an evidence record within the stated limitations.' }, session?.access_token), onSuccess: refresh });
  const agent = useMutation({ mutationFn: () => api.startAgentRun(orgId, caseId, session?.access_token), onSuccess: refresh });
  if (detail.isLoading) return <LoadingState label="Opening case record" />;
  if (detail.error) return <ErrorState error={detail.error} />;
  const item = detail.data!;
  return <section className="v2-page v2-case-detail"><Link className="v2-back" to={`/app/${orgId}/engines/${item.engine}`}><ArrowLeft />{item.engine}</Link><header className="v2-page-header"><div><p className="v2-kicker">{item.engine} / {item.id.slice(0, 8)}</p><h1>{item.title}</h1><p>{item.summary || 'No workflow summary has been produced.'}</p></div><span className={`v2-status is-${item.status}`}>{item.status.replace(/_/g, ' ')}</span></header><div className="v2-case-actions"><button onClick={() => report.mutate()} disabled={report.isPending}><FilePlus2 />{report.isPending ? 'Generating…' : 'Generate cited report'}</button><button onClick={() => agent.mutate()} disabled={agent.isPending}><Bot />{agent.isPending ? 'Queueing…' : 'Run consented CrewAI review'}</button><button onClick={() => review.mutate()} disabled={review.isPending}><CheckCircle2 />Approve after review</button></div><p className="v2-consent-note">Starting an agent review sends the case’s authorized text evidence to the configured AI provider. Images remain local; every result still requires human approval.</p>{(report.error || review.error || agent.error) && <p className="v2-form-error">{report.error?.message || review.error?.message || agent.error?.message}</p>}<div className="v2-case-columns"><section><p className="v2-kicker">Evidence-backed claims</p><h2>{item.claims.length} claim{item.claims.length === 1 ? '' : 's'}</h2>{item.claims.length ? item.claims.map((claim) => <article key={claim.id}><strong>{claim.stance}</strong><p>{claim.claim_text}</p><small>{claim.source_locator || 'No source locator supplied'} · {claim.review_status}</small></article>) : <p>No claims have been recorded. Reports will preserve this gap instead of filling it.</p>}</section><section><p className="v2-kicker">Human review history</p><h2>{item.reviews.length} decision{item.reviews.length === 1 ? '' : 's'}</h2>{item.reviews.map((entry) => <article key={entry.id}><strong>{entry.decision}</strong><p>{entry.notes}</p></article>)}<p className="v2-kicker">Report versions</p>{item.reports.map((entry) => <article key={entry.id}><strong>Version {entry.version}</strong><p>{entry.title}</p><small>{entry.review_status}</small></article>)}</section></div><section className="v2-limitations"><p className="v2-kicker">System limitations</p><ul>{item.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></section></section>;
}
