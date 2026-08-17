import React, { useState, useEffect, useRef } from 'react';

export default function EmailOutreachModal({ isOpen, onClose, sheetUrl }) {
  const [activeTab, setActiveTab] = useState('campaign'); // 'campaign', 'preview', 'test', 'sheet'
  const [previewData, setPreviewData] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // Campaign Execution State (shared between Campaign Console and Sheet Outreach tabs)
  const [isCampaignRunning, setIsCampaignRunning] = useState(false);
  const [taskId, setTaskId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [sentCount, setSentCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [queueCount, setQueueCount] = useState(0);
  const [campaignFinished, setCampaignFinished] = useState(false);
  const [activeSource, setActiveSource] = useState(null); // 'campaign' | 'sheet'

  // Test Email State
  const [testEmailInput, setTestEmailInput] = useState('');
  const [testStatus, setTestStatus] = useState({ loading: false, message: '', isError: false });

  const terminalEndRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchPreview();
    }
  }, [isOpen, sheetUrl]);

  // Reset state on modal close
  useEffect(() => {
    if (!isOpen) {
      setLogs([]);
      setSentCount(0);
      setFailedCount(0);
      setCampaignFinished(false);
      setActiveSource(null);
    }
  }, [isOpen]);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const fetchPreview = async () => {
    setLoadingPreview(true);
    try {
      const res = await fetch(`/api/outreach-preview?sheet_url=${encodeURIComponent(sheetUrl || '')}`);
      const data = await res.json();
      setPreviewData(data);
      setQueueCount(data.queue_count || 0);
    } catch (err) {
      console.error('Failed to load email preview:', err);
    } finally {
      setLoadingPreview(false);
    }
  };

  const listenToStream = (id) => {
    const eventSource = new EventSource(`/api/outreach-progress/${id}`);
    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.keepalive) return;
        if (payload.done) {
          setIsCampaignRunning(false);
          setCampaignFinished(true);
          setActiveSource(null);
          eventSource.close();
          fetchPreview();
          return;
        }
        setLogs((prev) => [...prev, payload]);
        if (payload.level === 'success' && payload.message.includes('Delivered email to')) {
          setSentCount((c) => c + 1);
        }
        if (payload.level === 'error' && payload.message.includes('Failed to send')) {
          setFailedCount((c) => c + 1);
        }
      } catch (err) {
        console.error('Error parsing SSE event:', err);
      }
    };
    eventSource.onerror = () => {
      setIsCampaignRunning(false);
      setActiveSource(null);
      eventSource.close();
    };
  };

  const startCampaign = async (endpoint = '/api/send-outreach', source = 'campaign') => {
    setIsCampaignRunning(true);
    setCampaignFinished(false);
    setActiveSource(source);
    setLogs([{ message: 'Initializing outreach campaign...', level: 'info', time: Date.now() / 1000 }]);
    setSentCount(0);
    setFailedCount(0);
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheet_url: sheetUrl })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to start campaign');
      setTaskId(data.task_id);
      listenToStream(data.task_id);
    } catch (err) {
      setIsCampaignRunning(false);
      setActiveSource(null);
      setLogs((prev) => [...prev, { message: `Launch Error: ${err.message}`, level: 'error', time: Date.now() / 1000 }]);
    }
  };

  const stopCampaign = async () => {
    if (!taskId) return;
    try {
      await fetch(`/api/stop-outreach/${taskId}`, { method: 'POST' });
      setLogs((prev) => [...prev, { message: 'Stopping campaign execution...', level: 'warning', time: Date.now() / 1000 }]);
    } catch (err) {
      console.error('Failed to stop campaign:', err);
    }
  };

  const sendTestEmail = async () => {
    if (!testEmailInput || !testEmailInput.includes('@')) {
      setTestStatus({ loading: false, message: 'Please enter a valid email address.', isError: true });
      return;
    }
    setTestStatus({ loading: true, message: 'Sending test email via Gmail SMTP...', isError: false });
    try {
      const res = await fetch('/api/test-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test_email: testEmailInput })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to send test email');
      setTestStatus({ loading: false, message: `Success! Test email delivered to ${testEmailInput}`, isError: false });
    } catch (err) {
      setTestStatus({ loading: false, message: `Error: ${err.message}`, isError: true });
    }
  };

  if (!isOpen) return null;

  const TABS = [
    { id: 'campaign', label: '⚡ Campaign Console' },
    { id: 'sheet',    label: '📬 Send to Sheet Emails' },
    { id: 'preview',  label: '📄 Email Template Preview' },
    { id: 'test',     label: '🧪 Send Test Email' },
  ];

  // Shared terminal console rendered in both campaign + sheet tabs
  const renderTerminal = () => (
    <div style={{
      flex: 1,
      backgroundColor: '#09090b',
      border: '1px solid #27272a',
      borderRadius: '10px',
      padding: '16px',
      fontFamily: 'monospace',
      fontSize: '12px',
      overflowY: 'auto',
      minHeight: '220px',
      boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.6)'
    }}>
      <div style={{ color: '#71717a', marginBottom: '8px', borderBottom: '1px solid #18181b', paddingBottom: '6px' }}>
        // Real-time Campaign Outbound Console
      </div>
      {logs.length === 0 ? (
        <div style={{ color: '#52525b', fontStyle: 'italic', marginTop: '20px' }}>
          Click the launch button to start sending emails...
        </div>
      ) : (
        logs.map((log, i) => {
          let color = '#d4d4d8';
          if (log.level === 'success') color = '#10b981';
          if (log.level === 'error')   color = '#f87171';
          if (log.level === 'warning') color = '#fbbf24';
          return (
            <div key={i} style={{ color, marginBottom: '6px', lineHeight: '1.5' }}>
              <span style={{ color: '#52525b', marginRight: '8px' }}>
                [{new Date((log.time || Date.now() / 1000) * 1000).toLocaleTimeString()}]
              </span>
              {log.message}
            </div>
          );
        })
      )}
      <div ref={terminalEndRef} />
    </div>
  );

  // Shared stats cards
  const renderStatsCards = () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
      <div style={{ backgroundColor: '#09090b', padding: '16px', borderRadius: '10px', border: '1px solid #27272a' }}>
        <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: '700' }}>Not Sent (Queue)</span>
        <div style={{ fontSize: '24px', fontWeight: '800', color: '#10b981', marginTop: '4px' }}>
          {queueCount} leads
        </div>
      </div>
      <div style={{ backgroundColor: '#09090b', padding: '16px', borderRadius: '10px', border: '1px solid #27272a' }}>
        <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: '700' }}>Sent This Session</span>
        <div style={{ fontSize: '24px', fontWeight: '800', color: '#3b82f6', marginTop: '4px' }}>
          {sentCount}
        </div>
      </div>
      <div style={{ backgroundColor: '#09090b', padding: '16px', borderRadius: '10px', border: '1px solid #27272a' }}>
        <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: '700' }}>Already Sent (Total)</span>
        <div style={{ fontSize: '24px', fontWeight: '800', color: '#8b5cf6', marginTop: '4px' }}>
          {previewData?.sent_count || 0}
        </div>
      </div>
    </div>
  );

  // Shared action buttons
  const renderActionButtons = (source, endpoint) => (
    <div style={{ display: 'flex', gap: '12px' }}>
      {!isCampaignRunning || activeSource !== source ? (
        <button
          onClick={() => startCampaign(endpoint, source)}
          disabled={isCampaignRunning || queueCount === 0}
          style={{
            flex: 1,
            padding: '14px',
            backgroundColor: (isCampaignRunning || queueCount === 0) ? '#27272a' : '#10b981',
            color: (isCampaignRunning || queueCount === 0) ? '#71717a' : '#000000',
            border: 'none',
            borderRadius: '10px',
            fontSize: '14px',
            fontWeight: '800',
            cursor: (isCampaignRunning || queueCount === 0) ? 'not-allowed' : 'pointer',
            boxShadow: (isCampaignRunning || queueCount === 0) ? 'none' : '0 0 20px rgba(16, 185, 129, 0.4)',
            transition: 'all 0.2s ease'
          }}
        >
          {isCampaignRunning && activeSource !== source
            ? '⏳ Another Campaign Running...'
            : queueCount > 0
            ? source === 'sheet'
              ? `📬 Send to All Not Sent Leads (${queueCount})`
              : `🚀 Launch Campaign (${queueCount} Leads Waiting)`
            : 'No Pending Leads in Sheet Queue'}
        </button>
      ) : (
        <button
          onClick={stopCampaign}
          style={{
            flex: 1,
            padding: '14px',
            backgroundColor: '#ef4444',
            color: '#ffffff',
            border: 'none',
            borderRadius: '10px',
            fontSize: '14px',
            fontWeight: '700',
            cursor: 'pointer'
          }}
        >
          ⏹ Stop Campaign Execution
        </button>
      )}
    </div>
  );

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 9999,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: '#09090b',
        border: '1px solid #27272a',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '900px',
        height: '88vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(16, 185, 129, 0.15)',
        overflow: 'hidden',
        color: '#f4f4f5'
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid #27272a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(180deg, #18181b 0%, #09090b 100%)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: '#10b981',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px rgba(16, 185, 129, 0.4)'
            }}>
              <span style={{ fontSize: '20px' }}>🚀</span>
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: '#ffffff', letterSpacing: '-0.3px' }}>
                Stremly Automated Cold Outreach
              </h3>
              <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: '#a1a1aa' }}>
                Sender Address: <strong style={{ color: '#10b981' }}>{previewData?.sender_email || 'email@stremly.site'}</strong>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isCampaignRunning}
            style={{
              background: 'transparent',
              border: '1px solid #3f3f46',
              color: '#a1a1aa',
              fontSize: '18px',
              borderRadius: '8px',
              width: '32px',
              height: '32px',
              cursor: isCampaignRunning ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            ✕
          </button>
        </div>

        {/* Tab Selector */}
        <div style={{
          padding: '12px 24px 0 24px',
          borderBottom: '1px solid #27272a',
          display: 'flex',
          gap: '4px',
          backgroundColor: '#09090b',
          overflowX: 'auto'
        }}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '10px 14px',
                fontSize: '12px',
                fontWeight: '600',
                borderRadius: '8px 8px 0 0',
                border: 'none',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                backgroundColor: activeTab === tab.id ? '#18181b' : 'transparent',
                color: activeTab === tab.id ? '#10b981' : '#71717a',
                borderBottom: activeTab === tab.id ? '2px solid #10b981' : '2px solid transparent',
                transition: 'all 0.2s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, padding: '24px', overflowY: 'auto', backgroundColor: '#18181b' }}>

          {/* TAB 1: CAMPAIGN CONSOLE */}
          {activeTab === 'campaign' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '16px' }}>
              {renderStatsCards()}
              {renderActionButtons('campaign', '/api/send-outreach')}
              {renderTerminal()}
            </div>
          )}

          {/* TAB 2: SEND TO SHEET EMAILS */}
          {activeTab === 'sheet' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '16px' }}>
              {/* Info banner */}
              <div style={{
                backgroundColor: '#09090b',
                border: '1px solid #1d4ed8',
                borderRadius: '10px',
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px'
              }}>
                <span style={{ fontSize: '20px', flexShrink: 0 }}>📬</span>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: '700', color: '#93c5fd', marginBottom: '4px' }}>
                    Send to Existing Sheet Leads
                  </div>
                  <div style={{ fontSize: '12px', color: '#a1a1aa', lineHeight: '1.6' }}>
                    Reads all leads directly from your connected Google Sheet and sends emails to every row with status&nbsp;
                    <strong style={{ color: '#10b981' }}>Not Sent</strong>. Rows marked&nbsp;
                    <strong style={{ color: '#3b82f6' }}>Sent</strong> or&nbsp;
                    <strong style={{ color: '#71717a' }}>NULL</strong> are automatically skipped.
                    Status updates in real time as each email is delivered.
                  </div>
                </div>
              </div>

              {/* Status summary */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                <div style={{ backgroundColor: '#09090b', padding: '14px', borderRadius: '10px', border: '1px solid #27272a' }}>
                  <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: '700' }}>Not Sent (Ready)</span>
                  <div style={{ fontSize: '26px', fontWeight: '800', color: '#10b981', marginTop: '4px' }}>{queueCount}</div>
                </div>
                <div style={{ backgroundColor: '#09090b', padding: '14px', borderRadius: '10px', border: '1px solid #27272a' }}>
                  <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: '700' }}>Already Sent</span>
                  <div style={{ fontSize: '26px', fontWeight: '800', color: '#3b82f6', marginTop: '4px' }}>{previewData?.sent_count || 0}</div>
                </div>
                <div style={{ backgroundColor: '#09090b', padding: '14px', borderRadius: '10px', border: '1px solid #27272a' }}>
                  <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: '700' }}>Sent This Session</span>
                  <div style={{ fontSize: '26px', fontWeight: '800', color: '#8b5cf6', marginTop: '4px' }}>{sentCount}</div>
                </div>
              </div>

              {renderActionButtons('sheet', '/api/send-outreach-from-sheet')}
              {renderTerminal()}
            </div>
          )}

          {/* TAB 3: TEMPLATE PREVIEW */}
          {activeTab === 'preview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ backgroundColor: '#09090b', padding: '12px 16px', borderRadius: '8px', border: '1px solid #27272a' }}>
                <span style={{ fontSize: '12px', color: '#a1a1aa' }}>Subject Line:</span>
                <div style={{ fontSize: '14px', fontWeight: '700', color: '#10b981', marginTop: '2px' }}>
                  {previewData?.sample_preview?.subject || 'Software & AI Automation Solutions for {business_name}'}
                </div>
              </div>
              {loadingPreview ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#a1a1aa' }}>Loading Stremly email template preview...</div>
              ) : (
                <div style={{
                  backgroundColor: '#ffffff',
                  borderRadius: '8px',
                  border: '1px solid #27272a',
                  overflow: 'hidden',
                  height: '420px'
                }}>
                  <iframe
                    title="Email Template Preview"
                    srcDoc={previewData?.sample_preview?.html_body || ''}
                    style={{ width: '100%', height: '100%', border: 'none' }}
                  />
                </div>
              )}
            </div>
          )}

          {/* TAB 4: TEST EMAIL */}
          {activeTab === 'test' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '500px', margin: '20px auto' }}>
              <div style={{ backgroundColor: '#09090b', padding: '20px', borderRadius: '12px', border: '1px solid #27272a' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '15px', color: '#ffffff' }}>Send a Test Email</h4>
                <p style={{ margin: '0 0 16px 0', fontSize: '12px', color: '#a1a1aa', lineHeight: '1.5' }}>
                  Send a live test email to your inbox to verify HTML rendering, logo graphics, and deliverability before running the campaign.
                </p>
                <input
                  type="email"
                  placeholder="Enter your personal email (e.g. yourname@gmail.com)"
                  value={testEmailInput}
                  onChange={(e) => setTestEmailInput(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px',
                    backgroundColor: '#18181b',
                    border: '1px solid #3f3f46',
                    borderRadius: '8px',
                    color: '#ffffff',
                    fontSize: '14px',
                    marginBottom: '14px',
                    boxSizing: 'border-box'
                  }}
                />
                <button
                  onClick={sendTestEmail}
                  disabled={testStatus.loading}
                  style={{
                    width: '100%',
                    padding: '12px',
                    backgroundColor: '#10b981',
                    color: '#000000',
                    fontWeight: '700',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '14px',
                    cursor: testStatus.loading ? 'not-allowed' : 'pointer'
                  }}
                >
                  {testStatus.loading ? 'Sending Test Email...' : '✉️ Send Test Email Now'}
                </button>
                {testStatus.message && (
                  <div style={{
                    marginTop: '14px',
                    padding: '10px 12px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    backgroundColor: testStatus.isError ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                    color: testStatus.isError ? '#f87171' : '#10b981',
                    border: `1px solid ${testStatus.isError ? '#ef4444' : '#10b981'}`
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
