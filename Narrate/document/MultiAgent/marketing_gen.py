import os
from datetime import datetime
from typing import List, Tuple, Union
import google.generativeai as genai
from dotenv import load_dotenv
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Frame, PageTemplate
import textwrap
import re
from fastapi.responses import FileResponse

from .marketing_structure import MarketingStrategy, MarketingSection, MarketingRequest
from .base_document_generator import BaseDocumentGenerator

load_dotenv()


def safe_get_text(response) -> str:
    """
    Safely extract text from a Gemini response without touching response.text,
    which can raise ValueError when no valid Part is returned.
    """
    try:
        if response and getattr(response, "candidates", None):
            cand0 = response.candidates[0]
            content = getattr(cand0, "content", None)
            parts = getattr(content, "parts", None) if content else None
            if parts:
                return "".join(
                    getattr(p, "text", "") for p in parts if hasattr(p, "text")
                ) or ""
    except Exception:
        # Swallow any unexpected schema variations and return empty string
        pass
    return ""


class MarketingStrategyGenerator(BaseDocumentGenerator):
    def __init__(self):
        super().__init__()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        self.configure_model()
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()
        
    def _add_custom_styles(self):
        # Adding custom styles to enhance aesthetics
        self.styles.add(ParagraphStyle(name="CHeading1", fontSize=40, alignment=1, textColor=colors.darkblue, fontName="Helvetica-Bold", leading=48))
        self.styles.add(ParagraphStyle(name="CHeading2", fontSize=20, alignment=0, textColor=colors.navy, fontName="Helvetica-Bold", leading=24))
        self.styles.add(ParagraphStyle(name="CHighNormal", fontSize=16, alignment=0, textColor=colors.black, fontName="Helvetica", spaceAfter=16))
        self.styles.add(ParagraphStyle(name="CNormal", fontSize=12, alignment=0, textColor=colors.gray, fontName="Helvetica", spaceAfter=12))
        self.styles.add(ParagraphStyle(name="CSubtitle", fontSize=14, alignment=1, textColor=colors.gray, fontName="Helvetica-Oblique"))
        self.styles.add(ParagraphStyle(name="CListItem", fontSize=12, bulletFontName="Helvetica", bulletFontSize=12, leftIndent=20, spaceAfter=6))
        
    def configure_model(self):
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel(self.gemini_model)
        
    def generate_pdf(self, title: str, request: MarketingRequest) -> dict:
        """
        Generate a complete marketing strategy PDF document and return both PDF and text content.
        """
        # Generate each section using specialized prompts
        strategy = MarketingStrategy(
            title=title,
            executive_summary=self._generate_executive_summary(request),
            market_analysis=self._generate_market_analysis(request),
            marketing_objectives=self._generate_marketing_objectives(request),
            target_audience=self._generate_target_audience(request),
            marketing_mix=self._generate_marketing_mix(request),
            digital_strategy=self._generate_digital_strategy(request),
            budget_timeline=self._generate_budget_timeline(request),
            implementation_plan=self._generate_implementation_plan(request),
            risk_analysis=self._generate_risk_analysis(request)
        )
        
        # Create text content dictionary
        text_content = {
            "title": title,
            "executive_summary": strategy.executive_summary,
            "market_analysis": strategy.market_analysis.content,
            "marketing_objectives": strategy.marketing_objectives.content,
            "target_audience": strategy.target_audience.content,
            "marketing_mix": strategy.marketing_mix.content,
            "digital_strategy": strategy.digital_strategy.content,
            "budget_timeline": strategy.budget_timeline.content,
            "implementation_plan": strategy.implementation_plan.content,
            "risk_analysis": strategy.risk_analysis.content
        }
        
        # Create PDF
        file_name = f"marketing_strategy_{title}_{datetime.now().strftime('%Y%m%d')}.pdf"
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
            ("Market Analysis", self.extract_headers_and_subpoints(strategy.market_analysis.content)),
            ("Marketing Objectives", self.extract_headers_and_subpoints(strategy.marketing_objectives.content)),
            ("Target Audience", self.extract_headers_and_subpoints(strategy.target_audience.content)),
            ("Marketing Mix", self.extract_headers_and_subpoints(strategy.marketing_mix.content)),
            ("Digital Strategy", self.extract_headers_and_subpoints(strategy.digital_strategy.content)),
            ("Budget & Timeline", self.extract_headers_and_subpoints(strategy.budget_timeline.content)),
            ("Implementation Plan", self.extract_headers_and_subpoints(strategy.implementation_plan.content)),
            ("Risk Analysis", self.extract_headers_and_subpoints(strategy.risk_analysis.content))
        ]
        
        for section_title, section_content in sections:
            self._add_single_column(elements, (section_title, section_content))
            elements.append(PageBreak())
            elements.append(Spacer(1, 20))
            
        document.build(elements)
        self.upload_file(file_name, file_path)
        
        return self.create_response(file_path, text_content)
        

    def _generate_executive_summary(self, request: MarketingRequest) -> str:
        prompt = f"""
        Create an executive summary for the marketing strategy with the following details:
        Title: {request.title}
        Objectives: {request.objectives}
        Strategic Context: {request.strategic_prompt}
        
        The executive summary should be concise but comprehensive, highlighting the key points of the marketing strategy.
        """
        response = self.model.generate_content(prompt)
        generated_text = safe_get_text(response)
        return generated_text
        
    def _generate_market_analysis(self, request: MarketingRequest) -> MarketingSection:
        target_market_context = f"\nTarget Market Information: {request.target_market}" if request.target_market else ""
        
        prompt = f"""
        Create a detailed market analysis section with the following subsections:
        1. Target Market Analysis
        2. Competitor Analysis
        3. Market Trends
        
        Based on the following context, identify and analyze:
        - Target market segments and their characteristics
        - Key competitors and their market positioning
        - Current market trends and future projections
        
        Context:
        Title: {request.title}
        Objectives: {request.objectives}
        Strategic Context: {request.strategic_prompt}{target_market_context}
        
        Provide a comprehensive analysis that includes:
        - Market size and growth potential
        - Competitive landscape with 3-5 key competitors
        - Emerging trends and opportunities
        - Market challenges and barriers to entry
        """
        response = self.model.generate_content(prompt)
        generated_text = safe_get_text(response)
        return MarketingSection(
            title="Market Analysis",
            content=generated_text,
            subsections=[
                MarketingSection(title="Target Market", content=""),
                MarketingSection(title="Competitor Analysis", content=""),
                MarketingSection(title="Market Trends", content="")
            ]
        )
        
    def _generate_marketing_objectives(self, request: MarketingRequest) -> MarketingSection:
        prompt = f"""
        Create detailed marketing objectives with the following subsections:
        1. Primary Goals
        2. KPIs and Metrics
        
        Context:
        Title: {request.title}
        Objectives: {request.objectives}
        Strategic Context: {request.strategic_prompt}
        """
        response = self.model.generate_content(prompt)
        generated_text = safe_get_text(response)
        return MarketingSection(
            title="Marketing Objectives",
            content=generated_text,
            subsections=[
                MarketingSection(title="Primary Goals", content=""),
                MarketingSection(title="KPIs and Metrics", content="")
            ]
        )
        
    def _generate_target_audience(self, request: MarketingRequest) -> MarketingSection:
        target_market_context = f"\nTarget Market Information: {request.target_market}" if request.target_market else ""
        
        prompt = f"""
        Create a detailed target audience analysis with the following subsections:
        1. Buyer Personas
        2. Customer Journey
        
        Based on the following context, develop:
        - Detailed buyer personas (2-3 key personas)
        - Complete customer journey mapping
        - Audience demographics and psychographics
        
        Context:
        Title: {request.title}
        Objectives: {request.objectives}
        Strategic Context: {request.strategic_prompt}{target_market_context}
        
        Include for each persona:
        - Demographics
        - Pain points and needs
        - Buying behavior
        - Preferred channels
        - Decision-making process
        
        If specific target market information is provided, ensure the personas align with these segments.
        """
        response = self.model.generate_content(prompt)
        generated_text = safe_get_text(response)
        return MarketingSection(
            title="Target Audience",
            content=generated_text,
            subsections=[
                MarketingSection(title="Buyer Personas", content=""),
                MarketingSection(title="Customer Journey", content="")
            ]
        )
        
    def _generate_marketing_mix(self, request: MarketingRequest) -> MarketingSection:
        prompt = f"""
        Create a detailed marketing mix (4Ps) analysis with the following subsections:
        1. Product Strategy
        2. Pricing Strategy
        3. Place/Distribution Strategy
        4. Promotion Strategy
        
        Based on the following context, develop:
        - Product positioning and value proposition
        - Pricing model and strategy
        - Distribution channels and partnerships
        - Promotional tactics and messaging
        
        Context:
        Title: {request.title}
        Objectives: {request.objectives}
        Strategic Context: {request.strategic_prompt}
        
        Include for each P:
        - Strategic approach
        - Implementation details
        - Success metrics
        - Competitive advantages
        """
        response = self.model.generate_content(prompt)
        generated_text = safe_get_text(response)
        return MarketingSection(
            title="Marketing Mix (4Ps)",
            content=generated_text,
            subsections=[
                MarketingSection(title="Product Strategy", content=""),
                MarketingSection(title="Pricing Strategy", content=""),
                MarketingSection(title="Place/Distribution Strategy", content=""),
                MarketingSection(title="Promotion Strategy", content="")
            ]
        )
        
    def _generate_digital_strategy(self, request: MarketingRequest) -> MarketingSection:
        prompt = f"""
        Create a detailed digital marketing strategy with the following subsections:
        1. Social Media Strategy
        2. Content Marketing Strategy
        3. SEO/SEM Strategy
        4. Email Marketing Strategy
        
        Based on the following context, develop:
        - Channel-specific strategies
        - Content calendar and themes
        - Performance metrics and KPIs
        - Integration across channels
        
        Context:
        Title: {request.title}
        Objectives: {request.objectives}
        Strategic Context: {request.strategic_prompt}
        
        Include for each channel:
        - Platform selection rationale
        - Content strategy
        - Engagement tactics
        - Measurement framework
        """
        response = self.model.generate_content(prompt)
        generated_text = safe_get_text(response)
        return MarketingSection(
            title="Digital Marketing Strategy",
            content=generated_text,
            subsections=[
                MarketingSection(title="Social Media Strategy", content=""),
                MarketingSection(title="Content Marketing Strategy", content=""),
                MarketingSection(title="SEO/SEM Strategy", content=""),
                MarketingSection(title="Email Marketing Strategy", content="")
            ]
        )
        
    def _generate_budget_timeline(self, request: MarketingRequest) -> MarketingSection:
        budget_context = f"\nBudget Constraints: {request.budget_constraints}" if request.budget_constraints else ""
        
        prompt = f"""
        Create a detailed budget and timeline plan with the following subsections:
        1. Budget Allocation
        2. Timeline and Milestones
        
        Based on the following context, develop:
        - A realistic budget allocation across different marketing activities
        - A detailed timeline with key milestones
        - Resource requirements and cost estimates
        
        Context:
        Title: {request.title}
        Objectives: {request.objectives}
        Strategic Context: {request.strategic_prompt}{budget_context}
        
        The plan should include:
        - 12-month budget breakdown
        - Quarterly milestones and deliverables
        - Resource allocation across different channels
        - ROI projections and success metrics
        
        If budget constraints are provided, ensure the plan aligns with these limitations while maximizing impact.
        """
        response = self.model.generate_content(prompt)
        generated_text = safe_get_text(response)
        return MarketingSection(
            title="Budget and Timeline",
            content=generated_text,
            subsections=[
                MarketingSection(title="Budget Allocation", content=""),
                MarketingSection(title="Timeline and Milestones", content="")
            ]
        )
        
    def _generate_implementation_plan(self, request: MarketingRequest) -> MarketingSection:
        prompt = f"""
        Create a detailed implementation plan with the following subsections:
        1. Action Items
        2. Resource Requirements
        3. Team Structure
        
        Based on the following context, develop:
        - Detailed action plan with timelines
        - Resource allocation and requirements
        - Team structure and responsibilities
        - Success metrics and milestones
        
        Context:
        Title: {request.title}
        Objectives: {request.objectives}
        Strategic Context: {request.strategic_prompt}
        
        Include:
        - 90-day action plan
        - Resource requirements by phase
        - Team roles and responsibilities
        - Performance tracking framework
        """
        response = self.model.generate_content(prompt)
        generated_text = safe_get_text(response)
        return MarketingSection(
            title="Implementation Plan",
            content=generated_text,
            subsections=[
                MarketingSection(title="Action Items", content=""),
                MarketingSection(title="Resource Requirements", content=""),
                MarketingSection(title="Team Structure", content="")
            ]
        )
        
    def _generate_risk_analysis(self, request: MarketingRequest) -> MarketingSection:
        prompt = f"""
        Create a detailed risk analysis with the following subsections:
        1. Potential Risks
        2. Mitigation Strategies
        
        Based on the following context, identify:
        - Market and competitive risks
        - Operational and resource risks
        - External and environmental risks
        - Mitigation strategies for each risk
        
        Context:
        Title: {request.title}
        Objectives: {request.objectives}
        Strategic Context: {request.strategic_prompt}
        
        Include for each risk:
        - Risk description and impact
        - Probability assessment
        - Mitigation strategy
        - Contingency plan
        """
        response = self.model.generate_content(prompt)
        generated_text = safe_get_text(response)
        return MarketingSection(
            title="Risk Analysis and Mitigation",
            content=generated_text,
            subsections=[
                MarketingSection(title="Potential Risks", content=""),
                MarketingSection(title="Mitigation Strategies", content="")
            ]
        )
