import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export interface DepthBandSummary {
  band: string
  depth_range: [number, number]
  mean_map: number[][]
  stats: { min: number; max: number; mean: number; std: number }
}

export interface OverviewResponse {
  basin: string
  metric: string
  timestep: number
  quality: number
  shape: { nz: number; ny: number; nx: number }
  lats: number[]
  lons: number[]
  depth_bands: DepthBandSummary[]
  elapsed_ms: number
}

async function fetchOverview(basin: string, metric: string): Promise<OverviewResponse> {
  const { data } = await axios.post<OverviewResponse>('/api/overview', { basin, metric })
  return data
}

export function useOverview(basin = 'north_atlantic', metric = 'sigma0') {
  return useQuery({
    queryKey: ['overview', basin, metric],
    queryFn: () => fetchOverview(basin, metric),
    staleTime: 24 * 60 * 60 * 1000,
    retry: 1,
  })
}
