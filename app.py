import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 페이지 기본 설정 & 모바일 전용 CSS 주입
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="부산 부동산 실질 주거비 시뮬레이터",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"  # 모바일에서 메인 화면이 먼저 시원하게 보이도록 설정
)

# 모바일 가독성 극대화를 위한 반응형 CSS
st.markdown("""
<style>
    /* 전체 여백 조정 */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    /* 모바일 메트릭 폰트 크기 최적화 */
    [data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
    }
    /* 탭 메뉴 터치 영역 확대 */
    .stTabs [data-baseweb="tab"] {
        padding: 8px 12px !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
    }
    /* 안내 박스 모바일 여백 */
    .mobile-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏠 부산 부동산 주거비 시뮬레이터")
st.caption("기회비용 · 숨은 부대비용 · 청년/신혼 정책대출 · 월 적립식 복리투자 엔진")

# 모바일 사이드바 유도 안내
st.info("👈 **조건 변경**: 좌측 상단 화살표 `>` 를 누르면 **내 자산, 연봉, 매물 시세**를 바꿀 수 있습니다.")

# -----------------------------------------------------------------------------
# 사이드바: 입력 제어 패널
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("1. 매물 정보 설정")
    district = st.selectbox(
        "부산 자치구 선택",
        ["부산진구", "해운대구", "수영구", "연제구", "남구", "동래구", "기장군", "사하구", "북구", "금정구", "강서구"]
    )
    
    col1, col2 = st.columns(2)
    with col1:
        buy_price = st.number_input("매매 시세 (만원)", value=50000, step=1000)
        monthly_deposit = st.number_input("월세 보증금 (만원)", value=2000, step=500)
    with col2:
        jeonse_price = st.number_input("전세 보증금 (만원)", value=19000, step=1000)
        monthly_rent = st.number_input("월세액 (만원/월)", value=95, step=5)

    st.markdown("---")
    st.header("2. 내 자산 및 조건")
    user_cash = st.number_input("보유 순자산 (만원)", value=4000, step=1000)
    user_income = st.number_input("연봉 / 총급여 (만원)", value=4000, step=500, help="월세 세액공제 및 정책대출 소득 심사에 사용됩니다.")
    
    is_youth = st.checkbox("만 19세 ~ 34세 청년", value=True, help="청년전용 버팀목 전세자금(최대 1.5억원 한도) 지원 대상 여부입니다.")
    is_married = st.checkbox("신혼부부 (혼인 7년 이내)", value=False)
    has_newborn = st.checkbox("신생아 출산/입양 (2년 이내)", value=False)
    is_first_buyer = st.checkbox("생애최초 주택구입", value=False)

    st.markdown("---")
    st.header("3. 대체투자 기회비용 엔진")
    
    monthly_invest_budget = st.number_input(
        "매월 저축/투자 가능 예산 (만원/월)", 
        value=150, 
        min_value=0, 
        step=10,
        help="월급 중 주거비(이자/월세) 지출 및 금융투자에 투입할 수 있는 총 가용 자금입니다."
    )
    
    with st.expander("💡 **적립식 복리 엔진이란? (원리 보기)**"):
        st.markdown(f"""
        **Q. 어떻게 적용되나요?**
        - 매달 월급에서 모으는 **{monthly_invest_budget}만원** 중, 각 주거방식의 **월 주거비(대출이자/월세)를 먼저 지출**합니다.
        - **지출하고 남은 잔여 월급**이 매달 주식/ETF/예적금에 **자동으로 적립식 복리 투자**되어 자산으로 쌓입니다!
        - 특히 **월세**의 경우, 연말정산으로 돌려받는 **세액공제 환급금까지 전액 재투자**되어 복리로 굴러갑니다.
        """)

    invest_preset = st.radio(
        "투자 성향 프리셋",
        ["보수적 (예적금 3.5%)", "중립적 (배당/채권 5.0%)", "적극적 (S&P 500 ETF 8.0%)", "직접 입력"],
        index=2
    )
    
    if invest_preset == "보수적 (예적금 3.5%)":
        pre_tax_rate = 3.5
    elif invest_preset == "중립적 (배당/채권 5.0%)":
        pre_tax_rate = 5.0
    elif invest_preset == "적극적 (S&P 500 ETF 8.0%)":
        pre_tax_rate = 8.0
    else:
        pre_tax_rate = st.slider("기대 연수익률 (%)", min_value=1.0, max_value=15.0, value=8.0, step=0.5)

    after_tax_rate = (pre_tax_rate / 100) * (1 - 0.154)
    monthly_r = ((1 + after_tax_rate) ** (1/12)) - 1
    st.info(f"💡 세후 실질 복리 수익률: **연 {after_tax_rate*100:.2f}%** 적용")

    st.markdown("---")
    st.header("4. 시뮬레이션 변수")
    holding_years = st.slider("예상 거주 기간 (년)", min_value=1, max_value=10, value=2, step=1)
    price_growth_rate = st.slider("연평균 집값 상승률 가정 (%)", min_value=-3.0, max_value=6.0, value=3.0, step=0.5) / 100

# -----------------------------------------------------------------------------
# 탭 구성: [탭 1: 의사결정 시뮬레이터] / [탭 2: 부산 시세 트렌드]
# -----------------------------------------------------------------------------
tab1, tab2 = st.tabs(["📊 1. 주거비 & BEP 시뮬레이터", "📈 2. 부산 연도별 시세 트렌드"])

with tab1:
    # 1. 깡통전세 위험도
    jeonse_ratio = (jeonse_price / buy_price) * 100
    if jeonse_ratio < 70:
        risk_badge = f"🟢 **안전 매물** (전세가율 {jeonse_ratio:.1f}%) : HUG 보증보험 할인 구간"
        badge_color = "success"
    elif jeonse_ratio <= 80:
        risk_badge = f"🟡 **주의 요망** (전세가율 {jeonse_ratio:.1f}%) : 보증금 미반환 대비 보증보험 가입 필수"
        badge_color = "warning"
    else:
        risk_badge = f"🔴 **깡통전세 위험 매물** (전세가율 {jeonse_ratio:.1f}%) : 매매가 하락 시 보증금 미반환 위험"
        badge_color = "error"

    # 2. 월세 세액공제 계산 엔진
    annual_rent_paid = monthly_rent * 12
    tax_credit_base = min(1000.0, float(annual_rent_paid))

    if user_income <= 5500:
        rent_tax_credit_rate = 0.17
        annual_tax_refund = tax_credit_base * rent_tax_credit_rate
        tax_credit_desc = f"연봉 5,500만 이하(17%) ➔ **연 {annual_tax_refund:.0f}만원 환급**"
    elif user_income <= 8000:
        rent_tax_credit_rate = 0.15
        annual_tax_refund = tax_credit_base * rent_tax_credit_rate
        tax_credit_desc = f"연봉 8,000만 이하(15%) ➔ **연 {annual_tax_refund:.0f}만원 환급**"
    else:
        rent_tax_credit_rate = 0.0
        annual_tax_refund = 0.0
        tax_credit_desc = "연봉 8,000만원 초과 (세액공제 대상 제외)"

    # 3. 매수 초기 부대비용 계산
    acq_tax_rate = 0.011 if buy_price <= 60000 else (0.022 if buy_price <= 90000 else 0.033)
    buy_initial_costs = (buy_price * acq_tax_rate) + (buy_price * 0.004) + 80
    buy_total_required = buy_price + buy_initial_costs
    buy_annual_holding = (buy_price * 0.69 * 0.002) + 36

    # 4. 현실적 대출 한도 검증
    def evaluate_realistic_loans():
        policy_buy = None
        if user_cash <= 51100 and buy_price <= 90000:
            if has_newborn and user_income <= 13000:
                policy_buy = {"name": "신생아 특례 디딤돌", "rate": 1.6, "limit": 40000}
            elif is_married and user_income <= 8500 and buy_price <= 60000:
                policy_buy = {"name": "신혼부부 디딤돌", "rate": 2.45, "limit": 32000}
            elif user_income <= 6000 and buy_price <= 50000:
                policy_buy = {"name": "내집마련 디딤돌", "rate": 2.65, "limit": 20000}

        commercial_ltv = 0.8 if is_first_buyer else 0.7
        commercial_buy_limit = buy_price * commercial_ltv
        commercial_buy = {"name": f"시중 주담대(LTV {int(commercial_ltv*100)}%)", "rate": 3.8, "limit": commercial_buy_limit}

        is_buy_possible = True
        buy_shortfall = 0
        final_buy_loan = None

        if policy_buy and (user_cash + policy_buy["limit"] >= buy_total_required):
            final_buy_loan = policy_buy
            final_buy_loan["reason"] = f"✅ 정부 주택도시기금 정책대출 요건 충족 ({policy_buy['rate']}%)"
            final_buy_loan_amt = buy_total_required - user_cash
        elif user_cash + commercial_buy_limit >= buy_total_required:
            final_buy_loan = commercial_buy
            final_buy_loan["reason"] = f"디딤돌 한도 부족으로 시중 주담대(최대 {commercial_buy_limit/10000:.1f}억원)로 자동 전환"
            final_buy_loan_amt = buy_total_required - user_cash
        else:
            is_buy_possible = False
            buy_shortfall = buy_total_required - (user_cash + commercial_buy_limit)
            final_buy_loan = commercial_buy
            final_buy_loan["reason"] = f"보유자산과 최대 대출금을 합쳐도 매수자금에 미치지 못합니다."
            final_buy_loan_amt = commercial_buy_limit

        # 전세 대출
        policy_jeonse = None
        if user_cash <= 34500:
            if has_newborn and user_income <= 13000 and jeonse_price <= 40000:
                policy_jeonse = {"name": "신생아 특례 버팀목", "rate": 1.1, "limit": min(24000, jeonse_price * 0.8)}
            elif is_youth and user_income <= 5000 and jeonse_price <= 30000:
                policy_jeonse = {"name": "청년전용 버팀목", "rate": 2.0, "limit": min(15000, jeonse_price * 0.8)}
            elif is_married and user_income <= 7500 and jeonse_price <= 30000:
                policy_jeonse = {"name": "신혼부부 버팀목", "rate": 1.9, "limit": min(16000, jeonse_price * 0.8)}
            elif user_income <= 5000 and jeonse_price <= 20000:
                policy_jeonse = {"name": "일반 버팀목전세", "rate": 2.3, "limit": min(8000, jeonse_price * 0.7)}

        commercial_jeonse_limit = jeonse_price * 0.8
        commercial_jeonse = {"name": "시중 전세대출(80%)", "rate": 3.6, "limit": commercial_jeonse_limit}

        is_jeonse_possible = True
        jeonse_shortfall = 0
        final_jeonse_loan = None

        if policy_jeonse and (user_cash + policy_jeonse["limit"] >= jeonse_price):
            final_jeonse_loan = policy_jeonse
            final_jeonse_loan["reason"] = f"✅ 정부 {policy_jeonse['name']} 요건 충족 (연 {policy_jeonse['rate']}%)"
            final_jeonse_loan_amt = max(0, jeonse_price - user_cash)
        elif user_cash + commercial_jeonse_limit >= jeonse_price:
            final_jeonse_loan = commercial_jeonse
            final_jeonse_loan["reason"] = "정부 대출 한도 초과로 시중은행 전세대출(80%) 적용"
            final_jeonse_loan_amt = max(0, jeonse_price - user_cash)
        else:
            is_jeonse_possible = False
            jeonse_shortfall = jeonse_price - (user_cash + commercial_jeonse_limit)
            final_jeonse_loan = commercial_jeonse
            final_jeonse_loan["reason"] = f"보유자산과 최대 대출로도 전세보증금 부족"
            final_jeonse_loan_amt = commercial_jeonse_limit

        return (is_buy_possible, buy_shortfall, final_buy_loan, final_buy_loan_amt,
                is_jeonse_possible, jeonse_shortfall, final_jeonse_loan, final_jeonse_loan_amt)

    (is_buy_possible, buy_shortfall, buy_loan, buy_loan_amt,
     is_jeonse_possible, jeonse_shortfall, jeonse_loan, jeonse_loan_amt) = evaluate_realistic_loans()

    # 5. 매월 주거비 및 월 잉여 투자금 산출
    buy_annual_interest = buy_loan_amt * (buy_loan["rate"] / 100)
    buy_monthly_cost = (buy_annual_interest + buy_annual_holding) / 12
    buy_free_cash = max(0, user_cash - (buy_total_required - buy_loan_amt))

    jeonse_annual_interest = jeonse_loan_amt * (jeonse_loan["rate"] / 100)
    jeonse_annual_guarantee = jeonse_price * 0.0012
    jeonse_monthly_cost = (jeonse_annual_interest + jeonse_annual_guarantee) / 12
    jeonse_free_cash = max(0, user_cash - (jeonse_price - jeonse_loan_amt))

    monthly_monthly_cost = monthly_rent
    monthly_free_cash = max(0, user_cash - monthly_deposit)

    buy_monthly_invest = max(0.0, monthly_invest_budget - buy_monthly_cost)
    jeonse_monthly_invest = max(0.0, monthly_invest_budget - jeonse_monthly_cost)
    monthly_monthly_invest = max(0.0, monthly_invest_budget - monthly_monthly_cost)

    # 6. 복리 미래가치 함수
    def calculate_investment_details(initial_lump_sum, monthly_contribution, years_count, annual_extra_cash=0.0):
        lump_fv = initial_lump_sum * ((1 + after_tax_rate) ** years_count)
        months_total = years_count * 12
        if monthly_r > 0:
            monthly_fv = monthly_contribution * (((1 + monthly_r) ** months_total - 1) / monthly_r)
        else:
            monthly_fv = monthly_contribution * months_total

        extra_fv = 0.0
        if annual_extra_cash > 0:
            for y in range(1, years_count + 1):
                rem_years = years_count - y
                extra_fv += annual_extra_cash * ((1 + after_tax_rate) ** rem_years)

        total_fv = lump_fv + monthly_fv + extra_fv
        total_principal = initial_lump_sum + (monthly_contribution * months_total) + (annual_extra_cash * years_count)
        pure_gain = total_fv - total_principal
        return total_fv, total_principal, pure_gain

    years = list(range(1, 11))
    buy_trajectory, jeonse_trajectory, monthly_trajectory = [], [], []
    buy_fvs, jeonse_fvs, monthly_fvs = [], [], []
    buy_cum_costs, jeonse_cum_costs, monthly_cum_costs = [], [], []
    bep_year = None

    for t in years:
        if is_buy_possible:
            future_val = buy_price * ((1 + price_growth_rate) ** t)
            buy_fv, _, _ = calculate_investment_details(buy_free_cash, buy_monthly_invest, t, 0.0)
            buy_nw = future_val - buy_loan_amt + buy_fv
            b_cost = buy_monthly_cost * 12 * t
        else:
            buy_nw, buy_fv, b_cost = None, 0, 0
        buy_trajectory.append(buy_nw)
        buy_fvs.append(buy_fv)
        buy_cum_costs.append(b_cost)

        if is_jeonse_possible:
            jeonse_fv, _, _ = calculate_investment_details(jeonse_free_cash, jeonse_monthly_invest, t, 0.0)
            jeonse_nw = (jeonse_price - jeonse_loan_amt) + jeonse_fv
            j_cost = jeonse_monthly_cost * 12 * t
        else:
            jeonse_nw, jeonse_fv, j_cost = None, 0, 0
        jeonse_trajectory.append(jeonse_nw)
        jeonse_fvs.append(jeonse_fv)
        jeonse_cum_costs.append(j_cost)

        monthly_fv, _, _ = calculate_investment_details(monthly_free_cash, monthly_monthly_invest, t, annual_tax_refund)
        monthly_nw = monthly_deposit + monthly_fv
        m_cost = (monthly_monthly_cost * 12 * t) - (annual_tax_refund * t)
        monthly_trajectory.append(monthly_nw)
        monthly_fvs.append(monthly_fv)
        monthly_cum_costs.append(m_cost)

        if is_buy_possible and bep_year is None:
            comp_targets = [v for v in [jeonse_nw, monthly_nw] if v is not None]
            if comp_targets and buy_nw > max(comp_targets):
                bep_year = t

    # 7. 최적 전략 도출
    cur_idx = holding_years - 1
    cur_buy = buy_trajectory[cur_idx]
    cur_jeonse = jeonse_trajectory[cur_idx]
    cur_monthly = monthly_trajectory[cur_idx]

    cur_buy_fv, cur_jeonse_fv, cur_monthly_fv = buy_fvs[cur_idx], jeonse_fvs[cur_idx], monthly_fvs[cur_idx]
    cur_buy_cost, cur_jeonse_cost, cur_monthly_cost = buy_cum_costs[cur_idx], jeonse_cum_costs[cur_idx], monthly_cum_costs[cur_idx]

    valid_options = {}
    if is_buy_possible:
        valid_options["매매"] = cur_buy
    if is_jeonse_possible:
        valid_options["전세"] = cur_jeonse
    valid_options["월세"] = cur_monthly

    best_key = max(valid_options, key=valid_options.get)
    best_val = valid_options[best_key]

    if best_key == "매매":
        best_strategy = "매매 (자가 구입)"
        strategy_msg = f"집값 상승분(연 {price_growth_rate*100:.1f}%)과 레버리지 효과가 대출 이자비용을 압도합니다."
    elif best_key == "전세":
        best_strategy = "전세"
        strategy_msg = f"저금리 정책대출({jeonse_loan['name']} {jeonse_loan['rate']}%)로 주거비를 아끼고 남은 월급을 복리 투자한 결과가 가장 유리합니다."
    else:
        best_strategy = "월세"
        strategy_msg = f"보증금 부담이 적어 목돈과 월세 세액공제금을 금융상품에 집중 복리 투자한 결과가 가장 우세합니다."

    # 상단 뱃지 알림
    if badge_color == "success":
        st.success(f"📍 **{district} 시세**: {risk_badge}")
    elif badge_color == "warning":
        st.warning(f"📍 **{district} 시세**: {risk_badge}")
    else:
        st.error(f"📍 **{district} 시세**: {risk_badge}")

    # 최종 추천 헤더
    st.subheader(f"🎯 {holding_years}년 거주 시 추천: **'{best_strategy}'**")
    st.markdown(f"> {strategy_msg} (예상 최종 자산: **{best_val/10000:.2f}억원**)")

    # -------------------------------------------------------------
    # [모바일 특화 UI 1] 한눈에 보는 3자 핵심 지표 미니 스코어보드
    # -------------------------------------------------------------
    st.markdown(f"""
    <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; padding:12px; margin-bottom:15px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size:12px; font-weight:700; color:#475569; margin-bottom:8px;">📱 모바일 한눈에 3자 비교 요약 ({holding_years}년 기준)</div>
        <table style="width:100%; font-size:12px; text-align:center; border-collapse:collapse;">
            <tr style="background:#f1f5f9; color:#334155; border-bottom:1px solid #cbd5e1;">
                <th style="padding:6px 2px;">항목</th>
                <th style="padding:6px 2px; color:#4f46e5;">🏠 매매</th>
                <th style="padding:6px 2px; color:#059669;">🔑 전세</th>
                <th style="padding:6px 2px; color:#d97706;">📄 월세</th>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:8px 2px; font-weight:600; color:#64748b;">최종자산</td>
                <td style="padding:8px 2px; font-weight:700; color:{'#4f46e5' if is_buy_possible else '#ef4444'};">
                    {f"{cur_buy/10000:.2f}억" if is_buy_possible else "매매불가"}
                </td>
                <td style="padding:8px 2px; font-weight:700; color:#059669;">{cur_jeonse/10000:.2f}억</td>
                <td style="padding:8px 2px; font-weight:700; color:#d97706;">{cur_monthly/10000:.2f}억</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:8px 2px; font-weight:600; color:#64748b;">월 주거비</td>
                <td style="padding:8px 2px; color:#334155;">{f"월 {buy_monthly_cost:.0f}만" if is_buy_possible else "-"}</td>
                <td style="padding:8px 2px; color:#334155;">월 {jeonse_monthly_cost:.0f}만</td>
                <td style="padding:8px 2px; color:#334155;">월 {monthly_monthly_cost:.0f}만</td>
            </tr>
            <tr>
                <td style="padding:8px 2px; font-weight:600; color:#64748b;">월 투자금</td>
                <td style="padding:8px 2px; color:#334155;">{f"월 {buy_monthly_invest:.0f}만" if is_buy_possible else "-"}</td>
                <td style="padding:8px 2px; color:#334155;">월 {jeonse_monthly_invest:.0f}만</td>
                <td style="padding:8px 2px; color:#334155;">월 {monthly_monthly_invest:.0f}만</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 8. 3개 상세 비교 카드
    # -------------------------------------------------------------
    mcol1, mcol2, mcol3 = st.columns(3)
    
    # [매매 카드]
    with mcol1:
        if is_buy_possible:
            st.metric(label="🏠 매매 최종 자산", value=f"{cur_buy/10000:.2f} 억원", delta=f"{buy_loan['name']} ({buy_loan['rate']:.2f}%)")
            st.caption(f"• 대출: {buy_loan_amt/10000:.1f}억 (월이자 약 {buy_annual_interest/12:.0f}만원)")
            st.caption(f"• {holding_years}년 불어난 총 투자자산: :green[**약 {cur_buy_fv:.0f}만원**]")
            st.caption(f"• {holding_years}년 누적 총 주거비: :red[**약 {cur_buy_cost:.0f}만원**]")
            future_prop_cur = buy_price * ((1 + price_growth_rate) ** holding_years)
            st.info(f"💡 미래 집값({future_prop_cur/10000:.2f}억) - 대출상환({buy_loan_amt/10000:.2f}억) + 투자자산({cur_buy_fv/10000:.2f}억) = **{cur_buy/10000:.2f}억원**")
        else:
            st.metric(label="🏠 매매 (자가 구입)", value="❌ 매매 불가", delta=f"부족: 약 {buy_shortfall/10000:.2f}억원", delta_color="inverse")
            with st.popover("🔍 매매 불가 상세 사유"):
                st.error(f"총 필요자금({buy_total_required/10000:.2f}억) 대비 내 자본과 대출금이 부족합니다.\n\n최소 **약 {buy_shortfall/10000:.2f}억원**의 추가 자기자본이 필요합니다.")
            st.caption("• 디딤돌 및 시중 주담대 최대 한도로도 잔금 부족")
            st.caption(f"• 추가 필요 자본: **약 {buy_shortfall/10000:.2f}억원**")

    # [전세 카드]
    with mcol2:
        if is_jeonse_possible:
            st.metric(label="🔑 전세 최종 자산", value=f"{cur_jeonse/10000:.2f} 억원", delta=f"{jeonse_loan['name']} ({jeonse_loan['rate']:.2f}%)")
            my_jeonse_deposit = (jeonse_price - jeonse_loan_amt)
            st.caption(f"• 대출: {jeonse_loan_amt/10000:.1f}억 (내 보증금 {my_jeonse_deposit/10000:.2f}억)")
            st.caption(f"• {holding_years}년 불어난 총 투자자산: :green[**약 {cur_jeonse_fv:.0f}만원**]")
            st.caption(f"• {holding_years}년 누적 총 주거비: :red[**약 {cur_jeonse_cost:.0f}만원**]")
            st.info(f"💡 내 보증금({my_jeonse_deposit/10000:.2f}억) + 불어난 투자자산({cur_jeonse_fv/10000:.2f}억) = **{cur_jeonse/10000:.2f}억원**")
        else:
            st.metric(label="🔑 전세", value="❌ 전세 불가", delta=f"보증금 부족: 약 {jeonse_shortfall/10000:.2f}억원", delta_color="inverse")

    # [월세 카드]
    with mcol3:
        st.metric(label="📄 월세 최종 자산", value=f"{cur_monthly/10000:.2f} 억원", delta="대출 불필요 (순수 투자)")
        st.caption(f"• {tax_credit_desc}")
        st.caption(f"• {holding_years}년 불어난 총 투자자산: :green[**약 {cur_monthly_fv:.0f}만원**]")
        st.caption(f"• {holding_years}년 누적 실질 주거비: :red[**약 {cur_monthly_cost:.0f}만원**]")
        st.info(f"💡 돌려받는 보증금({monthly_deposit/10000:.2f}억) + 불어난 투자자산({cur_monthly_fv/10000:.2f}억) = **{cur_monthly/10000:.2f}억원**")

    # -------------------------------------------------------------
    # 9. BEP 인터랙티브 차트 (모바일 여백 최적화)
    # -------------------------------------------------------------
    st.markdown("---")
    st.subheader("📈 거주 기간별 손익분기점(BEP) 차트")

    with st.expander("❓ **이 차트가 무엇을 의미하나요? (클릭)**"):
        st.markdown(f"""
        - **1~10년 후 이사갈 때 내 손에 남는 총 순자산**을 비교합니다.
        - 매달 **{monthly_invest_budget}만원** 중 주거비를 내고 남는 돈이 세후 복리(연 {after_tax_rate*100:.2f}%)로 투자됩니다.
        - **교차점(BEP)**: 매매 선이 전·월세 선을 뚫고 올라가는 순간부터 매매가 유리해집니다.
        """)

    fig = go.Figure()
    if is_buy_possible:
        fig.add_trace(go.Scatter(x=years, y=buy_trajectory, mode='lines+markers', name='매매', line=dict(color='#4f46e5', width=3)))
    else:
        fig.add_trace(go.Scatter(
            x=years, 
            y=[buy_price * ((1 + price_growth_rate) ** t) - (buy_total_required - user_cash) for t in years],
            mode='lines', 
            name='매매(자금부족-이론선)', 
            line=dict(color='#94a3b8', width=1.5, dash='dot')
        ))

    if is_jeonse_possible:
        fig.add_trace(go.Scatter(x=years, y=jeonse_trajectory, mode='lines+markers', name='전세', line=dict(color='#10b981', width=2.5, dash='dash')))
    fig.add_trace(go.Scatter(x=years, y=monthly_trajectory, mode='lines+markers', name='월세', line=dict(color='#f59e0b', width=2.5)))

    fig.add_vline(x=holding_years, line_width=1.5, line_dash="dot", line_color="gray", annotation_text=f"{holding_years}년")

    # 모바일 화면에 꼭 맞춘 마진과 범례 레이아웃
    fig.update_layout(
        xaxis_title="거주 기간 (년)",
        yaxis_title="순자산 (만원)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=30, b=10),
        height=380
    )
    st.plotly_chart(fig, use_container_width=True)

    if is_buy_possible:
        if bep_year:
            st.info(f"💡 **BEP 분석**: 매매는 **약 {bep_year}년차**에 전·월세를 역전합니다. {bep_year}년 이상 거주 시 **매매**가 가장 유리합니다.")
        else:
            st.warning("💡 **BEP 분석**: 현재 조건에서는 **10년 이내에 전·월세의 자산 성장**이 더 우세합니다.")
    else:
        st.error(f"💡 **BEP 분석**: 현재 매매는 자금 부족입니다. **실행 가능한 전세 vs 월세 중에서는 '{best_strategy}'가 가장 많은 자산({best_val/10000:.2f}억원)을 형성**합니다.")


# -----------------------------------------------------------------------------
# [탭 2] 부산 자치구별 시세 트렌드 (연도별)
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("📊 부산 아파트 연도별 시세 트렌드 (2019 ~ 2026)")
    st.caption("공공 실거래가 통계 & 통계청 소비자물가지수(CPI) 기반 권역별 비교")

    cpi_inflation = {
        2019: 0.4, 2020: 0.5, 2021: 2.5, 2022: 5.1,
        2023: 3.6, 2024: 2.3, 2025: 2.1, 2026: 2.0
    }
    avg_inflation = np.mean(list(cpi_inflation.values()))

    trend_data = {
        "연도": [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "부산 전체 (매매)": [3.40, 4.20, 5.20, 4.70, 4.10, 4.35, 4.50, 4.62],
        "부산 전체 (전세)": [2.20, 2.60, 3.10, 2.80, 2.50, 2.65, 2.75, 2.85],
        "해운대구 (매매)": [4.80, 6.50, 8.30, 7.50, 6.70, 7.20, 7.50, 7.80],
        "해운대구 (전세)": [2.90, 3.60, 4.40, 3.90, 3.50, 3.70, 3.90, 4.05],
        "수영구 (매매)": [4.50, 6.20, 8.10, 7.20, 6.50, 7.00, 7.30, 7.60],
        "수영구 (전세)": [2.70, 3.40, 4.20, 3.70, 3.30, 3.55, 3.75, 3.90],
        "연제구 (매매)": [3.60, 4.60, 5.80, 5.10, 4.40, 4.70, 4.90, 5.05],
        "연제구 (전세)": [2.30, 2.80, 3.40, 3.00, 2.60, 2.80, 2.95, 3.05],
        "동래구 (매매)": [3.90, 4.90, 6.10, 5.40, 4.60, 4.95, 5.20, 5.35],
        "동래구 (전세)": [2.50, 3.00, 3.60, 3.20, 2.80, 3.00, 3.15, 3.25],
        "부산진구 (매매)": [3.30, 4.10, 5.10, 4.50, 3.90, 4.15, 4.30, 4.40],
        "부산진구 (전세)": [2.10, 2.50, 3.00, 2.70, 2.40, 2.55, 2.65, 2.70],
        "남구 (매매)": [3.70, 4.80, 6.20, 5.40, 4.60, 4.90, 5.10, 5.25],
        "남구 (전세)": [2.40, 2.90, 3.50, 3.10, 2.70, 2.90, 3.05, 3.15],
    }
    df_trend = pd.DataFrame(trend_data)

    st.info(f"📈 **통계청 연평균 소비자물가상승률**: **연 약 {avg_inflation:.1f}%**")

    selected_region = st.selectbox(
        "트렌드 조회 지역",
        ["부산 전체", "연제구", "해운대구", "수영구", "동래구", "부산진구", "남구"]
    )

    buy_col = f"{selected_region} (매매)"
    jeonse_col = f"{selected_region} (전세)"

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=df_trend["연도"], y=df_trend[buy_col],
        mode='lines+markers', name='매매(억)',
        line=dict(color='#4f46e5', width=2.5),
        hovertemplate='%{x}년 매매: <b>%{y:.2f}억</b><extra></extra>'
    ))
    fig_trend.add_trace(go.Scatter(
        x=df_trend["연도"], y=df_trend[jeonse_col],
        mode='lines+markers', name='전세(억)',
        line=dict(color='#10b981', width=2.5, dash='dash'),
        hovertemplate='%{x}년 전세: <b>%{y:.2f}억</b><extra></extra>'
    ))

    fig_trend.update_layout(
        title=f"<b>{selected_region}</b> 매매 vs 전세 시세",
        xaxis_title="연도",
        yaxis_title="시세 (억원)",
        yaxis=dict(ticksuffix="억"),
        hovermode="x unified",
        margin=dict(l=10, r=10, t=35, b=10),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    with st.expander("📋 연도별 상세 수치 데이터표 보기"):
        buy_series = df_trend[buy_col]
        jeonse_series = df_trend[jeonse_col]
        buy_pct_change = buy_series.pct_change() * 100
        jeonse_pct_change = jeonse_series.pct_change() * 100

        display_rows = []
        for i in range(len(df_trend)):
            year = df_trend["연도"][i]
            b_val, j_val = buy_series[i], jeonse_series[i]
            cpi_val = cpi_inflation.get(year, "-")
            
            if i == 0:
                b_change_str, j_change_str = "-", "-"
            else:
                b_chg, j_chg = buy_pct_change[i], jeonse_pct_change[i]
                b_change_str = f"+{b_chg:.1f}%" if b_chg > 0 else (f"{b_chg:.1f}%" if b_chg < 0 else "0.0%")
                j_change_str = f"+{j_chg:.1f}%" if j_chg > 0 else (f"{j_chg:.1f}%" if j_chg < 0 else "0.0%")
                
            display_rows.append({
                "연도": f"{year}",
                "매매": f"{b_val:.2f}억",
                "매매증감": b_change_str,
                "전세": f"{j_val:.2f}억",
                "전세증감": j_change_str,
                "CPI": f"{cpi_val:.1f}%",
                "전세가율": f"{(j_val / b_val * 100):.0f}%"
            })

        df_display = pd.DataFrame(display_rows)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
