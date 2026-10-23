import {
    Aperture, BadgeCheck, BrainCircuit, Compass, CreditCard, FolderHeart, Gavel, Home,
    Library, Plus, ScanSearch, ShoppingBag, Users,
} from 'lucide-react';

export type StudioView =
    | 'home' | 'create' | 'explore' | 'artists' | 'marketplace' | 'auctions'
    | 'studio' | 'library' | 'collections' | 'council' | 'provenance' | 'team' | 'billing';

interface ArtNavigationProps {
    view: StudioView;
    onChange: (view: StudioView) => void;
    libraryCount: number;
}

const GROUPS = [
    {
        label: 'Discover', items: [
            { id: 'home' as const, label: 'Home', icon: Home },
            { id: 'explore' as const, label: 'Masterworks', icon: Compass },
            { id: 'artists' as const, label: 'Artists', icon: ScanSearch },
        ],
    },
    {
        label: 'Practice', items: [
            { id: 'create' as const, label: 'AI atelier', icon: Aperture },
            { id: 'council' as const, label: 'AI Art Council', icon: BrainCircuit },
            { id: 'studio' as const, label: 'My studio', icon: Library },
            { id: 'collections' as const, label: 'Collections', icon: FolderHeart },
        ],
    },
    {
        label: 'Commerce', items: [
            { id: 'marketplace' as const, label: 'Marketplace', icon: ShoppingBag },
            { id: 'auctions' as const, label: 'Auctions', icon: Gavel },
        ],
    },
    {
        label: 'Workspace', items: [
            { id: 'provenance' as const, label: 'Provenance', icon: BadgeCheck },
            { id: 'team' as const, label: 'Team & roles', icon: Users },
            { id: 'billing' as const, label: 'Plans & billing', icon: CreditCard },
        ],
    },
];

export function ArtNavigation({ view, onChange, libraryCount }: ArtNavigationProps) {
    return (
        <aside className="art-nav">
            <button className="art-wordmark" onClick={() => onChange('home')}>
                <span className="art-wordmark__seal"><b>V</b></span>
                <span><strong>Vernis</strong><small>Art Intelligence</small></span>
            </button>

            <button className="nav-create" onClick={() => onChange('create')}><Plus size={16} /> Create verified work</button>

            <nav className="nav-primary nav-groups">
                {GROUPS.map((group) => <section key={group.label}>
                    <p>{group.label}</p>
                    {group.items.map((item) => {
                        const Icon = item.icon;
                        return <button key={item.id} className={view === item.id || (item.id === 'studio' && view === 'library') ? 'is-active' : ''} onClick={() => onChange(item.id)}>
                            <Icon size={16} /><span>{item.label}</span>{item.id === 'studio' && libraryCount > 0 && <em>{libraryCount}</em>}
                        </button>;
                    })}
                </section>)}
            </nav>

            <div className="nav-palette-card">
                <small>Vernis principle / 01</small>
                <strong>The work keeps its story.</strong>
                <p>Creative direction, evidence, rights, editions, and ownership remain attached.</p>
            </div>
        </aside>
    );
}
