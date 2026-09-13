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

from .brief_doc_structure import BriefStrategy, BriefSection, BriefRequest
from .base_document_generator import BaseDocumentGenerator

load_dotenv()


class BriefDocGenerator(BaseDocumentGenerator):
    def __init__(self):
        super().__init__()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        self.configure_model()

    def configure_model(self):
        genai.configure(api_key=self.gemini_api_key)
        # Using a different model than EarlyAdopterGenerator
        self.model = genai.GenerativeModel(self.gemini_model)

    def generate_pdf(self, title: str, request: BriefRequest) -> dict:
        """
        Generate a complete brief document PDF and return both PDF and text content.
        """
        # Generate each section using specialized prompts
        strategy = BriefStrategy(
            title=title,
            executive_summary=self._generate_executive_summary(request),
            project_overview=self._generate_project_overview(request),
            objectives=self._generate_objectives(request),
            scope=self._generate_scope(request),
            deliverables=self._generate_deliverables(request),
            timeline=self._generate_timeline(request),
            resources=self._generate_resources(request),
            risks=self._generate_risks(request),
            success_criteria=self._generate_success_criteria(request)
        )

        # Create text content dictionary
        text_content = {
            "title": title,
            "executive_summary": strategy.executive_summary,
            "project_overview": strategy.project_overview.content,
            "objectives": strategy.objectives.content,
            "scope": strategy.scope.content,
            "deliverables": strategy.deliverables.content,
            "timeline": strategy.timeline.content,
            "resources": strategy.resources.content,
            "risks": strategy.risks.content,
            "success_criteria": strategy.success_criteria.content
        }

        # Create PDF
        file_name = f"brief_doc_{title}_{datetime.now().strftime('%Y%m%d')}.pdf"
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
            ("Project Overview", self.extract_headers_and_subpoints(strategy.project_overview.content)),
            ("Objectives", self.extract_headers_and_subpoints(strategy.objectives.content)),
            ("Scope", self.extract_headers_and_subpoints(strategy.scope.content)),
            ("Deliverables", self.extract_headers_and_subpoints(strategy.deliverables.content)),
            ("Timeline", self.extract_headers_and_subpoints(strategy.timeline.content)),
            ("Resources", self.extract_headers_and_subpoints(strategy.resources.content)),
            ("Risks", self.extract_headers_and_subpoints(strategy.risks.content)),
            ("Success Criteria", self.extract_headers_and_subpoints(strategy.success_criteria.content))
        ]

        for section_title, section_content in sections:
            self._add_single_column(elements, (section_title, section_content))
            elements.append(PageBreak())
            elements.append(Spacer(1, 20))

        document.build(elements)
        self.upload_file(file_name, file_path)

        return self.create_response(file_path, text_content)

    def _generate_executive_summary(self, request: BriefRequest) -> str:
        prompt = f"""
        Create an executive summary for the campaign with the following details:
        Name: {request.name}
        Description: {request.description}
        Target Audience: {request.targetAudience}
        Brand Values: {request.brandValues if request.brandValues else 'Not specified'}
        Budget: {request.budget if request.budget else 'Not specified'}
        Duration: {request.duration if request.duration else 'Not specified'}
        Goals: {', '.join(request.goals) if request.goals else 'Not specified'}
        
        The executive summary should highlight:
        1. Campaign objectives and expected outcomes
        2. Key deliverables and timeline
        3. Resource requirements and budget
        4. Success criteria based on goals
        """
        response = self.model.generate_content(prompt)
        return response.text

    def _generate_project_overview(self, request: BriefRequest) -> BriefSection:
        prompt = f"""
        Create a detailed campaign overview based on:
        Campaign: {request.description}
        Target Audience: {request.targetAudience}
        Category: {request.category if request.category else 'Not specified'}
        Content Type: {request.contentType if request.contentType else 'Not specified'}
        Platforms: {', '.join(request.platforms) if request.platforms else 'Not specified'}

        Include:
        1. Campaign background and context
        2. Key stakeholders and target audience
        3. Campaign scope overview
        4. High-level timeline and duration
        5. Expected outcomes and goals
        """
        response = self.model.generate_content(prompt)
        return BriefSection(
            title="Campaign Overview",
            content=response.text
        )

    def _generate_objectives(self, request: BriefRequest) -> BriefSection:
        prompt = f"""
        Define clear campaign objectives for:
        Campaign: {request.description}
        Goals: {', '.join(request.goals) if request.goals else 'Not specified'}
        Brand Values: {request.brandValues if request.brandValues else 'Not specified'}

        Include:
        1. Primary objectives aligned with goals
        2. Secondary objectives
        3. Success metrics
        4. Alignment with brand values
        5. Measurable outcomes
        """
        response = self.model.generate_content(prompt)
        return BriefSection(
            title="Objectives",
            content=response.text
        )

    def _generate_scope(self, request: BriefRequest) -> BriefSection:
        prompt = f"""
        Define the campaign scope for:
        Campaign: {request.description}
        Requirements: {request.requirements if request.requirements else 'Not specified'}
        Platforms: {', '.join(request.platforms) if request.platforms else 'Not specified'}

        Include:
        1. In-scope items and deliverables
        2. Out-of-scope items
        3. Scope boundaries
        4. Platform-specific requirements
        5. Constraints and limitations
        """
        response = self.model.generate_content(prompt)
        return BriefSection(
            title="Scope",
            content=response.text
        )

    def _generate_deliverables(self, request: BriefRequest) -> BriefSection:
        prompt = f"""
        List and describe campaign deliverables for:
        Campaign: {request.description}
        Deliverables: {request.deliverables if request.deliverables else 'Not specified'}
        Content Type: {request.contentType if request.contentType else 'Not specified'}
        Platforms: {', '.join(request.platforms) if request.platforms else 'Not specified'}

        Include:
        1. Key deliverables by platform
        2. Deliverable descriptions and specifications
        3. Quality criteria
        4. Acceptance criteria
        5. Delivery timeline
        """
        response = self.model.generate_content(prompt)
        return BriefSection(
            title="Deliverables",
            content=response.text
        )

    def _generate_timeline(self, request: BriefRequest) -> BriefSection:
        prompt = f"""
        Create a campaign timeline for:
        Campaign: {request.description}
        Duration: {request.duration if request.duration else 'Not specified'}

        Include:
        1. Major milestones
        2. Key activities by platform
        3. Content production schedule
        4. Critical path
        5. Resource allocation timeline
        """
        response = self.model.generate_content(prompt)
        return BriefSection(
            title="Timeline",
            content=response.text
        )

    def _generate_resources(self, request: BriefRequest) -> BriefSection:
        prompt = f"""
        Define resource requirements for:
        Campaign: {request.description}
        Budget: {request.budget if request.budget else 'Not specified'}
        Platforms: {', '.join(request.platforms) if request.platforms else 'Not specified'}

        Include:
        1. Human resources and team structure
        2. Technical resources and tools
        3. Budget allocation by platform
        4. External resources and vendors
        5. Resource allocation plan
        """
        response = self.model.generate_content(prompt)
        return BriefSection(
            title="Resources",
            content=response.text
        )

    def _generate_risks(self, request: BriefRequest) -> BriefSection:
        prompt = f"""
        Identify and analyze campaign risks for:
        Campaign: {request.description}
        Platforms: {', '.join(request.platforms) if request.platforms else 'Not specified'}
        Budget: {request.budget if request.budget else 'Not specified'}

        Include:
        1. Platform-specific risks
        2. Risk assessment and impact
        3. Mitigation strategies
        4. Contingency plans
        5. Risk monitoring approach
        """
        response = self.model.generate_content(prompt)
        return BriefSection(
            title="Risks",
            content=response.text
        )

    def _generate_success_criteria(self, request: BriefRequest) -> BriefSection:
        prompt = f"""
        Define success criteria for:
        Campaign: {request.description}
        Goals: {', '.join(request.goals) if request.goals else 'Not specified'}
        Platforms: {', '.join(request.platforms) if request.platforms else 'Not specified'}

        Include:
        1. Platform-specific KPIs
        2. Success metrics by goal
        3. Quality standards
        4. Stakeholder satisfaction criteria
        5. Campaign completion criteria
        """
        response = self.model.generate_content(prompt)
        return BriefSection(
            title="Success Criteria",
            content=response.text
        )
