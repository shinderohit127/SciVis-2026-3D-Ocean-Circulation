import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export interface Variable {
  name: string
  units: string
  description: string
  url: string
}

export interface GridInfo {
  nx: number
  ny: number
  nz: number
}

export interface TimestepInfo {
  count: number
  start: string
  end: string
  interval_hours: number
}

export interface RegionPreset {
  lat: [number, number]
  lon: [number, number]
}

export interface MetadataResponse {
  dataset: string
  metric_version: string
  variables: Variable[]
  grid: GridInfo
  timesteps: TimestepInfo
  depth_levels: number
  regions: Record<string, RegionPreset>
}

async function fetchMetadata(): Promise<MetadataResponse> {
  const { data } = await axios.get<MetadataResponse>('/api/metadata')
  return data
}

export function useMetadata() {
  return useQuery({
    queryKey: ['metadata'],
    queryFn: fetchMetadata,
    staleTime: Infinity, // metadata doesn't change during a session
  })
}
