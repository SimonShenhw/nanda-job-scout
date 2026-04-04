"""
frontend.py — Agent B 的独立前端页面
frontend.py — Standalone frontend page for Agent B

使用 Streamlit 构建，用户可以输入城市和薪资，点击计算查看生活成本评估结果。
Built with Streamlit. Users can enter a city and salary, click Calculate, and see results.

启动命令 / How to run:
  streamlit run frontend.py
"""

import requests
import streamlit as st

# ============================================================
# 页面基础配置
# Basic page configuration
# ============================================================

st.set_page_config(
    page_title="Cost of Living Calculator",
    page_icon="🏙️",
    layout="centered"
)

# Agent B 的后端地址
# Agent B backend URL
AGENT_B_URL = "http://localhost:8083"

# ============================================================
# 页面标题
# Page title
# ============================================================

st.title("Cost of Living Calculator")
st.caption("Powered by Agent B — NANDA")
st.caption("Developed by Wei Dong")
st.divider()

# ============================================================
# 输入区域
# Input section
# ============================================================

st.subheader("Enter Job Details")

# 城市选择框
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

# 职位输入框
# Job title input
job_title = st.text_input(
    "Job Title",
    value="Data Scientist",
    placeholder="e.g. Data Scientist, Software Engineer"
)

# 薪资范围输入（年薪）
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

# 输入校验：最低薪资不能高于最高薪资
# Input validation: min salary cannot be higher than max salary
if salary_min > salary_max:
    st.warning("Min salary cannot be higher than max salary.")

st.divider()

# ============================================================
# 计算按钮
# Calculate button
# ============================================================

if st.button("Calculate", use_container_width=True, type="primary"):

    # 校验职位名称不能为空
    # Validate job title is not empty
    if not job_title.strip():
        st.error("Please enter a job title.")

    elif salary_min > salary_max:
        st.error("Please fix the salary range before calculating.")

    else:
        # 把年薪格式化成 Agent B 能识别的字符串
        # Format annual salary into a string Agent B can read
        salary_str = f"${salary_min:,} - ${salary_max:,}"

        # 显示加载动画
        # Show loading spinner
        with st.spinner("Calculating... please wait."):
            try:
                # 调用 Agent B 的评估接口
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
                # 显示结果
                # Display results
                # ============================================================

                st.divider()
                st.subheader("Results")

                # 财务状态（大字显示）
                # Affordability rating (shown prominently)
                st.metric(label="Financial Status", value=data["affordability"])

                st.divider()

                # 三个核心数字分行显示，替换 $ 避免数学公式渲染
                # Three key numbers, replace $ to avoid math formula rendering
                salary  = data["monthly_salary_range"].replace("$", "USD ")
                cost    = data["monthly_cost_range"].replace("$", "USD ")
                surplus = data["monthly_surplus_range"].replace("$", "USD ")
                st.write("**Monthly Salary:** " + salary)
                st.write("**Monthly Living Cost:** " + cost)
                st.write("**Monthly Surplus:** " + surplus)

                st.divider()

                # AI 点评
                # AI comment
                st.info(data["ai_comment"])

                # 费用明细（可折叠）
                # Cost breakdown (collapsible)
                with st.expander("Cost Breakdown"):
                    breakdown = data["cost_breakdown"]
                    # 用字符串拼接避免 $ 触发 Streamlit 数学公式渲染
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