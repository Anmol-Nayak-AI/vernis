import { ChevronDown, Command, Frame, Layers3, Menu, Search, SlidersHorizontal, Sparkles, UserRound, WandSparkles } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ArtNavigation, StudioView } from './components/ArtNavigation';
import { AuthModal } from './components/AuthModal';
import { DiscoveryWall } from './components/DiscoveryWall';
import { GenerationCanvas } from './components/GenerationCanvas';
import { PlatformPages } from './components/PlatformPages';
import { StyleLibrary } from './components/StyleLibrary';
import { useAuth } from './context/AuthContext';
import { supabase } from './lib/supabase';
import { ArtStyle, ArtworkPurpose, AspectRatio, GenerateResponse, PaletteMode, StudioQuality } from './types';

const STARTERS = [
  'A solitary woman in a vermilion coat crossing a wind-polished salt plain at blue hour, monumental sky, quiet tension',
  'An overgrown glass conservatory where tiny mechanical birds tend impossible flowers',
  'A quiet portrait of an elderly astronomer surrounded by handwritten star charts',
  'A floating city built into enormous red sandstone arches at sunrise',
];

const PALETTES: { id: PaletteMode; name: string; colors: string[] }[] = [
  { id: 'artist-led', name: 'Artist led', colors: ['#2c315b', '#a54f54', '#d1a057'] },
  { id: 'chromatic', name: 'Chromatic', colors: ['#2346aa', '#ed3d66', '#f0bf39'] },
  { id: 'earth-and-gold', name: 'Earth & gold', colors: ['#553323', '#ae673f', '#d9aa52'] },
  { id: 'nocturne', name: 'Nocturne', colors: ['#10162f', '#243d79', '#ca944a'] },
  { id: 'luminous', name: 'Luminous', colors: ['#6ab2ad', '#d9c867', '#ec8c76'] },
  { id: 'unexpected', name: 'Unexpected', colors: ['#5c235f', '#ef553f', '#83b755'] },
];

const ASPECTS: { id: AspectRatio; label: string }[] = [
  { id: 'square', label: '1:1' }, { id: 'landscape', label: '3:2' },
  { id: 'portrait', label: '2:3' }, { id: 'widescreen', label: '16:9' },
];

const PURPOSES: { id: ArtworkPurpose; label: string }[] = [
  { id: 'fine-art-print', label: 'Fine art print' },
  { id: 'gallery-original', label: 'Gallery centerpiece' },
  { id: 'collector-series', label: 'Collector series' },
  { id: 'editorial', label: 'Editorial artwork' },
];

const PENDING_GENERATION_KEY = 'vernis.pendingGeneration';
const LOCAL_ARCHIVE_KEY = 'vernis.localArchive';

function readLocalArchive(): GenerateResponse[] {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(LOCAL_ARCHIVE_KEY) || '[]');
    return Array.isArray(parsed) ? parsed.filter((item) => item?.generation_id && item.images?.length).slice(0, 12) : [];
  } catch {
    return [];
  }
}

interface GenerationJob {
  job_id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  result?: GenerateResponse;
  error?: string;
}

