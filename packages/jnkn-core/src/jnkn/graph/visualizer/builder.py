"""
Visualization Builder.

Contains all HTML, CSS, and JS assets embedded as strings to ensure:
1. Zero IO latency (instant generation)
2. No package data/manifest issues
3. Single-file portability
"""

# =============================================================================
# CSS ASSETS
# =============================================================================
CSS_CONTENT = """
:root {
    /* Surfaces */
    --surface-void: #050508;
    --surface-base: #0a0a0f;
    --surface-elevated: #101015;
    --surface-overlay: #16161d;
    --surface-interactive: #1c1c25;
    --surface-active: #24242f;
    
    /* Borders */
    --border-subtle: rgba(255,255,255,0.04);
    --border-default: rgba(255,255,255,0.08);
    --border-strong: rgba(255,255,255,0.15);
    
    /* Text */
    --text-primary: #f0f0f5;
    --text-secondary: #9898a8;
    --text-tertiary: #5c5c6e;
    --text-disabled: #3e3e4a;
    
    /* Semantic: Status */
    --status-critical: #ff4757;
    --status-warning: #ffa502;
    --status-success: #2ed573;
    --status-info: #3b82f6;
    
    /* Semantic: Confidence */
    --confidence-high: var(--status-success);
    --confidence-medium: var(--status-warning);
    --confidence-low: var(--status-critical);
    
    /* Semantic: Domains */
    --domain-infrastructure: #ff6b35;
    --domain-configuration: #00d9ff;
    --domain-code: #a855f7;
    --domain-data: #22d3ee;
    
    /* Typography */
    --font-display: 'Space Grotesk', -apple-system, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
    
    --text-xs: 10px;
    --text-sm: 11px;
    --text-base: 13px;
    --text-lg: 15px;
    --text-xl: 18px;
    --text-2xl: 24px;
    
    /* Spacing */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 20px;
    
    /* Radii */
    --radius-sm: 4px;
    --radius-md: 6px;
    --radius-lg: 10px;
    --radius-full: 9999px;
    
    /* Transitions */
    --ease-out: cubic-bezier(0.4, 0, 0.2, 1);
    --duration-fast: 150ms;
    
    /* Diff Colors */
    --diff-added-bg: rgba(46, 213, 115, 0.08);
    --diff-removed-bg: rgba(255, 71, 87, 0.08);
    --diff-mod-bg: rgba(255, 165, 2, 0.08);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    height: 100vh;
    background: var(--surface-void);
    color: var(--text-primary);
    font-family: var(--font-display);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background-image: radial-gradient(ellipse at 50% 0%, rgba(59, 130, 246, 0.03) 0%, transparent 60%);
}

/* Header */
.header {
    height: 52px;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    padding: 0 var(--space-4);
    background: var(--surface-base);
    gap: 20px;
    position: relative;
    z-index: 100;
}

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: var(--text-lg);
    letter-spacing: -0.02em;
}

.brand-logo {
    width: 28px; height: 28px;
    background: linear-gradient(135deg, var(--status-info) 0%, var(--domain-code) 100%);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 700;
}

/* Stats */
.stats-bar { display: flex; gap: 16px; font-size: 11px; font-family: var(--font-mono); }
.stat { display: flex; align-items: center; gap: 6px; color: var(--text-tertiary); }
.stat-value { color: var(--text-secondary); font-weight: 600; }
.stat-critical .stat-value { color: var(--status-critical); }

/* Mode Toggle */
.mode-toggle {
    display: flex; background: var(--surface-overlay);
    border-radius: 6px; padding: 3px; border: 1px solid var(--border-default);
}
.mode-btn {
    background: transparent; border: none; color: var(--text-tertiary);
    padding: 6px 14px; font-size: 11px; font-weight: 600; cursor: pointer;
    border-radius: 4px; transition: 0.15s; font-family: var(--font-display);
    text-transform: uppercase;
}
.mode-btn:hover { color: var(--text-secondary); }
.mode-btn.active { background: var(--status-info); color: white; }

/* Search */
.search-container { flex: 1; max-width: 360px; position: relative; }
.search-input {
    width: 100%; background: var(--surface-overlay); border: 1px solid var(--border-default);
    padding: 8px 12px 8px 36px; border-radius: 6px; color: var(--text-primary);
    font-size: 13px; font-family: var(--font-display); transition: 0.15s;
}
.search-input:focus { border-color: var(--status-info); outline: none; }
.search-icon {
    position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
    color: var(--text-tertiary); font-size: 13px; pointer-events: none;
}
.search-results {
    position: absolute; top: calc(100% + 4px); left: 0; width: 100%;
    background: var(--surface-elevated); border: 1px solid var(--border-default);
    border-radius: 8px; max-height: 320px; overflow-y: auto; display: none;
    z-index: 1000; box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.search-item {
    padding: 10px 14px; cursor: pointer; font-size: 13px;
    border-bottom: 1px solid var(--border-subtle); display: flex;
    align-items: center; gap: 10px; transition: 0.15s;
}
.search-item:hover { background: var(--surface-interactive); }

/* Main Layout */
.main-container { flex: 1; display: flex; overflow: hidden; }
.columns-wrapper {
    flex: 1; display: flex; overflow-x: auto; scroll-behavior: smooth;
    scrollbar-width: thin; scrollbar-color: var(--surface-active) transparent;
}
.column {
    width: 340px; min-width: 340px; border-right: 1px solid var(--border-subtle);
    background: var(--surface-base); display: flex; flex-direction: column;
    animation: slideIn 0.25s ease forwards;
}
.column:nth-child(odd) { background: var(--surface-elevated); }
.column.in-trace-path { background: rgba(59, 130, 246, 0.03); }
.column-header {
    padding: 14px 16px; border-bottom: 1px solid var(--border-subtle);
    display: flex; justify-content: space-between; align-items: center;
    background: inherit; position: sticky; top: 0; z-index: 10;
}
.column-title { font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); }
.column-count {
    font-size: 10px; font-family: var(--font-mono); color: var(--text-disabled);
    background: var(--surface-overlay); padding: 2px 8px; border-radius: 10px;
}
.column-list { flex: 1; overflow-y: auto; padding: 8px; }

/* Inspector */
.inspector {
    width: 440px; min-width: 440px; background: var(--surface-elevated);
    border-left: 1px solid var(--border-default); display: none;
    flex-direction: column; position: relative;
}
.inspector.visible { display: flex; }
.inspector-header {
    padding: 20px; border-bottom: 1px solid var(--border-subtle);
    background: linear-gradient(180deg, var(--surface-overlay) 0%, var(--surface-elevated) 100%);
}
.inspector-icon { font-size: 32px; margin-bottom: 12px; }
.inspector-title { font-size: 18px; font-weight: 700; margin-bottom: 4px; word-break: break-all; }
.inspector-id { font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono); word-break: break-all; }

.action-bar { display: flex; gap: 8px; margin-top: 16px; }
.btn {
    flex: 1; padding: 10px 12px; border-radius: var(--radius-md);
    border: 1px solid var(--border-default); background: var(--surface-overlay);
    color: var(--text-secondary); cursor: pointer; font-size: 12px; font-weight: 600;
    display: flex; align-items: center; justify-content: center; gap: 8px;
    transition: 0.15s;
}
.btn:hover:not(:disabled) { background: var(--surface-interactive); color: var(--text-primary); border-color: var(--border-strong); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-primary { background: var(--status-info); color: white; border-color: var(--status-info); }
.btn-primary:hover:not(:disabled) { background: #2563eb; border-color: #2563eb; }

/* Tabs */
.tabs { display: flex; border-bottom: 1px solid var(--border-subtle); background: var(--surface-base); padding: 0 12px; }
.tab {
    padding: 12px 16px; font-size: 11px; font-weight: 600; text-transform: uppercase;
    color: var(--text-tertiary); cursor: pointer; border-bottom: 2px solid transparent;
}
.tab:hover { color: var(--text-secondary); }
.tab.active { color: var(--text-primary); border-bottom-color: var(--status-info); }
.tab-content { padding: 20px; flex: 1; overflow-y: auto; display: none; }
.tab-content.active { display: block; }

/* Components */
.item {
    display: flex; align-items: flex-start; padding: 10px 12px; margin-bottom: 4px;
    border-radius: var(--radius-md); cursor: pointer; border: 1px solid transparent;
    font-size: var(--text-base); transition: background var(--duration-fast) var(--ease-out);
    position: relative; animation: fadeIn 0.2s ease forwards;
}
.item:hover { background: var(--surface-interactive); border-color: var(--border-subtle); }
.item.active { background: var(--surface-active); border-color: var(--border-default); }
.item.in-trace { background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.3); }
.item.in-trace::before {
    content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: var(--status-info); border-radius: 3px 0 0 3px;
}
.item.diff-added { background: var(--diff-added-bg); border-left: 3px solid var(--status-success); }
.item.diff-removed { background: var(--diff-removed-bg); border-left: 3px solid var(--status-critical); opacity: 0.6; }
.item.diff-modified { background: var(--diff-mod-bg); border-left: 3px solid var(--status-warning); }

.item-icon { margin-right: 10px; font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.item-content { flex: 1; min-width: 0; }
.item-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; }
.item-meta { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; font-family: var(--font-mono); }
.item-chevron { color: var(--text-disabled); font-size: 14px; margin-left: 8px; }

/* Badges */
.badges { display: flex; gap: 4px; margin-top: 6px; flex-wrap: wrap; }
.badge {
    font-size: 9px; padding: 2px 6px; border-radius: 3px; text-transform: uppercase;
    font-weight: 600; font-family: var(--font-mono); border: 1px solid var(--border-subtle);
    background: var(--surface-overlay); color: var(--text-tertiary);
}
.badge-runtime { background: rgba(168, 85, 247, 0.15); color: #c084fc; border-color: rgba(168, 85, 247, 0.3); }
.confidence-indicator { display: inline-flex; align-items: center; gap: 4px; font-size: 9px; font-family: var(--font-mono); }
.conf-dot { width: 8px; height: 8px; border-radius: 50%; border: 2px solid currentColor; }
.conf-high { color: var(--confidence-high); } .conf-high .conf-dot { background: currentColor; }
.conf-medium { color: var(--confidence-medium); } .conf-medium .conf-dot { background: transparent; }
.conf-low { color: var(--confidence-low); } .conf-low .conf-dot { background: transparent; border-style: dashed; }
.risk-indicator {
    display: inline-flex; align-items: center; gap: 4px; font-size: 9px;
    padding: 2px 6px; border-radius: 3px; font-family: var(--font-mono); font-weight: 600;
}
.risk-high { background: var(--color-critical-bg); color: var(--status-critical); border: 1px solid rgba(255, 71, 87, 0.3); }
.risk-medium { background: var(--color-warning-bg); color: var(--status-warning); border: 1px solid rgba(255, 165, 2, 0.3); }

/* Evidence Panel */
.evidence-panel {
    background: var(--surface-overlay); border: 1px solid var(--border-default);
    border-radius: var(--radius-lg); padding: 16px; margin-bottom: 20px;
}
.evidence-header {
    display: flex; align-items: center; gap: 8px; margin-bottom: 12px; font-size: 11px;
    font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-tertiary);
}
.evidence-content { font-size: 13px; color: var(--text-secondary); line-height: 1.6; }
.evidence-code {
    display: block; background: var(--surface-base); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm); padding: 10px 12px; margin: 10px 0;
    font-family: var(--font-mono); font-size: 12px; color: var(--text-primary); overflow-x: auto;
}
.evidence-highlight { color: var(--domain-configuration); font-weight: 600; }

/* Details */
.detail-section { margin-bottom: 20px; }
.detail-section-title {
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--text-disabled); margin-bottom: 10px; padding-bottom: 6px;
    border-bottom: 1px solid var(--border-subtle);
}
.detail-row { display: flex; margin-bottom: 10px; font-size: 13px; align-items: flex-start; }
.detail-label {
    width: 90px; color: var(--text-tertiary); flex-shrink: 0; font-size: 11px;
    font-weight: 500; text-transform: uppercase; padding-top: 2px;
}
.detail-value { flex: 1; color: var(--text-secondary); word-break: break-all; font-family: var(--font-mono); font-size: 12px; }

/* Modal */
.modal-overlay {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0, 0, 0, 0.85); z-index: 1000;
    display: none; align-items: center; justify-content: center;
    backdrop-filter: blur(4px);
}
.modal-overlay.visible { display: flex; }
.modal-content {
    width: 90vw; height: 90vh; background: var(--surface-base);
    border-radius: var(--radius-lg); border: 1px solid var(--border-default);
    display: flex; flex-direction: column; box-shadow: 0 24px 48px rgba(0,0,0,0.5);
}
.modal-header {
    padding: 16px 20px; border-bottom: 1px solid var(--border-subtle);
    display: flex; justify-content: space-between; align-items: center;
}
.modal-title { font-size: 16px; font-weight: 700; }
#mesh-container { flex: 1; overflow: hidden; background: var(--surface-void); }

/* D3 */
.node circle { stroke: var(--surface-base); stroke-width: 2px; cursor: pointer; transition: 0.15s; }
.node circle:hover { stroke-width: 3px; }
.link { stroke: var(--border-default); stroke-opacity: 0.6; }
.node text { font-size: 11px; fill: var(--text-secondary); pointer-events: none; font-family: var(--font-mono); }

/* Animations */
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
@keyframes slideIn { from { opacity: 0; transform: translateX(10px); } to { opacity: 1; transform: translateX(0); } }
"""

