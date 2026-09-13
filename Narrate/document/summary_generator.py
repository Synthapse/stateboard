import google.generativeai as genai
from fastapi import FastAPI
import uuid
import time
import os
from dotenv import load_dotenv
import re
from fastapi.responses import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus.frames import Frame
from reportlab.platypus import PageTemplate
from fastapi.responses import FileResponse
import datetime

from integration.GCPClientBucket import StorageClientWrapper

app = FastAPI()

load_dotenv()


# Gemini limits:
# 15 RPM (requests per minute)
# 1 million TPM (tokens per minute)
# 1.5K RPD (requests per day)

class SummaryDocumentGenerator:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-pro")

    def configure_model(self):
        genai.configure(api_key=self.gemini_api_key)
        return genai.GenerativeModel(self.gemini_model), genai.GenerativeModel('gemini-pro-vision')

    def generate_summary(self, doc_prompts):
        text_model, image_model = self.configure_model()

        for prompt in doc_prompts:
            title = prompt["title"]

            # Step 1: Generate Summary Overview
            response = text_model.generate_content(prompt["strategic_prompt"])
            summary_overview = response.text[:300]  # Shortened initial overview

            print(f"Overview: {summary_overview}")

            # Step 2: Extract Key Themes
            print("Extracting Key Themes...")
            key_themes = self.extract_key_themes(title, summary_overview, text_model)
            print("Key Themes Extracted.")

            # Step 3: Identify Important Insights
            print("Identifying Important Insights...")
            insights = self.extract_insights(title, summary_overview, text_model)
            print("Insights Identified.")

            # Step 4: Determine Actionable Takeaways
            print("Generating Actionable Takeaways...")
            takeaways = self.extract_takeaways(title, summary_overview, text_model)
            print("Takeaways Generated.")

            # Step 5: Gather Supporting Evidence (Optional)
            print("Extracting Supporting Evidence...")
            supporting_evidence = self.extract_evidence(title, summary_overview, text_model)
            print("Supporting Evidence Extracted.")

            # Organize into structured output
            summary_content = {
                "overview": summary_overview,
                "key_themes": key_themes,
                "important_insights": insights,
                "actionable_takeaways": takeaways,
                "supporting_evidence": supporting_evidence
            }

            # Generate final summary PDF
            doc = self.generate_pdf(title, summary_content)
            return doc

    def extract_key_themes(self, title, summary_overview, text_model):
        prompt = f"""
            This is a summary of a document related to {title}:
            "{summary_overview}"

            Identify the key themes or topics discussed in the document.
            Return a list of main themes without excessive details.
        """

        response = text_model.generate_content(prompt)
        return self.parse_list(response.text)  # Convert to structured list

    def extract_insights(self, title, summary_overview, text_model):
        prompt = f"""
            This is a summary of a document related to {title}:
            "{summary_overview}"

            Extract the most important insights from the document.
            Focus on key learnings, statistics, or conclusions.
        """

        response = text_model.generate_content(prompt)
        return self.parse_list(response.text)  # Convert to structured list

    def extract_takeaways(self, title, summary_overview, text_model):
        prompt = f"""
            This is a summary of a document related to {title}:
            "{summary_overview}"

            Provide the most actionable takeaways from the document.
            These should be recommendations or practical applications.
        """

        response = text_model.generate_content(prompt)
        return self.parse_list(response.text)  # Convert to structured list

    def extract_evidence(self, title, summary_overview, text_model):
        prompt = f"""
            This is a summary of a document related to {title}:
            "{summary_overview}"

            Identify any supporting evidence or references mentioned in the document.
            This can include key statistics, studies, quotes, or expert opinions.
        """

        response = text_model.generate_content(prompt)
        return self.parse_list(response.text)  # Convert to structured list

    def parse_list(self, text):
        # Splitting into list format (Assuming AI returns comma or newline-separated values)
        items = [line.strip("-• ") for line in text.split("\n") if line.strip()]
        return items

    def add_title_page(self, canvas, doc):
        # Get page dimensions
        width, height = A4
        
        # Set navy blue background
        canvas.setFillColor(colors.green)
        canvas.rect(0, 0, width, height, fill=True, stroke=False)

        # Set text properties
        canvas.setFillColor(colors.white)  # White text for contrast
        canvas.setFont("Helvetica-Bold", 24)

        # Add Title (Centered at the top)
        title = doc.title
        canvas.drawCentredString(width / 2, height - 100, title)

        # Add Date (Below title)
        canvas.setFont("Helvetica", 14)
        current_date = datetime.now().strftime("%B %d, %Y")  # Format: February 11, 2025
        canvas.drawCentredString(width / 2, height - 140, f"Date: {current_date}")

        # Add Generation Info (Below date)
        canvas.setFont("Helvetica-Oblique", 12)
        canvas.drawCentredString(width / 2, height - 170, "Generated by Authentic Scope / Gemini")



    def generate_pdf(self, title, summary_content):
        # Set up the PDF document
        file_name = f"{title.replace(' ', '_')}.pdf"
        file_path = os.path.join("pdfs", file_name)
        os.makedirs("pdfs", exist_ok=True)
        
        # Create the PDF
        document = SimpleDocTemplate(file_path, pagesize=A4)
        document.title = title

        width, height = A4
        frame = Frame(0, 0, width, height - 100, id='normal')  # Leave space for the title page

        # Create the custom page template
        custom_page_template = PageTemplate(id='title', onPage=self.add_title_page, frames=[frame])
        document.addPageTemplates([custom_page_template])

        # Create a list to hold the elements to be added to the PDF
        elements = []
        styles = getSampleStyleSheet()

        #12.02.2025
        # Possibility to improve document aesthetic

        # Title Page (if you need a title page, customize this function)
        self.add_title_page(elements, title)

        # Overview Section
        elements.append(PageBreak())
        elements.append(Paragraph("1. Overview:", styles['Heading2']))
        elements.append(Paragraph(summary_content["overview"], styles['Normal']))

        # Key Themes Section
        elements.append(PageBreak())
        elements.append(Paragraph("2. Key Themes:", styles['Heading2']))
        for theme in summary_content["key_themes"]:
            elements.append(Paragraph(f"- {theme}", styles['Normal']))

        # Important Insights Section
        elements.append(PageBreak())
        elements.append(Paragraph("3. Important Insights:", styles['Heading2']))
        for insight in summary_content["important_insights"]:
            elements.append(Paragraph(f"- {insight}", styles['Normal']))

        # Actionable Takeaways Section
        elements.append(PageBreak())
        elements.append(Paragraph("4. Actionable Takeaways:", styles['Heading2']))
        for takeaway in summary_content["actionable_takeaways"]:
            elements.append(Paragraph(f"- {takeaway}", styles['Normal']))

        # Supporting Evidence Section
        elements.append(PageBreak())
        elements.append(Paragraph("5. Supporting Evidence:", styles['Heading2']))
        for evidence in summary_content["supporting_evidence"]:
            elements.append(Paragraph(f"- {evidence}", styles['Normal']))

        # Build PDF
        document.build(elements)

        storage_client_wrapper = StorageClientWrapper()
        storage_client_wrapper.upload_file(title, file_path)

        return FileResponse(file_path, media_type="application/pdf", filename=file_name)