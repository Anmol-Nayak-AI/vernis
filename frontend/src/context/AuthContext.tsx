import type { Session, User } from '@supabase/supabase-js';
import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import { isSupabaseConfigured, supabase } from '../lib/supabase';

export type WorkspaceRole = 'owner' | 'admin' | 'curator' | 'artist' | 'finance' | 'viewer';

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  role: WorkspaceRole | null;
  workspaceId: string | null;
  loading: boolean;
  configured: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [workspaceRole, setWorkspaceRole] = useState<WorkspaceRole | null>(null);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(isSupabaseConfigured);

  useEffect(() => {
    if (!supabase) { setLoading(false); return; }
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setLoading(false); });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setLoading(false);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!supabase || !session?.user) { setWorkspaceId(null); setWorkspaceRole(null); return; }
    const client = supabase;
    let active = true;
    const ensureStudio = async () => {
      const user = session.user;
      const displayName = String(user.user_metadata?.display_name || user.email?.split('@')[0] || 'Artist studio');
      await client.from('profiles').upsert({ id: user.id, display_name: displayName }, { onConflict: 'id' });
      const { data: existing } = await client.from('workspaces').select('id').limit(1).maybeSingle();
      let id = existing?.id as string | undefined;
      if (!id) {
        const base = displayName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '').slice(0, 46) || 'studio';
        const { data: created, error } = await client.from('workspaces').upsert({ owner_id: user.id, name: displayName, slug: `${base}-${user.id.slice(0, 8)}` }, { onConflict: 'slug' }).select('id').single();
        if (error) throw error;
        id = created.id;
        const { error: memberError } = await client.from('workspace_members').upsert({ workspace_id: id, user_id: user.id, role: 'owner' }, { onConflict: 'workspace_id,user_id' });
        if (memberError) throw memberError;
      }
      const { data: member } = await client.from('workspace_members').select('role').eq('workspace_id', id).eq('user_id', user.id).maybeSingle();
      if (active) { setWorkspaceId(id || null); setWorkspaceRole((member?.role as WorkspaceRole | undefined) || 'owner'); }
    };
    void ensureStudio().catch((error) => console.warn('Workspace onboarding is pending.', error));
    return () => { active = false; };
  }, [session]);

  const value = useMemo<AuthContextValue>(() => ({
    user: session?.user ?? null,
    session,
    role: workspaceRole ?? (session?.user.app_metadata?.workspace_role as WorkspaceRole | undefined) ?? null,
    workspaceId,
    loading,
    configured: isSupabaseConfigured,
    signIn: async (email, password) => {
      if (!supabase) throw new Error('Authentication is not configured. Add the Supabase browser environment variables.');
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
    },
    signUp: async (email, password, name) => {
      if (!supabase) throw new Error('Authentication is not configured. Add the Supabase browser environment variables.');
      const { error } = await supabase.auth.signUp({ email, password, options: { data: { display_name: name } } });
      if (error) throw error;
    },
    signInWithGoogle: async () => {
      if (!supabase) throw new Error('Authentication is not configured. Add the Supabase browser environment variables.');
      const { error } = await supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin } });
      if (error) throw error;
    },
    signOut: async () => { if (supabase) await supabase.auth.signOut(); },
  }), [session, loading, workspaceRole, workspaceId]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
