from pydantic import BaseModel
from typing import List, Optional

class GTMSection(BaseModel):
    title: str
    content: str
    subsections: Optional[List['GTMSection']] = None

class GTMStrategy(BaseModel):
    title: str
    executive_summary: str
    market_analysis: GTMSection
    target_segments: GTMSection
    positioning_strategy: GTMSection
    product_strategy: GTMSection
    pricing_strategy: GTMSection
    distribution_strategy: GTMSection
    marketing_plan: GTMSection
    sales_strategy: GTMSection
    customer_success: GTMSection
    timeline_milestones: GTMSection
    budget_forecast: GTMSection
    risk_mitigation: GTMSection

class GTMRequest(BaseModel):
    title: str
    product_description: str
    target_market: str
    budget_range: Optional[str] = None  # Optional: Available budget for GTM activities
    timeline_constraints: Optional[str] = None  # Optional: Time constraints or deadlines 