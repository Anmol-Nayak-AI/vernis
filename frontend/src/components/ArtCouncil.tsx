import { ArrowRight, BadgeCheck, BrainCircuit, FileSearch, LoaderCircle, Scale, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { GenerateResponse } from '../types';
import { StudioView } from './ArtNavigation';

interface ArtCouncilProps {
  onNavigate: (view: StudioView) => void;
  onAuthNeeded: () => void;
  works: GenerateResponse[];
}

interface AdvisoryResponse {
  report: string;
  engine: string;
  agents: string[];
  disclaimer: string;
}

const COUNCIL = [
  { icon: Sparkles, role: 'Curatorial intelligence', copy: 'Tests artistic coherence, distinctiveness, material logic, and exhibition context.' },
  { icon: Scale, role: 'Rights & provenance', copy: 'Surfaces missing attribution, source, edition, disclosure, and chain-of-custody evidence.' },
  { icon: FileSearch, role: 'Market strategy', copy: 'Builds a responsible release structure, research plan, and collector-facing narrative.' },
];

export function ArtCouncil({ onNavigate, onAuthNeeded, works }: ArtCouncilProps) {
  const { session } = useAuth();
  const [selectedWorkId, setSelectedWorkId] = useState(works[0]?.generation_id || 'specimen');
  const selectedWork = works.find((work) => work.generation_id === selectedWorkId);
  const [title, setTitle] = useState(selectedWork ? `Untitled ${selectedWork.style_name} study` : 'Vermilion Crossing');
  const [description, setDescription] = useState(selectedWork ? selectedWork.revised_prompt : 'An expressionist oil study of a solitary figure crossing a wind-polished salt plain at blue hour. The work was art-directed in Vernis, then selected from a small set of generated studies for a signed archival edition.');
  const [goal, setGoal] = useState('Prepare a transparent limited-edition release for galleries and serious private collectors.');
  const [report, setReport] = useState<AdvisoryResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedWork) return;
    setTitle(`Untitled ${selectedWork.style_name} study`);
    setDescription(`AI-assisted artwork directed in Vernis. Style: ${selectedWork.style_name}. Quality: ${selectedWork.quality}. Presentation intent: ${selectedWork.artwork_purpose}. Originality setting: ${selectedWork.originality}%.\n\nCreative brief and generation record:\n${selectedWork.revised_prompt}`);
    setReport(null);
  }, [selectedWorkId]);

  const runCouncil = async () => {
    if (title.trim().length < 1 || description.trim().length < 10 || loading) return;
    setLoading(true); setError(''); setReport(null);
    try {
      const response = await fetch('/api/advisory/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
        },
        body: JSON.stringify({ title: title.trim(), description: description.trim(), commercial_goal: goal.trim() }),
      });
      const payload = await response.json();
      if (response.status === 401) { onAuthNeeded(); throw new Error('Sign in to convene your private Art Council.'); }
      if (!response.ok) throw new Error(payload.detail || 'The Art Council could not complete its review.');
      setReport(payload);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The Art Council could not complete its review.');
    } finally {
      setLoading(false);
    }
  };

  return <section className="platform-page council-page">
    <header className="council-hero">
      <div className="council-hero__copy">
        <p className="kicker">Vernis Intelligence / Multi-agent review</p>
        <h1>An expert council<br />for every artwork.</h1>
        <p>Generation creates an image. The Vernis Art Council turns its creative intent, evidence, rights position, and release plan into a professional dossier.</p>
        <div><span><BadgeCheck size={13} /> Evidence before claims</span><span><BadgeCheck size={13} /> Human approval required</span></div>
      </div>
      <div className="council-portrait">
        <img src={selectedWork?.images[0].url || '/artworks/vermilion-crossing.jpg'} alt={`${title} under review`} />
        <aside><small>Work under review / {selectedWork ? selectedWork.generation_id.slice(0, 6).toUpperCase() : '001'}</small><strong>{title}</strong><span>{selectedWork ? `${selectedWork.style_name} · ${selectedWork.quality}` : 'AI-assisted oil study · 2026'}</span></aside>
      </div>
    </header>

    <div className="council-agents">{COUNCIL.map(({ icon: Icon, role, copy }, index) => <article key={role}><span>0{index + 1}</span><Icon size={20} /><div><strong>{role}</strong><p>{copy}</p></div><i>Specialist agent</i></article>)}</div>

    <section className="council-workbench">
      <div className="council-brief">
        <div><p className="kicker">Private review brief</p><h2>Convene the council.</h2><p>Describe the work honestly. The council identifies evidence gaps and recommendations; it never invents provenance or certifies authenticity.</p></div>
        {works.length > 0 && <label><span>Studio artwork</span><select value={selectedWorkId} onChange={(event) => setSelectedWorkId(event.target.value)}>{works.map((work, index) => <option key={work.generation_id} value={work.generation_id}>Work {String(works.length - index).padStart(2, '0')} · {work.style_name}</option>)}</select></label>}
        <label><span>Artwork title</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
        <label><span>Work, process, and context</span><textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={4000} /></label>
        <label><span>Commercial or institutional goal</span><textarea value={goal} onChange={(event) => setGoal(event.target.value)} maxLength={1000} /></label>
        <button onClick={() => void runCouncil()} disabled={loading || description.trim().length < 10}>{loading ? <LoaderCircle className="council-spin" size={16} /> : <BrainCircuit size={16} />} {loading ? 'Council in session…' : 'Run multi-agent review'} <ArrowRight size={14} /></button>
        {error && <p className="council-error">{error}</p>}
      </div>

      <div className={report ? 'council-dossier has-report' : 'council-dossier'}>
        <header><span>Vernis Council Dossier</span><em>{report?.engine || 'Awaiting brief'}</em></header>
        {report ? <>
          <div className="dossier-seal"><BadgeCheck size={18} /><span><small>Reviewed by</small><strong>{report.agents.join(' · ')}</strong></span></div>
          <div className="dossier-report">{report.report}</div>
          <footer>{report.disclaimer}</footer>
        </> : <div className="dossier-empty"><BrainCircuit size={34} /><h3>Your review will appear here.</h3><p>A structured curatorial, provenance, rights, and market-readiness dossier—built for a human decision, not an automated verdict.</p></div>}
      </div>
    </section>

    <section className="council-next"><span>From review to record</span><h2>Approved recommendations become part of the artwork passport.</h2><p>Keep human decisions, source evidence, editions, rights declarations, and ownership events attached to the work throughout its market life.</p><button onClick={() => onNavigate('provenance')}>Explore the provenance layer <ArrowRight size={14} /></button></section>
  </section>;
}
