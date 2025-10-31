import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# --------------------------
# Page Config
# --------------------------
st.set_page_config(page_title="🇳🇱 DGA Withdrawal Planner — Capital & Tax Simulator", layout="wide")
st.title("🇳🇱 DGA Withdrawal Planner — Capital & Tax Simulator")

# --------------------------
# Current Year
# --------------------------
current_year = datetime.date.today().year

# --------------------------
# Sidebar Inputs in Expanders
# --------------------------
with st.sidebar.expander("Capital & Returns", expanded=True):
    start_capital = st.number_input("Starting capital (€)", 50000, 10000000, 3000000, 5000)
    annual_return = st.number_input("Average annual return (%)", 0.0, 15.0, 4.0, 0.1)/100
    inflation = st.number_input("Inflation (%)", 0.0, 10.0, 2.0, 0.1)/100
    years = st.number_input("Projection period (years)", 1, 50, 35, 1)

with st.sidebar.expander("Taxes", expanded=True):
    tax_threshold1 = st.number_input("Lower rate threshold (€)", 200000, 1000000, 200000, 50000)
    tax_rate1 = st.number_input("Tax below threshold (%)", 0.0, 50.0, 19.0, 0.1)/100
    tax_rate2 = st.number_input("Tax above threshold (%)", 0.0, 50.0, 25.8, 0.1)/100
    dividend_tax = st.number_input("Dividend tax (%)", 0.0, 50.0, 25.0, 0.1)/100

with st.sidebar.expander("Withdrawals", expanded=True):
    auto_calc_withdrawal = st.checkbox("Automatically calculate net withdrawal")
    if not auto_calc_withdrawal:
        net_withdrawal = st.number_input("Initial net withdrawal (€)", 5000, 500000, 30000, 1000)
    st.markdown(
        "If automatic calculation is selected, the script calculates net withdrawals to deplete the capital over the chosen number of years."
    )

# --------------------------
# Function: simulate withdrawal
# --------------------------
def simulate_withdrawal(start_capital, annual_return, inflation, net_withdrawal,
                        tax_threshold1, tax_rate1, tax_rate2, dividend_tax, years):
    capital = start_capital
    capital_depleted = False
    data = []

    # Year 0
    data.append({
        "Year": current_year,
        "Profit": 0,
        "Profit Tax": 0,
        "Dividend Tax": 0,
        "Gross Withdrawal": 0,
        "Net Withdrawal": 0,
        "End Capital": capital
    })

    for year in range(1, years + 1):
        cal_year = current_year + year
        profit = capital * annual_return

        # Progressive tax (single threshold)
        if profit <= tax_threshold1:
            profit_tax = profit * tax_rate1
        else:
            profit_tax = tax_threshold1 * tax_rate1 + (profit - tax_threshold1) * tax_rate2

        # Inflation-adjusted net withdrawal
        adjusted_net_withdrawal = net_withdrawal * ((1 + inflation) ** (year - 1))
        gross_withdrawal = adjusted_net_withdrawal / (1 - dividend_tax)
        dividend_paid = gross_withdrawal * dividend_tax

        projected_capital = capital + profit - profit_tax - gross_withdrawal

        if projected_capital < 0:
            gross_withdrawal += projected_capital
            adjusted_net_withdrawal = gross_withdrawal * (1 - dividend_tax)
            dividend_paid = gross_withdrawal * dividend_tax
            capital = 0
            capital_depleted = True
        else:
            capital = projected_capital

        data.append({
            "Year": cal_year,
            "Profit": profit,
            "Profit Tax": profit_tax,
            "Dividend Tax": dividend_paid,
            "Gross Withdrawal": gross_withdrawal,
            "Net Withdrawal": adjusted_net_withdrawal,
            "End Capital": capital
        })

        if capital_depleted:
            break

    df = pd.DataFrame(data)
    return df, capital_depleted, capital

# --------------------------
# Automatic Net Withdrawal Calculation
# --------------------------
if auto_calc_withdrawal:
    tol = 1  # tolerance in euros
    low, high = 0, start_capital * 2
    while high - low > tol:
        test_withdrawal = (low + high) / 2
        df, capital_depleted, end_capital = simulate_withdrawal(
            start_capital, annual_return, inflation, test_withdrawal,
            tax_threshold1, tax_rate1, tax_rate2, dividend_tax, years
        )
        if end_capital > 0:
            low = test_withdrawal
        else:
            high = test_withdrawal
    net_withdrawal = (low + high) / 2
    
    st.sidebar.markdown(
        f"**✅ Calculated net withdrawal:** € {net_withdrawal:,.0f} per year  \n"
        f"*This amount depletes the capital to 0 after {years} years.*"
    )

