"""
Seed sample data for LLM / Agentic ranking demo.
Creates/Updates:
- Multiple Employee (Seeker) accounts:
  * employee1@example.com — Employee 1 (Backend & Cloud Engineer)
  * employee2@example.com — Employee 2 (AI/NLP & Backend Engineer)
  * employee3@example.com — Employee 3 (Junior Backend & Full-Stack Developer)
  * employee4@example.com — Employee 4 (Software Developer)
  * employee5@example.com — Employee 5 (Senior Backend & Machine Learning Engineer)
- Links their uploaded resumes.
- Employer account with approved status.
- A job listing created by the employer.

Usage:
    python manage.py seed_agentic_demo
"""
from decimal import Decimal
from django.core.management.base import BaseCommand

from talentwright.users.models import User, EmployerProfile, SeekerProfile, Resume, VerificationStatus
from talentwright.jobs.models import Job, EmploymentType, JobStatus
from talentwright.applications.models import Application, ApplicationStatus


COMMON_PASSWORD = "Password123!"

EMPLOYEES = [
    {
        "index": 1,
        "email": "employee1@example.com",
        "name": "Employee 1",
        "phone": "+1-555-0101",
        "bio": (
            "Backend & Cloud Engineer with strong experience in architecting and deploying "
            "resilient backend microservices. Proficient in Python, Django, Docker, Kubernetes, "
            "AWS cloud infrastructure, CI/CD automation, and PostgreSQL database performance tuning."
        ),
        "cover_letter": (
            "Dear Hiring Team at TechCorp AI Solutions,\n\n"
            "I am writing to express my strong interest in the Senior Python & AI Engineer position. "
            "With over 5 years of professional backend development experience specializing in Python, Django, "
            "and cloud infrastructure, I have designed and scaled resilient microservices handling high transaction volumes.\n\n"
            "My background includes architecting RESTful APIs using Django REST Framework and FastAPI, automating "
            "containerized deployments with Docker and Kubernetes, and optimizing complex PostgreSQL databases. "
            "I am deeply interested in your work building autonomous agent platforms and am excited about applying "
            "my cloud infrastructure and backend engineering experience to scale TechCorp AI's services.\n\n"
            "Thank you for your consideration.\n\n"
            "Sincerely,\nEmployee 1"
        ),
    },
    {
        "index": 2,
        "email": "employee2@example.com",
        "name": "Employee 2",
        "phone": "+1-555-0102",
        "bio": (
            "AI/NLP & Backend Engineer specializing in combining robust backend engineering with "
            "modern NLP and LLM technologies. Experienced in Python, Django REST Framework, FastAPI, "
            "Hugging Face transformers, OpenAI API integrations, and vector search systems."
        ),
        "cover_letter": (
            "Dear Hiring Team at TechCorp AI Solutions,\n\n"
            "I am thrilled to apply for the Senior Python & AI Engineer role. As a backend and NLP engineer, "
            "I specialize in bridging software systems with generative AI and LLM workflows.\n\n"
            "Over the past four years, I have built production AI pipelines utilizing Python, FastAPI, and OpenAI/Anthropic APIs. "
            "I have extensive experience implementing structured tool calling, prompt engineering architectures, "
            "and semantic search pipelines backed by pgvector and Chroma. TechCorp AI's focus on autonomous agent workflows "
            "aligns directly with my technical focus and passion.\n\n"
            "I look forward to discussing how my skills in Python backend engineering and LLM integrations can contribute to your team.\n\n"
            "Best regards,\nEmployee 2"
        ),
    },
    {
        "index": 3,
        "email": "employee3@example.com",
        "name": "Employee 3",
        "phone": "+1-555-0103",
        "bio": (
            "Junior Backend & Full-Stack Developer with foundational experience in Python, "
            "Django, JavaScript, React, and RESTful APIs. Quick learner enthusiastic about "
            "cloud services, test-driven development, and AI-driven products."
        ),
        "cover_letter": (
            "Dear TechCorp AI Solutions Team,\n\n"
            "I am excited to submit my application for the Python & AI Engineer role. Having worked as a full-stack "
            "developer with Python, Django, React, and TypeScript, I bring enthusiasm, clean coding standards, and a fast-learning mindset.\n\n"
            "I have contributed to building scalable REST APIs, managing relational schemas in PostgreSQL, and integrating "
            "modern frontend interfaces with backend services. I have also been actively exploring LangChain and LLM APIs "
            "for interactive developer tools. I am eager to learn from senior engineers and contribute to your intelligent platform.\n\n"
            "Thank you for reviewing my application.\n\n"
            "Warm regards,\nEmployee 3"
        ),
    },
    {
        "index": 4,
        "email": "employee4@example.com",
        "name": "Employee 4",
        "phone": "+1-555-0104",
        "bio": (
            "Software Developer with practical experience across backend application development, "
            "database management, and API design using Python, relational databases (PostgreSQL/MySQL), "
            "and Git workflows. Focused on writing clean, maintainable code."
        ),
        "cover_letter": (
            "Dear Hiring Team,\n\n"
            "I am writing to apply for the Senior Python & AI Engineer position at TechCorp AI Solutions. As a software "
            "developer with experience in Python application development, systems engineering, and database design, "
            "I pride myself on writing reliable, well-tested code.\n\n"
            "Throughout my work, I have focused on building performant backend services, implementing comprehensive "
            "automated test suites, and orchestrating containerized environments with Docker. I am passionate about applying "
            "core software engineering rigor to the rapidly evolving field of autonomous AI systems.\n\n"
            "I would love the opportunity to bring my development skills to TechCorp AI Solutions.\n\n"
            "Sincerely,\nEmployee 4"
        ),
    },
    {
        "index": 5,
        "email": "employee5@example.com",
        "name": "Employee 5",
        "phone": "+1-555-0105",
        "bio": (
            "Senior Backend & Machine Learning Engineer with extensive experience designing high-scale "
            "distributed systems and end-to-end ML pipelines. Expert in Python, Django, PyTorch, "
            "scalable database architectures, LLM fine-tuning, RAG, and production MLOps."
        ),
        "cover_letter": (
            "Dear TechCorp AI Solutions Hiring Team,\n\n"
            "I am writing to express my enthusiastic interest in the Senior Python & AI Engineer role. With over 7 years "
            "of engineering experience architecting enterprise Python platforms and production machine learning systems, "
            "I believe my background matches your requirements closely.\n\n"
            "In my recent roles, I have:\n"
            "- Architected high-throughput Python (Django & FastAPI) backend microservices serving millions of requests daily.\n"
            "- Built end-to-end LLM agent pipelines featuring function-calling, stateful conversation trees, and RAG architectures over PostgreSQL / pgvector.\n"
            "- Led database scaling initiatives, indexing strategies, and Docker/Kubernetes container infrastructure.\n"
            "- Mentored engineering teams on production AI deployment and clean architectural design.\n\n"
            "I am eager to contribute to TechCorp AI Solutions' mission to pioneer autonomous agent systems. Thank you for your time and consideration.\n\n"
            "Sincerely,\nEmployee 5"
        ),
    },
]

