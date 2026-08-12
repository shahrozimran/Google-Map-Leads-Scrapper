import React, { useState, useEffect, useRef } from 'react';

export default function EmailOutreachModal({ isOpen, onClose, sheetUrl }) {
  const [activeTab, setActiveTab] = useState('campaign'); // 'campaign', 'preview', 'test'
  const [previewData, setPreviewData] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  
  // Campaign Execution State
  const [isCampaignRunning, setIsCampaignRunning] = useState(false);
  const [taskId, setTaskId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [sentCount, setSentCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [queueCount, setQueueCount] = useState(0);
  const [campaignFinished, setCampaignFinished] = useState(false);

  // Test Email State
  const [testEmailInput, setTestEmailInput] = useState('');
  const [testStatus, setTestStatus] = useState({ loading: false, message: '', isError: false });

  const terminalEndRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchPreview();
    }
  }, [isOpen, sheetUrl]);

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

  const startCampaign = async () => {
    setIsCampaignRunning(true);
    setCampaignFinished(false);
    setLogs([{ message: 'Initializing outreach campaign...', level: 'info', time: Date.now() / 1000 }]);
    setSentCount(0);
    setFailedCount(0);

    try {
      const res = await fetch('/api/send-outreach', {
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
      setLogs((prev) => [...prev, { message: `Launch Error: ${err.message}`, level: 'error', time: Date.now() / 1000 }]);
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
          eventSource.close();
          fetchPreview(); // Refresh queue count after finish
          return;
        }

        setLogs((prev) => [...prev, payload]);

        if (payload.level === 'success' && payload.message.includes('Delivered email to')) {
          setSentCount((c) => c + 1);
        }
      } catch (err) {
        console.error('Error parsing SSE event:', err);
      }
    };

    eventSource.onerror = () => {
      setIsCampaignRunning(false);
      eventSource.close();
    };
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
        maxWidth: '850px',
        height: '85vh',
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
          gap: '12px',
          backgroundColor: '#09090b'
        }}>
          {[
            { id: 'campaign', label: '⚡ Campaign Console' },
            { id: 'preview', label: '📄 Email Template Preview' },
            { id: 'test', label: '🧪 Send Test Email' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '10px 16px',
                fontSize: '13px',
                fontWeight: '600',
                borderRadius: '8px 8px 0 0',
                border: 'none',
                cursor: 'pointer',
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
              {/* Queue Stats Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                <div style={{ backgroundColor: '#09090b', padding: '16px', borderRadius: '10px', border: '1px solid #27272a' }}>
                  <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: '700' }}>Ready in Queue</span>
                  <div style={{ fontSize: '24px', fontWeight: '800', color: '#10b981', marginTop: '4px' }}>
                    {queueCount} leads
                  </div>
                </div>
                <div style={{ backgroundColor: '#09090b', padding: '16px', borderRadius: '10px', border: '1px solid #27272a' }}>
                  <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: '700' }}>Sent Delivered</span>
                  <div style={{ fontSize: '24px', fontWeight: '800', color: '#3b82f6', marginTop: '4px' }}>
                    {sentCount} / {previewData?.sent_count || 0}
                  </div>
                </div>
                <div style={{ backgroundColor: '#09090b', padding: '16px', borderRadius: '10px', border: '1px solid #27272a' }}>
                  <span style={{ fontSize: '11px', color: '#a1a1aa', textTransform: 'uppercase', fontWeight: '700' }}>Deliverability Safeguard</span>
                  <div style={{ fontSize: '12px', color: '#e4e4e7', marginTop: '6px', fontWeight: '500' }}>
                    5-12s Anti-Spam Delay Active
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '12px' }}>
                {!isCampaignRunning ? (
                  <button
                    onClick={startCampaign}
                    disabled={queueCount === 0}
                    style={{
                      flex: 1,
                      padding: '14px',
                      backgroundColor: queueCount > 0 ? '#10b981' : '#27272a',
                      color: queueCount > 0 ? '#000000' : '#71717a',
                      border: 'none',
                      borderRadius: '10px',
                      fontSize: '14px',
                      fontWeight: '800',
                      cursor: queueCount > 0 ? 'pointer' : 'not-allowed',
                      boxShadow: queueCount > 0 ? '0 0 20px rgba(16, 185, 129, 0.4)' : 'none',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {queueCount > 0 ? `🚀 Launch Campaign (${queueCount} Leads Waiting)` : 'No Pending Leads in Sheet Queue'}
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

              {/* Real-time Terminal Log Console */}
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
                <div style={{ color: '#71717a', marginBottom: '8px', borderBottom: '1px solid #18181b', pb: '6px' }}>
                  // Real-time Campaign Outbound Console
                </div>
                {logs.length === 0 ? (
                  <div style={{ color: '#52525b', fontStyle: 'italic', marginTop: '20px' }}>
                    Click "Launch Campaign" to start emailing scraped business leads...
                  </div>
                ) : (
                  logs.map((log, i) => {
                    let color = '#d4d4d8';
                    if (log.level === 'success') color = '#10b981';
                    if (log.level === 'error') color = '#f87171';
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
            </div>
          )}

          {/* TAB 2: TEMPLATE PREVIEW */}
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

          {/* TAB 3: TEST EMAIL */}
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