# --------------------------
# Simulate
# --------------------------
df, capital_depleted, capital = simulate_withdrawal(
    start_capital, annual_return, inflation, net_withdrawal,
    tax_threshold1, tax_rate1, tax_rate2, dividend_tax, years
)

# --------------------------
# Highlight Functions
# --------------------------
def highlight_negative(val):
    color = 'red' if val < 0 else ''
    return f'color: {color}'

def highlight_net_withdrawal(val):
    return 'background-color: #D2F8D2'

# --------------------------
# Metrics Row
# --------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Starting Capital", f"€ {start_capital:,.0f}")
col2.metric("📈 End Capital", f"€ {capital:,.0f}")
col3.metric("🧾 Total Profit Tax", f"€ {df['Profit Tax'].sum():,.0f}")
col4.metric("🧾 Total Dividend Tax", f"€ {df['Dividend Tax'].sum():,.0f}")

if capital_depleted:
    st.warning(f"💡 Capital depleted in year {int(df.iloc[-1]['Year'])}! Consider reducing withdrawals or increasing returns.")

if auto_calc_withdrawal:
    st.info(f"✅ Net withdrawal of € {net_withdrawal:,.0f} is automatically calculated to deplete the capital after {years} years.")

# --------------------------
# Interactive Plotly Chart
# --------------------------
st.subheader("Capital Development Over Time")
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["Year"], 
    y=df["Net Withdrawal"], 
    mode='lines+markers', 
    name="Net Withdrawal", 
    line=dict(color='green', width=3, dash='dash' if auto_calc_withdrawal else 'solid'),
    hovertemplate='Year: %{x}<br>Net Withdrawal: €%{y:.0f}<extra></extra>'
))

fig.add_trace(go.Scatter(
    x=df["Year"], 
    y=df["End Capital"], 
    mode='lines+markers', 
    name="End Capital", 
    line=dict(color='blue'),
    hovertemplate='Year: %{x}<br>End Capital: €%{y:.0f}<extra></extra>'
))

fig.add_trace(go.Scatter(
    x=df["Year"], 
    y=df["Profit"], 
    mode='lines+markers', 
    name="Profit", 
    line=dict(color='orange'),
    hovertemplate='Year: %{x}<br>Profit: €%{y:.0f}<extra></extra>'
))

fig.add_trace(go.Scatter(
    x=df["Year"], 
    y=df["Profit Tax"], 
    mode='lines+markers', 
    name="Profit Tax", 
    line=dict(color='red'),
    hovertemplate='Year: %{x}<br>Profit Tax: €%{y:.0f}<extra></extra>'
))

fig.update_layout(
    xaxis_title="Year",
    yaxis_title="Amount (€)",
    hovermode="x unified",
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True, theme="streamlit")

# --------------------------
# Yearly Table
# --------------------------
st.subheader("Yearly Table")
st.dataframe(df.style.format({
    "Profit": "€ {:,.0f}",
    "Profit Tax": "€ {:,.0f}",
    "Dividend Tax": "€ {:,.0f}",
    "Gross Withdrawal": "€ {:,.0f}",
    "Net Withdrawal": "€ {:,.0f}",
    "End Capital": "€ {:,.0f}"
}).applymap(highlight_negative, subset=["End Capital"])
  .applymap(highlight_net_withdrawal, subset=["Net Withdrawal"]),
  use_container_width=True, height=500)

# --------------------------
# Download Buttons Side by Side
# --------------------------
col1, col2 = st.columns(2)
col1.download_button("📥 Download CSV", df.to_csv(index=False), "dga_simulation.csv", "text/csv")

# PDF creation
def create_pdf(dataframe):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    data = [list(dataframe.columns)] + dataframe.round(0).astype(int).astype(str).values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.gray),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    doc.build([table])
    buffer.seek(0)
    return buffer

pdf_buffer = create_pdf(df)
col2.download_button("📥 Download PDF", pdf_buffer, "dga_simulation.pdf", "application/pdf")