EMPLOYER = {
    "email": "employer1@example.com",
    "name": "Employer 1",
    "company_name": "TechCorp AI Solutions",
    "website": "https://techcorpai.example.com",
    "description": (
        "TechCorp AI Solutions is a technology firm building next-generation "
        "intelligent workflows, autonomous agent systems, and enterprise cloud solutions."
    ),
}

JOB_DATA = {
    "title": "Senior Python & AI Engineer",
    "description": """About the Role:
TechCorp AI Solutions is seeking a Senior Python & AI Engineer to help build our next-generation intelligent agent platform. You will architect backend microservices, design LLM agent workflows, and scale our AI services.

Key Responsibilities:
- Design and build robust backend APIs and services using Python and Django / FastAPI.
- Integrate external LLM APIs (OpenAI, Anthropic) and build autonomous agent pipelines with structured outputs and function calling.
- Design, optimize, and maintain PostgreSQL database schemas and vector search indexes.
- Package and deploy applications using Docker in modern cloud environments.
- Collaborate with frontend engineers to deliver intuitive AI-assisted user experiences.

Qualifications & Requirements:
- 4+ years of professional backend software development experience with Python.
- Proven experience with Django, Django REST Framework, or FastAPI.
- Hands-on experience integrating LLM APIs (e.g. OpenAI GPT-4, embeddings) and building AI-powered features.
- Strong proficiency with PostgreSQL, relational database design, and query optimization.
- Familiarity with Docker, containerization, and Git workflows.

Nice to Have:
- Experience with LangChain, LlamaIndex, or agentic frameworks.
- Experience with vector databases (Chroma, Pinecone, pgvector).
- Familiarity with React / TypeScript.""",
    "location": "Remote",
    "employment_type": EmploymentType.FULL_TIME,
    "salary_min": Decimal("100000.00"),
    "salary_max": Decimal("150000.00"),
    "salary_currency": "USD",
    "status": JobStatus.OPEN,
}


