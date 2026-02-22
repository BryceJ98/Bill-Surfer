"""
generate_dashboard.py
---------------------
Modern web dashboard for legislative bill analysis.
Uses legiscan_client.py for API access and generates a clean, interactive dashboard.

Usage:
    python generate_dashboard.py <bill_id>
    python generate_dashboard.py 1423040
    python generate_dashboard.py --port 8080

Requires: pip install flask
"""

import sys
import json
from datetime import date
from flask import Flask, render_template_string, jsonify, request

# Import shared LegiScan client
import legiscan_client as lc

app = Flask(__name__)

# ── MODERN COLOR PALETTE ─────────────────────────────────────────────────────
COLORS = {
    "primary_navy": "#0F172A",
    "secondary_blue": "#1E40AF",
    "action_mint": "#10B981",
    "neutral_gray": "#F8FAFC",
    "border_gray": "#E2E8F0",
    "text_dark": "#1E293B",
    "text_muted": "#64748B",
    "green_bg": "#D1FAE5",
    "green_txt": "#065F46",
    "yellow_bg": "#FEF3C7",
    "yellow_txt": "#92400E",
    "red_bg": "#FEE2E2",
    "red_txt": "#991B1B",
}

# ── HTML TEMPLATE ────────────────────────────────────────────────────────────
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ state }} {{ bill_number }} - Policy Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #F8FAFC 0%, #E2E8F0 100%);
            color: #1E293B;
            min-height: 100vh;
            padding: 2rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, #0F172A 0%, #1E40AF 100%);
            color: white;
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 40px rgba(15, 23, 42, 0.2);
        }

        .header-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #94A3B8;
            margin-bottom: 0.5rem;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .header h2 {
            font-size: 1.1rem;
            font-weight: 400;
            color: #CBD5E1;
            margin-bottom: 1rem;
        }

        .meta-row {
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
            font-size: 0.9rem;
            color: #94A3B8;
        }

        .meta-row span {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Status Stepper */
        .status-stepper {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 0.5rem;
            padding: 1.5rem;
            background: white;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        .step {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: 500;
            font-size: 0.9rem;
        }

        .step.completed {
            background: #D1FAE5;
            color: #065F46;
        }

        .step.current {
            background: #1E40AF;
            color: white;
        }

        .step.pending {
            background: #F1F5F9;
            color: #94A3B8;
        }

        .step-arrow {
            color: #CBD5E1;
            font-size: 1.2rem;
        }

        /* Cards Grid */
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid #F1F5F9;
        }

        .card-title {
            font-size: 1rem;
            font-weight: 600;
            color: #0F172A;
        }

        .card-badge {
            font-size: 0.75rem;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-weight: 500;
        }

        .badge-blue {
            background: #DBEAFE;
            color: #1E40AF;
        }

        .badge-green {
            background: #D1FAE5;
            color: #065F46;
        }

        /* TL;DR Box */
        .tldr-box {
            background: linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 100%);
            border-left: 4px solid #10B981;
            padding: 1.5rem;
            border-radius: 0 12px 12px 0;
            margin-bottom: 1.5rem;
        }

        .tldr-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #065F46;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }

        .tldr-text {
            color: #1E293B;
            line-height: 1.6;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }

        .stat-item {
            text-align: center;
            padding: 1rem;
            background: #F8FAFC;
            border-radius: 8px;
        }

        .stat-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0F172A;
        }

        .stat-label {
            font-size: 0.8rem;
            color: #64748B;
            margin-top: 0.25rem;
        }

        /* Tables */
        .table-container {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background: #0F172A;
            color: white;
            padding: 0.75rem 1rem;
            text-align: left;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        th:first-child {
            border-radius: 8px 0 0 0;
        }

        th:last-child {
            border-radius: 0 8px 0 0;
        }

        td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #E2E8F0;
            font-size: 0.9rem;
        }

        tr:nth-child(even) {
            background: #F8FAFC;
        }

        tr:hover {
            background: #F1F5F9;
        }

        /* Vote Result Badges */
        .vote-passed {
            background: #D1FAE5;
            color: #065F46;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8rem;
        }

        .vote-failed {
            background: #FEE2E2;
            color: #991B1B;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8rem;
        }

        /* Timeline */
        .timeline {
            position: relative;
            padding-left: 2rem;
        }

        .timeline::before {
            content: '';
            position: absolute;
            left: 0.5rem;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #E2E8F0;
        }

        .timeline-item {
            position: relative;
            padding-bottom: 1.25rem;
        }

        .timeline-item::before {
            content: '';
            position: absolute;
            left: -1.6rem;
            top: 0.25rem;
            width: 10px;
            height: 10px;
            background: #1E40AF;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 0 0 2px #1E40AF;
        }

        .timeline-date {
            font-size: 0.8rem;
            color: #64748B;
            font-weight: 500;
        }

        .timeline-chamber {
            font-size: 0.75rem;
            color: #94A3B8;
            text-transform: uppercase;
        }

        .timeline-action {
            color: #1E293B;
            margin-top: 0.25rem;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 2rem;
            color: #64748B;
            font-size: 0.85rem;
        }

        .footer a {
            color: #1E40AF;
            text-decoration: none;
        }

        .footer a:hover {
            text-decoration: underline;
        }

        /* Full Width Card */
        .card-full {
            grid-column: 1 / -1;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .header h1 {
                font-size: 1.75rem;
            }

            .status-stepper {
                flex-wrap: wrap;
            }
        }

        /* Refresh Button */
        .refresh-btn {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: #1E40AF;
            color: white;
            border: none;
            padding: 1rem;
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(30, 64, 175, 0.4);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .refresh-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(30, 64, 175, 0.5);
        }

        .refresh-btn svg {
            width: 24px;
            height: 24px;
        }

        /* Sponsor Tags */
        .sponsor-tag {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: #F1F5F9;
            border-radius: 8px;
            margin: 0.25rem;
            font-size: 0.9rem;
        }

        .sponsor-tag.primary {
            background: #DBEAFE;
            border: 1px solid #1E40AF;
        }

        .party-d {
            color: #1E40AF;
        }

        .party-r {
            color: #DC2626;
        }

        .party-i {
            color: #7C3AED;
        }

        /* Stakeholder Cards */
        .stakeholder-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
        }

        .stakeholder-card {
            background: #F8FAFC;
            border-radius: 8px;
            padding: 1rem;
            border-left: 4px solid #E2E8F0;
        }

        .stakeholder-card.support {
            border-left-color: #10B981;
            background: linear-gradient(135deg, #F0FDF4 0%, #F8FAFC 100%);
        }

        .stakeholder-card.oppose {
            border-left-color: #EF4444;
            background: linear-gradient(135deg, #FEF2F2 0%, #F8FAFC 100%);
        }

        .stakeholder-card.neutral {
            border-left-color: #F59E0B;
            background: linear-gradient(135deg, #FFFBEB 0%, #F8FAFC 100%);
        }

        .stakeholder-name {
            font-weight: 600;
            color: #0F172A;
            margin-bottom: 0.25rem;
        }

        .stakeholder-type {
            font-size: 0.75rem;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .stakeholder-stance {
            font-size: 0.8rem;
            font-weight: 500;
            margin-top: 0.5rem;
        }

        .stakeholder-stance.support { color: #065F46; }
        .stakeholder-stance.oppose { color: #991B1B; }
        .stakeholder-stance.neutral { color: #92400E; }

        /* Vote Detail Section */
        .vote-detail-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        .vote-summary {
            display: flex;
            gap: 2rem;
            margin-bottom: 1.5rem;
            padding: 1rem;
            background: #F8FAFC;
            border-radius: 8px;
        }

        .vote-count-box {
            text-align: center;
            flex: 1;
        }

        .vote-count-box.yea {
            border-right: 1px solid #E2E8F0;
        }

        .vote-count-number {
            font-size: 2.5rem;
            font-weight: 700;
        }

        .vote-count-number.yea { color: #065F46; }
        .vote-count-number.nay { color: #991B1B; }
        .vote-count-number.nv { color: #64748B; }
        .vote-count-number.absent { color: #94A3B8; }

        .vote-count-label {
            font-size: 0.85rem;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .vote-breakdown {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
        }

        .vote-column h4 {
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #E2E8F0;
        }

        .vote-column.yea h4 {
            color: #065F46;
            border-bottom-color: #10B981;
        }

        .vote-column.nay h4 {
            color: #991B1B;
            border-bottom-color: #EF4444;
        }

        .voter-list {
            max-height: 300px;
            overflow-y: auto;
        }

        .voter-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.4rem 0;
            font-size: 0.85rem;
            border-bottom: 1px solid #F1F5F9;
        }

        .voter-item:last-child {
            border-bottom: none;
        }

        .voter-party {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        .voter-party.d { background: #1E40AF; }
        .voter-party.r { background: #DC2626; }
        .voter-party.i { background: #7C3AED; }
        .voter-party.l { background: #F59E0B; }

        .voter-name {
            flex: 1;
        }

        .voter-district {
            font-size: 0.75rem;
            color: #94A3B8;
        }

        /* Collapsible sections */
        .collapse-toggle {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 0.85rem;
            color: #1E40AF;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 0;
        }

        .collapse-toggle:hover {
            text-decoration: underline;
        }

        .collapse-content {
            display: none;
        }

        .collapse-content.show {
            display: block;
        }

        /* Party breakdown bar */
        .party-bar {
            display: flex;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
            margin: 0.5rem 0;
        }

        .party-bar-segment {
            height: 100%;
        }

        .party-bar-segment.d { background: #1E40AF; }
        .party-bar-segment.r { background: #DC2626; }
        .party-bar-segment.i { background: #7C3AED; }

        .party-legend {
            display: flex;
            gap: 1rem;
            font-size: 0.75rem;
            color: #64748B;
            margin-top: 0.25rem;
        }

        .party-legend span {
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-label">Policy Impact Dashboard</div>
            <h1>{{ state }} {{ bill_number }}</h1>
            <h2>{{ title }}</h2>
            <div class="meta-row">
                <span>
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M8 16s6-5.686 6-10A6 6 0 0 0 2 6c0 4.314 6 10 6 10zm0-7a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"/>
                    </svg>
                    {{ state }}
                </span>
                <span>
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M11 6.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1z"/>
                        <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5zM1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4H1z"/>
                    </svg>
                    {{ session_name }}
                </span>
                <span>
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                        <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
                    </svg>
                    Status: {{ status_text }}
                </span>
                <span>
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M3 14s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1H3zm5-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>
                    </svg>
                    {{ primary_sponsor }}{% if sponsor_party %} ({{ sponsor_party }}){% endif %}
                </span>
            </div>
        </div>

        <!-- Status Stepper -->
        <div class="status-stepper">
            {% for step in status_steps %}
                <div class="step {{ step.status }}">
                    {% if step.status == 'completed' %}
                        <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/>
                        </svg>
                    {% elif step.status == 'current' %}
                        <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                            <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
                        </svg>
                    {% else %}
                        <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                        </svg>
                    {% endif %}
                    {{ step.name }}
                </div>
                {% if not loop.last %}
                    <span class="step-arrow">→</span>
                {% endif %}
            {% endfor %}
        </div>

        <!-- TL;DR Box -->
        <div class="tldr-box">
            <div class="tldr-label">The Quick Take</div>
            <div class="tldr-text">{{ description }}</div>
        </div>

        <!-- Stats Cards -->
        <div class="cards-grid">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Legislative Evolution</span>
                    <span class="card-badge badge-blue">{{ version_count }} Version{% if version_count != 1 %}s{% endif %}</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">{{ version_count }}</div>
                        <div class="stat-label">Versions</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{{ "{:,}".format(v1_size) }}</div>
                        <div class="stat-label">Initial Size</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{{ "{:,}".format(latest_size) }}</div>
                        <div class="stat-label">Current Size</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{% if growth >= 0 %}+{% endif %}{{ growth|int }}%</div>
                        <div class="stat-label">Growth</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Sponsors</span>
                    <span class="card-badge badge-green">{{ sponsors|length }} Total</span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                    {% for s in sponsors[:8] %}
                        <div class="sponsor-tag {% if loop.index == 1 %}primary{% endif %}">
                            <span class="party-{{ s.party|lower if s.party else 'i' }}">●</span>
                            {{ s.name }}{% if s.party %} ({{ s.party }}){% endif %}
                        </div>
                    {% endfor %}
                    {% if sponsors|length > 8 %}
                        <div class="sponsor-tag">+{{ sponsors|length - 8 }} more</div>
                    {% endif %}
                </div>
            </div>
        </div>

        <!-- Version History Table -->
        {% if texts %}
        <div class="card" style="margin-bottom: 1.5rem;">
            <div class="card-header">
                <span class="card-title">Bill Text Versions</span>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Version</th>
                            <th>Type</th>
                            <th>Date</th>
                            <th>Size</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for t in texts %}
                        <tr>
                            <td><strong>v{{ loop.index }}</strong></td>
                            <td>{{ t.type }}</td>
                            <td>{{ t.date }}</td>
                            <td>{{ "{:,}".format(t.text_size) }} chars</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        <!-- Key Stakeholders Section -->
        {% if stakeholders %}
        <div class="card" style="margin-bottom: 1.5rem;">
            <div class="card-header">
                <span class="card-title">Key Stakeholders</span>
                <span class="card-badge badge-blue">{{ stakeholders|length }} Identified</span>
            </div>
            <div class="stakeholder-grid">
                {% for s in stakeholders %}
                <div class="stakeholder-card {{ s.stance }}">
                    <div class="stakeholder-type">{{ s.type }}</div>
                    <div class="stakeholder-name">{{ s.name }}</div>
                    <div class="stakeholder-stance {{ s.stance }}">
                        {% if s.stance == 'support' %}
                            ✓ Supports this bill
                        {% elif s.stance == 'oppose' %}
                            ✗ Opposes this bill
                        {% else %}
                            ○ Position unclear
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Detailed Roll Call Votes -->
        {% if vote_details %}
        {% for vote in vote_details %}
        <div class="vote-detail-card">
            <div class="card-header">
                <span class="card-title">{{ vote.desc }}</span>
                <span>
                    {% if vote.passed == 1 %}
                        <span class="vote-passed">PASSED</span>
                    {% else %}
                        <span class="vote-failed">FAILED</span>
                    {% endif %}
                </span>
            </div>
            <p style="font-size: 0.85rem; color: #64748B; margin-bottom: 1rem;">
                {{ vote.chamber }} | {{ vote.date }}
            </p>

            <div class="vote-summary">
                <div class="vote-count-box yea">
                    <div class="vote-count-number yea">{{ vote.yea }}</div>
                    <div class="vote-count-label">Yea</div>
                </div>
                <div class="vote-count-box">
                    <div class="vote-count-number nay">{{ vote.nay }}</div>
                    <div class="vote-count-label">Nay</div>
                </div>
                <div class="vote-count-box">
                    <div class="vote-count-number nv">{{ vote.nv }}</div>
                    <div class="vote-count-label">Not Voting</div>
                </div>
                <div class="vote-count-box">
                    <div class="vote-count-number absent">{{ vote.absent }}</div>
                    <div class="vote-count-label">Absent</div>
                </div>
            </div>

            <!-- Party Breakdown -->
            {% if vote.party_breakdown %}
            <div style="margin-bottom: 1rem;">
                <h4 style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.5rem;">Party Breakdown (Yea Votes)</h4>
                <div class="party-bar">
                    {% if vote.party_breakdown.d_yea > 0 %}
                    <div class="party-bar-segment d" style="width: {{ (vote.party_breakdown.d_yea / vote.yea * 100) if vote.yea > 0 else 0 }}%"></div>
                    {% endif %}
                    {% if vote.party_breakdown.r_yea > 0 %}
                    <div class="party-bar-segment r" style="width: {{ (vote.party_breakdown.r_yea / vote.yea * 100) if vote.yea > 0 else 0 }}%"></div>
                    {% endif %}
                    {% if vote.party_breakdown.i_yea > 0 %}
                    <div class="party-bar-segment i" style="width: {{ (vote.party_breakdown.i_yea / vote.yea * 100) if vote.yea > 0 else 0 }}%"></div>
                    {% endif %}
                </div>
                <div class="party-legend">
                    <span><span class="voter-party d"></span> Democrat: {{ vote.party_breakdown.d_yea }}</span>
                    <span><span class="voter-party r"></span> Republican: {{ vote.party_breakdown.r_yea }}</span>
                    {% if vote.party_breakdown.i_yea > 0 %}
                    <span><span class="voter-party i"></span> Independent: {{ vote.party_breakdown.i_yea }}</span>
                    {% endif %}
                </div>
            </div>
            {% endif %}

            <button class="collapse-toggle" onclick="toggleVoteDetail('vote-{{ loop.index }}')">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/>
                </svg>
                Show individual votes
            </button>

            <div id="vote-{{ loop.index }}" class="collapse-content">
                <div class="vote-breakdown">
                    <div class="vote-column yea">
                        <h4>Voted Yea ({{ vote.yea_voters|length }})</h4>
                        <div class="voter-list">
                            {% for voter in vote.yea_voters %}
                            <div class="voter-item">
                                <span class="voter-party {{ voter.party|lower if voter.party else 'i' }}"></span>
                                <span class="voter-name">{{ voter.name }}</span>
                                <span class="voter-district">{{ voter.district }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    <div class="vote-column nay">
                        <h4>Voted Nay ({{ vote.nay_voters|length }})</h4>
                        <div class="voter-list">
                            {% for voter in vote.nay_voters %}
                            <div class="voter-item">
                                <span class="voter-party {{ voter.party|lower if voter.party else 'i' }}"></span>
                                <span class="voter-name">{{ voter.name }}</span>
                                <span class="voter-district">{{ voter.district }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
        {% endif %}

        <!-- Two Column: Activity & Votes Summary -->
        <div class="cards-grid">
            <!-- Recent Activity Timeline -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Recent Activity</span>
                    <span class="card-badge badge-blue">{{ history|length }} Actions</span>
                </div>
                <div class="timeline">
                    {% for h in history[-10:]|reverse %}
                    <div class="timeline-item">
                        <div class="timeline-date">{{ h.date }}</div>
                        <div class="timeline-chamber">{{ h.chamber }}</div>
                        <div class="timeline-action">{{ h.action }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- Votes Summary -->
            {% if votes and not vote_details %}
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Roll Call Votes</span>
                    <span class="card-badge badge-green">{{ votes|length }} Vote{% if votes|length != 1 %}s{% endif %}</span>
                </div>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Chamber</th>
                                <th>Yea</th>
                                <th>Nay</th>
                                <th>Result</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for v in votes %}
                            <tr>
                                <td>{{ v.date }}</td>
                                <td>{{ v.chamber }}</td>
                                <td><strong style="color: #065F46;">{{ v.yea }}</strong></td>
                                <td><strong style="color: #991B1B;">{{ v.nay }}</strong></td>
                                <td>
                                    {% if v.passed == 1 %}
                                        <span class="vote-passed">PASSED</span>
                                    {% else %}
                                        <span class="vote-failed">FAILED</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            {% endif %}
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>{{ state }} {{ bill_number }} Policy Dashboard | Generated {{ report_date }} | Data: <a href="{{ legiscan_url }}" target="_blank">LegiScan</a></p>
            <p style="margin-top: 0.5rem;">Legislative Assistant</p>
        </div>
    </div>

    <!-- Refresh Button -->
    <button class="refresh-btn" onclick="location.reload()" title="Refresh Data">
        <svg fill="currentColor" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/>
            <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/>
        </svg>
    </button>

    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => location.reload(), 5 * 60 * 1000);

        // Toggle vote detail sections
        function toggleVoteDetail(id) {
            const el = document.getElementById(id);
            if (el) {
                el.classList.toggle('show');
                const btn = el.previousElementSibling;
                if (btn && el.classList.contains('show')) {
                    btn.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M7.646 4.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1-.708.708L8 5.707l-5.646 5.647a.5.5 0 0 1-.708-.708l6-6z"/></svg> Hide individual votes';
                } else if (btn) {
                    btn.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/></svg> Show individual votes';
                }
            }
        }
    </script>
</body>
</html>
"""


def get_status_steps(status_code):
    """
    Convert status code to step data for the stepper.
    LegiScan status codes: 1=Intro, 2=Engrossed, 3=Enrolled, 4=Passed, 5=Vetoed, 6=Failed
    """
    steps = ["Introduced", "Engrossed", "Enrolled", "Passed"]
    status_map = {1: 0, 2: 1, 3: 2, 4: 3, 5: 3, 6: 0, 7: 3, 8: 3}
    current_idx = status_map.get(status_code, 0)

    result = []
    for i, step in enumerate(steps):
        if i < current_idx:
            result.append({"name": step, "status": "completed"})
        elif i == current_idx:
            result.append({"name": step, "status": "current"})
        else:
            result.append({"name": step, "status": "pending"})

    return result


def get_vote_details(votes: list) -> list:
    """
    Fetch detailed roll call data for each vote, including individual legislator votes.
    LegiScan's getRollCall only returns people_id, so we need to fetch person details.
    We cache person lookups to avoid redundant API calls.
    """
    vote_details = []
    person_cache = {}  # Cache person details by people_id

    def get_person_info(people_id):
        """Fetch and cache person details."""
        if people_id in person_cache:
            return person_cache[people_id]

        person = lc.get_person(people_id)
        if person and "error" not in person:
            info = {
                "name": person.get("name", "Unknown"),
                "party": person.get("party", ""),
                "district": person.get("district", ""),
            }
        else:
            info = {"name": f"ID:{people_id}", "party": "", "district": ""}

        person_cache[people_id] = info
        return info

    for vote in votes:
        roll_call_id = vote.get("roll_call_id")
        if not roll_call_id:
            continue

        # Fetch the full roll call data
        roll_call = lc.get_roll_call(roll_call_id)
        if not roll_call or "error" in roll_call:
            continue

        # Extract individual votes
        yea_voters = []
        nay_voters = []
        nv_voters = []
        absent_voters = []

        # Party breakdown
        party_breakdown = {
            "d_yea": 0, "r_yea": 0, "i_yea": 0,
            "d_nay": 0, "r_nay": 0, "i_nay": 0,
        }

        for v in roll_call.get("votes", []):
            people_id = v.get("people_id")
            vote_text = v.get("vote_text", "").lower()

            # Fetch person details (cached)
            voter_info = get_person_info(people_id)
            party = voter_info.get("party", "").upper()

            if vote_text in ("yea", "yes", "aye"):
                yea_voters.append(voter_info)
                if party == "D":
                    party_breakdown["d_yea"] += 1
                elif party == "R":
                    party_breakdown["r_yea"] += 1
                else:
                    party_breakdown["i_yea"] += 1
            elif vote_text in ("nay", "no"):
                nay_voters.append(voter_info)
                if party == "D":
                    party_breakdown["d_nay"] += 1
                elif party == "R":
                    party_breakdown["r_nay"] += 1
                else:
                    party_breakdown["i_nay"] += 1
            elif vote_text in ("nv", "not voting", "present"):
                nv_voters.append(voter_info)
            else:
                absent_voters.append(voter_info)

        # Sort voters by party then name
        def sort_key(v):
            party_order = {"R": 0, "D": 1}
            return (party_order.get(v.get("party", ""), 2), v.get("name", ""))

        yea_voters.sort(key=sort_key)
        nay_voters.sort(key=sort_key)

        vote_details.append({
            "roll_call_id": roll_call_id,
            "date": vote.get("date", ""),
            "chamber": vote.get("chamber", ""),
            "desc": vote.get("desc", "Roll Call Vote"),
            "yea": vote.get("yea", 0),
            "nay": vote.get("nay", 0),
            "nv": vote.get("nv", 0),
            "absent": vote.get("absent", 0),
            "passed": vote.get("passed", 0),
            "yea_voters": yea_voters,
            "nay_voters": nay_voters,
            "party_breakdown": party_breakdown,
        })

    return vote_details


def identify_stakeholders(bill_data: dict) -> list:
    """
    Identify key stakeholders based on bill sponsors and committee info.
    This creates a list of stakeholders including primary sponsors, committee chairs,
    and inferred interested parties based on the bill's subject matter.
    """
    stakeholders = []
    sponsors = bill_data.get("sponsors", [])

    # Add primary sponsor as key stakeholder (supporter)
    for i, sponsor in enumerate(sponsors[:3]):
        role = "Primary Sponsor" if sponsor.get("sponsor_type_id") == 1 else "Co-Sponsor"
        stakeholders.append({
            "name": sponsor.get("name", "Unknown"),
            "type": f"Legislator ({role})",
            "stance": "support",
            "party": sponsor.get("party", ""),
        })

    # Add committee info if available
    committee = bill_data.get("committee", {})
    if committee and committee.get("name"):
        stakeholders.append({
            "name": committee.get("name"),
            "type": "Committee",
            "stance": "neutral",
        })

    # Infer stakeholders from bill subjects/title
    title = bill_data.get("title", "").lower()
    description = bill_data.get("description", "").lower()
    combined_text = title + " " + description

    # Map keywords to potential stakeholder groups
    stakeholder_map = {
        "education": [
            {"name": "Teachers Unions", "type": "Interest Group", "stance": "neutral"},
            {"name": "School Districts", "type": "Government Entity", "stance": "neutral"},
            {"name": "Parent Organizations", "type": "Advocacy Group", "stance": "neutral"},
        ],
        "healthcare": [
            {"name": "Hospital Associations", "type": "Industry Group", "stance": "neutral"},
            {"name": "Medical Associations", "type": "Professional Group", "stance": "neutral"},
            {"name": "Patient Advocacy Groups", "type": "Advocacy Group", "stance": "neutral"},
        ],
        "tax": [
            {"name": "Business Associations", "type": "Industry Group", "stance": "neutral"},
            {"name": "Taxpayer Groups", "type": "Advocacy Group", "stance": "neutral"},
        ],
        "environment": [
            {"name": "Environmental Groups", "type": "Advocacy Group", "stance": "neutral"},
            {"name": "Industry Representatives", "type": "Industry Group", "stance": "neutral"},
        ],
        "labor": [
            {"name": "Labor Unions", "type": "Interest Group", "stance": "neutral"},
            {"name": "Business Groups", "type": "Industry Group", "stance": "neutral"},
        ],
        "gaming": [
            {"name": "Gaming Industry", "type": "Industry Group", "stance": "support"},
            {"name": "Anti-Gambling Advocates", "type": "Advocacy Group", "stance": "oppose"},
        ],
        "cannabis": [
            {"name": "Cannabis Industry", "type": "Industry Group", "stance": "support"},
            {"name": "Law Enforcement", "type": "Government Entity", "stance": "neutral"},
        ],
        "gun": [
            {"name": "Gun Rights Groups", "type": "Advocacy Group", "stance": "neutral"},
            {"name": "Gun Control Advocates", "type": "Advocacy Group", "stance": "neutral"},
        ],
        "immigration": [
            {"name": "Immigration Advocates", "type": "Advocacy Group", "stance": "neutral"},
            {"name": "Law Enforcement", "type": "Government Entity", "stance": "neutral"},
        ],
    }

    # Check for keyword matches and add relevant stakeholders
    added_types = set()
    for keyword, groups in stakeholder_map.items():
        if keyword in combined_text:
            for group in groups:
                group_key = f"{group['name']}_{group['type']}"
                if group_key not in added_types:
                    stakeholders.append(group)
                    added_types.add(group_key)

    return stakeholders[:12]  # Limit to 12 stakeholders


def prepare_dashboard_data(bill_id: int):
    """
    Fetch and prepare all data needed for the dashboard.

    Args:
        bill_id: LegiScan bill ID

    Returns:
        Dictionary of template variables, or None on error.
    """
    bill_data = lc.get_bill(bill_id)
    if not bill_data or "error" in bill_data:
        return None

    # Extract key fields
    bill_number = bill_data.get("bill_number", f"Bill_{bill_id}")
    state = bill_data.get("state", "US")
    title = bill_data.get("title", "Untitled Bill")
    description = bill_data.get("description", title)
    status_code = bill_data.get("status", 1)
    status_text = lc.status_label(status_code)
    session = bill_data.get("session", {})
    session_name = session.get("session_name", "") if isinstance(session, dict) else ""

    # Sponsors
    sponsors = bill_data.get("sponsors", [])
    primary_sponsor = sponsors[0].get("name", "Unknown") if sponsors else "Unknown"
    sponsor_party = sponsors[0].get("party", "") if sponsors else ""

    # Texts (versions)
    texts = bill_data.get("texts", [])
    version_count = len(texts)
    v1_size = texts[0].get("text_size", 0) if texts else 0
    latest_size = texts[-1].get("text_size", 0) if texts else 0
    growth = ((latest_size - v1_size) / v1_size * 100) if v1_size > 0 else 0

    # Votes (summary)
    votes = bill_data.get("votes", [])

    # Detailed vote data with individual legislator votes
    vote_details = get_vote_details(votes)

    # History
    history = bill_data.get("history", [])

    # URL
    legiscan_url = bill_data.get("url", "")

    # Key stakeholders
    stakeholders = identify_stakeholders(bill_data)

    return {
        "bill_id": bill_id,
        "bill_number": bill_number,
        "state": state,
        "title": title[:120] + "..." if len(title) > 120 else title,
        "description": description,
        "status_code": status_code,
        "status_text": status_text,
        "status_steps": get_status_steps(status_code),
        "session_name": session_name,
        "primary_sponsor": primary_sponsor,
        "sponsor_party": sponsor_party,
        "sponsors": sponsors,
        "texts": texts,
        "version_count": version_count,
        "v1_size": v1_size,
        "latest_size": latest_size,
        "growth": growth,
        "votes": votes,
        "vote_details": vote_details,
        "history": history,
        "legiscan_url": legiscan_url,
        "stakeholders": stakeholders,
        "report_date": date.today().strftime("%B %d, %Y"),
    }


# Store current bill_id for the app
current_bill_id = None


@app.route("/")
def dashboard():
    """Main dashboard view."""
    global current_bill_id

    # Check for bill_id in query params first
    bill_id = request.args.get("bill_id", type=int)
    if bill_id:
        current_bill_id = bill_id

    if not current_bill_id:
        return """
        <html>
        <head><title>Legislative Dashboard</title></head>
        <body style="font-family: system-ui; padding: 2rem; text-align: center;">
            <h1>Legislative Policy Dashboard</h1>
            <p>Enter a bill ID to view the dashboard:</p>
            <form action="/" method="GET" style="margin-top: 2rem;">
                <input type="number" name="bill_id" placeholder="Bill ID (e.g., 1423040)"
                       style="padding: 0.5rem 1rem; font-size: 1rem; width: 250px;">
                <button type="submit" style="padding: 0.5rem 1rem; font-size: 1rem;
                        background: #1E40AF; color: white; border: none; cursor: pointer;">
                    View Dashboard
                </button>
            </form>
        </body>
        </html>
        """

    data = prepare_dashboard_data(current_bill_id)
    if not data:
        return f"<h1>Error: Could not load bill {current_bill_id}</h1>", 404

    return render_template_string(DASHBOARD_TEMPLATE, **data)


@app.route("/api/bill/<int:bill_id>")
def api_bill(bill_id):
    """API endpoint to get bill data as JSON."""
    data = prepare_dashboard_data(bill_id)
    if not data:
        return jsonify({"error": f"Could not load bill {bill_id}"}), 404
    return jsonify(data)


def run_dashboard(bill_id: int = None, port: int = 5000, debug: bool = False):
    """
    Run the dashboard server.

    Args:
        bill_id: Initial bill ID to display
        port: Port to run the server on
        debug: Enable Flask debug mode
    """
    global current_bill_id
    current_bill_id = bill_id

    print(f"\n{'='*60}")
    print("  LEGISLATIVE POLICY DASHBOARD")
    print(f"{'='*60}")
    if bill_id:
        print(f"  Bill ID: {bill_id}")
    print(f"  URL: http://localhost:{port}")
    print(f"  Press Ctrl+C to stop")
    print(f"{'='*60}\n")

    app.run(host="0.0.0.0", port=port, debug=debug)


# ── CLI ENTRY POINT ──────────────────────────────────────────────────────────

def main():
    """Command-line interface for the dashboard."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python generate_dashboard.py <bill_id>       Start dashboard for a specific bill")
        print("  python generate_dashboard.py --port 8080     Change the port (default: 5000)")
        print("\nExamples:")
        print("  python generate_dashboard.py 1423040")
        print("  python generate_dashboard.py 1423040 --port 8080")
        sys.exit(1)

    bill_id = None
    port = 5000

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i].isdigit():
            bill_id = int(args[i])
            i += 1
        else:
            i += 1

    run_dashboard(bill_id=bill_id, port=port)


if __name__ == "__main__":
    main()
