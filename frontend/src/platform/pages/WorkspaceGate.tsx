import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Building2 } from 'lucide-react';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import { AuthenticationGate } from '../components/AuthenticationGate';
import { ErrorState, LoadingState } from '../components/PageState';

const schema = z.object({
  name: z.string().min(2, 'Enter an organization name.').max(160),
  slug: z.string().regex(/^[a-z0-9][a-z0-9-]{1,62}$/, 'Use lowercase letters, numbers, and hyphens.'),
  plan: z.enum(['artist', 'professional', 'gallery', 'institution', 'enterprise']),
});
type Values = z.infer<typeof schema>;

export function WorkspaceGate() {
  const { session, loading, configured } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const organizations = useQuery({
    queryKey: ['organizations', session?.user.id || 'development'],
    queryFn: () => api.organizations(session?.access_token),
    enabled: !configured || Boolean(session),
  });
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { name: '', slug: '', plan: 'gallery' } });
  const create = useMutation({
    mutationFn: (values: Values) => api.createOrganization(values, session?.access_token),
    onSuccess: async (organization) => {
      await queryClient.invalidateQueries({ queryKey: ['organizations'] });
      navigate(`/app/${organization.id}/command`, { replace: true });
    },
  });
  useEffect(() => {
    if (organizations.data?.length) navigate(`/app/${organizations.data[0].id}/command`, { replace: true });
  }, [organizations.data, navigate]);
  if (loading) return <main className="v2-gate"><LoadingState label="Checking your session" /></main>;
  if (configured && !session) return <AuthenticationGate />;
  if (organizations.isLoading) return <main className="v2-gate"><LoadingState label="Opening your workspace" /></main>;
  if (organizations.error) return <main className="v2-gate"><ErrorState error={organizations.error} /></main>;
  return <main className="v2-gate">
    <section className="v2-onboarding-card">
      <div className="v2-onboarding-mark"><Building2 /></div>
      <p className="v2-kicker">Workspace foundation</p>
      <h1>Create your Vernis organization.</h1>
      <p>Artworks, evidence, investigations, and exports remain isolated to this organization. You can invite specialists after setup.</p>
      <form onSubmit={form.handleSubmit((values) => create.mutate(values))}>
        <label><span>Organization name</span><input {...form.register('name')} onChange={(event) => { form.setValue('name', event.target.value); form.setValue('slug', event.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '').slice(0, 63)); }} />{form.formState.errors.name && <small>{form.formState.errors.name.message}</small>}</label>
        <label><span>Workspace URL key</span><input {...form.register('slug')} />{form.formState.errors.slug && <small>{form.formState.errors.slug.message}</small>}</label>
        <label><span>Starting plan</span><select {...form.register('plan')}><option value="artist">Artist</option><option value="professional">Professional</option><option value="gallery">Gallery</option><option value="institution">Institution</option><option value="enterprise">Enterprise</option></select></label>
        {create.error && <div className="v2-form-error">{create.error.message}</div>}
        <button className="v2-primary" disabled={create.isPending}>Create secure workspace <ArrowRight /></button>
      </form>
    </section>
  </main>;
}
