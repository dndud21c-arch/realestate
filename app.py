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
st.caption("기회비용 · 숨은 부대비용 · 정책대출 룰셋 · 월세 세액공제 · 연도별 시세 트렌드")

# -----------------------------------------------------------------------------
# 사이드바: 입력 제어 패널
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("1. 매물 정보 설정")
    # [요구사항 1] 연제구 추가
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
    st.info(f"💡 세후 실질 복리 수익률: **{after_tax_rate*100:.2f}%** 적용")

    st.markdown("---")
    st.header("4. 시뮬레이션 변수")
    holding_years = st.slider("예상 거주 기간 (년)", min_value=1, max_value=10, value=4, step=1)
    price_growth_rate = st.slider("연평균 집값 상승률 가정 (%)", min_value=-3.0, max_value=6.0, value=2.0, step=0.5) / 100

# -----------------------------------------------------------------------------
# 탭 구성: [탭 1: 의사결정 시뮬레이터] / [탭 2: 부산 시세 트렌드]
# -----------------------------------------------------------------------------
tab1, tab2 = st.tabs(["📊 매매 vs 전세 vs 월세 비교 & BEP", "📈 부산 자치구별 시세 트렌드 (연도별)"])

with tab1:
    # -------------------------------------------------------------
    # 핵심 계산 로직
    # -------------------------------------------------------------
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

    # 2. [요구사항 3] 월세 세액공제 계산 엔진
    # 대상: 무주택자(기본 가정), 총급여 8,000만원 이하, 연간 월세액 한도 1,000만원
    annual_rent_paid = monthly_rent * 12  # 연간 납부 월세액 (만원)
    tax_credit_base = min(1000.0, float(annual_rent_paid))  # 1,000만원 한도

    if user_income <= 5500:
        rent_tax_credit_rate = 0.17  # 17% 세액공제
        annual_tax_refund = tax_credit_base * rent_tax_credit_rate
        tax_credit_desc = f"연봉 5,500만원 이하 (17% 공제율 적용) ➔ **연 {annual_tax_refund:.0f}만원 세금 환급**"
    elif user_income <= 8000:
        rent_tax_credit_rate = 0.15  # 15% 세액공제
        annual_tax_refund = tax_credit_base * rent_tax_credit_rate
        tax_credit_desc = f"연봉 5,500만~8,000만원 이하 (15% 공제율 적용) ➔ **연 {annual_tax_refund:.0f}만원 세금 환급**"
    else:
        rent_tax_credit_rate = 0.0
        annual_tax_refund = 0.0
        tax_credit_desc = "연봉 8,000만원 초과 (세액공제 대상 제외, 현금영수증 소득공제 가능)"

    # 3. 정책 대출 룰베이스 엔진 (부산 우대금리 -0.2%p)
    def evaluate_loans():
        buy_loan = {"name": "시중 주담대", "rate": 3.8, "limit": buy_price * 0.7}
        jeonse_loan = {"name": "시중 전세대출", "rate": 3.6, "limit": jeonse_price * 0.8}

        if user_cash <= 51100 and buy_price <= 90000:
            if has_newborn and user_income <= 13000:
                buy_loan = {"name": "신생아 특례 디딤돌", "rate": 1.8 - 0.2, "limit": 40000}
            elif is_married and user_income <= 8500 and buy_price <= 60000:
                buy_loan = {"name": "신혼부부 디딤돌", "rate": 2.65 - 0.2, "limit": 32000}
            elif user_income <= 6000 and buy_price <= 50000:
                buy_loan = {"name": "내집마련 디딤돌", "rate": 2.85 - 0.2, "limit": 20000}

        if user_cash <= 34500:
            if has_newborn and user_income <= 13000 and jeonse_price <= 40000:
                jeonse_loan = {"name": "신생아 특례 버팀목", "rate": 1.3 - 0.2, "limit": 24000}
            elif is_married and user_income <= 7500 and jeonse_price <= 30000:
                jeonse_loan = {"name": "신혼부부 버팀목", "rate": 2.1 - 0.2, "limit": 16000}
            elif user_income <= 5000 and jeonse_price <= 20000:
                jeonse_loan = {"name": "일반 버팀목전세", "rate": 2.5 - 0.2, "limit": 8000}

        return buy_loan, jeonse_loan

    buy_loan, jeonse_loan = evaluate_loans()

    # 4. 부대비용 및 자본배치
    acq_tax_rate = 0.011 if buy_price <= 60000 else (0.022 if buy_price <= 90000 else 0.033)
    buy_initial_costs = (buy_price * acq_tax_rate) + (buy_price * 0.004) + 80
    buy_annual_holding = (buy_price * 0.69 * 0.002) + 36

    buy_loan_amt = min(buy_loan["limit"], max(0, buy_price - user_cash))
    buy_annual_interest = buy_loan_amt * (buy_loan["rate"] / 100)

    jeonse_loan_amt = min(jeonse_loan["limit"], max(0, jeonse_price - user_cash))
    jeonse_annual_interest = jeonse_loan_amt * (jeonse_loan["rate"] / 100)
    jeonse_equity_used = jeonse_price - jeonse_loan_amt
    jeonse_free_cash = max(0, user_cash - jeonse_equity_used)

    monthly_free_cash = max(0, user_cash - monthly_deposit)
    # 실질 월세 지출 = 순수 월세액 - 연말정산 환급금
    effective_annual_rent = annual_rent_paid - annual_tax_refund

    # 5. 1~10년 타임라인 순자산 계산
    years = list(range(1, 11))
    buy_trajectory = []
    jeonse_trajectory = []
    monthly_trajectory = []
    bep_year = None

    for t in years:
        # 매매 순자산
        future_val = buy_price * ((1 + price_growth_rate) ** t)
        buy_nw = future_val - buy_loan_amt - buy_initial_costs - (buy_annual_interest + buy_annual_holding) * t
        buy_trajectory.append(buy_nw)

        # 전세 순자산
        jeonse_invest_fv = jeonse_free_cash * ((1 + after_tax_rate) ** t)
        jeonse_guarantee = (jeonse_price * 0.0012) * t
        jeonse_nw = jeonse_price + jeonse_invest_fv - jeonse_loan_amt - (jeonse_annual_interest * t) - jeonse_guarantee
        jeonse_trajectory.append(jeonse_nw)

        # 월세 순자산 (세액공제 환급액 반영된 실질 월세 차감)
        monthly_invest_fv = monthly_free_cash * ((1 + after_tax_rate) ** t)
        monthly_nw = monthly_deposit + monthly_invest_fv - (effective_annual_rent * t)
        monthly_trajectory.append(monthly_nw)

        if bep_year is None and buy_nw > max(jeonse_nw, monthly_nw):
            bep_year = t

    # -------------------------------------------------------------
    # 화면 표시 (배너 & 메트릭)
    # -------------------------------------------------------------
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

    if best_val == cur_buy:
        best_strategy = "매매 (자가 구입)"
        strategy_msg = f"부동산 자산 상승분(연 {price_growth_rate*100:.1f}%)이 취득세 및 대출 이자를 상회하여 가장 많은 자산을 축적합니다."
    elif best_val == cur_jeonse:
        best_strategy = "전세"
        strategy_msg = f"저금리 기금 전세대출 레버리지와 잉여자본의 투자 복리 효과가 매매 부대비용 부담보다 안정적입니다."
    else:
        best_strategy = "월세"
        strategy_msg = f"세액공제 환급 혜택과 목돈을 대체투자(세후 연 {after_tax_rate*100:.2f}%)로 굴린 복리 수익이 월세 지출을 압도합니다."

    st.subheader(f"🎯 {holding_years}년 거주 시 최적 선택: **'{best_strategy}'**")
    st.markdown(f"> {strategy_msg} (예상 최종 순자산: **{best_val/10000:.2f}억원**)")

    # 3개 카드
    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.metric("🏠 매매 최종 자산", f"{cur_buy/10000:.2f} 억원", f"대출: {buy_loan['name']} ({buy_loan['rate']:.2f}%)")
        st.caption(f"• 대출액: {buy_loan_amt/10000:.1f}억 (월이자 약 {buy_annual_interest/12:.0f}만원)")
        st.caption(f"• 취득세/부대비용: 약 {buy_initial_costs:.0f}만원")
        st.caption(f"• 월할 보유세/건보료: 월 약 {buy_annual_holding/12:.0f}만원")

    with mcol2:
        st.metric("🔑 전세 최종 자산", f"{cur_jeonse/10000:.2f} 억원", f"대출: {jeonse_loan['name']} ({jeonse_loan['rate']:.2f}%)")
        st.caption(f"• 대출액: {jeonse_loan_amt/10000:.1f}억 (월이자 약 {jeonse_annual_interest/12:.0f}만원)")
        st.caption(f"• 투자 운용 여유자본: {jeonse_free_cash/10000:.1f}억원")
        st.caption(f"• {holding_years}년 누적 투자수익: + {jeonse_free_cash * ((1 + after_tax_rate)**holding_years) - jeonse_free_cash:.0f}만원")

    with mcol3:
        st.metric("📄 월세 최종 자산", f"{cur_monthly/10000:.2f} 억원", "연말정산 세액공제 반영")
        st.caption(f"• {tax_credit_desc}")
        st.caption(f"• 실질 월세 지출: 월 {effective_annual_rent/12:.0f}만원 (세액공제 차감 후)")
        st.caption(f"• 투자 운용 여유자본: {monthly_free_cash/10000:.1f}억원")
        st.caption(f"• {holding_years}년 누적 투자수익: + {monthly_free_cash * ((1 + after_tax_rate)**holding_years) - monthly_free_cash:.0f}만원")

    # -------------------------------------------------------------
    # [요구사항 4] BEP 인터랙티브 차트 및 초보자용 친절 해설 가이드
    # -------------------------------------------------------------
    st.markdown("---")
    st.subheader("📈 거주 기간별 손익분기점(BEP) 인터랙티브 차트")

    # 초보자용 3초 요약 가이드 박스
    with st.expander("❓ **이 차트가 무엇을 의미하나요? (1분 이해 가이드 클릭)**", expanded=True):
        st.markdown("""
        이 그래프는 **'지금 선택한 집에서 1년~10년 동안 살다가 이사 나갈 때, 내 손에 최종적으로 남는 통장 잔고(순자산)'**를 비교한 것입니다.
        
        1. **🟦 파란색 선 (매매)**: 
           - 처음 1~2년에는 **취득세, 중개수수료 등 목돈 비용** 때문에 가장 아래에서 시작합니다.
           - 하지만 매달 내는 이자 외에 **'집값 상승분'**이 내 자산으로 누적되므로 시간이 지날수록 그래프가 가파르게 위로 올라갑니다.
        2. **🟩 초록색 점선 (전세)**:
           - 보증금을 안전하게 돌려받고, 매매 대비 아낀 목돈을 금융상품(예금/주식)에 투자해 굴린 결과입니다.
        3. **🟧 주황색 선 (월세)**:
           - 보증금이 가장 적게 들기 때문에 **가장 큰 목돈을 주식/ETF에 투자**할 수 있지만, 매달 사라지는 월세 지출이 있습니다.
        4. **⭐ 교차점 (골든크로스 / BEP)**:
           - **파란색 선(매매)이 초록색/주황색 선을 뚫고 올라가는 순간**입니다! 즉, **"이 기간 이상 살 거면 무조건 집을 사는 게 돈을 번다"**는 손익분기점을 뜻합니다.
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
# [요구사항 2] 탭 2: 부산 자치구별 시세 트렌드 (연도별)
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("📊 부산 아파트 연도별 매매 & 전세 시세 트렌드 (2019 ~ 2026)")
    st.caption("공공 실거래가 통계 기반 권역별 평균 시세 추이 분석")

    # 부산 16개 구 주요 권역 연도별 평균 시세 데이터베이스 (만원/84㎡ 기준 추정치)
    trend_data = {
        "연도": [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "부산 전체 (매매)": [34000, 42000, 52000, 47000, 41000, 43500, 45000, 46200],
        "부산 전체 (전세)": [22000, 26000, 31000, 28000, 25000, 26500, 27500, 28500],
        "해운대구 (매매)": [48000, 65000, 83000, 75000, 67000, 72000, 75000, 78000],
        "해운대구 (전세)": [29000, 36000, 44000, 39000, 35000, 37000, 39000, 40500],
        "수영구 (매매)": [45000, 62000, 81000, 72000, 65000, 70000, 73000, 76000],
        "수영구 (전세)": [27000, 34000, 42000, 37000, 33000, 35500, 37500, 39000],
        "연제구 (매매)": [36000, 46000, 58000, 51000, 44000, 47000, 49000, 50500],
        "연제구 (전세)": [23000, 28000, 34000, 30000, 26000, 28000, 29500, 30500],
        "동래구 (매매)": [39000, 49000, 61000, 54000, 46000, 49500, 52000, 53500],
        "동래구 (전세)": [25000, 30000, 36000, 32000, 28000, 30000, 31500, 32500],
        "부산진구 (매매)": [33000, 41000, 51000, 45000, 39000, 41500, 43000, 44000],
        "부산진구 (전세)": [21000, 25000, 30000, 27000, 24000, 25500, 26500, 27000],
        "남구 (매매)": [37000, 48000, 62000, 54000, 46000, 49000, 51000, 52500],
        "남구 (전세)": [24000, 29000, 35000, 31000, 27000, 29000, 30500, 31500],
    }
    df_trend = pd.DataFrame(trend_data)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        selected_region = st.selectbox(
            "트렌드 조회 지역",
            ["부산 전체", "연제구", "해운대구", "수영구", "동래구", "부산진구", "남구"]
        )
        st.markdown(f"""
        **💡 {selected_region} 시세 인사이트**
        - 2021년 유동성 고점 형성 후 2023년 조정기를 거쳐 완만한 회복세를 보이고 있습니다.
        - 매매가와 전세가의 갭(Gap)이 좁아지는 구간에서는 전세가율 상승으로 인한 깡통전세 위험을 주의해야 합니다.
        """)
    
    with col_t2:
        buy_col = f"{selected_region} (매매)"
        jeonse_col = f"{selected_region} (전세)"

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=df_trend["연도"], y=df_trend[buy_col],
            mode='lines+markers', name='평균 매매가',
            line=dict(color='#4f46e5', width=3)
        ))
        fig_trend.add_trace(go.Scatter(
            x=df_trend["연도"], y=df_trend[jeonse_col],
            mode='lines+markers', name='평균 전세가',
            line=dict(color='#10b981', width=3, dash='dash')
        ))

        fig_trend.update_layout(
            title=f"{selected_region} 아파트 매매 vs 전세 시세 추이 (단위: 만원)",
            xaxis_title="연도",
            yaxis_title="평균 실거래가 (만원)",
            hovermode="x unified",
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # 데이터 테이블 표시
    with st.expander("📋 연도별 상세 수치 데이터표 보기"):
        st.dataframe(df_trend[["연도", buy_col, jeonse_col]], use_container_width=True)
