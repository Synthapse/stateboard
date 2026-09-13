from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from document.MultiAgent.marketing_structure import MarketingRequest
from document.MultiAgent.marketing_gen import MarketingStrategyGenerator
import os

from document.MultiAgent.early_adopters_structure import EarlyAdopterRequest
from document.MultiAgent.early_adopters_gen import EarlyAdopterGenerator
from document.MultiAgent.gtm_structure import GTMRequest
from document.MultiAgent.gtm_gen import GTMGenerator
from document.MultiAgent.brief_doc_structure import BriefRequest
from document.MultiAgent.brief_doc_gen import BriefDocGenerator
from firebase_admin import firestore


import firebase_admin
from firebase_admin import credentials, db  # or firestore

# Initialize the app with a service account
cred = credentials.Certificate("firebase.json")
firebase_admin.initialize_app(cred)


router = APIRouter()



# 17.06.2025
# Aureyo will be merge into the project within Hackhathon
# Then:
# Marketing Strategy raport
# Early Adapters raport
# Go to market raport
# Reddit Audience raport

# All may will be generated from the data from brand_onboard - without any user forms

# {
#   "title": "Fintool",
#   "objectives": "Finance tool for predicting strategies in stocks",
#   "strategic_prompt": "Develop a cost-effective go-to-market strategy for Fintool, a predictive analytics tool for stock market strategies. Focus on engaging individual investors and finance enthusiasts interested in AI-powered decision-making tools. Highlight Fintool's unique value in simplifying complex financial insights. Consider a lean digital marketing plan including organic social media, SEO-focused content marketing, and influencer outreach within a 1000 PLN monthly budget. Ensure all efforts are measurable, and prioritize ROI-positive channels for acquisition and retention.",
#   "target_market": "stocks, finances",
#   "budget_constraints": "1000 PLN"
# }

@router.post("/marketing-strategy", tags=["Aureyo"])
async def generate_marketing_strategy(request: MarketingRequest):
    """
    Generate a comprehensive marketing strategy document.
    
    Returns:
        dict: Contains both the PDF document and the text content in JSON format
            - pdf_document: PDF file response containing:
                - Executive Summary
                - Market Analysis
                - Marketing Objectives
                - Target Audience Analysis
                - Marketing Mix (4Ps)
                - Digital Marketing Strategy
                - Budget and Timeline
                - Implementation Plan
                - Risk Analysis
            - text_content: Dictionary containing the text content of each section
    """
    generator = MarketingStrategyGenerator()
    return generator.generate_pdf(request.title, request)

# {
#     "title": "Product X Early Adopter Program",
#     "product_description": "A revolutionary AI-powered productivity tool...",
#     "target_audience": "Tech-savvy professionals in medium to large enterprises...",
#     "strategic_goals": "Gather user feedback and validate coxpre features...",
#     "resource_constraints": "Limited to supporting 50 early adopters in first phase..."
# }

@router.post("/early-adopter-strategy", tags=["Aureyo"])
async def generate_early_adopter_strategy(request: EarlyAdopterRequest):
    """
    Generate a comprehensive early adopter program strategy document.
    
    Returns:
        dict: Contains both the PDF document and the text content in JSON format
            - pdf_document: PDF file response containing:
                - Executive Summary
                - Ideal Customer Profile
                - Value Proposition
                - Program Benefits
                - Onboarding Process
                - Feedback Mechanisms
                - Success Metrics
                - Engagement Plan
                - Resource Allocation
            - text_content: Dictionary containing the text content of each section
    """
    generator = EarlyAdopterGenerator()
    return generator.generate_pdf(request.title, request)

@router.post("/go-to-market", tags=["Aureyo"])
async def generate_gtm_strategy(request: GTMRequest):
    """
    Generate a comprehensive Go-To-Market (GTM) strategy document.
    
    Returns:
        dict: Contains both the PDF document and the text content in JSON format
            - pdf_document: PDF file response containing:
                - Executive Summary
                - Market Analysis
                - Target Market Segments
                - Positioning Strategy
                - Product Strategy
                - Pricing Strategy
                - Distribution Strategy
                - Marketing Plan
                - Sales Strategy
                - Customer Success Strategy
                - Timeline & Milestones
                - Budget & Forecast
                - Risk Mitigation
            - text_content: Dictionary containing the text content of each section
    
    The document is tailored based on:
    - Product description
    - Target market
    - Competitive landscape
    - Budget range (optional)
    - Timeline constraints (optional)
    - Existing channels (optional)
    - Unique value proposition (optional)
    """
    generator = GTMGenerator()
    return generator.generate_pdf(request.title, request) 


@dataclass
class Campaign:
    brandValues: Optional[str]
    budget: Optional[str]
    category: Optional[str]
    contentType: Optional[str]
    createdAt: Optional[datetime]
    createdBy: Optional[str]
    deliverables: Optional[str]
    description: Optional[str]
    duration: Optional[str]
    name: Optional[str]
    requirements: Optional[str]
    status: Optional[str]
    targetAudience: Optional[str]
    updatedAt: Optional[datetime]
    platforms: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    userId: Optional[str] = None

    
class CampaignIdRequest(BaseModel):
    campaign_id: str

@router.post("/brief", tags=["Aureyo"])
async def generate_brief_doc(request: CampaignIdRequest):
    """
    Generate a comprehensive brief document based on campaign data from Firebase.
    
    Args:
        request: CampaignIdRequest containing the campaign ID
        
    Returns:
        dict: Contains both the PDF document and the text content in JSON format
            - pdf_document: PDF file response containing:
                - Executive Summary
                - Campaign Overview
                - Objectives
                - Scope
                - Deliverables
                - Timeline
                - Resources
                - Risks
                - Success Criteria
            - text_content: Dictionary containing the text content of each section
    """
    # Get Firebase client
    db = firestore.client()
    
    # Fetch campaign data from Firebase
    campaign_doc = db.collection('campaigns').document(request.campaign_id).get()
    
    if not campaign_doc.exists:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_data = campaign_doc.to_dict()
    
    # Convert Firebase data to Campaign model
    campaign = Campaign(
        brandValues=campaign_data.get('brandValues'),
        budget=campaign_data.get('budget'),
        category=campaign_data.get('category'),
        contentType=campaign_data.get('contentType'),
        createdAt=campaign_data.get('createdAt'),
        createdBy=campaign_data.get('createdBy'),
        deliverables=campaign_data.get('deliverables'),
        description=campaign_data.get('description'),
        duration=campaign_data.get('duration'),
        name=campaign_data.get('name'),
        requirements=campaign_data.get('requirements'),
        status=campaign_data.get('status'),
        targetAudience=campaign_data.get('targetAudience'),
        updatedAt=campaign_data.get('updatedAt'),
        platforms=campaign_data.get('platforms', []),
        goals=campaign_data.get('goals', []),
        userId=campaign_data.get('userId')
    )
    
    # Convert Campaign to BriefRequest
    brief_request = BriefRequest(
        name=campaign.name or "Untitled Campaign",
        description=campaign.description or "",
        targetAudience=campaign.targetAudience or "",
        brandValues=campaign.brandValues,
        budget=campaign.budget,
        category=campaign.category,
        contentType=campaign.contentType,
        deliverables=campaign.deliverables,
        duration=campaign.duration,
        requirements=campaign.requirements,
        platforms=campaign.platforms,
        goals=campaign.goals
    )
    
    generator = BriefDocGenerator()
    return generator.generate_pdf(brief_request.name, brief_request)

