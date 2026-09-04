"""
Seed the database with rich sample data for Hirely.

Usage:
    python manage.py seed_data
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from talentwright.users.models import User, EmployerProfile, SeekerProfile, Resume, VerificationStatus
from talentwright.jobs.models import Job, EmploymentType, JobStatus
from talentwright.applications.models import Application, ApplicationStatus


COMPANIES = [
    {
        "name": "Acme Corp",
        "email": "hr@acmecorp.com",
        "website": "https://acmecorp.com",
        "description": "A leading technology company building the next generation of cloud infrastructure. We work at the intersection of distributed systems and developer experience.",
        "user_name": "Priya Mehta",
    },
    {
        "name": "Vision Labs",
        "email": "careers@visionlabs.io",
        "website": "https://visionlabs.io",
        "description": "Computer vision and AI research lab focused on healthcare imaging. Our models help radiologists detect anomalies 3x faster.",
        "user_name": "Rahul Verma",
    },
    {
        "name": "Zetabyte",
        "email": "jobs@zetabyte.in",
        "website": "https://zetabyte.in",
        "description": "India's fastest-growing data analytics platform. We help enterprises make sense of petabyte-scale data with real-time dashboards.",
        "user_name": "Anjali Krishnan",
    },
    {
        "name": "TechStack",
        "email": "talent@techstack.dev",
        "website": "https://techstack.dev",
        "description": "Open-source developer tools company. We maintain popular libraries used by over 2 million developers worldwide.",
        "user_name": "Vikram Singh",
    },
    {
        "name": "CloudNet",
        "email": "people@cloudnet.co",
        "website": "https://cloudnet.co",
        "description": "Enterprise cloud networking solutions. We simplify multi-cloud connectivity for Fortune 500 companies across 40 countries.",
        "user_name": "Deepa Nair",
    },
    {
        "name": "Humanly",
        "email": "hr@humanly.work",
        "website": "https://humanly.work",
        "description": "HR tech startup reimagining the hiring process with AI-driven candidate matching and structured interviews.",
        "user_name": "Arjun Rao",
    },
]

SEEKERS = [
    {
        "email": "arjun.sharma@email.com",
        "name": "Arjun Sharma",
        "phone": "+91-9876543210",
        "bio": "Full-stack developer with 4 years of experience in React, Node.js, and Python. Passionate about building accessible and performant web applications. Previously at a Series B startup where I led the frontend architecture migration.",
    },
    {
        "email": "sneha.patel@email.com",
        "name": "Sneha Patel",
        "phone": "+91-9123456789",
        "bio": "Product designer with a strong background in UX research and design systems. I love translating complex workflows into simple, intuitive interfaces. Figma evangelist.",
    },
    {
        "email": "karthik.iyer@email.com",
        "name": "Karthik Iyer",
        "phone": "+91-8765432109",
        "bio": "Backend engineer specializing in Go and distributed systems. Open source contributor to several CNCF projects. Looking for challenging infrastructure roles.",
    },
    {
        "email": "meera.reddy@email.com",
        "name": "Meera Reddy",
        "phone": "+91-7654321098",
        "bio": "Data scientist with expertise in NLP and recommendation systems. M.Tech from IIT Hyderabad. Published 3 papers at top-tier ML conferences.",
    },
    {
        "email": "ravi.kumar@email.com",
        "name": "Ravi Kumar",
        "phone": "+91-6543210987",
        "bio": "DevOps engineer with deep expertise in Kubernetes, Terraform, and CI/CD pipelines. AWS and GCP certified. I automate everything.",
    },
    {
        "email": "ananya.gupta@email.com",
        "name": "Ananya Gupta",
        "phone": "+91-5432109876",
        "bio": "Frontend developer focused on React and TypeScript. Strong advocate for web performance and accessibility. I enjoy mentoring junior developers.",
    },
    {
        "email": "rohit.joshi@email.com",
        "name": "Rohit Joshi",
        "phone": "+91-4321098765",
        "bio": "Mobile developer with 3 years of React Native and Flutter experience. Built apps with 500k+ downloads. Interested in cross-platform tooling.",
    },
    {
        "email": "divya.menon@email.com",
        "name": "Divya Menon",
        "phone": "+91-3210987654",
        "bio": "QA engineer transitioning to software development. Strong foundation in test automation with Selenium and Playwright. Currently learning Rust.",
    },
]

JOBS_DATA = [
    # Acme Corp jobs
    {
        "company": "Acme Corp",
        "title": "Frontend Developer",
        "description": """We're looking for a skilled Frontend Developer to join our product team in Bengaluru.

