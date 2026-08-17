import { useState } from 'react'
import SearchForm from './components/SearchForm'
import ProgressLog from './components/ProgressLog'
import StatsBanner from './components/StatsBanner'
import ResultLink from './components/ResultLink'
import EmailOutreachModal from './components/EmailOutreachModal'

/* ── tiny shared button primitives ───────────────────────────── */
function GhostBtn({ onClick, disabled, children, style = {} }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '6px 13px',
        fontSize: '12px',
        fontWeight: '500',
        backgroundColor: 'transparent',
        color: 'var(--ink-2)',
        border: '1px solid var(--border)',
        borderRadius: '6px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        transition: 'border-color 0.15s',
        ...style,
      }}
      onMouseEnter={e => { if (!disabled) e.currentTarget.style.borderColor = 'var(--border-dark)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = style.borderColor || 'var(--border)' }}
    >
      {children}
    </button>
  )
}

function SolidBtn({ onClick, disabled, children, danger = false, style = {} }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '6px 13px',
        fontSize: '12px',
        fontWeight: '600',
        backgroundColor: danger ? 'var(--danger)' : 'var(--ink)',
        color: '#fff',
        border: 'none',
        borderRadius: '6px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        transition: 'opacity 0.15s',
        ...style,
      }}
      onMouseEnter={e => { if (!disabled) e.currentTarget.style.opacity = '0.82' }}
      onMouseLeave={e => { e.currentTarget.style.opacity = disabled ? '0.45' : '1' }}
    >
      {children}
    </button>
  )
}

/* ── Idle placeholder shown in the right panel ───────────────── */
function RightPlaceholder() {
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '12px',
      color: 'var(--ink-3)',
      padding: '48px 32px',
      textAlign: 'center',
    }}>
      {/* simple grid of dots as decorative element */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '8px',
        marginBottom: '8px',
        opacity: 0.3,
      }}>
        {Array.from({ length: 25 }).map((_, i) => (
          <div key={i} style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--ink)' }} />
        ))}
      </div>
      <p style={{ margin: 0, fontSize: '13px', fontWeight: '500', color: 'var(--ink-2)' }}>
        Configure and run a scrape
      </p>
      <p style={{ margin: 0, fontSize: '12px', lineHeight: '1.6', maxWidth: '280px' }}>
        Results, live logs, and stats will appear here once you start a scraping job.
      </p>
    </div>
  )
}

