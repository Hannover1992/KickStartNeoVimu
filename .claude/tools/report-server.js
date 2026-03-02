/**
 * DCSRE Report Server
 * Hostet alle .md Analyse-Reports als gerenderte HTML-Seiten.
 * Keine npm-Dependencies -- nur Node.js built-in Module.
 *
 * HEALTH CHECK: Browser sendet alle 5s einen Heartbeat.
 * Kein Heartbeat seit 15s → Server terminiert sich selbst.
 *
 * Usage: node report-server.js [port]
 * Default port: 4200 (falls belegt, probiert 4201, 4202, ...)
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const BASE_DIR = path.resolve(__dirname, '..');
const ANALYSIS_DIR = path.join(BASE_DIR, 'analysis');
const PORT_START = parseInt(process.argv[2] || '4200', 10);

// --- Heartbeat / Auto-Shutdown ---
const HEARTBEAT_TIMEOUT_MS = 15_000;
let lastHeartbeat = Date.now();
let heartbeatCheckInterval = null;

function startHeartbeatCheck() {
  heartbeatCheckInterval = setInterval(() => {
    const elapsed = Date.now() - lastHeartbeat;
    if (elapsed > HEARTBEAT_TIMEOUT_MS) {
      console.log(`\n[SHUTDOWN] Kein Heartbeat seit ${Math.round(elapsed / 1000)}s -- Browser geschlossen. Server beendet sich.`);
      clearInterval(heartbeatCheckInterval);
      process.exit(0);
    }
  }, 5_000);
}

// --- Get local IP ---
function getLocalIP() {
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return '127.0.0.1';
}

// --- Markdown rendering is done CLIENT-SIDE via marked.js CDN ---
// Raw markdown is fetched via /raw/ endpoint -- zero escaping issues.

// --- Scan for reports ---
function scanReports() {
  const reports = [];
  const dirs = ['opus', 'sonnet', 'haiku'];

  for (const dir of dirs) {
    const fullDir = path.join(ANALYSIS_DIR, dir);
    if (!fs.existsSync(fullDir)) continue;
    const files = fs.readdirSync(fullDir).filter(f => f.endsWith('.md'));
    for (const file of files) {
      reports.push({
        name: file.replace('.md', ''),
        file,
        dir,
        path: path.join(fullDir, file),
        tier: dir.toUpperCase(),
      });
    }
  }

  // Root-level reports
  if (fs.existsSync(ANALYSIS_DIR)) {
    const rootFiles = fs.readdirSync(ANALYSIS_DIR).filter(f => f.endsWith('.md'));
    for (const file of rootFiles) {
      reports.push({
        name: file.replace('.md', ''),
        file,
        dir: '',
        path: path.join(ANALYSIS_DIR, file),
        tier: 'ROOT',
      });
    }
  }

  return reports;
}

// --- Heartbeat + marked.js + Mermaid JS injected into every page ---
const PAGE_SCRIPTS = `
<script src="https://cdn.jsdelivr.net/npm/marked@14/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({ startOnLoad: false, theme: 'dark' });

  // Heartbeat
  setInterval(function() {
    fetch('/heartbeat', { method: 'POST' }).catch(function(){});
  }, 5000);
  fetch('/heartbeat', { method: 'POST' }).catch(function(){});

  // Render markdown content if data-md-path is present
  (function() {
    var target = document.getElementById('rendered-content');
    if (!target) return;
    var mdPath = target.getAttribute('data-md-path');
    if (!mdPath) return;

    fetch('/raw/' + mdPath)
      .then(function(r) { return r.text(); })
      .then(function(rawMd) {
        // Custom renderer: mermaid code blocks -> <pre class="mermaid">
        var renderer = new marked.Renderer();
        renderer.code = function(args) {
          var text = args.text || '';
          var lang = (args.lang || '').trim().toLowerCase();
          if (lang === 'mermaid' || lang.startsWith('mermaid ')) {
            // If lang is "mermaid flowchart LR", prepend the extra part to the text
            if (lang.length > 7) {
              text = lang.substring(8) + '\\n' + text;
            }
            return '<pre class="mermaid">' + text + '</pre>';
          }
          var escaped = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
          return '<pre><code class="language-' + (lang || '') + '">' + escaped + '</code></pre>';
        };

        marked.setOptions({ renderer: renderer, gfm: true, breaks: false });
        target.innerHTML = marked.parse(rawMd);

        // Render mermaid diagrams after marked
        mermaid.run({ querySelector: 'pre.mermaid' }).catch(function(e) { console.warn('Mermaid:', e); });
      })
      .catch(function(e) { target.innerHTML = '<p style="color:red;">Fehler beim Laden: ' + e + '</p>'; });
  })();
</script>
`;

// --- HTML Template ---
const CSS = `
  :root {
    --bg: #0d1117; --fg: #e6edf3; --bg2: #161b22; --border: #30363d;
    --accent: #58a6ff; --green: #3fb950; --red: #f85149; --yellow: #d29922;
    --code-bg: #1c2128;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
         background: var(--bg); color: var(--fg); line-height: 1.6; }
  .container { max-width: 960px; margin: 0 auto; padding: 2rem; }
  h1 { color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin: 1.5rem 0 1rem; }
  h2 { color: var(--green); margin: 1.5rem 0 0.75rem; }
  h3 { color: var(--yellow); margin: 1.2rem 0 0.5rem; }
  h4, h5, h6 { margin: 1rem 0 0.5rem; }
  p { margin: 0.5rem 0; }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  pre { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px;
        padding: 1rem; overflow-x: auto; margin: 1rem 0; font-size: 0.85rem; }
  code { font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
         background: var(--code-bg); padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.9em; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  th, td { border: 1px solid var(--border); padding: 0.5rem 0.75rem; text-align: left; }
  th { background: var(--bg2); color: var(--accent); font-weight: 600; }
  tr:nth-child(even) { background: var(--bg2); }
  blockquote { border-left: 4px solid var(--accent); padding: 0.5rem 1rem; margin: 1rem 0;
               background: var(--bg2); border-radius: 0 6px 6px 0; }
  ul, ol { margin: 0.5rem 0 0.5rem 1.5rem; }
  li { margin: 0.25rem 0; }
  hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
  .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px;
           font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem; }
  .badge-opus { background: #7c3aed; color: white; }
  .badge-sonnet { background: #2563eb; color: white; }
  .badge-haiku { background: #059669; color: white; }
  .badge-root { background: var(--border); color: var(--fg); }
  .nav { background: var(--bg2); border-bottom: 1px solid var(--border); padding: 0.75rem 2rem;
         position: sticky; top: 0; z-index: 100; display: flex; align-items: center; gap: 1rem;
         flex-wrap: wrap; }
  .nav-title { font-weight: 700; color: var(--accent); font-size: 1.1rem; }
  .nav a { padding: 0.25rem 0.75rem; border-radius: 6px; transition: background 0.2s; }
  .nav a:hover { background: var(--border); text-decoration: none; }
  .card { background: var(--bg2); border: 1px solid var(--border); border-radius: 8px;
          padding: 1.25rem; margin: 0.75rem 0; transition: border-color 0.2s; }
  .card:hover { border-color: var(--accent); }
  .card h3 { margin: 0 0 0.5rem; }
  .card p { color: #8b949e; font-size: 0.9rem; }
  .status-bar { position: fixed; bottom: 0; left: 0; right: 0; background: var(--bg2);
                border-top: 1px solid var(--border); padding: 0.35rem 1rem;
                font-size: 0.75rem; color: #8b949e; display: flex; gap: 1.5rem; }
  .pulse { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
           background: var(--green); animation: pulse 2s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
  .tabs { display: flex; gap: 0; margin: 1.5rem 0 0; border-bottom: 2px solid var(--border); }
  .tab { padding: 0.6rem 1.2rem; cursor: pointer; border: none; background: none;
         color: #8b949e; font-size: 0.95rem; font-weight: 600; border-bottom: 2px solid transparent;
         margin-bottom: -2px; transition: all 0.2s; }
  .tab:hover { color: var(--fg); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab-content { display: none; padding-top: 0.75rem; }
  .tab-content.active { display: block; }
  .tab-count { font-size: 0.75rem; background: var(--border); color: var(--fg);
               padding: 0.1rem 0.45rem; border-radius: 10px; margin-left: 0.4rem; }
  pre.mermaid { background: transparent; border: none; padding: 0; text-align: center; }
`;

function renderPage(title, bodyHtml, navLinks, serverInfo) {
  const nav = navLinks ? `<div class="nav">
    <span class="nav-title">DCSRE Reports</span>
    ${navLinks.map(l => `<a href="${l.href}">${l.label}</a>`).join('')}
  </div>` : '';

  const statusBar = serverInfo ? `<div class="status-bar">
    <span><span class="pulse"></span> Server aktiv</span>
    <span>IP: ${serverInfo.ip}</span>
    <span>Port: ${serverInfo.port}</span>
    <span>Modus: Dauerhaft (kein Auto-Shutdown)</span>
  </div>` : '';

  return `<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${title}</title>
  <style>${CSS}</style>
</head>
<body>
  ${nav}
  <div class="container" style="padding-bottom: 3rem;">
    ${bodyHtml}
  </div>
  ${statusBar}
  ${PAGE_SCRIPTS}
</body>
</html>`;
}

// --- Server ---
function startServer(port) {
  const localIP = getLocalIP();

  const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://localhost:${port}`);

    // --- Heartbeat endpoint ---
    if (url.pathname === '/heartbeat') {
      lastHeartbeat = Date.now();
      res.writeHead(204);
      res.end();
      return;
    }

    const reports = scanReports();
    const serverInfo = { ip: localIP, port };

    if (url.pathname === '/' || url.pathname === '/index') {
      // Index page with tabs
      const groups = { opus: [], sonnet: [], other: [] };
      for (const r of reports) {
        const bucket = r.tier === 'OPUS' ? 'opus' : r.tier === 'SONNET' ? 'sonnet' : 'other';
        const firstLine = fs.readFileSync(r.path, 'utf-8').split('\n').find(l => l.startsWith('#')) || r.name;
        const title = firstLine.replace(/^#+\s*/, '');
        const badgeClass = `badge-${r.tier.toLowerCase()}`;
        groups[bucket].push(`<a href="/report/${r.dir}/${r.file}" style="text-decoration:none;color:inherit;">
          <div class="card">
            <h3>${title} <span class="badge ${badgeClass}">${r.tier}</span></h3>
            <p>${r.dir}/${r.file}</p>
          </div>
        </a>`);
      }

      const body = `
        <h1>DCSRE Analysis Reports</h1>
        <p>${reports.length} Reports | ${localIP}:${port}</p>

        <div class="tabs">
          <button class="tab active" onclick="showTab('opus')">Opus<span class="tab-count">${groups.opus.length}</span></button>
          <button class="tab" onclick="showTab('sonnet')">Sonnet<span class="tab-count">${groups.sonnet.length}</span></button>
          <button class="tab" onclick="showTab('other')">Sonstige<span class="tab-count">${groups.other.length}</span></button>
        </div>

        <div id="tab-opus" class="tab-content active">
          ${groups.opus.length ? groups.opus.join('\n') : '<p style="color:#8b949e;padding:1rem;">Keine Opus-Reports vorhanden.</p>'}
        </div>
        <div id="tab-sonnet" class="tab-content">
          ${groups.sonnet.length ? groups.sonnet.join('\n') : '<p style="color:#8b949e;padding:1rem;">Keine Sonnet-Reports vorhanden.</p>'}
        </div>
        <div id="tab-other" class="tab-content">
          ${groups.other.length ? groups.other.join('\n') : '<p style="color:#8b949e;padding:1rem;">Keine sonstigen Reports vorhanden.</p>'}
        </div>

        <script>
          function showTab(name) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + name).classList.add('active');
            event.target.classList.add('active');
          }
        </script>
      `;
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(renderPage('DCSRE Reports', body, null, serverInfo));
      return;
    }

    // --- Raw markdown endpoint (fetched by client-side marked.js) ---
    if (url.pathname.startsWith('/raw/')) {
      const relPath = url.pathname.replace('/raw/', '');
      const filePath = path.join(ANALYSIS_DIR, relPath);
      if (fs.existsSync(filePath)) {
        const md = fs.readFileSync(filePath, 'utf-8');
        const clean = md.replace(/^---[\s\S]*?---\n*/m, '');
        res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end(clean);
        return;
      }
    }

    if (url.pathname.startsWith('/report/')) {
      const relPath = url.pathname.replace('/report/', '');
      const filePath = path.join(ANALYSIS_DIR, relPath);

      if (fs.existsSync(filePath)) {
        // Client fetches raw markdown via /raw/ and renders with marked.js
        const bodyHtml = `<div id="rendered-content" data-md-path="${relPath}">
          <p style="color:#8b949e;">Lade Report...</p>
        </div>`;
        const navLinks = [
          { href: '/', label: 'Index' }
        ];
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(renderPage(relPath, bodyHtml, navLinks, serverInfo));
        return;
      }
    }

    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('404 Not Found');
  });

  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.log(`Port ${port} belegt, versuche ${port + 1}...`);
      startServer(port + 1);
    } else {
      console.error(err);
    }
  });

  server.listen(port, () => {
    console.log(`REPORT_SERVER_PORT=${port}`);
    console.log(`IP:      ${localIP}`);
    console.log(`Reports: ${scanReports().length} gefunden`);
    console.log(`Index:   http://localhost:${port}/`);
    console.log(`---`);
    console.log(`SERVER LAEUFT DAUERHAFT (kein Auto-Shutdown)`);
    console.log(`Zum Stoppen: Ctrl+C oder Task killen`);
    console.log(`---`);
    scanReports().forEach(r => {
      console.log(`  http://localhost:${port}/report/${r.dir}/${r.file}`);
    });

    // Heartbeat monitoring deaktiviert -- Server laeuft dauerhaft
    // lastHeartbeat = Date.now();
    // startHeartbeatCheck();
  });
}

startServer(PORT_START);
