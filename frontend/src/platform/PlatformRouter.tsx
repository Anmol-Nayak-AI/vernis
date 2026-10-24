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
const EngineWorkspace = lazy(() => import('./pages/EngineWorkspace').then((module) => ({ default: module.EngineWorkspace })));
const CaseDetail = lazy(() => import('./pages/CaseDetail').then((module) => ({ default: module.CaseDetail })));
const EvidenceLibrary = lazy(() => import('./pages/EvidenceLibrary').then((module) => ({ default: module.EvidenceLibrary })));
const AgentOperations = lazy(() => import('./pages/AgentOperations').then((module) => ({ default: module.AgentOperations })));
const ReportsHub = lazy(() => import('./pages/ReportsHub').then((module) => ({ default: module.ReportsHub })));
const OrganizationSettings = lazy(() => import('./pages/OrganizationSettings').then((module) => ({ default: module.OrganizationSettings })));

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
      <Route path="engines/artsentinel" element={<EngineWorkspace engine="artsentinel" />} />
      <Route path="engines/artshield" element={<EngineWorkspace engine="artshield" />} />
      <Route path="engines/conservavision" element={<EngineWorkspace engine="conservavision" />} />
      <Route path="engines/musegraph" element={<EngineWorkspace engine="musegraph" />} />
      <Route path="engines/artvaluate" element={<EngineWorkspace engine="artvaluate" />} />
      <Route path="engines/arttransit" element={<EngineWorkspace engine="arttransit" />} />
      <Route path="cases/:caseId" element={<CaseDetail />} />
      <Route path="evidence" element={<EvidenceLibrary />} />
      <Route path="agents" element={<AgentOperations />} />
      <Route path="reports" element={<ReportsHub />} />
      <Route path="settings" element={<OrganizationSettings />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></Suspense>;
}
