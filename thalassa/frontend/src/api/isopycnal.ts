import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { ROI, ColorBy } from '../state/store'

export interface IsopycnalMesh {
  vertices: [number, number, number][]   // [lon, lat, depth_m]
  faces: [number, number, number][]
  color_values: number[] | null
  isovalue: number
  vertex_count: number
  face_count: number
}

export interface JobStatus {
  job_id: string
  status: 'queued' | 'running' | 'complete' | 'failed'
  result: IsopycnalMesh | null
  error: string | null
}

async function submitIsopycnal(
  roi: ROI,
  sigma0_value: number,
  color_by: ColorBy,
): Promise<string> {
  const { data } = await axios.post<JobStatus>('/api/scene/isopycnal', {
    roi,
    sigma0_value,
    color_by,
  })
  return data.job_id
}

async function pollJob(job_id: string): Promise<JobStatus> {
  const { data } = await axios.get<JobStatus>(`/api/jobs/${job_id}`)
  return data
}

export function useIsopycnalJob(
  roi: ROI,
  sigma0Value: number,
  colorBy: ColorBy,
  enabled = true,
) {
  const submitQuery = useQuery({
    queryKey: ['isopycnal-submit', roi, sigma0Value, colorBy],
    queryFn: () => submitIsopycnal(roi, sigma0Value, colorBy),
    enabled,
    staleTime: Infinity,
    retry: 1,
  })

  const jobId = submitQuery.data

  const pollQuery = useQuery({
    queryKey: ['isopycnal-poll', jobId],
    queryFn: () => pollJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const st = query.state.data?.status
      return st === 'complete' || st === 'failed' ? false : 2000
    },
  })

  const status = pollQuery.data?.status
    ?? (submitQuery.isLoading ? 'queued' : submitQuery.isError ? 'failed' : undefined)

  return {
    jobId,
    status,
    mesh: pollQuery.data?.status === 'complete' ? pollQuery.data.result : null,
    error: pollQuery.data?.error ?? (submitQuery.error as Error | null)?.message ?? null,
    isLoading:
      submitQuery.isLoading ||
      (!!jobId && status !== 'complete' && status !== 'failed'),
  }
}
