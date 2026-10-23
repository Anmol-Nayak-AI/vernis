import { AnimatePresence, motion } from 'motion/react';
import {
  ArrowRight, BadgeCheck, BarChart3, Clock3, CreditCard, Database, Download,
  Fingerprint, Gavel, LockKeyhole, Plus, ShieldCheck, Sparkles, Users,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { useAuth } from '../context/AuthContext';
import { GenerateResponse } from '../types';
import { StudioView } from './ArtNavigation';
import { ArtCouncil } from './ArtCouncil';

interface MuseumArtwork { id: number; title: string; artist_display: string; image_id: string; date_display: string; is_public_domain: boolean; }
interface PlatformPagesProps {
  view: StudioView;
  onNavigate: (view: StudioView) => void;
  onAuthNeeded: () => void;
  history: GenerateResponse[];
  onOpenGeneration: (generation: GenerateResponse) => void;
}

const ART_ERAS = [
  { year: '40,000 BCE', short: 'Origins', title: 'The first mark', copy: 'Pigment, ritual, memory. Image-making begins as a way to hold experience beyond a lifetime.' },
  { year: '450 BCE', short: 'Classical', title: 'Measure & ideal', copy: 'Proportion, civic narrative, and the human form become instruments for ordering the visible world.' },
  { year: '1503', short: 'Renaissance', title: 'Light becomes knowledge', copy: 'Perspective, anatomy, and oil glaze turn observation into a radical technology of presence.' },
  { year: '1874', short: 'Impression', title: 'The instant matters', copy: 'Color leaves the studio. Atmosphere, perception, and the unfinished moment become the subject.' },
  { year: '1919', short: 'Modern', title: 'Form finds a new grammar', copy: 'Abstraction, collage, geometry, and mass production fracture inherited visual rules.' },
  { year: '2026', short: 'Generative', title: 'The medium learns', copy: 'Artists direct systems, authorship expands, and provenance becomes part of the creative material.' },
];

const HERO_STUDIES = [
  { image: '/artworks/monsoon-architecture.jpg', period: 'Material abstraction', title: 'Monsoon Archive I', year: '2026', color: '#e69b5d' },
  { image: '/artworks/blue-hour-musician.jpg', period: 'Figurative continuum', title: 'Nocturne for a Blue Room', year: '2026', color: '#718ee5' },
  { image: '/artworks/vermilion-crossing.jpg', period: 'Contemporary landscape', title: 'Vermilion Crossing', year: '2026', color: '#d85a43' },
  { image: '/artworks/nocturne-beacon.jpg', period: 'Romantic nocturne', title: 'The Beacon at High Water', year: '2025', color: '#66a690' },
];

const MARKET_WORKS = [
  { title: 'Monsoon Archive I', artist: 'Mira Sen', price: '$2,250', medium: 'Oil, wax & mineral pigment', image: '/artworks/monsoon-architecture.jpg', tag: 'Original', kind: 'Originals', year: '2026', location: 'New Delhi' },
  { title: 'Nocturne for a Blue Room', artist: 'León Alvarez', price: '$3,480', medium: 'Egg tempera on panel', image: '/artworks/blue-hour-musician.jpg', tag: 'Curator selected', kind: 'Originals', year: '2026', location: 'Madrid' },
  { title: 'Vermilion Crossing', artist: 'Aya Morita', price: '$1,100', medium: 'Archival pigment print', image: '/artworks/vermilion-crossing.jpg', tag: 'Edition 3 / 25', kind: 'Editions', year: '2026', location: 'Kyoto' },
  { title: 'The Beacon at High Water', artist: 'Niamh Okafor', price: '$3,350', medium: 'Signed digital master', image: '/artworks/nocturne-beacon.jpg', tag: 'Digital edition 1 / 10', kind: 'Digital', year: '2025', location: 'Dublin' },
];

const AUCTIONS = [
  { ...MARKET_WORKS[1], bid: '$2,900', bids: 18, end: '02h 14m' },
  { ...MARKET_WORKS[0], bid: '$4,860', bids: 31, end: '07h 42m' },
  { ...MARKET_WORKS[3], bid: '$4,500', bids: 24, end: '1d 03h' },
];

const ARTISTS = [
  { name: 'Raja Ravi Varma', movement: 'Academic realism · India', years: '1848—1906', number: '01', note: 'Mythology, modernity, print culture' },
  { name: 'Claude Monet', movement: 'Impressionism · France', years: '1840—1926', number: '02', note: 'Serial vision, atmosphere, light' },
  { name: 'Katsushika Hokusai', movement: 'Ukiyo-e · Japan', years: '1760—1849', number: '03', note: 'Line, movement, popular image' },
  { name: 'Hilma af Klint', movement: 'Abstraction · Sweden', years: '1862—1944', number: '04', note: 'Systems, spirit, monumental scale' },
  { name: 'Amrita Sher-Gil', movement: 'Modernism · India', years: '1913—1941', number: '05', note: 'Figure, interiority, cultural synthesis' },
  { name: 'Vincent van Gogh', movement: 'Post-Impressionism · Netherlands', years: '1853—1890', number: '06', note: 'Color, rhythm, emotional structure' },
];

function PageIntro({ eyebrow, title, copy, action, onAction, index }: { eyebrow: string; title: string; copy: string; action?: string; onAction?: () => void; index?: string }) {
  return <header className="platform-intro">
    <div className="intro-index">{index || 'V—01'}</div>
    <div><p className="kicker">{eyebrow}</p><h1>{title}</h1><p>{copy}</p></div>
    {action && <button onClick={onAction}><Plus size={15} /> {action}</button>}
  </header>;
}

function EraNavigator({ compact = false }: { compact?: boolean }) {
  const [active, setActive] = useState(5);
  const era = ART_ERAS[active];
  return <section className={compact ? 'era-module is-compact' : 'era-module'}>
    <div className="era-visual">
      <img src="/artworks/art-evolution-panorama.jpg" alt="An original visual essay tracing art from prehistoric mark-making to generative media" />
      <div className="era-visual__label"><span>{era.year}</span><strong>{era.title}</strong></div>
    </div>
    <div className="era-interface">
      <div><p className="kicker">A brief history of seeing</p><h2>Art is a continuum,<br /><em>not a preset.</em></h2></div>
      <p>{era.copy}</p>
      <nav>{ART_ERAS.map((item, index) => <button key={item.short} className={active === index ? 'is-active' : ''} onClick={() => setActive(index)}><span>{item.year}</span><strong>{item.short}</strong></button>)}</nav>
    </div>
  </section>;
}

function MuseumCollection() {
  const [works, setWorks] = useState<MuseumArtwork[]>([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const fields = 'id,title,artist_display,image_id,date_display,is_public_domain';
    fetch(`https://api.artic.edu/api/v1/artworks?ids=27992,28560,24645,111628,16568,81537&fields=${fields}`)
      .then((response) => { if (!response.ok) throw new Error(); return response.json(); })
      .then((payload) => setWorks((payload.data || []).filter((item: MuseumArtwork) => item.is_public_domain && item.image_id)))
      .catch(() => setFailed(true));
  }, []);
  if (!works.length) return <div className="museum-fallback">{failed ? 'Museum archive is temporarily unavailable.' : 'Opening the museum archive…'}</div>;
  return <div className="museum-grid">{works.map((work, index) => <motion.article className={index === 0 ? 'is-lead' : ''} key={work.id} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
    <div className="museum-image"><img src={`https://www.artic.edu/iiif/2/${work.image_id}/full/800,/0/default.jpg`} alt={work.title} loading="lazy" /><span>{String(index + 1).padStart(2, '0')}</span></div>
    <div><small>{work.date_display}</small><strong>{work.title}</strong><span>{work.artist_display}</span><em><BadgeCheck size={11} /> Public domain · Art Institute of Chicago</em></div>
  </motion.article>)}</div>;
}

function MarketCard({ work, featured = false }: { work: typeof MARKET_WORKS[number]; featured?: boolean }) {
  return <motion.article className={featured ? 'market-card is-featured' : 'market-card'} whileHover={{ y: -3 }}>
    <div className="market-card__image"><img src={work.image} alt={work.title} /><span>{work.tag}</span><button>View dossier <ArrowRight size={13} /></button></div>
    <div className="market-card__meta"><div><small>{work.medium} · {work.year}</small><h3>{work.title}</h3><p>{work.artist} · {work.location}</p></div><div><strong>{work.price}</strong><span><BadgeCheck size={11} /> Provenance verified</span></div></div>
  </motion.article>;
}

export function PlatformPages({ view, onNavigate, onAuthNeeded, history, onOpenGeneration }: PlatformPagesProps) {
  const { user, session } = useAuth();
  const [billingError, setBillingError] = useState('');
  const [marketFilter, setMarketFilter] = useState('All works');
  const [selectedHero, setSelectedHero] = useState(0);
  const [passportIndex, setPassportIndex] = useState(0);
  const [passportChecks, setPassportChecks] = useState({
    humanDirection: true,
    generationRecord: true,
    sourceDisclosure: false,
    rightsDeclaration: false,
    editionTerms: false,
  });
  const passportWork = history[passportIndex] || history[0];
  const passportFingerprint = passportWork?.images[0].sha256 || passportWork?.generation_id || '';
  const passportCompletion = Math.round((Object.values(passportChecks).filter(Boolean).length / Object.keys(passportChecks).length) * 100);

  const downloadPassport = () => {
    if (!passportWork) return;
    const record = {
      schema: 'vernis.artwork-passport.v1',
      certificate_id: `VRN-${passportFingerprint.slice(0, 12).toUpperCase()}`,
      exported_at: new Date().toISOString(),
      artwork: passportWork,
      evidence: passportChecks,
      completion: passportCompletion,
      notice: 'Creator-supplied and system-generated record. This file is not an authenticity certificate or legal opinion.',
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `vernis-passport-${passportWork.generation_id.slice(0, 8)}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };

  const startCheckout = async (plan: 'creator' | 'studio' | 'enterprise') => {
    if (!user || !session) { onAuthNeeded(); return; }
    setBillingError('');
    try {
      const response = await fetch('/api/billing/checkout', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}` }, body: JSON.stringify({ plan }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Billing is not configured.');
      window.location.assign(payload.url);
    } catch (reason) { setBillingError(reason instanceof Error ? reason.message : 'Unable to start checkout.'); }
  };

  const content = useMemo(() => {
    if (view === 'home') return <section className="platform-page home-platform">
      <header className="museum-hero">
        <div className="museum-hero__edition"><span>Vernis / 2026</span><i /><span>Art intelligence, from origin to ownership</span></div>
        <div className="museum-hero__body">
          <div className="museum-hero__copy"><p className="kicker">The provenance operating system for AI art</p><h1>Create the work.<br /><em>Prove its story.</em></h1><p>Vernis helps artists and galleries turn AI-assisted images into trusted cultural assets—with art-directed creation, expert AI review, rights disclosure, provenance, editions, and commerce in one system.</p><div><button onClick={() => onNavigate('create')}><Sparkles size={15} /> Create a verified artwork</button><button onClick={() => onNavigate('council')}>Open the Art Council <ArrowRight size={14} /></button></div></div>
          <div className="hero-artwall">
            <div className="hero-artwall__works">{HERO_STUDIES.map((study, index) => <button key={study.title} className={selectedHero === index ? 'is-selected' : ''} onMouseEnter={() => setSelectedHero(index)} onFocus={() => setSelectedHero(index)} onClick={() => setSelectedHero(index)} aria-label={`View ${study.title}`}><img src={study.image} alt="" /><span style={{ '--study-accent': study.color } as CSSProperties}><small>{study.period}</small><strong>{study.title}</strong></span></button>)}</div>
            <div className="hero-artwall__caption"><span>Living collection / {String(selectedHero + 1).padStart(2, '0')}</span><div><i style={{ background: HERO_STUDIES[selectedHero].color }} /><strong>{HERO_STUDIES[selectedHero].year}</strong><small>Hover across the collection</small></div></div>
          </div>
        </div>
        <div className="museum-hero__footer"><span>Art-directed generation</span><span>Multi-agent review</span><span>Artwork passports</span><span>Collector-ready commerce</span></div>
      </header>
      <section className="purpose-declaration"><div><span>01 / The problem Vernis solves</span><h2>AI can make an image.<br /><em>It cannot establish trust.</em></h2></div><p>Collectors, galleries, and artists need to know who directed the work, what tools and sources shaped it, which rights are declared, how editions are controlled, and how the object changed hands. Vernis keeps that evidence attached from the first prompt to the final sale.</p><div className="purpose-facts"><article><strong>Authorship</strong><span>Human direction, approvals, and model lineage</span></article><article><strong>Integrity</strong><span>Source evidence, rights, editions, and provenance</span></article><article><strong>Market readiness</strong><span>Curatorial context, release logic, and collector dossier</span></article></div></section>
      <section className="trust-system">
          <div className="trust-system__intro"><span>02 / The Vernis trust protocol</span><h2>One artwork.<br /><em>One living record.</em></h2><p>Vernis joins creation, expert review, human approval, rights declarations, provenance, editions, and exchange into a record that can travel with the work.</p><button onClick={() => onNavigate('provenance')}>Open provenance infrastructure <ArrowRight size={14} /></button></div>
        <div className="trust-system__map">
          <div className="trust-source"><span>Creative record</span><strong>Human direction + model lineage</strong><small>Prompt history · references · transformations · approvals</small></div>
          <div className="trust-line"><i /><i /><i /></div>
          <div className="trust-nodes">
            <article><b>01</b><span><strong>Authorship</strong><small>Who directed and approved the work?</small></span><em>Verified</em></article>
            <article><b>02</b><span><strong>Rights</strong><small>What may be exhibited, licensed, or sold?</small></span><em>Declared</em></article>
            <article><b>03</b><span><strong>Provenance</strong><small>How did the work evolve and change hands?</small></span><em>Recorded</em></article>
            <article><b>04</b><span><strong>Market</strong><small>What edition, price, and settlement terms apply?</small></span><em>Ready</em></article>
          </div>
        </div>
      </section>
      <section className="council-preview"><div className="council-preview__art"><img src="/artworks/blue-hour-musician.jpg" alt="AI-assisted artwork prepared for expert review" /><span>Review specimen / VRN—2026—014</span></div><div className="council-preview__copy"><p className="kicker">03 / Vernis Art Council</p><h2>Three expert agents.<br />One human decision.</h2><p>A curator, rights-and-provenance reviewer, and market strategist examine each work from different professional perspectives. Their findings become a transparent dossier—not an automatic certificate or invented claim.</p><div><span>Curatorial coherence</span><span>Rights and evidence gaps</span><span>Edition and release strategy</span></div><button onClick={() => onNavigate('council')}>Convene the Art Council <ArrowRight size={14} /></button></div></section>
      <EraNavigator />
      <section className="editorial-section"><div className="editorial-heading"><span>05</span><div><p className="kicker">A complete practice</p><h2>From historical intelligence<br />to cultural object.</h2></div><p>Vernis treats generation as one moment in a larger professional practice: research, direction, making, review, editioning, provenance, and exchange.</p></div>
        <div className="editorial-capabilities"><article><span>Atelier</span><h3>Direct with material knowledge.</h3><p>Build from painting, print, textile, photographic, and experimental visual languages.</p><button onClick={() => onNavigate('create')}>Open creation studio <ArrowRight size={13} /></button></article><article><span>Archive</span><h3>Preserve the story of the work.</h3><p>Record model, prompt lineage, rights declarations, editions, approvals, and ownership events.</p><button onClick={() => onNavigate('provenance')}>View provenance <ArrowRight size={13} /></button></article><article><span>Market</span><h3>Place work with context.</h3><p>Publish fixed-price works and timed auctions with condition, settlement, and provenance data.</p><button onClick={() => onNavigate('marketplace')}>Enter the market <ArrowRight size={13} /></button></article></div>
      </section>
    </section>;

    if (view === 'council') return <ArtCouncil onNavigate={onNavigate} onAuthNeeded={onAuthNeeded} works={history} />;

    if (view === 'explore') return <section className="platform-page archive-page"><PageIntro index="A—01" eyebrow="The open archive" title="History is a working material." copy="Move across periods, study public-domain masterworks, and translate visual intelligence into an original practice—not imitation." /><EraNavigator compact /><div className="collection-heading"><span>Selected masterworks</span><p>Open-access works for study and critical reference</p></div><MuseumCollection /></section>;

    if (view === 'artists') return <section className="platform-page"><PageIntro index="A—02" eyebrow="Artist index" title="The lives behind visual language." copy="A research index of artists who changed how images are composed, circulated, and understood." /><div className="artist-ledger">{ARTISTS.map((artist) => <motion.article key={artist.name} whileHover={{ x: 5 }}><span>{artist.number}</span><div><small>{artist.movement}</small><h2>{artist.name}</h2></div><p>{artist.note}</p><em>{artist.years}</em><ArrowRight size={16} /></motion.article>)}</div></section>;

    if (view === 'marketplace') {
      const filtered = marketFilter === 'All works' ? MARKET_WORKS : MARKET_WORKS.filter((work) => work.kind === marketFilter);
      return <section className="platform-page market-page"><PageIntro index="M—01" eyebrow="Primary market" title="Exceptional work, fully contextualized." copy="Original and editioned work presented with authorship, material, condition, rights, provenance, logistics, and settlement information." action="List an artwork" onAction={() => user ? onNavigate('studio') : onAuthNeeded()} />
        <div className="market-toolbar"><div>{['All works', 'Originals', 'Editions', 'Digital'].map((filter) => <button key={filter} className={marketFilter === filter ? 'is-active' : ''} onClick={() => setMarketFilter(filter)}>{filter}</button>)}</div><span><BadgeCheck size={12} /> Curator-reviewed inventory</span></div>
        <div className="market-editorial-grid">{filtered.map((work, index) => <MarketCard key={work.title} work={work} featured={index === 0 && marketFilter === 'All works'} />)}</div>
        <div className="market-assurance"><span>Collector services</span><p>Condition reporting · insured logistics · edition management · NEFT and international settlement · post-sale provenance transfer</p><button>How acquisitions work <ArrowRight size={13} /></button></div>
      </section>;
    }

    if (view === 'auctions') return <section className="platform-page"><PageIntro index="M—02" eyebrow="Live auction room" title="Bid with context and confidence." copy="Timed, curator-led sales with reserves, bidder verification, anti-sniping extensions, and auditable settlement." action="Consign work" onAction={() => user ? onNavigate('studio') : onAuthNeeded()} /><div className="auction-grid">{AUCTIONS.map((lot, index) => <article key={lot.title}><div className="auction-art"><img src={lot.image} alt={lot.title} /><span>Lot {String(index + 1).padStart(2, '0')}</span><em><Clock3 size={12} /> {lot.end}</em></div><div><small>{lot.artist} · {lot.medium}</small><h3>{lot.title}</h3><section><span>Current bid<strong>{lot.bid}</strong></span><span>Bids<strong>{lot.bids}</strong></span></section><button onClick={() => user ? undefined : onAuthNeeded()}><Gavel size={14} /> Place bid</button></div></article>)}</div><div className="auction-trust"><ShieldCheck size={18} /><div><strong>Collector protection</strong><span>Identity checks, reserve transparency, condition reports, escrow-ready settlement, and a complete bid audit trail.</span></div></div></section>;

    if (view === 'billing') return <section className="platform-page"><PageIntro index="W—04" eyebrow="Plans & usage" title="Infrastructure for every practice." copy="Begin independently, then add collaborators, governance, advanced provenance, and commerce controls as the studio grows." /><div className="pricing-grid">{[
      { id: 'creator' as const, name: 'Creator', price: '$19', copy: 'For a focused independent practice.', features: ['120 studio credits', '4K master files', 'Private portfolio', 'Basic licensing'] },
      { id: 'studio' as const, name: 'Studio', price: '$59', copy: 'For professional artists and galleries.', features: ['600 studio credits', '5 team seats', 'Marketplace & auctions', 'Provenance certificates'], featured: true },
      { id: 'enterprise' as const, name: 'Enterprise', price: 'Custom', copy: 'For institutions and art businesses.', features: ['SSO & SCIM-ready', 'Custom roles & approvals', 'Audit exports', 'Dedicated infrastructure'] },
    ].map((plan) => <article className={plan.featured ? 'is-featured' : ''} key={plan.id}>{plan.featured && <em>Most selected</em>}<span>{plan.name}</span><strong>{plan.price}<small>{plan.price !== 'Custom' && '/month USD'}</small></strong><p>{plan.copy}</p><ul>{plan.features.map((feature) => <li key={feature}><BadgeCheck size={13} /> {feature}</li>)}</ul><button onClick={() => startCheckout(plan.id)}>{plan.id === 'enterprise' ? 'Contact sales' : 'Choose plan'} <ArrowRight size={14} /></button></article>)}</div>{billingError && <div className="billing-error">{billingError}</div>}<div className="billing-security"><CreditCard /><div><strong>Hosted, auditable billing</strong><span>Stripe Checkout architecture, usage metering, tax-ready invoices, and no card data stored by Vernis.</span></div></div></section>;

    if (view === 'provenance') return <section className="platform-page passport-page"><PageIntro index="W—01" eyebrow="Artwork passports" title="Proof that travels with the work." copy="Turn a generated file into a living record of human direction, model lineage, rights disclosures, editions, reviews, and ownership events." action={passportWork ? 'Export passport' : 'Create artwork'} onAction={passportWork ? downloadPassport : () => onNavigate('create')} />
      {!passportWork ? <div className="passport-empty"><Fingerprint size={34} /><h2>No artwork record yet.</h2><p>Create a work in the atelier. Vernis will automatically preserve its generation evidence and open an artwork passport.</p><button onClick={() => onNavigate('create')}>Create your first recorded work <ArrowRight size={14} /></button></div> : <>
        <div className="passport-switcher"><span>Registered studio works</span><div>{history.map((work, index) => <button key={work.generation_id} className={passportWork.generation_id === work.generation_id ? 'is-active' : ''} onClick={() => setPassportIndex(index)}><img src={work.images[0].url} alt="" /><span>VRN—{work.generation_id.slice(0, 5).toUpperCase()}</span></button>)}</div></div>
        <div className="passport-console">
          <aside className="passport-art"><img src={passportWork.images[0].url} alt={passportWork.style_name} /><div><small>Vernis artwork passport</small><strong>Untitled {passportWork.style_name} study</strong><span>VRN-{passportFingerprint.slice(0, 12).toUpperCase()}</span></div></aside>
          <div className="passport-record">
            <header><div><p className="kicker">Evidence completeness</p><strong>{passportCompletion}%</strong><span>{passportCompletion === 100 ? 'Collector dossier complete' : 'Complete the missing declarations before listing'}</span></div><i style={{ '--passport-score': `${passportCompletion * 3.6}deg` } as CSSProperties}><b>{passportCompletion}</b><small>/100</small></i></header>
            <section className="evidence-checklist"><div><h3>Evidence ledger</h3><p>Each declaration remains distinguishable from system-generated evidence.</p></div>{[
              ['humanDirection', 'Human direction', 'Creative brief and selection decision recorded'],
              ['generationRecord', 'Generation lineage', `${passportWork.model} · ${passportWork.quality} · ${passportWork.aspect_ratio}`],
              ['sourceDisclosure', 'Source disclosure', 'References and source-material statement attached'],
              ['rightsDeclaration', 'Rights declaration', 'Creator commercial-use declaration attached'],
              ['editionTerms', 'Edition terms', 'Edition size, proofs, and retirement rules defined'],
            ].map(([key, label, detail]) => { const complete = passportChecks[key as keyof typeof passportChecks]; return <button key={key} className={complete ? 'is-complete' : ''} onClick={() => setPassportChecks((current) => ({ ...current, [key]: !complete }))}><span>{complete ? <BadgeCheck size={15} /> : <Plus size={15} />}</span><strong>{label}</strong><small>{detail}</small><em>{complete ? 'Recorded' : 'Add evidence'}</em></button>; })}</section>
            <section className="passport-lineage"><article><Fingerprint size={16} /><span><small>Master SHA-256 fingerprint</small><strong>{passportWork.images[0].sha256 || 'Legacy work — fingerprint created on next export'}</strong></span></article><article><Database size={16} /><span><small>Generation ID</small><strong>{passportWork.generation_id}</strong></span></article><article><Database size={16} /><span><small>Model lineage</small><strong>{passportWork.model}</strong></span></article><article><Sparkles size={16} /><span><small>Art direction</small><strong>{passportWork.style_name} · {passportWork.originality}% originality</strong></span></article></section>
            <footer><div><BadgeCheck size={15} /><span><strong>System evidence locked</strong><small>Generation metadata is read-only in this passport export.</small></span></div><button onClick={downloadPassport}><Download size={14} /> Download JSON passport</button><button onClick={() => onNavigate('council')}>Request expert review <ArrowRight size={14} /></button></footer>
          </div>
        </div>
        <div className="passport-events"><span>Chain of custody</span>{[['Created', 'Generation parameters preserved', 'System'], ['Selected', 'Creator retained this work', 'Creator'], ['Council review', 'Curatorial and rights dossier', 'Next'], ['Edition opened', 'Release terms and proofs registered', 'Pending'], ['Transferred', 'Collector ownership event', 'Future']].map((event, index) => <article key={event[0]} className={index < 2 ? 'is-complete' : ''}><i>{String(index + 1).padStart(2, '0')}</i><strong>{event[0]}</strong><small>{event[1]}</small><em>{event[2]}</em></article>)}</div>
      </>}
    </section>;

    if (view === 'team') return <section className="platform-page"><PageIntro index="W—02" eyebrow="Enterprise workspace" title="One studio. Clear responsibility." copy="Assign precise roles for creation, curation, approvals, finance, publishing, and collection access." action="Invite member" onAction={() => user ? undefined : onAuthNeeded()} /><div className="team-console"><div className="team-stats"><article><Users /><strong>8</strong><span>Members</span></article><article><LockKeyhole /><strong>4</strong><span>Roles active</span></article><article><BarChart3 /><strong>94%</strong><span>Credits available</span></article></div><div className="team-table"><header><span>Member</span><span>Role</span><span>Access</span><span>Status</span></header>{[['Aditya A.','Owner','Full workspace'],['Mira Sen','Artist','Create & publish'],['Rhea Kapoor','Curator','Review & approve'],['Finance desk','Finance','Orders & payouts']].map((row, index) => <div key={row[0]}><span><i>{row[0].split(' ').map((part) => part[0]).join('').slice(0,2)}</i>{row[0]}</span><span>{row[1]}</span><span>{row[2]}</span><span><b />{index === 3 ? 'Invited' : 'Active'}</span></div>)}</div></div></section>;

    if (view === 'studio' || view === 'collections' || view === 'library') return <section className="platform-page"><PageIntro index="S—01" eyebrow="Private archive" title={view === 'collections' ? 'Collections, deliberately assembled.' : 'The studio inventory.'} copy="Generated works, masters, listings, editions, rights, and provenance—organized around the artwork." action="Create artwork" onAction={() => onNavigate('create')} />{history.length ? <div className="inventory-grid">{history.map((item, index) => <motion.article key={item.generation_id} whileHover={{ y: -4 }} onClick={() => onOpenGeneration(item)}><img src={item.images[0].url} alt={item.style_name} /><div><small>VRN-{item.generation_id.slice(0,6).toUpperCase()}</small><strong>Untitled work {String(history.length-index).padStart(2,'0')}</strong><span>{item.style_name} · {item.quality}</span><footer><em>Private</em><b>Master file</b></footer></div></motion.article>)}</div> : <div className="library-empty"><span><Sparkles size={28} /></span><h2>Your first collection starts here.</h2><p>Create a work in the atelier; Vernis will preserve its visual metadata, rights state, and edition history.</p><button onClick={() => onNavigate('create')}>Create your first artwork</button></div>}</section>;

    return null;
  }, [view, history, user, session, billingError, marketFilter, selectedHero, passportIndex, passportChecks]);

  return <AnimatePresence mode="wait"><motion.div key={view} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: .22 }}>{content}</motion.div></AnimatePresence>;
}
