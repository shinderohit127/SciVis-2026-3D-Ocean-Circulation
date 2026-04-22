import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { ROI } from '../state/store'

export interface FieldStats {
  min: number
  max: number
  mean: number
  std: number
  surface_slice: number[][]
}

export interface DensityResponse {
  roi: ROI
  fields: Record<string, FieldStats>
  metric_version: string
}

async function fetchDensity(roi: ROI, include: string[]): Promise<DensityResponse> {
  const { data } = await axios.post<DensityResponse>('/api/derived/density', {
    roi,
    include,
  })
  return data
}

export function useDensityFields(roi: ROI, include: string[], enabled = true) {
  return useQuery({
    queryKey: ['density', roi, include],
    queryFn: () => fetchDensity(roi, include),
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })
}
