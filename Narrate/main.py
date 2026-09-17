"""Narrate entrypoints.

Cloud Functions gen2: --entry-point=digest_http (loads this module).
FastAPI (parked) only loads when not running as a Cloud Function.
"""

from __future__ import annotations

import os


def digest_http(request):
    """M5 HTTP entry — no FastAPI / Firebase import path."""
    from insights.entrypoints.handler import digest_http as _handler

    return _handler(request)


# Functions Framework / GCF set FUNCTION_TARGET before import.
if not os.environ.get("FUNCTION_TARGET"):
    import time

    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

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
        version="1.0.0",
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
        "https://storage.googleapis.com/voicesense/index.html",
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
        title = "Project Overview"
        sd = MultiAgentPdfGenerator()
        doc = sd.generate_pdf(title, request)
        return doc

    @app.post("/generateDocument", tags=["Authentic Scope"])
    async def generateDoc(title, objective, strategic_prompt):
        prompts = [
            {
                "title": title,
                "objectives": objective,
                "strategic_prompt": strategic_prompt,
            }
        ]
        c = GenericDocumentGenerator()
        model = "gemini"
        doc = c.generate_plan(prompts, model)
        return doc

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
        print(f"Fetched files from GCS bucket: {file_names}")
        return {"files": file_names}
