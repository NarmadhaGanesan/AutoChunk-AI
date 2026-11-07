import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import './styles.css';

const initialSettings = {
  strategy: 'auto',
  chunk_size: 500,
  overlap: 50,
  min_chunk_size: 100,
  max_chunk_size: 800,
  max_pages: 30,
  preserve_headings: true,
};

function RuleScoreChart({ score, thresholds }) {
  const data = [{ name: 'Structural rule score', score }];
  const fill = score >= thresholds.hierarchical_at_or_above ? '#b7f36b' : score <= thresholds.recursive_at_or_below ? '#c3a6ff' : '#f1d87f';

  return (
    <div className="score-chart" role="img" aria-label={`Rule score ${score}; this is not a probability`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 16, right: 22, left: 8, bottom: 4 }}>
          <CartesianGrid stroke="#2c3730" strokeDasharray="3 4" horizontal={false} />
          <XAxis type="number" domain={[-10, 10]} tick={{ fill: '#8e9b91', fontSize: 10 }} />
          <YAxis type="category" dataKey="name" hide />
          <Tooltip contentStyle={{ background: '#171e1a', border: '1px solid #344039', borderRadius: 8 }} />
          <ReferenceLine x={0} stroke="#77847b" />
          <ReferenceLine x={thresholds.recursive_at_or_below} stroke="#c3a6ff" strokeDasharray="4 4" />
          <ReferenceLine x={thresholds.hierarchical_at_or_above} stroke="#b7f36b" strokeDasharray="4 4" />
          <Bar dataKey="score" radius={[5, 5, 5, 5]} barSize={24}>
            {data.map((entry) => <Cell key={entry.name} fill={fill} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="chart-legend">
        <span><i className="dot purple" />Recursive ≤ {thresholds.recursive_at_or_below}</span>
        <span><i className="dot green" />Hierarchical ≥ {thresholds.hierarchical_at_or_above}</span>
      </div>
    </div>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [settings, setSettings] = useState(initialSettings);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

  const setField = (event) => {
    const { name, value, checked, type } = event.target;
    setSettings((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : type === 'number' ? Number(value) : value,
    }));
  };

  const analyze = async (event) => {
    event.preventDefault();
    if (!file) {
      setError('Choose a document to analyze first.');
      return;
    }

    setBusy(true);
    setError('');
    setResult(null);

    const body = new FormData();
    body.append('file', file);
    Object.entries(settings).forEach(([key, value]) => body.append(key, String(value)));

    try {
      const response = await fetch('/api/analyze', { method: 'POST', body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Analysis failed.');
      setResult(payload);
    } catch (problem) {
      setError(problem.message || 'Could not connect to the AutoChunk API.');
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${result.filename.replace(/\.[^.]+$/, '')}-autochunk.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="/">
          <span className="logo">⌘</span>
          AutoChunk <b>AI</b>
        </a>
        <span className="api-badge"><i /> RULE-BASED DOCUMENT INTELLIGENCE</span>
      </header>

      <section className="hero">
        <div className="eyebrow">Structure-aware chunking</div>
        <h1>Understand the document before you chunk it.</h1>
        <p>
          Inspect structure, compare the rule evidence, and preview the output before it enters your AI pipeline.
        </p>
      </section>

      <section className="layout">
        <form className="card form-card" onSubmit={analyze}>
          <h2>Analyze a document</h2>
          <p className="muted">The recommendation engine is deterministic and rule-based, not model confidence.</p>

          <label className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); if (event.dataTransfer.files[0]) setFile(event.dataTransfer.files[0]); }}>
            <input
              type="file"
              accept=".pdf,.docx,.md,.txt,.csv,.json,.html,.htm,.xml,.rtf,.log,.yaml,.yml,.jpg,.jpeg,.png,.tif,.tiff,.bmp,.gif"
              onChange={(event) => setFile(event.target.files[0])}
            />
            <span className="upload-icon">↥</span>
            <strong>{file ? file.name : 'Drop a document here'}</strong>
            <span>{file ? `${(file.size / 1024).toFixed(0)} KB · click to change` : 'or browse from your device'}</span>
          </label>

          <div className="fields">
            <label className="field wide">
              <span>CHUNKING STRATEGY</span>
              <select name="strategy" value={settings.strategy} onChange={setField}>
                <option value="auto">Auto (recommended)</option>
                <option value="hierarchical">Hierarchical</option>
                <option value="recursive">Recursive</option>
              </select>
            </label>

            <label className="field">
              <span>CHUNK SIZE</span>
              <input name="chunk_size" type="number" min="1" max="10000" value={settings.chunk_size} onChange={setField} />
            </label>

            <label className="field">
              <span>OVERLAP</span>
              <input name="overlap" type="number" min="0" max="9999" value={settings.overlap} onChange={setField} />
            </label>

            <label className="field">
              <span>MIN CHUNK</span>
              <input name="min_chunk_size" type="number" min="1" value={settings.min_chunk_size} onChange={setField} />
            </label>

            <label className="field">
              <span>MAX CHUNK</span>
              <input name="max_chunk_size" type="number" min="1" value={settings.max_chunk_size} onChange={setField} />
            </label>

            <label className="field wide">
              <span>MAX PAGES</span>
              <input name="max_pages" type="number" min="1" max="500" value={settings.max_pages} onChange={setField} />
            </label>
          </div>

          <label className="check">
            <input name="preserve_headings" type="checkbox" checked={settings.preserve_headings} onChange={setField} />
            Preserve headings in chunks
          </label>

          <button className="primary" disabled={busy}>
            {busy ? 'Analyzing document…' : 'Analyze document ↗'}
          </button>

          <p className="helper">
            PDF · DOCX · Markdown · text · data · scanned images<br />
            15 MiB maximum. Some formats may require PDF/DOCX/OCR system tools.
          </p>
        </form>

        <section className="results-column">
          {error && <div className="error" role="alert">{error}</div>}

          {!result && (
            <div className="card empty">
              <div className="orb">✳</div>
              <h2>Ready when you are</h2>
              <p>
                Upload a file to see its recommendation, structural score, rule evidence, and generated chunks.
              </p>
            </div>
          )}

          {result && (
            <>
              <section className="card recommendation-panel">
                <div className="recommendation-head">
                  <div>
                    <div className="eyebrow">Recommended method</div>
                    <h2 className="method">{result.recommendation}</h2>
                  </div>
                  <span className="status-badge">{result.strategy}</span>
                </div>
                <p className="reason">{result.reason}</p>
              </section>

              <div className="dashboard-grid">
                <section className="card score-panel">
                  <h2>Recommendation score</h2>
                  <p className="muted">Structural rule points, not probability or model confidence.</p>
                  <div className="score-wrap">
                    <RuleScoreChart score={result.rule_score} thresholds={result.thresholds} />
                  </div>
                </section>

                <section className="card evidence-panel">
                  <h2>Rule evidence</h2>
                  <ul className="evidence-list">
                    {result.rules.map((rule, index) => (
                      <li key={`${rule.description}-${index}`}>
                        <span className="rule-points">{rule.points > 0 ? '+' : ''}{rule.points}</span>
                        <span>{rule.description}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              </div>

              <section className="card stats-panel">
                <div className="stats-header">
                  <div>
                    <h2>Document stats</h2>
                  </div>
                  <button type="button" className="secondary" onClick={download}>Download JSON ↓</button>
                </div>
                <div className="stats-grid">
                  <div><span>Pages read</span><strong>{result.stats.pages_read}</strong></div>
                  <div><span>Lines</span><strong>{result.stats.lines}</strong></div>
                  <div><span>Tokens</span><strong>{result.stats.tokens}</strong></div>
                  <div><span>Chunks</span><strong>{result.stats.chunk_count}</strong></div>
                </div>
              </section>

              <section className="card">
                <div className="chunk-header">
                  <div>
                    <h2>Generated chunks</h2>
                    <p className="muted">{result.stats.chunk_count} chunks · average {result.stats.average_chunk_tokens} tokens</p>
                  </div>
                </div>

                <div className="chunk-list">
                  {result.chunks.map((chunk) => (
                    <details className="chunk" key={chunk.chunk_index} open={chunk.chunk_index === 1}>
                      <summary>
                        <span>Chunk {chunk.chunk_index} · {chunk.strategy}</span>
                        <small>{chunk.token_count} tokens · page {chunk.start_page}</small>
                      </summary>
                      <pre>{chunk.text}</pre>
                    </details>
                  ))}
                </div>
              </section>
            </>
          )}
        </section>
      </section>

      <footer className="footer">
        <span>AutoChunk AI · document structure analysis</span>
        <a href="/react">Open React dashboard ↗</a>
      </footer>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
