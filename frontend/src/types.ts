// ==========================================
// 1. LangChain Execution Trace Types
// ==========================================

export type LangChainStage = 'THOUGHT_ACTION' | 'OBSERVATION' | 'FINAL_ANSWER';

export interface LangChainTraceItem {
    stage: LangChainStage;
    tool?: string;
    tool_input?: Record<string, unknown> | string;
    log?: string;
    output?: string;
}

export interface LangChainResponse {
    final_output: string;
    trace: LangChainTraceItem[];
    execution_type: string;
}

// ==========================================
// 2. LangGraph Execution State Types
// ==========================================

export interface ToolCallPayload {
    name: string;
    args: Record<string, unknown>;
    id: string;
}

export interface GraphMessageState {
    type: 'human' | 'ai' | 'tool' | 'system';
    content: string;
    tool_calls?: ToolCallPayload[];
}

export interface GraphStepTransition {
    node_executed: 'agent' | 'tools' | string;
    state_emitted: GraphMessageState[];
}

export interface LangGraphResponse {
    final_output: string;
    graph_steps: GraphStepTransition[];
    execution_type: string;
}

// ==========================================
// 3. API Request / Response Types
// ==========================================

export interface CompareRequest {
    prompt: string;
}

export interface CompareResponse {
    langchain: LangChainResponse;
    langgraph: LangGraphResponse;
}

// ==========================================
// 4. UI Flow & State Inspection Types
// ==========================================

export type ActiveEngineTab = 'both' | 'langchain' | 'langgraph';

export interface CanvasDimensions {
    width: number;
    height: number;
}

export interface ArtToolResultPalette {
    mood: string;
    hex_codes: string[];
}

export interface ArtToolResultGrid {
    canvas_size: string;
    divisions: number;
    horizontal_anchors: number[];
    vertical_anchors: number[];
}

export interface ArtStyle {
    id: string;
    name: string;
    category: string;
    description: string;
    palette: string[];
}

export type AspectRatio = 'square' | 'landscape' | 'portrait' | 'widescreen';
export type StudioQuality = 'draft' | 'standard' | 'studio' | 'masterpiece';
export type PaletteMode = 'artist-led' | 'chromatic' | 'earth-and-gold' | 'nocturne' | 'luminous' | 'unexpected';
export type ArtworkPurpose = 'gallery-original' | 'fine-art-print' | 'editorial' | 'collector-series';

export interface GeneratedImage {
    id: string;
    url: string;
    width: number;
    height: number;
    format: string;
    sha256?: string | null;
}

export interface GenerateResponse {
    generation_id: string;
    images: GeneratedImage[];
    style_id: string;
    style_name: string;
    palette: string[];
    model: string;
    quality: StudioQuality;
    aspect_ratio: AspectRatio;
    palette_mode: PaletteMode;
    artwork_purpose: ArtworkPurpose;
    originality: number;
    revised_prompt: string;
}
