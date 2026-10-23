import { AlertCircle, Download, Expand, Grid3X3, Image as ImageIcon, LoaderCircle, Sparkles, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { GenerateResponse } from '../types';

interface GenerationCanvasProps {
    result: GenerateResponse | null;
    isLoading: boolean;
    error: string;
    showGrid: boolean;
    onToggleGrid: () => void;
    onStopWaiting: () => void;
    canResume: boolean;
    onResume: () => void;
}

const PROGRESS_COPY = ['Composing the visual hierarchy', 'Mixing the material palette', 'Building light and atmosphere', 'Rendering fine surface detail'];

export function GenerationCanvas({ result, isLoading, error, showGrid, onToggleGrid, onStopWaiting, canResume, onResume }: GenerationCanvasProps) {
    const [activeIndex, setActiveIndex] = useState(0);
    const [progressIndex, setProgressIndex] = useState(0);
    const [elapsedSeconds, setElapsedSeconds] = useState(0);

    useEffect(() => {
        if (!isLoading) return;
        setProgressIndex(0);
        setElapsedSeconds(0);
        const timer = window.setInterval(() => setProgressIndex((value) => (value + 1) % PROGRESS_COPY.length), 3200);
        const elapsedTimer = window.setInterval(() => setElapsedSeconds((value) => value + 1), 1000);
        return () => { window.clearInterval(timer); window.clearInterval(elapsedTimer); };
    }, [isLoading]);

    useEffect(() => setActiveIndex(0), [result?.generation_id]);
    const activeImage = result?.images[activeIndex];

    return (
        <section className="canvas-panel">
            <div className="canvas-toolbar">
                <div><span className="status-dot" /> <strong>Studio canvas</strong>{result && <span className="render-meta">{result.style_name} · {result.quality}</span>}</div>
                <div className="canvas-actions">
                    <button className={showGrid ? 'is-active' : ''} onClick={onToggleGrid} title="Composition grid"><Grid3X3 size={15} /></button>
                    {activeImage && <a href={activeImage.url} download={`${result?.style_id}-${activeImage.id}.${activeImage.format}`} title="Download original"><Download size={15} /></a>}
                    {activeImage && <a href={activeImage.url} target="_blank" rel="noreferrer" title="Open full size"><Expand size={15} /></a>}
                </div>
            </div>

            <div className={`canvas-stage ratio-${result?.aspect_ratio || 'landscape'}`}>
                {!result && !isLoading && !error && (
                    <div className="blank-canvas">
                        <span className="blank-canvas__mark"><ImageIcon size={27} /></span>
                        <p className="eyebrow">Blank canvas</p>
                        <h2>Describe something worth framing.</h2>
                        <p>Choose an art direction, write your brief, and generate a high-resolution original.</p>
                    </div>
                )}
                {activeImage && !isLoading && <img src={activeImage.url} alt={`Generated ${result?.style_name} artwork`} />}
                {activeImage && showGrid && <div className="composition-grid" aria-hidden="true"><i /><i /><b /><b /></div>}
                {isLoading && (
                    <div className="generation-progress">
                        <span className="progress-orbit"><LoaderCircle size={34} /></span>
                        <p className="eyebrow">Master render in progress</p>
                        <h2>{PROGRESS_COPY[progressIndex]}</h2>
                        <p>{elapsedSeconds < 45 ? 'Standard work usually takes 30–90 seconds.' : 'This is a background render. You can leave this screen and resume it later without losing the work.'}</p>
                        <div className="generation-time"><strong>{Math.floor(elapsedSeconds / 60)}:{String(elapsedSeconds % 60).padStart(2, '0')}</strong><span>elapsed</span></div>
                        <div className="progress-line"><span /></div>
                        <button className="stop-waiting" onClick={onStopWaiting}><X size={12} /> Continue in background</button>
                    </div>
                )}
                {error && !isLoading && (
                    <div className="canvas-error"><AlertCircle size={28} /><h2>{canResume ? 'Render safely queued' : 'Generation paused'}</h2><p>{error}</p>{canResume && <button className="resume-render" onClick={onResume}>Resume render</button>}</div>
                )}
            </div>

            {result && (
                <div className="result-footer">
                    <div className="variant-strip">
                        {result.images.map((image, index) => (
                            <button key={image.id} className={index === activeIndex ? 'is-active' : ''} onClick={() => setActiveIndex(index)}>
                                <img src={image.url} alt={`Variant ${index + 1}`} /><span>0{index + 1}</span>
                            </button>
                        ))}
                    </div>
                    <div className="palette-readout"><Sparkles size={14} /><span>{result.style_name}</span>{result.palette.map((color) => <i key={color} style={{ background: color }} title={color} />)}</div>
                    <div className="resolution-readout">{activeImage?.width} × {activeImage?.height} · {result.model}</div>
                </div>
            )}
        </section>
    );
}