class Command(BaseCommand):
    help = "Seed Employee and Employer accounts with an active Job listing for agentic demo"

    def handle(self, *args, **options):
        self.stdout.write("--- Updating Agentic Demo Data ---")

        # 1. Create/Update Employer User & Profile
        emp_user, _ = User.objects.get_or_create(
            email=EMPLOYER["email"],
            defaults={
                "name": EMPLOYER["name"],
                "is_active": True,
            },
        )
        emp_user.name = EMPLOYER["name"]
        emp_user.set_password(COMMON_PASSWORD)
        emp_user.save()
        emp_profile, _ = EmployerProfile.objects.update_or_create(
            user=emp_user,
            defaults={
                "company_name": EMPLOYER["company_name"],
                "website": EMPLOYER["website"],
                "description": EMPLOYER["description"],
                "verification_status": VerificationStatus.APPROVED,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"✓ Employer ready: {emp_user.email} (Approved)"))

        # 2. Create/Update Job under the Employer
        job, job_created = Job.objects.update_or_create(
            employer=emp_profile,
            title=JOB_DATA["title"],
            defaults={
                "description": JOB_DATA["description"],
                "location": JOB_DATA["location"],
                "employment_type": JOB_DATA["employment_type"],
                "salary_min": JOB_DATA["salary_min"],
                "salary_max": JOB_DATA["salary_max"],
                "salary_currency": JOB_DATA["salary_currency"],
                "status": JOB_DATA["status"],
            },
        )
        action_str = "Created" if job_created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"✓ Job {action_str}: '{job.title}' (ID: {job.id}, Status: {job.status})"))

        # 3. Create/Update Employees (Seekers) and link resumes
        self.stdout.write("\nUpdating Employee / Seeker accounts and resumes:")
        for emp_data in EMPLOYEES:
            idx = emp_data["index"]
            user, _ = User.objects.get_or_create(
                email=emp_data["email"],
                defaults={
                    "name": emp_data["name"],
                    "is_active": True,
                },
            )
            user.name = emp_data["name"]
            user.set_password(COMMON_PASSWORD)
            user.save()

            seeker_profile, _ = SeekerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "phone": emp_data["phone"],
                    "bio": emp_data["bio"],
                },
            )

            resume, _ = Resume.objects.update_or_create(
                seeker=seeker_profile,
                title=f"Employee {idx} Resume",
                defaults={
                    "file": f"resumes/2026/09/Employee_{idx}_Resume.pdf",
                    "is_primary": True,
                },
            )
            self.stdout.write(f"  ✓ {user.email} | Resume ID: {resume.id} ({resume.file})")

        # 4. If kiran@gmail.com exists, link KiranKuruvilaCV.pdf as their resume
        kiran_user = User.objects.filter(email="kiran@gmail.com").first()
        if kiran_user and hasattr(kiran_user, "seeker_profile"):
            kiran_resume, _ = Resume.objects.update_or_create(
                seeker=kiran_user.seeker_profile,
                title="Kiran Kuruvila CV",
                defaults={
                    "file": "resumes/2026/09/KiranKuruvilaCV.pdf",
                    "is_primary": True,
                },
            )
            self.stdout.write(f"  ✓ {kiran_user.email} | Resume ID: {kiran_resume.id} ({kiran_resume.file})")

        # 5. Create/Update Applications for Job
        self.stdout.write(f"\nSubmitting Applications for Job '{job.title}' (ID: {job.id}):")
        for emp_data in EMPLOYEES:
            user = User.objects.get(email=emp_data["email"])
            seeker = user.seeker_profile
            resume = seeker.resumes.filter(is_primary=True).first() or seeker.resumes.first()
            app, app_created = Application.objects.update_or_create(
                job=job,
                seeker=seeker,
                defaults={
                    "resume": resume,
                    "cover_letter": emp_data["cover_letter"],
                    "status": ApplicationStatus.SUBMITTED,
                },
            )
            action = "Created" if app_created else "Updated"
            self.stdout.write(f"  ✓ {action} Application: {user.email} -> Job {job.id} (Resume: {resume.title if resume else 'None'})")

        if kiran_user and hasattr(kiran_user, "seeker_profile"):
            kiran_resume = kiran_user.seeker_profile.resumes.filter(is_primary=True).first() or kiran_user.seeker_profile.resumes.first()
            k_app, k_created = Application.objects.update_or_create(
                job=job,
                seeker=kiran_user.seeker_profile,
                defaults={
                    "resume": kiran_resume,
                    "cover_letter": (
                        "Dear Hiring Team at TechCorp AI Solutions,\n\n"
                        "I am excited to apply for the Senior Python & AI Engineer position. "
                        "As a software engineer experienced with backend architectures, Python development, "
                        "and modern full-stack web applications, I look forward to contributing to your intelligent agent systems.\n\n"
                        "Best regards,\nKiran Kuruvila"
                    ),
                    "status": ApplicationStatus.SUBMITTED,
                },
            )
            action = "Created" if k_created else "Updated"
            self.stdout.write(f"  ✓ {action} Application: {kiran_user.email} -> Job {job.id} (Resume: {kiran_resume.title if kiran_resume else 'None'})")

        self.stdout.write(self.style.SUCCESS("\n--- Complete ---"))
