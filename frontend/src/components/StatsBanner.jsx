function StatsBanner({ counts, isRunning }) {
  return (
    <div className="bg-surface border border-white/10 p-4 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-zinc-400 text-sm">Total Found:</span>
          <span className="text-white font-mono font-semibold">{counts.total}</span>
        </div>
        <div className="w-px h-4 bg-white/10"></div>
        <div className="flex items-center gap-2">
          <span className="text-zinc-400 text-sm">With Website:</span>
          <span className="text-green-400 font-mono font-semibold">{counts.with_website}</span>
        </div>
        <div className="w-px h-4 bg-white/10"></div>
        <div className="flex items-center gap-2">
          <span className="text-zinc-400 text-sm">Without Website:</span>
          <span className="text-yellow-400 font-mono font-semibold">{counts.without_website}</span>
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