/* ── App ─────────────────────────────────────────────────────── */
function App() {
  const [taskId,    setTaskId]    = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [counts,    setCounts]    = useState({
    total: 0, with_website: 0, without_website: 0,
    from_maps: 0, from_google: 0, from_duckduckgo: 0, enriched: 0,
  })
  const [sheetUrl, setSheetUrl]   = useState(null)
  const [status,   setStatus]     = useState('idle')
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false)

  /* clear sheet */
  const [isClearing,       setIsClearing]       = useState(false)
  const [clearStatus,      setClearStatus]      = useState(null)
  const [clearMessage,     setClearMessage]     = useState('')
  const [showClearConfirm, setShowClearConfirm] = useState(false)

  const handleStart = async (query, maxResults, filter, sources) => {
    setIsRunning(true)
    setSheetUrl(null)
    setCounts({ total: 0, with_website: 0, without_website: 0, from_maps: 0, from_google: 0, from_duckduckgo: 0, enriched: 0 })
    setStatus('running')
    try {
      const res  = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, max_results: maxResults, filter, sources }),
      })
      const data = await res.json()
      if (data.task_id) setTaskId(data.task_id)
    } catch {
      setStatus('error'); setIsRunning(false)
    }
  }

  const handleComplete = (finalData) => {
    setIsRunning(false)
    if (finalData.sheet_url) setSheetUrl(finalData.sheet_url)
    if (finalData.counts)    setCounts(finalData.counts)
    setStatus(finalData.status === 'error' ? 'error' : 'completed')
  }

  const handleCountsUpdate = (newCounts) => setCounts(newCounts)

  const handleClearSheet = async () => {
    setShowClearConfirm(false); setIsClearing(true); setClearStatus(null)
    try {
      const res  = await fetch('/api/clear-sheet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheet_url: sheetUrl || '' }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Clear failed')
      setClearStatus('success')
      setClearMessage('Sheet cleared successfully.')
    } catch (err) {
      setClearStatus('error'); setClearMessage(err.message)
    } finally {
      setIsClearing(false)
      setTimeout(() => { setClearStatus(null); setClearMessage('') }, 4000)
    }
  }

  const hasOutput = status !== 'idle'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', backgroundColor: 'var(--bg)' }}>

      {/* ══ Top bar ════════════════════════════════════════════ */}
      <header style={{
        height: '52px',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        backgroundColor: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        zIndex: 40,
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--ink)' }} />
          <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--ink)', letterSpacing: '-0.2px' }}>
            Leads Generator
          </span>
          <span style={{
            fontSize: '10px',
            fontWeight: '500',
            color: 'var(--ink-3)',
            backgroundColor: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            padding: '1px 6px',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}>
            Beta
          </span>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Toast */}
          {clearStatus && (
            <span style={{
              fontSize: '11px',
              fontWeight: '500',
              color: clearStatus === 'success' ? 'var(--success)' : 'var(--danger)',
              padding: '4px 10px',
              borderRadius: '5px',
              backgroundColor: clearStatus === 'success' ? '#f0fdf4' : '#fef2f2',
              border: `1px solid ${clearStatus === 'success' ? '#bbf7d0' : '#fecaca'}`,
            }}>
              {clearMessage}
            </span>
          )}

          {/* Clear confirm inline */}
          {showClearConfirm ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '11px', color: 'var(--ink-3)' }}>Delete all sheet data?</span>
              <SolidBtn onClick={handleClearSheet} danger>Confirm</SolidBtn>
              <GhostBtn onClick={() => setShowClearConfirm(false)}>Cancel</GhostBtn>
            </div>
          ) : (
            <GhostBtn onClick={() => setShowClearConfirm(true)} disabled={isClearing || isRunning}>
              {isClearing ? 'Clearing...' : 'Clear Sheet'}
            </GhostBtn>
          )}

          <SolidBtn onClick={() => setIsEmailModalOpen(true)}>
            Send Outreach Emails
          </SolidBtn>
        </div>
      </header>

      {/* ══ Body: sidebar + right panel ════════════════════════ */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── Left sidebar ─────────────────────────────────── */}
        <aside style={{
          width: '340px',
          flexShrink: 0,
          borderRight: '1px solid var(--border)',
          backgroundColor: 'var(--surface)',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
        }}>
          {/* Sidebar header */}
          <div style={{
            padding: '20px 24px 14px',
            borderBottom: '1px solid var(--border)',
          }}>
            <h2 style={{ margin: 0, fontSize: '13px', fontWeight: '600', color: 'var(--ink)' }}>
              Configure Scrape
            </h2>
            <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--ink-3)' }}>
              Set your query, sources, and filters below.
            </p>
          </div>

          {/* Search form lives in sidebar */}
          <div style={{ padding: '20px 24px', flex: 1 }}>
            <SearchForm onStart={handleStart} isRunning={isRunning} />
          </div>

          {/* Sidebar footer — status indicator */}
          <div style={{
            padding: '14px 24px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'var(--bg)',
          }}>
            <div style={{
              width: '6px', height: '6px', borderRadius: '50%',
              backgroundColor: isRunning ? '#22c55e' : status === 'error' ? 'var(--danger)' : status === 'completed' ? '#22c55e' : 'var(--border-dark)',
              animation: isRunning ? 'pulse-dot 1.4s ease-in-out infinite' : 'none',
              flexShrink: 0,
            }} />
            <span style={{ fontSize: '11px', color: 'var(--ink-3)', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {isRunning ? 'Scraping' : status === 'error' ? 'Error' : status === 'completed' ? 'Complete' : 'Idle'}
            </span>
          </div>
        </aside>

        {/* ── Right panel ──────────────────────────────────── */}
        <main style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          backgroundColor: 'var(--bg)',
        }}>
          {/* Right panel header */}
          <div style={{
            padding: '0 28px',
            height: '48px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--border)',
            backgroundColor: 'var(--surface)',
            flexShrink: 0,
          }}>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
              Output
            </span>
            {sheetUrl && (
              <a
                href={sheetUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '5px',
                  fontSize: '11px', fontWeight: '600',
                  color: 'var(--ink)', textDecoration: 'none',
                  padding: '4px 10px',
                  border: '1px solid var(--border)',
                  borderRadius: '5px',
                  transition: 'border-color 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-dark)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)' }}
              >
                Open Google Sheet
                <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                  <path d="M2 10L10 2M10 2H4M10 2V8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </a>
            )}
          </div>

          {/* Right panel body */}
          <div
            className="modal-scroll"
            style={{ flex: 1, overflowY: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: '16px' }}
          >
            {!hasOutput && <RightPlaceholder />}

            {hasOutput && (
              <>
                {/* Stats grid */}
                <StatsBanner counts={counts} isRunning={isRunning} />

                {/* Live log */}
                {taskId && (
                  <ProgressLog
                    taskId={taskId}
                    onComplete={handleComplete}
                    onCountsUpdate={handleCountsUpdate}
                  />
                )}

                {/* Sheet ready card */}
                {sheetUrl && <ResultLink url={sheetUrl} />}
              </>
            )}
          </div>
        </main>
      </div>

      {/* ══ Modal ══════════════════════════════════════════════ */}
      <EmailOutreachModal
        isOpen={isEmailModalOpen}
        onClose={() => setIsEmailModalOpen(false)}
        sheetUrl={sheetUrl}
      />
    </div>
  )
}

export default App
