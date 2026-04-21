"""
frontend.py — Standalone frontend page for Agent B

Built with Streamlit. Users can enter a city and salary, click Calculate, and see results.

How to run:
  streamlit run frontend.py

  weidong
"""

import requests
import streamlit as st

# ============================================================
# Basic page configuration
# ============================================================

st.set_page_config(
    page_title="Cost of Living Calculator",
    page_icon="🏙️",
    layout="centered"
)

# Agent B backend URL
AGENT_B_URL = "http://localhost:8083"

# ============================================================
# Page title
# ============================================================

st.title("Cost of Living Calculator")
st.caption("Powered by Agent B — NANDA")
st.caption("Developed by Wei Dong")
st.divider()

# ============================================================
# Input section
# ============================================================

st.subheader("Enter Job Details")

# City selector
city = st.selectbox(
    "City",
    options=[
        "Boston, MA",
        "New York, NY",
        "Los Angeles, CA",
        "Seattle, WA",
        "San Francisco, CA",
        "Austin, TX",
    ],
    index=0,
)

# Job title input
job_title = st.text_input(
    "Job Title",
    value="Data Scientist",
    placeholder="e.g. Data Scientist, Software Engineer"
)

# Salary range input (annual)
st.write("Annual Salary Range (USD)")
col1, col2 = st.columns(2)
with col1:
    salary_min = st.number_input(
        "Min",
        min_value=0,
        max_value=500000,
        value=80000,
        step=5000
    )
with col2:
    salary_max = st.number_input(
        "Max",
        min_value=0,
        max_value=500000,
        value=100000,
        step=5000
    )

# Input validation: min salary cannot be higher than max salary
if salary_min > salary_max:
    st.warning("Min salary cannot be higher than max salary.")

st.divider()

# ============================================================
# Calculate button
# ============================================================

if st.button("Calculate", use_container_width=True, type="primary"):

    # Validate job title is not empty
    if not job_title.strip():
        st.error("Please enter a job title.")

    elif salary_min > salary_max:
        st.error("Please fix the salary range before calculating.")

    else:
        # Format annual salary into a string Agent B can read
        salary_str = f"${salary_min:,} - ${salary_max:,}"

        # Show loading spinner
        with st.spinner("Calculating... please wait."):
            try:
                # Call Agent B's evaluate endpoint
                response = requests.post(
                    f"{AGENT_B_URL}/api/v1/evaluate",
                    json={
                        "job_title":        job_title.strip(),
                        "location":         city,
                        "estimated_salary": salary_str,
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                # ============================================================
                # Display results
                # ============================================================

                st.divider()
                st.subheader("Results")

                # Affordability rating (shown prominently)
                st.metric(label="Financial Status", value=data["affordability"])

                st.divider()

              
                # Three key numbers, replace $ to avoid math formula rendering
                salary  = data["monthly_salary_range"].replace("$", "USD ")
                cost    = data["monthly_cost_range"].replace("$", "USD ")
                surplus = data["monthly_surplus_range"].replace("$", "USD ")
                st.write("**Monthly Salary:** " + salary)
                st.write("**Monthly Living Cost:** " + cost)
                st.write("**Monthly Surplus:** " + surplus)

                st.divider()

            
                # AI comment
                st.info(data["ai_comment"])

                
                # Cost breakdown (collapsible)
                with st.expander("Cost Breakdown"):
                    breakdown = data["cost_breakdown"]
                   
                    # Use string concat to avoid $ triggering Streamlit math rendering
                    rent        = breakdown["rent"].replace("$", "USD ")
                    food        = breakdown["food"].replace("$", "USD ")
                    commute     = breakdown["commute"].replace("$", "USD ")
                    necessities = breakdown["necessities"].replace("$", "USD ")
                    st.write("Rent: " + rent)
                    st.write("Food: " + food)
                    st.write("Commute: " + commute)
                    st.write("Necessities: " + necessities)

                # 城市兜底提示（只在使用了兜底城市时显示）
                # City fallback notice (only shown when fallback city was used)
                notes = data.get("notes", {})
                if notes.get("city_note"):
                    st.caption(notes["city_note"])
                if notes.get("salary_note"):
                    st.caption(notes["salary_note"])

            except requests.exceptions.ConnectionError:
                # Agent B 服务未启动时的错误提示
                # Error message when Agent B service is not running
                st.error(
                    "Cannot connect to Agent B. "
                    "Please make sure Agent B is running on port 8083. "
                    "Run: python main.py in the agent_b folder."
                )
            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")
