import { useMutation, useQuery } from '@tanstack/react-query';
import { CreditCard, ShieldCheck } from 'lucide-react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { ErrorState, LoadingState } from '../components/PageState';

export function OrganizationSettings() {
  const { orgId = '' } = useParams();
  const { session } = useAuth();
  const billing = useQuery({ queryKey: ['billing', orgId], queryFn: () => api.billing(orgId, session?.access_token) });
  const checkout = useMutation({ mutationFn: (plan: string) => api.checkout(orgId, plan, session?.access_token), onSuccess: (result) => { window.location.assign(result.url); } });
  if (billing.isLoading) return <LoadingState label="Opening organization settings" />;
  if (billing.error) return <ErrorState error={billing.error} />;
  const data = billing.data!;
  return <section className="v2-page"><header className="v2-page-header"><div><p className="v2-kicker">Organization governance</p><h1>Settings & billing</h1><p>Server-enforced plan entitlements, measured workflow usage, hosted billing, and provider configuration state.</p></div></header><div className="v2-case-columns"><section><p className="v2-kicker">Current plan</p><h2>{data.plan}</h2><article><strong>Subscription</strong><p>{data.subscription.status}</p><small>{data.subscription.provider || 'No hosted subscription connected'}</small></article><article><strong>Workflow usage this month</strong><p>{data.usage.workflow_case_created || 0} cases</p></article>{checkout.error && <p className="v2-form-error">{checkout.error.message}</p>}<button className="v2-primary" disabled={!data.billing_provider_configured || checkout.isPending} onClick={() => checkout.mutate(data.plan)}><CreditCard />{data.billing_provider_configured ? 'Manage with hosted Checkout' : 'Billing provider not configured'}</button></section><section><p className="v2-kicker">Entitlements</p><h2>Enforced limits</h2>{data.entitlements.map((entry) => <article key={entry.key}><strong>{entry.key.replace(/_/g, ' ')}</strong><p>{entry.limit === null ? 'Custom / unlimited' : entry.limit.toLocaleString()}</p><small>{entry.enabled ? 'Enabled' : 'Disabled'} · plan catalog</small></article>)}</section></div><section className="v2-limitations"><p className="v2-kicker"><ShieldCheck /> Security posture</p><ul><li>Organization membership and object-level authorization are enforced server-side and by PostgreSQL RLS.</li><li>External AI text processing requires explicit per-run consent.</li><li>Billing secrets and webhook signatures remain server-only.</li></ul></section></section>;
}
