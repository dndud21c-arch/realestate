import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="부산 부동산 실질 주거비 & 자산성장 시뮬레이터",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 부산 부동산 실질 주거비 & 자산 성장 시뮬레이터")
st.caption("기회비용 · 숨은 부대비용 · 정책대출 룰셋 · 월 적립식 복리투자 엔진 · 연도별 시세 트렌드")

# -----------------------------------------------------------------------------
# 사이드바: 입력 제어 패널
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("1. 매물 정보 설정")
    district = st.selectbox(
        "부산 자치구 선택",
        ["해운대구", "수영구", "연제구", "부산진구", "남구", "동래구", "기장군", "사하구", "북구", "금정구", "강서구"]
    )
    
    col1, col2 = st.columns(2)
    with col1:
        buy_price = st.number_input("매매 시세 (만원)", value=50000, step=1000)
        monthly_deposit = st.number_input("월세 보증금 (만원)", value=5000, step=500)
    with col2:
        jeonse_price = st.number_input("전세 보증금 (만원)", value=30000, step=1000)
        monthly_rent = st.number_input("월세액 (만원/월)", value=90, step=5)

    st.markdown("---")
    st.header("2. 내 자산 및 조건")
    user_cash = st.number_input("보유 순자산 (만원)", value=15000, step=1000)
    user_income = st.number_input("연봉 / 총급여 (만원)", value=6500, step=500, help="월세 세액공제(8,000만원 이하) 판정에 사용됩니다.")
    
    is_married = st.checkbox("신혼부부 (혼인 7년 이내)", value=True)
    has_newborn = st.checkbox("신생아 출산/입양 (2년 이내)", value=False)
    is_first_buyer = st.checkbox("생애최초 주택구입", value=True)

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
    st.info(f"💡 세후 실질 복리 수익률: **연 {after_tax_rate*100:.2f}%** (월 {monthly_r*100:.3f}%) 적용")

    st.markdown("---")
    st.header("4. 시뮬레이션 변수")
    holding_years = st.slider("예상 거주 기간 (년)", min_value=1, max_value=10, value=4, step=1)
    price_growth_rate = st.slider("연평균 집값 상승률 가정 (%)", min_value=-3.0, max_value=6.0, value=2.0, step=0.5) / 100

