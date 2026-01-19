from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from typing import Dict, Any

import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def make_briefing_pdf(title: str, subtitle: str, summary: Dict[str, Any], highlights: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, title)

    y -= 20
    c.setFont("Helvetica", 11)
    c.drawString(50, y, subtitle)

    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Executive snapshot")

    y -= 18
    c.setFont("Helvetica", 10)
    lines = [
        f"Revenue: {summary.get('revenue', 0):,.0f}",
        f"Costs: {summary.get('total_cost', 0):,.0f}",
        f"Profit: {summary.get('profit', 0):,.0f}",
        f"Avg margin: {summary.get('margin', 0)*100:,.1f}%" if summary.get('margin') is not None else "Avg margin: n/a",
        f"Median cost/km: {summary.get('cost_per_km', 0):,.2f}",
        f"Median cost/hr: {summary.get('cost_per_hour', 0):,.2f}",
        f"Median cost/m3: {summary.get('cost_per_m3', 0):,.2f}",
        f"Total downtime (h): {summary.get('downtime_hours', 0):,.1f}",
    ]
    for ln in lines:
        c.drawString(60, y, ln)
        y -= 14

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Key highlights")
    y -= 18
    c.setFont("Helvetica", 10)
    for h in highlights[:10]:
        if y < 80:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 10)
        c.drawString(60, y, f"• {h}")
        y -= 14

    y -= 16
    c.setFont("Helvetica", 8)
    c.drawString(50, y, f"Generated: {datetime.now().isoformat(timespec='seconds')}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def make_zip_pack(files: Dict[str, bytes], meta: Dict[str, Any] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        if meta is not None:
            z.writestr("metadata.json", json.dumps(meta, indent=2))
        for name, content in files.items():
            z.writestr(name, content)
    buf.seek(0)
    return buf.read()
