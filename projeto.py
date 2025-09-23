import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import tempfile
import gc
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import psutil
import traceback
from io import BytesIO

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Sistema de Processamento Massivo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações
BATCH_SIZE = 1000
MAX_WORKERS = min(multiprocessing.cpu_count(), 8)
MEMORY_THRESHOLD = 85

# --- FUNÇÃO SLIDER SEGURA ---
def create_safe_slider(df, column, label, default_range=None):
    """
    Cria um slider com verificação de valores mínimos e máximos
    """
    try:
        if df.empty or column not in df.columns:
            return None
            
        min_val = float(df[column].min())
        max_val = float(df[column].max())
        
        # Verifica se os valores são válidos
        if min_val == max_val:
            st.warning(f"⚠️ A coluna '{column}' possui apenas um valor único: {min_val}")
            return (min_val, max_val)
        
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        
        # Define valores padrão seguros
        if default_range is None:
            default_range = (min_val, max_val)
        else:
            default_low = max(min_val, default_range[0])
            default_high = min(max_val, default_range[1])
            default_range = (default_low, default_high)
        
        return st.slider(
            label=label,
            min_value=min_val,
            max_value=max_val,
            value=default_range,
            step=(max_val - min_val) / 100 if (max_val - min_val) > 0 else 0.1
        )
        
    except Exception as e:
        st.error(f"Erro ao criar slider para {column}: {str(e)}")
        return None

