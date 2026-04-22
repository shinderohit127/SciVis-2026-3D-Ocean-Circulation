import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { ROI } from '../state/store'

export interface VariableStats {
  min: number
  max: number
  mean: number
  std: number
  surface_slice: number[][]
}

export interface QueryPlanInfo {
  recommended_quality: number
  estimated_mb: number
  capped: boolean
}

export interface ROIQueryResponse {
  roi: ROI
  variables: Record<string, VariableStats>
  query_plan: QueryPlanInfo
}

async function fetchROIQuery(roi: ROI): Promise<ROIQueryResponse> {
  const { data } = await axios.post<ROIQueryResponse>('/api/roi/query', { roi })
  return data
}

export function useROIQuery(roi: ROI, enabled = true) {
  return useQuery({
    queryKey: ['roi', roi],
    queryFn: () => fetchROIQuery(roi),
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })
}
