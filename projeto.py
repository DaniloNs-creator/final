import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO

# Configuração inicial da página
st.set_page_config(page_title="Análise de KPIs Contábeis", layout="wide")
st.title("📊 Análise de KPIs das Demonstrações Contábeis")
st.subheader("Baseado na ECD - Bloco L155")

# Função para processar o arquivo da ECD
def processar_ecd(arquivo):
    try:
        # Lendo o arquivo como texto
        conteudo = StringIO(arquivo.getvalue().decode("latin-1"))
        linhas = conteudo.readlines()
        
        # Filtrando apenas o bloco L155
        l155 = [linha for linha in linhas if linha.startswith("|L155|")]
        
        if not l155:
            st.error("Nenhum registro do bloco L155 encontrado no arquivo.")
            return None
        
        # Criando DataFrame
        dados = []
        for linha in l155:
            partes = linha.split("|")
            if len(partes) >= 8:
                dados.append({
                    "Data": partes[2],
                    "Código Conta": partes[3],
                    "Descrição Conta": partes[4],
                    "Valor": float(partes[5].replace(",", ".")),
                    "Indicador": partes[6],
                    "CNPJ": partes[7]
                })
        
        df = pd.DataFrame(dados)
        return df
    
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        return None

# Função para calcular KPIs
def calcular_kpis(df):
    kpis = {}
    
    try:
        # Extraindo valores relevantes
        receita_bruta = df[df["Código Conta"] == "3"]["Valor"].sum()
        custos = df[df["Código Conta"].str.startswith("4")]["Valor"].sum()
        despesas = df[df["Código Conta"].str.startswith("5")]["Valor"].sum()
        lucro_liquido = df[df["Código Conta"] == "3.11"]["Valor"].sum()
        ativo_total = df[df["Código Conta"] == "1"]["Valor"].sum()
        patrimonio_liquido = df[df["Código Conta"] == "2.01"]["Valor"].sum()
        
        # Calculando KPIs
        kpis["Lucro Líquido"] = lucro_liquido
        kpis["Margem Líquida"] = (lucro_liquido / receita_bruta) * 100 if receita_bruta != 0 else 0
        kpis["ROE"] = (lucro_liquido / patrimonio_liquido) * 100 if patrimonio_liquido != 0 else 0
        kpis["ROA"] = (lucro_liquido / ativo_total) * 100 if ativo_total != 0 else 0
        kpis["Margem de Contribuição"] = ((receita_bruta - custos) / receita_bruta) * 100 if receita_bruta != 0 else 0
        kpis["EBITDA"] = lucro_liquido + despesas  # Simplificação
        
    except Exception as e:
        st.error(f"Erro ao calcular KPIs: {str(e)}")
    
    return kpis

# Sidebar - Upload do arquivo
with st.sidebar:
    st.header("Configurações")
    arquivo = st.file_uploader("📤 Importar Arquivo da ECD (TXT)", type="txt")
    
    if arquivo:
        st.success("Arquivo carregado com sucesso!")
        df_ecd = processar_ecd(arquivo)
        
        if df_ecd is not None:
            st.session_state['df_ecd'] = df_ecd
            st.session_state['kpis'] = calcular_kpis(df_ecd)

# Página principal
if 'df_ecd' not in st.session_state:
    st.info("Por favor, importe um arquivo da ECD usando o menu lateral.")
    st.stop()

# Mostrando dados brutos
with st.expander("🔍 Visualizar Dados da ECD (Bloco L155)"):
    st.dataframe(st.session_state['df_ecd'])

# KPIs principais
st.header("📈 Principais Indicadores Financeiros")

if 'kpis' in st.session_state:
    kpis = st.session_state['kpis']
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Lucro Líquido", f"R$ {kpis['Lucro Líquido']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.metric("ROE", f"{kpis['ROE']:.2f}%")
    with col2:
        st.metric("Margem Líquida", f"{kpis['Margem Líquida']:.2f}%")
        st.metric("ROA", f"{kpis['ROA']:.2f}%")
    with col3:
        st.metric("Margem de Contribuição", f"{kpis['Margem de Contribuição']:.2f}%")
        st.metric("EBITDA", f"R$ {kpis['EBITDA']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

# Análise gráfica
st.header("📊 Análise Gráfica")

# Gráfico de composição do resultado
try:
    df_resultado = st.session_state['df_ecd'][st.session_state['df_ecd']['Código Conta'].str.startswith(('3', '4', '5'))]
    df_resultado = df_resultado.groupby("Descrição Conta")["Valor"].sum().reset_index()
    
    fig = px.bar(df_resultado, 
                 x="Descrição Conta", 
                 y="Valor", 
                 title="Composição do Resultado",
                 color="Descrição Conta")
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.warning(f"Não foi possível gerar o gráfico de composição: {str(e)}")

# Análise temporal (se houver dados de vários períodos)
try:
    if len(st.session_state['df_ecd']['Data'].unique()) > 1:
        df_temporal = st.session_state['df_ecd'].groupby("Data")["Valor"].sum().reset_index()
        fig = px.line(df_temporal, 
                     x="Data", 
                     y="Valor", 
                     title="Evolução Temporal dos Valores Contábeis")
        st.plotly_chart(fig, use_container_width=True)
except:
    st.info("Dados insuficientes para análise temporal (apenas um período encontrado).")

# Exportar relatório
st.header("📤 Exportar Relatório")

if st.button("Gerar Relatório em Excel"):
    try:
        # Criando um Excel com abas diferentes
        with pd.ExcelWriter("relatorio_kpis.xlsx") as writer:
            st.session_state['df_ecd'].to_excel(writer, sheet_name="Dados ECD", index=False)
            
            # Sheet de KPIs
            df_kpis = pd.DataFrame.from_dict(st.session_state['kpis'], orient="index", columns=["Valor"])
            df_kpis.to_excel(writer, sheet_name="KPIs")
            
        with open("relatorio_kpis.xlsx", "rb") as f:
            st.download_button("Baixar Relatório", f, file_name="relatorio_kpis.xlsx")
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {str(e)}")
