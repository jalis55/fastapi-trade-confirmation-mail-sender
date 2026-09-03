#!/usr/bin/env python3
"""
Generate a Trade Confirmation Note (Summary) PDF from JSON data.

Usage:
    from app.services.pdf_service import generate_trade_confirmation

    data = { ... }   # see SAMPLE_DATA in the live app for the expected shape
    generate_trade_confirmation(data, output_file="Trade_Confirmation.pdf")
    # The generated PDF is saved inside the "<REPORT_OUTPUT_DIR>/<trading_date>/" folder.
"""

from datetime import datetime
import json
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.services.dir_service import get_report_output_dir, set_report_output_dir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_number(value, decimals=2, use_comma=True):
    """Format number; optionally with thousand separators."""
    if not isinstance(value, (int, float)):
        return str(value)
    if use_comma:
        return f"{value:,.{decimals}f}"
    return f"{value:.{decimals}f}"


def create_styles():
    """Create custom paragraph styles used by the report."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CompanyName",
        fontName="Helvetica-Bold",
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="BranchInfo",
        fontName="Helvetica",
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="ClientCopy",
        fontName="Helvetica",
        fontSize=9,
        alignment=TA_RIGHT,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="ClientInfo",
        fontName="Helvetica",
        fontSize=9,
        alignment=TA_LEFT,
        spaceAfter=2,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name="IntroText",
        fontName="Helvetica",
        fontSize=9,
        alignment=TA_LEFT,
        spaceAfter=8,
        spaceBefore=6,
    ))
    styles.add(ParagraphStyle(
        name="Agreement",
        fontName="Helvetica",
        fontSize=9,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name="SignatureLabel",
        fontName="Helvetica",
        fontSize=9,
        alignment=TA_CENTER,
        spaceBefore=4,
    ))
    styles.add(ParagraphStyle(
        name="Footer",
        fontName="Helvetica",
        fontSize=8,
        alignment=TA_LEFT,
        textColor=colors.grey,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8,
        alignment=TA_CENTER,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=8,
        alignment=TA_CENTER,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name="TableCellLeft",
        fontName="Helvetica",
        fontSize=8,
        alignment=TA_LEFT,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name="TableCellRight",
        fontName="Helvetica",
        fontSize=8,
        alignment=TA_RIGHT,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name="TotalLabel",
        fontName="Helvetica-Bold",
        fontSize=8,
        alignment=TA_CENTER,
        leading=10,
    ))
    return styles


def build_transaction_table(transactions, styles):
    """
    Build a transaction table matching the original layout:
    - Market / Trans. Type / Exchange span all instrument rows (merged cells)
    - Each instrument is its own row
    - Total row at the bottom
    """
    if not transactions:
        return None

    n = len(transactions)

    # Header row
    header = [
        Paragraph("Market", styles["TableHeader"]),
        Paragraph("Trans. Type", styles["TableHeader"]),
        Paragraph("Exchange", styles["TableHeader"]),
        Paragraph("Instrument<br/>Name", styles["TableHeader"]),
        Paragraph("Total<br/>Qty.", styles["TableHeader"]),
        Paragraph("Avg. Rate", styles["TableHeader"]),
        Paragraph("Amount", styles["TableHeader"]),
        Paragraph("Commission", styles["TableHeader"]),
        Paragraph("Balance", styles["TableHeader"]),
    ]

    data = [header]

    total_amount = 0.0
    total_commission = 0.0
    total_balance = 0.0

    # Use values from the first transaction for the merged columns
    first = transactions[0]
    market_text = str(first.get("market", ""))
    trans_type_text = str(first.get("trans_type", ""))
    exchange_text = str(first.get("exchange", ""))

    for i, tx in enumerate(transactions):
        total_amount += float(tx.get("amount", 0))
        total_commission += float(tx.get("commission", 0))
        total_balance += float(tx.get("balance", 0))

        # Only put text in the first data row; SPAN will merge the cells
        if i == 0:
            market_cell = Paragraph(market_text, styles["TableCell"])
            trans_cell = Paragraph(trans_type_text, styles["TableCell"])
            exchange_cell = Paragraph(exchange_text, styles["TableCell"])
        else:
            market_cell = Paragraph("", styles["TableCell"])
            trans_cell = Paragraph("", styles["TableCell"])
            exchange_cell = Paragraph("", styles["TableCell"])

        row = [
            market_cell,
            trans_cell,
            exchange_cell,
            Paragraph(str(tx.get("instrument", "")), styles["TableCellLeft"]),
            Paragraph(format_number(tx.get("qty", 0), 0), styles["TableCellRight"]),
            Paragraph(format_number(tx.get("avg_rate", 0)), styles["TableCellRight"]),
            Paragraph(format_number(tx.get("amount", 0)), styles["TableCellRight"]),
            Paragraph(format_number(tx.get("commission", 0)), styles["TableCellRight"]),
            # Balance on detail rows often shown without comma in the original
            Paragraph(format_number(tx.get("balance", 0), use_comma=False), styles["TableCellRight"]),
        ]
        data.append(row)

    # Total row — empty Market / Trans / Exchange, "Total" under Instrument
    total_row = [
        Paragraph("", styles["TableCell"]),
        Paragraph("", styles["TableCell"]),
        Paragraph("", styles["TableCell"]),
        Paragraph("<b>Total</b>", styles["TotalLabel"]),
        Paragraph("", styles["TableCell"]),
        Paragraph("", styles["TableCell"]),
        Paragraph(f"<b>{format_number(total_amount)}</b>", styles["TableCellRight"]),
        Paragraph(f"<b>{format_number(total_commission)}</b>", styles["TableCellRight"]),
        Paragraph(f"<b>{format_number(total_balance)}</b>", styles["TableCellRight"]),
    ]
    data.append(total_row)

    col_widths = [48, 58, 50, 72, 48, 55, 72, 62, 68]

    table = Table(data, colWidths=col_widths)

    style_commands = [
        # Header
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.93, 0.93, 0.93)),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),

        # Full grid
        ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),

        # Total row background
        ("BACKGROUND", (0, -1), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
        ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
    ]

    # Merge Market / Trans. Type / Exchange across all instrument rows
    # (rows 1 .. n inclusive; row 0 is header, row n+1 is total)
    if n >= 1:
        style_commands.append(("SPAN", (0, 1), (0, n)))
        style_commands.append(("SPAN", (1, 1), (1, n)))
        style_commands.append(("SPAN", (2, 1), (2, n)))
        # Center the merged text vertically
        style_commands.append(("VALIGN", (0, 1), (2, n), "MIDDLE"))
        style_commands.append(("ALIGN", (0, 1), (2, n), "CENTER"))

    table.setStyle(TableStyle(style_commands))
    return table


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_trade_confirmation(data, output_file="Trade_Confirmation.pdf"):

    if isinstance(data, str):
        data = json.loads(data)

    if not isinstance(data, dict):
        raise TypeError("data must be a dict or a JSON string")

    # company_name = data.get("company_name", "Meenhar Securities Limited.")
    # branch_location = data.get("branch_location", "")
    # branch_name = data.get("branch_name", "")

    company_name = "ALAM Securities Limited"
    branch_location = "499,Motijhil"
    branch_name = "Head Office"
    client_code = data.get("client_code", "")
    client_name = data.get("client_name", "")
    bo_id = data.get("bo_id", "")
    trading_date = data.get("trading_date", "")
    buy_transactions = data.get("buy_transactions", []) or []
    sell_transactions = data.get("sell_transactions", []) or []
    opening_balance = data.get("opening_balance", 0)
    closing_balance = data.get("closing_balance", 0)

    styles = create_styles()

    # Resolve the output directory. In the normal report run,
    # ``dir_service.set_report_output_dir`` has already been called (once, before
    # the client loop) and cached the date-specific folder — so this is just a
    # cheap cached read. If it hasn't been primed (e.g. this function is called
    # standalone), delegate to ``dir_service`` so all path/mkdir logic lives in
    # one place.
    output_dir = get_report_output_dir()
    if output_dir is None:
        output_dir = set_report_output_dir(str(trading_date).strip() or "undated")

    output_file = os.path.join(output_dir, os.path.basename(output_file))

    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    story = []

    # ---- Header ----
    story.append(Paragraph(company_name, styles["CompanyName"]))
    if branch_location:
        story.append(Paragraph(branch_location, styles["BranchInfo"]))
    if branch_name:
        story.append(Paragraph(f"Branch: {branch_name}", styles["BranchInfo"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Trade Confirmation Note (Summary)", styles["ReportTitle"]))
    story.append(Paragraph("Client's Copy", styles["ClientCopy"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=8))

    # ---- Client Info ----
    client_info_data = [
        [
            Paragraph(f"<b>Client Code</b> : {client_code}", styles["ClientInfo"]),
            Paragraph(f"<b>Name</b> : {client_name}", styles["ClientInfo"]),
        ],
        [
            Paragraph(f"<b>BO ID</b> : {bo_id}", styles["ClientInfo"]),
            Paragraph("", styles["ClientInfo"]),
        ],
        [
            Paragraph(f"<b>Trading Date</b> : {trading_date}", styles["ClientInfo"]),
            Paragraph("", styles["ClientInfo"]),
        ],
    ]
    client_table = Table(client_info_data, colWidths=[260, 260])
    client_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 6))

    # Intro text
    story.append(Paragraph(
        "With reference to your order no. as stated date above, "
        "We have purchased / sold the following Instruments",
        styles["IntroText"],
    ))

    # ---- BUY Table ----
    if buy_transactions:
        tbl = build_transaction_table(buy_transactions, styles)
        if tbl:
            story.append(tbl)
            story.append(Spacer(1, 10))

    # ---- SELL Table ----
    if sell_transactions:
        tbl = build_transaction_table(sell_transactions, styles)
        if tbl:
            story.append(tbl)
            story.append(Spacer(1, 12))
# ---- Balances ----
    balance_data = [
        [
            Paragraph("<b>Opening Balance(Tk.)</b> :", styles["ClientInfo"]),
            Paragraph(format_number(opening_balance), styles["ClientInfo"]),
        ],
        [
            Paragraph("<b>Closing Balance(Tk.)</b> :", styles["ClientInfo"]),
            Paragraph(format_number(closing_balance), styles["ClientInfo"]),
        ],
    ]
    balance_table = Table(balance_data, colWidths=[140, 120])
    balance_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(balance_table)

    # Agreement
    story.append(Paragraph(
        "I agree that the figures in this Confirmation Report are accurate as per my orders.",
        styles["Agreement"],
    ))
    story.append(Spacer(1, 30))

    # ---- Signatures ----
    sig_line = "______________________________"
    sig_data = [
        [
            Paragraph(sig_line, styles["SignatureLabel"]),
            Paragraph(sig_line, styles["SignatureLabel"]),
        ],
        [
            Paragraph("Client's Signature", styles["SignatureLabel"]),
            Paragraph(f"For {company_name}", styles["SignatureLabel"]),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[250, 250])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(sig_table)

    # Footer
    story.append(Spacer(1, 40))
    printed_on = datetime.now().strftime("%b %d, %Y %I:%M %p")
    footer_data = [[
        Paragraph(f"Printed on:{printed_on}", styles["Footer"]),
        Paragraph("Page 1 of 1", styles["Footer"]),
    ]]
    footer_table = Table(footer_data, colWidths=[350, 150])
    footer_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(footer_table)

    doc.build(story)
    return output_file