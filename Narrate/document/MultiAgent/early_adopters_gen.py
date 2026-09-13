import os
from datetime import datetime
from typing import List, Tuple, Union
import google.generativeai as genai
from dotenv import load_dotenv
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, PageBreak, Frame, PageTemplate, Spacer, Paragraph
import textwrap
from fastapi.responses import FileResponse

from .early_adopters_structure import EarlyAdopterStrategy, EarlyAdopterSection, EarlyAdopterRequest
from .base_document_generator import BaseDocumentGenerator

load_dotenv()

class EarlyAdopterGenerator(BaseDocumentGenerator):
    def __init__(self):
        super().__init__()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        self.configure_model()

    def configure_model(self):
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel(self.gemini_model)
        
    def generate_pdf(self, title: str, request: EarlyAdopterRequest) -> dict:
        """
        Generate a complete early adopter program strategy PDF document and return both PDF and text content.
        """
        # Generate each section using specialized prompts
        strategy = EarlyAdopterStrategy(
            title=title,
            executive_summary=self._generate_executive_summary(request),
            ideal_customer_profile=self._generate_ideal_customer_profile(request),
            value_proposition=self._generate_value_proposition(request),
            program_benefits=self._generate_program_benefits(request),
            onboarding_process=self._generate_onboarding_process(request),
            feedback_mechanisms=self._generate_feedback_mechanisms(request),
            success_metrics=self._generate_success_metrics(request),
            engagement_plan=self._generate_engagement_plan(request),
            resource_allocation=self._generate_resource_allocation(request)
        )
        
        # Create text content dictionary
        text_content = {
            "title": title,
            "executive_summary": strategy.executive_summary,
            "ideal_customer_profile": strategy.ideal_customer_profile.content,
            "value_proposition": strategy.value_proposition.content,
            "program_benefits": strategy.program_benefits.content,
            "onboarding_process": strategy.onboarding_process.content,
            "feedback_mechanisms": strategy.feedback_mechanisms.content,
            "success_metrics": strategy.success_metrics.content,
            "engagement_plan": strategy.engagement_plan.content,
            "resource_allocation": strategy.resource_allocation.content
        }
        
        # Create PDF
        file_name = f"early_adopter_strategy_{title}_{datetime.now().strftime('%Y%m%d')}.pdf"
        file_path = os.path.join("pdfs", file_name)
        os.makedirs("pdfs", exist_ok=True)
        
        document = SimpleDocTemplate(file_path, pagesize=A4)
        document.title = title
        
        width, height = A4
        frame = Frame(0, 0, width, height - 100, id='normal')
        
        custom_page_template = PageTemplate(id='title', onPage=self.add_title_page, frames=[frame])
        document.addPageTemplates([custom_page_template])
        
        elements = []
        
        # Add executive summary
        elements.append(PageBreak())
        self._add_single_column(elements, ("Executive Summary", strategy.executive_summary))
        elements.append(Spacer(1, 20))
        
        # Add each section
        sections = [
            ("Ideal Customer Profile", self.extract_headers_and_subpoints(strategy.ideal_customer_profile.content)),
            ("Value Proposition", self.extract_headers_and_subpoints(strategy.value_proposition.content)),
            ("Program Benefits", self.extract_headers_and_subpoints(strategy.program_benefits.content)),
            ("Onboarding Process", self.extract_headers_and_subpoints(strategy.onboarding_process.content)),
            ("Feedback Mechanisms", self.extract_headers_and_subpoints(strategy.feedback_mechanisms.content)),
            ("Success Metrics", self.extract_headers_and_subpoints(strategy.success_metrics.content)),
            ("Engagement Plan", self.extract_headers_and_subpoints(strategy.engagement_plan.content)),
            ("Resource Allocation", self.extract_headers_and_subpoints(strategy.resource_allocation.content))
        ]
        
        for section_title, section_content in sections:
            self._add_single_column(elements, (section_title, section_content))
            elements.append(PageBreak())
            elements.append(Spacer(1, 20))
            
        document.build(elements)
        self.upload_file(file_name, file_path)
        
        return self.create_response(file_path, text_content)

    def _generate_executive_summary(self, request: EarlyAdopterRequest) -> str:
        prompt = f"""
        Create an executive summary for the early adopter program with the following details:
        Title: {request.title}
        Product Description: {request.product_description}
        Target Audience: {request.target_audience}
        Strategic Goals: {request.strategic_goals if request.strategic_goals else 'Not specified'}
        
        The executive summary should highlight:
        1. Program objectives and expected outcomes
        2. Key benefits for early adopters
        3. Timeline and resource requirements
        4. Success criteria
        """
        response = self.model.generate_content(prompt)
        return response.text

    def _generate_ideal_customer_profile(self, request: EarlyAdopterRequest) -> EarlyAdopterSection:
        prompt = f"""
        Create a detailed ideal customer profile for early adopters based on:
        Product: {request.product_description}
        Target Audience: {request.target_audience}

        Include:
        1. Demographic characteristics
        2. Psychographic profile
        3. Pain points and needs
        4. Technology adoption patterns
        5. Decision-making criteria
        """
        response = self.model.generate_content(prompt)
        return EarlyAdopterSection(
            title="Ideal Customer Profile",
            content=response.text
        )

    def _generate_value_proposition(self, request: EarlyAdopterRequest) -> EarlyAdopterSection:
        prompt = f"""
        Create a compelling value proposition for early adopters of:
        Product: {request.product_description}

        Include:
        1. Unique benefits for early adopters
        2. Exclusive features or access
        3. Competitive advantages
        4. Long-term value potential
        """
        response = self.model.generate_content(prompt)
        return EarlyAdopterSection(
            title="Value Proposition",
            content=response.text
        )

    def _generate_program_benefits(self, request: EarlyAdopterRequest) -> EarlyAdopterSection:
        prompt = f"""
        Detail the benefits of joining the early adopter program for:
        Product: {request.product_description}

        Include:
        1. Exclusive features and privileges
        2. Priority support and access
        3. Influence on product development
        4. Special pricing or terms
        5. Recognition and visibility opportunities
        """
        response = self.model.generate_content(prompt)
        return EarlyAdopterSection(
            title="Program Benefits",
            content=response.text
        )

    def _generate_onboarding_process(self, request: EarlyAdopterRequest) -> EarlyAdopterSection:
        prompt = f"""
        Design a smooth onboarding process for early adopters of:
        Product: {request.product_description}

        Include:
        1. Application and selection criteria
        2. Initial setup and training
        3. Support mechanisms
        4. Timeline and milestones
        5. Success criteria
        """
        response = self.model.generate_content(prompt)
        return EarlyAdopterSection(
            title="Onboarding Process",
            content=response.text
        )

    def _generate_feedback_mechanisms(self, request: EarlyAdopterRequest) -> EarlyAdopterSection:
        prompt = f"""
        Design feedback collection mechanisms for the early adopter program:
        Product: {request.product_description}

        Include:
        1. Feedback channels and tools
        2. Regular check-ins and reviews
        3. Usage analytics and metrics
        4. Feedback implementation process
        5. Recognition for valuable feedback
        """
        response = self.model.generate_content(prompt)
        return EarlyAdopterSection(
            title="Feedback Mechanisms",
            content=response.text
        )

    def _generate_success_metrics(self, request: EarlyAdopterRequest) -> EarlyAdopterSection:
        goals_context = f"\nStrategic Goals: {request.strategic_goals}" if request.strategic_goals else ""
        
        prompt = f"""
        Define success metrics for the early adopter program:
        Product: {request.product_description}{goals_context}

        Include:
        1. Key Performance Indicators (KPIs)
        2. Adoption and usage metrics
        3. Feedback quality metrics
        4. Customer satisfaction measures
        5. Business impact metrics
        """
        response = self.model.generate_content(prompt)
        return EarlyAdopterSection(
            title="Success Metrics",
            content=response.text
        )

    def _generate_engagement_plan(self, request: EarlyAdopterRequest) -> EarlyAdopterSection:
        prompt = f"""
        Create an engagement plan for early adopters:
        Product: {request.product_description}

        Include:
        1. Communication channels and frequency
        2. Community building activities
        3. Recognition and rewards program
        4. Exclusive events and workshops
        5. Content and resource sharing
        """
        response = self.model.generate_content(prompt)
        return EarlyAdopterSection(
            title="Engagement Plan",
            content=response.text
        )

    def _generate_resource_allocation(self, request: EarlyAdopterRequest) -> EarlyAdopterSection:
        resources_context = f"\nResource Constraints: {request.resource_constraints}" if request.resource_constraints else ""
        
        prompt = f"""
        Plan resource allocation for the early adopter program:
        Product: {request.product_description}{resources_context}

        Include:
        1. Team roles and responsibilities
        2. Budget allocation
        3. Technology and tools required
        4. Timeline and milestones
        5. Scalability considerations
        """
        response = self.model.generate_content(prompt)
        return EarlyAdopterSection(
            title="Resource Allocation",
            content=response.text
        ) 