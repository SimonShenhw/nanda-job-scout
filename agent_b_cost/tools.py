"""
tools.py — Agent B 的底层工具函数
tools.py — Low-level tool functions for Agent B

包含三个工具：薪资解析、生活成本查询、默认薪资参考数据
Contains three tools: salary parsing, cost of living lookup, default salary data
"""

import re
import requests


# ============================================================
# 工具 1：薪资字符串解析器
# Tool 1: Salary String Parser
#
# 把 Agent A 传来的薪资字符串转成月薪的最低值和最高值（美元）
# Convert Agent A's salary string into monthly min and max values (USD)
# ============================================================

def parse_salary(estimated_salary: str) -> dict:
    """
    支持三种格式 / Supports three formats:
      - 时薪 Hourly:  "$30 - $35/hr"   → × 40 × 52 ÷ 12
      - 年薪 Annual:  "$80k - $100k"   → ÷ 12
      - 无数据 None:  "Not Specified"  → 返回 None，交给兜底逻辑处理
                                         Returns None, handled by fallback
    """

    # 如果没有薪资数据，直接返回 None
    # If no salary data, return None right away
    if not estimated_salary or "not specified" in estimated_salary.lower():
        return {"min": None, "max": None, "type": "not_specified", "note": "Salary not specified. Using market average."}

    # 把字符串统一转成小写，方便匹配
    # Convert to lowercase for easier matching
    salary_str = estimated_salary.lower().strip()

    # 用正则表达式提取所有数字（支持 30, 30.5, 80k, 80,000 这些格式）
    # Use regex to find all numbers (handles 30, 30.5, 80k, 80,000 formats)
    raw_numbers = re.findall(r'[\d,]+\.?\d*k?', salary_str)

    # 把提取到的数字字符串转成真正的数字
    # Convert number strings into real numbers
    def to_number(s: str) -> float:
        s = s.replace(',', '')          # 去掉千位逗号 / Remove comma separators
        if s.endswith('k'):
            return float(s[:-1]) * 1000  # 80k → 80000
        return float(s)

    numbers = [to_number(n) for n in raw_numbers if n]

    if not numbers:
        return {"min": None, "max": None, "type": "not_specified"}

    # 只有一个数字时，最低值和最高值都用它
    # If only one number found, use it for both min and max
    val_min = numbers[0]
    val_max = numbers[1] if len(numbers) >= 2 else numbers[0]

    # 判断是时薪还是年薪
    # Check if it is hourly or annual salary
    if "/hr" in salary_str or "per hour" in salary_str or "hourly" in salary_str:
        # 时薪换算月薪：× 40小时/周 × 52周/年 ÷ 12月
        # Hourly to monthly: × 40 hrs/week × 52 weeks/year ÷ 12 months
        monthly_min = round(val_min * 40 * 52 / 12)
        monthly_max = round(val_max * 40 * 52 / 12)
        salary_type = "hourly"
    else:
        # 年薪换算月薪：÷ 12
        # Annual to monthly: ÷ 12
        monthly_min = round(val_min / 12)
        monthly_max = round(val_max / 12)
        salary_type = "annual"

    return {
        "min": monthly_min,
        "max": monthly_max,
        "type": salary_type
    }


# ============================================================
# 工具 2：城市名称清洗器
# Tool 2: City Name Cleaner
#
# 把 Agent A 传来的城市名清洗成 Teleport API 能识别的格式
# Clean the city name from Agent A into a format Teleport API can read
# ============================================================

# 兜底映射表：找不到小城市时，用最近的大城市代替
# Fallback map: if a small city is not found, use the nearest big city
FALLBACK_CITIES = {
    "providence":    "Boston",
    "cambridge":     "Boston",
    "somerville":    "Boston",
    "worcester":     "Boston",
    "newark":        "New York",
    "jersey city":   "New York",
    "long beach":    "Los Angeles",
    "anaheim":       "Los Angeles",
    "henderson":     "Las Vegas",
    "default":       "Boston",   # 所有未知城市的最终兜底 / Final fallback for all unknown cities
}

def clean_city_name(location: str) -> str:
    """
    清洗城市名称，去掉州名缩写和 'Greater' 前缀
    Clean the city name by removing state codes and 'Greater' prefix

    例子 / Examples:
      "Greater Boston Area" → "Boston"
      "Boston, MA"          → "Boston"
      "New York, NY"        → "New York"
    """
    if not location:
        return "Boston"

    city = location.strip()

    # 去掉 "Greater" 前缀和 "Area" 后缀
    # Remove "Greater" prefix and "Area" suffix
    city = re.sub(r'^greater\s+', '', city, flags=re.IGNORECASE)
    city = re.sub(r'\s+area$', '', city, flags=re.IGNORECASE)

    # 去掉逗号后面的州名缩写，如 ", MA" ", NY"
    # Remove state code after comma, e.g. ", MA" or ", NY"
    city = re.sub(r',\s*[A-Z]{2}$', '', city)

    return city.strip()