# =============================================================================
# JS ASSETS
# =============================================================================
JS_CONTENT = """
// --- UTILS ---
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

function getCategoryIcon(cat) {
    return { 'Infrastructure': '☁️', 'Configuration': '⚙️', 'Code': '💻', 'Data': '📊' }[cat] || '📦';
}

function getNodeIcon(type) {
    const t = (type || '').toLowerCase();
    if (t.includes('infra') || t.includes('aws') || t.includes('terraform')) return '☁️';
    if (t.includes('env') || t.includes('config')) return '⚙️';
    if (t.includes('data') || t.includes('table') || t.includes('dbt')) return '📊';
    if (t.includes('python') || t.includes('py')) return '🐍';
    if (t.includes('js') || t.includes('javascript') || t.includes('ts')) return '📜';
    return '📄';
}

function getChangeIcon(changeType) {
    return { 'added': '➕', 'removed': '➖', 'modified': '✏️' }[changeType] || '•';
}

// --- STATE ---
const AppState = {
    nodeMap: {},
    outgoingEdges: {},
    incomingEdges: {},
    blastRadiusCache: {},
    mode: 'downstream',
    currentNode: null,
    currentEdge: null,
    tracePath: [],
    _listeners: new Map(),
    
    subscribe(key, callback) {
        if (!this._listeners.has(key)) this._listeners.set(key, new Set());
        this._listeners.get(key).add(callback);
    },
    emit(key, value) { this._listeners.get(key)?.forEach(cb => cb(value)); },
    setMode(mode) { this.mode = mode; this.emit('mode', mode); },
    selectNode(node, edge = null) {
        this.currentNode = node;
        this.currentEdge = edge;
        this.emit('selection', { node, edge });
    }
};

// --- DATA ---
function indexGraphData(rawData) {
    AppState.nodeMap = {};
    AppState.outgoingEdges = {};
    AppState.incomingEdges = {};
    
    rawData.nodes.forEach(n => AppState.nodeMap[n.id] = n);
    rawData.edges?.forEach(e => {
        if (!AppState.outgoingEdges[e.source_id]) AppState.outgoingEdges[e.source_id] = [];
        AppState.outgoingEdges[e.source_id].push(e);
        
        if (!AppState.incomingEdges[e.target_id]) AppState.incomingEdges[e.target_id] = [];
        AppState.incomingEdges[e.target_id].push(e);
    });
}

function computeBlastRadius() {
    Object.keys(AppState.nodeMap).forEach(nodeId => {
        const visited = new Set();
        const queue = [nodeId];
        while (queue.length > 0) {
            const current = queue.shift();
            if (visited.has(current)) continue;
            visited.add(current);
            (AppState.outgoingEdges[current] || []).forEach(e => {
                if (!visited.has(e.target_id)) queue.push(e.target_id);
            });
        }
        AppState.blastRadiusCache[nodeId] = visited.size - 1;
    });
}

// --- COLUMNS ---
function getDomainForNode(node) {
    const t = (node.type || '').toLowerCase();
    const id = node.id.toLowerCase();
    if (t.includes('infra') || id.startsWith('infra:')) return 'Infrastructure';
    if (t.includes('env') || t.includes('config') || id.startsWith('env:')) return 'Configuration';
    if (t.includes('data') || id.startsWith('data:')) return 'Data';
    return 'Code';
}

function renderRootColumn() {
    const wrapper = document.getElementById('columnsWrapper');
    wrapper.innerHTML = '';
    AppState.tracePath = [];
    const groups = { 'Infrastructure': [], 'Configuration': [], 'Code': [], 'Data': [] };
    
    Object.values(AppState.nodeMap).forEach(n => {
        const domain = getDomainForNode(n);
        if (groups[domain]) groups[domain].push(n);
    });
    
    const col = createColumn('Domains', Object.values(AppState.nodeMap).length);
    Object.keys(groups).forEach(key => {
        if (groups[key].length === 0) return;
        const blastTotal = groups[key].reduce((sum, n) => sum + (AppState.blastRadiusCache[n.id] || 0), 0);
        const avgBlast = Math.round(blastTotal / groups[key].length);
        const item = document.createElement('div');
        item.className = 'item';
        item.dataset.domain = key;
        item.innerHTML = `
            <span class="item-icon">${getCategoryIcon(key)}</span>
            <div class="item-content">
                <div class="item-title">${key}</div>
                <div class="item-meta">${groups[key].length} artifacts</div>
            </div>
            ${avgBlast > 3 ? `<span class="risk-indicator risk-medium">⚡ ${avgBlast} avg</span>` : ''}
            <span class="item-chevron">›</span>
        `;
        item.onclick = () => {
            highlightItem(item);
            AppState.tracePath = [key];
            renderNodeList(groups[key], key, 0);
        };
        col.querySelector('.column-list').appendChild(item);
    });
    wrapper.appendChild(col);
}

function renderNodeList(nodes, title, parentColIndex) {
    removeColumnsAfter(parentColIndex);
    const col = createColumn(title, nodes.length);
    const myColIndex = parentColIndex + 1;
    
    nodes.sort((a, b) => {
        const brDiff = (AppState.blastRadiusCache[b.id] || 0) - (AppState.blastRadiusCache[a.id] || 0);
        if (brDiff !== 0) return brDiff;
        return a.name.localeCompare(b.name);
    });
    
    nodes.forEach((node, idx) => {
        const item = createNodeItem(node, null, idx);
        item.dataset.nodeId = node.id;
        item.onclick = () => {
            highlightItem(item);
            AppState.tracePath = AppState.tracePath.slice(0, myColIndex);
            AppState.tracePath.push(node.id);
            AppState.selectNode(node, null);
            renderConnections(node, myColIndex);
        };
        item.onmouseenter = () => highlightTrace(node.id, myColIndex);
        item.onmouseleave = () => clearTraceHighlight();
        col.querySelector('.column-list').appendChild(item);
    });
    document.getElementById('columnsWrapper').appendChild(col);
    col.scrollIntoView({behavior: 'smooth', inline: 'end'});
}

function renderConnections(node, parentColIndex) {
    removeColumnsAfter(parentColIndex);
    let connections = [];
    let title = '';
    
    if (AppState.mode === 'downstream') {
        const edges = AppState.outgoingEdges[node.id] || [];
        connections = edges.map(e => ({ node: AppState.nodeMap[e.target_id], edge: e })).filter(c => c.node);
        title = `Impacts`;
    } else {
        const edges = AppState.incomingEdges[node.id] || [];
        connections = edges.map(e => ({ node: AppState.nodeMap[e.source_id], edge: e })).filter(c => c.node);
        title = `Dependencies`;
    }
    
    if (connections.length === 0) return;
    const col = createColumn(title, connections.length);
    const myColIndex = parentColIndex + 1;
    connections.sort((a, b) => (b.edge.confidence || 1) - (a.edge.confidence || 1));
    
    connections.forEach(({node: connNode, edge}, idx) => {
        const item = createNodeItem(connNode, edge, idx);
        item.dataset.nodeId = connNode.id;
        item.onclick = () => {
            highlightItem(item);
            AppState.tracePath = AppState.tracePath.slice(0, myColIndex);
            AppState.tracePath.push(connNode.id);
            AppState.selectNode(connNode, edge);
            renderConnections(connNode, myColIndex);
        };
        item.onmouseenter = () => highlightTrace(connNode.id, myColIndex);
        item.onmouseleave = () => clearTraceHighlight();
        col.querySelector('.column-list').appendChild(item);
    });
    document.getElementById('columnsWrapper').appendChild(col);
    col.scrollIntoView({behavior: 'smooth', inline: 'end'});
}

function createColumn(title, count) {
    const div = document.createElement('div');
    div.className = 'column';
    div.innerHTML = `<div class="column-header"><span class="column-title">${title}</span><span class="column-count">${count}</span></div><div class="column-list"></div>`;
    return div;
}

function createNodeItem(node, edge, index) {
    const div = document.createElement('div');
    let classes = 'item';
    const changeType = node.metadata?.change_type;
    if (changeType === 'added') classes += ' diff-added';
    if (changeType === 'removed') classes += ' diff-removed';
    if (changeType === 'modified') classes += ' diff-modified';
    div.className = classes;
    div.style.animationDelay = `${index * 0.03}s`;
    
    const blastRadius = AppState.blastRadiusCache[node.id] || 0;
    const icon = getNodeIcon(node.type);
    let badgesHtml = '<div class="badges">';
    if (edge) {
        const conf = edge.confidence || 1;
        const confClass = conf >= 0.8 ? 'conf-high' : conf >= 0.5 ? 'conf-medium' : 'conf-low';
        badgesHtml += `<span class="confidence-indicator ${confClass}"><span class="conf-dot"></span>${Math.round(conf * 100)}%</span>`;
    }
    if (blastRadius > 5) badgesHtml += `<span class="risk-indicator risk-medium">⚡ ${blastRadius}</span>`;
    badgesHtml += '</div>';
    
    div.innerHTML = `
        <span class="item-icon">${icon}</span>
        <div class="item-content">
            <div class="item-title">${node.name}</div>
            <div class="item-meta">${node.type}</div>
            ${badgesHtml}
        </div>
        <span class="item-chevron">›</span>
    `;
    return div;
}

function highlightItem(item) {
    const list = item.parentElement;
    Array.from(list.children).forEach(c => c.classList.remove('active'));
    item.classList.add('active');
}

function removeColumnsAfter(index) {
    const wrapper = document.getElementById('columnsWrapper');
    while (wrapper.children.length > index + 1) {
        wrapper.removeChild(wrapper.lastChild);
    }
}

function highlightTrace(nodeId, colIndex) {
    clearTraceHighlight();
    const wrapper = document.getElementById('columnsWrapper');
    const columns = Array.from(wrapper.children);
    for (let i = 0; i <= colIndex; i++) columns[i]?.classList.add('in-trace-path');
    AppState.tracePath.forEach(pathNodeId => {
        document.querySelector(`.item[data-node-id="${pathNodeId}"]`)?.classList.add('in-trace');
    });
    document.querySelector(`.item[data-node-id="${nodeId}"]`)?.classList.add('in-trace');
}

function clearTraceHighlight() {
    document.querySelectorAll('.in-trace-path').forEach(el => el.classList.remove('in-trace-path'));
    document.querySelectorAll('.in-trace').forEach(el => el.classList.remove('in-trace'));
}

// --- INSPECTOR ---
AppState.subscribe('selection', ({node, edge}) => {
    updateInspector(node, edge);
});

function updateInspector(node, contextEdge = null) {
    const inspector = document.getElementById('inspector');
    inspector.classList.add('visible');
    
    document.getElementById('insp-icon').textContent = getNodeIcon(node.type);
    document.getElementById('insp-title').textContent = node.name;
    document.getElementById('insp-id').textContent = node.id;
    
    const btnEditor = document.getElementById('btn-editor');
    btnEditor.disabled = !node.path;
    btnEditor.title = node.path || 'No file path available';
    
    const upEdges = AppState.incomingEdges[node.id] || [];
    const downEdges = AppState.outgoingEdges[node.id] || [];
    document.getElementById('tab-up-count').textContent = upEdges.length;
    document.getElementById('tab-down-count').textContent = downEdges.length;

    renderEvidenceTab(node, contextEdge);
    renderDetailsTab(node);
    renderDependencyTab('view-upstream', upEdges, 'source_id');
    renderDependencyTab('view-downstream', downEdges, 'target_id');
    
    switchTab('evidence');
}

function renderEvidenceTab(node, edge) {
    const container = document.getElementById('view-evidence');
    if (!edge) {
        const blastRadius = AppState.blastRadiusCache[node.id] || 0;
        const riskLevel = blastRadius > 10 ? 'high' : blastRadius > 5 ? 'medium' : 'low';
        container.innerHTML = `
            <div class="strength-meter">
                <div class="strength-header">
                    <span class="strength-label">Blast Radius: </span>
                    <span class="strength-value ${riskLevel}">${blastRadius}</span>
                </div>
                <div class="strength-bar">
                    <div class="strength-fill ${riskLevel}" style="width: ${Math.min(100, blastRadius * 5)}%"></div>
                </div>
            </div>
            <div class="evidence-panel">
                <div class="evidence-header"><span class="evidence-header-icon">📍</span><span>Location</span></div>
                <div class="evidence-content">${node.path ? `<code class="evidence-code">${node.path}</code>` : 'No file path'}</div>
            </div>
            ${node.metadata?.change_type ? `
            <div class="evidence-panel" style="border-color: var(--diff-mod-border);">
                <div class="evidence-header"><span class="evidence-header-icon">${getChangeIcon(node.metadata.change_type)}</span><span>Change Detected</span></div>
                <div class="evidence-content">This artifact was <strong>${node.metadata.change_type}</strong>.</div>
            </div>` : ''}
        `;
        return;
    }
    const evidence = buildEvidenceExplanation(edge, node);
    const conf = edge.confidence || 1;
    const confClass = conf >= 0.8 ? 'conf-high' : conf >= 0.5 ? 'conf-medium' : 'conf-low';
    container.innerHTML = `
        <div class="strength-meter">
            <div class="strength-header">
                <span class="strength-label">Confidence</span>
                <span class="strength-value ${confClass}">${Math.round(conf * 100)}%</span>
            </div>
            <div class="strength-bar"><div class="strength-fill ${confClass}" style="width: ${conf * 100}%"></div></div>
        </div>
        <div class="evidence-panel">
            <div class="evidence-header"><span class="evidence-header-icon">🔗</span><span>Connection Evidence</span></div>
            <div class="evidence-content">
                ${evidence.explanation}
                ${evidence.sourceCode ? `<code class="evidence-code">${escapeHtml(evidence.sourceCode)}</code>` : ''}
                ${evidence.targetCode ? `<code class="evidence-code">${escapeHtml(evidence.targetCode)}</code>` : ''}
            </div>
        </div>
    `;
}

function buildEvidenceExplanation(edge, node) {
    const sourceNode = AppState.nodeMap[edge.source_id];
    const targetNode = AppState.nodeMap[edge.target_id];
    const via = edge.metadata?.via || edge.metadata?.env_var || edge.metadata?.matched_key;
    const edgeType = (edge.type || '').toLowerCase();

    if (edgeType === 'env_reference' || via) {
        return {
            explanation: `<strong>${sourceNode?.name}</strong> outputs a value that <strong>${targetNode?.name}</strong> reads via environment variable.`,
            sourceCode: sourceNode?.path ? `# ${sourceNode.path}\noutput "${via}" { value = ... }` : null,
            targetCode: targetNode?.path ? `# ${targetNode.path}\nos.getenv('${via}')` : null
        };
    } 
    return {
        explanation: `Static analysis detected a <span class="evidence-highlight">${edge.type || 'dependency'}</span> relationship. ${edge.metadata?.explanation || ''}`,
        sourceCode: null,
        targetCode: null
    };
}

function renderDetailsTab(node) {
    const container = document.getElementById('view-details');
    container.innerHTML = `
        <div class="detail-section">
            <div class="detail-section-title">Metadata</div>
            <div class="detail-row"><span class="detail-label">Type</span><span class="detail-value">${node.type}</span></div>
            <div class="detail-row"><span class="detail-label">ID</span><span class="detail-value">${node.id}</span></div>
            ${Object.entries(node.metadata || {}).map(([k, v]) => `
                <div class="detail-row"><span class="detail-label">${k}</span><span class="detail-value">${JSON.stringify(v)}</span></div>
            `).join('')}
        </div>
    `;
}

function renderDependencyTab(elementId, edges, nodeKey) {
    const container = document.getElementById(elementId);
    if (edges.length === 0) { container.innerHTML = '<div class="empty-state">No dependencies</div>'; return; }
    container.innerHTML = edges.map(e => {
        const other = AppState.nodeMap[e[nodeKey]];
        if (!other) return '';
        return `
            <div class="dep-list-item" onclick="jumpToNode('${other.id}')">
                <div class="dep-list-name"><span>${getNodeIcon(other.type)}</span><strong>${other.name}</strong></div>
            </div>
        `;
    }).join('');
}

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`.tab[data-tab="${tabName}"]`)?.classList.add('active');
    document.getElementById(`view-${tabName}`)?.classList.add('active');
}

function openEditor() {
    if (AppState.currentNode?.path) {
        const line = AppState.currentNode.metadata?.line || 1;
        window.location.href = `vscode://file/${AppState.currentNode.path}:${line}`;
    }
}

// --- MESH ---
function openMeshModal() {
    if (!AppState.currentNode) return;
    document.getElementById('meshModal').classList.add('visible');
    setTimeout(() => renderMesh(AppState.currentNode), 50);
}

function closeMeshModal() {
    document.getElementById('meshModal').classList.remove('visible');
    document.getElementById('mesh-container').innerHTML = '';
}

function renderMesh(centerNode) {
    const container = document.getElementById('mesh-container');
    container.innerHTML = '';
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    const nodeSet = new Set([centerNode.id]);
    const links = [];
    
    function addEdges(nodeId) {
        const up = AppState.incomingEdges[nodeId] || [];
        const down = AppState.outgoingEdges[nodeId] || [];
        return [...up, ...down];
    }
    
    addEdges(centerNode.id).forEach(e => {
        nodeSet.add(e.source_id); nodeSet.add(e.target_id);
        links.push({ source: e.source_id, target: e.target_id });
    });
    
    const graphNodes = Array.from(nodeSet).map(id => {
        const n = AppState.nodeMap[id];
        return { id, name: n?.name || id, isCenter: id === centerNode.id };
    });
    
    const svg = d3.select("#mesh-container").append("svg").attr("width", width).attr("height", height).attr("viewBox", [0, 0, width, height]);
    const g = svg.append("g");
    svg.call(d3.zoom().scaleExtent([0.2, 4]).on("zoom", (event) => g.attr("transform", event.transform)));

    const simulation = d3.forceSimulation(graphNodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(80))
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(30));

    const link = g.append("g").selectAll("line").data(links).join("line").attr("stroke", "#555").attr("stroke-opacity", 0.6).attr("stroke-width", 2);
    const node = g.append("g").selectAll("g").data(graphNodes).join("g")
        .call(d3.drag().on("start", (e) => { if (!e.active) simulation.alphaTarget(0.3).restart(); e.subject.fx = e.subject.x; e.subject.fy = e.subject.y; })
        .on("drag", (e) => { e.subject.fx = e.x; e.subject.fy = e.y; })
        .on("end", (e) => { if (!e.active) simulation.alphaTarget(0); e.subject.fx = null; e.subject.fy = null; }))
        .on("click", (e, d) => { closeMeshModal(); jumpToNode(d.id); });

    node.append("circle").attr("r", d => d.isCenter ? 12 : 8).attr("fill", d => d.isCenter ? "#fff" : "#3b82f6").attr("stroke", "#fff").attr("stroke-width", 1);
    node.append("text").text(d => d.name).attr("x", 12).attr("y", 4).style("font-size", "10px").style("fill", "#ccc");

    simulation.on("tick", () => {
        link.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
        node.attr("transform", d => `translate(${d.x},${d.y})`);
    });
}

// --- SEARCH & MAIN ---
function handleSearch(query) {
    const resultsDiv = document.getElementById('searchResults');
    if (query.length < 2) { resultsDiv.style.display = 'none'; return; }
    const queryLower = query.toLowerCase();
    const matches = Object.values(AppState.nodeMap).filter(n => n.name.toLowerCase().includes(queryLower) || n.id.toLowerCase().includes(queryLower)).slice(0, 12);
    
    if (matches.length > 0) {
        resultsDiv.innerHTML = matches.map(n => `
            <div class="search-item" onclick="jumpToNode('${n.id}')">
                <span class="search-item-icon">${getNodeIcon(n.type)}</span>
                <div class="search-item-content"><div class="search-item-name">${highlightMatch(n.name, query)}</div></div>
            </div>`).join('');
        resultsDiv.style.display = 'block';
    } else {
        resultsDiv.innerHTML = '<div class="search-item">No results found</div>'; resultsDiv.style.display = 'block';
    }
}

function highlightMatch(text, query) {
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return text;
    return text.slice(0, idx) + '<strong>' + text.slice(idx, idx + query.length) + '</strong>' + text.slice(idx + query.length);
}

function jumpToNode(nodeId) {
    document.getElementById('searchResults').style.display = 'none';
    document.querySelector('.search-input').value = '';
    const node = AppState.nodeMap[nodeId];
    if (!node) return;
    const domain = getDomainForNode(node);
    renderRootColumn();
    setTimeout(() => {
        const items = document.querySelectorAll('.column:first-child .item');
        for (let item of items) { if (item.textContent.includes(domain)) { item.click(); break; } }
        setTimeout(() => { AppState.selectNode(node); updateInspector(node); }, 100);
    }, 50);
}

window.onload = function() {
    if (typeof rawData !== 'undefined') {
        indexGraphData(rawData);
        computeBlastRadius();
        renderRootColumn();
        updateStats();
    }
    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); document.querySelector('.search-input').focus(); }
        if (e.key === 'Escape') { document.getElementById('searchResults').style.display = 'none'; closeMeshModal(); }
    });
};

function updateStats() {
    document.getElementById('stat-nodes').textContent = Object.keys(AppState.nodeMap).length;
    document.getElementById('stat-edges').textContent = (rawData.edges || []).length;
    const highRisk = Object.values(AppState.blastRadiusCache).filter(br => br > 5).length;
    document.getElementById('stat-risk').textContent = highRisk;
}

window.setMode = (mode) => {
    AppState.setMode(mode);
    document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.mode === mode));
    renderRootColumn();
};
"""

