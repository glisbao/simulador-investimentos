import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Simulador de Portfólio", layout="wide")

# Estilo CSS para forçar fundo branco e texto preto (visual "Relatório")
st.markdown("""
    <style>
        .stApp {
            background-color: #FFFFFF;
            color: #000000;
        }
        h1, h2, h3, p, label {
            color: #000000 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Projeção de Patrimônio com Bandas de Incerteza")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Parâmetros Iniciais")
    patrimonio_inicial = st.number_input("Patrimônio Inicial (R$)", value=1000000.0, step=10000.0)
    
    col_d1, col_d2 = st.columns(2)
    data_inicio = col_d1.date_input("Data Inicial", value=datetime.today())
    data_fim = col_d2.date_input("Data Final", value=datetime.today() + relativedelta(years=10))
    
    st.header("2. Premissas de Mercado (% a.a.)")
    retorno_anual = st.number_input("Retorno Esperado", value=12.0) / 100
    inflacao_anual = st.number_input("Inflação (IPCA)", value=4.5) / 100
    imposto_anual = st.number_input("Impostos sobre Rendimento", value=15.0) / 100
    variancia_anual = st.number_input("Variância (Volatilidade)", value=10.0) / 100
    
    st.header("3. Fluxo de Caixa")
    retirada_mensal = st.number_input("Retirada Mensal (R$)", value=5000.0, help="Use valores negativos para aportes")

# --- LÓGICA DE CÁLCULO ---

# Cálculo do número de meses
meses_totais = (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month)

if meses_totais <= 0:
    st.error("A Data Final deve ser posterior à Data Inicial.")
    st.stop()

# Ajuste das taxas para mensal (Linear conforme solicitado para simplicidade visual, mas composto financeiramente é o padrão)
# Usaremos a taxa equivalente mensal para projeção
taxa_retorno_liq_mensal = ((1 + retorno_anual * (1 - imposto_anual))**(1/12)) - 1
taxa_inflacao_mensal = ((1 + inflacao_anual)**(1/12)) - 1
volatilidade_mensal = variancia_anual / np.sqrt(12) 

# Listas para armazenar a projeção
datas = [data_inicio + relativedelta(months=i) for i in range(meses_totais + 1)]
saldo_sem_retirada = [patrimonio_inicial]
saldo_com_retirada = [patrimonio_inicial]
banda_superior = [patrimonio_inicial]
banda_inferior = [patrimonio_inicial]

# Loop de Projeção Mês a Mês
val_atual_sr = patrimonio_inicial
val_atual_cr = patrimonio_inicial
retirada_atual = retirada_mensal

for i in range(1, meses_totais + 1):
    # 1. Curva SEM Retiradas
    val_atual_sr = val_atual_sr * (1 + taxa_retorno_liq_mensal)
    saldo_sem_retirada.append(val_atual_sr)
    
    # 2. Curva COM Retiradas
    # A retirada é corrigida pela inflação acumulada
    retirada_atual = retirada_mensal * ((1 + taxa_inflacao_mensal)**i)
    
    val_atual_cr = val_atual_cr * (1 + taxa_retorno_liq_mensal) - retirada_atual
    # Evitar valores negativos para visualização logica
    if val_atual_cr < 0: val_atual_cr = 0
    saldo_com_retirada.append(val_atual_cr)
    
    # 3. Bandas de Incerteza (Cone de Volatilidade) com base na curva COM retiradas
    # O desvio padrão aumenta com a raiz quadrada do tempo
    desvio = val_atual_cr * (variancia_anual * np.sqrt(i/12))
    banda_superior.append(val_atual_cr + desvio)
    banda_inferior.append(max(0, val_atual_cr - desvio))

# Criando DataFrame para plotagem
df = pd.DataFrame({
    'Data': datas,
    'Sem Retiradas': np.array(saldo_sem_retirada) / 1000000, # Em Milhões
    'Com Retiradas': np.array(saldo_com_retirada) / 1000000,
    'Superior': np.array(banda_superior) / 1000000,
    'Inferior': np.array(banda_inferior) / 1000000
})

# --- GRÁFICO (PLOTLY) ---
fig = go.Figure()

# Banda de Incerteza (Sombreado)
fig.add_trace(go.Scatter(
    x=df['Data'], y=df['Superior'],
    mode='lines', line=dict(width=0),
    showlegend=False, hoverinfo='skip'
))

fig.add_trace(go.Scatter(
    x=df['Data'], y=df['Inferior'],
    mode='lines', line=dict(width=0),
    fill='tonexty', # Preenche até a linha superior
    fillcolor='rgba(0, 128, 0, 0.2)', # Verde translúcido
    name='Intervalo de Variância',
    showlegend=True
))

# Linha 1: Sem Retiradas (Referência)
fig.add_trace(go.Scatter(
    x=df['Data'], y=df['Sem Retiradas'],
    mode='lines',
    name='Patrimônio SEM Retiradas',
    line=dict(color='gray', width=2, dash='dot')
))

# Linha 2: Com Retiradas (Principal)
fig.add_trace(go.Scatter(
    x=df['Data'], y=df['Com Retiradas'],
    mode='lines',
    name='Patrimônio COM Retiradas (Real)',
    line=dict(color='green', width=3)
))

# Layout estrito conforme solicitado
fig.update_layout(
    title="Evolução do Patrimônio (Em Milhões de R$)",
    xaxis_title="Tempo (Meses/Anos)",
    yaxis_title="Patrimônio (Milhões R$)",
    template="plotly_white", # Fundo branco
    font=dict(color="black"), # Fonte preta
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# --- RESUMO NUMÉRICO ---
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Patrimônio Final Estimado", f"R$ {saldo_com_retirada[-1]:,.2f}")
with col2:
    retirada_acumulada = sum([retirada_mensal * ((1 + taxa_inflacao_mensal)**i) for i in range(len(datas))])
    st.metric("Total Retirado no Período", f"R$ {retirada_acumulada:,.2f}")
with col3:
    st.metric("Retorno Líquido Médio Mensal", f"{taxa_retorno_liq_mensal*100:.2f}%")
