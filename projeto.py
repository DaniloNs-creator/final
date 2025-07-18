import pandas as pd
import streamlit as st
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import time

# Configuração inicial da página
st.set_page_config(
    page_title="Análise de KPIs Contábeis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado com animações (incluindo estilo para metric cards)
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
        
        * {
            font-family: 'Montserrat', sans-serif;
        }
        
        .main {
            background-color: #f8f9fa;
        }
        
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
        }
        
        .header {
            font-size: 2.5em;
            font-weight: 700;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 0.5em;
            animation: fadeIn 1.5s ease-in-out;
        }
        
        .subheader {
            font-size: 1.2em;
            color: #7f8c8d;
            text-align: center;
            margin-bottom: 2em;
            animation: slideIn 1s ease-in-out;
        }
        
        .card {
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            padding: 20px;
            background-color: white;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            animation: fadeInUp 0.8s ease-out;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }
        
        .metric-card {
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            padding: 15px;
            background-color: white;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
        }
        
        .kpi-title {
            font-size: 1em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        
        .kpi-value {
            font-size: 1.8em;
            font-weight: 700;
            color: #2c3e50;
        }
        
        .positive {
            color: #27ae60;
        }
        
        .negative {
            color: #e74c3c;
        }
        
        .neutral {
            color: #3498db;
        }
        
        /* Restante do CSS permanece igual */
    </style>
    """, unsafe_allow_html=True)

load_css()

# Função para criar metric cards customizados
def custom_metric(label, value, delta=None):
    delta_color = "neutral"
    if delta:
        if isinstance(delta, str):
            delta_text = delta
        else:
            delta_text = f"{delta:+.2f}%" if "%" in value else f"{delta:+,.2f}"
            delta_color = "positive" if (isinstance(delta, (int, float)) and delta >= 0) else "negative"
    
    html = f"""
    <div class="metric-card">
        <div class="kpi-title">{label}</div>
        <div class="kpi-value">{value}</div>
        {f'<div class="{delta_color}">{delta_text}</div>' if delta else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# Header (o mesmo do código anterior)
st.markdown('<p class="header">Dashboard de Análise de KPIs Contábeis</p>', unsafe_allow_html=True)
st.markdown('<p class="subheader">Análise completa de demonstrações financeiras baseada na ECD (Layouts J100 e J155)</p>', unsafe_allow_html=True)

# Restante do código permanece igual, substituindo apenas:
# st.metric() por custom_metric() nas seções de KPIs

# Na seção de KPIs, substitua:
# col1.metric(...) por col1.write(custom_metric(...), etc.

# Exemplo de como ficaria a seção de KPIs:
st.markdown("---")
st.subheader("Indicadores Financeiros")

col1, col2, col3, col4 = st.columns(4)

with col1:
    custom_metric(label="Receita Líquida", value=f"R$ {receita_liquida:,.2f}")
    custom_metric(label="Margem Bruta", value=f"{margem_bruta:.2f}%", delta=margem_bruta - 20)

with col2:
    custom_metric(label="Lucro Líquido", value=f"R$ {lucro_liquido:,.2f}")
    custom_metric(label="Margem Líquida", value=f"{margem_liquida:.2f}%", delta=margem_liquida - 8)

# ... e assim por diante para as outras métricas
