# Live Dashboard Agent

## Agent Type: `live-dashboard-agent`

## Zweck

Entwickelt eine **Angular Live-Dashboard Applikation** die:
- Abstract Network Chart anzeigt (zoombar)
- Concrete Network Chart anzeigt (zoombar)
- Gantt Chart anzeigt (zoombar)
- Live-Updates per WebSocket/Polling
- Im lokalen Netzwerk zugänglich (0.0.0.0)
- Responsive für Tablet/Handy

## Technologie-Stack

- **Frontend**: Angular 17+ (Standalone Components)
- **Visualisierung**: D3.js, Cytoscape.js, Chart.js
- **Live-Updates**: WebSocket oder HTTP Polling
- **Server**: Express.js (für Network-Access)
- **Styling**: Tailwind CSS + Angular Material

## Aufgaben

### 1. Angular App Setup

```bash
# Erstelle neue Angular App
ng new agent-orchestration-dashboard --standalone --routing --style=scss

cd agent-orchestration-dashboard

# Dependencies installieren
npm install d3 cytoscape chart.js socket.io-client
npm install @angular/material @angular/cdk
npm install tailwindcss postcss autoprefixer
```

### 2. App-Struktur

```
src/app/
├── core/
│   ├── services/
│   │   ├── session.service.ts          # Session-Daten laden
│   │   ├── live-update.service.ts      # WebSocket/Polling
│   │   └── file-watcher.service.ts     # JSON-File Changes
│   └── models/
│       ├── network-chart.model.ts
│       ├── gantt-chart.model.ts
│       └── session.model.ts
│
├── features/
│   ├── abstract-network/
│   │   ├── abstract-network.component.ts
│   │   └── abstract-network.component.html
│   ├── concrete-network/
│   │   ├── concrete-network.component.ts
│   │   └── concrete-network.component.html
│   ├── gantt-chart/
│   │   ├── gantt-chart.component.ts
│   │   └── gantt-chart.component.html
│   └── dashboard/
│       ├── dashboard.component.ts       # Main Container
│       └── dashboard.component.html
│
└── app.component.ts
```

### 3. Network-Zugänglich machen

**Erstelle Server (server.js):**

