import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import moveLogoUrl from './assets/logo.svg'
import openDoorsLogoUrl from './assets/facelift-small.png'

type Prize = {
  id: number
  name: string
  description: string
  emoji: string
  color: string
  quantity: number
  display_weight?: number
  is_winning: boolean
}

type Lottery = {
  prizes: Prize[]
}

type Draw = {
  id: string
  prize: Omit<Prize, 'quantity'>
}

type Phase = 'ready' | 'spinning' | 'result'

const DRAW_STORAGE = 'lottery-last-result'
const REQUEST_STORAGE = 'lottery-pending-draw'
const SPIN_DURATION = 4200
const APP_BASE = import.meta.env.BASE_URL

function savedDraw(): Draw | null {
  try {
    const value = sessionStorage.getItem(DRAW_STORAGE)
    return value ? JSON.parse(value) as Draw : null
  } catch {
    return null
  }
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}

function makeWheelSlices(prizes: Prize[]) {
  const weights = prizes.map(prize => prize.quantity * (prize.display_weight ?? 1))
  const total = weights.reduce((sum, weight) => sum + weight, 0)
  let start = 0
  return prizes.map((prize, index) => {
    const end = start + (total ? weights[index] / total * 360 : 0)
    const slice = { prize, start, end, middle: (start + end) / 2 }
    start = end
    return slice
  })
}

function App() {
  const [lottery, setLottery] = useState<Lottery | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [draw, setDraw] = useState<Draw | null>(savedDraw)
  const [phase, setPhase] = useState<Phase>(() => draw ? 'result' : 'ready')
  const [rotation, setRotation] = useState(0)
  const [spinDuration, setSpinDuration] = useState(SPIN_DURATION)
  const [fixedSegments, setFixedSegments] = useState<Prize[] | null>(null)
  const rotationRef = useRef(0)
  const requestRef = useRef<string | null>(sessionStorage.getItem(REQUEST_STORAGE))
  const timerRef = useRef<number | undefined>(undefined)
  const busyRef = useRef(false)

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(`${APP_BASE}api/lottery/`, { cache: 'no-store' })
      if (!response.ok) throw new Error('Could not load the lottery. Please try again.')
      setLottery(await response.json() as Lottery)
      setError('')
    } catch (cause) {
      setError(message(cause))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    localStorage.removeItem('lottery-kiosk-key')
    void refresh()
    const interval = window.setInterval(() => {
      if (!busyRef.current) void refresh()
    }, 30000)
    return () => {
      window.clearInterval(interval)
      window.clearTimeout(timerRef.current)
    }
  }, [refresh])

  const availableSegments = useMemo(() => {
    return lottery?.prizes || []
  }, [lottery])
  const segments = fixedSegments || availableSegments
  const wheelSlices = useMemo(() => makeWheelSlices(segments), [segments])
  const gradient = useMemo(() => {
    if (!wheelSlices.length) return 'conic-gradient(#e5e9e6, #e5e9e6)'
    return `conic-gradient(${wheelSlices.map(({ prize, start, end }) =>
      `color-mix(in srgb, ${prize.color} 55%, white) ${start}deg ${end}deg`
    ).join(', ')})`
  }, [wheelSlices])

  async function spin() {
    if (busyRef.current || phase !== 'ready' || !lottery?.prizes.length) return
    busyRef.current = true
    setPhase('spinning')
    setError('')
    setFixedSegments(segments)

    try {
      const requestId = requestRef.current || crypto.randomUUID()
      requestRef.current = requestId
      sessionStorage.setItem(REQUEST_STORAGE, requestId)
      const response = await fetch(`${APP_BASE}api/draw/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ request_id: requestId }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.error || 'The draw failed. Please try again.')
      }

      const result = data as Draw
      sessionStorage.setItem(DRAW_STORAGE, JSON.stringify(result))
      setDraw(result)

      let wheelSegments = segments
      let matching = wheelSegments.map((prize, index) => prize.id === result.prize.id ? index : -1).filter(index => index >= 0)
      if (!matching.length) {
        wheelSegments = [...segments]
        wheelSegments[0] = { ...result.prize, quantity: 1 }
        setFixedSegments(wheelSegments)
        matching = [0]
      }
      const targetIndex = matching[Math.floor(Math.random() * matching.length)]
      const target = (360 - makeWheelSlices(wheelSegments)[targetIndex].middle) % 360
      const current = ((rotationRef.current % 360) + 360) % 360
      const alignment = (target - current + 360) % 360
      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      const duration = reducedMotion ? 1200 : SPIN_DURATION
      setSpinDuration(duration)
      rotationRef.current += 360 * (reducedMotion ? 2 : 6) + alignment
      setRotation(rotationRef.current)

      timerRef.current = window.setTimeout(() => {
        setPhase('result')
        busyRef.current = false
        void refresh()
      }, duration)
    } catch (cause) {
      busyRef.current = false
      setPhase('ready')
      setFixedSegments(null)
      setError(message(cause))
      void refresh()
    }
  }

  function reset() {
    requestRef.current = null
    sessionStorage.removeItem(REQUEST_STORAGE)
    sessionStorage.removeItem(DRAW_STORAGE)
    setDraw(null)
    setPhase('ready')
    setFixedSegments(null)
    setError('')
    void refresh()
  }

  const noPrizes = !loading && !lottery?.prizes.length

  return (
    <div className="app">
      <header className="topbar">
        <a className="text-link" href={`${APP_BASE}admin/`} target="_blank" rel="noreferrer">Admin</a>
      </header>

      <main className="main-content">
        <h1>Lottery</h1>

        <div className="wheel-stage">
          <img className="brand-logo-primary" src={moveLogoUrl} alt="Time to Move logo" />
          <div className="wheel-wrap" aria-hidden="true">
            <div className="wheel-pointer" />
            <div className="wheel" style={{ transform: `rotate(${rotation}deg)`, background: gradient, transitionDuration: `${spinDuration}ms` }}>
              {wheelSlices.map(({ prize, start, end, middle }, index) => (
                <div className={`wheel-item${end - start < 25 ? ' wheel-item--small' : ''}`} key={`${prize.id}-${index}`} style={{ transform: `rotate(${middle}deg) translateY(calc(var(--wheel-size) * ${end - start < 25 ? (index % 2 ? '-0.39' : '-0.27') : '-0.34'})) rotate(${-middle}deg)` }}>
                  <span>{prize.emoji}</span>
                  {end - start >= 25 && <small>{prize.name}</small>}
                </div>
              ))}
              <div className="wheel-center" />
            </div>
          </div>
          <div className="brand-mark"><img className="brand-logo-secondary" src={openDoorsLogoUrl} alt="Open Doors logo" /></div>
        </div>

        {phase === 'result' && draw ? (
          <div className="result" role="status" aria-live="polite">
            <h2>{draw.prize.is_winning === false ? 'No prize this time' : `You won: ${draw.prize.emoji} ${draw.prize.name}`}</h2>
            {draw.prize.is_winning !== false && <p>Show this screen to the team to collect your prize.</p>}
            <small>#{draw.id.slice(0, 8).toUpperCase()}</small>
            <button className="primary-button" onClick={reset}>Next player</button>
          </div>
        ) : (
          <button className="primary-button" onClick={() => void spin()} disabled={loading || noPrizes || phase === 'spinning'}>
            {loading ? 'Loading...' : noPrizes ? 'No spins left' : phase === 'spinning' ? 'Spinning...' : 'Spin'}
          </button>
        )}

        {error && <div className="error" role="alert">{error} <button onClick={() => void refresh()}>Retry</button></div>}
      </main>

    </div>
  )
}

export default App
