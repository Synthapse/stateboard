from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BriefSection(BaseModel):
    title: str
    content: str
    subsections: Optional[List['BriefSection']] = None

class BriefStrategy(BaseModel):
    title: str
    executive_summary: str
    project_overview: BriefSection
    objectives: BriefSection
    scope: BriefSection
    deliverables: BriefSection
    timeline: BriefSection
    resources: BriefSection
    risks: BriefSection
    success_criteria: BriefSection

class BriefRequest(BaseModel):
    name: str
    description: str
    targetAudience: str
    brandValues: Optional[str] = None
    budget: Optional[str] = None
    category: Optional[str] = None
    contentType: Optional[str] = None
    deliverables: Optional[str] = None
    duration: Optional[str] = None
    requirements: Optional[str] = None
    platforms: List[str] = []
    goals: List[str] = [] 