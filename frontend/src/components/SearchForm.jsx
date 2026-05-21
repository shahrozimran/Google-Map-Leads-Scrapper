import { useState } from 'react'

function SearchForm({ onStart, isRunning }) {
  const [niche, setNiche] = useState('')
  const [state, setState] = useState('')
  const [maxResults, setMaxResults] = useState(100)
  const [filter, setFilter] = useState('both')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (niche.trim() && state.trim()) {
      onStart(niche.trim(), state.trim(), maxResults, filter)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface border border-white/10 p-4 sm:p-6 space-y-4 sm:space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm text-zinc-400 font-medium">Niche / Business Type</label>
          <input
            type="text"
            value={niche}
            onChange={(e) => setNiche(e.target.value)}
            placeholder="e.g. Plumbers, Dentists, Restaurants"
            disabled={isRunning}
            className="w-full bg-black border border-white/20 px-4 py-2.5 text-white placeholder-zinc-600 focus:border-white focus:outline-none transition-colors disabled:opacity-50"
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm text-zinc-400 font-medium">State / Location</label>
          <input
            type="text"
            value={state}
            onChange={(e) => setState(e.target.value)}
            placeholder="e.g. California, New York, Texas"
            disabled={isRunning}
            className="w-full bg-black border border-white/20 px-4 py-2.5 text-white placeholder-zinc-600 focus:border-white focus:outline-none transition-colors disabled:opacity-50"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm text-zinc-400 font-medium">Filter</label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: 'both', label: 'Both' },
            { value: 'with_website', label: 'With Website' },
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
        disabled={isRunning || !niche.trim() || !state.trim()}
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
