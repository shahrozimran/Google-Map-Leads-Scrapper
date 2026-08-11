import { useState } from 'react'
import SearchForm from './components/SearchForm'
import ProgressLog from './components/ProgressLog'
import StatsBanner from './components/StatsBanner'
import ResultLink from './components/ResultLink'

function App() {
  const [taskId, setTaskId] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [counts, setCounts] = useState({
    total: 0, with_website: 0, without_website: 0,
    from_maps: 0, from_google: 0, from_duckduckgo: 0, enriched: 0
  })
  const [sheetUrl, setSheetUrl] = useState(null)
  const [status, setStatus] = useState('idle')

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
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <div className="w-2 h-2 bg-white rounded-full"></div>
          <h1 className="text-lg font-semibold tracking-tight">Leads Scraper</h1>
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
    </div>
  )
}

export default App