# -----------------------------------------------------------------------------
# 탭 구성: [탭 1: 의사결정 시뮬레이터] / [탭 2: 부산 시세 트렌드]
# -----------------------------------------------------------------------------
tab1, tab2 = st.tabs(["📊 매매 vs 전세 vs 월세 비교 & BEP", "📈 부산 자치구별 시세 트렌드 (연도별)"])

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
        tax_credit_desc = f"연봉 5,500만원 이하 (17% 공제율 적용) ➔ **연 {annual_tax_refund:.0f}만원 세금 환급**"
    elif user_income <= 8000:
        rent_tax_credit_rate = 0.15
        annual_tax_refund = tax_credit_base * rent_tax_credit_rate
        tax_credit_desc = f"연봉 5,500만~8,000만원 이하 (15% 공제율 적용) ➔ **연 {annual_tax_refund:.0f}만원 세금 환급**"
    else:
        rent_tax_credit_rate = 0.0
        annual_tax_refund = 0.0
        tax_credit_desc = "연봉 8,000만원 초과 (세액공제 대상 제외, 현금영수증 소득공제 가능)"

    # 3. 정책 대출 룰베이스 엔진
    def evaluate_loans():
        buy_loan = {
            "name": "시중 주담대", 
            "rate": 3.8, 
            "limit": buy_price * 0.7,
            "reason": "소득 또는 순자산 기준이 기금 정책대출 요건을 초과하여 1금융권 시중 주담대(평균 3.8%)가 적용되었습니다."
        }
        jeonse_loan = {
            "name": "시중 전세대출", 
            "rate": 3.6, 
            "limit": jeonse_price * 0.8,
            "reason": "소득 또는 순자산 기준이 기금 정책대출 요건을 초과하여 1금융권 전세대출(평균 3.6%)이 적용되었습니다."
        }

        if user_cash <= 51100 and buy_price <= 90000:
            if has_newborn and user_income <= 13000:
                buy_loan = {
                    "name": "신생아 특례 디딤돌",
                    "rate": 1.8 - 0.2,
                    "limit": 40000,
                    "reason": "✅ [추천 근거] 2년 내 출산(입양) 무주택 가구 요건 충족!\n• 시중 주담대(3.8%) 대비 연 2.2%p 저렴하여 연간 막대한 이자 절감\n• 부산 소재 주택 지방우대금리(-0.2%p)가 자동 차감되어 최저 1.6%대 적용"
                }
            elif is_married and user_income <= 8500 and buy_price <= 60000:
                buy_loan = {
                    "name": "신혼부부 디딤돌",
                    "rate": 2.65 - 0.2,
                    "limit": 32000,
                    "reason": "✅ [추천 근거] 혼인 7년 이내 신혼부부 및 소득 요건(8.5천 이하) 충족!\n• 시중 주담대(3.8%) 대비 연 1.35%p 저렴하여 매월 이자 부담 대폭 절감\n• 부산 소재 주택 지방우대금리(-0.2%p) 적용으로 2.45% 최적화"
                }
            elif user_income <= 6000 and buy_price <= 50000:
                buy_loan = {
                    "name": "내집마련 디딤돌",
                    "rate": 2.85 - 0.2,
                    "limit": 20000,
                    "reason": "✅ [추천 근거] 서민 무주택 세대주 및 소득 요건(6천 이하) 충족!\n• 정부 주택도시기금 지원 저금리로 시중은행 대비 연 1.15%p 이자 절약\n• 부산 소재 주택 지방우대금리(-0.2%p) 적용된 2.65% 우대금리"
                }

        if user_cash <= 34500:
            if has_newborn and user_income <= 13000 and jeonse_price <= 40000:
                jeonse_loan = {
                    "name": "신생아 특례 버팀목",
                    "rate": 1.3 - 0.2,
                    "limit": 24000,
                    "reason": "✅ [추천 근거] 2년 내 출산 무주택 가구 특례 적용!\n• 시중 전세대출(3.6%) 대비 무려 2.5%p 저렴한 연 1.1%대 파격 금리\n• 부산(수도권 외) 보증금 4억원 한도 및 지방우대(-0.2%p) 반영"
                }
            elif is_married and user_income <= 7500 and jeonse_price <= 30000:
                jeonse_loan = {
                    "name": "신혼부부 버팀목",
                    "rate": 2.1 - 0.2,
                    "limit": 16000,
                    "reason": "✅ [추천 근거] 혼인 7년 이내 신혼부부 전세자금 지원 요건 충족!\n• 시중 전세대출 대비 연 1.7%p 낮은 1.9%대 초저금리 제공\n• 부산(수도권 외) 보증금 3억 이하 및 지방우대(-0.2%p) 반영"
                }
            elif user_income <= 5000 and jeonse_price <= 20000:
                jeonse_loan = {
                    "name": "일반 버팀목전세",
                    "rate": 2.5 - 0.2,
                    "limit": 8000,
                    "reason": "✅ [추천 근거] 서민 근로자 전세자금 대출 요건 충족!\n• 시중 전세대출 대비 연 1.3%p 저렴하여 월 주거비 최소화\n• 부산 소재 주택 지방우대금리(-0.2%p) 자동 차감 반영"
                }

        return buy_loan, jeonse_loan

    buy_loan, jeonse_loan = evaluate_loans()

    # 4. 부대비용 및 월 주거비/월 잉여투자액 산출
    acq_tax_rate = 0.011 if buy_price <= 60000 else (0.022 if buy_price <= 90000 else 0.033)
    buy_initial_costs = (buy_price * acq_tax_rate) + (buy_price * 0.004) + 80
    buy_annual_holding = (buy_price * 0.69 * 0.002) + 36

    buy_loan_amt = min(buy_loan["limit"], max(0, buy_price - user_cash))
    buy_annual_interest = buy_loan_amt * (buy_loan["rate"] / 100)
    buy_monthly_cost = (buy_annual_interest + buy_annual_holding) / 12
    buy_equity_used = buy_price - buy_loan_amt + buy_initial_costs
    buy_free_cash = max(0, user_cash - buy_equity_used)

    jeonse_loan_amt = min(jeonse_loan["limit"], max(0, jeonse_price - user_cash))
    jeonse_annual_interest = jeonse_loan_amt * (jeonse_loan["rate"] / 100)
    jeonse_annual_guarantee = jeonse_price * 0.0012
    jeonse_monthly_cost = (jeonse_annual_interest + jeonse_annual_guarantee) / 12
    jeonse_equity_used = jeonse_price - jeonse_loan_amt
    jeonse_free_cash = max(0, user_cash - jeonse_equity_used)

    # 월세의 월 주거비 지출 (순수 월세액)
    monthly_monthly_cost = monthly_rent
    monthly_free_cash = max(0, user_cash - monthly_deposit)

    # 매달 실제 투자에 투입되는 잉여 저축액
    buy_monthly_invest = max(0.0, monthly_invest_budget - buy_monthly_cost)
    jeonse_monthly_invest = max(0.0, monthly_invest_budget - jeonse_monthly_cost)
    monthly_monthly_invest = max(0.0, monthly_invest_budget - monthly_monthly_cost)

    # -------------------------------------------------------------
    # 5. [요구사항 2] 거치식 + 적립식 + 월세 환급금 재투자 복리 엔진
    # -------------------------------------------------------------
    def calculate_investment_details(initial_lump_sum, monthly_contribution, years_count, annual_extra_cash=0.0):
        """
        초기 목돈 복리 + 매월 적립금 복리 + 매년 유입되는 환급금 복리 재투자
        반환값: (최종 평가액, 총 투입 원금, 순수 투자 수익)
        """
        # 1) 초기 목돈 거치식 복리
        lump_fv = initial_lump_sum * ((1 + after_tax_rate) ** years_count)
        
        # 2) 매월 적립식 복리 (월복리 연금 미래가치 수식)
        months_total = years_count * 12
        if monthly_r > 0:
            monthly_fv = monthly_contribution * (((1 + monthly_r) ** months_total - 1) / monthly_r)
        else:
            monthly_fv = monthly_contribution * months_total

        # 3) [월세 특화] 매년 말 환급되는 세액공제 환급금의 복리 재투자
        extra_fv = 0.0
        if annual_extra_cash > 0:
            for y in range(1, years_count + 1):
                # 각 연도말에 들어온 환급금이 남은 기간 동안 복리로 불어남
                rem_years = years_count - y
                extra_fv += annual_extra_cash * ((1 + after_tax_rate) ** rem_years)

        total_fv = lump_fv + monthly_fv + extra_fv
        # 총 투입 원금 (초기 목돈 + 매월 부은 돈 + 환급받아 넣은 돈)
        total_principal = initial_lump_sum + (monthly_contribution * months_total) + (annual_extra_cash * years_count)
        # 순수 투자 수익 (이자 및 자본 이득)
        pure_gain = total_fv - total_principal

        return total_fv, total_principal, pure_gain

    # 1~10년 타임라인 순자산 계산
    years = list(range(1, 11))
    buy_trajectory = []
    jeonse_trajectory = []
    monthly_trajectory = []
    
    # 거주기간별 순수 투자 수익 저장
    buy_gains = []
    jeonse_gains = []
    monthly_gains = []

    bep_year = None

    for t in years:
        # 매매
        future_val = buy_price * ((1 + price_growth_rate) ** t)
        buy_fv, buy_princ, buy_gain = calculate_investment_details(buy_free_cash, buy_monthly_invest, t, 0.0)
        buy_nw = future_val - buy_loan_amt + buy_fv
        buy_trajectory.append(buy_nw)
        buy_gains.append(buy_gain)

        # 전세
        jeonse_fv, jeonse_princ, jeonse_gain = calculate_investment_details(jeonse_free_cash, jeonse_monthly_invest, t, 0.0)
        jeonse_nw = jeonse_price - jeonse_loan_amt + jeonse_fv
        jeonse_trajectory.append(jeonse_nw)
        jeonse_gains.append(jeonse_gain)

        # 월세 (매년 환급금 annual_tax_refund 재투자 적용!)
        monthly_fv, monthly_princ, monthly_gain = calculate_investment_details(monthly_free_cash, monthly_monthly_invest, t, annual_tax_refund)
        monthly_nw = monthly_deposit + monthly_fv
        monthly_trajectory.append(monthly_nw)
        monthly_gains.append(monthly_gain)

        if bep_year is None and buy_nw > max(jeonse_nw, monthly_nw):
            bep_year = t

    # 6. 화면 표시
    if badge_color == "success":
        st.success(f"📍 **{district} 시세 분석 결과**: {risk_badge}")
    elif badge_color == "warning":
        st.warning(f"📍 **{district} 시세 분석 결과**: {risk_badge}")
    else:
        st.error(f"📍 **{district} 시세 분석 결과**: {risk_badge}")

    cur_idx = holding_years - 1
    cur_buy = buy_trajectory[cur_idx]
    cur_jeonse = jeonse_trajectory[cur_idx]
    cur_monthly = monthly_trajectory[cur_idx]
    best_val = max(cur_buy, cur_jeonse, cur_monthly)

    cur_buy_gain = buy_gains[cur_idx]
    cur_jeonse_gain = jeonse_gains[cur_idx]
    cur_monthly_gain = monthly_gains[cur_idx]

    if best_val == cur_buy:
        best_strategy = "매매 (자가 구입)"
        strategy_msg = f"부동산 자산 상승분(연 {price_growth_rate*100:.1f}%)과 레버리지 효과가 매월 나가는 이자비용을 압도하여 가장 많은 자산을 축적합니다."
    elif best_val == cur_jeonse:
        best_strategy = "전세"
        strategy_msg = f"저금리 기금 전세대출로 주거비를 아끼고, 남은 월급을 꾸준히 복리 투자({holding_years}년 누적수익 +{cur_jeonse_gain:.0f}만원)한 결과가 가장 유리합니다."
    else:
        best_strategy = "월세"
        strategy_msg = f"보증금으로 묶이지 않은 목돈과 매년 환급되는 월세 세액공제금의 복리 재투자({holding_years}년 누적수익 +{cur_monthly_gain:.0f}만원)가 월세 지출을 압도합니다."

    st.subheader(f"🎯 {holding_years}년 거주 시 최적 선택: **'{best_strategy}'**")
    st.markdown(f"> {strategy_msg} (예상 최종 순자산: **{best_val/10000:.2f}억원**)")

    # 월간 현금흐름 배분 안내 박스
    st.markdown(f"""
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; margin: 15px 0;">
        <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #1e293b;">
            💡 <strong>[적립식 복리 엔진 안내]</strong> 매월 저축 가능 예산 <strong>{monthly_invest_budget}만원</strong>은 이렇게 배분되어 굴러갑니다:
        </h4>
        <div style="display: flex; gap: 15px; font-size: 12px; color: #475569; flex-wrap: wrap;">
            <div>🏠 <strong>매매</strong>: 주거비(이자+세금) <strong>{buy_monthly_cost:.0f}만</strong> 지출 ➔ <strong>남는 {buy_monthly_invest:.0f}만원/월</strong> 매달 복리투자</div>
            <div>🔑 <strong>전세</strong>: 주거비(전세대출이자) <strong>{jeonse_monthly_cost:.0f}만</strong> 지출 ➔ <strong>남는 {jeonse_monthly_invest:.0f}만원/월</strong> 매달 복리투자</div>
            <div>📄 <strong>월세</strong>: 월세 <strong>{monthly_monthly_cost:.0f}만</strong> 지출 ➔ <strong>남는 {monthly_monthly_invest:.0f}만원/월 + 연말정산 환급금</strong> 매달/매년 복리투자</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # [요구사항 1] 3개 비교 카드 (예상 거주기간 누적 투자수익 표기)
    # -------------------------------------------------------------
    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.metric(
            label="🏠 매매 최종 자산", 
            value=f"{cur_buy/10000:.2f} 억원", 
            delta=f"대출: {buy_loan['name']} ({buy_loan['rate']:.2f}%)",
            help=f"💡 [마우스 호버/클릭 시 상세 사유]\n\n{buy_loan['reason']}"
        )
        with st.popover("🔍 대출 추천 근거 및 비교 보기"):
            st.markdown(f"**[{buy_loan['name']} 추천 사유]**")
            st.info(buy_loan['reason'])
            st.caption(f"• 시중 주담대 금리: 평균 3.80%\n• 추천 대출 금리: 연 {buy_loan['rate']:.2f}%\n• 연간 이자 차액 절감: 약 {buy_loan_amt * (0.038 - buy_loan['rate']/100):.0f}만원/년")

        st.caption(f"• 대출액: {buy_loan_amt/10000:.1f}억 (월이자 약 {buy_annual_interest/12:.0f}만원)")
        st.caption(f"• 매월 주거비 지출: 월 약 {buy_monthly_cost:.0f}만원 (이자+세금)")
        # 누적 투자수익 표기
        st.caption(f"• **{holding_years}년 누적 투자수익**: :green[**+ {cur_buy_gain:.0f}만원**] (순수 금융수익)")

    with mcol2:
        st.metric(
            label="🔑 전세 최종 자산", 
            value=f"{cur_jeonse/10000:.2f} 억원", 
            delta=f"대출: {jeonse_loan['name']} ({jeonse_loan['rate']:.2f}%)",
            help=f"💡 [마우스 호버/클릭 시 상세 사유]\n\n{jeonse_loan['reason']}"
        )
        with st.popover("🔍 대출 추천 근거 및 비교 보기"):
            st.markdown(f"**[{jeonse_loan['name']} 추천 사유]**")
            st.info(jeonse_loan['reason'])
            st.caption(f"• 시중 전세대출 금리: 평균 3.60%\n• 추천 대출 금리: 연 {jeonse_loan['rate']:.2f}%\n• 연간 이자 차액 절감: 약 {jeonse_loan_amt * (0.036 - jeonse_loan['rate']/100):.0f}만원/년")

        st.caption(f"• 대출액: {jeonse_loan_amt/10000:.1f}억 (월이자 약 {jeonse_annual_interest/12:.0f}만원)")
        st.caption(f"• 초기 여유 목돈: {jeonse_free_cash/10000:.1f}억원")
        # 누적 투자수익 표기
        st.caption(f"• **{holding_years}년 누적 투자수익**: :green[**+ {cur_jeonse_gain:.0f}만원**] (순수 금융수익)")

    with mcol3:
        st.metric(
            label="📄 월세 최종 자산", 
            value=f"{cur_monthly/10000:.2f} 억원", 
            delta="대출 불필요 (순수 투자 집중)",
            help="보증금이 적어 대출이 필요 없으며, 남는 목돈 전액과 매달 아낀 대출이자 차액을 금융상품에 집중 투자합니다."
        )
        st.caption(f"• {tax_credit_desc}")
        st.caption(f"• 초기 여유 목돈: {monthly_free_cash/10000:.1f}억원 (보증금 제외 전액투자)")
        # 월세 세액공제 환급금 재투자가 반영된 누적 투자수익 표기
        st.caption(f"• **{holding_years}년 누적 투자수익**: :green[**+ {cur_monthly_gain:.0f}만원**] (환급금 재투자 반영)")

    # 7. BEP 인터랙티브 차트
    st.markdown("---")
    st.subheader("📈 거주 기간별 손익분기점(BEP) 인터랙티브 차트")

    with st.expander("❓ **이 차트가 무엇을 의미하나요? (1분 이해 가이드 클릭)**", expanded=True):
        st.markdown(f"""
        이 그래프는 **'지금 선택한 집에서 1년~10년 동안 살다가 이사 나갈 때, 내 손에 최종적으로 남는 통장 잔고(순자산)'**를 비교한 것입니다.
        현재 매월 **{monthly_invest_budget}만원**의 저축 예산 중 주거비를 내고 남는 돈과 월세 환급금이 매달 금융상품(세후 연 {after_tax_rate*100:.2f}%)에 자동으로 적립식 투자됩니다.
        
        1. **🟦 파란색 선 (매매)**: 
           - 처음 1~2년에는 **취득세, 중개수수료 등 목돈 비용**과 높은 대출이자 지출로 매월 투자할 수 있는 돈이 적어 낮게 시작합니다.
           - 하지만 매달 집값이 연 {price_growth_rate*100:.1f}%씩 복리로 상승하므로 거주 기간이 길어질수록 자산 성장 속도가 가장 가파릅니다.
        2. **🟩 초록색 점선 (전세)**:
           - 저금리 정책대출로 월 주거비를 아끼고 남는 목돈과 월급을 꾸준히 적립식 투자({holding_years}년 누적수익 +{cur_jeonse_gain:.0f}만원)한 결과입니다.
        3. **🟧 주황색 선 (월세)**:
           - 보증금이 가장 적게 들기 때문에 **가장 큰 목돈({monthly_free_cash/10000:.1f}억원)과 매년 환급받는 월세 세액공제금을 모두 복리로 굴려** 높은 금융 투자 수익({holding_years}년 누적수익 +{cur_monthly_gain:.0f}만원)을 달성합니다.
        4. **⭐ 교차점 (골든크로스 / BEP)**:
           - **파란색 선(매매)이 초록색/주황색 선을 뚫고 올라가는 순간**입니다! 즉, **"이 기간 이상 살 거면 무조건 집을 사는 게 돈을 번다"**는 손익분기점입니다.
        """)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=buy_trajectory, mode='lines+markers', name='매매(자가)', line=dict(color='#4f46e5', width=3)))
    fig.add_trace(go.Scatter(x=years, y=jeonse_trajectory, mode='lines+markers', name='전세', line=dict(color='#10b981', width=2.5, dash='dash')))
    fig.add_trace(go.Scatter(x=years, y=monthly_trajectory, mode='lines+markers', name='월세', line=dict(color='#f59e0b', width=2.5)))

    fig.add_vline(x=holding_years, line_width=1.5, line_dash="dot", line_color="gray", annotation_text=f"현재 선택: {holding_years}년")

    fig.update_layout(
        xaxis_title="거주 기간 (년)",
        yaxis_title="최종 순자산 가치 (만원)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20),
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)

    if bep_year:
        st.info(f"💡 **BEP 판정**: 현재 설정에서 매매는 **약 {bep_year}년차**에 전·월세를 역전합니다. {bep_year}년 이상 거주 계획이라면 **매매**가 가장 유리합니다.")
    else:
        st.warning("💡 **BEP 판정**: 현재 집값 변동률 가정에서는 **10년 이내에 전·월세의 자산 형성**이 더 유리합니다.")


# -----------------------------------------------------------------------------
# [탭 2] 부산 자치구별 시세 트렌드 (연도별) + 물가상승률(CPI) 비교
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("📊 부산 아파트 연도별 매매 & 전세 시세 트렌드 (2019 ~ 2026)")
    st.caption("공공 실거래가 통계 & 통계청 소비자물가지수(CPI) 기반 권역별 비교 분석")

    cpi_inflation = {
        2019: 0.4,
        2020: 0.5,
        2021: 2.5,
        2022: 5.1,
        2023: 3.6,
        2024: 2.3,
        2025: 2.1,
        2026: 2.0
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

    st.info(f"""
    📈 **대한민국 통계청 기준 연평균 소비자물가상승률**: **연 약 {avg_inflation:.1f}%** 
    (2019년 0.4% ➔ 2022년 고물가 5.1% ➔ 2025년 2.1% 안정세)  
    👉 **부동산 매매가 상승률이 물가상승률({avg_inflation:.1f}%)보다 높다면**, 화폐가치 하락을 방어하고 실질 자산을 불린 것입니다.
    """)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        selected_region = st.selectbox(
            "트렌드 조회 지역",
            ["부산 전체", "연제구", "해운대구", "수영구", "동래구", "부산진구", "남구"]
        )
        st.markdown(f"""
        **💡 {selected_region} 시세 인사이트**
        - **유동성 랠리(2020~2021)**: 저금리와 유동성으로 아파트 상승률이 물가상승률(0.5~2.5%)을 크게 초과했습니다.
        - **고물가·고금리(2022~2023)**: 물가는 5.1% 급등했으나, 금리 인상 충격으로 아파트 매매가는 일시적 조정을 겪었습니다.
        - **현재 국면(2024~2026)**: 물가가 2%대로 안정화되면서 아파트 가격도 연 2~3%대 완만한 회복세를 보이고 있습니다.
        """)
    
    with col_t2:
        buy_col = f"{selected_region} (매매)"
        jeonse_col = f"{selected_region} (전세)"

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=df_trend["연도"], 
            y=df_trend[buy_col],
            mode='lines+markers', 
            name='평균 매매가 (억원)',
            line=dict(color='#4f46e5', width=3),
            hovertemplate='%{x}년 매매: <b>%{y:.2f}억원</b><extra></extra>'
        ))
        fig_trend.add_trace(go.Scatter(
            x=df_trend["연도"], 
            y=df_trend[jeonse_col],
            mode='lines+markers', 
            name='평균 전세가 (억원)',
            line=dict(color='#10b981', width=3, dash='dash'),
            hovertemplate='%{x}년 전세: <b>%{y:.2f}억원</b><extra></extra>'
        ))

        fig_trend.update_layout(
            title=f"<b>{selected_region}</b> 아파트 매매 vs 전세 시세 추이",
            xaxis_title="연도",
            yaxis_title="평균 시세 (억원)",
            yaxis=dict(ticksuffix="억"),
            hovermode="x unified",
            height=430,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")
    st.subheader(f"📋 {selected_region} 연도별 시세 · 증감률 · 소비자물가상승률(CPI) 비교표")

    buy_series = df_trend[buy_col]
    jeonse_series = df_trend[jeonse_col]

    buy_pct_change = buy_series.pct_change() * 100
    jeonse_pct_change = jeonse_series.pct_change() * 100

    display_rows = []
    for i in range(len(df_trend)):
        year = df_trend["연도"][i]
        b_val = buy_series[i]
        j_val = jeonse_series[i]
        cpi_val = cpi_inflation.get(year, "-")
        
        if i == 0:
            b_change_str = "-"
            j_change_str = "-"
        else:
            b_chg = buy_pct_change[i]
            j_chg = jeonse_pct_change[i]
            b_change_str = f"+{b_chg:.1f}%" if b_chg > 0 else (f"{b_chg:.1f}%" if b_chg < 0 else "0.0%")
            j_change_str = f"+{j_chg:.1f}%" if j_chg > 0 else (f"{j_chg:.1f}%" if j_chg < 0 else "0.0%")
            
        display_rows.append({
            "연도": f"{year}년",
            "평균 매매가": f"{b_val:.2f} 억원",
            "매매 전년대비 증감률": b_change_str,
            "평균 전세가": f"{j_val:.2f} 억원",
            "전세 전년대비 증감률": j_change_str,
            "소비자물가상승률 (CPI)": f"{cpi_val:.1f}%",
            "전세가율": f"{(j_val / b_val * 100):.1f}%"
        })

    df_display = pd.DataFrame(display_rows)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
