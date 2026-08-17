import React, { useState, useEffect, useRef } from 'react';

/* ── small helpers ────────────────────────────────────────────── */
const labelStyle = {
  fontSize: '11px',
  fontWeight: '600',
  color: 'var(--ink-3)',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
};

const cardStyle = {
  backgroundColor: 'var(--bg)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  padding: '16px 18px',
};

function StatCard({ label, value, mono = true }) {
  return (
    <div style={cardStyle}>
      <div style={labelStyle}>{label}</div>
      <div style={{
        marginTop: '6px',
        fontSize: '26px',
        fontWeight: '700',
        fontFamily: mono ? "'JetBrains Mono', monospace" : 'inherit',
        color: 'var(--ink)',
        lineHeight: 1,
      }}>
        {value}
      </div>
    </div>
  );
}

function InfoBanner({ children }) {
  return (
    <div style={{
      backgroundColor: 'var(--bg)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '14px 16px',
      fontSize: '12px',
      color: 'var(--ink-2)',
      lineHeight: '1.6',
    }}>
      {children}
    </div>
  );
}

/* ── main modal ───────────────────────────────────────────────── */
export default function EmailOutreachModal({ isOpen, onClose, sheetUrl }) {
  const [activeTab, setActiveTab] = useState('campaign');
  const [previewData, setPreviewData]     = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const [isCampaignRunning, setIsCampaignRunning] = useState(false);
  const [taskId, setTaskId]           = useState(null);
  const [logs, setLogs]               = useState([]);
  const [sentCount, setSentCount]     = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [queueCount, setQueueCount]   = useState(0);
  const [campaignFinished, setCampaignFinished] = useState(false);
  const [activeSource, setActiveSource] = useState(null);

  const [testEmailInput, setTestEmailInput] = useState('');
  const [testStatus, setTestStatus] = useState({ loading: false, message: '', isError: false });

  const terminalEndRef = useRef(null);

  useEffect(() => { if (isOpen) fetchPreview(); }, [isOpen, sheetUrl]);

  useEffect(() => {
    if (!isOpen) {
      setLogs([]); setSentCount(0); setFailedCount(0);
      setCampaignFinished(false); setActiveSource(null);
    }
  }, [isOpen]);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const fetchPreview = async () => {
    setLoadingPreview(true);
    try {
      const res  = await fetch(`/api/outreach-preview?sheet_url=${encodeURIComponent(sheetUrl || '')}`);
      const data = await res.json();
      setPreviewData(data);
      setQueueCount(data.queue_count || 0);
    } catch { /* skip */ }
    finally { setLoadingPreview(false); }
  };

  const listenToStream = (id) => {
    const es = new EventSource(`/api/outreach-progress/${id}`);
    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.keepalive) return;
        if (payload.done) {
          setIsCampaignRunning(false); setCampaignFinished(true);
          setActiveSource(null); es.close(); fetchPreview(); return;
        }
        setLogs(prev => [...prev, payload]);
        if (payload.level === 'success' && payload.message.includes('Delivered email to'))
          setSentCount(c => c + 1);
        if (payload.level === 'error' && payload.message.includes('Failed to send'))
          setFailedCount(c => c + 1);
      } catch { /* skip */ }
    };
    es.onerror = () => { setIsCampaignRunning(false); setActiveSource(null); es.close(); };
  };

  const startCampaign = async (endpoint = '/api/send-outreach', source = 'campaign') => {
    setIsCampaignRunning(true); setCampaignFinished(false); setActiveSource(source);
    setLogs([{ message: 'Initializing outreach campaign...', level: 'info', time: Date.now() / 1000 }]);
    setSentCount(0); setFailedCount(0);
    try {
      const res  = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheet_url: sheetUrl })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to start campaign');
      setTaskId(data.task_id);
      listenToStream(data.task_id);
    } catch (err) {
      setIsCampaignRunning(false); setActiveSource(null);
      setLogs(prev => [...prev, { message: `Error: ${err.message}`, level: 'error', time: Date.now() / 1000 }]);
    }
  };

  const stopCampaign = async () => {
    if (!taskId) return;
    try { await fetch(`/api/stop-outreach/${taskId}`, { method: 'POST' }); }
    catch { /* skip */ }
    setLogs(prev => [...prev, { message: 'Stopping campaign...', level: 'warning', time: Date.now() / 1000 }]);
  };

  const sendTestEmail = async () => {
    if (!testEmailInput.includes('@')) {
      setTestStatus({ loading: false, message: 'Please enter a valid email address.', isError: true });
      return;
    }
    setTestStatus({ loading: true, message: 'Sending...', isError: false });
    try {
      const res  = await fetch('/api/test-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test_email: testEmailInput })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed');
      setTestStatus({ loading: false, message: `Test email delivered to ${testEmailInput}`, isError: false });
    } catch (err) {
      setTestStatus({ loading: false, message: err.message, isError: true });
    }
  };

  if (!isOpen) return null;

  const TABS = [
    { id: 'campaign', label: 'Campaign Console'     },
    { id: 'sheet',    label: 'Send to Sheet Emails' },
    { id: 'preview',  label: 'Template Preview'     },
    { id: 'test',     label: 'Send Test Email'      },
  ];

  /* ── shared terminal ──────────────────────────────────────── */
  const Terminal = () => (
    <div
      className="log-panel"
      style={{
        flex: 1,
        minHeight: '200px',
        backgroundColor: 'var(--mono-bg)',
        borderRadius: '8px',
        padding: '14px 16px',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '12px',
        lineHeight: '1.7',
        overflowY: 'auto',
        border: '1px solid #2a2a2a',
      }}
    >
      <div style={{ color: '#444', marginBottom: '8px', paddingBottom: '8px', borderBottom: '1px solid #222', fontSize: '11px' }}>
        // outbound console
      </div>
      {logs.length === 0 ? (
        <span style={{ color: '#444' }}>Waiting for launch...</span>
      ) : logs.map((log, i) => {
        const c = log.level === 'success' ? '#4ade80'
                : log.level === 'error'   ? '#f87171'
                : log.level === 'warning' ? '#fbbf24'
                : '#a3a3a3';
        const p = log.level === 'success' ? '+' : log.level === 'error' ? '!' : log.level === 'warning' ? '~' : '>';
        return (
          <div key={i} style={{ color: c, marginBottom: '2px' }}>
            <span style={{ color: '#444', marginRight: '8px', userSelect: 'none' }}>{p}</span>
            {log.message}
          </div>
        );
      })}
      <div ref={terminalEndRef} />
    </div>
  );

  /* ── shared launch / stop button ─────────────────────────── */
  const ActionButton = ({ source, endpoint }) => {
    const thisRunning = isCampaignRunning && activeSource === source;
    const otherRunning = isCampaignRunning && activeSource !== source;
    const disabled = otherRunning || (!thisRunning && queueCount === 0);

    if (thisRunning) {
      return (
        <button
          onClick={stopCampaign}
          style={{
            width: '100%', padding: '11px',
            backgroundColor: '#991b1b', color: '#fff',
            border: 'none', borderRadius: '7px',
            fontSize: '13px', fontWeight: '600', cursor: 'pointer',
          }}
        >
          Stop Campaign
        </button>
      );
    }
    return (
      <button
        onClick={() => startCampaign(endpoint, source)}
        disabled={disabled}
        style={{
          width: '100%', padding: '11px',
          backgroundColor: disabled ? 'var(--border)' : 'var(--ink)',
          color: disabled ? 'var(--ink-3)' : '#fff',
          border: 'none', borderRadius: '7px',
          fontSize: '13px', fontWeight: '600',
          cursor: disabled ? 'not-allowed' : 'pointer',
          transition: 'opacity 0.15s',
        }}
        onMouseEnter={e => { if (!disabled) e.currentTarget.style.opacity = '0.85' }}
        onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
      >
        {otherRunning
          ? 'Another campaign is running...'
          : queueCount === 0
          ? 'No pending leads'
          : source === 'sheet'
          ? `Send to All — ${queueCount} Not Sent`
          : `Launch Campaign — ${queueCount} leads`}
      </button>
    );
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      backgroundColor: 'rgba(0,0,0,0.45)',
      backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '20px',
    }}>
      <div style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '820px',
        maxHeight: '88vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
      }}>

        {/* Modal header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--surface)',
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '15px', fontWeight: '600', color: 'var(--ink)' }}>
              Cold Email Outreach
            </h2>
            <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--ink-3)' }}>
              Sender: {previewData?.sender_email || 'email@stremly.site'}
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isCampaignRunning}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--ink-3)',
              width: '30px', height: '30px',
              borderRadius: '6px',
              cursor: isCampaignRunning ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              opacity: isCampaignRunning ? 0.5 : 1,
            }}
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          gap: '0',
          borderBottom: '1px solid var(--border)',
          backgroundColor: 'var(--bg)',
          padding: '0 24px',
          overflowX: 'auto',
        }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '12px 16px',
                fontSize: '12px',
                fontWeight: activeTab === tab.id ? '600' : '400',
                color: activeTab === tab.id ? 'var(--ink)' : 'var(--ink-3)',
                backgroundColor: 'transparent',
                border: 'none',
                borderBottom: activeTab === tab.id ? '2px solid var(--ink)' : '2px solid transparent',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'color 0.15s',
                marginBottom: '-1px',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab body */}
        <div
          className="modal-scroll"
          style={{
            flex: 1, overflowY: 'auto', padding: '24px',
            backgroundColor: 'var(--surface)',
            display: 'flex', flexDirection: 'column', gap: '16px',
          }}
        >

          {/* ── Campaign Console ─────────────────────────────── */}
          {activeTab === 'campaign' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                <StatCard label="Not Sent"      value={queueCount} />
                <StatCard label="Sent (Session)" value={sentCount} />
                <StatCard label="Total Sent"    value={previewData?.sent_count || 0} />
              </div>
              <ActionButton source="campaign" endpoint="/api/send-outreach" />
              <Terminal />
            </>
          )}

          {/* ── Send to Sheet Emails ─────────────────────────── */}
          {activeTab === 'sheet' && (
            <>
              <InfoBanner>
                Sends emails to every row with status{' '}
                <strong style={{ color: 'var(--ink)' }}>Not Sent</strong> in your connected Google Sheet.
                Rows marked <strong style={{ color: 'var(--ink)' }}>Sent</strong> or{' '}
                <strong style={{ color: 'var(--ink)' }}>NULL</strong> are automatically skipped.
                Sheet statuses update in real time as each email is delivered.
              </InfoBanner>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                <StatCard label="Not Sent (Ready)"  value={queueCount} />
                <StatCard label="Already Sent"      value={previewData?.sent_count || 0} />
                <StatCard label="Sent This Session" value={sentCount} />
              </div>
              <ActionButton source="sheet" endpoint="/api/send-outreach-from-sheet" />
              <Terminal />
            </>
          )}

          {/* ── Template Preview ─────────────────────────────── */}
          {activeTab === 'preview' && (
            <>
              <div style={cardStyle}>
                <div style={labelStyle}>Subject Line</div>
                <div style={{ marginTop: '6px', fontSize: '13px', fontWeight: '500', color: 'var(--ink)' }}>
                  {previewData?.sample_preview?.subject || 'Loading...'}
                </div>
              </div>
              {loadingPreview ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--ink-3)', fontSize: '13px' }}>
                  Loading email template...
                </div>
              ) : (
                <div style={{
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  height: '420px',
                  backgroundColor: '#fff',
                }}>
                  <iframe
                    title="Email Template Preview"
                    srcDoc={previewData?.sample_preview?.html_body || ''}
                    style={{ width: '100%', height: '100%', border: 'none' }}
                  />
                </div>
              )}
            </>
          )}

          {/* ── Send Test Email ──────────────────────────────── */}
          {activeTab === 'test' && (
            <div style={{ maxWidth: '460px' }}>
              <div style={{ ...cardStyle, display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--ink)', marginBottom: '4px' }}>
                    Send a Test Email
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--ink-3)', lineHeight: '1.5' }}>
                    Verify HTML rendering and deliverability before running the full campaign.
                  </div>
                </div>

                <input
                  type="email"
                  placeholder="yourname@gmail.com"
                  value={testEmailInput}
                  onChange={e => setTestEmailInput(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    fontSize: '13px',
                    color: 'var(--ink)',
                    backgroundColor: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: '7px',
                    outline: 'none',
                  }}
                  onFocus={e => { e.target.style.borderColor = 'var(--ink)' }}
                  onBlur={e  => { e.target.style.borderColor = 'var(--border)' }}
                />

                <button
                  onClick={sendTestEmail}
                  disabled={testStatus.loading}
                  style={{
                    padding: '10px 20px',
                    fontSize: '13px',
                    fontWeight: '600',
                    backgroundColor: testStatus.loading ? 'var(--border)' : 'var(--ink)',
                    color: testStatus.loading ? 'var(--ink-3)' : '#fff',
                    border: 'none',
                    borderRadius: '7px',
                    cursor: testStatus.loading ? 'not-allowed' : 'pointer',
                    transition: 'opacity 0.15s',
                  }}
                  onMouseEnter={e => { if (!testStatus.loading) e.currentTarget.style.opacity = '0.85' }}
                  onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
                >
                  {testStatus.loading ? 'Sending...' : 'Send Test Email'}
                </button>

                {testStatus.message && (
                  <div style={{
                    padding: '10px 12px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    backgroundColor: testStatus.isError ? '#fef2f2' : '#f0fdf4',
                    color: testStatus.isError ? 'var(--danger)' : 'var(--success)',
                    border: `1px solid ${testStatus.isError ? '#fecaca' : '#bbf7d0'}`,
                  }}>
                    {testStatus.message}
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
