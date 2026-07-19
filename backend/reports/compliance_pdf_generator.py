"""
compliance_pdf_generator.py  RegIntel AI V2
Compliance Assessment PDF Generator

Reads ONLY existing pipeline-generated artifacts:
  datasets/maps/<doc_id>.json
  datasets/verification_plans/<doc_id>.json
  datasets/compliance_decisions/<doc_id>_*.json  (latest)
  datasets/verification_results/<doc_id>.json    (if present)

Produces: datasets/compliance_reports/Compliance_Assessment_<doc_id>.pdf

SAFETY: completely read-only with respect to compliance data.
        Never writes to maps/, verification_plans/, or any other pipeline dir.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

C_NAVY       = colors.HexColor("#0f1f35")
C_TEAL       = colors.HexColor("#0d9488")
C_TEAL_LIGHT = colors.HexColor("#ccfbf1")
C_AMBER      = colors.HexColor("#d97706")
C_RED        = colors.HexColor("#dc2626")
C_GREEN      = colors.HexColor("#16a34a")
C_SLATE      = colors.HexColor("#475569")
C_SILVER     = colors.HexColor("#e2e8f0")
C_WHITE      = colors.white
C_ROW_ALT    = colors.HexColor("#f8fafc")

PAGE_W, PAGE_H = A4
MARGIN     = 1.8 * cm
CONTENT_W  = PAGE_W - 2 * MARGIN


def _style(name, **kw):
    return ParagraphStyle(name, **kw)


S_TITLE      = _style("rt",    fontSize=26, textColor=C_WHITE,      fontName="Helvetica-Bold",  alignment=TA_CENTER, spaceAfter=4)
S_SUBTITLE   = _style("rs",    fontSize=13, textColor=C_TEAL_LIGHT, fontName="Helvetica",       alignment=TA_CENTER, spaceAfter=6)
S_COVER_META = _style("rcm",   fontSize=10, textColor=colors.HexColor("#94a3b8"), fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4)
S_H1         = _style("rh1",   fontSize=16, textColor=C_NAVY,  fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
S_H2         = _style("rh2",   fontSize=13, textColor=C_TEAL,  fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=5)
S_H3         = _style("rh3",   fontSize=11, textColor=C_SLATE, fontName="Helvetica-Bold", spaceBefore=8,  spaceAfter=4)
S_BODY       = _style("rb",    fontSize=9,  textColor=C_SLATE, fontName="Helvetica",      spaceAfter=4,   leading=14)
S_LABEL      = _style("rl",    fontSize=8,  textColor=C_SLATE, fontName="Helvetica-Bold", spaceAfter=2)
S_MAPID      = _style("rm",    fontSize=9,  textColor=C_TEAL,  fontName="Courier-Bold",   spaceAfter=2)
S_TH         = _style("rth",   fontSize=8,  textColor=C_WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER)
S_TD         = _style("rtd",   fontSize=8,  textColor=C_SLATE, fontName="Helvetica",      leading=11)


def _p(text, style=None):
    return Paragraph(str(text or ""), style or S_BODY)


def _hr(color=None, thickness=0.8):
    return HRFlowable(width="100%", thickness=thickness, color=color or C_TEAL, spaceAfter=4, spaceBefore=4)


def _kv_table(pairs, col_widths=None):
    data = [[_p(k, S_LABEL), _p(v, S_BODY)] for k, v in pairs]
    cw   = col_widths or [4*cm, CONTENT_W - 4*cm]
    t    = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, C_SILVER),
    ]))
    return t


def _pill_color(val):
    v = (val or "").upper()
    if v in ("CRITICAL", "HIGH", "NON_COMPLIANT", "FAIL", "BLOCKER"): return C_RED
    if v in ("MEDIUM", "PARTIALLY_COMPLIANT", "ESCALATE"):             return C_AMBER
    if v in ("LOW", "COMPLIANT", "PASS", "GO"):                        return C_GREEN
    return C_SLATE


def _std_table(headers, rows, col_widths):
    h_row = [_p(h, S_TH) for h in headers]
    data  = [h_row] + [[_p(str(c or ""), S_TD) for c in row] for row in rows]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  C_NAVY),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
        ("GRID",         (0, 0), (-1, -1), 0.3, C_SILVER),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _pie_chart(data, title, size=5.5*cm):
    palette = [C_TEAL, C_AMBER, C_RED, C_GREEN, C_SLATE,
               colors.HexColor("#7c3aed"), colors.HexColor("#0284c7")]
    labels  = list(data.keys())
    values  = [float(v) for v in data.values()]
    if not any(values):
        return None
    d   = Drawing(size + 5*cm, size + 0.9*cm)
    pie = Pie()
    pie.x = 0.5*cm; pie.y = 0.5*cm
    pie.width = size; pie.height = size
    pie.data   = values
    pie.labels = [f"{l} ({v:.0f})" for l, v in zip(labels, values)]
    pie.sideLabels = True
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = C_WHITE
    for i, c in enumerate(palette[:len(labels)]):
        pie.slices[i].fillColor   = c
        pie.slices[i].labelRadius = 1.25
    d.add(pie)
    d.add(String(0, size + 0.65*cm, title, fontSize=9, fontName="Helvetica-Bold", fillColor=C_NAVY))
    return d


def _on_cover_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(C_TEAL)
    canvas.rect(0, PAGE_H - 1*cm, PAGE_W, 1*cm, fill=1, stroke=0)
    canvas.rect(0, 0, PAGE_W, 0.7*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(PAGE_W/2, 0.25*cm, "CONFIDENTIAL  RegIntel AI V2  Compliance Assessment Report")
    canvas.restoreState()


def _on_body_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_TEAL)
    canvas.rect(0, PAGE_H - 0.8*cm, PAGE_W, 0.8*cm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, PAGE_H - 0.55*cm, "RegIntel AI V2  Compliance Assessment Report")
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.55*cm, "CONFIDENTIAL")
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, 0, PAGE_W, 0.6*cm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(PAGE_W/2, 0.2*cm, f"Page {doc.page}")
    canvas.restoreState()


def _load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Failed to read {path}: {e}")
        return None


def _latest_decision(decisions_dir, doc_id):
    candidates = sorted(decisions_dir.glob(f"{doc_id}_*.json"), reverse=True)
    for p in candidates:
        d = _load_json(p)
        if d:
            return d
    return None


def generate_compliance_pdf(document_id: str, project_root: Path) -> Path:
    """Generate a professional compliance assessment PDF. Returns the output path."""
    maps_file     = project_root / "datasets" / "maps"                 / f"{document_id}.json"
    plans_file    = project_root / "datasets" / "verification_plans"   / f"{document_id}.json"
    decisions_dir = project_root / "datasets" / "compliance_decisions"
    out_dir       = project_root / "datasets" / "compliance_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path      = out_dir / f"Compliance_Assessment_{document_id}.pdf"

    if not maps_file.exists():
        raise FileNotFoundError(f"MAP file not found: {maps_file}")

    maps_data  = _load_json(maps_file)  or {}
    plans_data = _load_json(plans_file) or {}
    decision   = _latest_decision(decisions_dir, document_id) or {}

    maps_list  = maps_data.get("maps", [])
    plans_list = plans_data.get("verification_plans", [])
    plans_by_id = {p["plan_id"]: p for p in plans_list}

    def _plan_for_map(m):
        ctrl_id = m.get("control_id", "")
        if "_ctrl_req" in ctrl_id:
            parts = ctrl_id.split("_ctrl_req")
            if len(parts) == 2:
                doc_part = parts[0]
                req_num  = parts[1].split("_")[0] if "_" in parts[1] else parts[1]
                pid = f"CVP_VR_{doc_part}_req{req_num}"
                return plans_by_id.get(pid)
        return None

    ts_now       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_tasks  = sum(len(m.get("tasks", [])) for m in maps_list)
    total_checks = sum(len(p.get("checks", [])) for p in plans_list)
    total_effort = sum((m.get("estimated_total_effort_hours") or 0) for m in maps_list)
    depts_set    = set(m.get("owner_department", "") for m in maps_list)
    prio_counter = Counter(m.get("priority", "UNKNOWN") for m in maps_list)
    crit_counter = Counter(m.get("criticality", "UNKNOWN") for m in maps_list)
    dept_counter = Counter(m.get("owner_department", "Unknown") for m in maps_list)
    domain_ctr   = Counter(d for m in maps_list for d in (m.get("compliance_domain") or []))
    risk_ctr     = Counter(d for m in maps_list for d in (m.get("risk_domain") or []))
    cap_ctr      = Counter(p.get("business_capability", "") for p in plans_list if p.get("business_capability"))
    auto_pcts    = [p.get("automation_percentage") or 0 for p in plans_list]
    avg_auto     = (sum(auto_pcts) / len(auto_pcts)) if auto_pcts else 0.0
    doc_verdict  = decision.get("overall_document_verdict", "PENDING")
    comp_pct     = decision.get("compliance_percentage") or 0

    # ── Document setup ────────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.2*cm, bottomMargin=1.0*cm,
        title=f"Compliance Assessment  {document_id}",
        author="RegIntel AI V2",
    )
    cover_frame = Frame(0, 0, PAGE_W, PAGE_H, leftPadding=2*cm, rightPadding=2*cm,
                        topPadding=6*cm, bottomPadding=1.2*cm, id="cover")
    body_frame  = Frame(MARGIN, 0.7*cm, CONTENT_W, PAGE_H - 1.7*cm, id="body")
    doc.addPageTemplates([
        PageTemplate("cover", frames=[cover_frame], onPage=_on_cover_page),
        PageTemplate("body",  frames=[body_frame],  onPage=_on_body_page),
    ])

    story = []

    # ── COVER PAGE ────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 2.5*cm),
        _p("RegIntel AI  V2.0", S_SUBTITLE),
        Spacer(1, 0.4*cm),
        _p("Compliance Assessment Report", S_TITLE),
        Spacer(1, 1.0*cm),
        _p(document_id, _style("ci", fontSize=18, textColor=C_TEAL, fontName="Courier-Bold",
                                alignment=TA_CENTER, spaceAfter=6)),
        Spacer(1, 1.5*cm),
        _p(f"Overall Verdict: <b>{doc_verdict}</b>",
           _style("cv", fontSize=13, textColor=C_WHITE, fontName="Helvetica", alignment=TA_CENTER, spaceAfter=6)),
    ]
    if comp_pct:
        story.append(_p(f"Compliance Score: {comp_pct:.1f}%",
                         _style("cs", fontSize=11, textColor=C_TEAL_LIGHT, fontName="Helvetica",
                                alignment=TA_CENTER, spaceAfter=4)))
    story += [
        Spacer(1, 2.0*cm),
        _p(f"Generated: {ts_now}", S_COVER_META),
        _p("CONFIDENTIAL  FOR AUTHORISED RECIPIENTS ONLY", S_COVER_META),
        NextPageTemplate("body"),
        PageBreak(),
    ]

    # ── EXECUTIVE SUMMARY ─────────────────────────────────────────────────────
    story += [_p("Executive Summary", S_H1), _hr(), Spacer(1, 0.2*cm)]
    story.append(_kv_table([
        ("Document ID",              document_id),
        ("Assessment Generated",     ts_now),
        ("Overall Verdict",          doc_verdict),
        ("Compliance Score",         f"{comp_pct:.1f}%" if comp_pct else "N/A"),
        ("Number of MAPs",           str(len(maps_list))),
        ("Verification Plans",       str(len(plans_list))),
        ("Implementation Tasks",     str(total_tasks)),
        ("Verification Checks",      str(total_checks)),
        ("Departments Involved",     ", ".join(sorted(depts_set)) or ""),
        ("Est. Total Effort",        f"{total_effort:.0f} hours" if total_effort else "N/A"),
        ("Avg. Automation Coverage", f"{avg_auto:.1f}%"),
    ]))

    exec_sum = decision.get("execution_summary", {})
    if exec_sum:
        story += [Spacer(1, 0.3*cm), _p("Verification Execution Summary", S_H2)]
        story.append(_kv_table([
            ("Machine Passed",  str(exec_sum.get("machine_passed",  0))),
            ("Machine Failed",  str(exec_sum.get("machine_failed",  0))),
            ("Machine Errored", str(exec_sum.get("machine_errored", 0))),
            ("Manual Pending",  str(exec_sum.get("manual_pending",  0))),
        ]))

    # ── DOCUMENT OVERVIEW ─────────────────────────────────────────────────────
    story += [PageBreak(), _p("Document Overview", S_H1), _hr(), Spacer(1, 0.2*cm)]

    def _top(ctr, n=8):
        return ", ".join(f"{k} ({v})" for k, v in ctr.most_common(n)) or "N/A"

    story.append(_kv_table([
        ("Compliance Domains",      _top(domain_ctr)),
        ("Risk Domains",            _top(risk_ctr)),
        ("Business Capabilities",   _top(cap_ctr)),
        ("Priority Distribution",   _top(prio_counter)),
        ("Criticality Distribution",_top(crit_counter)),
    ]))
    story.append(Spacer(1, 0.5*cm))

    charts = []
    if dept_counter:
        c = _pie_chart(dict(dept_counter.most_common(8)), "MAPs by Department")
        if c: charts.append(c)
    if prio_counter:
        c = _pie_chart(dict(prio_counter), "Priority Distribution")
        if c: charts.append(c)
    if crit_counter:
        c = _pie_chart(dict(crit_counter), "Criticality Distribution")
        if c: charts.append(c)
    if auto_pcts:
        bkt = {"0%": 0, "1-25%": 0, "26-50%": 0, "51-75%": 0, "76-100%": 0}
        for v in auto_pcts:
            if v == 0: bkt["0%"] += 1
            elif v <= 25: bkt["1-25%"] += 1
            elif v <= 50: bkt["26-50%"] += 1
            elif v <= 75: bkt["51-75%"] += 1
            else: bkt["76-100%"] += 1
        bkt = {k: v for k, v in bkt.items() if v}
        c = _pie_chart(bkt, "Automation Coverage Distribution")
        if c: charts.append(c)

    for i in range(0, len(charts), 2):
        row = charts[i:i+2]
        cw  = [CONTENT_W/2] * len(row)
        t   = Table([row], colWidths=cw)
        t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))

    # ── PIPELINE SUMMARY ──────────────────────────────────────────────────────
    story += [PageBreak(), _p("Pipeline Summary", S_H1), _hr(), Spacer(1, 0.2*cm)]
    p_rows = []
    for m in maps_list:
        plan = _plan_for_map(m)
        p_rows.append([
            m.get("map_id", ""),
            m.get("owner_department", ""),
            m.get("priority", ""),
            ", ".join(m.get("compliance_domain") or []) or "",
            str(len(m.get("tasks", []))),
            str(len(plan.get("checks", [])) if plan else 0),
            f"{plan.get('automation_percentage') or 0:.0f}%" if plan else "",
            m.get("status", ""),
        ])
    story.append(_std_table(
        ["MAP ID", "Department", "Priority", "Domain(s)", "Tasks", "Checks", "Auto%", "Status"],
        p_rows,
        [3.8*cm, 2.2*cm, 1.5*cm, 3.5*cm, 1*cm, 1*cm, 1.2*cm, 1.8*cm],
    ))

    # ── PER-MAP SECTIONS ──────────────────────────────────────────────────────
    for idx, m in enumerate(maps_list):
        story.append(PageBreak())
        map_id    = m.get("map_id", "")
        objective = m.get("objective", "")
        effort    = m.get("estimated_total_effort_hours")
        tasks     = m.get("tasks", [])
        plan      = _plan_for_map(m)

        story += [
            KeepTogether([
                _p(f"MAP {idx+1} of {len(maps_list)}", S_H2),
                _p(map_id, S_MAPID),
                _hr(C_TEAL, 1.2),
            ]),
        ]
        story.append(_kv_table([
            ("Title",             m.get("title", "")),
            ("Control ID",        m.get("control_id", "")),
            ("Owner Department",  m.get("owner_department", "")),
            ("Priority",          m.get("priority", "")),
            ("Criticality",       m.get("criticality", "")),
            ("Status",            m.get("status", "")),
            ("Compliance Domain", ", ".join(m.get("compliance_domain") or [])),
            ("Risk Domain",       ", ".join(m.get("risk_domain") or [])),
            ("Est. Effort",       f"{effort} hours" if effort else "N/A"),
        ], col_widths=[4.2*cm, CONTENT_W - 4.2*cm]))

        if objective:
            story += [Spacer(1, 0.2*cm), _p("Objective", S_H3), _p(objective)]

        if tasks:
            story += [Spacer(1, 0.4*cm), _p(f"Implementation Tasks ({len(tasks)})", S_H3)]
            t_rows = []
            for t in tasks:
                deps = ", ".join(str(d).split("_T")[-1] for d in (t.get("dependencies") or []))
                t_rows.append([
                    str(t.get("task_number", "")),
                    t.get("title", ""),
                    t.get("assigned_department", ""),
                    t.get("priority", ""),
                    t.get("deliverable", ""),
                    str(t.get("estimated_effort_hours", "")),
                    deps or "",
                ])
            story.append(_std_table(
                ["#", "Task", "Department", "Priority", "Deliverable", "Hours", "Deps"],
                t_rows,
                [0.6*cm, 4.8*cm, 2.2*cm, 1.3*cm, 2.8*cm, 1*cm, 2.1*cm],
            ))

        if plan:
            story += [Spacer(1, 0.4*cm), _p("Verification Plan", S_H3)]
            story.append(_kv_table([
                ("Plan ID",            plan.get("plan_id", "")),
                ("Control Name",       plan.get("control_name", "")),
                ("Strategy",           plan.get("verification_strategy", "")),
                ("Automation %",       f"{plan.get('automation_percentage') or 0:.1f}%"),
                ("Total Checks",       str(plan.get("total_checks", 0))),
                ("Mandatory Checks",   str(plan.get("mandatory_checks", 0))),
                ("Machine Verifiable", str(plan.get("machine_verifiable_checks", 0))),
                ("Est. Manual Effort", f"{plan.get('estimated_manual_effort_hours') or 0:.1f} hours"),
                ("Pass Condition",     plan.get("pass_condition", "")),
                ("Final Decision Rule",plan.get("final_decision_rule", "")),
            ], col_widths=[4.2*cm, CONTENT_W - 4.2*cm]))

            checks = plan.get("checks", [])
            if checks:
                story += [Spacer(1, 0.3*cm), _p(f"Verification Checks ({len(checks)})", S_H3)]
                c_rows = []
                for ck in checks:
                    exp = str(ck.get("expected_result", ""))
                    if len(exp) > 40: exp = exp[:40] + "..."
                    c_rows.append([
                        str(ck.get("sequence_number", "")),
                        ck.get("title", ""),
                        ck.get("verification_platform", ""),
                        ck.get("verification_mechanism", ""),
                        "Yes" if ck.get("machine_verifiable") else "No",
                        "Yes" if ck.get("mandatory") else "No",
                        exp,
                        ck.get("failure_impact", ""),
                    ])
                story.append(_std_table(
                    ["#", "Check", "Platform", "Mechanism", "Auto", "Mandatory", "Expected", "Impact"],
                    c_rows,
                    [0.6*cm, 4.2*cm, 1.8*cm, 1.8*cm, 0.8*cm, 1.2*cm, 1.8*cm, 1.3*cm],
                ))

        if plan and decision:
            pv = next((v for v in decision.get("plan_verdicts", [])
                       if v.get("plan_id") == plan.get("plan_id")), None)
            if pv:
                story += [Spacer(1, 0.3*cm), _p("Compliance Decision", S_H3)]
                story.append(_p(f"Verdict: <b>{pv.get('verdict', 'PENDING')}</b>"))
                story.append(_p(f"Rationale: {pv.get('rationale', 'N/A')}"))

    failed_blks = decision.get("failed_blocker_list", [])
    if failed_blks:
        story += [PageBreak(), _p("Appendix: Failed Blocker Checks", S_H1), _hr(C_RED)]
        story.append(_p(f"{len(failed_blks)} check(s) classified as BLOCKER failures contributed to non-compliance."))
        story.append(Spacer(1, 0.3*cm))
        story.append(_std_table(["#", "Check ID"],
                                [[str(i+1), b] for i, b in enumerate(failed_blks)],
                                [1*cm, CONTENT_W - 1*cm]))

    doc.build(story)
    logger.info(f"PDF generated: {out_path}")
    return out_path
