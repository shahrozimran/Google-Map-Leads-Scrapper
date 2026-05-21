function ResultLink({ url }) {
  return (
    <div className="bg-surface border border-white/10 p-6 text-center space-y-3">
      <p className="text-zinc-400 text-sm">Scraping complete! Your leads are ready.</p>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-block w-full bg-white text-black font-semibold py-3 px-6 hover:bg-zinc-200 transition-colors text-center"
      >
        Open Google Sheet ↗
      </a>
    </div>
  )
}

export default ResultLink
