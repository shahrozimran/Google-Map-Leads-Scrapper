import { useEffect, useRef, useState } from 'react'

function ProgressLog({ taskId, onComplete, onCountsUpdate }) {
  const [logs, setLogs] = useState([])
  const logEndRef       = useRef(null)

  useEffect(() => {
    if (!taskId) return
    const es = new EventSource(`/api/progress/${taskId}`)

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.keepalive) return
        if (data.done) { onComplete(data); es.close(); return }
        if (data.message) setLogs(prev => [...prev, data])
        fetch(`/api/status/${taskId}`)
          .then(r => r.json())
          .then(s => { if (s.counts) onCountsUpdate(s.counts) })
          .catch(() => {})
      } catch { /* skip */ }
    }

    es.onerror = () => es.close()
    return () => es.close()
  }, [taskId])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const levelColor = (level) => {
    switch (level) {
      case 'success': return '#4ade80'
      case 'error':   return '#f87171'
      case 'warning': return '#fbbf24'
      default:        return '#8a8a8a'
    }
  }

  const levelChar = (level) => {
    switch (level) {
      case 'success': return '+'
      case 'error':   return '!'
      case 'warning': return '~'
      default:        return '›'
    }
  }

  return (
    <div style={{
      backgroundColor: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: '10px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Panel label */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        backgroundColor: 'var(--bg)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flexShrink: 0,
      }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          backgroundColor: '#22c55e',
          animation: 'pulse-dot 1.4s ease-in-out infinite',
          flexShrink: 0,
        }} />
        <span style={{
          fontSize: '10px', fontWeight: '600',
          color: 'var(--ink-3)',
          textTransform: 'uppercase', letterSpacing: '0.08em',
        }}>
          Live Output
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: '10px',
          color: 'var(--ink-3)',
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          {logs.length} lines
        </span>
      </div>

      {/* Terminal */}
      <div
        className="log-panel"
        style={{
          height: '320px',
          overflowY: 'auto',
          padding: '14px 16px',
          backgroundColor: 'var(--mono-bg)',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '12px',
          lineHeight: '1.8',
        }}
      >
        {logs.length === 0 ? (
          <span style={{ color: '#3a3a3a' }}>Waiting for output...</span>
        ) : logs.map((log, i) => (
          <div
            key={i}
            className="animate-fade-in"
            style={{ color: levelColor(log.level), marginBottom: '1px' }}
          >
            <span style={{ color: '#3a3a3a', marginRight: '10px', userSelect: 'none' }}>
              {levelChar(log.level)}
            </span>
            {log.message}
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  )
}

export default ProgressLog
