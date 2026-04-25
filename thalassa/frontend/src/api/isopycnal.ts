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
  decimated?: boolean
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
  target_faces: number | null,
): Promise<string> {
  const { data } = await axios.post<JobStatus>('/api/scene/isopycnal', {
    roi,
    sigma0_value,
    color_by,
    target_faces,
  })
  return data.job_id
}

async function pollJob(job_id: string): Promise<JobStatus> {
  const { data } = await axios.get<JobStatus>(`/api/jobs/${job_id}`)
  return data
}

function useSingleJob(
  roi: ROI,
  sigma0Value: number,
  colorBy: ColorBy,
  targetFaces: number | null,
  enabled: boolean,
  keyPrefix: string,
) {
  const submitQuery = useQuery({
    queryKey: [keyPrefix + '-submit', roi, sigma0Value, colorBy, targetFaces],
    queryFn: () => submitIsopycnal(roi, sigma0Value, colorBy, targetFaces),
    enabled,
    staleTime: Infinity,
    retry: 1,
  })
  const jobId = submitQuery.data
  const pollQuery = useQuery({
    queryKey: [keyPrefix + '-poll', jobId],
    queryFn: () => pollJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const st = query.state.data?.status
      return st === 'complete' || st === 'failed' ? false : 2000
    },
  })
  const mesh = pollQuery.data?.status === 'complete' ? pollQuery.data.result : null
  const done = pollQuery.data?.status === 'complete' || pollQuery.data?.status === 'failed'
  return { jobId, mesh, done, isLoading: submitQuery.isLoading || (!!jobId && !done) }
}

// PREVIEW_QUALITY: the fast first pass shown while the refined job runs.
const PREVIEW_QUALITY = -7

export function useIsopycnalJob(
  roi: ROI,
  sigma0Value: number,
  colorBy: ColorBy,
  targetFaces: number | null = null,
  enabled = true,
) {
  const isPreviewQuality = roi.quality >= PREVIEW_QUALITY

  // Final-quality job — always submitted
  const final = useSingleJob(roi, sigma0Value, colorBy, targetFaces, enabled, 'iso-final')

  // Preview job — submitted concurrently when quality is better than preview.
  // Uses quality -7 so the surface appears within ~3s while the fine job runs.
  const previewROI: ROI = { ...roi, quality: PREVIEW_QUALITY }
  const preview = useSingleJob(
    previewROI, sigma0Value, colorBy, targetFaces,
    !isPreviewQuality && enabled,  // skip if roi already IS preview quality
    'iso-preview',
  )

  // Show the best available result: final mesh if ready, else preview
  const mesh = final.mesh ?? preview.mesh
  const isRefining = !isPreviewQuality && !!preview.mesh && !final.mesh

  // Derive overall status for the status bar
  const status = final.done
    ? (final.mesh ? 'complete' : 'failed')
    : isRefining ? 'refining'
    : final.isLoading ? 'running'
    : 'queued'

  return {
    jobId: final.jobId ?? null,
    status,
    mesh,
    isRefining,
    error: null,
    isLoading: !mesh && final.isLoading,
  }
}
