import { useState } from 'react'

const SOURCES = [
  { value: 'google_maps',   label: 'Google Maps'   },
  { value: 'google_search', label: 'Google Search' },
  { value: 'duckduckgo',    label: 'DuckDuckGo'    },
]

const FILTERS = [
  { value: 'both',            label: 'All'          },
  { value: 'with_website',    label: 'With website' },
  { value: 'without_website', label: 'No website'   },
]

const EXAMPLES = [
  'Restaurants in New York',
  'Dentists in London',
  'Plumbers in Dubai',
  'Hotels in Paris',
  'Car dealers in Tokyo',
  'Lawyers in Sydney',
]

/* ── Field wrapper ──────────────────────────────────────────── */
function Field({ label, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <label style={{
        fontSize: '10px',
        fontWeight: '600',
        color: 'var(--ink-3)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
      }}>
        {label}
      </label>
      {children}
    </div>
  )
}

/* ── Toggle pill ────────────────────────────────────────────── */
function Pill({ active, onClick, disabled, children }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      style={{
        padding: '5px 12px',
        fontSize: '12px',
        fontWeight: active ? '600' : '400',
        borderRadius: '20px',
        border: `1px solid ${active ? 'var(--ink)' : 'var(--border)'}`,
        backgroundColor: active ? 'var(--ink)' : 'transparent',
        color: active ? '#fff' : 'var(--ink-2)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        transition: 'all 0.15s',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </button>
  )
}

/* ── Divider ────────────────────────────────────────────────── */
function Divider() {
  return <div style={{ height: '1px', backgroundColor: 'var(--border)', margin: '4px 0' }} />
}

/* ── Form ───────────────────────────────────────────────────── */
function SearchForm({ onStart, isRunning }) {
  const [query,      setQuery]      = useState('')
  const [maxResults, setMaxResults] = useState(100)
  const [filter,     setFilter]     = useState('both')
  const [sources,    setSources]    = useState(['google_maps', 'google_search', 'duckduckgo'])

  const toggle = val =>
    setSources(prev => prev.includes(val) ? prev.filter(s => s !== val) : [...prev, val])

  const handleSubmit = e => {
    e.preventDefault()
    if (query.trim() && sources.length > 0) onStart(query.trim(), maxResults, filter, sources)
  }

  const canSubmit = !isRunning && query.trim() && sources.length > 0

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>

      {/* Query input */}
      <Field label="Search Query">
        <textarea
          rows={2}
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="e.g. Dentists in London"
          disabled={isRunning}
          style={{
            resize: 'none',
            width: '100%',
            padding: '9px 12px',
            fontSize: '13px',
            lineHeight: '1.5',
            color: 'var(--ink)',
            backgroundColor: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: '7px',
            outline: 'none',
            transition: 'border-color 0.15s',
            opacity: isRunning ? 0.5 : 1,
            fontFamily: 'inherit',
          }}
          onFocus={e => { e.target.style.borderColor = 'var(--ink)' }}
          onBlur={e  => { e.target.style.borderColor = 'var(--border)' }}
        />
        {/* Example pills */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {EXAMPLES.map(ex => (
            <button
              key={ex}
              type="button"
              disabled={isRunning}
              onClick={() => setQuery(ex)}
              style={{
                padding: '2px 8px',
                fontSize: '10px',
                color: 'var(--ink-3)',
                backgroundColor: 'transparent',
                border: '1px solid var(--border)',
                borderRadius: '20px',
                cursor: isRunning ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s',
                opacity: isRunning ? 0.4 : 1,
              }}
              onMouseEnter={e => { if (!isRunning) { e.currentTarget.style.borderColor = 'var(--border-dark)'; e.currentTarget.style.color = 'var(--ink-2)' } }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--ink-3)' }}
            >
              {ex}
            </button>
          ))}
        </div>
      </Field>

      <Divider />

      {/* Sources */}
      <Field label="Data Sources">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {SOURCES.map(s => (
            <Pill key={s.value} active={sources.includes(s.value)} disabled={isRunning} onClick={() => toggle(s.value)}>
              {s.label}
            </Pill>
          ))}
        </div>
        {sources.length === 0 && (
          <span style={{ fontSize: '11px', color: 'var(--danger)' }}>Select at least one source.</span>
        )}
      </Field>

      {/* Filter */}
      <Field label="Filter">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {FILTERS.map(f => (
            <Pill key={f.value} active={filter === f.value} disabled={isRunning} onClick={() => setFilter(f.value)}>
              {f.label}
            </Pill>
          ))}
        </div>
      </Field>

      <Divider />

      {/* Max results */}
      <Field label={`Max Results — ${maxResults}`}>
        <input
          type="range"
          min="20" max="500" step="10"
          value={maxResults}
          onChange={e => setMaxResults(Number(e.target.value))}
          disabled={isRunning}
          style={{ width: '100%' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--ink-3)' }}>
          <span>20</span><span>500</span>
        </div>
      </Field>

      {/* Submit */}
      <button
        type="submit"
        disabled={!canSubmit}
        style={{
          width: '100%',
          padding: '10px',
          fontSize: '13px',
          fontWeight: '600',
          backgroundColor: canSubmit ? 'var(--ink)' : 'var(--border)',
          color: canSubmit ? '#fff' : 'var(--ink-3)',
          border: 'none',
          borderRadius: '7px',
          cursor: canSubmit ? 'pointer' : 'not-allowed',
          transition: 'all 0.15s',
          letterSpacing: '0.01em',
          marginTop: '2px',
        }}
        onMouseEnter={e => { if (canSubmit) e.currentTarget.style.opacity = '0.83' }}
        onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
      >
        {isRunning ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%',
              backgroundColor: '#888',
              display: 'inline-block',
              animation: 'pulse-dot 1.4s ease-in-out infinite',
            }} />
            Scraping in progress...
          </span>
        ) : 'Start Scraping'}
      </button>
    </form>
  )
}

export default SearchForm
