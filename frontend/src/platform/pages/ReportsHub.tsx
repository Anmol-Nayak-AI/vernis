import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { ErrorState, LoadingState } from '../components/PageState';

export function ReportsHub() {
  const { orgId = '' } = useParams();
  const { session } = useAuth();
  const cases = useQuery({ queryKey: ['cases', orgId], queryFn: () => api.cases(orgId, undefined, session?.access_token) });
  if (cases.isLoading) return <LoadingState label="Opening reports" />;
  if (cases.error) return <ErrorState error={cases.error} />;
  return <section className="v2-page"><header className="v2-page-header"><div><p className="v2-kicker">Organization reporting</p><h1>Reports</h1><p>Open a workflow to create a versioned report from real claims, citations, limitations, and named human decisions.</p></div></header>{cases.data?.length ? <div className="v2-case-list">{cases.data.map((item) => <Link key={item.id} to={`/app/${orgId}/cases/${item.id}`}><span className={`v2-status is-${item.status}`}>{item.status.replace(/_/g, ' ')}</span><div><small>{item.engine}</small><h2>{item.title}</h2><p>{item.summary || 'No summary yet.'}</p></div></Link>)}</div> : <div className="v2-state"><FileText /><strong>No reportable cases</strong><span>Create an engine workflow first.</span></div>}</section>;
}
