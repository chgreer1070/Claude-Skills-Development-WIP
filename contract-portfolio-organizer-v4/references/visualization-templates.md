# Visualization Templates Reference

This file contains the HTML/SVG/Markdown/Timeline templates used by the contract-portfolio-organizer skill. Read this file when generating the four visualization deliverables.

## Color Scheme (consistent across all four deliverables)

| Contract Type | Color | Hex | Badge Text |
|---|---|---|---|
| Parent types (MSA, PSA, Supply, Framework, GTC, Interim, Sourcing, Cooperation) | Blue | #2563EB | `PARENT` |
| Amendment / Assignment-Novation | Amber | #D97706 | `AMEND` / `ASSIGN` |
| SOW / Sub-SOW | Green | #059669 | `SOW` |
| Addendum / PO Terms | Teal | #0D9488 | `ADDENDUM` |
| Ancillary (LOA, Letter, Settlement) | Slate | #64748B | `ANCILLARY` |
| Termination | Red | #DC2626 | `TERMINATED` |
| Standalone (NDA, etc.) | Purple | #7C3AED | `STANDALONE` |
| Placeholder (not uploaded) | Gray dashed | #9CA3AF | `⚠️ MISSING` |

---

## Template 1: Interactive HTML Hierarchy (_HIERARCHY.html)

Build a single-file HTML page. All CSS and JS must be inline. No external dependencies.

### Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Contract Hierarchy: {CUSTOMER_NAME}</title>
    <style>
        /* Self-contained styles */
        :root {
            --parent: #2563EB;
            --amendment: #D97706;
            --sow: #059669;
            --addendum: #0D9488;
            --ancillary: #64748B;
            --terminated: #DC2626;
            --standalone: #7C3AED;
            --missing: #9CA3AF;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; padding: 2rem; }
        h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
        .subtitle { color: #64748b; margin-bottom: 2rem; font-size: 0.875rem; }
        .tree { padding-left: 0; }
        .tree ul { padding-left: 1.5rem; border-left: 2px solid #e2e8f0; margin-left: 0.75rem; }
        .tree li { list-style: none; position: relative; padding: 0.5rem 0; }
        .node { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; background: white; border-radius: 0.5rem; border: 1px solid #e2e8f0; cursor: pointer; transition: box-shadow 0.15s; }
        .node:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .node.missing { border-style: dashed; border-color: var(--missing); background: #f9fafb; }
        .badge { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; padding: 0.15rem 0.5rem; border-radius: 9999px; color: white; white-space: nowrap; }
        .badge-parent { background: var(--parent); }
        .badge-amendment { background: var(--amendment); }
        .badge-sow { background: var(--sow); }
        .badge-addendum { background: var(--addendum); }
        .badge-ancillary { background: var(--ancillary); }
        .badge-terminated { background: var(--terminated); }
        .badge-standalone { background: var(--standalone); }
        .badge-missing { background: var(--missing); }
        .node-title { font-weight: 600; font-size: 0.9rem; }
        .node-date { color: #64748b; font-size: 0.8rem; }
        .node-status { font-size: 0.75rem; color: #94a3b8; }
        .toggle { font-size: 0.75rem; color: #94a3b8; cursor: pointer; user-select: none; width: 1.25rem; text-align: center; }
        .collapsed > ul { display: none; }
        .detail-panel { position: fixed; right: 0; top: 0; width: 350px; height: 100vh; background: white; border-left: 1px solid #e2e8f0; padding: 1.5rem; overflow-y: auto; transform: translateX(100%); transition: transform 0.2s; z-index: 100; }
        .detail-panel.open { transform: translateX(0); }
        .detail-panel h3 { font-size: 1rem; margin-bottom: 1rem; }
        .detail-row { margin-bottom: 0.75rem; }
        .detail-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
        .detail-value { font-size: 0.875rem; margin-top: 0.15rem; color: #334155; }
        .detail-value.term { font-family: monospace; font-size: 0.8rem; }
        .stats { display: flex; gap: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap; }
        .stat { background: white; padding: 1rem 1.25rem; border-radius: 0.5rem; border: 1px solid #e2e8f0; }
        .stat-value { font-size: 1.5rem; font-weight: 700; }
        .stat-label { font-size: 0.75rem; color: #64748b; }
    </style>
</head>
<body>
    <h1>📋 Contract Hierarchy: {CUSTOMER_NAME}</h1>
    <p class="subtitle">Generated {DATE} · {COUNT} contracts across {PARENT_COUNT} agreement families</p>

    <div class="stats">
        <div class="stat"><div class="stat-value">{TOTAL}</div><div class="stat-label">Total Contracts</div></div>
        <div class="stat"><div class="stat-value">{PARENTS}</div><div class="stat-label">Parent Agreements</div></div>
        <div class="stat"><div class="stat-value">{AMENDMENTS}</div><div class="stat-label">Amendments</div></div>
        <div class="stat"><div class="stat-value">{ANCILLARY}</div><div class="stat-label">Ancillary</div></div>
        <div class="stat"><div class="stat-value">{MISSING}</div><div class="stat-label">Missing / Not Uploaded</div></div>
    </div>

    <div class="tree" id="tree">
        <!-- Generated tree nodes go here -->
    </div>

    <div class="detail-panel" id="detailPanel">
        <h3 id="detailTitle"></h3>
        <div id="detailContent"></div>
    </div>

    <script>
        // Contract data injected here
        const contracts = {CONTRACT_DATA_JSON};

        // Build tree HTML from hierarchical data
        function buildTree(nodes, container) {
            const ul = document.createElement('ul');
            nodes.forEach(node => {
                const li = document.createElement('li');
                const hasChildren = node.children && node.children.length > 0;

                const div = document.createElement('div');
                div.className = 'node' + (node.missing ? ' missing' : '');
                div.onclick = (e) => { e.stopPropagation(); showDetail(node); };

                if (hasChildren) {
                    const toggle = document.createElement('span');
                    toggle.className = 'toggle';
                    toggle.textContent = '▼';
                    toggle.onclick = (e) => {
                        e.stopPropagation();
                        li.classList.toggle('collapsed');
                        toggle.textContent = li.classList.contains('collapsed') ? '▶' : '▼';
                    };
                    div.appendChild(toggle);
                }

                const badge = document.createElement('span');
                badge.className = 'badge badge-' + node.badge_class;
                badge.textContent = node.badge_text;
                div.appendChild(badge);

                const title = document.createElement('span');
                title.className = 'node-title';
                title.textContent = node.title;
                div.appendChild(title);

                const date = document.createElement('span');
                date.className = 'node-date';
                date.textContent = node.effective_date || 'Date unknown';
                div.appendChild(date);

                if (node.status === 'terminated') {
                    const status = document.createElement('span');
                    status.className = 'node-status';
                    status.textContent = '⊘ Terminated';
                    div.appendChild(status);
                }

                li.appendChild(div);
                if (hasChildren) buildTree(node.children, li);
                ul.appendChild(li);
            });
            container.appendChild(ul);
        }

        function showDetail(node) {
            const panel = document.getElementById('detailPanel');
            document.getElementById('detailTitle').textContent = node.title;
            const content = document.getElementById('detailContent');
            content.innerHTML = '';
            const fields = [
                ['Type', node.document_type],
                ['Effective Date', node.effective_date],
                ['Expiration Date', node.expiration_date],
                ['Term', node.term],
                ['Parties', (node.parties || []).join(', ')],
                ['Status', node.status],
                ['Contract Value', node.contract_value],
                ['Liability Cap', node.liability_cap],
                ['Payment Terms', node.payment_terms],
                ['Parent Reference', node.parent_ref],
                ['Governing Law', node.governing_law],
                ['Original Filename', node.filename]
            ];
            fields.forEach(([label, value]) => {
                if (value) {
                    const row = document.createElement('div');
                    row.className = 'detail-row';
                    const isFinancial = ['Contract Value', 'Liability Cap', 'Payment Terms'].includes(label);
                    const valueClass = isFinancial ? 'detail-value term' : 'detail-value';
                    row.innerHTML = `<div class="detail-label">${label}</div><div class="${valueClass}">${value}</div>`;
                    content.appendChild(row);
                }
            });
            panel.classList.add('open');
        }

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.detail-panel') && !e.target.closest('.node')) {
                document.getElementById('detailPanel').classList.remove('open');
            }
        });

        buildTree(contracts, document.getElementById('tree'));
    </script>
</body>
</html>
```

### Generating the data

Build the `contracts` array as a nested JSON structure matching the hierarchy. Each node:

```json
{
    "title": "Manufacturing Services Agreement",
    "document_type": "MSA",
    "badge_class": "parent",
    "badge_text": "PARENT",
    "effective_date": "2015-10-23",
    "expiration_date": "2025-10-22",
    "term": "10 years",
    "status": "active",
    "parties": ["Cisa S.p.A.", "Flextronics Industrial, Ltd."],
    "parent_ref": null,
    "governing_law": "New York",
    "contract_value": "$12.5M annually",
    "liability_cap": "$25M",
    "payment_terms": "Net 30",
    "filename": "Cisa_MSA_10-2015_fully_executed.pdf",
    "missing": false,
    "children": [ /* nested child nodes */ ]
}
```

---

## Template 2: Static SVG Tree (_HIERARCHY.svg)

Generate a clean SVG using Python. Complete implementation with layout algorithm:

### Complete Python SVG Generation Function

```python
def generate_hierarchy_svg(tree_data, customer_name):
    """
    Generate a static SVG tree visualization from hierarchical contract data.
    Implements breadth-first layout with connector lines and styled nodes.
    """

    # Layout constants
    NODE_W = 280
    NODE_H = 60
    H_GAP = 40  # horizontal gap between nodes
    V_GAP = 100  # vertical gap between levels
    PADDING = 60

    # Color map
    COLORS = {
        'parent': '#2563EB',
        'amendment': '#D97706',
        'sow': '#059669',
        'addendum': '#0D9488',
        'ancillary': '#64748B',
        'terminated': '#DC2626',
        'standalone': '#7C3AED',
        'missing': '#9CA3AF'
    }

    # Calculate positions using breadth-first traversal
    def calculate_positions(nodes, parent_x=None, parent_y=None, level=0, level_positions=None):
        """Recursively calculate (x, y) for each node."""
        if level_positions is None:
            level_positions = {}

        if level not in level_positions:
            level_positions[level] = []

        positions = {}

        for node in nodes:
            # Assign x based on position in level (spread horizontally)
            node_index = len(level_positions[level])
            x = PADDING + (node_index * (NODE_W + H_GAP))
            y = PADDING + (level * V_GAP)

            positions[node.get('id')] = {
                'x': x,
                'y': y,
                'node': node,
                'children': []
            }

            level_positions[level].append(x)

            # Recursively process children
            if node.get('children'):
                child_positions = calculate_positions(
                    node['children'],
                    parent_x=x,
                    parent_y=y,
                    level=level + 1,
                    level_positions=level_positions
                )
                positions.update(child_positions)

        return positions

    # Flatten tree and assign IDs
    node_counter = [0]
    def assign_ids(nodes):
        for node in nodes:
            node['id'] = f"node_{node_counter[0]}"
            node_counter[0] += 1
            if node.get('children'):
                assign_ids(node['children'])

    assign_ids(tree_data)
    positions = calculate_positions(tree_data)

    # Calculate canvas size
    max_x = max([p['x'] for p in positions.values()]) if positions else 0
    max_y = max([p['y'] for p in positions.values()]) if positions else 0
    width = max_x + NODE_W + PADDING
    height = max_y + NODE_H + PADDING

    # Build SVG
    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">')
    svg_parts.append('''<defs>
        <style>
            text { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
            .node-rect { stroke-width: 2; }
            .node-rect.missing { stroke-dasharray: 5,5; }
            .connector { stroke: #cbd5e1; stroke-width: 1.5; fill: none; }
        </style>
    </defs>''')

    # Draw connectors first (so they appear behind nodes)
    connectors = []
    for node_id, pos in positions.items():
        node = pos['node']
        if node.get('children'):
            for child in node['children']:
                child_id = child['id']
                if child_id in positions:
                    child_pos = positions[child_id]
                    # Draw line from parent center to child center
                    x1 = pos['x'] + NODE_W / 2
                    y1 = pos['y'] + NODE_H
                    x2 = child_pos['x'] + NODE_W / 2
                    y2 = child_pos['y']
                    svg_parts.append(f'<line class="connector" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')

    # Draw nodes
    for node_id, pos in positions.items():
        node = pos['node']
        x = pos['x']
        y = pos['y']
        badge_class = node.get('badge_class', 'missing')
        color = COLORS.get(badge_class, '#9CA3AF')
        is_missing = node.get('missing', False)
        dash_class = ' missing' if is_missing else ''
        stroke_width = 2 if is_missing else 2

        # Node container group
        svg_parts.append(f'<g transform="translate({x}, {y})">')

        # Background rectangle
        svg_parts.append(f'<rect class="node-rect{dash_class}" width="{NODE_W}" height="{NODE_H}" rx="8" fill="white" stroke="{color}" stroke-width="{stroke_width}"/>')

        # Title text
        title = node.get('title', 'Unknown')[:40]  # Truncate long titles
        svg_parts.append(f'<text x="12" y="22" font-size="13" font-weight="600" fill="#1e293b">{title}</text>')

        # Type and date text
        doc_type = node.get('document_type', 'Unknown')
        effective_date = node.get('effective_date', 'Unknown date')
        svg_parts.append(f'<text x="12" y="40" font-size="11" fill="#64748b">{doc_type} · {effective_date}</text>')

        # Badge
        badge_text = node.get('badge_text', '?')
        svg_parts.append(f'<rect x="220" y="8" width="50" height="18" rx="9" fill="{color}"/>')
        svg_parts.append(f'<text x="245" y="20" font-size="9" fill="white" text-anchor="middle" font-weight="700">{badge_text}</text>')

        svg_parts.append('</g>')

    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)
```

### Node Structure for SVG

Each node in the SVG is rendered as:

```xml
<g transform="translate({x}, {y})">
    <rect width="280" height="60" rx="8" fill="white" stroke="{color}" stroke-width="2"/>
    <text x="12" y="22" font-size="13" font-weight="600" fill="#1e293b">{title}</text>
    <text x="12" y="40" font-size="11" fill="#64748b">{type} · {date}</text>
    <rect x="220" y="8" width="50" height="18" rx="9" fill="{color}"/>
    <text x="245" y="20" font-size="9" fill="white" text-anchor="middle" font-weight="700">{badge}</text>
</g>
```

---

## Template 3: Markdown Outline (_HIERARCHY.md)

Generate programmatically from the hierarchical tree data structure.

### Markdown Format

```markdown
# Contract Hierarchy: {CUSTOMER_NAME}

Generated {DATE} | {TOTAL} contracts across {PARENT_COUNT} agreement families

## Summary Statistics

- **Total Contracts**: {TOTAL}
- **Parent Agreements**: {PARENTS}
- **Amendments**: {AMENDMENTS}
- **SOWs**: {SOWS}
- **Ancillary Documents**: {ANCILLARY}
- **Terminated**: {TERMINATED}
- **Missing/Not Uploaded**: {MISSING}

---

## Parent Agreements & Children

### {PARENT_TITLE} (Effective {DATE})
*{DESCRIPTION_FROM_RECITALS}*

**Status**: {STATUS} | **Governing Law**: {GOVERNING_LAW} | **Parties**: {PARTIES}

#### Amendments & Restatements
- **Amendment No. 1** (Effective 2016-05-15) - Adds supply provisions
- **First Amendment & Restatement** (Effective 2018-02-03) - Complete rewrite

#### Statements of Work
- **SOW A-1: Manufacturing Support** (Effective 2016-01-10 – Expires 2023-12-31, 2-year term)
- **SOW B-2: Maintenance Services** (Effective 2017-06-30 – Expires 2025-06-29, 2-year term)
  - Sub-SOW B-2a: Preventive Maintenance Phase
  - Sub-SOW B-2b: Emergency Response Protocols

#### Ancillary Documents
- **LOA #1** (Dated 2016-03-15) - Temporary rate adjustment for Q2 2016
- **Letter Agreement: BGA Amendment** (Dated 2018-11-20) - Adds new geographic territory

---

### {PARENT_TITLE_2} (Effective {DATE})
*{DESCRIPTION}*

**Status**: ⊘ Terminated (2024-12-31) | **Governing Law**: {GOVERNING_LAW} | **Parties**: {PARTIES}

#### Amendments & Restatements
- **Waiver Letter** (Effective 2019-07-01) - Waives volume minimums for Q3 2019
- **Addendum 1** (Effective 2020-03-15) - Adds Work-from-Home provisions

#### Statements of Work
- **SOW #1: Implementation** (Effective 2015-12-10 – Expires 2016-12-09, 1-year term)

#### Ancillary Documents
- **Settlement Agreement** (Dated 2024-11-15) - Resolves performance dispute

---

## Orphaned Contracts (No Parent Link Identified)

⚠️ The following {COUNT} contracts could not be linked to a parent agreement. Review these for potential parent relationships:

- **Standalone NDA with Acme Corp** (Dated 2019-01-10) - May belong to Cisa family
- **PO Terms (Order #2847)** (Dated 2020-04-05) - Supplier: Unknown
- **Equipment Lease Agreement** (Effective 2017-08-15) - Missing header information

---

## Missing / Not Yet Uploaded

⚠️ {COUNT} referenced contracts were not found in the portfolio:

- PSA Amendment 3 (referenced in Amendment 2, dated 2017-02-03)
- SOW C-1: Logistics Support (referenced in Master SOW, effective 2016-06-01)
```

### Key Formatting Rules

- Use `##` for parent agreements with effective date
- Use `###` for category headers (Amendments, SOWs, Ancillary)
- Use `-` for individual documents with effective/expiration dates and term info
- Include brief descriptions extracted from recitals or preamble where available
- Mark terminated agreements with ⊘ symbol
- Mark missing agreements with ⚠️ symbol
- Include a summary statistics section at the top
- Group orphaned and missing contracts at the end

---

## Template 4: Interactive Timeline (_TIMELINE.html)

Complete self-contained HTML5 timeline with horizontal time axis, vertical lanes, event dots, duration bars, and interactive tooltips.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Contract Timeline: {CUSTOMER_NAME}</title>
    <style>
        :root {
            --parent: #2563EB;
            --amendment: #D97706;
            --sow: #059669;
            --addendum: #0D9488;
            --ancillary: #64748B;
            --terminated: #DC2626;
            --standalone: #7C3AED;
            --missing: #9CA3AF;
            --today: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f8fafc;
            color: #1e293b;
            padding: 2rem;
        }
        .header {
            margin-bottom: 2rem;
        }
        h1 {
            font-size: 1.5rem;
            margin-bottom: 0.25rem;
        }
        .subtitle {
            color: #64748b;
            font-size: 0.875rem;
        }
        .legend {
            display: flex;
            gap: 1.5rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
        }
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        .legend-bar {
            width: 20px;
            height: 4px;
            border-radius: 2px;
        }
        .timeline-container {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            padding: 2rem;
            overflow-x: auto;
            margin-top: 2rem;
        }
        .timeline {
            position: relative;
            min-width: 1400px;
            display: flex;
            flex-direction: column;
        }
        .timeline-header {
            display: flex;
            height: 60px;
            margin-bottom: 2rem;
            position: relative;
            border-bottom: 2px solid #e2e8f0;
        }
        .lane-label-space {
            width: 200px;
            flex-shrink: 0;
        }
        .timeline-axis {
            flex: 1;
            position: relative;
        }
        .year-marker {
            position: absolute;
            height: 100%;
            border-left: 1px solid #cbd5e1;
            padding-left: 0.5rem;
            font-weight: 600;
            font-size: 0.875rem;
            color: #475569;
        }
        .timeline-today {
            position: absolute;
            width: 2px;
            background: var(--today);
            top: 0;
            height: 100%;
            opacity: 0.7;
        }
        .timeline-today-label {
            position: absolute;
            top: -1.5rem;
            background: var(--today);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.7rem;
            font-weight: 700;
        }
        .lane {
            display: flex;
            height: 80px;
            margin-bottom: 1rem;
            align-items: center;
            position: relative;
            border-bottom: 1px solid #f1f5f9;
        }
        .lane-label {
            width: 200px;
            flex-shrink: 0;
            padding-right: 1rem;
            font-size: 0.875rem;
            font-weight: 600;
            color: #334155;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .lane-content {
            flex: 1;
            position: relative;
            height: 100%;
        }
        .duration-bar {
            position: absolute;
            height: 6px;
            border-radius: 3px;
            top: 18px;
            opacity: 0.6;
            transition: opacity 0.15s;
        }
        .duration-bar:hover {
            opacity: 1;
        }
        .event {
            position: absolute;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 2px solid white;
            top: 50%;
            transform: translate(-12px, -12px);
            cursor: pointer;
            transition: transform 0.15s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .event:hover {
            transform: translate(-12px, -12px) scale(1.3);
            z-index: 50;
        }
        .event-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: currentColor;
        }
        .tooltip {
            position: fixed;
            background: #1e293b;
            color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            font-size: 0.875rem;
            z-index: 1000;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            pointer-events: none;
            display: none;
        }
        .tooltip.visible {
            display: block;
        }
        .tooltip-title {
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        .tooltip-row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            font-size: 0.8rem;
        }
        .tooltip-label {
            color: #cbd5e1;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📅 Contract Timeline: {CUSTOMER_NAME}</h1>
        <p class="subtitle">Generated {DATE} · Spanning {START_DATE} to {END_DATE} ({SPAN_YEARS} years)</p>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-dot" style="background: var(--parent);"></div>
                <span>Parent Agreements</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background: var(--amendment);"></div>
                <span>Amendments / Assignments</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background: var(--sow);"></div>
                <span>SOWs</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background: var(--addendum);"></div>
                <span>Addendums</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background: var(--ancillary);"></div>
                <span>Ancillary</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background: var(--terminated);"></div>
                <span>Terminations</span>
            </div>
            <div class="legend-item">
                <div class="legend-bar" style="background: #cbd5e1;"></div>
                <span>Contract Duration</span>
            </div>
            <div class="legend-item">
                <div style="width: 2px; height: 16px; background: var(--today);"></div>
                <span>Today</span>
            </div>
        </div>
    </div>

    <div class="timeline-container">
        <div class="timeline" id="timeline">
            <!-- Generated by JavaScript -->
        </div>
    </div>

    <div class="tooltip" id="tooltip"></div>

    <script>
        // Contract timeline data injected here
        const timelineData = {TIMELINE_DATA_JSON};

        // Date utilities
        const dateToX = (dateStr, minDate, maxDate, containerWidth) => {
            const date = new Date(dateStr);
            const min = new Date(minDate);
            const max = new Date(maxDate);
            const ratio = (date - min) / (max - min);
            return ratio * containerWidth;
        };

        const formatDate = (dateStr) => {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        };

        // Color map
        const colorMap = {
            'parent': '#2563EB',
            'amendment': '#D97706',
            'sow': '#059669',
            'addendum': '#0D9488',
            'ancillary': '#64748B',
            'terminated': '#DC2626',
            'standalone': '#7C3AED',
            'missing': '#9CA3AF'
        };

        // Build timeline
        const timelineContainer = document.getElementById('timeline');
        const minDate = timelineData.date_range.start;
        const maxDate = timelineData.date_range.end;

        // Create header with year markers
        const headerDiv = document.createElement('div');
        headerDiv.className = 'timeline-header';

        const labelSpace = document.createElement('div');
        labelSpace.className = 'lane-label-space';
        headerDiv.appendChild(labelSpace);

        const axisDiv = document.createElement('div');
        axisDiv.className = 'timeline-axis';

        // Add year markers
        const minYear = new Date(minDate).getFullYear();
        const maxYear = new Date(maxDate).getFullYear();
        const containerWidth = 1200;  // Approximate

        for (let year = minYear; year <= maxYear; year++) {
            const yearDate = `${year}-01-01`;
            const x = dateToX(yearDate, minDate, maxDate, containerWidth);
            const marker = document.createElement('div');
            marker.className = 'year-marker';
            marker.style.left = x + 'px';
            marker.textContent = year;
            axisDiv.appendChild(marker);
        }

        // Add "today" line
        const todayX = dateToX(new Date().toISOString().split('T')[0], minDate, maxDate, containerWidth);
        const todayLine = document.createElement('div');
        todayLine.className = 'timeline-today';
        todayLine.style.left = todayX + 'px';
        const todayLabel = document.createElement('div');
        todayLabel.className = 'timeline-today-label';
        todayLabel.style.left = (todayX - 20) + 'px';
        todayLabel.textContent = 'TODAY';
        axisDiv.appendChild(todayLine);
        axisDiv.appendChild(todayLabel);

        headerDiv.appendChild(axisDiv);
        timelineContainer.appendChild(headerDiv);

        // Add lanes
        timelineData.lanes.forEach(lane => {
            const laneDiv = document.createElement('div');
            laneDiv.className = 'lane';

            const labelDiv = document.createElement('div');
            labelDiv.className = 'lane-label';
            labelDiv.textContent = lane.label;
            laneDiv.appendChild(labelDiv);

            const contentDiv = document.createElement('div');
            contentDiv.className = 'lane-content';

            // Draw duration bars first (behind events)
            lane.events.forEach((event, idx) => {
                if (event.start_date && event.end_date) {
                    const startX = dateToX(event.start_date, minDate, maxDate, containerWidth);
                    const endX = dateToX(event.end_date, minDate, maxDate, containerWidth);
                    const bar = document.createElement('div');
                    bar.className = 'duration-bar';
                    bar.style.left = startX + 'px';
                    bar.style.width = (endX - startX) + 'px';
                    bar.style.background = colorMap[event.type] || '#9CA3AF';
                    contentDiv.appendChild(bar);
                }
            });

            // Draw event dots
            lane.events.forEach(event => {
                const x = dateToX(event.date, minDate, maxDate, containerWidth);
                const eventDiv = document.createElement('div');
                eventDiv.className = 'event';
                eventDiv.style.left = x + 'px';
                eventDiv.style.color = colorMap[event.type] || '#9CA3AF';
                eventDiv.innerHTML = '<div class="event-dot"></div>';
                eventDiv.addEventListener('mouseenter', (e) => {
                    const tooltip = document.getElementById('tooltip');
                    tooltip.innerHTML = `
                        <div class="tooltip-title">${event.title}</div>
                        <div class="tooltip-row">
                            <span class="tooltip-label">Date:</span>
                            <span>${formatDate(event.date)}</span>
                        </div>
                        <div class="tooltip-row">
                            <span class="tooltip-label">Type:</span>
                            <span>${event.type.charAt(0).toUpperCase() + event.type.slice(1)}</span>
                        </div>
                        ${event.expiration_date ? `<div class="tooltip-row">
                            <span class="tooltip-label">Expires:</span>
                            <span>${formatDate(event.expiration_date)}</span>
                        </div>` : ''}
                        ${event.parties ? `<div class="tooltip-row">
                            <span class="tooltip-label">Parties:</span>
                            <span>${event.parties.length} party(ies)</span>
                        </div>` : ''}
                    `;
                    tooltip.classList.add('visible');
                    const rect = eventDiv.getBoundingClientRect();
                    tooltip.style.left = (rect.left + 12) + 'px';
                    tooltip.style.top = (rect.top - 120) + 'px';
                });
                eventDiv.addEventListener('mouseleave', () => {
                    document.getElementById('tooltip').classList.remove('visible');
                });
                contentDiv.appendChild(eventDiv);
            });

            laneDiv.appendChild(contentDiv);
            timelineContainer.appendChild(laneDiv);
        });
    </script>
</body>
</html>
```

### Timeline Data Structure

```json
{
    "customer": "Allegion",
    "date_range": {
        "start": "2014-12-30",
        "end": "2026-03-10"
    },
    "lanes": [
        {
            "label": "Interim Agreement (Schlage)",
            "parent_date": "2014-12-30",
            "events": [
                {
                    "date": "2014-12-30",
                    "title": "Interim Agreement",
                    "type": "parent",
                    "start_date": "2014-12-30",
                    "end_date": "2015-02-19",
                    "parties": ["Allegion", "Schlage"]
                },
                {
                    "date": "2015-02-20",
                    "title": "PSA",
                    "type": "parent",
                    "start_date": "2015-02-20",
                    "end_date": null,
                    "parties": ["Allegion", "Schlage"]
                },
                {
                    "date": "2015-12-17",
                    "title": "SOW A-7 KPD/KPL",
                    "type": "sow",
                    "start_date": "2015-12-17",
                    "end_date": "2023-12-31",
                    "expiration_date": "2023-12-31",
                    "parties": ["Allegion", "Schlage"]
                },
                {
                    "date": "2025-03-17",
                    "title": "Settlement",
                    "type": "ancillary",
                    "parties": ["Allegion", "Schlage"]
                }
            ]
        },
        {
            "label": "MSA (Cisa)",
            "parent_date": "2015-10-23",
            "events": [
                {
                    "date": "2015-10-23",
                    "title": "MSA",
                    "type": "parent",
                    "start_date": "2015-10-23",
                    "end_date": "2025-10-22",
                    "expiration_date": "2025-10-22",
                    "parties": ["Cisa", "Flextronics"]
                },
                {
                    "date": "2016-05-04",
                    "title": "Consignment Addendum",
                    "type": "addendum",
                    "parties": ["Cisa", "Flextronics"]
                },
                {
                    "date": "2017-02-03",
                    "title": "Amendment 1",
                    "type": "amendment",
                    "parties": ["Cisa", "Flextronics"]
                },
                {
                    "date": "2025-07-16",
                    "title": "Termination Notice",
                    "type": "terminated",
                    "parties": ["Cisa", "Flextronics"]
                }
            ]
        }
    ]
}
```

---

## Implementation Notes

### All Four Templates

1. **Color Consistency**: Use the shared color scheme across all deliverables (HTML, SVG, Markdown, Timeline)
2. **Date Formats**: ISO 8601 internally; display as "MMM DD, YYYY" to users
3. **Confidence Scores**: Include where available; use grayscale fades for lower-confidence data
4. **Responsive Design**: HTML templates should adapt to mobile (stack vertically below 768px)
5. **Accessibility**: Use semantic HTML, ARIA labels, sufficient color contrast (4.5:1 minimum)
6. **Financial Data**: Display with appropriate formatting (currency symbols, commas)
7. **Missing Data**: Always mark with ⚠️ to alert users; never hide gaps silently

### Large Portfolio Guidance (100+ contracts)

- **Hierarchy HTML**: Use collapsible sections; implement scroll-to-top button
- **SVG Tree**: Consider multi-page output or interactive pan/zoom
- **Timeline**: Add date range filter; implement horizontal scroll with sticky labels
- **Markdown**: Break into multiple files per parent agreement; create index

### Data Quality Checks

Before generating visualizations, validate:

- All dates are ISO 8601 format
- Parent references exist and are reciprocal (child points to parent, parent has children)
- No circular references in supersession chains
- Entity names are consistent (check fuzzy matches)
- Financial values have currency codes
