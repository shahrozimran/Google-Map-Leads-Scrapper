function StatsBanner({ counts, isRunning }) {
  return (
    <div className="bg-surface border border-white/10 p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
      <div className="grid grid-cols-3 sm:flex sm:items-center sm:gap-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2">
          <span className="text-zinc-400 text-xs sm:text-sm">Total</span>
          <span className="text-white font-mono font-semibold text-base sm:text-base">{counts.total}</span>
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
  )
}

export default StatsBanner
