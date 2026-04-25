import React, { useEffect } from 'react'
import MainLayout from './panes/MainLayout'
import { useStore } from './state/store'

const MAX_TIMESTEP = 10311

// Global keyboard shortcuts for temporal navigation.
// These fire regardless of focus so users can scrub without clicking the slider.
//   ArrowLeft / ArrowRight   → step ±1 timestep
//   Shift + ArrowLeft/Right  → step ±10 timesteps
//   Space                    → play / pause
//   [ / ]                    → previous / next quality preset
function useGlobalKeyboard() {
  const { roi, isPlaying, qualityPreset, setROI, setIsPlaying, setQualityPreset } = useStore()

  useEffect(() => {
    const PRESETS = ['preview', 'standard', 'fine'] as const

    const onKey = (e: KeyboardEvent) => {
      // Ignore when user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return

      const step = e.shiftKey ? 10 : 1

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault()
          setIsPlaying(false)
          setROI({ timestep: Math.max(0, roi.timestep - step) })
          break
        case 'ArrowRight':
          e.preventDefault()
          setIsPlaying(false)
          setROI({ timestep: Math.min(MAX_TIMESTEP, roi.timestep + step) })
          break
        case ' ':
          e.preventDefault()
          setIsPlaying(!isPlaying)
          break
        case '[': {
          const idx = PRESETS.indexOf(qualityPreset)
          if (idx > 0) setQualityPreset(PRESETS[idx - 1])
          break
        }
        case ']': {
          const idx = PRESETS.indexOf(qualityPreset)
          if (idx < PRESETS.length - 1) setQualityPreset(PRESETS[idx + 1])
          break
        }
      }
    }

    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [roi.timestep, isPlaying, qualityPreset])
}

export default function App() {
  useGlobalKeyboard()
  return <MainLayout />
}
