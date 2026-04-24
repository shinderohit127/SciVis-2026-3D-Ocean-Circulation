import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export interface TimestepDescriptor {
  timestep: number
  sigma0_mean: number
  sigma0_std: number
  ct_mean: number
  sa_mean: number
  anomaly_score: number
}

export interface TemporalWindowResult {
  t_start: number
  t_end: number
  n_computed: number
  descriptors: TimestepDescriptor[]
  descriptor_version: string
}

interface JobStatus {
  job_id: string
  status: 'queued' | 'running' | 'complete' | 'failed'
  result: TemporalWindowResult | null
  error: string | null
}

export interface TemporalWindowParams {
  lat_min: number
  lat_max: number
  lon_min: number
  lon_max: number
  depth_min_m?: number
  depth_max_m?: number
  t_start: number
  t_end: number
  n_samples?: number
}

async function submitWindow(params: TemporalWindowParams): Promise<string> {
  const { data } = await axios.post<JobStatus>('/api/temporal/window', params)
  return data.job_id
}

async function pollJob(job_id: string): Promise<JobStatus> {
  const { data } = await axios.get<JobStatus>(`/api/jobs/${job_id}`)
  return data
}

export function useTemporalWindow(params: TemporalWindowParams | null) {
  const submitQuery = useQuery({
    queryKey: ['temporal-submit', params],
    queryFn: () => submitWindow(params!),
    enabled: params !== null,
    staleTime: Infinity,
    retry: 1,
  })

  const jobId = submitQuery.data

  const pollQuery = useQuery({
    queryKey: ['temporal-poll', jobId],
    queryFn: () => pollJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const st = query.state.data?.status
      return st === 'complete' || st === 'failed' ? false : 3000
    },
  })

  const status = pollQuery.data?.status
    ?? (submitQuery.isLoading ? 'queued' : submitQuery.isError ? 'failed' : undefined)

  return {
    jobId,
    status,
    result: pollQuery.data?.status === 'complete' ? pollQuery.data.result : null,
    error: pollQuery.data?.error ?? (submitQuery.error as Error | null)?.message ?? null,
    isLoading:
      submitQuery.isLoading ||
      (!!jobId && status !== 'complete' && status !== 'failed'),
  }
}
