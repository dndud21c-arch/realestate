import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="부산 부동산 진정한 주거비용(True Cost) 시뮬레이터",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 부산 부동산 실질 주거비 & 자산 성장 시뮬레이터")
st.caption("기회비용 · 숨은 부대비용 · 정책대출 룰셋 · 거주기간별 BEP 분석 엔진 (부산 지역 특화)")

# -----------------------------------------------------------------------------
# 사이드바: 입력 제어 패널
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("1. 매물 정보 설정")
    district = st.selectbox(
        "부산 자치구 선택",
        ["해운대구", "수영구", "부산진구", "남구", "동래구", "기장군", "사하구", "북구"]
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
    user_income = st.number_input("부부합산 연소득 (만원)", value=6500, step=500)
    
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

    # 배당소득세(15.4%) 차감 세후 복리 수익률
    after_tax_rate = (pre_tax_rate / 100) * (1 - 0.154)
    st.info(f"💡 세후 실질 복리 수익률: **{after_tax_rate*100:.2f}%** 적용")

    st.markdown("---")
    st.header("4. 시뮬레이션 변수")
    holding_years = st.slider("예상 거주 기간 (년)", min_value=1, max_value=10, value=4, step=1)
    price_growth_rate = st.slider("연평균 집값 상승률 가정 (%)", min_value=-3.0, max_value=6.0, value=2.0, step=0.5) / 100

# -----------------------------------------------------------------------------
# 5대 핵심 로직 연산 모듈
# -----------------------------------------------------------------------------

# [기능 5] 깡통전세 위험도 지수 산출
jeonse_ratio = (jeonse_price / buy_price) * 100
if jeonse_ratio < 70:
    risk_badge = f"🟢 **안전 매물** (전세가율 {jeonse_ratio:.1f}%) : HUG 전세보증금반환보증 할인 구간"
    badge_color = "success"
elif jeonse_ratio <= 80:
    risk_badge = f"🟡 **주의 요망** (전세가율 {jeonse_ratio:.1f}%) : 보증금 미반환 방지를 위해 보증보험 가입 필수"
    badge_color = "warning"
else:
    risk_badge = f"🔴 **깡통전세 고위험 매물** (전세가율 {jeonse_ratio:.1f}%) : 매매가 하락 시 보증금 미반환 위험 높음"
    badge_color = "error"

# [기능 3] 정책 대출 룰베이스 엔진 (부산 지방 우대금리 -0.2%p 자동 반영)
def evaluate_loans():
    # 기본값: 시중은행 대출
    buy_loan = {"name": "시중 주담대", "rate": 3.8, "limit": buy_price * 0.7}
    jeonse_loan = {"name": "시중 전세대출", "rate": 3.6, "limit": jeonse_price * 0.8}

    # 매매 정책대출 (디딤돌 계열 - 자산 5.11억 이하)
    if user_cash <= 51100 and buy_price <= 90000:
        if has_newborn and user_income <= 13000:
            buy_loan = {"name": "신생아 특례 디딤돌", "rate": 1.8 - 0.2, "limit": 40000}
        elif is_married and user_income <= 8500 and buy_price <= 60000:
            buy_loan = {"name": "신혼부부 디딤돌", "rate": 2.65 - 0.2, "limit": 32000}
        elif user_income <= 6000 and buy_price <= 50000:
            buy_loan = {"name": "내집마련 디딤돌", "rate": 2.85 - 0.2, "limit": 20000}

    # 전세 정책대출 (버팀목 계열 - 자산 3.45억 이하, 부산 보증금 3~4억 이하)
    if user_cash <= 34500:
        if has_newborn and user_income <= 13000 and jeonse_price <= 40000:
            jeonse_loan = {"name": "신생아 특례 버팀목", "rate": 1.3 - 0.2, "limit": 24000}
        elif is_married and user_income <= 7500 and jeonse_price <= 30000:
            jeonse_loan = {"name": "신혼부부 버팀목", "rate": 2.1 - 0.2, "limit": 16000}
        elif user_income <= 5000 and jeonse_price <= 20000:
            jeonse_loan = {"name": "일반 버팀목전세", "rate": 2.5 - 0.2, "limit": 8000}

    return buy_loan, jeonse_loan

buy_loan, jeonse_loan = evaluate_loans()

# [기능 2] 숨은 부대비용 및 보유세 연산
# 취득세 (6억 이하 1.1% 등) + 중개보수 0.4% + 등기법무사 비용
acq_tax_rate = 0.011 if buy_price <= 60000 else (0.022 if buy_price <= 90000 else 0.033)
buy_initial_costs = (buy_price * acq_tax_rate) + (buy_price * 0.004) + 80
# 공시가격 69% 추정 재산세 + 지역건보료 추가분(연 36만)
buy_annual_holding = (buy_price * 0.69 * 0.002) + 36

# 대출 필요액 및 자본 배치 계산
buy_loan_amt = min(buy_loan["limit"], max(0, buy_price - user_cash))
buy_annual_interest = buy_loan_amt * (buy_loan["rate"] / 100)

jeonse_loan_amt = min(jeonse_loan["limit"], max(0, jeonse_price - user_cash))
jeonse_annual_interest = jeonse_loan_amt * (jeonse_loan["rate"] / 100)
jeonse_equity_used = jeonse_price - jeonse_loan_amt
jeonse_free_cash = max(0, user_cash - jeonse_equity_used)  # 대체투자 가능 자본

monthly_free_cash = max(0, user_cash - monthly_deposit)    # 대체투자 가능 자본
monthly_annual_rent = monthly_rent * 12

# [기능 1 & 4] 타임라인(1~10년) 순자산 궤적 및 BEP 산출
years = list(range(1, 11))
buy_trajectory = []
jeonse_trajectory = []
monthly_trajectory = []
bep_year = None

for t in years:
    # 매매: 미래가치 - 대출원금 - 초기취득비용 - 누적(이자 + 보유세)
    future_val = buy_price * ((1 + price_growth_rate) ** t)
    buy_nw = future_val - buy_loan_amt - buy_initial_costs - (buy_annual_interest + buy_annual_holding) * t
    buy_trajectory.append(buy_nw)

    # 전세: 전세보증금 + (여유자본 * (1+r)^t) - 대출원금 - 누적(대출이자 + HUG보증료)
    jeonse_invest_fv = jeonse_free_cash * ((1 + after_tax_rate) ** t)
    jeonse_guarantee = (jeonse_price * 0.0012) * t
    jeonse_nw = jeonse_price + jeonse_invest_fv - jeonse_loan_amt - (jeonse_annual_interest * t) - jeonse_guarantee
    jeonse_trajectory.append(jeonse_nw)

    # 월세: 월세보증금 + (여유자본 * (1+r)^t) - 누적월세
    monthly_invest_fv = monthly_free_cash * ((1 + after_tax_rate) ** t)
    monthly_nw = monthly_deposit + monthly_invest_fv - (monthly_annual_rent * t)
    monthly_trajectory.append(monthly_nw)

    # 매매 역전 골든크로스(BEP) 판별
    if bep_year is None and buy_nw > max(jeonse_nw, monthly_nw):
        bep_year = t

# -----------------------------------------------------------------------------
# 메인 화면 렌더링
# -----------------------------------------------------------------------------

# 1. 깡통전세 위험도 배너
if badge_color == "success":
    st.success(f"📍 **{district} 시세 분석 결과**: {risk_badge}")
elif badge_color == "warning":
    st.warning(f"📍 **{district} 시세 분석 결과**: {risk_badge}")
else:
    st.error(f"📍 **{district} 시세 분석 결과**: {risk_badge}")

# 2. 최종 추천 결과 콜아웃
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
    strategy_msg = f"저금리 기금 전세대출 레버리지 효과와 잉여자본의 투자 복리 효과가 매매 부대비용 부담보다 안정적입니다."
else:
    best_strategy = "월세"
    strategy_msg = f"목돈을 주거비에 묶지 않고 금융 자산에 투자(세후 연 {after_tax_rate*100:.2f}%)한 수익이 월세 지출을 압도합니다."

st.subheader(f"🎯 {holding_years}년 거주 시 최적 선택: **'{best_strategy}'**")
st.markdown(f"> {strategy_msg} (예상 최종 순자산: **{best_val/10000:.2f}억원**)")

# 3. 3자 비교 메트릭 카드
mcol1, mcol2, mcol3 = st.columns(3)
with mcol1:
    st.metric(
        label="🏠 매매 선택 시 최종 자산",
        value=f"{cur_buy/10000:.2f} 억원",
        delta=f"추천 대출: {buy_loan['name']} ({buy_loan['rate']:.2f}%)"
    )
    st.caption(f"• 대출 실행액: {buy_loan_amt/10000:.1f}억원 (월이자 약 {buy_annual_interest/12:.0f}만원)")
    st.caption(f"• 취득세/부대비용: 약 {buy_initial_costs:.0f}만원")
    st.caption(f"• 월할 보유세/건보료: 월 약 {buy_annual_holding/12:.0f}만원")

with mcol2:
    st.metric(
        label="🔑 전세 선택 시 최종 자산",
        value=f"{cur_jeonse/10000:.2f} 억원",
        delta=f"추천 대출: {jeonse_loan['name']} ({jeonse_loan['rate']:.2f}%)"
    )
    st.caption(f"• 대출 실행액: {jeonse_loan_amt/10000:.1f}억원 (월이자 약 {jeonse_annual_interest/12:.0f}만원)")
    st.caption(f"• 투자 운용 여유자본: {jeonse_free_cash/10000:.1f}억원")
    st.caption(f"• {holding_years}년 누적 투자수익: + {jeonse_free_cash * ((1 + after_tax_rate)**holding_years) - jeonse_free_cash:.0f}만원")

with mcol3:
    st.metric(
        label="📄 월세 선택 시 최종 자산",
        value=f"{cur_monthly/10000:.2f} 억원",
        delta="대출 불필요 (순수 투자 집중)"
    )
    st.caption(f"• 월세 순수 지출: 월 {monthly_rent}만원 ({holding_years}년 총 {monthly_annual_rent*holding_years:.0f}만원)")
    st.caption(f"• 투자 운용 여유자본: {monthly_free_cash/10000:.1f}억원")
    st.caption(f"• {holding_years}년 누적 투자수익: + {monthly_free_cash * ((1 + after_tax_rate)**holding_years) - monthly_free_cash:.0f}만원")

# 4. 인터랙티브 BEP 타임라인 그래프 (Plotly)
st.markdown("---")
st.subheader("📈 거주 기간별 손익분기점(BEP) 인터랙티브 차트")

fig = go.Figure()
fig.add_trace(go.Scatter(x=years, y=buy_trajectory, mode='lines+markers', name='매매(자가)', line=dict(color='#4f46e5', width=3)))
fig.add_trace(go.Scatter(x=years, y=jeonse_trajectory, mode='lines+markers', name='전세', line=dict(color='#10b981', width=2.5, dash='dash')))
fig.add_trace(go.Scatter(x=years, y=monthly_trajectory, mode='lines+markers', name='월세', line=dict(color='#f59e0b', width=2.5)))

# 현재 거주기간 수직선 표시
fig.add_vline(x=holding_years, line_width=1.5, line_dash="dot", line_color="gray", annotation_text=f"현재 선택: {holding_years}년")

fig.update_layout(
    xaxis_title="거주 기간 (년)",
    yaxis_title="순자산 가치 (만원)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=40, b=20),
    height=450
)
st.plotly_chart(fig, use_container_width=True)

# BEP 안내 코멘트
if bep_year:
    st.info(f"💡 **BEP 분석 결과**: 현재 조건에서 매매는 **약 {bep_year}년차**부터 전·월세를 역전하여 최고 자산을 형성합니다.")
else:
    st.warning("💡 **BEP 분석 결과**: 현재 집값 변동률/투자수익률 조건에서는 **10년 이내에 전·월세의 자산 성장**이 더 우세합니다.")