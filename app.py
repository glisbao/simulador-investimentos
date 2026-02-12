import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Simulador Patrimonial", layout="wide")

st.title("Projeção de Evolução Patrimonial")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Parâmetros Iniciais")
    patrimonio_inicial = st.number_input("Patrimônio Inicial (R$)", value=1000000.0, step=10000.0)
    
    col_d1, col_d2 = st.columns(2)
    data_inicio = col_d1.date_input("Data Inicial", value=datetime.today())
    data_fim = col_d2.date_input("Data Final", value=datetime.today() + relativedelta(years=10))
    
    st.header("2. Premissas (% a.a.)")
    retorno_anual = st.number_input("Retorno Esperado", value=12.0) / 100
    inflacao_anual = st.number_input("Inflação (IPCA)", value=4.5) / 100
    imposto_anual = st.number_input("Impostos sobre Rendimento", value=15.0) / 100
    variancia_anual = st.number_input("Variância (Volatilidade)", value=10.0) / 100
    
    st.header("3. Fluxo de Caixa")
    retirada_mensal = st.number_input("Retirada Mensal (R$)", value=5000.0, help="Use valores negativos para aportes")
    
    st.divider()
    # CHECKBOX NOVO AQUI
    exibir_sem_retiradas = st.checkbox("Mostrar cenário 'Sem Retiradas'", value=True)

# --- LÓGICA DE CÁLCULO ---
meses_totais = (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month)

if meses_totais <= 0:
    st.error("A Data Final deve ser posterior à Data Inicial.")
    st.stop()

# Ajuste das taxas para mensal
taxa_retorno_liq_mensal = ((1 + retorno_anual * (1 - imposto_anual))**(1/12)) - 1
taxa_inflacao_mensal = ((1 + inflacao_anual)**(1/12)) - 1

# Listas para armazenar a projeção
datas = [data_inicio + relativedelta(months=i) for i in range(meses_totais + 1)]
saldo_sem_retirada = [patrimonio_inicial]
saldo_com_retirada = [patrimonio_inicial]
banda_superior = [patrimonio_inicial]
banda_inferior = [patrimonio_inicial]

val_atual_sr = patrimonio_inicial
val_atual_cr = patrimonio_inicial

for i in range(1, meses_totais + 1):
    # 1. Sem Retiradas
    val_atual_sr = val_atual_sr * (1 + taxa_retorno_liq_mensal)
    saldo_sem_retirada.append(val_atual_sr)
    
    # 2. Com Retiradas
    retirada_atual = retirada_mensal * ((1 + taxa_inflacao_mensal)**i)
    val_atual_cr = val_atual_cr * (1 + taxa_retorno_liq_mensal) - retirada_atual
    if val_atual_cr < 0: val_atual_cr = 0
    saldo_com_retirada.append(val_atual_cr)
    
    # 3. Bandas (Volatilidade aumenta com raiz do tempo)
    desvio = val_atual_cr * (variancia_anual * np.sqrt(i/12))
    banda_superior.append(val_atual_cr + desvio)
    banda_inferior.append(max(0, val_atual_cr - desvio))

df = pd.DataFrame({
    'Data': datas,
    'Sem Retiradas': np.array(saldo_sem_retirada) / 1000000,
    'Com Retiradas': np.array(saldo_com_retirada) / 1000000,
    'Superior': np.array(banda_superior) / 1000000,
    'Inferior': np.array(banda_inferior) / 1000000
})

# --- GRÁFICO ---
fig = go.Figure()

# Bandas (Sempre visíveis)
fig.add_trace(go.Scatter(x=df['Data'], y=df['Superior'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
fig.add_trace(go.Scatter(x=df['Data'], y=df['Inferior'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 128, 0, 0.2)', name='Intervalo de Variância'))

# Linha Sem Retiradas (CONDICIONAL - Só aparece se o checkbox estiver marcado)
if exibir_sem_retiradas:
    fig.add_trace(go.Scatter(
        x=df['Data'], y=df['Sem Retiradas'],
        mode='lines', name='Sem Retiradas (Teórico)',
        line=dict(color='gray', width=2, dash='dot')
    ))

# Linha Principal
fig.add_trace(go.Scatter(
    x=df['Data'], y=df['Com Retiradas'],
    mode='lines', name='Com Retiradas (Real)',
    line=dict(color='green', width=3)
))

fig.update_layout(
    xaxis_title="Tempo",
    yaxis_title="Patrimônio (Milhões R$)",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    # AQUI ESTÁ A MUDANÇA DA CASA DECIMAL
    yaxis=dict(tickformat=".1f") 
)

st.plotly_chart(fig, use_container_width=True)

# --- RESUMO ---
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Patrimônio Final", f"R$ {saldo_com_retirada[-1]:,.2f}")
with col2:
    total_retirado = sum([retirada_mensal * ((1 + taxa_inflacao_mensal)**i) for i in range(len(datas))])
    st.metric("Total Saques", f"R$ {total_retirado:,.2f}")
with col3:
    st.metric("Retorno Líq. Mensal", f"{taxa_retorno_liq_mensal*100:.2f}%")
