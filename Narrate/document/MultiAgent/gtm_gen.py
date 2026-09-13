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

from .gtm_structure import GTMStrategy, GTMSection, GTMRequest
from .base_document_generator import BaseDocumentGenerator

load_dotenv()

class GTMGenerator(BaseDocumentGenerator):
    def __init__(self):
        super().__init__()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        self.configure_model()

    def configure_model(self):
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel(self.gemini_model)

    def _generate_competitive_landscape(self, request: GTMRequest) -> str:
        """Auto-generate competitive landscape analysis based on product and market info."""
        prompt = f"""
        Analyze the competitive landscape for:
        Product: {request.product_description}
        Target Market: {request.target_market}

        Provide a comprehensive competitive analysis including:
        1. Direct competitors
        2. Indirect competitors
        3. Market leaders and their positions
        4. Key competitive advantages and weaknesses
        5. Market dynamics and trends
        """
        response = self.model.generate_content(prompt)
        return response.text

    def _generate_unique_value_prop(self, request: GTMRequest, competitive_landscape: str) -> str:
        """Auto-generate unique value proposition based on product, market, and competitive info."""
        prompt = f"""
        Create a compelling unique value proposition for:
        Product: {request.product_description}
        Target Market: {request.target_market}
        
        Consider the competitive landscape:
        {competitive_landscape}

        Define:
        1. Core differentiators
        2. Unique benefits and advantages
        3. Customer pain points addressed
        4. Value creation mechanisms
        5. Competitive advantages
        """
        response = self.model.generate_content(prompt)
        return response.text

    def _generate_existing_channels(self, request: GTMRequest, target_segments: str) -> str:
        """Auto-generate potential distribution channels based on product and target segments."""
        prompt = f"""
        Identify optimal distribution channels for:
        Product: {request.product_description}
        Target Market: {request.target_market}

        Consider the target segments:
        {target_segments}

        Include:
        1. Primary distribution channels
        2. Secondary channels and partnerships
        3. Channel effectiveness analysis
        4. Channel coverage assessment
        5. Integration opportunities
        """
        response = self.model.generate_content(prompt)
        return response.text
        
    def generate_pdf(self, title: str, request: GTMRequest) -> dict:
        """
        Generate a complete Go-To-Market strategy PDF document and return both PDF and text content.
        """
        # First generate the foundational analyses
        competitive_landscape = self._generate_competitive_landscape(request)
        target_segments_content = self._generate_target_segments(request)
        unique_value_prop = self._generate_unique_value_prop(request, competitive_landscape)
        existing_channels = self._generate_existing_channels(request, target_segments_content.content)
        
        # Generate each section using specialized prompts and the auto-generated content
        strategy = GTMStrategy(
            title=title,
            executive_summary=self._generate_executive_summary(request, competitive_landscape, unique_value_prop),
            market_analysis=self._generate_market_analysis(request, competitive_landscape),
            target_segments=target_segments_content,
            positioning_strategy=self._generate_positioning_strategy(request, competitive_landscape, unique_value_prop),
            product_strategy=self._generate_product_strategy(request),
            pricing_strategy=self._generate_pricing_strategy(request, competitive_landscape),
            distribution_strategy=self._generate_distribution_strategy(request, existing_channels),
            marketing_plan=self._generate_marketing_plan(request),
            sales_strategy=self._generate_sales_strategy(request),
            customer_success=self._generate_customer_success(request),
            timeline_milestones=self._generate_timeline_milestones(request),
            budget_forecast=self._generate_budget_forecast(request),
            risk_mitigation=self._generate_risk_mitigation(request, competitive_landscape)
        )
        
        # Create text content dictionary
        text_content = {
            "title": title,
            "executive_summary": strategy.executive_summary,
            "market_analysis": strategy.market_analysis.content,
            "target_segments": strategy.target_segments.content,
            "positioning_strategy": strategy.positioning_strategy.content,
            "product_strategy": strategy.product_strategy.content,
            "pricing_strategy": strategy.pricing_strategy.content,
            "distribution_strategy": strategy.distribution_strategy.content,
            "marketing_plan": strategy.marketing_plan.content,
            "sales_strategy": strategy.sales_strategy.content,
            "customer_success": strategy.customer_success.content,
            "timeline_milestones": strategy.timeline_milestones.content,
            "budget_forecast": strategy.budget_forecast.content,
            "risk_mitigation": strategy.risk_mitigation.content
        }
        
        # Create PDF
        file_name = f"gtm_strategy_{title}_{datetime.now().strftime('%Y%m%d')}.pdf"
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
            ("Target Market Segments", self.extract_headers_and_subpoints(strategy.target_segments.content)),
            ("Positioning Strategy", self.extract_headers_and_subpoints(strategy.positioning_strategy.content)),
            ("Product Strategy", self.extract_headers_and_subpoints(strategy.product_strategy.content)),
            ("Pricing Strategy", self.extract_headers_and_subpoints(strategy.pricing_strategy.content)),
            ("Distribution Strategy", self.extract_headers_and_subpoints(strategy.distribution_strategy.content)),
            ("Marketing Plan", self.extract_headers_and_subpoints(strategy.marketing_plan.content)),
            ("Sales Strategy", self.extract_headers_and_subpoints(strategy.sales_strategy.content)),
            ("Customer Success Strategy", self.extract_headers_and_subpoints(strategy.customer_success.content)),
            ("Timeline & Milestones", self.extract_headers_and_subpoints(strategy.timeline_milestones.content)),
            ("Budget & Forecast", self.extract_headers_and_subpoints(strategy.budget_forecast.content)),
            ("Risk Mitigation", self.extract_headers_and_subpoints(strategy.risk_mitigation.content))
        ]
        
        for section_title, section_content in sections:
            self._add_single_column(elements, (section_title, section_content))
            elements.append(PageBreak())
            elements.append(Spacer(1, 20))
            
        document.build(elements)
        
        self.upload_file(file_name, file_path)

        return self.create_response(file_path, text_content)

    def _generate_executive_summary(self, request: GTMRequest, competitive_landscape: str, unique_value_prop: str) -> str:
        prompt = f"""
        Create an executive summary for the Go-To-Market strategy with the following details:
        Title: {request.title}
        Product: {request.product_description}
        Target Market: {request.target_market}
        Competitive Landscape: {competitive_landscape}
        Unique Value Proposition: {unique_value_prop}
        
        The executive summary should highlight:
        1. Market opportunity and potential
        2. Key differentiators and value proposition
        3. Go-to-market approach and strategy
        4. Expected outcomes and success metrics
        5. Resource requirements and timeline
        """
        response = self.model.generate_content(prompt)
        return response.text

    def _generate_market_analysis(self, request: GTMRequest, competitive_landscape: str) -> GTMSection:
        prompt = f"""
        Create a comprehensive market analysis based on:
        Target Market: {request.target_market}
        Competitive Landscape: {competitive_landscape}

        Include:
        1. Market size and growth potential
        2. Market trends and dynamics
        3. Competitive analysis
        4. Market barriers and opportunities
        5. Regulatory considerations
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Market Analysis",
            content=response.text
        )

    def _generate_target_segments(self, request: GTMRequest) -> GTMSection:
        prompt = f"""
        Define detailed target market segments based on:
        Target Market: {request.target_market}
        Product: {request.product_description}

        Include:
        1. Primary target segments
        2. Segment characteristics and needs
        3. Segment prioritization
        4. Segment-specific value propositions
        5. Market size by segment
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Target Market Segments",
            content=response.text
        )

    def _generate_positioning_strategy(self, request: GTMRequest, competitive_landscape: str, unique_value_prop: str) -> GTMSection:
        prompt = f"""
        Create a positioning strategy based on:
        Product: {request.product_description}
        Competitive Landscape: {competitive_landscape}
        Unique Value Proposition: {unique_value_prop}

        Include:
        1. Brand positioning statement
        2. Key differentiators
        3. Competitive advantages
        4. Brand messaging framework
        5. Value proposition by segment
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Positioning Strategy",
            content=response.text
        )

    def _generate_product_strategy(self, request: GTMRequest) -> GTMSection:
        prompt = f"""
        Develop a product strategy for:
        Product: {request.product_description}
        Target Market: {request.target_market}

        Include:
        1. Product roadmap
        2. Feature prioritization
        3. Product packaging/editions
        4. Technical requirements
        5. Product launch plan
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Product Strategy",
            content=response.text
        )

    def _generate_pricing_strategy(self, request: GTMRequest, competitive_landscape: str) -> GTMSection:
        prompt = f"""
        Create a pricing strategy for:
        Product: {request.product_description}
        Target Market: {request.target_market}
        Competitive Landscape: {competitive_landscape}

        Include:
        1. Pricing models and structure
        2. Price points by segment
        3. Competitive pricing analysis
        4. Pricing objectives
        5. Discount and promotion strategy
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Pricing Strategy",
            content=response.text
        )

    def _generate_distribution_strategy(self, request: GTMRequest, existing_channels: str) -> GTMSection:
        channels = f"\nExisting Channels: {existing_channels}" if existing_channels else ""
        
        prompt = f"""
        Design a distribution strategy for:
        Product: {request.product_description}
        Target Market: {request.target_market}{channels}

        Include:
        1. Channel strategy
        2. Partner ecosystem
        3. Distribution models
        4. Channel enablement
        5. Coverage strategy
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Distribution Strategy",
            content=response.text
        )

    def _generate_marketing_plan(self, request: GTMRequest) -> GTMSection:
        prompt = f"""
        Create a comprehensive marketing plan for:
        Product: {request.product_description}
        Target Market: {request.target_market}

        Include:
        1. Marketing objectives
        2. Channel mix and strategy
        3. Content strategy
        4. Campaign planning
        5. Lead generation approach
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Marketing Plan",
            content=response.text
        )

    def _generate_sales_strategy(self, request: GTMRequest) -> GTMSection:
        prompt = f"""
        Develop a sales strategy for:
        Product: {request.product_description}
        Target Market: {request.target_market}

        Include:
        1. Sales process and methodology
        2. Sales team structure
        3. Territory planning
        4. Sales enablement
        5. Compensation and incentives
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Sales Strategy",
            content=response.text
        )

    def _generate_customer_success(self, request: GTMRequest) -> GTMSection:
        prompt = f"""
        Design a customer success strategy for:
        Product: {request.product_description}
        Target Market: {request.target_market}

        Include:
        1. Customer onboarding process
        2. Support structure and levels
        3. Success metrics and KPIs
        4. Customer retention strategy
        5. Feedback and improvement loops
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Customer Success Strategy",
            content=response.text
        )

    def _generate_timeline_milestones(self, request: GTMRequest) -> GTMSection:
        timeline = f"\nTimeline Constraints: {request.timeline_constraints}" if request.timeline_constraints else ""
        
        prompt = f"""
        Create a timeline and milestones plan for GTM execution:
        Product: {request.product_description}{timeline}

        Include:
        1. Key phases and milestones
        2. Dependencies and critical path
        3. Resource allocation timeline
        4. Launch sequence
        5. Success metrics by phase
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Timeline & Milestones",
            content=response.text
        )

    def _generate_budget_forecast(self, request: GTMRequest) -> GTMSection:
        budget = f"\nBudget Range: {request.budget_range}" if request.budget_range else ""
        
        prompt = f"""
        Create a budget and forecast plan for GTM execution:
        Product: {request.product_description}{budget}

        Include:
        1. Budget allocation by function
        2. Revenue projections
        3. Cost structure analysis
        4. ROI calculations
        5. Financial metrics and KPIs
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Budget & Forecast",
            content=response.text
        )

    def _generate_risk_mitigation(self, request: GTMRequest, competitive_landscape: str) -> GTMSection:
        prompt = f"""
        Develop a risk mitigation strategy for the GTM plan:
        Product: {request.product_description}
        Target Market: {request.target_market}
        Competitive Landscape: {competitive_landscape}

        Include:
        1. Risk identification and assessment
        2. Market risks and mitigation
        3. Competitive risks and mitigation
        4. Operational risks and mitigation
        5. Contingency planning
        """
        response = self.model.generate_content(prompt)
        return GTMSection(
            title="Risk Mitigation",
            content=response.text
        ) 