**What you'll do:**
- Build and maintain our React-based dashboard used by 10,000+ developers
- Collaborate with designers to implement pixel-perfect, accessible UIs
- Optimize bundle size and runtime performance
- Write comprehensive tests with React Testing Library

**What we're looking for:**
- 2+ years of professional React experience
- Strong TypeScript skills
- Experience with state management (TanStack Query, Zustand, or Redux)
- Familiarity with CI/CD and modern frontend tooling (Vite, ESLint, Prettier)

**Nice to have:**
- Experience with design systems
- Contributions to open-source projects
- Understanding of Web APIs and browser internals""",
        "location": "Bengaluru, India",
        "employment_type": "FULL_TIME",
        "salary_min": 1200000,
        "salary_max": 2000000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 2,
    },
    {
        "company": "Acme Corp",
        "title": "Senior Backend Engineer",
        "description": """Join our infrastructure team to build scalable microservices powering our cloud platform.

**Responsibilities:**
- Design and implement RESTful APIs and gRPC services in Go
- Own the deployment pipeline for your services (Docker, Kubernetes)
- Participate in on-call rotation and incident response
- Mentor junior engineers through code reviews and pair programming

**Requirements:**
- 4+ years of backend development experience
- Proficiency in Go, Python, or Java
- Experience with PostgreSQL, Redis, and message queues (Kafka/RabbitMQ)
- Understanding of distributed systems concepts

**Compensation:** Competitive salary + equity + annual bonus""",
        "location": "Bengaluru, India",
        "employment_type": "FULL_TIME",
        "salary_min": 2500000,
        "salary_max": 4000000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 5,
    },
    # Vision Labs jobs
    {
        "company": "Vision Labs",
        "title": "Product Designer",
        "description": """Vision Labs is hiring a Product Designer to shape the future of medical imaging interfaces.

**The role:**
- Lead end-to-end design for our radiology AI platform
- Conduct user research with healthcare professionals
- Create wireframes, prototypes, and high-fidelity mockups in Figma
- Build and maintain our design system

**You'll thrive here if you:**
- Have 3+ years of product design experience
- Understand accessibility standards (WCAG 2.1 AA)
- Can articulate design decisions to stakeholders
- Have experience designing for complex enterprise workflows

This is a fully remote position with quarterly team offsites.""",
        "location": "Remote",
        "employment_type": "FULL_TIME",
        "salary_min": 1800000,
        "salary_max": 3000000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 5,
    },
    {
        "company": "Vision Labs",
        "title": "ML Research Intern",
        "description": """6-month paid internship working on state-of-the-art computer vision models for medical imaging.

**What you'll work on:**
- Train and fine-tune vision transformers on proprietary medical datasets
- Collaborate with our research team on novel architectures
- Write experiment tracking code and produce reproducible results
- Present findings in weekly research meetings

**Requirements:**
- Currently pursuing M.Tech/PhD in CS, ML, or related field
- Strong foundation in deep learning (PyTorch preferred)
- Published or ongoing research in computer vision is a plus
- Good communication skills

**Stipend:** ₹50,000 - ₹75,000/month""",
        "location": "Hyderabad, India",
        "employment_type": "INTERNSHIP",
        "salary_min": 50000,
        "salary_max": 75000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 3,
    },
    # Zetabyte jobs
    {
        "company": "Zetabyte",
        "title": "Data Analyst",
        "description": """Join our analytics team to help clients unlock insights from their data.

**Your day-to-day:**
- Build interactive dashboards and reports using our platform
- Work with SQL, Python, and data visualization tools
- Collaborate with client success teams to understand business requirements
- Develop data models and ETL pipelines

**We're looking for:**
- 1-3 years of data analysis experience
- Strong SQL skills (window functions, CTEs, query optimization)
- Proficiency in Python (pandas, numpy)
- Experience with BI tools (Metabase, Looker, or Tableau)
- Excellent communication and presentation skills""",
        "location": "Hyderabad, India",
        "employment_type": "FULL_TIME",
        "salary_min": 800000,
        "salary_max": 1500000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 7,
    },
    {
        "company": "Zetabyte",
        "title": "Platform Engineer",
        "description": """We need a Platform Engineer to build and maintain the infrastructure behind our analytics platform.

**What you'll do:**
- Manage Kubernetes clusters across AWS and GCP
- Build CI/CD pipelines using GitHub Actions and ArgoCD
- Implement monitoring, alerting, and observability (Prometheus, Grafana)
- Automate infrastructure provisioning with Terraform

