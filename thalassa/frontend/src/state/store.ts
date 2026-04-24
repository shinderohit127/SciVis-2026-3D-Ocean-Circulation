import { create } from 'zustand'

export interface ROI {
  lat_min: number
  lat_max: number
  lon_min: number
  lon_max: number
  depth_min_m: number
  depth_max_m: number
  timestep: number
  quality: number
}

export type ColorBy = 'CT' | 'SA' | 'alpha' | 'beta' | null

export type PlaySpeed = 0.5 | 1 | 2 | 4

interface AppState {
  roi: ROI
  sigma0Value: number
  colorBy: ColorBy
  brushedSigma0Range: [number, number] | null   // from T-S lasso → triggers new isopycnal
  isPlaying: boolean
  playSpeed: PlaySpeed
  setROI: (patch: Partial<ROI>) => void
  setSigma0: (v: number) => void
  setColorBy: (c: ColorBy) => void
  setBrushedSigma0Range: (r: [number, number] | null) => void
  setIsPlaying: (v: boolean) => void
  setPlaySpeed: (v: PlaySpeed) => void
}

const DEFAULT_ROI: ROI = {
  lat_min: 35,
  lat_max: 45,
  lon_min: -40,
  lon_max: -30,
  depth_min_m: 0,
  depth_max_m: 2000,
  timestep: 0,
  quality: -9,
}

export const useStore = create<AppState>((set) => ({
  roi: DEFAULT_ROI,
  sigma0Value: 27.0,
  colorBy: 'CT',
  brushedSigma0Range: null,
  isPlaying: false,
  playSpeed: 1,
  setROI: (patch) => set((s) => ({ roi: { ...s.roi, ...patch } })),
  setSigma0: (sigma0Value) => set({ sigma0Value }),
  setColorBy: (colorBy) => set({ colorBy }),
  setBrushedSigma0Range: (brushedSigma0Range) => set({ brushedSigma0Range }),
  setIsPlaying: (isPlaying) => set({ isPlaying }),
  setPlaySpeed: (playSpeed) => set({ playSpeed }),
}))
