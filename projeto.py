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
        
