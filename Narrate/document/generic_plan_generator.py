import google.generativeai as genai
from fastapi import FastAPI
import textwrap

from openai import OpenAI
from reportlab.lib.pagesizes import A4

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer, PageBreak
from google.generativeai import list_models
import os
from dotenv import load_dotenv
import time
import re
from datetime import datetime

from document.Requirements.document_generator import PDFGenerator
from document.document_structure import Phase, Objective, PlanContent

app = FastAPI()

load_dotenv()


#Calls to LLM

# 1. Generate Overview
# 2. Generate Phases
# 3. Generate Objectives (looped by phases)
# 4. Generate Resources (looped by phases

# This solution use

# Gemini

# Need to also integrate Grok3

# Gemini limits:
# 15 RPM (requests per minute)
# 1 million TPM (tokens per minute)
# 1.5K RPD (requests per day)

# models/chat-bison-001
# models/text-bison-001
# models/embedding-gecko-001
# models/gemini-1.0-pro-vision-latest
# models/gemini-pro-vision
# models/gemini-1.5-pro-latest
# models/gemini-1.5-pro-001
# models/gemini-1.5-pro-002
# models/gemini-1.5-pro
# models/gemini-1.5-flash-latest
# models/gemini-1.5-flash-001
# models/gemini-1.5-flash-001-tuning
# models/gemini-1.5-flash
# models/gemini-1.5-flash-002
# models/gemini-1.5-flash-8b
# models/gemini-1.5-flash-8b-001
# models/gemini-1.5-flash-8b-latest
# models/gemini-1.5-flash-8b-exp-0827
# models/gemini-1.5-flash-8b-exp-0924
# models/gemini-2.0-flash-exp
# models/gemini-2.0-flash
# models/gemini-2.0-flash-001
# models/gemini-2.0-flash-lite-001
# models/gemini-2.0-flash-lite
# models/gemini-2.0-pro-exp
# models/gemini-2.0-pro-exp-02-05
# models/gemini-exp-1206
# models/gemini-2.0-flash-thinking-exp-01-21
# models/gemini-2.0-flash-thinking-exp
# models/gemini-2.0-flash-thinking-exp-1219
# models/learnlm-1.5-pro-experimental
# models/embedding-001
# models/text-embedding-004
# models/aqa
# models/imagen-3.0-generate-002


class GenericDocumentGenerator:


