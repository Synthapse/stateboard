from pydantic import BaseModel
from typing import List, Optional

class MarketingSection(BaseModel):
    title: str
    content: str
    subsections: Optional[List['MarketingSection']] = None

class MarketingStrategy(BaseModel):
    title: str
    executive_summary: str
    market_analysis: MarketingSection
    marketing_objectives: MarketingSection
    target_audience: MarketingSection
    marketing_mix: MarketingSection
    digital_strategy: MarketingSection
    budget_timeline: MarketingSection
    implementation_plan: MarketingSection
    risk_analysis: MarketingSection

class MarketingRequest(BaseModel):
    title: str
    objectives: str
    strategic_prompt: str
    target_market: Optional[str] = None  # Optional: Specific target market segments or demographics
    budget_constraints: Optional[str] = None  # Optional: Budget limitations or specific financial constraints 