import { useState } from 'react'

const SOURCE_OPTIONS = [
  { value: 'google_maps',   label: 'Google Maps',   color: 'blue' },
  { value: 'google_search', label: 'Google Search', color: 'indigo' },
  { value: 'duckduckgo',    label: 'DuckDuckGo',    color: 'orange' },
]

const colorMap = {
  blue:   { on: 'bg-blue-500/20 border-blue-400 text-blue-300',     dot: 'bg-blue-400' },
  indigo: { on: 'bg-indigo-500/20 border-indigo-400 text-indigo-300', dot: 'bg-indigo-400' },
  orange: { on: 'bg-orange-500/20 border-orange-400 text-orange-300', dot: 'bg-orange-400' },
}

// Example queries shown as clickable pills below the input
const EXAMPLE_QUERIES = [
  'Restaurants in New York',
  'Dentists in London',
  'Plumbers in Dubai',
  'Hotels in Paris',
  'Car dealers in Tokyo',
  'Lawyers in Sydney',
]

function SearchForm({ onStart, isRunning }) {
  const [query, setQuery] = useState('')
  const [maxResults, setMaxResults] = useState(100)
  const [filter, setFilter] = useState('both')
  const [sources, setSources] = useState(['google_maps', 'google_search', 'duckduckgo'])

  const toggleSource = (value) => {
    setSources(prev =>
      prev.includes(value)
        ? prev.filter(s => s !== value)
        : [...prev, value]
    )
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim() && sources.length > 0) {
      onStart(query.trim(), maxResults, filter, sources)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface border border-white/10 p-4 sm:p-6 space-y-4 sm:space-y-5">

      {/* Search Query — single free-form field */}
      <div className="space-y-2">
        <label className="text-sm text-zinc-400 font-medium">Search Query</label>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. Restaurants in New York, Dentists in London, Hotels in Dubai..."
          disabled={isRunning}
          className="w-full bg-black border border-white/20 px-4 py-3 text-white placeholder-zinc-600 focus:border-white focus:outline-none transition-colors disabled:opacity-50 text-sm"
        />
        {/* Example query pills */}
        <div className="flex flex-wrap gap-1.5">
          {EXAMPLE_QUERIES.map(ex => (
            <button
              key={ex}
              type="button"
              disabled={isRunning}
              onClick={() => setQuery(ex)}
              className="text-xs px-2.5 py-1 border border-white/10 text-zinc-500 hover:border-white/30 hover:text-zinc-300 transition-colors disabled:opacity-40"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Sources toggle */}
      <div className="space-y-2">
        <label className="text-sm text-zinc-400 font-medium">Sources</label>
        <div className="grid grid-cols-3 gap-2">
          {SOURCE_OPTIONS.map((opt) => {
            const active = sources.includes(opt.value)
            const cls = colorMap[opt.color]
            return (
              <button
                key={opt.value}
                type="button"
                disabled={isRunning}
                onClick={() => toggleSource(opt.value)}
                className={`flex items-center justify-center gap-1.5 py-2 px-2 sm:px-3 text-xs sm:text-sm font-medium border transition-colors disabled:opacity-50 leading-tight ${
                  active
                    ? cls.on
                    : 'bg-black text-zinc-500 border-white/10 hover:border-white/30'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${active ? cls.dot : 'bg-zinc-600'}`}></span>
                {opt.label}
              </button>
            )
          })}
        </div>
        {sources.length === 0 && (
          <p className="text-xs text-red-400">Select at least one source.</p>
        )}
      </div>

      {/* Filter */}
      <div className="space-y-2">
        <label className="text-sm text-zinc-400 font-medium">Filter</label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: 'both',            label: 'Both' },
            { value: 'with_website',    label: 'With Website' },
            { value: 'without_website', label: 'No Website' },
          ].map((opt) => (
            <button
              key={opt.value}
              type="button"
              disabled={isRunning}
              onClick={() => setFilter(opt.value)}
              className={`py-2 px-2 sm:px-3 text-xs sm:text-sm font-medium border transition-colors disabled:opacity-50 leading-tight ${
                filter === opt.value
                  ? 'bg-white text-black border-white'
                  : 'bg-black text-zinc-400 border-white/20 hover:border-white/40'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Max Results */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm text-zinc-400 font-medium">Max Results</label>
          <span className="text-sm font-mono text-white">{maxResults}</span>
        </div>
        <input
          type="range"
          min="20"
          max="500"
          step="10"
          value={maxResults}
          onChange={(e) => setMaxResults(Number(e.target.value))}
          disabled={isRunning}
          className="w-full h-1 bg-white/20 appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-none disabled:opacity-50"
        />
        <div className="flex justify-between text-xs text-zinc-600">
          <span>20</span>
          <span>500</span>
        </div>
      </div>

      <button
        type="submit"
        disabled={isRunning || !query.trim() || sources.length === 0}
        className="w-full bg-white text-black font-semibold py-3 px-6 hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isRunning ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-2 h-2 bg-black rounded-full animate-pulse-dot"></span>
            Scraping...
          </span>
        ) : (
          'Start Scraping'
        )}
      </button>
    </form>
  )
}

export default SearchForm