**Requirements:**
- 3+ years in DevOps/Platform Engineering
- Strong Linux fundamentals
- Experience with container orchestration
- Familiarity with IaC tools""",
        "location": "Hyderabad, India",
        "employment_type": "FULL_TIME",
        "salary_min": 1600000,
        "salary_max": 2800000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 4,
    },
    # TechStack jobs
    {
        "company": "TechStack",
        "title": "Backend Engineer",
        "description": """Work on open-source developer tools used by millions.

**The role:**
- Contribute to our core libraries (TypeScript, Rust)
- Design and implement new APIs for our CLI tools
- Engage with the community through GitHub issues and discussions
- Write documentation and tutorials

**Requirements:**
- 2+ years of professional development experience
- Strong skills in TypeScript or Rust
- Experience maintaining public-facing APIs
- Passion for open source and developer experience

**Perks:** Work from anywhere, 4-day work week, open-source contribution time""",
        "location": "Pune, India",
        "employment_type": "FULL_TIME",
        "salary_min": 1400000,
        "salary_max": 2400000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 2,
    },
    {
        "company": "TechStack",
        "title": "Technical Writer (Contract)",
        "description": """We're looking for a Technical Writer to help document our developer tools.

**Scope:**
- Write API reference documentation
- Create getting-started guides and tutorials
- Review and edit existing documentation for clarity
- Work with engineers to document new features

**Requirements:**
- 2+ years of technical writing experience
- Ability to read and understand code
- Experience with docs-as-code workflows (Markdown, Git)
- Excellent written English

This is a 6-month contract with possibility of extension.""",
        "location": "Remote",
        "employment_type": "CONTRACT",
        "salary_min": 60000,
        "salary_max": 100000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 1,
    },
    # CloudNet jobs
    {
        "company": "CloudNet",
        "title": "DevOps Engineer",
        "description": """Join our DevOps team to build and maintain cloud infrastructure for enterprise clients.

**Responsibilities:**
- Design and manage multi-cloud networking architectures
- Implement zero-trust security models
- Automate deployment workflows
- Troubleshoot production issues and participate in on-call rotation

**Requirements:**
- 3+ years of DevOps experience
- AWS/GCP/Azure certifications preferred
- Strong networking fundamentals (TCP/IP, DNS, VPN, load balancing)
- Experience with Terraform, Ansible, or Pulumi""",
        "location": "Bengaluru, India",
        "employment_type": "FULL_TIME",
        "salary_min": 1800000,
        "salary_max": 3200000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 6,
    },
    # Humanly jobs
    {
        "company": "Humanly",
        "title": "UX Researcher",
        "description": """Help us understand how recruiters and candidates interact with hiring platforms.

**What you'll do:**
- Plan and conduct user research studies (interviews, surveys, usability tests)
- Synthesize findings into actionable insights
- Create personas, journey maps, and research reports
- Collaborate with product and design teams

**You should have:**
- 2+ years of UX research experience
- Experience with both qualitative and quantitative methods
- Strong presentation and storytelling skills
- Background in HCI, psychology, or related field is a plus

Fully remote role with flexible hours.""",
        "location": "Remote",
        "employment_type": "FULL_TIME",
        "salary_min": 1000000,
        "salary_max": 1800000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 5,
    },
    {
        "company": "Humanly",
        "title": "Part-time Content Strategist",
        "description": """We need a Content Strategist to help shape our brand voice and content pipeline.

**Responsibilities:**
- Develop content strategy for blog, social media, and email
- Write thought leadership pieces on HR tech trends
- Collaborate with the marketing team on campaigns
- Manage content calendar and editorial workflow

**Requirements:**
- 2+ years in content marketing or strategy
- Excellent writing skills
- Understanding of B2B SaaS marketing
- Familiarity with SEO best practices