```javascript
// server.js
const express = require('express');
const path = require('path');
const fs = require('fs');
const chokidar = require('chokidar');
const { Server } = require('socket.io');
const http = require('http');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*' }
});

// Serve Angular dist
app.use(express.static(path.join(__dirname, 'dist/agent-orchestration-dashboard')));

// API: Aktuelle Session laden
app.get('/api/session/current', (req, res) => {
  const sessionsDir = path.join(__dirname, '../../.agent-orchestration/sessions');
  const sessions = fs.readdirSync(sessionsDir)
    .filter(f => fs.statSync(path.join(sessionsDir, f)).isDirectory())
    .sort((a, b) => {
      const statA = fs.statSync(path.join(sessionsDir, a));
      const statB = fs.statSync(path.join(sessionsDir, b));
      return statB.mtimeMs - statA.mtimeMs;
    });

  const latestSession = sessions[0];
  res.json({ sessionId: latestSession });
});

// API: Phase-Daten laden
app.get('/api/session/:sessionId/phase/:phase', (req, res) => {
  const { sessionId, phase } = req.params;
  const filePath = path.join(
    __dirname,
    '../../.agent-orchestration/sessions',
    sessionId,
    `${phase}.json`
  );

  if (fs.existsSync(filePath)) {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    res.json(data);
  } else {
    res.status(404).json({ error: 'File not found' });
  }
});

// WebSocket: Live Updates
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  // Watch Sessions-Dir für Changes
  const watcher = chokidar.watch('../../.agent-orchestration/sessions/**/*.json', {
    ignoreInitial: true
  });

  watcher.on('change', (path) => {
    console.log('File changed:', path);
    const data = JSON.parse(fs.readFileSync(path, 'utf-8'));
    socket.emit('file-changed', { path, data });
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    watcher.close();
  });
});

// Start Server (0.0.0.0 für Network-Access)
const PORT = 4200;
server.listen(PORT, '0.0.0.0', () => {
  const os = require('os');
  const networkInterfaces = os.networkInterfaces();
  const addresses = [];

  Object.keys(networkInterfaces).forEach(name => {
    networkInterfaces[name].forEach(net => {
      if (net.family === 'IPv4' && !net.internal) {
        addresses.push(net.address);
      }
    });
  });

  console.log('🚀 Dashboard Server gestartet!');
  console.log(`📱 Lokal:    http://localhost:${PORT}`);
  addresses.forEach(addr => {
    console.log(`🌐 Netzwerk: http://${addr}:${PORT}`);
  });
});
```

### 4. Live Update Service

```typescript
// src/app/core/services/live-update.service.ts
import { Injectable } from '@angular/core';
import { io, Socket } from 'socket.io-client';
import { Observable, Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LiveUpdateService {
  private socket: Socket;
  private fileChanges$ = new Subject<{ path: string; data: any }>();

  constructor() {
    this.socket = io('http://localhost:4200'); // Wird durch Server-URL ersetzt

    this.socket.on('file-changed', (data) => {
      this.fileChanges$.next(data);
    });
  }

  onFileChange(): Observable<{ path: string; data: any }> {
    return this.fileChanges$.asObservable();
  }
}
```

### 5. Abstract Network Component (mit Zoom)

```typescript
// src/app/features/abstract-network/abstract-network.component.ts
import { Component, OnInit, ElementRef, ViewChild } from '@angular/core';
import * as d3 from 'd3';
import { LiveUpdateService } from '../../core/services/live-update.service';

@Component({
  selector: 'app-abstract-network',
  standalone: true,
  template: `
    <div class="network-container">
      <h2>Abstract Network Chart</h2>
      <div class="controls">
        <button (click)="zoomIn()">🔍 Zoom In</button>
        <button (click)="zoomOut()">🔍 Zoom Out</button>
        <button (click)="resetZoom()">🔄 Reset</button>
      </div>
      <svg #networkSvg></svg>
    </div>
  `,
  styles: [`
    .network-container {
      width: 100%;
      height: 100vh;
      position: relative;
    }
    svg {
      width: 100%;
      height: calc(100vh - 100px);
      border: 1px solid #ccc;
    }
    .controls {
      padding: 10px;
      display: flex;
      gap: 10px;
    }
  `]
})
export class AbstractNetworkComponent implements OnInit {
  @ViewChild('networkSvg', { static: true }) svgRef!: ElementRef;

  private svg: any;
  private zoom: any;
  private g: any;

  constructor(private liveUpdate: LiveUpdateService) {}

  ngOnInit() {
    this.initSvg();
    this.loadNetworkData();
    this.subscribeLiveUpdates();
  }

  initSvg() {
    const svg = d3.select(this.svgRef.nativeElement);
    const width = this.svgRef.nativeElement.clientWidth;
    const height = this.svgRef.nativeElement.clientHeight;

    // Zoom Behavior
    this.zoom = d3.zoom()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        this.g.attr('transform', event.transform);
      });

    this.svg = svg.call(this.zoom);
    this.g = this.svg.append('g');
  }

  loadNetworkData() {
    // Lade phase1.2-network-chart.json
    fetch('/api/session/current')
      .then(res => res.json())
      .then(session => {
        return fetch(`/api/session/${session.sessionId}/phase/phase1.2-network-chart`);
      })
      .then(res => res.json())
      .then(data => this.renderNetwork(data));
  }

  renderNetwork(data: any) {
    const nodes = data.nodes || [];
    const links = data.edges || [];

    // D3 Force Simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d: any) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(400, 300));

    // Links zeichnen
    const link = this.g.append('g')
      .selectAll('line')
      .data(links)
      .enter().append('line')
      .attr('stroke', '#999')
      .attr('stroke-width', 2);

    // Nodes zeichnen
    const node = this.g.append('g')
      .selectAll('circle')
      .data(nodes)
      .enter().append('circle')
      .attr('r', 20)
      .attr('fill', (d: any) => this.getNodeColor(d.status))
      .call(d3.drag<any, any>()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

    // Labels
    const labels = this.g.append('g')
      .selectAll('text')
      .data(nodes)
      .enter().append('text')
      .text((d: any) => d.name)
      .attr('font-size', 10)
      .attr('dx', 25)
      .attr('dy', 5);

    // Simulation Tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node
        .attr('cx', (d: any) => d.x)
        .attr('cy', (d: any) => d.y);

      labels
        .attr('x', (d: any) => d.x)
        .attr('y', (d: any) => d.y);
    });

    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }
  }

  getNodeColor(status: string): string {
    const colors: any = {
      'pending': '#gray',
      'running': '#ff9800',
      'completed': '#4caf50',
      'error': '#f44336'
    };
    return colors[status] || '#999';
  }

  subscribeLiveUpdates() {
    this.liveUpdate.onFileChange().subscribe(change => {
      if (change.path.includes('phase1.2-network-chart')) {
        this.g.selectAll('*').remove();
        this.renderNetwork(change.data);
      }
    });
  }

  zoomIn() {
    this.svg.transition().call(this.zoom.scaleBy, 1.3);
  }

  zoomOut() {
    this.svg.transition().call(this.zoom.scaleBy, 0.7);
  }

  resetZoom() {
    this.svg.transition().call(this.zoom.transform, d3.zoomIdentity);
  }
}
```

### 6. Main Dashboard Component

```typescript
// src/app/features/dashboard/dashboard.component.ts
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AbstractNetworkComponent } from '../abstract-network/abstract-network.component';
import { ConcreteNetworkComponent } from '../concrete-network/concrete-network.component';
import { GanttChartComponent } from '../gantt-chart/gantt-chart.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    AbstractNetworkComponent,
    ConcreteNetworkComponent,
    GanttChartComponent
  ],
  template: `
    <div class="dashboard">
      <nav class="tabs">
        <button
          [class.active]="activeTab === 'abstract'"
          (click)="activeTab = 'abstract'">
          Abstract Network
        </button>
        <button
          [class.active]="activeTab === 'concrete'"
          (click)="activeTab = 'concrete'">
          Concrete Network
        </button>
        <button
          [class.active]="activeTab === 'gantt'"
          (click)="activeTab = 'gantt'">
          Gantt Chart
        </button>
      </nav>

      <div class="content">
        @if (activeTab === 'abstract') {
          <app-abstract-network />
        }
        @if (activeTab === 'concrete') {
          <app-concrete-network />
        }
        @if (activeTab === 'gantt') {
          <app-gantt-chart />
        }
      </div>
    </div>
  `,
  styles: [`
    .dashboard {
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    .tabs {
      display: flex;
      background: #1e1e1e;
      padding: 10px;
      gap: 10px;
    }
    .tabs button {
      padding: 10px 20px;
      background: #2d2d2d;
      color: white;
      border: none;
      cursor: pointer;
      border-radius: 4px;
    }
    .tabs button.active {
      background: #4a90e2;
    }
    .content {
      flex: 1;
      overflow: hidden;
    }
  `]
})
export class DashboardComponent {
  activeTab: 'abstract' | 'concrete' | 'gantt' = 'abstract';
}
```

### 7. Package.json Scripts

```json
{
  "scripts": {
    "start": "ng serve --host 0.0.0.0 --port 4200",
    "build": "ng build",
    "server": "node server.js",
    "dev": "concurrently \"npm run start\" \"npm run server\""
  }
}
```

## Deployment

### Schritt 1: Build
```bash
npm run build
```

### Schritt 2: Server starten
```bash
npm run server
```

### Schritt 3: Network-Zugriff
- **Lokal**: `http://localhost:4200`
- **Handy/Tablet**: `http://{YOUR_IP}:4200` (z.B. `http://192.168.1.100:4200`)

