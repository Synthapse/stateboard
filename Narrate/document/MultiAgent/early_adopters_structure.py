from pydantic import BaseModel
from typing import List, Optional

class EarlyAdopterSection(BaseModel):
    title: str
    content: str
    subsections: Optional[List['EarlyAdopterSection']] = None

class EarlyAdopterStrategy(BaseModel):
    title: str
    executive_summary: str
    ideal_customer_profile: EarlyAdopterSection
    value_proposition: EarlyAdopterSection
    program_benefits: EarlyAdopterSection
    onboarding_process: EarlyAdopterSection
    feedback_mechanisms: EarlyAdopterSection
    success_metrics: EarlyAdopterSection
    engagement_plan: EarlyAdopterSection
    resource_allocation: EarlyAdopterSection

class EarlyAdopterRequest(BaseModel):
    title: str
    product_description: str
    target_audience: str
    strategic_goals: Optional[str] = None  # Optional: Specific goals for the early adopter program
    resource_constraints: Optional[str] = None  # Optional: Available resources and limitations 