20-25 hours per week. Fully remote.""",
        "location": "Remote",
        "employment_type": "PART_TIME",
        "salary_min": 400000,
        "salary_max": 700000,
        "salary_currency": "INR",
        "status": "OPEN",
        "days_ago": 8,
    },
    # Some closed/draft jobs for variety
    {
        "company": "Acme Corp",
        "title": "Site Reliability Engineer",
        "description": "SRE role focused on improving system reliability and observability.",
        "location": "Bengaluru, India",
        "employment_type": "FULL_TIME",
        "salary_min": 2000000,
        "salary_max": 3500000,
        "salary_currency": "INR",
        "status": "CLOSED",
        "days_ago": 30,
    },
    {
        "company": "Zetabyte",
        "title": "Junior Frontend Developer",
        "description": "Entry-level frontend role for recent graduates.",
        "location": "Hyderabad, India",
        "employment_type": "FULL_TIME",
        "salary_min": 500000,
        "salary_max": 800000,
        "salary_currency": "INR",
        "status": "DRAFT",
        "days_ago": 1,
    },
]


class Command(BaseCommand):
    help = "Seed the database with sample data for Hirely"

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        # Create employer accounts
        employer_profiles = {}
        for company in COMPANIES:
            user, created = User.objects.get_or_create(
                email=company["email"],
                defaults={
                    "name": company["user_name"],
                    "is_active": True,
                },
            )
            if created:
                user.set_password("demo1234")
                user.save()
                self.stdout.write(f"  [+] Created employer user: {company['email']}")

            profile, _ = EmployerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": company["name"],
                    "website": company["website"],
                    "description": company["description"],
                    "verification_status": VerificationStatus.APPROVED,
                },
            )
            employer_profiles[company["name"]] = profile

        # Create seeker accounts
        seeker_profiles = []
        for seeker in SEEKERS:
            user, created = User.objects.get_or_create(
                email=seeker["email"],
                defaults={
                    "name": seeker["name"],
                    "is_active": True,
                },
            )
            if created:
                user.set_password("demo1234")
                user.save()
                self.stdout.write(f"  [+] Created seeker user: {seeker['email']}")

            profile, _ = SeekerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone": seeker["phone"],
                    "bio": seeker["bio"],
                },
            )
            seeker_profiles.append(profile)

        # Create jobs
        now = timezone.now()
        jobs = []
        for job_data in JOBS_DATA:
            employer_profile = employer_profiles[job_data["company"]]
            created_at = now - timedelta(days=job_data["days_ago"])

            job, created = Job.objects.get_or_create(
                employer=employer_profile,
                title=job_data["title"],
                defaults={
                    "description": job_data["description"],
                    "location": job_data["location"],
                    "employment_type": job_data["employment_type"],
                    "salary_min": Decimal(str(job_data["salary_min"])) if job_data.get("salary_min") else None,
                    "salary_max": Decimal(str(job_data["salary_max"])) if job_data.get("salary_max") else None,
                    "salary_currency": job_data.get("salary_currency", "INR"),
                    "status": job_data["status"],
                },
            )
            if created:
                # Backdate the created_at
                Job.objects.filter(pk=job.pk).update(created_at=created_at)
                self.stdout.write(f"  [+] Created job: {job_data['title']} @ {job_data['company']}")
            jobs.append(job)

        # Create applications
        open_jobs = [j for j in jobs if j.status == "OPEN"]
        cover_letters = [
            "I'm very excited about this opportunity. My background in {field} makes me a strong fit for this role. I've been following your company's work and would love to contribute to your mission.",
            "I believe my experience with {field} aligns well with what you're looking for. I'm particularly drawn to the challenges described in this role and the team's focus on quality.",
            "Having worked on similar problems at my previous company, I'm confident I can make an immediate impact. I'm especially interested in the {field} aspects of this position.",
            "This role resonates strongly with my career goals. I have hands-on experience with the technologies mentioned and am eager to bring my skills to your team.",
            "",  # Some applications without cover letters
        ]
        fields = ["frontend development", "backend systems", "data analysis", "product design", "DevOps", "machine learning", "content strategy", "user research"]

        statuses = [
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.REJECTED,
        ]

        application_count = 0
        for seeker_profile in seeker_profiles:
            # Each seeker applies to 3-5 random open jobs
            num_applications = random.randint(3, min(5, len(open_jobs)))
            applied_jobs = random.sample(open_jobs, num_applications)

            for job in applied_jobs:
                cover = random.choice(cover_letters).format(field=random.choice(fields))
                status = random.choice(statuses)
                days_after_posting = random.randint(0, 3)
                applied_at = now - timedelta(days=max(0, job.created_at.day - days_after_posting if hasattr(job.created_at, 'day') else random.randint(0, 5)))

                app, created = Application.objects.get_or_create(
                    job=job,
                    seeker=seeker_profile,
                    defaults={
                        "cover_letter": cover,
                        "status": status,
                    },
                )
                if created:
                    application_count += 1

        self.stdout.write(f"  [+] Created {application_count} applications")

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Seed complete!"))
        self.stdout.write(f"  Employers: {User.objects.filter(employer_profile__isnull=False).count()}")
        self.stdout.write(f"  Seekers:   {User.objects.filter(seeker_profile__isnull=False).count()}")
        self.stdout.write(f"  Jobs:      {Job.objects.count()}")
        self.stdout.write(f"  Applications: {Application.objects.count()}")
        self.stdout.write(f"\n  Demo login:  arjun.sharma@email.com / demo1234")
        self.stdout.write(f"  Employer login: hr@acmecorp.com / demo1234")

