import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import io
import re

# Configuração da página
st.set_page_config(
    page_title="Análise de ECD - KPIs Contábeis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título do dashboard
st.title("📊 Análise de KPIs Contábeis - ECD")
st.markdown("Carregue o arquivo TXT da Escrituração Contábil Digital para análise dos registros J100 e J150")

# Funções para processar a ECD
def parse_ecd(file_content):
    """Processa o arquivo ECD e extrai os registros relevantes"""
    lines = file_content.split('\n')
    registros = []
    
    for line in lines:
        if line.strip() == '':
            continue
            
        # Verifica o tipo de registro (primeiros 4 caracteres)
        tipo_registro = line[:4].strip()
        
        # Processa apenas registros J100 e J150
        if tipo_registro in ['J100', 'J150']:
            registro = {
                'TIPO_REG': tipo_registro,
                'DT_INI': line[4:12].strip(),
                'DT_FIN': line[12:20].strip(),
                'COD_VER': line[20:22].strip(),
                'COD_FIN': line[22:24].strip(),
                'NOME': line[24:84].strip(),
                'CNPJ': line[84:98].strip(),
                'UF': line[98:100].strip(),
                'IE': line[100:114].strip(),
                'COD_MUN': line[114:122].strip(),
                'IM': line[122:136].strip(),
                'IND_SIT_ESP': line[136:138].strip()
            }
            
            if tipo_registro == 'J100':
                registro.update({
                    'COD_AGR': line[138:142].strip(),
                    'COD_CTA': line[142:202].strip(),
                    'COD_CCUS': line[202:262].strip(),
                    'VL_SLD_INI': float(line[262:282].strip() or 0) / 100,
                    'IND_VL_SLD_INI': line[282:283].strip(),
                    'VL_DEB': float(line[283:303].strip() or 0) / 100,
                    'VL_CRED': float(line[303:323].strip() or 0) / 100,
                    'VL_SLD_FIN': float(line[323:343].strip() or 0) / 100,
                    'IND_VL_SLD_FIN': line[343:344].strip()
                })
            elif tipo_registro == 'J150':
                registro.update({
                    'COD_CTA_REF': line[138:198].strip(),
                    'VL_CTA': float(line[198:218].strip() or 0) / 100,
                    'IND_VL_CTA': line[218:219].strip()
                })
            
            registros.append(registro)
    
    return pd.DataFrame(registros)

def processar_kpis(df_ecd):
    """Processa os registros da ECD para calcular os KPIs"""
    # Filtra apenas contas relevantes para KPIs
    contas_receita = ['3', '3.']  # Códigos de contas de receita (exemplo)
    contas_custo = ['4', '4.']    # Códigos de contas de custo
    contas_despesa = ['5', '5.']  # Códigos de contas de despesa
    
    # Extrai período da ECD
    dt_ini = pd.to_datetime(df_ecd['DT_INI'].iloc[0], format='%Y%m%d')
    dt_fin = pd.to_datetime(df_ecd['DT_FIN'].iloc[0], format='%Y%m%d')
    periodo = f"{dt_ini.strftime('%d/%m/%Y')} a {dt_fin.strftime('%d/%m/%Y')}"
    
    # Processa J100 (Balancete)
    df_j100 = df_ecd[df_ecd['TIPO_REG'] == 'J100'].copy()
    
    # Agrupa por natureza das contas
    receita_bruta = df_j100[df_j100['COD_CTA'].str.startswith(tuple(contas_receita))]['VL_CRED'].sum()
    custos = df_j100[df_j100['COD_CTA'].str.startswith(tuple(contas_custo))]['VL_DEB'].sum()
    despesas_oper = df_j100[df_j100['COD_CTA'].str.startswith(tuple(contas_despesa))]['VL_DEB'].sum()
    
    # Processa J150 (DRE)
    df_j150 = df_ecd[df_ecd['TIPO_REG'] == 'J150'].copy()
    
    # Tenta encontrar PL para cálculo do ROE
    patrimonio_liquido = df_j100[df_j100['COD_CTA'].str.contains('2.01.04')]['VL_SLD_FIN'].sum()  # Código exemplo para PL
    
    # Calcula KPIs
    lucro_bruto = receita_bruta - custos
    lucro_operacional = lucro_bruto - despesas_oper
    lucro_liquido = lucro_operacional  # Simplificado - na prática deve considerar todos os ajustes
    
    margem_bruta = lucro_bruto / receita_bruta if receita_bruta != 0 else 0
    margem_operacional = lucro_operacional / receita_bruta if receita_bruta != 0 else 0
    margem_liquida = lucro_liquido / receita_bruta if receita_bruta != 0 else 0
    roe = lucro_liquido / patrimonio_liquido if patrimonio_liquido != 0 else 0
    
    return {
        'PERIODO': periodo,
        'RECEITA_BRUTA': receita_bruta,
        'CUSTOS': custos,
        'DESPESAS_OPER': despesas_oper,
        'LUCRO_BRUTO': lucro_bruto,
        'LUCRO_OPERACIONAL': lucro_operacional,
        'LUCRO_LIQUIDO': lucro_liquido,
        'MARGEM_BRUTA': margem_bruta,
        'MARGEM_OPER': margem_operacional,
        'MARGEM_LIQUIDA': margem_liquida,
        'ROE': roe,
        'PATRIMONIO_LIQUIDO': patrimonio_liquido
    }

# Upload do arquivo ECD
uploaded_file = st.file_uploader("Carregue o arquivo TXT da ECD", type=['txt'])

if uploaded_file is not None:
    try:
        # Lê o arquivo
        stringio = io.StringIO(uploaded_file.getvalue().decode("latin-1"))
        file_content = stringio.read()
        
        # Processa o arquivo ECD
        df_ecd = parse_ecd(file_content)
        
        if len(df_ecd) == 0:
            st.error("Nenhum registro J100 ou J150 encontrado no arquivo!")
        else:
            # Processa KPIs
            kpis = processar_kpis(df_ecd)
            
            # Exibe informações da empresa
            st.subheader("Informações da Empresa")
            primeiro_registro = df_ecd.iloc[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("Nome", primeiro_registro['NOME'])
            col2.metric("CNPJ", primeiro_registro['CNPJ'])
            col3.metric("Período", kpis['PERIODO'])
            
            # Métricas principais
            st.subheader("Principais KPIs")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Receita Bruta", f"R$ {kpis['RECEITA_BRUTA']:,.2f}")
            col2.metric("Lucro Líquido", f"R$ {kpis['LUCRO_LIQUIDO']:,.2f}")
            col3.metric("Margem Líquida", f"{kpis['MARGEM_LIQUIDA']*100:.2f}%")
            col4.metric("ROE", f"{kpis['ROE']*100:.2f}%")
            
            # Abas para análise detalhada
            tab1, tab2, tab3 = st.tabs(["📈 Análise Vertical", "📊 Análise Horizontal", "🧮 Registros ECD"])
            
            with tab1:
                st.header("Análise Vertical da DRE")
                
                # Cria dataframe para análise vertical
                dre_data = [
                    {"Item": "Receita Bruta", "Valor": kpis['RECEITA_BRUTA'], "%": 100.0},
                    {"Item": "(-) Custos", "Valor": -kpis['CUSTOS'], "%": -(kpis['CUSTOS']/kpis['RECEITA_BRUTA']*100)},
                    {"Item": "(=) Lucro Bruto", "Valor": kpis['LUCRO_BRUTO'], "%": kpis['MARGEM_BRUTA']*100},
                    {"Item": "(-) Despesas Operacionais", "Valor": -kpis['DESPESAS_OPER'], "%": -(kpis['DESPESAS_OPER']/kpis['RECEITA_BRUTA']*100)},
                    {"Item": "(=) Lucro Operacional", "Valor": kpis['LUCRO_OPERACIONAL'], "%": kpis['MARGEM_OPER']*100},
                    {"Item": "(=) Lucro Líquido", "Valor": kpis['LUCRO_LIQUIDO'], "%": kpis['MARGEM_LIQUIDA']*100}
                ]
                df_dre = pd.DataFrame(dre_data)
                
                # Gráfico de análise vertical
                fig = px.bar(
                    df_dre,
                    x='Item',
                    y='%',
                    text=[f"{x:.1f}%" for x in df_dre['%']],
                    title="Análise Vertical da DRE (% da Receita Bruta)",
                    labels={'%': 'Percentual (%)', 'Item': 'Conta'}
                )
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela com valores
                st.dataframe(
                    df_dre.style.format({
                        'Valor': 'R$ {:.2f}',
                        '%': '{:.1f}%'
                    }),
                    use_container_width=True
                )
            
            with tab2:
                st.header("Análise Horizontal")
                st.warning("Para análise horizontal é necessário carregar mais de um período. Esta funcionalidade será implementada na próxima versão.")
            
            with tab3:
                st.header("Registros da ECD")
                
                # Filtros para os registros
                tipo_registro = st.selectbox("Tipo de Registro", options=['J100', 'J150'])
                df_filtrado = df_ecd[df_ecd['TIPO_REG'] == tipo_registro]
                
                # Mostra registros conforme layout da ECD
                if tipo_registro == 'J100':
                    cols = [
                        'COD_CTA', 'VL_SLD_INI', 'IND_VL_SLD_INI', 
                        'VL_DEB', 'VL_CRED', 'VL_SLD_FIN', 'IND_VL_SLD_FIN'
                    ]
                    st.dataframe(
                        df_filtrado[cols].style.format({
                            'VL_SLD_INI': 'R$ {:.2f}',
                            'VL_DEB': 'R$ {:.2f}',
                            'VL_CRED': 'R$ {:.2f}',
                            'VL_SLD_FIN': 'R$ {:.2f}'
                        }),
                        use_container_width=True
                    )
                else:  # J150
                    cols = ['COD_CTA_REF', 'VL_CTA', 'IND_VL_CTA']
                    st.dataframe(
                        df_filtrado[cols].style.format({
                            'VL_CTA': 'R$ {:.2f}'
                        }),
                        use_container_width=True
                    )
                
                # Mostra layout oficial do registro
                st.subheader(f"Layout Oficial do Registro {tipo_registro}")
                if tipo_registro == 'J100':
                    st.markdown("""
                    | Campo | Posição | Tamanho | Descrição |
                    |-------|---------|---------|-----------|
                    | TIPO_REG | 1-4 | 4 | Tipo do registro (J100) |
                    | DT_INI | 5-12 | 8 | Data inicial do período |
                    | DT_FIN | 13-20 | 8 | Data final do período |
                    | COD_VER | 21-22 | 2 | Código da versão do layout |
                    | COD_FIN | 23-24 | 2 | Código da finalidade do arquivo |
                    | NOME | 25-84 | 60 | Nome da empresa |
                    | CNPJ | 85-98 | 14 | CNPJ da empresa |
                    | UF | 99-100 | 2 | Sigla da UF |
                    | IE | 101-114 | 14 | Inscrição Estadual |
                    | COD_MUN | 115-122 | 8 | Código do município |
                    | IM | 123-136 | 14 | Inscrição Municipal |
                    | IND_SIT_ESP | 137-138 | 2 | Indicador de situação especial |
                    | COD_AGR | 139-142 | 4 | Código do agrupamento |
                    | COD_CTA | 143-202 | 60 | Código da conta contábil |
                    | COD_CCUS | 203-262 | 60 | Código do centro de custos |
                    | VL_SLD_INI | 263-282 | 20 | Valor do saldo inicial (com 2 decimais) |
                    | IND_VL_SLD_INI | 283 | 1 | Indicador da natureza do saldo inicial |
                    | VL_DEB | 284-303 | 20 | Valor do débito (com 2 decimais) |
                    | VL_CRED | 304-323 | 20 | Valor do crédito (com 2 decimais) |
                    | VL_SLD_FIN | 324-343 | 20 | Valor do saldo final (com 2 decimais) |
                    | IND_VL_SLD_FIN | 344 | 1 | Indicador da natureza do saldo final |
                    """)
                else:  # J150
                    st.markdown("""
                    | Campo | Posição | Tamanho | Descrição |
                    |-------|---------|---------|-----------|
                    | TIPO_REG | 1-4 | 4 | Tipo do registro (J150) |
                    | DT_INI | 5-12 | 8 | Data inicial do período |
                    | DT_FIN | 13-20 | 8 | Data final do período |
                    | COD_VER | 21-22 | 2 | Código da versão do layout |
                    | COD_FIN | 23-24 | 2 | Código da finalidade do arquivo |
                    | NOME | 25-84 | 60 | Nome da empresa |
                    | CNPJ | 85-98 | 14 | CNPJ da empresa |
                    | UF | 99-100 | 2 | Sigla da UF |
                    | IE | 101-114 | 14 | Inscrição Estadual |
                    | COD_MUN | 115-122 | 8 | Código do município |
                    | IM | 123-136 | 14 | Inscrição Municipal |
                    | IND_SIT_ESP | 137-138 | 2 | Indicador de situação especial |
                    | COD_CTA_REF | 139-198 | 60 | Código da conta de referência |
                    | VL_CTA | 199-218 | 20 | Valor da conta (com 2 decimais) |
                    | IND_VL_CTA | 219 | 1 | Indicador da natureza do valor |
                    """)
    
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")

else:
    st.info("Por favor, carregue o arquivo TXT da ECD para iniciar a análise")
    st.markdown("""
    ### Instruções:
    1. Clique no botão "Browse files" ou arraste o arquivo TXT da ECD para a área acima
    2. O sistema processará automaticamente os registros J100 e J150
    3. Os principais KPIs serão calculados e exibidos
    
    ### Sobre a ECD:
    A Escrituração Contábil Digital (ECD) é obrigatória para todas as empresas sujeitas à escrituração contábil.
    Este dashboard analisa especificamente os registros:
    - **J100**: Balancete Diário - Contas de Resultado
    - **J150**: Demonstração do Resultado do Exercício (DRE)
    """)

# Rodapé
st.markdown("---")
st.markdown("**Dashboard para análise de ECD - v1.0**")
st.markdown(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
