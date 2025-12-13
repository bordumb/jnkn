# FILE: src/jnkn/graph/visualize.py
"""
Visualization Engine v3.1 (Stable)

A professional-grade Miller Columns interface for exploring dependency graphs.

Key Features:
- Bi-directional Traversal: Switch between Impact (Downstream) and Dependency (Upstream).
- Diff Visualization: Highlights added, removed, and modified artifacts.
- Rich Inspector: Confidence scores, line numbers, and file paths.
- Global Search: Rapid access to specific nodes.
"""

import json
import webbrowser
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..core.interfaces import IGraph

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jnkn Impact Browser</title>
    <style>
        /* ============================================================
           DESIGN SYSTEM
           ============================================================ */
        :root {
            /* Core palette */
            --bg-base: #0a0a0a;
            --bg-elevated: #111111;
            --bg-surface: #171717;
            --bg-hover: #1f1f1f;
            --bg-active: #262626;
            
            /* Borders */
            --border-subtle: #262626;
            --border-default: #333333;
            --border-focus: #525252;
            
            /* Text */
            --text-primary: #fafafa;
            --text-secondary: #a1a1aa;
            --text-tertiary: #71717a;
            
            /* Semantic colors */
            --color-danger: #ef4444;
            --color-danger-bg: rgba(239, 68, 68, 0.1);
            --color-warning: #f59e0b;
            --color-warning-bg: rgba(245, 158, 11, 0.1);
            --color-success: #22c55e;
            --color-success-bg: rgba(34, 197, 94, 0.1);
            --color-info: #3b82f6;
            --color-info-bg: rgba(59, 130, 246, 0.1);
            
            /* Diff colors */
            --diff-added: rgba(34, 197, 94, 0.1);
            --diff-removed: rgba(239, 68, 68, 0.1);
            --diff-modified: rgba(245, 158, 11, 0.1);
            
            /* Accent */
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            
            /* Domain colors */
            --domain-infra: #f59e0b;
            --domain-config: #22c55e;
            --domain-code: #3b82f6;
            --domain-data: #a855f7;
            
            /* Typography */
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", Roboto, sans-serif;
            --font-mono: "SF Mono", "Fira Code", monospace;
        }

        * { box-sizing: border-box; }
        
        body {
            margin: 0;
            padding: 0;
            height: 100vh;
            background: var(--bg-base);
            color: var(--text-primary);
            font-family: var(--font-sans);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* ============================================================
           HEADER
           ============================================================ */
        .header {
            height: 56px;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            padding: 0 16px;
            background: var(--bg-elevated);
            gap: 16px;
        }
        
        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 700;
            font-size: 16px;
        }
        
        .brand-logo {
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%);
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }

        /* Mode Toggle */
        .mode-toggle {
            display: flex;
            background: var(--bg-surface);
            border-radius: 6px;
            padding: 2px;
            border: 1px solid var(--border-default);
        }
        
        .mode-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.2s;
        }
        
        .mode-btn.active {
            background: var(--bg-active);
            color: var(--text-primary);
            box-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }

        /* Search Bar */
        .search-container {
            flex: 1;
            max-width: 400px;
            position: relative;
        }
        
        .search-input {
            width: 100%;
            background: var(--bg-base);
            border: 1px solid var(--border-default);
            padding: 6px 12px 6px 32px;
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 13px;
        }
        
        .search-input:focus {
            border-color: var(--accent);
            outline: none;
        }
        
        .search-icon {
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-tertiary);
            font-size: 12px;
        }

        /* ============================================================
           MILLER COLUMNS
           ============================================================ */
        .main-container {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        
        .columns-wrapper {
            flex: 1;
            display: flex;
            overflow-x: auto;
            scroll-behavior: smooth;
        }
        
        .column {
            width: 320px;
            min-width: 320px;
            border-right: 1px solid var(--border-subtle);
            background: var(--bg-elevated);
            display: flex;
            flex-direction: column;
        }
        
        .column:nth-child(odd) { background: var(--bg-base); }
        
        .column-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-subtle);
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--text-tertiary);
            display: flex;
            justify-content: space-between;
        }
        
        .column-list {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }

        /* ============================================================
           ITEMS
           ============================================================ */
        .item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            margin-bottom: 2px;
            border-radius: 6px;
            cursor: pointer;
            border: 1px solid transparent;
            font-size: 13px;
        }
        
        .item:hover { background: var(--bg-hover); }
        .item.active { background: var(--bg-active); border-color: var(--border-default); }
        
        /* Diff States */
        .item.diff-added { background: var(--diff-added); border-left: 3px solid var(--color-success); }
        .item.diff-removed { background: var(--diff-removed); border-left: 3px solid var(--color-danger); opacity: 0.7; }
        .item.diff-modified { background: var(--diff-modified); border-left: 3px solid var(--color-warning); }
        
        .item-icon { margin-right: 10px; font-size: 16px; }
        .item-content { flex: 1; min-width: 0; }
        .item-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .item-meta { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
        
        .badge {
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 6px;
            text-transform: uppercase;
            font-weight: 600;
        }
        
        .badge.runtime { background: rgba(139, 92, 246, 0.2); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }
        .badge.static { background: rgba(113, 113, 122, 0.2); color: #a1a1aa; }
        .badge.low-conf { background: var(--color-warning-bg); color: var(--color-warning); }

        /* ============================================================
           INSPECTOR
           ============================================================ */
        .inspector {
            width: 400px;
            min-width: 400px;
            background: var(--bg-elevated);
            border-left: 1px solid var(--border-subtle);
            padding: 0;
            overflow-y: auto;
            display: none;
            flex-direction: column;
        }
        
        .inspector-header {
            padding: 20px 20px 10px 20px;
            border-bottom: 1px solid var(--border-subtle);
        }

        .inspector-body {
            padding: 20px;
            flex: 1;
        }
        
        .inspector-title { font-size: 18px; font-weight: 600; margin-bottom: 5px; word-break: break-all; }
        .inspector-subtitle { font-size: 12px; color: var(--text-tertiary); font-family: var(--font-mono); }
        
        .section { margin-bottom: 24px; }
        .section-header { 
            font-size: 11px; font-weight: 600; text-transform: uppercase; 
            color: var(--text-tertiary); margin-bottom: 12px; letter-spacing: 0.5px;
        }
        
        .prop-row { display: flex; margin-bottom: 8px; font-size: 13px; }
        .prop-label { width: 100px; color: var(--text-tertiary); flex-shrink: 0; }
        .prop-value { flex: 1; color: var(--text-secondary); word-break: break-all; }
        
        /* Confidence Meter */
        .confidence-meter {
            background: var(--bg-surface);
            border: 1px solid var(--border-default);
            border-radius: 6px;
            padding: 12px;
        }
        
        .confidence-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 12px;
        }
        
        .confidence-bar-bg {
            height: 6px;
            background: var(--bg-active);
            border-radius: 3px;
            overflow: hidden;
        }
        
        .confidence-bar-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        
        /* Actions */
        .btn-action {
            width: 100%;
            padding: 10px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .btn-action:hover { background: var(--accent-hover); }
        
        /* Risk Card */
        .risk-card {
            padding: 12px;
            border-radius: 6px;
            border: 1px solid transparent;
            font-size: 13px;
            margin-bottom: 16px;
        }
        .risk-card.critical {
            background: var(--color-danger-bg);
            border-color: rgba(239, 68, 68, 0.3);
            color: #fca5a5;
        }

        /* Search Results Dropdown */
        .search-results {
            position: absolute;
            top: 100%;
            left: 0;
            width: 100%;
            background: var(--bg-elevated);
            border: 1px solid var(--border-default);
            border-radius: 6px;
            margin-top: 4px;
            max-height: 300px;
            overflow-y: auto;
            display: none;
            z-index: 1000;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        }
        
        .search-item {
            padding: 8px 12px;
            cursor: pointer;
            font-size: 13px;
            border-bottom: 1px solid var(--border-subtle);
        }
        
        .search-item:hover { background: var(--bg-hover); }
        .search-item small { color: var(--text-tertiary); display: block; font-size: 11px; }

    </style>
</head>
<body>
    <header class="header">
        <div class="brand">
            <div class="brand-logo">J</div>
            <span>Jnkn</span>
        </div>
        
        <div class="mode-toggle">
            <button class="mode-btn active" onclick="setMode('downstream')">
                Impact (Downstream)
            </button>
            <button class="mode-btn" onclick="setMode('upstream')">
                Dependency (Upstream)
            </button>
        </div>
        
        <div class="search-container">
            <span class="search-icon">🔍</span>
            <input type="text" class="search-input" placeholder="Search resources, tables, files..." onkeyup="handleSearch(this.value)">
            <div class="search-results" id="searchResults"></div>
        </div>
    </header>
    
    <main class="main-container">
        <div class="columns-wrapper" id="columnsWrapper"></div>
        <aside class="inspector" id="inspector">
            </aside>
    </main>

    <script>
        // DATA
        const rawData = __GRAPH_DATA__;
        
        // STATE
        let state = {
            mode: 'downstream', // 'downstream' or 'upstream'
            nodeMap: {},
            outgoingEdges: {}, // Source -> [Edges]
            incomingEdges: {}, // Target -> [Edges]
            selectedPath: []   // Array of Node IDs
        };

        // INITIALIZATION
        window.onload = function() {
            indexData(rawData);
            renderRootColumn();
        };

        function indexData(data) {
            data.nodes.forEach(n => state.nodeMap[n.id] = n);
            
            if (data.edges) {
                data.edges.forEach(e => {
                    if (!state.outgoingEdges[e.source_id]) state.outgoingEdges[e.source_id] = [];
                    state.outgoingEdges[e.source_id].push(e);
                    
                    if (!state.incomingEdges[e.target_id]) state.incomingEdges[e.target_id] = [];
                    state.incomingEdges[e.target_id].push(e);
                });
            }
        }

        // ============================================================
        // LOGIC & NAVIGATION
        // ============================================================
        window.setMode = function(mode) {
            state.mode = mode;
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.classList.toggle('active', btn.innerText.toLowerCase().includes(mode));
            });
            
            // Reset view when mode changes to avoid confusion
            renderRootColumn();
        };

        window.handleSearch = function(query) {
            const resultsDiv = document.getElementById('searchResults');
            if (query.length < 2) {
                resultsDiv.style.display = 'none';
                return;
            }
            
            const matches = rawData.nodes.filter(n => 
                n.name.toLowerCase().includes(query.toLowerCase()) || 
                n.id.toLowerCase().includes(query.toLowerCase())
            ).slice(0, 10);
            
            if (matches.length > 0) {
                resultsDiv.innerHTML = matches.map(n => `
                    <div class="search-item" onclick="jumpToNode('${n.id}')">
                        <div>${n.name}</div>
                        <small>${n.id}</small>
                    </div>
                `).join('');
                resultsDiv.style.display = 'block';
            } else {
                resultsDiv.style.display = 'none';
            }
        };

        window.jumpToNode = function(nodeId) {
            document.getElementById('searchResults').style.display = 'none';
            document.querySelector('.search-input').value = '';
            
            const node = state.nodeMap[nodeId];
            if (node) {
                // Reset columns and show just this node info
                renderRootColumn(); 
                showInspector(node);
                // In a future version, we could "pathfind" from root to this node
            }
        };

        function removeColumnsAfter(index) {
            const wrapper = document.getElementById('columnsWrapper');
            while (wrapper.children.length > index + 1) {
                wrapper.removeChild(wrapper.lastChild);
            }
        }

        // ============================================================
        // COLUMN RENDERING
        // ============================================================
        function renderRootColumn() {
            const wrapper = document.getElementById('columnsWrapper');
            wrapper.innerHTML = ''; // Clear all
            
            // Group nodes by type
            const groups = {
                'Infrastructure': [],
                'Configuration': [],
                'Code': [],
                'Data': []
            };
            
            rawData.nodes.forEach(n => {
                const type = n.type || '';
                if (type.includes('infra')) groups['Infrastructure'].push(n);
                else if (type.includes('env') || type.includes('config')) groups['Configuration'].push(n);
                else if (type.includes('data')) groups['Data'].push(n);
                else groups['Code'].push(n);
            });
            
            const col = createColumn('Domains', rawData.nodes.length);
            
            Object.keys(groups).forEach(key => {
                if (groups[key].length === 0) return;
                
                const item = document.createElement('div');
                item.className = 'item';
                item.innerHTML = `
                    <span class="item-icon">${getIconForCategory(key)}</span>
                    <div class="item-content">
                        <div class="item-title">${key}</div>
                        <div class="item-meta">${groups[key].length} items</div>
                    </div>
                    <span>›</span>
                `;
                
                // Root items are always at index 0
                item.onclick = () => {
                    highlightItem(item);
                    renderNodeList(groups[key], key, 0); 
                };
                col.querySelector('.column-list').appendChild(item);
            });
            wrapper.appendChild(col);
            
            // Hide inspector on reset
            document.getElementById('inspector').style.display = 'none';
        }

        function renderNodeList(nodes, title, parentColIndex) {
            // Remove columns that came after the parent of this new list
            removeColumnsAfter(parentColIndex);
            
            const col = createColumn(title, nodes.length);
            const myColIndex = parentColIndex + 1;
            
            nodes.sort((a, b) => a.name.localeCompare(b.name));
            
            nodes.forEach(node => {
                const item = createNodeItem(node);
                item.onclick = () => {
                    highlightItem(item);
                    showInspector(node);
                    renderConnections(node, myColIndex);
                };
                col.querySelector('.column-list').appendChild(item);
            });
            
            document.getElementById('columnsWrapper').appendChild(col);
            col.scrollIntoView({behavior: 'smooth'});
        }

        function renderConnections(node, parentColIndex) {
            removeColumnsAfter(parentColIndex);
            
            let connections = [];
            let title = "";
            
            if (state.mode === 'downstream') {
                // Outgoing: What does this node affect?
                const edges = state.outgoingEdges[node.id] || [];
                connections = edges.map(e => ({ node: state.nodeMap[e.target_id], edge: e }));
                title = `Impacts (${connections.length})`;
            } else {
                // Incoming: What does this node depend on?
                const edges = state.incomingEdges[node.id] || [];
                connections = edges.map(e => ({ node: state.nodeMap[e.source_id], edge: e }));
                title = `Depends On (${connections.length})`;
            }
            
            if (connections.length === 0) return;
            
            const col = createColumn(title, connections.length);
            const myColIndex = parentColIndex + 1;
            
            connections.sort((a, b) => (b.edge.confidence || 0) - (a.edge.confidence || 0));
            
            connections.forEach(({node, edge}) => {
                if (!node) return;
                const item = createNodeItem(node, edge);
                
                item.onclick = () => {
                    highlightItem(item);
                    showInspector(node, edge);
                    renderConnections(node, myColIndex);
                };
                
                col.querySelector('.column-list').appendChild(item);
            });
            
            document.getElementById('columnsWrapper').appendChild(col);
            col.scrollIntoView({behavior: 'smooth'});
        }

        // ============================================================
        // DOM HELPERS
        // ============================================================
        function createColumn(title, count) {
            const div = document.createElement('div');
            div.className = 'column';
            div.innerHTML = `
                <div class="column-header">
                    <span>${title}</span>
                    ${count !== undefined ? `<span style="opacity:0.6">${count}</span>` : ''}
                </div>
                <div class="column-list"></div>
            `;
            return div;
        }

        function createNodeItem(node, edge) {
            const div = document.createElement('div');
            
            let classes = 'item';
            if (node.metadata?.change_type === 'added') classes += ' diff-added';
            if (node.metadata?.change_type === 'removed') classes += ' diff-removed';
            if (node.metadata?.change_type === 'modified') classes += ' diff-modified';
            
            div.className = classes;
            
            // Badges
            let badge = '';
            if (edge && edge.metadata?.source === 'openlineage') {
                badge = `<span class="badge runtime">Runtime</span>`;
            } else if (edge) {
                const conf = edge.confidence || 1.0;
                if (conf < 0.5) badge = `<span class="badge low-conf">Low Conf</span>`;
            }

            const icon = getNodeIcon(node.type);
            div.innerHTML = `
                <span class="item-icon">${icon}</span>
                <div class="item-content">
                    <div class="item-title">${node.name}</div>
                    <div class="item-meta">${node.type}</div>
                </div>
                ${badge}
                <span style="color:var(--text-tertiary)">›</span>
            `;
            return div;
        }

        function highlightItem(item) {
            // Find parent list, remove active from siblings
            const parentList = item.parentElement;
            Array.from(parentList.children).forEach(child => child.classList.remove('active'));
            item.classList.add('active');
        }

        // ============================================================
        // INSPECTOR & DETAILS
        // ============================================================
        function showInspector(node, edge = null) {
            const inspector = document.getElementById('inspector');
            const filePath = node.path || node.metadata?.file || 'N/A';
            const line = node.metadata?.line || node.line || 1;
            
            // Confidence calculation
            const confidence = edge ? (edge.confidence || 1.0) : 1.0;
            const confPercent = Math.round(confidence * 100);
            
            let confColor = 'var(--color-success)';
            if (confidence < 0.8) confColor = 'var(--color-warning)';
            if (confidence < 0.5) confColor = 'var(--color-danger)';

            let html = `
                <div class="inspector-header">
                    <div class="inspector-title">${node.name}</div>
                    <div class="inspector-subtitle">${node.id}</div>
                </div>
                
                <div class="inspector-body">
            `;

            // Risk Assessment
            if (confidence < 0.5) {
                html += `
                    <div class="risk-card critical">
                        <strong>⚠️ Low Confidence Match</strong><br>
                        This dependency was inferred with only ${confPercent}% confidence.
                        Verify it before relying on it.
                    </div>
                `;
            }

            // Confidence Meter (Only if showing an edge connection)
            if (edge) {
                html += `
                    <div class="section">
                        <div class="section-header">Connection Strength</div>
                        <div class="confidence-meter">
                            <div class="confidence-header">
                                <span>Confidence</span>
                                <span style="color:${confColor}; font-weight:bold;">${confPercent}%</span>
                            </div>
                            <div class="confidence-bar-bg">
                                <div class="confidence-bar-fill" style="width: ${confPercent}%; background: ${confColor}"></div>
                            </div>
                            <div style="font-size:11px; color:var(--text-tertiary); margin-top:6px;">
                                ${edge.metadata?.explanation || 'Matched via static token analysis.'}
                            </div>
                        </div>
                    </div>
                `;
            }

            // Metadata
            html += `
                <div class="section">
                    <div class="section-header">Properties</div>
                    <div class="prop-row">
                        <span class="prop-label">Type</span>
                        <span class="prop-value">${node.type}</span>
                    </div>
                    <div class="prop-row">
                        <span class="prop-label">File</span>
                        <span class="prop-value">${filePath}</span>
                    </div>
                    <div class="prop-row">
                        <span class="prop-label">Line</span>
                        <span class="prop-value">${line}</span>
                    </div>
                </div>
            `;

            // Actions
            if (node.path) {
                html += `
                    <button class="btn-action" onclick="openVsCode('${node.path}', ${line})">
                        <span>📝</span> Open in Editor
                    </button>
                `;
            }

            html += `</div>`; // Close body
            
            inspector.innerHTML = html;
            inspector.style.display = 'flex';
        }

        function openVsCode(path, line) {
            const cleanPath = path.startsWith('/') ? path.substring(1) : path;
            window.location.href = `vscode://file/${cleanPath}:${line}`;
        }

        // ============================================================
        // UTILS
        // ============================================================
        function getIconForCategory(cat) {
            const map = {'Infrastructure': '☁️', 'Configuration': '🔧', 'Code': '💻', 'Data': '📊'};
            return map[cat] || '📦';
        }
        
        function getNodeIcon(type) {
            if (type.includes('infra')) return '☁️';
            if (type.includes('env')) return '🔧';
            if (type.includes('data')) return '📊';
            return '📄';
        }
    </script>
</body>
</html>
"""


def _json_default(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def generate_html(graph: IGraph) -> str:
    """
    Generate the HTML content for the graph visualization.
    """
    if hasattr(graph, "to_dict"):
        graph_data = graph.to_dict()
    else:
        graph_data = {
            "nodes": [n.model_dump() for n in graph.iter_nodes()],
            "edges": [e.model_dump() for e in graph.iter_edges()],
        }

    json_data = json.dumps(graph_data, default=_json_default)
    return HTML_TEMPLATE.replace("__GRAPH_DATA__", json_data)


def open_visualization(graph: IGraph, output_path: str = "graph.html") -> str:
    """
    Generate and open the visualization in the browser.
    """
    html_content = generate_html(graph)
    out_file = Path(output_path)
    out_file.write_text(html_content, encoding="utf-8")

    abs_path = out_file.resolve().as_uri()
    webbrowser.open(abs_path)

    return str(out_file)
