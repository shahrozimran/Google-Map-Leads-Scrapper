function StatsBanner({ counts, isRunning }) {
  return (
    <div className="bg-surface border border-white/10 p-4 space-y-3">
      {/* Row 1: Core counts */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
        <div className="grid grid-cols-3 sm:flex sm:items-center sm:gap-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2">
            <span className="text-zinc-400 text-xs sm:text-sm">Total</span>
            <span className="text-white font-mono font-semibold text-base">{counts.total}</span>
          </div>
          <div className="hidden sm:block w-px h-4 bg-white/10"></div>
          <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2">
            <span className="text-zinc-400 text-xs sm:text-sm">With Site</span>
            <span className="text-green-400 font-mono font-semibold text-base">{counts.with_website}</span>
          </div>
          <div className="hidden sm:block w-px h-4 bg-white/10"></div>
          <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2">
            <span className="text-zinc-400 text-xs sm:text-sm">No Site</span>
            <span className="text-yellow-400 font-mono font-semibold text-base">{counts.without_website}</span>
          </div>
        </div>
        {isRunning && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse-dot"></div>
            <span className="text-xs text-zinc-500">RUNNING</span>
          </div>
        )}
      </div>

      {/* Row 2: Per-source breakdown */}
      <div className="border-t border-white/10 pt-3 grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-2">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0"></span>
          <span className="text-zinc-500 text-xs">Maps</span>
          <span className="text-blue-400 font-mono text-xs font-semibold ml-auto">{counts.from_maps}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"></span>
          <span className="text-zinc-500 text-xs">Google</span>
          <span className="text-indigo-400 font-mono text-xs font-semibold ml-auto">{counts.from_google}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-orange-400 flex-shrink-0"></span>
          <span className="text-zinc-500 text-xs">DuckDuckGo</span>
          <span className="text-orange-400 font-mono text-xs font-semibold ml-auto">{counts.from_duckduckgo}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0"></span>
          <span className="text-zinc-500 text-xs">Enriched</span>
          <span className="text-emerald-400 font-mono text-xs font-semibold ml-auto">{counts.enriched}</span>
        </div>
      </div>
    </div>
  )
}

export default StatsBanner
