import React, { useEffect, useRef } from 'react'
import type { IsopycnalMesh } from '../api/isopycnal'

interface Props {
  mesh: IsopycnalMesh | null
  isLoading: boolean
}

const KM_PER_DEG_LAT = 111.32

// Minimal perspective + orbit renderer using raw WebGL.
// vtk.js is reserved for Week 11-12 quality pass; this handles the contest demo.
function buildRenderer(canvas: HTMLCanvasElement) {
  const gl = canvas.getContext('webgl')
  if (!gl) return null

  const vert = `
    attribute vec3 aPos;
    attribute float aColor;
    uniform mat4 uMVP;
    uniform float uColorMin;
    uniform float uColorRange;
    varying float vT;
    void main() {
      gl_Position = uMVP * vec4(aPos, 1.0);
      vT = (aColor - uColorMin) / max(uColorRange, 0.001);
    }
  `
  const frag = `
    precision mediump float;
    varying float vT;
    void main() {
      // viridis approximation
      float r = clamp(1.8 * vT - 0.8, 0.0, 1.0);
      float g = vT < 0.5 ? clamp(2.2 * vT, 0.0, 1.0) : clamp(2.2 - 2.2 * vT, 0.0, 1.0);
      float b = clamp(0.9 - 1.4 * vT, 0.0, 1.0);
      gl_FragColor = vec4(r, g, b, 0.85);
    }
  `

  // UNSIGNED_INT indices require this extension in WebGL1
  const extUint32 = gl.getExtension('OES_element_index_uint')

  const compile = (type: number, src: string) => {
    const sh = gl.createShader(type)!
    gl.shaderSource(sh, src); gl.compileShader(sh)
    return sh
  }
  const prog = gl.createProgram()!
  gl.attachShader(prog, compile(gl.VERTEX_SHADER, vert))
  gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, frag))
  gl.linkProgram(prog)

  return { gl, prog, extUint32 }
}

// Build a 4×4 MVP matrix (no external deps).
function mvp(
  rotX: number, rotY: number, zoom: number,
  cx: number, cy: number, cz: number,
  aspect: number,
): Float32Array {
  const cos = Math.cos, sin = Math.sin
  // Rotation X
  const rx = [
    1,0,0,0,
    0,cos(rotX),-sin(rotX),0,
    0,sin(rotX), cos(rotX),0,
    0,0,0,1,
  ]
  // Rotation Y
  const ry = [
    cos(rotY),0,sin(rotY),0,
    0,1,0,0,
    -sin(rotY),0,cos(rotY),0,
    0,0,0,1,
  ]
  const mul = (a: number[], b: number[]) => {
    const r = new Array(16).fill(0)
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++)
      for (let k = 0; k < 4; k++) r[i*4+j] += a[i*4+k]*b[k*4+j]
    return r
  }
  const rot = mul(rx, ry)
  // Translate to center mesh at origin
  const t = [
    1,0,0,0, 0,1,0,0, 0,0,1,0,
    -cx, -cy, -cz, 1,
  ]
  const mv = mul(t, rot)
  // Perspective
  const fov = Math.PI / 4, near = 0.1, far = 1000
  const f = 1 / Math.tan(fov / 2)
  const p = [
    f/aspect,0,0,0,
    0,f,0,0,
    0,0,(far+near)/(near-far),-1,
    0,0,2*far*near/(near-far),0,
  ]
  // Apply zoom by moving camera back
  const tz = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,-zoom,1]
  return new Float32Array(mul(mul(mv, tz), p))
}

