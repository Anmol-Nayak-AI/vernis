import { Archive, Bell, BookOpen, Boxes, ChevronDown, Command, FileText, Fingerprint, Menu, Network, PackageCheck, Search, Settings, Shield, Sparkles, X } from 'lucide-react';
import { useState } from 'react';
import { NavLink, Outlet, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';

const ENGINES = [
  ['artsentinel', 'ArtSentinel', 'Authenticity & provenance', Fingerprint],
  ['artshield', 'ArtShield', 'Rights monitoring', Shield],
  ['conservavision', 'ConservaVision', 'Condition intelligence', Sparkles],
  ['musegraph', 'MuseGraph', 'Collection intelligence', Network],
  ['artvaluate', 'ArtValuate', 'Market intelligence', Archive],
  ['arttransit', 'ArtTransit', 'Shipment evidence', PackageCheck],
] as const;

export function AppShell() {
  const { orgId = '' } = useParams();
  const navigate = useNavigate();
  const { session, user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [organizationOpen, setOrganizationOpen] = useState(false);
  const organizations = useQuery({ queryKey: ['organizations'], queryFn: () => api.organizations(session?.access_token) });
  const current = organizations.data?.find((item) => item.id === orgId);
  const close = () => setMobileOpen(false);
  return <div className="v2-app-shell">
    <a className="v2-skip-link" href="#main-content">Skip to content</a>
    <header className="v2-topbar">
      <button className="v2-mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu /></button>
      <div className="v2-org-control"><button className="v2-org-switcher" type="button" aria-expanded={organizationOpen} onClick={() => setOrganizationOpen((value) => !value)}>
        <span className="v2-org-monogram">{current?.name.slice(0, 1) || 'V'}</span>
        <span><strong>{current?.name || 'Vernis workspace'}</strong><small>{current?.role || 'Loading membership'}</small></span>
        <ChevronDown aria-hidden="true" />
      </button>{organizationOpen && <div className="v2-org-menu" role="menu">{organizations.data?.map((organization) => <button key={organization.id} role="menuitem" onClick={() => { setOrganizationOpen(false); navigate(`/app/${organization.id}/command`); }}><span>{organization.name.slice(0, 1)}</span><strong>{organization.name}</strong><small>{organization.role}</small></button>)}</div>}</div>
      <label className="v2-global-search" title="Global search arrives with the evidence library"><Search aria-hidden="true" /><span className="sr-only">Global search is planned</span><input disabled placeholder="Global search · planned" /><kbd><Command />K</kbd></label>
      <div className="v2-top-actions"><button disabled title="Notifications arrive with durable workflow events" aria-label="Notifications are planned"><Bell /></button><span>{user?.email?.split('@')[0] || 'Local development'}</span></div>
    </header>
    <aside className={`v2-sidebar ${mobileOpen ? 'is-open' : ''}`} aria-label="Primary navigation">
      <div className="v2-brand"><span>V</span><div><strong>VERNIS</strong><small>Art Intelligence OS</small></div><button onClick={close} aria-label="Close navigation"><X /></button></div>
      <nav>
        <p>Workspace</p>
        <NavLink to={`/app/${orgId}/command`} onClick={close}><Boxes />Command Center</NavLink>
        <NavLink to={`/app/${orgId}/artworks`} onClick={close}><Archive />Artwork Registry</NavLink>
        <NavLink to={`/app/${orgId}/evidence`} onClick={close}><BookOpen />Evidence Library</NavLink>
        <NavLink to={`/app/${orgId}/reports`} onClick={close}><FileText />Reports</NavLink>
        <NavLink to={`/app/${orgId}/agents`} onClick={close}><Sparkles />Agent Operations</NavLink>
        <p>Intelligence engines</p>
        {ENGINES.map(([key, name, description, Icon]) => <NavLink className="v2-engine-link" to={`/app/${orgId}/engines/${key}`} onClick={close} key={key}><Icon /><span><strong>{name}</strong><small>{description}</small></span><em>Live</em></NavLink>)}
      </nav>
      <footer><span>Evidence-first platform</span><p>Real organization records. No simulated intelligence results.</p><NavLink to="/legacy">Open legacy prototype</NavLink><button onClick={() => navigate(`/app/${orgId}/settings`)}><Settings />Organization settings</button></footer>
    </aside>
    {mobileOpen && <button className="v2-nav-scrim" onClick={close} aria-label="Close navigation overlay" />}
    <main id="main-content" className="v2-main"><Outlet /></main>
  </div>;
}
