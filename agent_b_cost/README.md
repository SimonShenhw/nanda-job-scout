# Agent 3 — CostCompass (Cost of Living Calculator)
Developed by Wei Dong | AAI 6600 | Northeastern University

## What This Agent Does
CostCompass is a standalone AI agent that calculates the cost of living 
for US cities and evaluates whether a job's salary is enough to live 
there comfortably.

It works alongside Agent A (Job Scout) in this repository. After Agent A 
finds job listings, Agent B adds two fields to each job card:
- monthly_cost_range: estimated monthly living cost for that city
- affordability: financial status rating (Comfortable / Moderate / Tight)

## Files
- main.py      — FastAPI service (port 8083)
- agent.py     — Core calculation logic + Gemini AI comment
- tools.py     — Salary parsing, city lookup, cost data
- frontend.py  — Streamlit web page

## Live Deployment
- Frontend: http://66.228.47.228:8501
- API: http://66.228.47.228:8083
- Health Check: http://66.228.47.228:8083/health

## How to Connect Agent B to This Project
See integration guide: 
https://github.com/appleorbit/AAI-6600_Team-project_NANDA_agent-b

## Why Agent B became Agent 3
During development, this agent was internally called Agent B — but it has been renamed to Agent 3 to align with the team's naming convention.
