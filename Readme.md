
⸻

🩺 HealthSync

Web-Based Personal Health & Wellness Management System
Built with Python & Django

⸻

📌 Project Overview

HealthSync is a role-based web application designed to help users monitor personal health metrics, access medically reviewed articles, participate in a health community, and receive doctor specialization suggestions through a rule-based symptom checker.

This is an academic project built using Django following proper software engineering practices (SRS, UML, RBAC, modular design).

⸻

🎯 Core Objectives
	•	Allow users to track daily health metrics.
	•	Provide medically reviewed health articles.
	•	Enable moderated community discussions.
	•	Suggest doctor specializations based on symptoms.
	•	Implement Role-Based Access Control (RBAC).
	•	Maintain structured and scalable Django architecture.

⸻

👥 User Roles (RBAC)

The system contains 3 actors:

1️⃣ User
	•	Register / Login
	•	Update profile
	•	Track health logs
	•	View health score
	•	Read articles
	•	Post articles (draft)
	•	Participate in community discussions
	•	Use symptom checker

2️⃣ Doctor
	•	Review submitted articles
	•	Approve or reject articles
	•	Provide medical validation

3️⃣ Admin
	•	Full system access
	•	Manage users & doctors
	•	Assign roles
	•	Moderate community posts
	•	Publish approved articles
	•	Control article visibility

⸻

🏗 System Architecture

HealthSync follows Django’s MVT (Model-View-Template) architecture.

Main Components:
	•	Authentication & Role Management
	•	Health Tracking Module
	•	Article Management Module
	•	Community Discussion Module
	•	Symptom Checker Module
	•	Admin Moderation Panel

⸻

🧠 Symptom Checker Design

⚠️ Important:
This is a static rule-based system, NOT AI-based medical diagnosis.


User selects symptoms
        ↓
System maps symptoms → Specialization
        ↓
Specialization maps → Available Doctors
        ↓
System suggests doctor specialization
Data Mapping:
	•	Symptom → Specialization
	•	Specialization → Doctor

No medical diagnosis is provided.

⸻

🗃 Database Model Overview

Core Entities

User
	•	id
	•	name
	•	email
	•	password
	•	role (User / Doctor / Admin)

HealthLog
	•	user (ForeignKey)
	•	sleep_hours
	•	water_intake
	•	exercise_minutes
	•	mood
	•	meals
	•	weight
	•	date
	•	health_score (calculated field)

Article
	•	author (User)
	•	title
	•	content
	•	status (Draft / Under Review / Approved / Published / Rejected)
	•	reviewed_by (Doctor)
	•	created_at

Comment
	•	article (ForeignKey)
	•	user (ForeignKey)
	•	content
	•	created_at

CommunityPost
	•	user (ForeignKey)
	•	title
	•	content
	•	created_at
	•	status (Active / Flagged / Removed)

Symptom
	•	name
	•	specialization (ForeignKey)

Specialization
	•	name
	•	description

Doctor
	•	user (OneToOne with User)
	•	specialization (ForeignKey)
	•	license_number

⸻

📊 Health Score Calculation

Health score is calculated based on:
	•	Sleep duration
	•	Water intake
	•	Exercise time
	•	Mood rating
	•	Meal consistency
	•	Weight tracking consistency

Formula is rule-based and can be improved later.

⸻

🔐 Security & Access Control
	•	Django Authentication System
	•	Role-Based Access Control (RBAC)
	•	Admin-only management routes
	•	Doctor-only review routes
	•	User-specific health logs (data isolation)

⸻

healthsync/
│
├── accounts/          # User authentication & roles
├── health/            # Health logs & score calculation
├── articles/          # Article posting & review
├── community/         # Community discussions
├── symptom_checker/   # Rule-based symptom mapping
├── templates/
├── static/
├── manage.py
└── settings.py
⸻

🚀 Future Improvements
	•	AI-based symptom analysis
	•	REST API integration
	•	Weekly/monthly analytics dashboard
	•	Doctor appointment booking
	•	Email notifications
	•	Health trend graphs
	•	Mobile responsiveness improvements

⸻

⚙️ Development Stack
	•	Python
	•	Django
	•	SQLite (development)
	•	HTML / CSS
	•	Bootstrap / Custom UI (Glassmorphism planned)

⸻
📜 License

Academic Project – Not for commercial medical use.

⸻
