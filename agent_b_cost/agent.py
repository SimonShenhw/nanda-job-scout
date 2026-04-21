"""
agent.py — Core logic for Agent B


Receives job data from Agent A, calls tool functions to calculate
living costs, uses Gemini to generate analysis, and returns results.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
from tools import parse_salary, get_cost_of_living

# Load API Key from .env file
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Gemini model once to save resources
model = genai.GenerativeModel("gemini-2.0-flash")


# ============================================================
# Affordability Rating Function
#
# Based on the 50/30/20 rule, check what percent of salary goes to living costs
# ============================================================

def get_affordability(monthly_cost: float, monthly_salary: float) -> str:
    """
    Returns one of three ratings:
      - Comfortable : Cost is less than 40% of salary
      - Moderate    : Cost is 40–60% of salary
      - Tight       : Cost is more than 60% of salary
    """
    if monthly_salary <= 0:
        return "Tight"

    ratio = monthly_cost / monthly_salary

    if ratio < 0.4:
        return "🟢 Comfortable"
    elif ratio <= 0.6:
        return "🟡 Moderate"
    else:
        return "🔴 Tight"


# ============================================================
# Default market salary data (used when salary is Not Specified)
# ============================================================

DEFAULT_SALARIES = {
    "data scientist":            {"monthly_min": 9583, "monthly_max": 12917},
    "software engineer":         {"monthly_min": 8333, "monthly_max": 12500},
    "machine learning engineer": {"monthly_min": 10000, "monthly_max": 14167},
    "ai engineer":               {"monthly_min": 9583, "monthly_max": 13333},
    "data analyst":              {"monthly_min": 6667, "monthly_max": 9167},
    "product manager":           {"monthly_min": 9167, "monthly_max": 13333},
    "backend engineer":          {"monthly_min": 8333, "monthly_max": 12500},
    "frontend engineer":         {"monthly_min": 7500, "monthly_max": 11250},
    "default":                   {"monthly_min": 7500, "monthly_max": 11000},
}

def get_default_salary(job_title: str) -> dict:
    """
    Fuzzy match job title to get default monthly salary range
    """
    title_lower = job_title.lower()
    for key in DEFAULT_SALARIES:
        if key in title_lower or title_lower in key:
            return DEFAULT_SALARIES[key]
    return DEFAULT_SALARIES["default"]


# ============================================================
# Main Function: Evaluate living cost for one job
# ============================================================

async def evaluate_job(job_title: str, location: str, estimated_salary: str) -> dict:
    """
    This is Agent B's main function, called by the API endpoint in main.py.

    Input:
      - job_title        : Job title
      - location         : City name
      - estimated_salary : Salary string

    Output:
      A full result dict with monthly salary, living costs, surplus, and rating
    """

    # Step 1: Parse salary string and convert to monthly salary
    salary_data = parse_salary(estimated_salary)

    if salary_data["type"] == "not_specified":
        # Use market default data when salary is unknown
        default = get_default_salary(job_title)
        monthly_salary_min = default["monthly_min"]
        monthly_salary_max = default["monthly_max"]
        salary_note = "Salary not listed. Showing market average for this role."
    else:
        monthly_salary_min = salary_data["min"]
        monthly_salary_max = salary_data["max"]
        salary_note = None

    # Midpoint monthly salary (used for affordability calculation)
    monthly_salary_mid = (monthly_salary_min + monthly_salary_max) / 2

    # Step 2: Look up cost of living for the city
    cost_data = get_cost_of_living(location)

    rent_min       = cost_data["rent_min"]
    rent_max       = cost_data["rent_max"]
    food           = cost_data["food"]
    commute        = cost_data["commute"]
    necessities    = cost_data["necessities"]
    city_note      = cost_data.get("city_note")
    city           = cost_data["city"]

    # Step 3: Calculate total monthly living cost range
    total_cost_min = rent_min + food + commute + necessities
    total_cost_max = rent_max + food + commute + necessities
    total_cost_mid = (total_cost_min + total_cost_max) / 2

    # Step 4: Calculate estimated monthly surplus range
    surplus_min = monthly_salary_min - total_cost_max   # 最差情况 / Worst case
    surplus_max = monthly_salary_max - total_cost_min   # 最好情况 / Best case

    # Step 5: Get affordability rating (using midpoint values)
    affordability = get_affordability(total_cost_mid, monthly_salary_mid)

    # Step 6: Use Gemini to generate a one-sentence analysis
    prompt = f"""
You are a helpful career advisor. Give a short, friendly one-sentence comment 
(under 25 words) about this job offer based on the financial data below.
Use simple, clear English.

Job: {job_title} in {city}
Monthly salary range: ${monthly_salary_min:,} - ${monthly_salary_max:,}
Monthly living cost: ${total_cost_min:,} - ${total_cost_max:,}
Financial status: {affordability}

Write only the one sentence. No bullet points. No extra explanation.
"""
    try:
        response = model.generate_content(prompt)
        ai_comment = response.text.strip()
    except Exception:
    
        # Use a default comment if Gemini call fails
        ai_comment = f"This {job_title} role in {city} offers a {affordability.split()[-1].lower()} financial outlook."

    # Step 7: Build the final result dict

    # Short fields sent back to Agent A (only two)
    agent_a_payload = {
        "monthly_cost_range": f"${total_cost_min:,} - ${total_cost_max:,} / mo",
        "affordability":      affordability,
    }

    # Full fields for Agent B's own frontend page
    full_result = {
        "job_title":             job_title,
        "city":                  city,
        "monthly_salary_range":  f"${monthly_salary_min:,} - ${monthly_salary_max:,} / mo",
        "monthly_cost_range":    f"${total_cost_min:,} - ${total_cost_max:,} / mo",
        "monthly_surplus_range": f"${surplus_min:,} - ${surplus_max:,} / mo",
        "affordability":         affordability,
        "ai_comment":            ai_comment,
        "cost_breakdown": {
            "rent":        f"${rent_min:,} - ${rent_max:,} / mo",
            "food":        f"${food:,} / mo",
            "commute":     f"${commute:,} / mo",
            "necessities": f"${necessities:,} / mo",
        },
        "notes": {
            "salary_note": salary_note,
            "city_note":   city_note,
        },
        "for_agent_a": agent_a_payload,
    }

    return full_result
