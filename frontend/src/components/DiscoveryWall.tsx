import { ArrowUpRight, Heart, Sparkles } from 'lucide-react';

export const DISCOVERY_ART = [
    { title: 'The Vermilion Hour', style: 'Expressionist oil', className: 'pigment-vermilion', palette: ['#f04438', '#552137', '#f2b84b'] },
    { title: 'Garden After Rain', style: 'Luminous impressionism', className: 'pigment-garden', palette: ['#205f55', '#88bd76', '#e4c95a'] },
    { title: 'Quiet Geometry', style: 'Bauhaus study', className: 'pigment-geometry', palette: ['#172b68', '#e65732', '#e8c356'] },
    { title: 'Nocturne No. 7', style: 'Ink and mineral wash', className: 'pigment-nocturne', palette: ['#111936', '#334a75', '#d9a756'] },
    { title: 'Blue Salt', style: 'Color field', className: 'pigment-blue', palette: ['#182e7a', '#4169c1', '#e9dfca'] },
    { title: 'The Orchard Dreams', style: 'Narrative gouache', className: 'pigment-orchard', palette: ['#4b2354', '#ce5b57', '#eba84d'] },
];

interface DiscoveryWallProps {
    compact?: boolean;
    onUsePrompt?: (prompt: string) => void;
}

export function DiscoveryWall({ compact = false, onUsePrompt }: DiscoveryWallProps) {
    return (
        <div className={`discovery-grid ${compact ? 'is-compact' : ''}`}>
            {DISCOVERY_ART.map((art, index) => (
                <article className="discovery-card" key={art.title}>
                    <button className={`artwork-study ${art.className}`} onClick={() => onUsePrompt?.(`Create an original artwork inspired by the mood of “${art.title}”: ${art.style}, with a distinctive contemporary composition.`)} aria-label={`Use ${art.title} as inspiration`}>
                        <span className="study-grain" />
                        <span className="study-number">Study 0{index + 1}</span>
                        <span className="study-action"><ArrowUpRight size={15} /></span>
                    </button>
                    <div className="discovery-card__meta">
                        <div><strong>{art.title}</strong><span>{art.style}</span></div>
                        <div className="mini-palette">{art.palette.map((color) => <i key={color} style={{ background: color }} />)}</div>
                        <button aria-label="Save study"><Heart size={14} /></button>
                    </div>
                </article>
            ))}
            {!compact && <article className="discovery-manifesto"><Sparkles size={18} /><p>Made for walls,<br />not timelines.</p><span>Every prompt becomes a considered object of color, texture, and form.</span></article>}
        </div>
    );
}