# ============================================================
# 工具 3：生活成本查询（Teleport API）
# Tool 3: Cost of Living Lookup (Teleport API)
#
# 查询城市的房租和日常开销参考数据
# Look up rent and daily expense data for a city
# ============================================================

# 内置城市参考数据（Teleport API 的兜底）
# Built-in city data as fallback when Teleport API fails
CITY_COST_DATA = {
    "Boston": {
        "rent_min": 2000, "rent_max": 2800,
        "food": 600, "commute": 90, "necessities": 200
    },
    "New York": {
        "rent_min": 2800, "rent_max": 3800,
        "food": 700, "commute": 127, "necessities": 250
    },
    "Los Angeles": {
        "rent_min": 2200, "rent_max": 3200,
        "food": 620, "commute": 150, "necessities": 220
    },
    "Seattle": {
        "rent_min": 1900, "rent_max": 2700,
        "food": 580, "commute": 99, "necessities": 200
    },
    "San Francisco": {
        "rent_min": 2800, "rent_max": 3900,
        "food": 700, "commute": 98, "necessities": 260
    },
    "Austin": {
        "rent_min": 1600, "rent_max": 2300,
        "food": 520, "commute": 80, "necessities": 180
    },
}

def get_cost_of_living(city: str) -> dict:
    """
    先尝试用 Teleport API 查询城市生活成本
    First try to get cost of living data from Teleport API

    如果找不到，自动换成兜底城市（无感）
    If not found, quietly switch to the fallback city
    """
    city_note = None  # 兜底提示信息 / Fallback notice message

    # 先清洗城市名
    # Clean the city name first
    clean_city = clean_city_name(city)

    try:
        # 第一步：用 Teleport API 搜索城市
        # Step 1: Search for the city using Teleport API
        search_url = f"https://api.teleport.org/api/cities/?search={clean_city}&limit=1"
        resp = requests.get(search_url, timeout=10)
        data = resp.json()

        results = data.get("_embedded", {}).get("city:search-results", [])

        if results:
            # 第二步：拿到城市详情链接
            # Step 2: Get the city detail link
            city_url = results[0]["_links"]["city:item"]["href"]
            city_resp = requests.get(city_url, timeout=10)
            city_data = city_resp.json()

            # 第三步：找 urban area 数据（包含生活评分）
            # Step 3: Get urban area data (contains life scores)
            ua_link = city_data.get("_links", {}).get("city:urban_area")

            if ua_link:
                ua_url = ua_link["href"] + "details/"
                ua_resp = requests.get(ua_url, timeout=10)
                ua_data = ua_resp.json()

                # 从 Teleport 数据中提取房租信息
                # Extract rent info from Teleport data
                categories = ua_data.get("categories", [])
                rent_min, rent_max = None, None

                for cat in categories:
                    if "housing" in cat.get("id", "").lower():
                        for item in cat.get("data", []):
                            if "rent" in item.get("id", "").lower():
                                rent_val = item.get("currency_dollar_value")
                                if rent_val:
                                    rent_min = round(rent_val * 0.85)
                                    rent_max = round(rent_val * 1.15)
                                break

                # 如果 Teleport 有租金数据，用 Teleport 的
                # If Teleport has rent data, use it
                if rent_min and rent_max:
                    fallback = CITY_COST_DATA.get(clean_city, CITY_COST_DATA["Boston"])
                    return {
                        "city": clean_city,
                        "rent_min": rent_min,
                        "rent_max": rent_max,
                        "food": fallback["food"],
                        "commute": fallback["commute"],
                        "necessities": fallback["necessities"],
                        "city_note": city_note,
                        "source": "Teleport API"
                    }

    except Exception:
        # API 请求失败时静默处理，使用内置数据
        # If API call fails, silently use built-in data
        pass

    # 兜底逻辑：先查内置数据，找不到就换最近大城市
    # Fallback: check built-in data first, then switch to nearest big city
    if clean_city in CITY_COST_DATA:
        cost = CITY_COST_DATA[clean_city]
    else:
        # 在兜底映射表里找最近的大城市
        # Find the nearest big city in the fallback map
        fallback_city = FALLBACK_CITIES.get(clean_city.lower(), FALLBACK_CITIES["default"])
        cost = CITY_COST_DATA.get(fallback_city, CITY_COST_DATA["Boston"])
        city_note = f"No data found for {clean_city}. Showing {fallback_city} data instead."
        clean_city = fallback_city

    return {
        "city": clean_city,
        "rent_min": cost["rent_min"],
        "rent_max": cost["rent_max"],
        "food": cost["food"],
        "commute": cost["commute"],
        "necessities": cost["necessities"],
        "city_note": city_note,
        "source": "built-in data"
    }