export default function App() {
  const { user, session, role, workspaceId, signOut } = useAuth();
  const [view, setView] = useState<StudioView>('home');
  const [authOpen, setAuthOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [styles, setStyles] = useState<ArtStyle[]>([]);
  const [stylesLoading, setStylesLoading] = useState(true);
  const [stylePanelOpen, setStylePanelOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [prompt, setPrompt] = useState(STARTERS[0]);
  const [styleId, setStyleId] = useState('auto');
  const [secondaryStyleId, setSecondaryStyleId] = useState('');
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('portrait');
  const [quality, setQuality] = useState<StudioQuality>('standard');
  const [variants, setVariants] = useState(1);
  const [paletteMode, setPaletteMode] = useState<PaletteMode>('unexpected');
  const [purpose, setPurpose] = useState<ArtworkPurpose>('fine-art-print');
  const [originality, setOriginality] = useState(78);
  const [negativePrompt, setNegativePrompt] = useState('');
  const [directorMode, setDirectorMode] = useState(true);
  const [showGrid, setShowGrid] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [history, setHistory] = useState<GenerateResponse[]>(readLocalArchive);
  const [pendingJobId, setPendingJobId] = useState(() => window.localStorage.getItem(PENDING_GENERATION_KEY) || '');
  const generationController = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/studio/styles', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('The style archive is unavailable.');
        return response.json();
      })
      .then((payload) => setStyles(payload.styles || []))
      .catch((reason) => { if (reason.name !== 'AbortError') setError(reason.message || 'Could not open the atelier.'); })
      .finally(() => setStylesLoading(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!supabase || !workspaceId) return;
    const client = supabase;
    let active = true;
    void (async () => {
      const { data, error: archiveError } = await client.from('artworks').select('metadata').eq('workspace_id', workspaceId).order('created_at', { ascending: false }).limit(12);
      if (archiveError) throw archiveError;
      const saved = (data || []).map((row) => row.metadata as unknown as GenerateResponse).filter((item) => item?.generation_id && item.images?.length);
      if (active && saved.length) setHistory((current) => {
        const merged = [...saved, ...current.filter((local) => !saved.some((cloud) => cloud.generation_id === local.generation_id))].slice(0, 12);
        window.localStorage.setItem(LOCAL_ARCHIVE_KEY, JSON.stringify(merged));
        return merged;
      });
    })().catch((archiveError: unknown) => console.warn('The cloud studio archive could not be opened.', archiveError));
    return () => { active = false; };
  }, [workspaceId]);

  const selectedStyle = useMemo(() => styles.find((style) => style.id === styleId), [styles, styleId]);
  const selectedPalette = PALETTES.find((palette) => palette.id === paletteMode) || PALETTES[0];

  const finishGeneration = (payload: GenerateResponse) => {
    setResult(payload);
    setHistory((current) => {
      const next = [payload, ...current.filter((item) => item.generation_id !== payload.generation_id)].slice(0, 12);
      window.localStorage.setItem(LOCAL_ARCHIVE_KEY, JSON.stringify(next));
      return next;
    });
    setPendingJobId('');
    window.localStorage.removeItem(PENDING_GENERATION_KEY);
    if (supabase && user && workspaceId) {
      void (async () => {
        const { data: job, error: jobError } = await supabase.from('generation_jobs').insert({
          workspace_id: workspaceId, requested_by: user.id, status: 'succeeded', model: payload.model,
          parameters: { prompt: prompt.trim(), style_id: styleId, aspect_ratio: aspectRatio, quality, variants, palette_mode: paletteMode, artwork_purpose: purpose, originality },
          completed_at: new Date().toISOString(),
        }).select('id').single();
        if (jobError) throw jobError;
        const { error: artError } = await supabase.from('artworks').insert({
          workspace_id: workspaceId, creator_id: user.id, generation_job_id: job.id,
          title: `Untitled ${payload.style_name} study`, prompt: prompt.trim(), style_id: payload.style_id,
          image_url: payload.images[0].url, preview_url: payload.images[0].url,
          metadata: payload,
        });
        if (artError) throw artError;
      })().catch((persistenceError) => console.warn('Artwork was generated but its cloud record could not be saved.', persistenceError));
    }
  };

  const pollGeneration = async (jobId: string, controller: AbortController) => {
    while (!controller.signal.aborted) {
      const response = await fetch(`/api/studio/jobs/${jobId}`, {
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        signal: controller.signal,
      });
      const job = await response.json() as GenerationJob & { detail?: string };
      if (!response.ok) throw new Error(job.detail || 'The render could not be resumed.');
      if (job.status === 'succeeded' && job.result) return job.result;
      if (job.status === 'failed') throw new Error(job.error || 'The artwork could not be completed.');
      await new Promise<void>((resolve) => window.setTimeout(resolve, 1600));
    }
    throw new DOMException('Polling stopped', 'AbortError');
  };

  const watchGeneration = async (jobId: string) => {
    const controller = new AbortController();
    generationController.current = controller;
    setView('create'); setIsLoading(true); setError('');
    try {
      const payload = await pollGeneration(jobId, controller);
      finishGeneration(payload);
    } catch (reason) {
      if (controller.signal.aborted) {
        setError('The render is continuing safely in the background. Resume whenever you are ready.');
      } else {
        setPendingJobId('');
        window.localStorage.removeItem(PENDING_GENERATION_KEY);
        setError(reason instanceof Error ? reason.message : 'An unexpected studio error occurred.');
      }
    } finally {
      if (generationController.current === controller) generationController.current = null;
      setIsLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (prompt.trim().length < 3 || isLoading) return;
    setView('create'); setIsLoading(true); setError(''); setResult(null);
    try {
      const response = await fetch('/api/studio/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
        },
        body: JSON.stringify({
          prompt: prompt.trim(), style_id: styleId, secondary_style_id: secondaryStyleId || null,
          aspect_ratio: aspectRatio, quality, variants, palette_mode: paletteMode,
          artwork_purpose: purpose, originality, negative_prompt: negativePrompt.trim(), show_grid: showGrid,
        }),
      });
      const job = await response.json() as GenerationJob & { detail?: string };
      if (!response.ok) throw new Error(job.detail || 'The artwork could not be started.');
      setPendingJobId(job.job_id);
      window.localStorage.setItem(PENDING_GENERATION_KEY, job.job_id);
      await watchGeneration(job.job_id);
    } catch (reason) {
      setIsLoading(false);
      setError(reason instanceof Error ? reason.message : 'An unexpected studio error occurred.');
    }
  };

  const stopWaiting = () => generationController.current?.abort();
  const resumeGeneration = () => { if (pendingJobId && !isLoading) void watchGeneration(pendingJobId); };

  const useInspiration = (nextPrompt: string) => { setPrompt(nextPrompt); setView('create'); };

  const renderPage = () => {
    if (view === 'create') return (
      <div className="create-workspace">
        <section className="creator-desk">
          <div className="creator-desk__header">
            <div><p className="kicker">New work</p><h1>Create</h1></div>
            <div className="mode-switch"><button className={!directorMode ? 'is-active' : ''} onClick={() => setDirectorMode(false)}>Simple</button><button className={directorMode ? 'is-active' : ''} onClick={() => setDirectorMode(true)}>Art director</button></div>
          </div>

          <label className="creation-prompt">
            <span>Describe the work</span>
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={4000} placeholder="Subject, atmosphere, light, material, emotion…" />
            <small>{prompt.length}/4000</small>
          </label>
          <div className="prompt-sparks"><span>Starting points</span>{STARTERS.slice(1).map((starter, index) => <button key={starter} onClick={() => setPrompt(starter)}>Muse {index + 1}</button>)}</div>

          <div className="direction-block">
            <div className="control-label"><span>Art direction</span><small>{selectedStyle?.category || 'Intelligent match'}</small></div>
            <button className="style-selector" onClick={() => setStylePanelOpen((value) => !value)}>
              <div className="selected-style-palette">{(selectedStyle?.palette || ['#2d3158', '#a74352', '#d5a451']).map((color) => <i key={color} style={{ background: color }} />)}</div>
              <span><strong>{selectedStyle?.name || 'Auto art director'}</strong><small>{selectedStyle?.description || 'Let the atelier interpret your brief'}</small></span>
              <ChevronDown size={15} className={stylePanelOpen ? 'rotate' : ''} />
            </button>
            {stylePanelOpen && <div className="creator-styles"><StyleLibrary styles={styles} selectedId={styleId} onSelect={(id) => { setStyleId(id); setStylePanelOpen(false); }} isLoading={stylesLoading} /></div>}
          </div>

          <div className="direction-block">
            <div className="control-label"><span>Chromatic voice</span><small>{selectedPalette.name}</small></div>
            <div className="palette-modes">{PALETTES.map((palette) => <button key={palette.id} className={paletteMode === palette.id ? 'is-active' : ''} onClick={() => setPaletteMode(palette.id)} title={palette.name}>{palette.colors.map((color) => <i key={color} style={{ background: color }} />)}<span>{palette.name}</span></button>)}</div>
          </div>

          {directorMode && <div className="director-controls">
            <label><span>Presentation intent</span><select value={purpose} onChange={(event) => setPurpose(event.target.value as ArtworkPurpose)}>{PURPOSES.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
            <label className="originality-control"><span>Originality <em>{originality}%</em></span><input type="range" min="0" max="100" value={originality} onChange={(event) => setOriginality(Number(event.target.value))} /><small>Classical</small><small>Uncommon</small></label>
            <label><span>Blend medium</span><select value={secondaryStyleId} onChange={(event) => setSecondaryStyleId(event.target.value)}><option value="">None</option>{styles.filter((style) => style.id !== styleId).map((style) => <option key={style.id} value={style.id}>{style.name}</option>)}</select></label>
            <label><span>Exclude</span><input value={negativePrompt} onChange={(event) => setNegativePrompt(event.target.value)} placeholder="Elements to keep off the canvas" /></label>
          </div>}

          <div className="render-row">
            <div><span>Format</span><div className="format-buttons">{ASPECTS.map((item) => <button key={item.id} className={aspectRatio === item.id ? 'is-active' : ''} onClick={() => setAspectRatio(item.id)}><i className={item.id} />{item.label}</button>)}</div></div>
            <label><span>Quality</span><select value={quality} onChange={(event) => setQuality(event.target.value as StudioQuality)}><option value="draft">Preview · fastest</option><option value="standard">Standard · recommended</option><option value="studio">Studio · high detail</option><option value="masterpiece">Masterpiece · slowest</option></select></label>
            <label><span>Works</span><select value={variants} onChange={(event) => setVariants(Number(event.target.value))}>{[1, 2, 3, 4].map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
          </div>

          <button className="create-art-button" onClick={handleGenerate} disabled={isLoading || prompt.trim().length < 3}><WandSparkles size={18} /><span>{isLoading ? 'Painting in progress…' : 'Create artwork'}<small>{variants} {variants === 1 ? 'work' : 'variations'} · {quality} finish</small></span></button>
        </section>

        <section className="creation-results">
          <div className="results-heading"><div><p className="kicker">Atelier output</p><h2>{result ? 'Your new work' : 'The canvas awaits'}</h2></div><div className="results-note"><Sparkles size={14} /> Original compositions · print-ready detail</div></div>
          <GenerationCanvas result={result} isLoading={isLoading} error={error} showGrid={showGrid} onToggleGrid={() => setShowGrid((value) => !value)} onStopWaiting={stopWaiting} canResume={Boolean(pendingJobId)} onResume={resumeGeneration} />
          {result && !isLoading && <div className="post-generation-actions">
            <div><span>Artwork record initiated</span><strong>Generation evidence has been preserved in your studio.</strong><small>Next, review the work and complete its authorship and rights evidence.</small></div>
            <button onClick={() => setView('council')}>Run Art Council review</button>
            <button onClick={() => setView('provenance')}>Complete artwork passport</button>
          </div>}
          {!result && !isLoading && !error && <div className="under-canvas"><p>Explore a visual direction while you compose.</p><DiscoveryWall compact onUsePrompt={useInspiration} /></div>}
        </section>
      </div>
    );

    return <PlatformPages
      view={view}
      history={history}
      onNavigate={setView}
      onAuthNeeded={() => setAuthOpen(true)}
      onOpenGeneration={(generation) => { setResult(generation); setView('create'); }}
    />;
  };

  return (
    <div className="vernis-app">
      <button className="mobile-nav-toggle" onClick={() => setMobileNavOpen((value) => !value)}><Menu size={18} /><span>Vernis</span></button>
      <div className={mobileNavOpen ? 'mobile-nav-wrap is-open' : 'mobile-nav-wrap'}><ArtNavigation view={view} libraryCount={history.length} onChange={(next) => { setView(next); setMobileNavOpen(false); }} /></div>
      {mobileNavOpen && <button className="mobile-nav-scrim" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation" />}
      <main className="vernis-main">
        <div className="app-topline">
          <span>AI art trust infrastructure</span>
          <label className="global-search"><Search size={14} /><input placeholder="Search works, artists, collections…" /><kbd><Command size={10} /> K</kbd></label>
          <div className="topline-signals"><Frame size={13} /> Artwork passports <i /> <Layers3 size={13} /> 36 material languages <i /> <SlidersHorizontal size={13} /> Rights-aware</div>
          <div className="account-control">
            <button onClick={() => user ? setProfileOpen((open) => !open) : setAuthOpen(true)}><UserRound size={14} /><span>{user?.email?.split('@')[0] || 'Sign in'}</span></button>
            {profileOpen && user && <div className="profile-menu"><small>{user.email}</small><strong>{role || 'Studio member'}</strong><button onClick={() => { void signOut(); setProfileOpen(false); }}>Sign out</button></div>}
          </div>
        </div>
        {renderPage()}
      </main>
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
    </div>
  );
}
