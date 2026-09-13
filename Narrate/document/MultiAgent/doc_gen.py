from datetime import datetime
from typing import List, Tuple, Union

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Frame, PageTemplate
import os
import re
import textwrap
from fastapi.responses import FileResponse

from document.MultiAgent.structure import SystemRequest
from integration.GCPClientBucket import StorageClientWrapper


class MultiAgentPdfGenerator:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()


    # Define design layout 2-3 styles (with colors)
    def _add_custom_styles(self):
        # Adding custom styles to enhance aesthetics
        self.styles.add(ParagraphStyle(name="CHeading1", fontSize=40, alignment=1, textColor=colors.darkblue, fontName="Helvetica-Bold", leading=48))
        self.styles.add(ParagraphStyle(name="CHeading2", fontSize=20, alignment=0, textColor=colors.navy, fontName="Helvetica-Bold", leading=24))
        self.styles.add(ParagraphStyle(name="CHighNormal", fontSize=16, alignment=0, textColor=colors.black, fontName="Helvetica", spaceAfter=16))
        self.styles.add(ParagraphStyle(name="CNormal", fontSize=12, alignment=0, textColor=colors.gray, fontName="Helvetica", spaceAfter=12))
        self.styles.add(ParagraphStyle(name="CSubtitle", fontSize=14, alignment=1, textColor=colors.gray, fontName="Helvetica-Oblique"))
        self.styles.add(ParagraphStyle(name="CListItem", fontSize=12, bulletFontName="Helvetica", bulletFontSize=12, leftIndent=20, spaceAfter=6))


    def generate_pdf(self, title, agents_summary: SystemRequest, layout_type="two_column"):


        file_name = f"{title.replace(' ', '_')}.pdf"
        file_path = os.path.join("pdfs", file_name)
        os.makedirs("pdfs", exist_ok=True)

        document = SimpleDocTemplate(file_path, pagesize=A4)
        document.title = title

        width, height = A4
        frame = Frame(0, 0, width, height - 100, id='normal')  # Leave space for the title page

        custom_page_template = PageTemplate(id='title', onPage=self.add_title_page, frames=[frame])
        document.addPageTemplates([custom_page_template])
        elements = []
        layout_type = "two_column"
        
        # 1page print ->


        # Improve after MVP

        network_agent = agents_summary.networkAgent
        energy_agent = agents_summary.energyAgent
        cyber_security_agent = agents_summary.cyberSecurityAgent

        network_agent_title = f"Network Agent: {network_agent.agentId}"
        energy_agent_title = f"Energy Agent: {energy_agent.agentId}"
        cyber_security_agent_title = f"Cyber Security Agent: {cyber_security_agent.agentId}"

        network_agent_content = self.extract_headers_and_subpoints(network_agent.recommendation)
        energy_agent_content = self.extract_headers_and_subpoints(energy_agent.recommendation)
        cyber_security_agent_content = self.extract_headers_and_subpoints(cyber_security_agent.recommendation)

        self._add_single_column(elements, (network_agent_title, network_agent_content))
        self._add_single_column(elements, (energy_agent_title, energy_agent_content))
        self._add_single_column(elements, (cyber_security_agent_title, cyber_security_agent_content))

        document.build(elements)
        storage_client_wrapper = StorageClientWrapper()
        storage_client_wrapper.upload_file(title, file_path)

        return FileResponse(file_path, media_type="application/pdf", filename=file_name)

    def extract_headers_and_subpoints(self, text: str) -> List[Tuple[str, List[Tuple[str, str]]]]:
        """
        Parses a structured text input and extracts headers with subpoints.
        Returns a list of tuples, where each tuple consists of a header
        and a list of subpoints (title, description pairs).
        """
        if not isinstance(text, str):
            raise ValueError("Input text must be a string")

        sections = []
        current_header = None
        subpoints = []

        lines = text.strip().split("\n")

        header_pattern = re.compile(r"^(?:\*\*|\d+\.|[IVXLCDM]+\.)\s*(.+?):?$")  # Matches "I.", "1.", "**Header:**"
        subpoint_pattern = re.compile(r"^\*\s*(.+?):\s*(.*)")  # Matches "* Subpoint: Description"

        for line in lines:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            header_match = header_pattern.match(line)
            subpoint_match = subpoint_pattern.match(line)

            if header_match:
                # Save previous section
                if current_header and subpoints:
                    sections.append((current_header, subpoints))

                current_header = header_match.group(1).strip()
                subpoints = []

            elif subpoint_match:
                sub_title = subpoint_match.group(1).strip()
                sub_desc = subpoint_match.group(2).strip()
                subpoints.append((sub_title, sub_desc))

        # Save the last section
        if current_header and subpoints:
            sections.append((current_header, subpoints))

        return sections

    def add_title_page(self, canvas, doc):
        # Get page dimensions
        width, height = A4

        # Set navy blue background
        canvas.setFillColor(HexColor("#263D48"))
        canvas.rect(0, 0, width, height, fill=True, stroke=False)

        # Set text properties
        canvas.setFillColor(colors.white)  # White text for contrast
        canvas.setFont("Helvetica-Bold", 24)

        # Add Title (Centered at the top)
        title = doc.title
        max_width = 80  # Adjust based on font size and page width
        wrapped_title = textwrap.wrap(title, width=max_width)  # Break into lines

        # Start drawing each line from the top, moving downward for each line
        y_position = height - 100
        for line in wrapped_title:
            canvas.drawCentredString(width / 2, y_position, line)
            y_position -= 20  # Adjust line spacin

        # Add Date (Below title)
        canvas.setFont("Helvetica", 14)
        current_date = datetime.now().strftime("%B %d, %Y")  # Format: February 11, 2025
        canvas.drawCentredString(width / 2, height - 140, f"Date: {current_date}")

        # Add Generation Info (Below date)
        canvas.setFont("Helvetica-Oblique", 12)
        canvas.drawCentredString(width / 2, height - 170, "Generated by Authentic Scope / Gemini")

    def _add_single_column(self, elements, content_data: Tuple[str, Union[str, List[Tuple[str, List[Tuple[str, str]]]]]]) -> None:
        """
        Adds structured content into a list of ReportLab elements.
        Supports both simple strings and parsed hierarchical content.
        """
        styles = getSampleStyleSheet()

        if not isinstance(content_data, tuple) or len(content_data) != 2:
            raise ValueError("content_data must be a tuple containing a main title and content")

        main_title, content = content_data
        elements.append(Paragraph(f"<b>{main_title}</b>", styles["Title"]))
        elements.append(Spacer(1, 12))

        if isinstance(content, str):  # Simple text
            elements.append(Paragraph(content, styles["Normal"]))
            elements.append(Spacer(1, 6))

        elif isinstance(content, list):  # Structured sections
            for section in content:
                if isinstance(section, tuple) and len(section) == 2:
                    sub_title, sub_content = section
                    elements.append(Paragraph(f"<b>{sub_title}</b>", styles["Heading2"]))
                    elements.append(Spacer(1, 6))
                    if isinstance(sub_content, str):
                        elements.append(Paragraph(sub_content, styles["Normal"]))
                    elif isinstance(sub_content, list):
                        for item in sub_content:

                            if isinstance(item, tuple) and len(item) == 2:

                                i1 = item[0].replace("*", "")
                                i2 = item[1].replace("*", "")

                                elements.append(Paragraph(f"<b>{i1}</b>", styles["Normal"]))
                                elements.append(Paragraph(f"- {i2}", styles["Normal"]))
                            else:

                                i1 = item.replace("*", "")
                                elements.append(Paragraph(f"- {i1}", styles["Normal"]))
                                elements.append(Spacer(1, 4))

    def _add_two_column(self, elements, content_data: List[Tuple[str, str]]):
        """Creates a two-column layout with titles and descriptions."""
        styles = getSampleStyleSheet()
        table_data = []

        # Ensure content_data is not empty
        if not content_data:
            print("Warning: content_data is empty. Skipping table creation.")
            return  # Prevent further execution

        for title, description in content_data:
            title_paragraph = Paragraph(f"<b>{title}</b>", styles["Heading2"])
            description_paragraph = Paragraph(description, styles["Normal"])
            table_data.append([title_paragraph, description_paragraph])

        # Ensure at least one row exists before creating the table
        if not table_data:
            print("Warning: No valid data to create a table.")
            return

        table = Table(table_data, colWidths=[200, 300])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))

        elements.append(table)

    def _add_three_column(self, elements, content_data):
        """Creates a three-column layout: Title, Description, Additional Info."""
        styles = getSampleStyleSheet()
        table_data = []

        for title, description, extra_info in content_data:
            title_paragraph = Paragraph(f"<b>{title}</b>", styles["Heading2"])
            description_paragraph = Paragraph(description, styles["Normal"])

            # Handle list case by joining with line breaks
            if isinstance(extra_info, list):
                extra_text = "<br/>".join([f"• {item}" for item in extra_info])
            else:
                extra_text = extra_info  # Keep as is if it's a string

            extra_paragraph = Paragraph(extra_text, styles["Normal"])
            table_data.append([title_paragraph, description_paragraph, extra_paragraph])

        table = Table(table_data, colWidths=[120, 220, 200])  # Adjust column sizes
        table.hAlign = 'CENTER'  # Align table to the center
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))

        elements.append(table)

    def _add_table(self, elements, content_data):
        """Creates a table layout where all data is aligned in rows and columns with proper text wrapping."""
        styles = getSampleStyleSheet()

        table_data = [[Paragraph("<b>Objectives</b>", styles["Heading2"]),
                       Paragraph("<b>SubPoints</b>", styles["Heading2"])]]

        for title, description in content_data:
            title_paragraph = Paragraph(title, styles["Normal"])
            description_paragraph = Paragraph(description, styles["Normal"])  # Wraps text
            table_data.append([title_paragraph, description_paragraph])

        table = Table(table_data, colWidths=[200, 300])  # Adjust column widths

        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1), 'ON'),  # Ensures text wraps
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))

        elements.append(table)
