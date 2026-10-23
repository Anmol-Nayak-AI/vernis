import { Search, SlidersHorizontal } from 'lucide-react';
import { useMemo, useState } from 'react';
import { ArtStyle } from '../types';

interface StyleLibraryProps {
    styles: ArtStyle[];
    selectedId: string;
    onSelect: (id: string) => void;
    isLoading: boolean;
}

export function StyleLibrary({ styles, selectedId, onSelect, isLoading }: StyleLibraryProps) {
    const [query, setQuery] = useState('');
    const [category, setCategory] = useState('All');
    const categories = useMemo(() => ['All', ...Array.from(new Set(styles.map((style) => style.category))).sort()], [styles]);
    const filtered = useMemo(() => styles.filter((style) => {
        const matchesCategory = category === 'All' || style.category === category;
        const text = `${style.name} ${style.description} ${style.category}`.toLowerCase();
        return matchesCategory && text.includes(query.toLowerCase());
    }), [styles, query, category]);

    return (
        <aside className="style-library">
            <div className="style-library__head">
                <div>
                    <p className="eyebrow">Art direction</p>
                    <h2>Style library</h2>
                </div>
                <span className="count-badge">{styles.length}</span>
            </div>

            <button className={`auto-style ${selectedId === 'auto' ? 'is-selected' : ''}`} onClick={() => onSelect('auto')}>
                <span className="auto-style__icon"><SlidersHorizontal size={16} /></span>
                <span><strong>Auto art director</strong><small>Match a style from your brief</small></span>
            </button>

            <label className="search-field">
                <Search size={15} />
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search 35 styles" />
            </label>

            <div className="category-strip">
                {categories.map((item) => (
                    <button key={item} className={item === category ? 'is-active' : ''} onClick={() => setCategory(item)}>{item}</button>
                ))}
            </div>

            <div className="style-list">
                {isLoading && Array.from({ length: 7 }).map((_, index) => <div className="style-skeleton" key={index} />)}
                {!isLoading && filtered.map((style) => (
                    <button key={style.id} className={`style-card ${style.id === selectedId ? 'is-selected' : ''}`} onClick={() => onSelect(style.id)}>
                        <div className="swatch-row" aria-hidden="true">
                            {style.palette.map((color) => <span key={color} style={{ background: color }} />)}
                        </div>
                        <div><strong>{style.name}</strong><small>{style.description}</small></div>
                        <span className="style-category">{style.category}</span>
                    </button>
                ))}
                {!isLoading && !filtered.length && <p className="empty-filter">No styles match this filter.</p>}
            </div>
        </aside>
    );
}