export default function IsopycnalView({ mesh, isLoading }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const stateRef = useRef({ rotX: 0.62, rotY: -0.55, zoom: 2.15, dragging: false, lastX: 0, lastY: 0 })
  const rafRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !mesh || mesh.vertex_count === 0) return

    const ctx = buildRenderer(canvas)
    if (!ctx) return
    const { gl, prog, extUint32 } = ctx

    // Convert geographic coordinates into comparable local units before scaling.
    // Raw lon/lat degrees versus depth in metres collapses the mesh into a line.
    const verts = mesh.vertices
    const lons = verts.map((v) => v[0])
    const lats = verts.map((v) => v[1])
    const deps = verts.map((v) => v[2])

    const lonMin = Math.min(...lons)
    const lonMax = Math.max(...lons)
    const latMin = Math.min(...lats)
    const latMax = Math.max(...lats)
    const depMin = Math.min(...deps)
    const depMax = Math.max(...deps)

    const lonMid = (lonMax + lonMin) / 2
    const latMid = (latMax + latMin) / 2
    const depMid = (depMax + depMin) / 2
    const cosLat = Math.max(0.2, Math.cos((latMid * Math.PI) / 180))

    const localX = verts.map((v) => (v[0] - lonMid) * KM_PER_DEG_LAT * cosLat)
    const localY = verts.map((v) => (v[1] - latMid) * KM_PER_DEG_LAT)
    const localZ = verts.map((v) => -(v[2] - depMid) / 1000)

    const xRange = Math.max(...localX) - Math.min(...localX) || 1
    const yRange = Math.max(...localY) - Math.min(...localY) || 1
    const zRange = Math.max(...localZ) - Math.min(...localZ) || 1
    const horizontalRange = Math.max(xRange, yRange)
    const verticalScale = Math.min(12, Math.max(1.8, (horizontalRange * 0.42) / zRange))
    const fitRange = Math.max(xRange, yRange, zRange * verticalScale) || 1

    const posData = new Float32Array(verts.length * 3)
    for (let i = 0; i < verts.length; i++) {
      posData[i * 3] = (localX[i] / fitRange) * 2.15
      posData[i * 3 + 1] = (localY[i] / fitRange) * 2.15
      posData[i * 3 + 2] = ((localZ[i] * verticalScale) / fitRange) * 2.15
    }

    const colorData = new Float32Array(verts.length)
    const cv = mesh.color_values
    let cMin = 0, cRange = 1
    if (cv && cv.length === verts.length) {
      const valid = cv.filter((value) => Number.isFinite(value) && value !== 0)
      if (valid.length) {
        cMin = Math.min(...valid)
        cRange = Math.max(...valid) - cMin || 1
      }
      for (let i = 0; i < cv.length; i++) colorData[i] = cv[i]
    }

    const idxData = extUint32
      ? new Uint32Array(mesh.faces.flat())
      : new Uint16Array(mesh.faces.flat())
    const idxType = extUint32 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT

    const posBuf = gl.createBuffer()!
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf)
    gl.bufferData(gl.ARRAY_BUFFER, posData, gl.STATIC_DRAW)

    const colBuf = gl.createBuffer()!
    gl.bindBuffer(gl.ARRAY_BUFFER, colBuf)
    gl.bufferData(gl.ARRAY_BUFFER, colorData, gl.STATIC_DRAW)

    const idxBuf = gl.createBuffer()!
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf)
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idxData, gl.STATIC_DRAW)

    const aPos   = gl.getAttribLocation(prog, 'aPos')
    const aColor = gl.getAttribLocation(prog, 'aColor')
    const uMVP   = gl.getUniformLocation(prog, 'uMVP')
    const uCMin  = gl.getUniformLocation(prog, 'uColorMin')
    const uCRng  = gl.getUniformLocation(prog, 'uColorRange')

    const st = stateRef.current

    const draw = () => {
      const w = canvas.clientWidth, h = canvas.clientHeight
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w; canvas.height = h
      }
      gl.viewport(0, 0, w, h)
      gl.clearColor(0.04, 0.09, 0.16, 1)
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT)
      gl.enable(gl.DEPTH_TEST)
      gl.enable(gl.BLEND)
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)

      gl.useProgram(prog)
      gl.uniformMatrix4fv(uMVP, false, mvp(st.rotX, st.rotY, st.zoom, 0, 0, 0, w / h))
      gl.uniform1f(uCMin, cMin)
      gl.uniform1f(uCRng, cRange)

      gl.bindBuffer(gl.ARRAY_BUFFER, posBuf)
      gl.enableVertexAttribArray(aPos)
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0)

      gl.bindBuffer(gl.ARRAY_BUFFER, colBuf)
      gl.enableVertexAttribArray(aColor)
      gl.vertexAttribPointer(aColor, 1, gl.FLOAT, false, 0, 0)

      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf)
      gl.drawElements(gl.TRIANGLES, idxData.length, idxType, 0)

      rafRef.current = requestAnimationFrame(draw)
    }

    rafRef.current = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(rafRef.current)
      gl.deleteBuffer(posBuf)
      gl.deleteBuffer(colBuf)
      gl.deleteBuffer(idxBuf)
    }
  }, [mesh])

  // Orbit controls
  const onMouseDown = (e: React.MouseEvent) => {
    const st = stateRef.current
    st.dragging = true; st.lastX = e.clientX; st.lastY = e.clientY
  }
  const onMouseMove = (e: React.MouseEvent) => {
    const st = stateRef.current
    if (!st.dragging) return
    st.rotY += (e.clientX - st.lastX) * 0.008
    st.rotX += (e.clientY - st.lastY) * 0.008
    st.lastX = e.clientX; st.lastY = e.clientY
  }
  const onMouseUp = () => { stateRef.current.dragging = false }
  const onWheel = (e: React.WheelEvent) => {
    stateRef.current.zoom = Math.max(1, Math.min(20, stateRef.current.zoom + e.deltaY * 0.005))
  }

  if (isLoading) {
    return (
      <div style={{ width:'100%', height:'100%', display:'flex', alignItems:'center', justifyContent:'center', background:'#060f1a', color:'#2a6a9c', fontSize:13 }}>
        <span>Computing isopycnal surface…</span>
      </div>
    )
  }

  if (!mesh) {
    return (
      <div style={{ width:'100%', height:'100%', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', background:'#060f1a', color:'#2a6a9c', fontSize:12, gap:6 }}>
        <span style={{ fontSize:14, color:'#6aaad4' }}>σ₀ Isopycnal Surface</span>
        <span>Set ROI &amp; σ₀ value, then wait for job to complete</span>
      </div>
    )
  }

  if (mesh.vertex_count === 0) {
    return (
      <div style={{ width:'100%', height:'100%', display:'flex', alignItems:'center', justifyContent:'center', background:'#060f1a', color:'#f0a020', fontSize:12 }}>
        No isopycnal surface found at σ₀ = {mesh.isovalue} in this ROI
      </div>
    )
  }

  return (
    <div style={{ width:'100%', height:'100%', position:'relative' }}>
      <canvas
        ref={canvasRef}
        style={{ width:'100%', height:'100%', cursor:'grab', display:'block' }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onWheel={onWheel}
      />
      <div style={{
        position:'absolute', bottom:8, left:8,
        background:'rgba(6,15,26,0.75)', color:'#6aaad4',
        fontSize:10, padding:'3px 6px', borderRadius:3, pointerEvents:'none',
      }}>
        σ₀ = {mesh.isovalue} · drag to rotate · scroll to zoom
      </div>
    </div>
  )
}
