import { useEffect, useRef, useState } from 'react'

function ProgressLog({ taskId, onComplete, onCountsUpdate }) {
  const [logs, setLogs] = useState([])
  const logEndRef = useRef(null)
  const eventSourceRef = useRef(null)

  useEffect(() => {
    if (!taskId) return

    const eventSource = new EventSource(`/api/progress/${taskId}`)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.keepalive) return

        if (data.done) {
          onComplete(data)
          eventSource.close()
          return
        }

        if (data.message) {
          setLogs((prev) => [...prev, data])
        }

        // Poll status for live counts
        fetch(`/api/status/${taskId}`)
          .then(res => res.json())
          .then(status => {
            if (status.counts) {
              onCountsUpdate(status.counts)
            }
          })
          .catch(() => {})
      } catch (e) {
        // Skip malformed messages
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [taskId])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const getLevelColor = (level) => {
    switch (level) {
      case 'success': return 'text-green-400'
      case 'error': return 'text-red-400'
      case 'warning': return 'text-yellow-400'
      default: return 'text-zinc-400'
    }
  }

  const getLevelPrefix = (level) => {
    switch (level) {
      case 'success': return '✓'
      case 'error': return '✗'
      case 'warning': return '!'
      default: return '›'
    }
  }

  return (
    <div className="bg-[#0a0a0a] border border-white/10 overflow-hidden">
      <div className="px-4 py-2 border-b border-white/10 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse-dot"></div>
        <span className="text-xs font-mono text-zinc-500">LIVE LOG</span>
      </div>
      <div className="log-panel h-80 overflow-y-auto p-4 font-mono text-sm space-y-0.5">
        {logs.map((log, i) => (
          <div key={i} className={`animate-fade-in ${getLevelColor(log.level)}`}>
            <span className="text-zinc-600 mr-2">{getLevelPrefix(log.level)}</span>
            {log.message}
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  )
}

export default ProgressLog
