"""
Visualization Engine v2.0

A redesigned Miller Columns interface with:
- Risk-first design: Broken/risky items surface immediately
- Hover lineage: Visual path tracing without clicking
- Contextual badges: Inline risk indicators
- Enhanced inspector: Micro-charts and actionable insights
- Guided actions: Clear next steps for remediation

Design Philosophy: "Show the story, not just the data"
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
           DESIGN SYSTEM - Enterprise Ready (Vercel/Linear inspired)
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
            --text-inverted: #09090b;
            
            /* Semantic colors */
            --color-danger: #ef4444;
            --color-danger-bg: rgba(239, 68, 68, 0.1);
            --color-danger-border: rgba(239, 68, 68, 0.3);
            
            --color-warning: #f59e0b;
            --color-warning-bg: rgba(245, 158, 11, 0.1);
            --color-warning-border: rgba(245, 158, 11, 0.3);
            
            --color-success: #22c55e;
            --color-success-bg: rgba(34, 197, 94, 0.1);
            --color-success-border: rgba(34, 197, 94, 0.3);
            
            --color-info: #3b82f6;
            --color-info-bg: rgba(59, 130, 246, 0.1);
            --color-info-border: rgba(59, 130, 246, 0.3);
            
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
            --font-mono: "SF Mono", "Fira Code", "Consolas", monospace;
            
            /* Spacing */
            --radius-sm: 4px;
            --radius-md: 6px;
            --radius-lg: 8px;
            
            /* Transitions */
            --transition-fast: 150ms ease;
            --transition-normal: 200ms ease;
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
            -webkit-font-smoothing: antialiased;
        }

        /* ============================================================
           HEADER - Status Bar with Summary Metrics
           ============================================================ */
        .header {
            height: 52px;
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
            font-weight: 600;
            font-size: 14px;
            color: var(--text-primary);
        }
        
        .brand-logo {
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%);
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
        }
        
        .divider {
            width: 1px;
            height: 24px;
            background: var(--border-default);
        }
        
        /* Summary Chips - Key insights at a glance */
        .summary-chips {
            display: flex;
            gap: 8px;
            flex: 1;
        }
        
        .chip {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 100px;
            font-size: 12px;
            font-weight: 500;
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            color: var(--text-secondary);
        }
        
        .chip.danger {
            background: var(--color-danger-bg);
            border-color: var(--color-danger-border);
            color: var(--color-danger);
        }
        
        .chip.warning {
            background: var(--color-warning-bg);
            border-color: var(--color-warning-border);
            color: var(--color-warning);
        }
        
        .chip.success {
            background: var(--color-success-bg);
            border-color: var(--color-success-border);
            color: var(--color-success);
        }
        
        .chip-icon { font-size: 14px; }
        
        .keyboard-hint {
            font-size: 11px;
            color: var(--text-tertiary);
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        kbd {
            background: var(--bg-surface);
            border: 1px solid var(--border-default);
            border-radius: 3px;
            padding: 2px 5px;
            font-family: var(--font-mono);
            font-size: 10px;
        }

        /* ============================================================
           MAIN CONTAINER - Miller Columns + Inspector
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
            overflow-y: hidden;
            scroll-behavior: smooth;
        }
        
        /* Hide scrollbar but keep functionality */
        .columns-wrapper::-webkit-scrollbar { height: 0; }

        /* ============================================================
           COLUMN - Individual Miller Column
           ============================================================ */
        .column {
            width: 320px;
            min-width: 320px;
            border-right: 1px solid var(--border-subtle);
            background: var(--bg-elevated);
            display: flex;
            flex-direction: column;
            height: 100%;
            position: relative;
        }
        
        .column:nth-child(odd) { background: var(--bg-base); }
        
        .column-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: inherit;
            position: sticky;
            top: 0;
            z-index: 2;
        }
        
        .column-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-tertiary);
        }
        
        .column-count {
            font-size: 11px;
            color: var(--text-tertiary);
            background: var(--bg-surface);
            padding: 2px 8px;
            border-radius: 100px;
        }
        
        .column-list {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }
        
        .column-list::-webkit-scrollbar { width: 6px; }
        .column-list::-webkit-scrollbar-track { background: transparent; }
        .column-list::-webkit-scrollbar-thumb { 
            background: var(--border-default); 
            border-radius: 3px; 
        }

        /* ============================================================
           ITEM - List Item with Risk Indicators
           ============================================================ */
        .item {
            display: flex;
            align-items: flex-start;
            padding: 10px 12px;
            margin-bottom: 2px;
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: all var(--transition-fast);
            border: 1px solid transparent;
            position: relative;
        }
        
        .item:hover {
            background: var(--bg-hover);
            border-color: var(--border-subtle);
        }
        
        .item.active {
            background: var(--bg-active);
            border-color: var(--border-default);
        }
        
        /* Hover lineage highlighting */
        .item.lineage-highlight {
            background: var(--color-info-bg);
            border-color: var(--color-info-border);
        }
        
        .item.lineage-source {
            border-color: var(--accent);
            box-shadow: 0 0 0 1px var(--accent);
        }
        
        /* Risk-based left border indicator */
        .item[data-risk="critical"] {
            border-left: 3px solid var(--color-danger);
        }
        
        .item[data-risk="warning"] {
            border-left: 3px solid var(--color-warning);
        }
        
        .item[data-risk="healthy"] {
            border-left: 3px solid var(--color-success);
        }
        
        /* Item icon with domain color */
        .item-icon {
            width: 32px;
            height: 32px;
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            margin-right: 12px;
            flex-shrink: 0;
        }
        
        .item-icon.infra { background: rgba(245, 158, 11, 0.15); }
        .item-icon.config { background: rgba(34, 197, 94, 0.15); }
        .item-icon.code { background: rgba(59, 130, 246, 0.15); }
        .item-icon.data { background: rgba(168, 85, 247, 0.15); }
        
        .item-content {
            flex: 1;
            min-width: 0;
        }
        
        .item-main {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 2px;
        }
        
        .item-label {
            font-size: 13px;
            font-weight: 500;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* Inline badges for quick scanning */
        .badge {
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            padding: 2px 6px;
            border-radius: 3px;
            white-space: nowrap;
        }
        
        .badge.critical {
            background: var(--color-danger);
            color: white;
        }
        
        .badge.breaking {
            background: var(--color-danger);
            color: white;
        }
        
        .badge.unused {
            background: var(--color-warning-bg);
            color: var(--color-warning);
            border: 1px solid var(--color-warning-border);
        }
        
        .badge.new {
            background: var(--color-info-bg);
            color: var(--color-info);
            border: 1px solid var(--color-info-border);
        }
        
        .item-meta {
            font-size: 11px;
            color: var(--text-tertiary);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .meta-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        /* Confidence dot indicator */
        .confidence-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }
        
        .confidence-dot.high { background: var(--color-success); }
        .confidence-dot.medium { background: var(--color-warning); }
        .confidence-dot.low { background: var(--color-danger); }
        
        .item-arrow {
            color: var(--text-tertiary);
            font-size: 10px;
            margin-left: 8px;
            opacity: 0;
            transition: opacity var(--transition-fast);
        }
        
        .item:hover .item-arrow,
        .item.active .item-arrow {
            opacity: 1;
        }

        /* ============================================================
           EMPTY STATE
           ============================================================ */
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px 20px;
            text-align: center;
            color: var(--text-tertiary);
        }
        
        .empty-state-icon {
            font-size: 32px;
            margin-bottom: 12px;
            opacity: 0.5;
        }
        
        .empty-state-text {
            font-size: 13px;
        }

        /* ============================================================
           INSPECTOR PANEL - The "Tell Me" Feature
           ============================================================ */
        .inspector {
            width: 380px;
            min-width: 380px;
            background: var(--bg-elevated);
            border-left: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .inspector-header {
            padding: 16px;
            border-bottom: 1px solid var(--border-subtle);
        }
        
        .inspector-type {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-tertiary);
            margin-bottom: 8px;
        }
        
        .type-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        
        .type-dot.infra { background: var(--domain-infra); }
        .type-dot.config { background: var(--domain-config); }
        .type-dot.code { background: var(--domain-code); }
        .type-dot.data { background: var(--domain-data); }
        
        .inspector-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            word-break: break-word;
            line-height: 1.4;
        }
        
        .inspector-body {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }
        
        /* Section styling */
        .section {
            margin-bottom: 20px;
        }
        
        .section-header {
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-tertiary);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        /* Risk Assessment Card */
        .risk-card {
            background: var(--bg-surface);
            border-radius: var(--radius-lg);
            padding: 14px;
            border: 1px solid var(--border-subtle);
        }
        
        .risk-card.critical {
            background: var(--color-danger-bg);
            border-color: var(--color-danger-border);
        }
        
        .risk-card.warning {
            background: var(--color-warning-bg);
            border-color: var(--color-warning-border);
        }
        
        .risk-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }
        
        .risk-icon {
            font-size: 18px;
        }
        
        .risk-title {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .risk-description {
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.5;
        }
        
        /* Confidence Meter */
        .confidence-section {
            background: var(--bg-surface);
            border-radius: var(--radius-lg);
            padding: 14px;
            border: 1px solid var(--border-subtle);
        }
        
        .confidence-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .confidence-label {
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .confidence-value {
            font-size: 14px;
            font-weight: 600;
            font-family: var(--font-mono);
        }
        
        .confidence-bar {
            height: 6px;
            background: var(--bg-active);
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 8px;
        }
        
        .confidence-fill {
            height: 100%;
            border-radius: 3px;
            transition: width var(--transition-normal);
        }
        
        .confidence-explanation {
            font-size: 11px;
            color: var(--text-tertiary);
            line-height: 1.4;
        }
        
        /* Mini Lineage Graph */
        .lineage-mini {
            background: var(--bg-surface);
            border-radius: var(--radius-lg);
            padding: 14px;
            border: 1px solid var(--border-subtle);
        }
        
        .lineage-flow {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        
        .lineage-node {
            flex: 1;
            text-align: center;
            padding: 8px;
            background: var(--bg-active);
            border-radius: var(--radius-sm);
            font-size: 10px;
            color: var(--text-secondary);
            border: 1px solid transparent;
        }
        
        .lineage-node.current {
            background: var(--color-info-bg);
            border-color: var(--color-info-border);
            color: var(--color-info);
        }
        
        .lineage-arrow {
            color: var(--text-tertiary);
            font-size: 12px;
        }
        
        /* Source Location */
        .location-card {
            background: var(--bg-surface);
            border-radius: var(--radius-lg);
            padding: 14px;
            border: 1px solid var(--border-subtle);
        }
        
        .location-path {
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--text-secondary);
            background: var(--bg-active);
            padding: 8px 10px;
            border-radius: var(--radius-sm);
            margin-bottom: 10px;
            word-break: break-all;
        }
        
        .location-meta {
            display: flex;
            gap: 16px;
            font-size: 12px;
            color: var(--text-tertiary);
        }
        
        /* Inspector Footer - Actions */
        .inspector-footer {
            padding: 16px;
            border-top: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 16px;
            border-radius: var(--radius-md);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all var(--transition-fast);
            text-decoration: none;
            border: none;
        }
        
        .btn-primary {
            background: var(--accent);
            color: white;
        }
        
        .btn-primary:hover {
            background: var(--accent-hover);
        }
        
        .btn-secondary {
            background: var(--bg-surface);
            color: var(--text-secondary);
            border: 1px solid var(--border-default);
        }
        
        .btn-secondary:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* ============================================================
           LINEAGE CONNECTOR - Visual Path Between Columns
           ============================================================ */
        .lineage-connector {
            position: absolute;
            pointer-events: none;
            z-index: 100;
        }
        
        .lineage-line {
            stroke: var(--accent);
            stroke-width: 2;
            fill: none;
            opacity: 0.6;
        }

        /* ============================================================
           KEYBOARD NAVIGATION FOCUS STATES
           ============================================================ */
        .item:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
        }
        
        /* ============================================================
           ANIMATIONS
           ============================================================ */
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .column {
            animation: slideIn 0.2s ease-out;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .badge.critical {
            animation: pulse 2s infinite;
        }

        /* ============================================================
           RESPONSIVE ADJUSTMENTS
           ============================================================ */
        @media (max-width: 1200px) {
            .column {
                width: 280px;
                min-width: 280px;
            }
            .inspector {
                width: 340px;
                min-width: 340px;
            }
        }
    </style>
</head>
<body>
    <!-- Header with summary metrics -->
    <header class="header">
        <div class="brand">
            <div class="brand-logo">J</div>
            <span>Jnkn Impact Browser</span>
        </div>
        
        <div class="divider"></div>
        
        <div class="summary-chips" id="summaryChips">
            <!-- Populated by JS -->
        </div>
        
        <div class="keyboard-hint">
            <kbd>↑↓</kbd> Navigate
            <kbd>→</kbd> Expand
            <kbd>Enter</kbd> Open
        </div>
    </header>
    
    <!-- Main content area -->
    <main class="main-container">
        <div class="columns-wrapper" id="columnsWrapper">
            <!-- Columns populated by JS -->
        </div>
        
        <aside class="inspector" id="inspector" style="display: none;">
            <!-- Inspector populated by JS -->
        </aside>
    </main>
    
    <!-- SVG container for lineage connectors -->
    <svg class="lineage-connector" id="lineageConnector" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1000;"></svg>

    <script>
        // ============================================================
        // DATA & STATE
        // ============================================================
        const rawData = __GRAPH_DATA__;
        
        let nodeMap = {};
        let edgeMap = {};      // source_id -> [edges]
        let reverseEdgeMap = {}; // target_id -> [edges]
        let selectedPath = [];   // Track selection path for lineage
        let hoveredItem = null;
        
        // DOM references
        const columnsWrapper = document.getElementById('columnsWrapper');
        const inspector = document.getElementById('inspector');
        const summaryChips = document.getElementById('summaryChips');
        const lineageConnector = document.getElementById('lineageConnector');

        // ============================================================
        // INITIALIZATION
        // ============================================================
        window.onload = function() {
            processData(rawData);
            setupKeyboardNavigation();
        };

        function processData(data) {
            // Build lookup maps
            nodeMap = {};
            edgeMap = {};
            reverseEdgeMap = {};

            data.nodes.forEach(n => { nodeMap[n.id] = n; });

            if (data.edges) {
                data.edges.forEach(e => {
                    if (!edgeMap[e.source_id]) edgeMap[e.source_id] = [];
                    edgeMap[e.source_id].push(e);
                    
                    if (!reverseEdgeMap[e.target_id]) reverseEdgeMap[e.target_id] = [];
                    reverseEdgeMap[e.target_id].push(e);
                });
            }

            // Calculate summary metrics
            const metrics = calculateMetrics(data);
            renderSummaryChips(metrics);
            
            // Render initial column
            renderRootColumn();
        }

        function calculateMetrics(data) {
            let criticalCount = 0;
            let warningCount = 0;
            let orphanCount = 0;
            
            data.nodes.forEach(n => {
                const outgoing = edgeMap[n.id] || [];
                const incoming = reverseEdgeMap[n.id] || [];
                
                // Check for broken/critical nodes
                if (n.metadata?.broken || n.metadata?.missing_target) {
                    criticalCount++;
                }
                
                // Check for low confidence connections
                outgoing.forEach(e => {
                    if (e.confidence && e.confidence < 0.5) warningCount++;
                });
                
                // Orphan nodes (no connections)
                if (outgoing.length === 0 && incoming.length === 0) {
                    orphanCount++;
                }
            });

            return {
                total: data.nodes.length,
                edges: data.edges.length,
                critical: criticalCount,
                warnings: warningCount,
                orphans: orphanCount
            };
        }

        function renderSummaryChips(metrics) {
            let html = '';
            
            if (metrics.critical > 0) {
                html += `<div class="chip danger">
                    <span class="chip-icon">⚠</span>
                    <span>${metrics.critical} Breaking</span>
                </div>`;
            }
            
            if (metrics.warnings > 0) {
                html += `<div class="chip warning">
                    <span class="chip-icon">⚡</span>
                    <span>${metrics.warnings} Low Confidence</span>
                </div>`;
            }
            
            html += `<div class="chip">
                <span class="chip-icon">📦</span>
                <span>${metrics.total} Artifacts</span>
            </div>`;
            
            html += `<div class="chip">
                <span class="chip-icon">🔗</span>
                <span>${metrics.edges} Dependencies</span>
            </div>`;
            
            if (metrics.orphans > 0) {
                html += `<div class="chip">
                    <span class="chip-icon">👻</span>
                    <span>${metrics.orphans} Orphaned</span>
                </div>`;
            }
            
            summaryChips.innerHTML = html;
        }

        // ============================================================
        // COLUMN RENDERING
        // ============================================================
        function renderRootColumn() {
            columnsWrapper.innerHTML = '';
            selectedPath = [];
            hideInspector();
            
            // Categorize nodes by domain
            const categories = [
                { 
                    id: 'cat:infra', 
                    name: 'Infrastructure', 
                    type: 'infra', 
                    icon: '☁️', 
                    desc: 'Terraform, Cloud Resources',
                    color: 'infra',
                    nodes: [] 
                },
                { 
                    id: 'cat:config', 
                    name: 'Configuration', 
                    type: 'config', 
                    icon: '🔧', 
                    desc: 'Environment Variables, Secrets',
                    color: 'config',
                    nodes: [] 
                },
                { 
                    id: 'cat:code', 
                    name: 'Application Code', 
                    type: 'code', 
                    icon: '💻', 
                    desc: 'Python, JavaScript, Go',
                    color: 'code',
                    nodes: [] 
                },
                { 
                    id: 'cat:data', 
                    name: 'Data Assets', 
                    type: 'data', 
                    icon: '📊', 
                    desc: 'Tables, Topics, Pipelines',
                    color: 'data',
                    nodes: [] 
                }
            ];

            // Classify nodes
            rawData.nodes.forEach(n => {
                const t = (n.type || "").toLowerCase();
                const id = n.id.toLowerCase();
                
                if (t.includes('infra') || t.includes('terraform') || id.startsWith('infra:')) {
                    categories[0].nodes.push(n);
                } else if (t.includes('env') || t.includes('config') || id.startsWith('env:') || id.startsWith('config:')) {
                    categories[1].nodes.push(n);
                } else if (t.includes('data') || id.startsWith('data:')) {
                    categories[3].nodes.push(n);
                } else {
                    categories[2].nodes.push(n);
                }
            });

            // Count critical items per category
            categories.forEach(cat => {
                cat.criticalCount = cat.nodes.filter(n => 
                    n.metadata?.broken || 
                    (edgeMap[n.id] || []).some(e => e.confidence < 0.5)
                ).length;
            });

            const col = createColumn('Domains');
            const list = col.querySelector('.column-list');
            
            categories.forEach(cat => {
                if (cat.nodes.length === 0) return;
                
                const item = document.createElement('div');
                item.className = 'item';
                item.tabIndex = 0;
                item.dataset.categoryId = cat.id;
                
                // Add risk indicator if category has critical items
                if (cat.criticalCount > 0) {
                    item.dataset.risk = 'warning';
                }
                
                item.innerHTML = `
                    <div class="item-icon ${cat.color}">${cat.icon}</div>
                    <div class="item-content">
                        <div class="item-main">
                            <span class="item-label">${cat.name}</span>
                            ${cat.criticalCount > 0 ? `<span class="badge critical">${cat.criticalCount} issues</span>` : ''}
                        </div>
                        <div class="item-meta">
                            <span class="meta-item">${cat.nodes.length} items</span>
                            <span class="meta-item">${cat.desc}</span>
                        </div>
                    </div>
                    <span class="item-arrow">→</span>
                `;
                
                item.onclick = () => handleCategoryClick(item, cat);
                item.onmouseenter = () => handleItemHover(item, 0);
                item.onmouseleave = () => clearLineageHighlight();
                
                list.appendChild(item);
            });
            
            columnsWrapper.appendChild(col);
        }

        function handleCategoryClick(item, category) {
            selectItem(item);
            selectedPath = [{ type: 'category', id: category.id, name: category.name }];
            removeColumnsAfter(0);
            renderNodeListColumn(category.nodes, category.name, category.color);
        }

        function renderNodeListColumn(nodes, title, colorClass) {
            const col = createColumn(title, nodes.length);
            const list = col.querySelector('.column-list');
            
            // Sort: critical items first, then alphabetically
            nodes.sort((a, b) => {
                const aRisk = getNodeRisk(a);
                const bRisk = getNodeRisk(b);
                if (aRisk !== bRisk) return aRisk === 'critical' ? -1 : 1;
                return a.name.localeCompare(b.name);
            });

            nodes.forEach(node => {
                const outgoing = edgeMap[node.id] || [];
                const incoming = reverseEdgeMap[node.id] || [];
                const risk = getNodeRisk(node);
                const badges = getNodeBadges(node, outgoing);
                
                const item = document.createElement('div');
                item.className = 'item';
                item.tabIndex = 0;
                item.dataset.nodeId = node.id;
                if (risk) item.dataset.risk = risk;
                
                const icon = getNodeIcon(node.type, node.id);
                const domainClass = getDomainClass(node.type, node.id);
                
                item.innerHTML = `
                    <div class="item-icon ${domainClass}">${icon}</div>
                    <div class="item-content">
                        <div class="item-main">
                            <span class="item-label" title="${node.name}">${node.name}</span>
                            ${badges}
                        </div>
                        <div class="item-meta">
                            ${outgoing.length > 0 ? `<span class="meta-item">→ ${outgoing.length} deps</span>` : ''}
                            ${incoming.length > 0 ? `<span class="meta-item">← ${incoming.length} refs</span>` : ''}
                            <span class="meta-item">${getShortPath(node.path)}</span>
                        </div>
                    </div>
                    ${outgoing.length > 0 ? '<span class="item-arrow">→</span>' : ''}
                `;
                
                const colIndex = columnsWrapper.children.length;
                item.onclick = () => handleNodeClick(item, node, colIndex);
                item.onmouseenter = () => handleItemHover(item, colIndex);
                item.onmouseleave = () => clearLineageHighlight();
                
                list.appendChild(item);
            });

            columnsWrapper.appendChild(col);
            col.scrollIntoView({ behavior: 'smooth', inline: 'end' });
        }

        function handleNodeClick(item, node, colIndex) {
            selectItem(item);
            selectedPath = selectedPath.slice(0, colIndex);
            selectedPath.push({ type: 'node', id: node.id, name: node.name });
            removeColumnsAfter(colIndex);
            
            const outgoing = edgeMap[node.id] || [];
            
            if (outgoing.length > 0) {
                renderDependencyColumn(node.id, node.name);
            }
            
            showInspector(node);
        }

        function renderDependencyColumn(sourceId, sourceName) {
            const edges = edgeMap[sourceId] || [];
            if (edges.length === 0) return;
            
            const col = createColumn(`Impacts from ${sourceName}`, edges.length);
            const list = col.querySelector('.column-list');
            
            // Sort by confidence (lowest first to surface issues)
            edges.sort((a, b) => (a.confidence || 1) - (b.confidence || 1));
            
            edges.forEach(edge => {
                const node = nodeMap[edge.target_id];
                if (!node) return;
                
                const outgoing = edgeMap[node.id] || [];
                const confidence = edge.confidence || 1.0;
                const confPercent = Math.round(confidence * 100);
                const confClass = confidence >= 0.8 ? 'high' : confidence >= 0.5 ? 'medium' : 'low';
                
                const item = document.createElement('div');
                item.className = 'item';
                item.tabIndex = 0;
                item.dataset.nodeId = node.id;
                item.dataset.edgeSource = sourceId;
                
                if (confidence < 0.5) item.dataset.risk = 'warning';
                
                const icon = getNodeIcon(node.type, node.id);
                const domainClass = getDomainClass(node.type, node.id);
                
                item.innerHTML = `
                    <div class="item-icon ${domainClass}">${icon}</div>
                    <div class="item-content">
                        <div class="item-main">
                            <span class="item-label" title="${node.name}">${node.name}</span>
                            ${confidence < 0.5 ? '<span class="badge unused">Low Conf</span>' : ''}
                        </div>
                        <div class="item-meta">
                            <span class="meta-item">
                                <span class="confidence-dot ${confClass}"></span>
                                ${confPercent}%
                            </span>
                            <span class="meta-item">${getShortPath(node.path)}</span>
                        </div>
                    </div>
                    ${outgoing.length > 0 ? '<span class="item-arrow">→</span>' : ''}
                `;
                
                const colIndex = columnsWrapper.children.length;
                item.onclick = () => handleDependencyClick(item, node, edge, colIndex);
                item.onmouseenter = () => handleItemHover(item, colIndex);
                item.onmouseleave = () => clearLineageHighlight();
                
                list.appendChild(item);
            });

            columnsWrapper.appendChild(col);
            col.scrollIntoView({ behavior: 'smooth', inline: 'end' });
        }

        function handleDependencyClick(item, node, edge, colIndex) {
            selectItem(item);
            selectedPath = selectedPath.slice(0, colIndex);
            selectedPath.push({ type: 'node', id: node.id, name: node.name, edge: edge });
            removeColumnsAfter(colIndex);
            
            const outgoing = edgeMap[node.id] || [];
            if (outgoing.length > 0) {
                renderDependencyColumn(node.id, node.name);
            }
            
            showInspector(node, edge);
        }

        // ============================================================
        // INSPECTOR
        // ============================================================
        function showInspector(node, incomingEdge = null) {
            const confidence = incomingEdge ? (incomingEdge.confidence || 1.0) : null;
            const confPercent = confidence ? Math.round(confidence * 100) : null;
            const confClass = confidence >= 0.8 ? 'high' : confidence >= 0.5 ? 'medium' : 'low';
            const confColor = confidence >= 0.8 ? 'var(--color-success)' : confidence >= 0.5 ? 'var(--color-warning)' : 'var(--color-danger)';
            
            const filePath = node.path || node.metadata?.file || '';
            const lineNum = node.line || node.metadata?.line || 1;
            const vscodeUrl = filePath ? `vscode://file${filePath.startsWith('/') ? '' : '/'}${filePath}:${lineNum}` : null;
            
            const domainClass = getDomainClass(node.type, node.id);
            const risk = getNodeRisk(node);
            
            // Build lineage path
            const lineagePath = selectedPath.filter(p => p.type === 'node').slice(-3);
            
            inspector.innerHTML = `
                <div class="inspector-header">
                    <div class="inspector-type">
                        <span class="type-dot ${domainClass}"></span>
                        ${node.type || 'Unknown Type'}
                    </div>
                    <div class="inspector-title">${node.name}</div>
                </div>
                
                <div class="inspector-body">
                    ${risk ? `
                    <div class="section">
                        <div class="section-header">⚠ Risk Assessment</div>
                        <div class="risk-card ${risk}">
                            <div class="risk-header">
                                <span class="risk-icon">${risk === 'critical' ? '🔴' : '🟡'}</span>
                                <span class="risk-title">${risk === 'critical' ? 'Breaking Change Detected' : 'Review Recommended'}</span>
                            </div>
                            <div class="risk-description">
                                ${risk === 'critical' 
                                    ? 'This artifact has a broken dependency or is missing a required target. Deployment may fail.'
                                    : 'Low confidence match. Verify this connection is intentional.'}
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${confidence !== null ? `
                    <div class="section">
                        <div class="section-header">🎯 Match Confidence</div>
                        <div class="confidence-section">
                            <div class="confidence-header">
                                <span class="confidence-label">Link Strength</span>
                                <span class="confidence-value" style="color: ${confColor}">${confPercent}%</span>
                            </div>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: ${confPercent}%; background: ${confColor}"></div>
                            </div>
                            <div class="confidence-explanation">
                                ${incomingEdge?.metadata?.explanation || 'Matched via token overlap between artifact names.'}
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${lineagePath.length > 1 ? `
                    <div class="section">
                        <div class="section-header">🔗 Dependency Path</div>
                        <div class="lineage-mini">
                            <div class="lineage-flow">
                                ${lineagePath.map((p, i) => `
                                    <div class="lineage-node ${i === lineagePath.length - 1 ? 'current' : ''}" title="${p.name}">
                                        ${truncate(p.name, 12)}
                                    </div>
                                    ${i < lineagePath.length - 1 ? '<span class="lineage-arrow">→</span>' : ''}
                                `).join('')}
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    
                    <div class="section">
                        <div class="section-header">📍 Source Location</div>
                        <div class="location-card">
                            <div class="location-path">${filePath || 'No file path available'}</div>
                            <div class="location-meta">
                                <span>Line ${lineNum}</span>
                                ${node.tokens?.length ? `<span>${node.tokens.length} tokens</span>` : ''}
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="inspector-footer">
                    ${vscodeUrl ? `
                    <a href="${vscodeUrl}" class="btn btn-primary">
                        <span>📝</span> Open in VS Code
                    </a>
                    ` : `
                    <button class="btn btn-primary" disabled>
                        <span>📝</span> No File Location
                    </button>
                    `}
                    <button class="btn btn-secondary" onclick="copyNodeId('${node.id}')">
                        <span>📋</span> Copy Node ID
                    </button>
                </div>
            `;
            
            inspector.style.display = 'flex';
        }

        function hideInspector() {
            inspector.style.display = 'none';
        }

        function copyNodeId(nodeId) {
            navigator.clipboard.writeText(nodeId).then(() => {
                // Visual feedback could be added here
            });
        }

        // ============================================================
        // HOVER LINEAGE HIGHLIGHTING
        // ============================================================
        function handleItemHover(item, colIndex) {
            clearLineageHighlight();
            hoveredItem = item;
            
            // Highlight current item
            item.classList.add('lineage-source');
            
            // Highlight ancestors (items in previous columns that led here)
            for (let i = 0; i < colIndex; i++) {
                const col = columnsWrapper.children[i];
                const activeItem = col.querySelector('.item.active');
                if (activeItem) {
                    activeItem.classList.add('lineage-highlight');
                }
            }
            
            // If this item has outgoing edges, highlight potential targets
            const nodeId = item.dataset.nodeId;
            if (nodeId) {
                const edges = edgeMap[nodeId] || [];
                if (edges.length > 0 && columnsWrapper.children[colIndex + 1]) {
                    const nextCol = columnsWrapper.children[colIndex + 1];
                    edges.forEach(e => {
                        const targetItem = nextCol.querySelector(`[data-node-id="${e.target_id}"]`);
                        if (targetItem) {
                            targetItem.classList.add('lineage-highlight');
                        }
                    });
                }
            }
        }

        function clearLineageHighlight() {
            document.querySelectorAll('.lineage-highlight, .lineage-source').forEach(el => {
                el.classList.remove('lineage-highlight', 'lineage-source');
            });
            hoveredItem = null;
        }

        // ============================================================
        // HELPER FUNCTIONS
        // ============================================================
        function createColumn(title, count) {
            const col = document.createElement('div');
            col.className = 'column';
            col.innerHTML = `
                <div class="column-header">
                    <span class="column-title">${title}</span>
                    ${count !== undefined ? `<span class="column-count">${count}</span>` : ''}
                </div>
                <div class="column-list"></div>
            `;
            return col;
        }

        function selectItem(item) {
            // Deselect siblings
            const list = item.parentElement;
            list.querySelectorAll('.item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        }

        function removeColumnsAfter(index) {
            const columns = Array.from(columnsWrapper.children);
            for (let i = index + 1; i < columns.length; i++) {
                columns[i].remove();
            }
        }

        function getNodeRisk(node) {
            if (node.metadata?.broken || node.metadata?.missing_target) return 'critical';
            const edges = edgeMap[node.id] || [];
            if (edges.some(e => e.confidence && e.confidence < 0.5)) return 'warning';
            return null;
        }

        function getNodeBadges(node, outgoingEdges) {
            let badges = '';
            
            if (node.metadata?.broken) {
                badges += '<span class="badge breaking">Broken</span>';
            }
            if (node.metadata?.new || node.metadata?.added) {
                badges += '<span class="badge new">New</span>';
            }
            if (outgoingEdges.length === 0 && (reverseEdgeMap[node.id] || []).length === 0) {
                badges += '<span class="badge unused">Orphan</span>';
            }
            
            return badges;
        }

        function getNodeIcon(type, id) {
            const t = (type || '').toLowerCase();
            const i = (id || '').toLowerCase();
            
            if (t.includes('infra') || t.includes('terraform') || i.startsWith('infra:')) return '☁️';
            if (t.includes('env') || t.includes('config') || i.startsWith('env:') || i.startsWith('config:')) return '🔧';
            if (t.includes('data') || i.startsWith('data:')) return '📊';
            return '📄';
        }

        function getDomainClass(type, id) {
            const t = (type || '').toLowerCase();
            const i = (id || '').toLowerCase();
            
            if (t.includes('infra') || t.includes('terraform') || i.startsWith('infra:')) return 'infra';
            if (t.includes('env') || t.includes('config') || i.startsWith('env:') || i.startsWith('config:')) return 'config';
            if (t.includes('data') || i.startsWith('data:')) return 'data';
            return 'code';
        }

        function getShortPath(path) {
            if (!path) return '';
            const parts = path.split('/');
            if (parts.length <= 2) return path;
            return '…/' + parts.slice(-2).join('/');
        }

        function truncate(str, len) {
            if (!str) return '';
            return str.length > len ? str.substring(0, len) + '…' : str;
        }

        // ============================================================
        // KEYBOARD NAVIGATION
        // ============================================================
        function setupKeyboardNavigation() {
            document.addEventListener('keydown', (e) => {
                const activeCol = document.querySelector('.column:has(.item.active)') || columnsWrapper.firstChild;
                if (!activeCol) return;
                
                const items = Array.from(activeCol.querySelectorAll('.item'));
                const activeItem = activeCol.querySelector('.item.active');
                const activeIndex = activeItem ? items.indexOf(activeItem) : -1;
                
                switch (e.key) {
                    case 'ArrowDown':
                        e.preventDefault();
                        if (activeIndex < items.length - 1) {
                            items[activeIndex + 1].click();
                        }
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        if (activeIndex > 0) {
                            items[activeIndex - 1].click();
                        }
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        // Focus first item in next column
                        const nextCol = activeCol.nextElementSibling;
                        if (nextCol && !nextCol.classList.contains('inspector')) {
                            const firstItem = nextCol.querySelector('.item');
                            if (firstItem) firstItem.click();
                        }
                        break;
                    case 'ArrowLeft':
                        e.preventDefault();
                        // Focus active item in previous column
                        const prevCol = activeCol.previousElementSibling;
                        if (prevCol) {
                            const prevActive = prevCol.querySelector('.item.active');
                            if (prevActive) prevActive.focus();
                        }
                        break;
                    case 'Enter':
                        if (activeItem) {
                            // Trigger "Open in Editor" if inspector is visible
                            const openBtn = inspector.querySelector('.btn-primary:not([disabled])');
                            if (openBtn) openBtn.click();
                        }
                        break;
                }
            });
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