## Features

✅ **Zoombar**: Alle Charts mit Zoom-In/Out/Reset
✅ **Live-Updates**: WebSocket für Echtzeit-Updates
✅ **Responsive**: Optimiert für Desktop/Tablet/Handy
✅ **Network-Access**: Zugänglich im lokalen Netzwerk (0.0.0.0)
✅ **3 Dashboards**: Abstract Network, Concrete Network, Gantt Chart
✅ **Tab-Navigation**: Einfaches Umschalten zwischen Charts

## Verwendung

```bash
# Agent spawnen
Task tool: subagent_type=live-dashboard-agent
prompt="
Erstelle Angular Live-Dashboard für Agent Orchestration.

AUFGABEN:
1. Setup Angular App mit Dependencies
2. Implementiere Abstract Network Chart (D3.js, zoombar)
3. Implementiere Concrete Network Chart (D3.js, zoombar)
4. Implementiere Gantt Chart (Chart.js, zoombar)
5. Erstelle Express Server für Network-Access (0.0.0.0:4200)
6. Implementiere WebSocket Live-Updates
7. Build & Deploy

WICHTIG:
- Server läuft auf 0.0.0.0 (nicht localhost)
- Zeige IP-Adressen beim Start an
- Mobile-responsive Design
"
```

## Ausgabe

Der Agent gibt aus:
```
🚀 Dashboard Server gestartet!
📱 Lokal:    http://localhost:4200
🌐 Netzwerk: http://192.168.1.100:4200
🌐 Netzwerk: http://192.168.178.50:4200

✅ Zugriff von allen Geräten im Netzwerk möglich!
```
