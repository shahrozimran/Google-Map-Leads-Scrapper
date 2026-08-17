function StatsBanner({ counts, isRunning }) {
  const primary = [
    { label: 'Total Leads',  value: counts.total           },
    { label: 'With Website', value: counts.with_website    },
    { label: 'No Website',   value: counts.without_website },
    { label: 'Enriched',     value: counts.enriched        },
  ]

  const sources = [
    { label: 'Google Maps',   value: counts.from_maps       },
    { label: 'Google Search', value: counts.from_google     },
    { label: 'DuckDuckGo',    value: counts.from_duckduckgo },
  ]

  return (
    <div style={{
      backgroundColor: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: '10px',
      overflow: 'hidden',
    }}>
      {/* ── Primary stats ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
      }}>
        {primary.map((s, i) => (
          <div
            key={s.label}
            style={{
              padding: '18px 20px',
              borderRight: i < primary.length - 1 ? '1px solid var(--border)' : 'none',
            }}
          >
            <div style={{
              fontSize: '10px',
              fontWeight: '600',
              color: 'var(--ink-3)',
              textTransform: 'uppercase',
              letterSpacing: '0.07em',
              marginBottom: '8px',
            }}>
              {s.label}
            </div>
            <div style={{
              fontSize: '28px',
              fontWeight: '700',
              fontFamily: "'JetBrains Mono', monospace",
              color: 'var(--ink)',
              lineHeight: 1,
              transition: 'color 0.2s',
            }}>
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {/* ── Source breakdown + status ── */}
      <div style={{
        padding: '10px 20px',
        borderTop: '1px solid var(--border)',
        backgroundColor: 'var(--bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
      }}>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          {sources.map(s => (
            <div key={s.label} style={{ display: 'flex', alignItems: 'baseline', gap: '5px' }}>
              <span style={{ fontSize: '11px', color: 'var(--ink-3)' }}>{s.label}</span>
              <span style={{
                fontSize: '12px',
                fontWeight: '700',
                fontFamily: "'JetBrains Mono', monospace",
                color: 'var(--ink-2)',
              }}>
                {s.value}
              </span>
            </div>
          ))}
        </div>

        {isRunning && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
            <div style={{
              width: '6px', height: '6px', borderRadius: '50%',
              backgroundColor: '#22c55e',
              animation: 'pulse-dot 1.4s ease-in-out infinite',
            }} />
            <span style={{
              fontSize: '10px', fontWeight: '600',
              color: 'var(--ink-3)',
              textTransform: 'uppercase', letterSpacing: '0.07em',
            }}>
              Live
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export default StatsBanner