# --- PROCESSADOR CT-E CORRIGIDO ---
def processador_cte_corrigido():
    st.title("🚚 Processador de CT-e para Grandes Volumes")
    
    # Simulação de dados para demonstração
    if 'cte_data' not in st.session_state:
        # Dados de exemplo - substitua pelos seus dados reais
        np.random.seed(42)
        n_records = 1000
        
        st.session_state.cte_data = pd.DataFrame({
            'Arquivo': [f'cte_{i}.xml' for i in range(n_records)],
            'nCT': [f'41190600000000{i:03d}' for i in range(n_records)],
            'Data Emissão': pd.date_range('2024-01-01', periods=n_records, freq='D').strftime('%d/%m/%y'),
            'UF Início': np.random.choice(['SP', 'RJ', 'MG', 'RS', 'PR'], n_records),
            'UF Fim': np.random.choice(['SP', 'RJ', 'MG', 'RS', 'PR'], n_records),
            'Emitente': [f'Emitente {i}' for i in range(n_records)],
            'Valor Prestação': np.random.uniform(1000, 50000, n_records),
            'Peso Bruto (kg)': np.random.uniform(1000, 25000, n_records),
            'Tipo de Peso Encontrado': np.random.choice(['PESO BRUTO', 'PESO BASE DE CALCULO'], n_records),
            'Remetente': [f'Remetente {i}' for i in range(n_records)],
            'Destinatário': [f'Destinatário {i}' for i in range(n_records)]
        })
    
    df = st.session_state.cte_data
    
    # --- ABA DE VISUALIZAÇÃO CORRIGIDA ---
    st.header("📊 Dados Processados")
    st.write(f"Total de CT-es processados: {len(df)}")
    
    # Filtros seguros
    col1, col2 = st.columns(2)
    
    with col1:
        uf_options = df['UF Início'].unique().tolist()
        uf_filter = st.multiselect(
            "Filtrar por UF Início", 
            options=uf_options,
            default=uf_options[:2] if len(uf_options) > 1 else uf_options
        )
    
    with col2:
        tipo_peso_options = df['Tipo de Peso Encontrado'].unique().tolist()
        tipo_peso_filter = st.multiselect(
            "Filtrar por Tipo de Peso", 
            options=tipo_peso_options,
            default=tipo_peso_options
        )
    
    # Aplica filtros multiselect
    filtered_df = df.copy()
    
    if uf_filter:
        filtered_df = filtered_df[filtered_df['UF Início'].isin(uf_filter)]
    
    if tipo_peso_filter:
        filtered_df = filtered_df[filtered_df['Tipo de Peso Encontrado'].isin(tipo_peso_filter)]
    
    # --- SLIDER SEGURO PARA PESO ---
    st.subheader("🔧 Filtro por Peso Bruto (Corrigido)")
    
    if not filtered_df.empty:
        # Verifica se temos dados após os filtros
        peso_min = float(filtered_df['Peso Bruto (kg)'].min())
        peso_max = float(filtered_df['Peso Bruto (kg)'].max())
        
        # Critério para determinar se usa slider ou não
        use_slider = (peso_max - peso_min) > 0.001  # Margem de tolerância
        
        if use_slider:
            peso_filter = create_safe_slider(
                filtered_df, 
                'Peso Bruto (kg)', 
                "Selecione a faixa de peso (kg)",
                default_range=(peso_min, peso_max)
            )
            
            if peso_filter:
                filtered_df = filtered_df[
                    (filtered_df['Peso Bruto (kg)'] >= peso_filter[0]) & 
                    (filtered_df['Peso Bruto (kg)'] <= peso_filter[1])
                ]
        else:
            st.info(f"ℹ️ Faixa de peso limitada: {peso_min:.2f} kg")
            filtered_df = filtered_df[filtered_df['Peso Bruto (kg)'] >= peso_min]
    
    # Exibe dataframe com verificação de dados
    if not filtered_df.empty:
        st.success(f"✅ {len(filtered_df)} registros após filtros")
        
        colunas_principais = [
            'Arquivo', 'nCT', 'Data Emissão', 'Emitente', 
            'UF Início', 'UF Fim', 'Peso Bruto (kg)', 
            'Tipo de Peso Encontrado', 'Valor Prestação'
        ]
        
        # Seleção de colunas para exibição
        colunas_selecionadas = st.multiselect(
            "Selecione as colunas para exibir:",
            options=colunas_principais,
            default=colunas_principais
        )
        
        if colunas_selecionadas:
            st.dataframe(filtered_df[colunas_selecionadas], use_container_width=True)
        
        # Estatísticas
        st.subheader("📈 Estatísticas")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Valor", f"R$ {filtered_df['Valor Prestação'].sum():,.2f}")
        
        with col2:
            st.metric("Peso Total", f"{filtered_df['Peso Bruto (kg)'].sum():,.0f} kg")
        
        with col3:
            avg_peso = filtered_df['Peso Bruto (kg)'].mean()
            st.metric("Média Peso", f"{avg_peso:,.0f} kg")
        
        with col4:
            st.metric("CT-es Válidos", len(filtered_df))
        
        # Gráficos condicionais
        if len(filtered_df) > 1:  # Só exibe gráficos se houver dados suficientes
            st.subheader("📊 Visualizações")
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                try:
                    tipo_counts = filtered_df['Tipo de Peso Encontrado'].value_counts()
                    if len(tipo_counts) > 0:
                        fig_tipo = px.pie(
                            values=tipo_counts.values,
                            names=tipo_counts.index,
                            title="Distribuição por Tipo de Peso"
                        )
                        st.plotly_chart(fig_tipo, use_container_width=True)
                except Exception as e:
                    st.warning("Não foi possível gerar o gráfico de distribuição")
            
            with col_chart2:
                try:
                    if len(filtered_df) > 1:
                        fig_relacao = px.scatter(
                            filtered_df,
                            x='Peso Bruto (kg)',
                            y='Valor Prestação',
                            title="Relação Peso x Valor",
                            color='Tipo de Peso Encontrado'
                        )
                        st.plotly_chart(fig_relacao, use_container_width=True)
                except Exception as e:
                    st.warning("Não foi possível gerar o gráfico de relação")
        
    else:
        st.warning("⚠️ Nenhum dado encontrado com os filtros aplicados.")
        st.info("💡 Tente ajustar os filtros para visualizar os dados.")
    
    # --- ABA DE EXPORTAÇÃO ---
    st.header("📥 Exportar Dados")
    
    if not filtered_df.empty:
        export_format = st.radio(
            "Formato de exportação:",
            ["Parquet (Recomendado)", "Excel", "CSV"]
        )
        
        if st.button("💾 Gerar Arquivo de Exportação"):
            try:
                if export_format == "Parquet (Recomendado)":
                    buffer = BytesIO()
                    filtered_df.to_parquet(buffer)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="⬇️ Baixar Parquet",
                        data=buffer,
                        file_name="cte_dados.parquet",
                        mime="application/octet-stream"
                    )
                
                elif export_format == "Excel":
                    if len(filtered_df) <= 1000000:  # Limite do Excel
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            filtered_df.to_excel(writer, index=False)
                        buffer.seek(0)
                        
                        st.download_button(
                            label="⬇️ Baixar Excel",
                            data=buffer,
                            file_name="cte_dados.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error("Excel suporta apenas até 1.000.000 linhas. Use Parquet.")
                
                else:  # CSV
                    csv = filtered_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Baixar CSV",
                        data=csv,
                        file_name="cte_dados.csv",
                        mime="text/csv"
                    )
                        
            except Exception as e:
                st.error(f"Erro na exportação: {str(e)}")
    
    # --- CONTROLES DE MANUTENÇÃO ---
    st.sidebar.header("⚙️ Controles do Sistema")
    
    if st.sidebar.button("🔄 Limpar Filtros"):
        if 'cte_data' in st.session_state:
            st.session_state.cte_data = st.session_state.cte_data  # Restaura dados originais
        st.rerun()
    
    if st.sidebar.button("🧹 Limpar Cache"):
        keys_to_keep = ['cte_data']
        keys_to_remove = [key for key in st.session_state.keys() if key not in keys_to_keep]
        for key in keys_to_remove:
            del st.session_state[key]
        gc.collect()
        st.sidebar.success("Cache limpo!")
        time.sleep(1)
        st.rerun()
    
    # Informações do sistema
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Status do Sistema")
    st.sidebar.write(f"Memória usada: {psutil.virtual_memory().percent}%")
    st.sidebar.write(f"Registros totais: {len(df)}")
    st.sidebar.write(f"Registros filtrados: {len(filtered_df)}")

# --- CSS E ESTILO ---
def load_css():
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(90deg, #2c3e50, #3498db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin: 1rem 0;
        }
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 0.5rem 0;
        }
        .warning-box {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 12px;
            margin: 10px 0;
            border-radius: 4px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- APLICAÇÃO PRINCIPAL ---
def main():
    """Função principal corrigida"""
    load_css()
    
    st.markdown('<div class="main-header">Sistema de Processamento Massivo de CT-e</div>', 
                unsafe_allow_html=True)
    
    try:
        processador_cte_corrigido()
    except Exception as e:
        st.error(f"❌ Erro crítico na aplicação: {str(e)}")
        with st.expander("🔍 Detalhes do erro"):
            st.code(traceback.format_exc())
        
        st.info("""
        **Soluções possíveis:**
        1. Recarregue a página (F5)
        2. Verifique os dados de entrada
        3. Limpe o cache do navegador
        """)

if __name__ == "__main__":
    import time
    main()