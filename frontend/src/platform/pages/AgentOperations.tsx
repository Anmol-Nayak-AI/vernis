import { useQuery } from '@tanstack/react-query';
import { Bot, Clock3 } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { ErrorState, LoadingState } from '../components/PageState';

export function AgentOperations() {
  const { orgId = '' } = useParams();
  const { session } = useAuth();
  const runs = useQuery({ queryKey: ['agent-runs', orgId], queryFn: () => api.agentRuns(orgId, session?.access_token), refetchInterval: 5000 });
  if (runs.isLoading) return <LoadingState label="Opening agent operations" />;
  if (runs.error) return <ErrorState error={runs.error} />;
  return <section className="v2-page"><header className="v2-page-header"><div><p className="v2-kicker">Auditable orchestration</p><h1>Agent Operations</h1><p>Workflow state, model identity, tool events, bounded failures, usage, and human approval handoffs—without private chain-of-thought.</p></div></header>{runs.data?.length ? <div className="v2-evidence-list">{runs.data.map((run) => <article key={run.id}><span className={`v2-status is-${run.status}`}>{run.status.replace(/_/g, ' ')}</span><div><small>{run.crew_name}</small><h2>{run.model_identifier || 'Model not started'}</h2><p><Clock3 /> {run.started_at ? `Started ${new Date(run.started_at).toLocaleString()}` : 'Queued'}</p><Link to={`/app/${orgId}/cases/${run.case_id}`}>Open case</Link></div></article>)}</div> : <div className="v2-state"><Bot /><strong>No agent runs</strong><span>Consented ArtSentinel runs will appear here. Vernis does not simulate activity.</span></div>}</section>;
}
