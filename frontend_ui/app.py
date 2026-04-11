from pathlib import Path
import re

import streamlit as st
from PyPDF2 import PdfReader

from api_client import run_module_d_workflow

APP_DIR = Path(__file__).resolve().parent

# ==============================================
# Page config
# ==============================================
st.set_page_config(
    page_title="NANDA Job Scout",
    page_icon="🤖",
    layout="wide",
)

# ==============================================
# Load custom CSS
# ==============================================
with open(APP_DIR / "style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ==============================================
# Salary + affordability helpers
# ==============================================
def _parse_salary_to_annual(salary_text: str):
    if not salary_text or salary_text.lower() == "not specified":
        return None

    salary_lower = salary_text.lower()
    values = [float(v.replace(",", "")) for v in re.findall(r"(\d[\d,]*(?:\.\d+)?)", salary_text)]
    if not values:
        return None

    if "k" in salary_lower and max(values) <= 500:
        values = [v * 1000 for v in values]

    annual_salary = sum(values) / len(values)

    if any(token in salary_lower for token in ["/hr", "per hour", "hour"]):
        annual_salary *= 2080
    elif annual_salary < 1000:
        annual_salary *= 1000

    return annual_salary


def _cost_of_living_index(location_name: str) -> int:
    location_lower = (location_name or "").lower()
    reference = {
        "new york": 95,
        "san francisco": 100,
        "seattle": 82,
        "boston": 80,
        "los angeles": 88,
        "austin": 62,
        "chicago": 70,
        "atlanta": 58,
        "dallas": 57,
        "miami": 74,
    }

    for city, score in reference.items():
        if city in location_lower:
            return score

    return 68


def _affordability_score(salary_text: str, location_name: str):
    annual_salary = _parse_salary_to_annual(salary_text)
    if annual_salary is None:
        return None, "Salary unavailable"

    cost_index = _cost_of_living_index(location_name)
    baseline_cost = 38000 + (cost_index * 650)
    raw_score = int((annual_salary / baseline_cost) * 55)
    score = max(1, min(100, raw_score))

    if score >= 80:
        label = "Excellent fit"
    elif score >= 60:
        label = "Solid fit"
    elif score >= 40:
        label = "Manageable"
    else:
        label = "Tight budget"

    return score, label


def _score_badge(score: int | None, label: str) -> str:
    if score is None:
        return (
            "<span style='background:#F3F4F6; color:#4B5563; padding:4px 10px; "
            "border-radius:999px; font-size:0.78rem; font-weight:600;'>"
            "Affordability: N/A</span>"
        )

    color = "#065F46" if score >= 70 else "#92400E" if score >= 45 else "#991B1B"
    background = "#D1FAE5" if score >= 70 else "#FEF3C7" if score >= 45 else "#FEE2E2"
    return (
        f"<span style='background:{background}; color:{color}; padding:4px 10px; "
        f"border-radius:999px; font-size:0.78rem; font-weight:600;'>"
        f"Cost-of-living score: {score}/100 • {label}</span>"
    )


def _job_key(job: dict) -> str:
    return f"{job.get('company', '').strip().lower()}::{job.get('job_title', '').strip().lower()}"


def _compute_overall_status(service_statuses: dict) -> str:
    if not service_statuses:
        return "waiting"

    statuses = [item.get("status", "waiting") for item in service_statuses.values()]
    if statuses and all(status == "success" for status in statuses):
        return "success"
    if any(status in {"success", "fallback", "waiting"} for status in statuses):
        return "partial"
    return "failed"


def _status_card_html(title: str, status: str, detail: str = "") -> str:
    status_map = {
        "success": ("🟢", "Live Success", "#D1FAE5", "#065F46"),
        "partial": ("🟡", "Partial / Fallback", "#FEF3C7", "#92400E"),
        "fallback": ("🟡", "Fallback", "#FEF3C7", "#92400E"),
        "waiting": ("⚪", "Waiting", "#F3F4F6", "#4B5563"),
        "failed": ("🔴", "Failed", "#FEE2E2", "#991B1B"),
    }
    icon, label, bg, fg = status_map.get(status, status_map["waiting"])
    detail_html = (
        f"<p style='margin:0.45rem 0 0; font-size:0.82rem; color:#555;'>{detail}</p>"
        if detail else ""
    )
    return f"""
        <div style='background:{bg}; border:1px solid rgba(0,0,0,0.06); border-radius:12px; padding:0.9rem 1rem; height:100%;'>
            <div style='font-size:0.8rem; color:#6B7280; text-transform:uppercase; letter-spacing:0.05em;'>{title}</div>
            <div style='margin-top:0.35rem; font-size:1rem; font-weight:700; color:{fg};'>{icon} {label}</div>
            {detail_html}
        </div>
    """


# ==============================================
# Initialize session state
# ==============================================
if "jobs" not in st.session_state:
    st.session_state.jobs = []
if "selected_job" not in st.session_state:
    st.session_state.selected_job = None
if "interview_questions" not in st.session_state:
    st.session_state.interview_questions = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "is_live" not in st.session_state:
    st.session_state.is_live = False
if "job_prep" not in st.session_state:
    st.session_state.job_prep = {}
if "prep_message" not in st.session_state:
    st.session_state.prep_message = ""
if "service_statuses" not in st.session_state:
    st.session_state.service_statuses = {}

# ==============================================
# Sidebar — User inputs
# ==============================================
with st.sidebar:
    st.markdown("# 🤖 NANDA Job Scout")
    st.markdown(
        "<p style='color:#9090B0; font-size:0.85rem; margin-top:-10px;'>"
        "Find matching jobs, prepare for interviews, and compare salary vs. cost of living</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    location = st.text_input(
        "📍 PREFERRED CITY / LOCATION",
        value="Greater Boston Area",
        placeholder="e.g. Greater Boston Area",
    )

    keywords = st.text_input(
        "🎯 SEEKING ROLE / INTEREST",
        value="Data Scientist",
        placeholder="e.g. Data Scientist, Product Analyst, ML Engineer",
    )

    num_results = st.slider(
        "📊 NUMBER OF MATCHES",
        min_value=1,
        max_value=10,
        value=3,
    )

    st.markdown("---")

    uploaded_file = st.file_uploader(
        "📄 UPLOAD RESUME",
        type=["pdf", "txt"],
        help="Your resume is parsed and used to match jobs and generate interview questions.",
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.type == "text/plain":
                st.session_state.resume_text = uploaded_file.read().decode("utf-8")
            else:
                reader = PdfReader(uploaded_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                st.session_state.resume_text = text.strip()

            if st.session_state.resume_text:
                st.success(f"✅ Parsed {uploaded_file.name}")
                with st.expander("📄 Preview extracted resume text"):
                    st.text(st.session_state.resume_text[:500] + "...")
            else:
                st.warning("⚠️ Could not extract text from this file.")
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")

    st.markdown("---")

    scout_button = st.button(
        "✨  Find Matching Jobs", use_container_width=True, type="primary"
    )

    # Show connection status
    overall_sidebar_status = _compute_overall_status(st.session_state.service_statuses)
    if overall_sidebar_status == "success":
        st.markdown(
            "<div style='background:#D1FAE5; color:#065F46; padding:6px 12px;"
            " border-radius:8px; font-size:0.75rem; text-align:center;'>"
            "🟢 Live orchestration active</div>",
            unsafe_allow_html=True,
        )
    elif overall_sidebar_status == "partial" or st.session_state.jobs:
        st.markdown(
            "<div style='background:#FEF3C7; color:#92400E; padding:6px 12px;"
            " border-radius:8px; font-size:0.75rem; text-align:center;'>"
            "🟡 Partial / fallback mode</div>",
            unsafe_allow_html=True,
        )
    elif overall_sidebar_status == "failed":
        st.markdown(
            "<div style='background:#FEE2E2; color:#991B1B; padding:6px 12px;"
            " border-radius:8px; font-size:0.75rem; text-align:center;'>"
            "🔴 Services unavailable</div>",
            unsafe_allow_html=True,
        )

    # Footer
    st.markdown(
        "<div style='position:fixed; bottom:16px; left:16px; "
        "font-size:0.7rem; color:#6B6B8D;'>"
        "Built with Streamlit • NANDA Job Scout"
        "</div>",
        unsafe_allow_html=True,
    )

# ==============================================
# Main content area
# ==============================================

# Header
st.markdown("# 🤖 NANDA Job Scout")
st.markdown(
    "This web app parses your resume, sends one request to **Module D**, and lets the orchestrator coordinate Agent 1 for jobs, Module A for resume guidance, Agent 2 for interview preparation, and Agent 3 for cost-of-living analysis."
)
st.caption("Click **Find Matching Jobs** to invoke `Module D` at `/api/v1/master-graph` and run all four steps together.")

# Handle the scout button click
if scout_button:
    # Validate inputs
    if not location.strip():
        st.warning("⚠️ Please enter a location.")
    elif not keywords.strip():
        st.warning("⚠️ Please enter a target role or area of interest.")
    else:
        with st.spinner("🧭 Module D is orchestrating Agent 1, Module A, Agent 2, and Agent 3 for your request..."):
            result = run_module_d_workflow(
                query=keywords,
                location=location,
                resume_text=st.session_state.resume_text,
            )

        if result["status"] == "success" and result.get("jobs"):
            st.session_state.jobs = result.get("jobs", [])
            st.session_state.is_live = result.get("is_live", False)
            st.session_state.selected_job = None
            st.session_state.interview_questions = []
            st.session_state.chat_history = []
            st.session_state.job_prep = result.get("job_prep", {})
            st.session_state.prep_message = result.get("message", "")
            st.session_state.service_statuses = result.get("service_statuses", {})

            if result.get("overall_status") == "success":
                st.success("✅ Module D orchestration completed successfully.")
            elif result.get("overall_status") == "partial":
                st.info("ℹ️ Module D completed with some fallback content.")
        elif result.get("message"):
            st.session_state.service_statuses = result.get("service_statuses", {})
            st.error(f"❌ {result['message']}")
        else:
            st.error("❌ No jobs found. Try a different role, keyword, or location.")

# ==============================================
# Stats row
# ==============================================
if st.session_state.jobs:
    st.markdown("## 🧭 Multi-Agent Workflow")
    st.caption("These badges mirror the orchestration states you see in Module D for Agent 1, Module A, Agent 2, and the new Agent 3 cost-of-living step.")

    overall_status = _compute_overall_status(st.session_state.service_statuses)
    overall_detail_map = {
        "success": "All connected services returned live results.",
        "partial": "At least one step used fallback/demo data or is waiting for a resume.",
        "failed": "The workflow could not complete successfully.",
        "waiting": "Run a search to see service health.",
    }
    st.markdown(
        _status_card_html("Overall Status", overall_status, overall_detail_map.get(overall_status, "")),
        unsafe_allow_html=True,
    )

    flow1, flow2, flow3, flow4 = st.columns(4)
    flow1.markdown(
        _status_card_html(
            "Agent 1 — Job Scout",
            st.session_state.service_statuses.get("agent1", {}).get("status", "waiting"),
            st.session_state.service_statuses.get("agent1", {}).get("message", "Finds matched jobs."),
        ),
        unsafe_allow_html=True,
    )
    flow2.markdown(
        _status_card_html(
            "Module A — Resume Tailor",
            st.session_state.service_statuses.get("module_a", {}).get("status", "waiting"),
            st.session_state.service_statuses.get("module_a", {}).get("message", "Suggests resume improvements."),
        ),
        unsafe_allow_html=True,
    )
    flow3.markdown(
        _status_card_html(
            "Agent 2 — Interview Prep",
            st.session_state.service_statuses.get("agent2", {}).get("status", "waiting"),
            st.session_state.service_statuses.get("agent2", {}).get("message", "Generates interview questions."),
        ),
        unsafe_allow_html=True,
    )
    flow4.markdown(
        _status_card_html(
            "Agent 3 — Cost of Living",
            st.session_state.service_statuses.get("agent3", {}).get("status", "waiting"),
            st.session_state.service_statuses.get("agent3", {}).get("message", "Evaluates salary against local living costs."),
        ),
        unsafe_allow_html=True,
    )

    if st.session_state.prep_message:
        if overall_status == "success":
            st.success(st.session_state.prep_message or "All services returned live results.")
        elif st.session_state.resume_text:
            st.info(st.session_state.prep_message)
        else:
            st.warning(st.session_state.prep_message)

    with st.expander("View service details"):
        for service_name, info in st.session_state.service_statuses.items():
            st.markdown(f"**{service_name}** — `{info.get('status', 'unknown')}`")
            if info.get("message"):
                st.write(info.get("message"))

    st.markdown("## 📊 Matched Job Openings")

    col1, col2, col3 = st.columns(3)
    jobs = st.session_state.jobs

    col1.metric("Jobs Found", len(jobs))

    all_skills = []
    affordability_scores = []
    for job in jobs:
        all_skills.extend(job.get("core_skills", []))
        prep = st.session_state.job_prep.get(_job_key(job), {})
        cost_details = prep.get("cost_of_living", {})
        score = cost_details.get("affordability_score")
        if score is None:
            score, _ = _affordability_score(job.get("estimated_salary", "Not Specified"), location)
        if score is not None:
            affordability_scores.append(score)

    col2.metric("Unique Skills", len(set(all_skills)))
    avg_score = f"{round(sum(affordability_scores) / len(affordability_scores))}/100" if affordability_scores else "N/A"
    col3.metric("Avg COL Score", avg_score)

    st.markdown("")

    for index, job in enumerate(jobs):
        badges = "".join(
            f"<span class='skill-badge'>{skill}</span>"
            for skill in job.get("core_skills", [])
        )
        salary = job.get("estimated_salary", "Not Specified")
        score, affordability_label = _affordability_score(salary, location)
        if cost_details.get("affordability_score") is not None:
            score = cost_details.get("affordability_score")
            affordability_label = cost_details.get("label", affordability_label)
        score_badge = _score_badge(score, affordability_label)
        prep = st.session_state.job_prep.get(_job_key(job), {})
        highlights = prep.get("candidate_highlights", [])
        resume_tips = prep.get("resume_tips", [])
        questions = prep.get("questions", [])
        cost_details = prep.get("cost_of_living", {})

        with st.expander(f"{job.get('job_title', 'Unknown Role')} — {job.get('company', 'Unknown Company')}", expanded=index == 0):
            st.markdown(
                f"""
                <div style='background:white; border:1px solid #E5E7EB;
                     border-radius:12px; padding:1.2rem 1.5rem;
                     margin-bottom:0.8rem;
                     box-shadow: 0 1px 3px rgba(0,0,0,0.04);'>
                    <div style='display:flex; justify-content:space-between;
                          align-items:start; gap:12px;'>
                        <div>
                            <h3 style='margin:0 0 4px 0; font-size:1.05rem;
                                 color:#1E1E2E;'>{job.get("job_title", "Unknown Role")}</h3>
                            <p style='margin:0; color:#6C63FF; font-weight:600;
                                font-size:0.9rem;'>{job.get("company", "Unknown Company")}</p>
                        </div>
                        <a href='{job.get("apply_link", "#")}' target='_blank'
                           style='background:#6C63FF; color:white;
                           padding:6px 16px; border-radius:8px;
                           text-decoration:none; font-size:0.82rem;
                           font-weight:600; white-space:nowrap;'>
                            Apply →
                        </a>
                    </div>
                    <p style='margin:10px 0 8px; color:#555;
                        font-size:0.88rem;'>{job.get("summary", "No summary available.")}</p>
                    <div style='display:flex; gap:10px; flex-wrap:wrap; margin:0 0 10px;'>
                        <span style='background:#EEF2FF; color:#4338CA; padding:4px 10px;
                             border-radius:999px; font-size:0.78rem; font-weight:600;'>
                            Salary: {salary}
                        </span>
                        {score_badge}
                    </div>
                    <div>{badges}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            overview_tab, resume_tab, interview_tab, cost_tab = st.tabs(
                ["Overview", "Resume Tailoring", "Interview Questions", "Cost of Living"]
            )

            with overview_tab:
                st.markdown("**Why this job was returned:**")
                st.write(job.get("summary", "No summary available."))
                if highlights:
                    st.markdown("**Resume match highlights:**")
                    for item in highlights:
                        st.markdown(f"- {item}")
                else:
                    st.caption("Upload a resume to generate role-specific match highlights.")

            with resume_tab:
                if resume_tips:
                    st.markdown("**How to modify your resume for this job:**")
                    for tip in resume_tips:
                        st.markdown(f"- {tip}")
                else:
                    st.info("Module A tips will appear here after you upload a resume and run the scout flow.")

            with interview_tab:
                if questions:
                    st.markdown("**Questions prepared by Agent 2:**")
                    for idx, question in enumerate(questions, start=1):
                        st.markdown(f"**{idx}.** {question}")
                else:
                    st.info("Upload a resume to generate tailored interview questions for this job.")

            with cost_tab:
                if cost_details:
                    col_a, col_b = st.columns(2)
                    col_a.metric(
                        "Affordability Score",
                        f"{cost_details.get('affordability_score', 'N/A')}/100" if cost_details.get('affordability_score') is not None else "N/A",
                    )
                    col_b.metric(
                        "Cost of Living Index",
                        cost_details.get("cost_of_living_index", "N/A"),
                    )
                    st.markdown(f"**Agent 3 label:** {cost_details.get('label', 'Not available')}")
                    if cost_details.get("recommendation"):
                        st.write(cost_details.get("recommendation"))
                    if cost_details.get("annual_salary_estimate") is not None:
                        st.caption(f"Estimated annual salary used in the calculation: ${cost_details.get('annual_salary_estimate'):,.0f}")
                else:
                    st.info("Agent 3 cost-of-living analysis will appear here when Module D returns it.")

# ==============================================
# Empty state — landing page
# ==============================================
else:
    st.markdown("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div style='text-align:center; padding:2rem 1rem;
                 background:white; border:1px solid #E5E7EB;
                 border-radius:12px;'>
                <div style='font-size:2.5rem; margin-bottom:0.5rem;'>🔎</div>
                <h3 style='margin:0 0 6px;'>Find Matches</h3>
                <p style='color:#666; font-size:0.85rem; margin:0;'>
                    Search job openings using your target role and preferred location
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div style='text-align:center; padding:2rem 1rem;
                 background:white; border:1px solid #E5E7EB;
                 border-radius:12px;'>
                <div style='font-size:2.5rem; margin-bottom:0.5rem;'>📄</div>
                <h3 style='margin:0 0 6px;'>Parse Resume</h3>
                <p style='color:#666; font-size:0.85rem; margin:0;'>
                    Break down your resume so the agents can recommend roles you fit
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div style='text-align:center; padding:2rem 1rem;
                 background:white; border:1px solid #E5E7EB;
                 border-radius:12px;'>
                <div style='font-size:2.5rem; margin-bottom:0.5rem;'>💸</div>
                <h3 style='margin:0 0 6px;'>Prepare + Evaluate</h3>
                <p style='color:#666; font-size:0.85rem; margin:0;'>
                    Generate interview questions and compare salary against cost of living
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.info("👈 Enter your preferences in the sidebar and click **Find Matching Jobs** to get started.")
