import { useEffect, useState } from 'react'
import Library from '../features/library/Library'
import { checkHealth } from '../api/health'

type HealthState = 'loading' | 'ready' | 'unavailable'
const messages: Record<HealthState, string> = {
  loading: 'Checking local connection…',
  ready: 'Ready — local connection is available.',
  unavailable: 'Unavailable — check that the local backend is running, then reload.',
}

export default function App() {
  const [health, setHealth] = useState<HealthState>('loading')

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    const timeout = window.setTimeout(() => {
      if (active) setHealth('unavailable')
      active = false
      controller.abort()
    }, 5000)
    checkHealth(controller.signal)
      .then(() => { if (active) setHealth('ready') })
      .catch(() => { if (active) setHealth('unavailable') })
      .finally(() => window.clearTimeout(timeout))
    return () => {
      active = false
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [])

  return (
    <main>
      <p className="eyebrow">Your local learning workspace</p>
      <h1>PDF Learning OS</h1>
      <p>Read. Understand. Recall. Build. Teach.</p>
      <section aria-labelledby="connection-heading">
        <h2 id="connection-heading">Local connection</h2>
        <p role="status" className={`status ${health}`}>{messages[health]}</p>
      </section>
      <Library />
    </main>
  )
}
