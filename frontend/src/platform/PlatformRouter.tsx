import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { LoadingState } from './components/PageState';

const LegacyApp = lazy(() => import('../App'));
const AppShell = lazy(() => import('./components/AppShell').then((module) => ({ default: module.AppShell })));
const ArtworkDetail = lazy(() => import('./pages/ArtworkDetail').then((module) => ({ default: module.ArtworkDetail })));
const ArtworkRegistry = lazy(() => import('./pages/ArtworkRegistry').then((module) => ({ default: module.ArtworkRegistry })));
const CommandCenter = lazy(() => import('./pages/CommandCenter').then((module) => ({ default: module.CommandCenter })));
const PublicLanding = lazy(() => import('./pages/PublicLanding').then((module) => ({ default: module.PublicLanding })));
const WorkspaceGate = lazy(() => import('./pages/WorkspaceGate').then((module) => ({ default: module.WorkspaceGate })));

function SettingsPlaceholder() {
  return <section className="v2-page"><header className="v2-page-header"><div><p className="v2-kicker">Organization governance</p><h1>Settings</h1><p>Membership, roles, security, provider consent, and retention controls will be released with their backend enforcement.</p></div></header><div className="v2-state"><strong>No configurable settings in this slice.</strong><span>This page deliberately avoids presenting non-functional controls.</span></div></section>;
}

export function PlatformRouter() {
  return <Suspense fallback={<LoadingState label="Opening Vernis" />}><Routes>
    <Route path="/" element={<PublicLanding />} />
    <Route path="/legacy/*" element={<LegacyApp />} />
    <Route path="/app" element={<WorkspaceGate />} />
    <Route path="/app/:orgId" element={<AppShell />}>
      <Route index element={<Navigate to="command" replace />} />
      <Route path="command" element={<CommandCenter />} />
      <Route path="artworks" element={<ArtworkRegistry />} />
      <Route path="artworks/:artworkId" element={<ArtworkDetail />} />
      <Route path="settings" element={<SettingsPlaceholder />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></Suspense>;
}
