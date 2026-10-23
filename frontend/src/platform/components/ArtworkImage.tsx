import { useQuery } from '@tanstack/react-query';
import { Image as ImageIcon } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../api';
import type { Artwork } from '../types';

export function ArtworkImage({ artwork, className = '' }: { artwork: Artwork; className?: string }) {
  const { session } = useAuth();
  const asset = artwork.assets.find((item) => item.is_primary && item.status === 'ready')
    || artwork.assets.find((item) => item.status === 'ready');
  const download = useQuery({
    queryKey: ['asset-download', artwork.organization_id, asset?.id],
    queryFn: () => api.downloadUrl(artwork.organization_id, asset!.id, session?.access_token),
    enabled: Boolean(asset),
    staleTime: 240_000,
  });
  if (!asset || !download.data) {
    return <div className={`v2-art-placeholder ${className}`} aria-label="Artwork image has not been added"><ImageIcon aria-hidden="true" /><span>{asset?.status === 'pending' ? 'Image processing' : 'No image yet'}</span></div>;
  }
  return <img className={className} src={download.data.url} alt={artwork.title} />;
}
