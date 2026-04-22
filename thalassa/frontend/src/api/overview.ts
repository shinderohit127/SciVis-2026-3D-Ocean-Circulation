import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export interface DepthBandSummary {
  band: string
  depth_range_m: [number, number]
  stats: { min: number; max: number; mean: number; std: number; p95: number }
  surface_slice: number[][] | null
}

export interface OverviewResponse {
  basin: string
  metric: string
  depth_bands: DepthBandSummary[]
  cached: boolean
}

async function fetchOverview(basin: string, metric: string): Promise<OverviewResponse> {
  const { data } = await axios.post<OverviewResponse>('/api/overview', { basin, metric })
  return data
}

export function useOverview(basin = 'global', metric = 'sigma0') {
  return useQuery({
    queryKey: ['overview', basin, metric],
    queryFn: () => fetchOverview(basin, metric),
    staleTime: 24 * 60 * 60 * 1000,
    retry: 1,
  })
}
