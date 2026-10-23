import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { PublicLanding } from './PublicLanding';

describe('PublicLanding', () => {
  it('presents all six bounded intelligence engines and a workspace entry point', () => {
    render(<MemoryRouter><PublicLanding /></MemoryRouter>);

    expect(screen.getByRole('heading', { name: /Every artwork carries questions/i })).toBeInTheDocument();
    for (const engine of ['ArtSentinel', 'ArtShield', 'ConservaVision', 'ArtValuate', 'MuseGraph', 'ArtTransit']) {
      expect(screen.getByRole('heading', { name: engine })).toBeInTheDocument();
    }
    expect(screen.getByRole('link', { name: /Open workspace/i })).toHaveAttribute('href', '/app');
    expect(screen.getByText(/No invented evidence/i)).toBeInTheDocument();
  });
});
