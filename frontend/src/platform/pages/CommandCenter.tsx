import { useQuery } from '@tanstack/react-query';
import { ArrowRight, CircleAlert, Clock3, Fingerprint, PackageCheck, Plus, ShieldCheck, Sparkles } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { ErrorState, LoadingState } from '../components/PageState';

export function CommandCenter() {
  const { orgId = '' } = useParams();
  const { session } = useAuth();
  const metrics = useQuery({ queryKey: ['command-center', orgId], queryFn: () => api.commandCenter(orgId, session?.access_token) });
  if (metrics.isLoading) return <LoadingState label="Building the command view" />;
  if (metrics.error) return <ErrorState error={metrics.error} />;
  const data = metrics.data!;
  const cards = [
    ['Registered artworks', data.registered_artworks, Fingerprint, 'Canonical records in this organization'],
    ['Active workflows', data.active_jobs, Clock3, 'Queued, running, or awaiting review'],
    ['Expert reviews', data.pending_reviews, ShieldCheck, 'Decisions requiring a named reviewer'],
    ['Copyright matches', data.potential_copyright_matches, CircleAlert, 'Potential matches—not legal conclusions'],
    ['Condition alerts', data.condition_alerts, Sparkles, 'Observable changes awaiting review'],
    ['Active shipments', data.active_shipments, PackageCheck, 'Custody journeys currently in progress'],
  ] as const;
  return <section className="v2-page">
    <header className="v2-page-header"><div><p className="v2-kicker">Organization intelligence / Live records</p><h1>Command Center</h1><p>A truthful operational view of artwork records, reviews, evidence, and running analysis.</p></div><Link className="v2-primary" to={`/app/${orgId}/artworks?new=1`}><Plus />Register artwork</Link></header>
    <div className="v2-metric-grid">{cards.map(([label, value, Icon, description]) => <article key={label}><span><Icon /></span><small>{label}</small><strong>{value}</strong><p>{description}</p></article>)}</div>
    {!data.onboarding_complete ? <section className="v2-onboarding-panel"><div><p className="v2-kicker">Your first intelligence record</p><h2>Start with the artwork—not the engine.</h2><p>Register one work and upload its authorized primary image. Every future investigation, condition report, collection relationship, valuation reference, and shipment will reuse that identity.</p></div><ol><li><b>01</b><span><strong>Register identity</strong><small>Known, unknown, disputed, and approximate values are preserved.</small></span></li><li><b>02</b><span><strong>Add evidence</strong><small>Files are validated, fingerprinted, and tenant-scoped.</small></span></li><li><b>03</b><span><strong>Choose a workflow</strong><small>No artwork is forced through all six engines.</small></span></li></ol><Link to={`/app/${orgId}/artworks?new=1`}>Register the first artwork <ArrowRight /></Link></section>
      : <section className="v2-activity-panel"><div><p className="v2-kicker">Recent activity</p><h2>Organization activity will appear here.</h2><p>Audit events exist for new records. A richer event stream arrives with agent jobs and human review workflows.</p></div><Link to={`/app/${orgId}/artworks`}>Open artwork registry <ArrowRight /></Link></section>}
  </section>;
}