#
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Google -> Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        # X.ai -> Grok (set XAI_API_KEY in Narrate/.env — gitignored)
        self.grok_api_key = os.getenv("XAI_API_KEY")
        self.grok_api_url = "https://api.x.ai/v1/chat/completions"

        self.styles = getSampleStyleSheet()

    def configure_model(self):
        genai.configure(api_key=self.gemini_api_key)

        models = list_models()
        for model in models:
            print(model.name)

        model_name = self.gemini_model
        return genai.GenerativeModel(model_name), genai.GenerativeModel('gemini-pro-vision')

    def generate_plan(self, doc_prompts, model_choice="gemini"):

        text_model, image_model = self.configure_model()
        for prompt in doc_prompts:

            title = prompt["title"]
            objectives = prompt["objectives"]

            response = text_model.generate_content(prompt["strategic_prompt"])
            strategic_overview = response.text

            # Choose AI model
            if model_choice == "gemini":
                response = text_model.generate_content(prompt["strategic_prompt"])
                strategic_overview = response.text
            elif model_choice == "grok":
                strategic_overview = self.generate_content_with_grok(prompt["strategic_prompt"])

            print(f"Overview: {strategic_overview}")
            summarization_strategic_overview = strategic_overview[:300]

            # Step 2: Generate Phases
            print("Phases Generating...")
            phases_num, phases_content = self.generate_phases(title, summarization_strategic_overview, text_model,
                                                              model_choice)

            print("Phases Generated")
            phases = []

            if len(phases_content) > 0:
                for i in range(1):
                #for i in range(phases_num):

                    print(f"Objectives in Phase {i} Generating...")
                    time.sleep(5)
                    phase = phases_content[i]
                    objectives = self.generate_objectives(title, phase, objectives, text_model, model_choice)

                    print(f"Objectives in Phase {i} Generated")
                    print(f"Resources in Phase {i} Generating...")
                    time.sleep(5)
                    resources = self.generate_resources(title, phase, text_model, model_choice)
                    print(f"Resources in Phase {i} Generated...")

                    phase_data = Phase(
                        phase=phases_content[i],
                        objectives=objectives,
                        resources=resources
                    )

                    phases.append(phase_data)

            # Objectives per phase & resources per objective in phase!

            plan_content = PlanContent(
                mission_overview=strategic_overview,
                phases=phases
            )

            doc = self.generate_pdf(title, plan_content)
            return doc

    def generate_phases(self, title, strategic_overview, text_model, model_choice):
        prompt = f"""
            This is the project title: {title}
            This is the strategic overview: {strategic_overview}

            Generate a **structured** project plan with exactly **3 to 5 phases**.
            Each phase should have:
            - A **title** in the format: "Phase X: [Title]"
            - A **brief description** explaining the purpose and key tasks.
            - A **timeline** (e.g., "Duration: 2 weeks")

            **Format the output like this:**
            ```
            Phase 1: [Title]
            - Description: [Brief explanation]
            - Timeline: [Duration]

            Phase 2: [Title]
            - Description: [Brief explanation]
            - Timeline: [Duration]
            ```

            **Do not exceed 5 phases.**
        """

        if model_choice == "gemini":
            response = text_model.generate_content(prompt)
            return self.parse_phases(response.text)
        elif model_choice == "grok":
            response = self.generate_content_with_grok(prompt)
            return self.parse_phases(response)

    def generate_objectives(self, title, phase, objectives, text_model, model_choice):
        prompt = f"""
            For the title '{title}' with main objectives '{objectives}', 
            during the phase '{phase}',

            Generate detailed and specific objectives. 
            Each objective should include a short title, followed by 5 detailed sub-points explaining the objective.

            Format them like this:
            1. Objective Title
               - Sub-point 1
               - Sub-point 2
               - Sub-point 3
               - Sub-point 4
               - Sub-point 5
        """

        if model_choice == "gemini":
            response = text_model.generate_content(prompt)
            # Debugging: Print AI Response
            objectives_text = response.text.strip()
            print("AI Response:\n", response.text)
        elif model_choice == "grok":
            response = self.generate_content_with_grok(prompt)
            objectives_text = response.strip()

        if not objectives_text:
            return []  # Return empty list if AI fails to generate content

        objectives_list = []
        current_objective = None

        # Split response into lines and process each line
        for line in objectives_text.split("\n"):
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            match = re.match(r"\*\*(\d+)\.\s(.+?)\*\*|(\d+)\.\s\*\*(.+?)\*\*", line)
            if match:
                # If an objective is found, save the previous one
                if current_objective:
                    objectives_list.append(current_objective)

                # Capture the objective name based on the match
                objective_name = match.group(2) or match.group(4)

                current_objective = Objective(
                    objective=objective_name.strip(),
                    sub_points=[]
                )

            elif line.startswith("-") and current_objective:  # Detect sub-points
                sub_point = line.lstrip("-").strip()
                current_objective.sub_points.append(sub_point)

        # Add the last objective if it's valid
        if current_objective:
            objectives_list.append(current_objective)

        return objectives_list

    def generate_resources(self, title, phase, text_model, model_choice):
        prompt = f"""
            For the mission '{title}', in the phase '{phase}'.',

            Generate a structured list of all required resources.  
            Include key resource categories such as **Hardware, Personnel, Equipment, Money, etc.**  
            Provide a brief description for each resource, explaining its role in the mission.

            Format them like this:
            **Category Name**
            - Resource 1: Description
            - Resource 2: Description
        """

        if model_choice == "gemini":
            response = text_model.generate_content(prompt)
            resources_text = response.text.strip()
            # Debugging: Print AI Response to verify formatting
            print("AI Response:\n", response.text)
        elif model_choice == "grok":
            response = self.generate_content_with_grok(prompt)
            resources_text = response.strip()

        if not resources_text:
            return {}  # Return empty dict if AI fails to generate content

        structured_resources = {}
        current_category = None

        for line in resources_text.split("\n"):
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            # Detect category (e.g., "**Hardware**")
            category_match = re.match(r"\*\*(.+?)\*\*", line)
            if category_match:
                current_category = category_match.group(1).strip()
                structured_resources[current_category] = []
            elif line.startswith("-") and current_category:  # Detect resource items
                parts = line.lstrip("-").split(":", 1)
                resource_name = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else "No description provided."
                structured_resources[current_category].append({"name": resource_name, "description": description})

        return structured_resources

    def parse_phases(self, phases_text):
        # Parse the text response into a structured format (you can customize this as needed)
        phases_num = 0
        phases = []
        for line in phases_text.split("\n"):
            if line.strip():
                parts = line.split(":")
                if len(parts) == 2:
                    phases_num = phases_num + 1
                    phase_title, phase_details = parts
                    phases.append({phase_title.strip() + phase_details.strip()})
        return phases_num, phases

    def generate_pdf(self, title, plan_content):
        # Set up the PDF document

        gen = PDFGenerator()
        return gen.generate_pdf(title, plan_content)

    # is this code longer necessary?

    # file_name = f"{title.replace(' ', '_')}.pdf"
    # file_path = os.path.join("pdfs", file_name)
    # os.makedirs("pdfs", exist_ok=True)
    #
    # document = SimpleDocTemplate(file_path, pagesize=A4)
    # document.title = title
    #
    # width, height = A4
    # frame = Frame(0, 0, width, height - 100, id='normal')  # Leave space for the title page
    #
    # # Create the custom page template with navy background on the first page
    # custom_page_template = PageTemplate(id='title', onPage=self.add_title_page, frames=[frame])
    # document.addPageTemplates([custom_page_template])
    # elements = []
    #
    # elements.append(PageBreak())
    # # Mission Overview
    # self.parse_and_add_content(elements, plan_content["mission_overview"])
    # # Phases
    # self.add_phases(elements, plan_content)
    # # Build PDF
    # document.build(elements)
    #
    # storage_client_wrapper = StorageClientWrapper()
    # storage_client_wrapper.upload_file(title, file_path)
    #
    # return FileResponse(file_path, media_type="application/pdf", filename=file_name)

    def add_title_page(self, canvas, doc):
        # Get page dimensions
        width, height = A4

        # Set navy blue background
        canvas.setFillColor(colors.navy)
        canvas.rect(0, 0, width, height, fill=True, stroke=False)

        # Set text properties
        canvas.setFillColor(colors.white)  # White text for contrast
        canvas.setFont("Helvetica-Bold", 24)

        # Add Title (Centered at the top)
        title = doc.title
        max_width = 80  # Adjust based on font size and page width
        wrapped_title = textwrap.wrap(title, width=max_width)  # Break into lines

        # Start drawing each line from the top, moving downward for each line
        y_position = height - 100
        for line in wrapped_title:
            canvas.drawCentredString(width / 2, y_position, line)
            y_position -= 20  # Adjust line spacin

        # Add Date (Below title)
        canvas.setFont("Helvetica", 14)
        current_date = datetime.now().strftime("%B %d, %Y")  # Format: February 11, 2025
        canvas.drawCentredString(width / 2, height - 140, f"Date: {current_date}")

        # Add Generation Info (Below date)
        canvas.setFont("Helvetica-Oblique", 12)
        canvas.drawCentredString(width / 2, height - 170, "Generated by Authentic Scope / Gemini")

    def generate_content_with_grok(self, prompt):
        """
        Calls Grok-3 API to generate content.
        """
        client = OpenAI(
            api_key=self.grok_api_key,
            base_url="https://api.x.ai/v1",
        )

        completion = client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {
                    "role": "system",
                    "content": "You are Grok, a chatbot inspired by the Hitchhikers Guide to the Galaxy."
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
        )
        print(completion)
        print(completion.choices[0].message.content)

        return completion.choices[0].message.content

    ## 11.02.2025 -> It's depends on the "*" sugn
    def parse_and_add_content(self, elements, content):
        # Get the standard styles
        styles = getSampleStyleSheet()
        normal_style = self.styles["CNormal"]
        bold_style = self.styles["CHeading2"]
        bullet_style = self.styles["CListItem"]

        # Split the content into lines (assuming paragraphs are separated by newlines)
        lines = content.split('\n')

        # Process each line
        for i, line in enumerate(lines):
            # Make the first line in the section a header (if not already bolded)
            if i == 0:
                header_paragraph = Paragraph(f"<b>{line.strip()}</b>", bold_style)
                elements.append(header_paragraph)
                elements.append(Spacer(1, 12))
                continue

            # Check if it's a bullet point (starts with '*')
            if line.strip().startswith('*'):
                # Remove the '*' and any extra spaces
                bullet_point = line.strip()[1:].strip()

                # Bold the text before the colon
                bullet_point = re.sub(r'^(.*?)(:)', r'<b>\1</b> \2', bullet_point)
                cleaned_bullet_point = bullet_point.replace("*", "")

                bullet_paragraph = Paragraph(f"• {cleaned_bullet_point}", bullet_style)
                elements.append(bullet_paragraph)
                elements.append(Spacer(1, 6))

            # Check if it has bold text (surrounded by '**')
            elif '**' in line:
                # Replace '**' with <b> for HTML-like formatting
                formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                cleaned_formatted_text = formatted_text.replace("*", "")

                bold_paragraph = Paragraph(cleaned_formatted_text, bold_style)
                elements.append(bold_paragraph)
                elements.append(Spacer(1, 6))

            # If it's normal text (neither bold nor a bullet point)
            else:
                formatted_text = line.strip()
                cleaned_formatted_text = formatted_text.replace("*", "")

                normal_paragraph = Paragraph(cleaned_formatted_text, normal_style)
                elements.append(normal_paragraph)
                elements.append(Spacer(1, 6))

        elements.append(PageBreak())  # Optionally, you can add a page break after content

    def parse_phase(self, phase_string):
        # If phase_string is a set, extract its single value
        if isinstance(phase_string, set):
            if len(phase_string) == 1:  # Ensure it's not an empty or multi-value set
                phase_string = next(iter(phase_string))  # Extract the single element
            else:
                raise ValueError(f"Expected a set with one element, but got: {phase_string}")

        if not isinstance(phase_string, str):
            raise TypeError(f"Expected a string, but got {type(phase_string).__name__}")

        # Debugging: Print the phase_string before processing
        print(f"Parsing phase string: {phase_string}")

        # Adjusted regex pattern for flexibility
        match = re.search(r'Phase\s*\d+\s*[:-]?\s*(.*)', phase_string, re.IGNORECASE)

        if match:
            result = match.group(1).strip()  # Return the phase name without leading/trailing spaces
            print(f"Extracted Phase Name: {result}")  # Debugging output
            return result

        print("No match found!")  # Debugging output
        return phase_string

    def add_phases(self, elements, plan_content):
        for i, phase in enumerate(plan_content["phases"], start=1):
            # Phase Title
            self.add_phase_title(elements, phase, i)

            # Objectives and Sub-Points
            self.add_objectives_and_subpoints(elements, phase)

            # Resources
            self.add_resources(elements, phase)

            if i < len(plan_content["phases"]) - 1:  # Add page break between phases if not the last
                elements.append(PageBreak())

    def add_phase_title(self, elements, phase, phase_number):
        phase_title_style = self.styles["CHeading2"]

        parsed_phase = self.parse_phase(phase['phase'])
        cleaned_parsed_phase = parsed_phase.replace("*", "")

        phase_title = Paragraph(f"<b>Phase {phase_number}: {cleaned_parsed_phase}</b>", phase_title_style)
        elements.append(phase_title)
        elements.append(Spacer(1, 16))

    def add_objectives_and_subpoints(self, elements, phase):
        for j, objective_data in enumerate(phase["objectives"]):
            objective_style = self.styles["CHighNormal"]
            cleaned_objective_text = objective_data['objective'].replace("*", "")

            objective_title = Paragraph(f"<b>{j + 1}. {cleaned_objective_text}</b>", objective_style)

            elements.append(objective_title)
            elements.append(Spacer(1, 8))

            for sub_point in objective_data['sub_points']:
                sub_point_style = self.styles["CNormal"]

                cleaned_sub_point = sub_point.replace("*", "")

                sub_point_para = Paragraph(f"- {cleaned_sub_point}", sub_point_style)
                elements.append(sub_point_para)
                elements.append(Spacer(1, 2))

    def add_resources(self, elements, phase):
        resources_title_style = self.styles["CHeading2"]
        resources_title = Paragraph("<b>Resources</b>", resources_title_style)
        elements.append(resources_title)
        elements.append(Spacer(1, 16))

        for category, items in phase["resources"].items():
            self.add_resource_category(elements, category, items)

    def add_resource_category(self, elements, category, items):
        resources_category_style = self.styles["CHighNormal"]
        cleaned_category = category.replace("*", "")

        category_title = Paragraph(f"<b>{cleaned_category}:</b>", resources_category_style)
        elements.append(category_title)
        elements.append(Spacer(1, 8))

        for item in items:
            resource_item_style = self.styles["CNormal"]

            cleaned_item_name = item['name'].replace("*", "")
            cleaned_item_description = item['description'].replace("*", "")

            resource_item = Paragraph(f"- {cleaned_item_name}: {cleaned_item_description}", resource_item_style)
            elements.append(resource_item)
            elements.append(Spacer(1, 4))