# =============================================================================
# HTML TEMPLATE
# =============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jnkn Impact Cockpit</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        /* INJECT: STYLES */
        {styles}
    </style>
</head>
<body>
    <header class="header">
        <div class="brand"><div class="brand-logo">J</div><span>Jnkn Impact Cockpit</span></div>
        <div class="stats-bar">
            <div class="stat"><span>Nodes:</span><span class="stat-value" id="stat-nodes">0</span></div>
            <div class="stat"><span>Edges:</span><span class="stat-value" id="stat-edges">0</span></div>
            <div class="stat stat-critical"><span>High Risk:</span><span class="stat-value" id="stat-risk">0</span></div>
        </div>
        <div class="mode-toggle">
            <button class="mode-btn active" data-mode="downstream" onclick="setMode('downstream')">↓ Impact</button>
            <button class="mode-btn" data-mode="upstream" onclick="setMode('upstream')">↑ Depends</button>
        </div>
        <div class="search-container">
            <span class="search-icon">⌕</span>
            <input type="text" class="search-input" placeholder="Search artifacts... (⌘K)" onkeyup="handleSearch(this.value)" onfocus="this.select()">
            <div class="search-results" id="searchResults"></div>
        </div>
    </header>
    
    <main class="main-container">
        <div class="columns-wrapper" id="columnsWrapper"></div>
        <aside class="inspector" id="inspector">
            <div class="inspector-header">
                <div class="inspector-icon" id="insp-icon">📄</div>
                <div class="inspector-title" id="insp-title">Select an artifact</div>
                <div class="inspector-id" id="insp-id"></div>
                <div class="action-bar">
                    <button class="btn btn-primary" id="btn-editor" onclick="openEditor()" disabled><span>📝</span> Open in Editor</button>
                    <button class="btn" onclick="openMeshModal()"><span>🕸️</span> Neighborhood</button>
                </div>
            </div>
            <div class="tabs">
                <div class="tab active" data-tab="evidence" onclick="switchTab('evidence')">Evidence</div>
                <div class="tab" data-tab="details" onclick="switchTab('details')">Details</div>
                <div class="tab" data-tab="upstream" onclick="switchTab('upstream')">Upstream <span class="tab-count" id="tab-up-count">0</span></div>
                <div class="tab" data-tab="downstream" onclick="switchTab('downstream')">Downstream <span class="tab-count" id="tab-down-count">0</span></div>
            </div>
            <div id="view-evidence" class="tab-content active"></div>
            <div id="view-details" class="tab-content"></div>
            <div id="view-upstream" class="tab-content"></div>
            <div id="view-downstream" class="tab-content"></div>
        </aside>
    </main>

    <div class="modal-overlay" id="meshModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">🕸️ Neighborhood Graph</h3>
                <button class="btn" style="width: auto;" onclick="closeMeshModal()">✕ Close</button>
            </div>
            <div id="mesh-container"></div>
        </div>
    </div>

    <script>
        const rawData = {data};
        
        /* INJECT: SCRIPTS */
        {scripts}
    </script>
</body>
</html>
"""


def build_html(graph_json: str) -> str:
    """
    Assemble the final HTML using embedded assets.
    """
    return HTML_TEMPLATE.format(
        styles=CSS_CONTENT,
        data=graph_json,
        scripts=JS_CONTENT
    )