import { AlertTriangle, LoaderCircle } from 'lucide-react';

export function LoadingState({ label = 'Loading workspace' }: { label?: string }) {
  return <div className="v2-state" role="status"><LoaderCircle className="v2-spin" /><strong>{label}</strong><span>Retrieving authorized records…</span></div>;
}

export function ErrorState({ error }: { error: unknown }) {
  return <div className="v2-state is-error" role="alert"><AlertTriangle /><strong>Vernis could not load this view.</strong><span>{error instanceof Error ? error.message : 'An unexpected error occurred.'}</span></div>;
}
