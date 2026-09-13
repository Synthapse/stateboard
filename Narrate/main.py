import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import FileResponse
import time

from document.MultiAgent.doc_gen import MultiAgentPdfGenerator
from document.MultiAgent.structure import SystemRequest
from document.generic_plan_generator import GenericDocumentGenerator
from document.summary_generator import SummaryDocumentGenerator
from integration.GCPClientBucket import StorageClientWrapper


from raports.router import router as raports_router

app = FastAPI(
    title="LLM Document API",
    description=(
        "An API designed to generate, manage, and update structured marketing documents using a multi-agent system. "
        "Supports creating sections like executive summaries, market analysis, content strategy, and more."
    ),
    version="1.0.0"
)

app.include_router(raports_router)


origins = [
    "https://authenticscope.xyz",
    "https://www.aiviralbuzz.com",
    "https://aiviralbuzz.com/",
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8081",
    "https://storage.googleapis.com",
    "https://storage.googleapis.com/voicesense",
    "https://storage.googleapis.com/voicesense/index.html"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessionid = os.getsid(0)
print("Session ID: ", sessionid)
sessionid2 = int(time.time())

@app.post("/multiAgentDoc", tags=["Nexus"])
async def generate_doc_summary(request: SystemRequest):

    # possibilities: network_agent, energy_agent, cyber_security_agent
    # network_agent.numberOfNodes
    # energy_agent.recommendation
    # cyber_security_agent.recommendation

    # Whats are possibilities?

    title = "Project Overview"

    sd = MultiAgentPdfGenerator()
    doc = sd.generate_pdf(title, request)
    return doc



@app.post("/generateDocument", tags=["Authentic Scope"])
async def generateDoc(title, objective, strategic_prompt):

    space_prompts = [
        {
            "mission_name": "Lunar mining",
            "objectives": "Land and start minning the key resources (Helium-3) and Earth Rare Resources on moon, with detecting water ice and mapping geological structures",
        }
    ]

    prompts = [
        {
            "title": title,
            "objectives": objective,
            "strategic_prompt": strategic_prompt,
        }
    ]

    c = GenericDocumentGenerator()
    # Monitor Grok usage - report cost ->  ~$0.01 (based on prompts)

    # https://console.x.ai/team/072165ae-42cf-4b5c-8ea0-2b2882fcb67a/usage
    # https://aistudio.google.com/app/u/2/apikey?pli=1
    model = "gemini"
    doc = c.generate_plan(prompts, model)
    return doc
    #return FileResponse(doc, media_type="application/pdf", filename="{title}.pdf")




@app.post("/generateSummarization", tags=["QualityCare"])
async def generateDocSummary(title, strategic_prompt):


    prompts = [
        {
            "title": title,
            "strategic_prompt": strategic_prompt,
        }
    ]

    sd = SummaryDocumentGenerator()
    doc = sd.generate_summary(prompts)
    return doc


storage_wrapper = StorageClientWrapper()

@app.get("/getAuthenticScopeSpecs", tags=["AuthenticScope"])
async def get_files_from_bucket():
    """Fetches all files from the GCS bucket and returns them."""
    file_names = storage_wrapper.list_files()

    # Log files for debugging
    print(f"Fetched files from GCS bucket: {file_names}")

    return {"files": file_names}
