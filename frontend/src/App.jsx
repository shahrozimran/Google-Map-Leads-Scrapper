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

  return (
    <div className="min-h-screen bg-black text-white overflow-x-hidden">
      {/* Header */}
      <header className="border-b border-white/10 px-4 sm:px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full shadow-[0_0_8px_#10b981]"></div>
            <h1 className="text-lg font-bold tracking-tight text-white">Google Maps Leads Generator</h1>
          </div>
          <button
            onClick={() => setIsEmailModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg font-semibold text-xs transition-all shadow-[0_0_15px_rgba(16,185,129,0.15)] hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]"
          >
            <span>✉️</span>
            <span>Send Outreach Emails</span>
          </button>
        </div>
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
