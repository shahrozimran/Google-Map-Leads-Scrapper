import { useState } from 'react'
import SearchForm from './components/SearchForm'
import ProgressLog from './components/ProgressLog'
import StatsBanner from './components/StatsBanner'
import ResultLink from './components/ResultLink'
import EmailOutreachModal from './components/EmailOutreachModal'

function App() {
  const [taskId, setTaskId] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [counts, setCounts] = useState({
    total: 0, with_website: 0, without_website: 0,
    from_maps: 0, from_google: 0, from_duckduckgo: 0, enriched: 0
  })
  const [sheetUrl, setSheetUrl] = useState(null)
  const [status, setStatus] = useState('idle')
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false)

  // Clear sheet state
  const [isClearing, setIsClearing] = useState(false)
  const [clearStatus, setClearStatus] = useState(null) // null | 'success' | 'error'
  const [clearMessage, setClearMessage] = useState('')
  const [showClearConfirm, setShowClearConfirm] = useState(false)

  const handleStart = async (query, maxResults, filter, sources) => {
    setIsRunning(true)
    setSheetUrl(null)
    setCounts({ total: 0, with_website: 0, without_website: 0, from_maps: 0, from_google: 0, from_duckduckgo: 0, enriched: 0 })
    setStatus('running')

    try {
      const res = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, max_results: maxResults, filter, sources }),
      })
      const data = await res.json()
      if (data.task_id) {
        setTaskId(data.task_id)
      }
    } catch (err) {
      setStatus('error')
      setIsRunning(false)
    }
  }

  const handleComplete = (finalData) => {
    setIsRunning(false)
    if (finalData.sheet_url) {
      setSheetUrl(finalData.sheet_url)
    }
    if (finalData.counts) {
      setCounts(finalData.counts)
    }
    setStatus(finalData.status === 'error' ? 'error' : 'completed')
  }

  const handleCountsUpdate = (newCounts) => {
    setCounts(newCounts)
  }

  const handleClearSheet = async () => {
    setShowClearConfirm(false)
    setIsClearing(true)
    setClearStatus(null)
    setClearMessage('')
    try {
      const res = await fetch('/api/clear-sheet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheet_url: sheetUrl || '' })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Clear failed')
      setClearStatus('success')
      setClearMessage('Sheet cleared successfully. All lead data has been removed.')
    } catch (err) {
      setClearStatus('error')
      setClearMessage(`Error: ${err.message}`)
    } finally {
      setIsClearing(false)
      // Auto-dismiss after 4 seconds
      setTimeout(() => {
        setClearStatus(null)
        setClearMessage('')
      }, 4000)
    }
  }

  return (
    <div className="min-h-screen bg-black text-white overflow-x-hidden">
      {/* Header */}
      <header className="border-b border-white/10 px-4 sm:px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full shadow-[0_0_8px_#10b981]"></div>
            <h1 className="text-lg font-bold tracking-tight text-white">Google Maps Leads Generator</h1>
          </div>

          {/* Header actions */}
          <div className="flex items-center gap-2">
            {/* Clear Sheet Button */}
            {showClearConfirm ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-400">Clear all sheet data?</span>
                <button
                  onClick={handleClearSheet}
                  disabled={isClearing}
                  className="px-3 py-1.5 text-xs font-bold bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/40 rounded-lg transition-all"
                >
                  Yes, Clear
                </button>
                <button
                  onClick={() => setShowClearConfirm(false)}
                  className="px-3 py-1.5 text-xs font-medium text-zinc-400 border border-white/10 rounded-lg hover:border-white/20 transition-all"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowClearConfirm(true)}
                disabled={isClearing || isRunning}
                className="flex items-center gap-1.5 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 hover:border-red-500/40 rounded-lg font-semibold text-xs transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                title="Clear all data from the Google Sheet"
              >
                {isClearing ? (
                  <>
                    <span className="w-1.5 h-1.5 bg-red-400 rounded-full animate-pulse"></span>
                    Clearing...
                  </>
                ) : (
                  <>
                    <span>🗑️</span>
                    <span>Clear Sheet</span>
                  </>
                )}
              </button>
            )}

            {/* Email Outreach Button */}
            <button
              onClick={() => setIsEmailModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg font-semibold text-xs transition-all shadow-[0_0_15px_rgba(16,185,129,0.15)] hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]"
            >
              <span>✉️</span>
              <span>Send Outreach Emails</span>
            </button>
          </div>
        </div>

        {/* Clear status toast */}
        {clearStatus && (
          <div className="max-w-4xl mx-auto mt-2">
            <div className={`px-4 py-2 rounded-lg text-xs font-medium border ${
              clearStatus === 'success'
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-red-500/10 text-red-400 border-red-500/30'
            }`}>
              {clearMessage}
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-4 sm:space-y-6">
        <SearchForm onStart={handleStart} isRunning={isRunning} />

        {status !== 'idle' && (
          <>
            <StatsBanner counts={counts} isRunning={isRunning} />
            {taskId && (
              <ProgressLog
                taskId={taskId}
                onComplete={handleComplete}
                onCountsUpdate={handleCountsUpdate}
              />
            )}
            {sheetUrl && <ResultLink url={sheetUrl} />}
          </>
        )}
      </main>

      {/* Email Outreach Modal */}
      <EmailOutreachModal
        isOpen={isEmailModalOpen}
        onClose={() => setIsEmailModalOpen(false)}
        sheetUrl={sheetUrl}
      />
    </div>
  )
}

export default App
