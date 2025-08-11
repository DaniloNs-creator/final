import streamlit as st
import chardet
from io import BytesIO
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import numpy as np
import plotly.express as px
import base64
from streamlit.components.v1 import html

# =============================================
# CONFIGURAÇÃO INICIAL
# =============================================

st.set_page_config(
    page_title="Sistema Fiscal HÄFELE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================
# ESTILOS CSS
# =============================================

st.markdown("""
<style>
    :root {
        --primary-color: #1e3a8a;
        --primary-light: #3b82f6;
        --secondary-color: #f0f2f6;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
        --dark-color: #343a40;
        --light-color: #f8f9fa;
    }
    
    .header-container {
        background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
        color: white;
        padding: 2.5rem 2rem;
        border-radius: 0.75rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    .card {
        background-color: white;
        border-radius: 0.75rem;
        padding: 1.75rem;
        margin-bottom: 1.75rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-left: 4px solid var(--primary-color);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
    }
    
    .status-badge {
        padding: 0.4rem 0.8rem;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        font-weight: 600;
        display: inline-block;
        text-align: center;
        min-width: 100px;
    }
    
    .status-pendente {
        background-color: var(--warning-color);
        color: var(--dark-color);
    }
    
    .status-andamento {
        background-color: var(--primary-light);
        color: white;
    }
    
    .status-finalizado {
        background-color: var(--success-color);
        color: white;
    }
    
    .status-fechado {
        background-color: var(--light-color);
        color: var(--dark-color);
    }
    
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border-radius: 0.5rem;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
        font-weight: 600;
    }
    
    .stButton>button:hover {
        background-color: var(--primary-light);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    
    .stTextInput>div>div>input,
    .stSelectbox>div>div>select,
    .stDateInput>div>div>input,
    .stTextArea>div>div>textarea {
        border-radius: 0.5rem !important;
        border: 1px solid #e5e7eb !important;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-in;
    }
</style>
""", unsafe_allow_html=True)

# =============================================
# FUNÇÕES AUXILIARES
# =============================================

def show_notification(message, type="success"):
    """Exibe uma notificação temporária"""
    if type == "success":
        st.success(message)
    elif type == "error":
        st.error(message)
    elif type == "warning":
        st.warning(message)
    else:
        st.info(message)

def validate_cnpj(cnpj):
    """Valida se o CNPJ possui 14 dígitos numéricos"""
    return len(cnpj) == 14 and cnpj.isdigit()

# =============================================
# MÓDULO DE PROCESSAMENTO DE ARQUIVOS TXT
# =============================================

def txt_processor_module():
    st.markdown("""
    <div class="header-container fade-in">
        <h1>📄 Processador de Arquivos TXT</h1>
        <p>Ferramenta profissional para tratamento e otimização de arquivos textuais</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card fade-in">
        <h3>Instruções de Uso</h3>
        <p>Esta ferramenta permite processar arquivos TXT removendo linhas indesejadas e realizando substituições automáticas de termos técnicos.</p>
        <p><strong>Passo a passo:</strong></p>
        <ol>
            <li>Selecione o arquivo TXT para processamento</li>
            <li>Configure os padrões de remoção (opcional)</li>
            <li>Visualize o resultado e baixe o arquivo processado</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    def detect_encoding(content):
        """Detecta a codificação do arquivo"""
        result = chardet.detect(content)
        return result['encoding']

    def process_file(content, patterns):
        """Processa o conteúdo do arquivo aplicando as regras especificadas"""
        try:
            replacements = {
                "IMPOSTO IMPORTACAO": "IMP. IMPORTAÇÃO",
                "TAXA SICOMEX": "TX. SISCOMEX",
                "FRETE INTERNACIONAL": "FRETE INTERNAC.",
                "SEGURO INTERNACIONAL": "SEGURO INTERNAC."
            }
            
            encoding = detect_encoding(content)
            text = content.decode(encoding if encoding else 'latin-1')
            
            processed_lines = [
                line.strip() for line in text.splitlines()
                if not any(pattern in line for pattern in patterns)
            ]
            
            for original, replacement in replacements.items():
                processed_lines = [line.replace(original, replacement) for line in processed_lines]
            
            return "\n".join(processed_lines), len(text.splitlines())
        
        except Exception as e:
            show_notification(f"Erro durante o processamento: {str(e)}", "error")
            return None, 0

    default_patterns = ["-------", "SPED EFD-ICMS/IPI"]
    
    uploaded_file = st.file_uploader("Selecione o arquivo para processamento", type=['txt'], 
                                   help="Arquivos TXT com conteúdo fiscal ou contábil")
    
    with st.expander("🔧 Configurações Avançadas", expanded=False):
        additional_patterns = st.text_input(
            "Padrões adicionais para remoção (separados por vírgula)",
            help="Exemplo: Página 1, Total Geral, RESUMO"
        )
        
        patterns = default_patterns + [
            p.strip() for p in additional_patterns.split(",") 
            if p.strip()
        ] if additional_patterns else default_patterns

    if uploaded_file is not None:
        try:
            file_content = uploaded_file.read()
            result, original_lines = process_file(file_content, patterns)
            
            if result is not None:
                processed_lines = len(result.splitlines())
                
                st.markdown("""
                <div class="card">
                    <h4>Resultado do Processamento</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin: 1rem 0;">
                        <div style="background: #f8f9fa; padding: 1rem; border-radius: 0.5rem;">
                            <h5 style="margin: 0 0 0.5rem 0; color: var(--primary-color);">Linhas Originais</h5>
                            <p style="font-size: 1.5rem; margin: 0; font-weight: bold;">{:,}</p>
                        </div>
                        <div style="background: #f8f9fa; padding: 1rem; border-radius: 0.5rem;">
                            <h5 style="margin: 0 0 0.5rem 0; color: var(--primary-color);">Linhas Processadas</h5>
                            <p style="font-size: 1.5rem; margin: 0; font-weight: bold;">{:,}</p>
                        </div>
                        <div style="background: #f8f9fa; padding: 1rem; border-radius: 0.5rem;">
                            <h5 style="margin: 0 0 0.5rem 0; color: var(--primary-color);">Redução</h5>
                            <p style="font-size: 1.5rem; margin: 0; font-weight: bold;">{:,} ({:.1f}%)</p>
                        </div>
                    </div>
                </div>
                """.format(
                    original_lines, 
                    processed_lines, 
                    original_lines - processed_lines,
                    ((original_lines - processed_lines) / original_lines * 100) if original_lines else 0
                ), unsafe_allow_html=True)

                st.subheader("Prévia do Conteúdo Processado")
                st.text_area("Visualização", result, height=300, label_visibility="collapsed")

                output_buffer = BytesIO()
                output_buffer.write(result.encode('utf-8'))
                output_buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Baixar Arquivo Processado",
                    data=output_buffer,
                    file_name=f"processed_{uploaded_file.name}",
                    mime="text/plain",
                    help="Clique para baixar o arquivo após o processamento"
                )
        
        except Exception as e:
            show_notification(f"Erro inesperado: {str(e)}", "error")

# =============================================
# MÓDULO DE LANÇAMENTOS EFD REINF
# =============================================

def reinf_module():
    st.markdown("""
    <div class="header-container fade-in">
        <h1>📊 Sistema EFD-REINF</h1>
        <p>Gestão completa de eventos fiscais para o SPED Contribuições</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card fade-in">
        <h3>Funcionalidades Principais</h3>
        <ul>
            <li>Cadastro de notas fiscais de serviços tomados</li>
            <li>Cálculo automático de tributos (INSS, IRRF, PIS, COFINS, CSLL)</li>
            <li>Geração de arquivos para entrega (R-2010 e R-4020)</li>
            <li>Controle de prazos e obrigações acessórias</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Conexão com banco de dados
    conn = sqlite3.connect('fiscal_hefele.db')
    cursor = conn.cursor()
    
    # Criar tabela se não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notas_fiscais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            cnpj_tomador TEXT NOT NULL,
            cnpj_prestador TEXT NOT NULL,
            valor_servico REAL NOT NULL,
            descricao_servico TEXT,
            codigo_servico TEXT,
            aliquota_inss REAL DEFAULT 0,
            valor_inss REAL DEFAULT 0,
            retem_irrf INTEGER DEFAULT 0,
            aliquota_irrf REAL DEFAULT 0,
            valor_irrf REAL DEFAULT 0,
            retem_pis INTEGER DEFAULT 0,
            aliquota_pis REAL DEFAULT 0,
            valor_pis REAL DEFAULT 0,
            retem_cofins INTEGER DEFAULT 0,
            aliquota_cofins REAL DEFAULT 0,
            valor_cofins REAL DEFAULT 0,
            retem_csll INTEGER DEFAULT 0,
            aliquota_csll REAL DEFAULT 0,
            valor_csll REAL DEFAULT 0,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Formulário de cadastro
    with st.expander("➕ Cadastrar Nova Nota Fiscal", expanded=True):
        with st.form("nota_fiscal_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Dados da Nota Fiscal")
                invoice_date = st.date_input("Data de Emissão*", format="DD/MM/YYYY")
                provider_cnpj = st.text_input("CNPJ Prestador*", max_chars=14, 
                                            help="Informe o CNPJ do prestador do serviço (14 dígitos)")
                receiver_cnpj = st.text_input("CNPJ Tomador*", max_chars=14,
                                            help="Informe o CNPJ da HÄFELE como tomadora (14 dígitos)")
                service_value = st.number_input("Valor do Serviço (R$)*", min_value=0.0, format="%.2f")
                service_description = st.text_input("Descrição do Serviço")
                service_code = st.text_input("Código do Serviço (LC 116)")
            
            with col2:
                st.subheader("Tributos e Retenções")
                
                st.markdown("**INSS**")
                inss_rate = st.slider("Alíquota INSS (%)", 0.0, 100.0, 4.5, 0.01, format="%.2f%%")
                inss_value = service_value * (inss_rate / 100)
                st.info(f"Valor a reter: R$ {inss_value:,.2f}")
                
                st.markdown("**IRRF**")
                irrf_retention = st.checkbox("Submeter à retenção de IRRF?")
                irrf_rate = st.slider("Alíquota IRRF (%)", 0.0, 100.0, 1.5, 0.01, 
                                     disabled=not irrf_retention, format="%.2f%%")
                irrf_value = service_value * (irrf_rate / 100) if irrf_retention else 0.0
                st.info(f"Valor a reter: R$ {irrf_value:,.2f}")
                
                st.markdown("**PIS**")
                pis_retention = st.checkbox("Submeter à retenção de PIS?")
                pis_rate = st.slider("Alíquota PIS (%)", 0.0, 100.0, 0.65, 0.01, 
                                   disabled=not pis_retention, format="%.2f%%")
                pis_value = service_value * (pis_rate / 100) if pis_retention else 0.0
                st.info(f"Valor a reter: R$ {pis_value:,.2f}")
                
                st.markdown("**COFINS**")
                cofins_retention = st.checkbox("Submeter à retenção de COFINS?")
                cofins_rate = st.slider("Alíquota COFINS (%)", 0.0, 100.0, 3.0, 0.01, 
                                      disabled=not cofins_retention, format="%.2f%%")
                cofins_value = service_value * (cofins_rate / 100) if cofins_retention else 0.0
                st.info(f"Valor a reter: R$ {cofins_value:,.2f}")
                
                st.markdown("**CSLL**")
                csll_retention = st.checkbox("Submeter à retenção de CSLL?")
                csll_rate = st.slider("Alíquota CSLL (%)", 0.0, 100.0, 1.0, 0.01, 
                                    disabled=not csll_retention, format="%.2f%%")
                csll_value = service_value * (csll_rate / 100) if csll_retention else 0.0
                st.info(f"Valor a reter: R$ {csll_value:,.2f}")
            
            if st.form_submit_button("Cadastrar Nota Fiscal"):
                if not validate_cnpj(provider_cnpj):
                    show_notification("CNPJ do prestador inválido. Deve conter 14 dígitos.", "error")
                elif not validate_cnpj(receiver_cnpj):
                    show_notification("CNPJ do tomador inválido. Deve conter 14 dígitos.", "error")
                elif service_value <= 0:
                    show_notification("O valor do serviço deve ser maior que zero.", "error")
                else:
                    try:
                        cursor.execute('''
                            INSERT INTO notas_fiscais (
                                data, cnpj_tomador, cnpj_prestador, valor_servico, descricao_servico, codigo_servico,
                                aliquota_inss, valor_inss, retem_irrf, aliquota_irrf, valor_irrf,
                                retem_pis, aliquota_pis, valor_pis, retem_cofins, aliquota_cofins, valor_cofins,
                                retem_csll, aliquota_csll, valor_csll
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            invoice_date.strftime('%Y-%m-%d'), receiver_cnpj, provider_cnpj, service_value, 
                            service_description, service_code, inss_rate, inss_value, int(irrf_retention), 
                            irrf_rate, irrf_value, int(pis_retention), pis_rate, pis_value, 
                            int(cofins_retention), cofins_rate, cofins_value, int(csll_retention), 
                            csll_rate, csll_value
                        ))
                        conn.commit()
                        show_notification("Nota fiscal cadastrada com sucesso!", "success")
                    except Exception as e:
                        show_notification(f"Erro ao cadastrar nota: {str(e)}", "error")

    # Listagem de notas cadastradas
    st.subheader("Notas Fiscais Cadastradas")
    df_invoices = pd.read_sql_query("SELECT * FROM notas_fiscais ORDER BY data DESC", conn)
    
    if not df_invoices.empty:
        # Formatação dos dados para exibição
        df_display = df_invoices.copy()
        df_display['data'] = pd.to_datetime(df_display['data']).dt.strftime('%d/%m/%Y')
        df_display['valor_servico'] = df_display['valor_servico'].map('R$ {:,.2f}'.format)
        
        # Seleção de colunas para exibição
        display_columns = [
            'data', 'cnpj_prestador', 'cnpj_tomador', 'valor_servico',
            'descricao_servico', 'codigo_servico'
        ]
        
        st.dataframe(
            df_display[display_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "data": "Data",
                "cnpj_prestador": "CNPJ Prestador",
                "cnpj_tomador": "CNPJ Tomador",
                "valor_servico": "Valor do Serviço",
                "descricao_servico": "Descrição",
                "codigo_servico": "Código"
            }
        )
        
        # Geração do arquivo EFD-REINF
        st.subheader("Gerar Arquivo para Entrega")
        
        if st.button("🔄 Gerar Arquivo EFD-REINF"):
            try:
                # Cálculo dos totais
                totals = {
                    'inss': df_invoices['valor_inss'].sum(),
                    'irrf': df_invoices['valor_irrf'].sum(),
                    'pis': df_invoices['valor_pis'].sum(),
                    'cofins': df_invoices['valor_cofins'].sum(),
                    'csll': df_invoices['valor_csll'].sum()
                }
                
                # Criação do conteúdo do arquivo
                file_content = [
                    "|EFDREINF|0100|1|",
                    "|0001|1|12345678901234|HAFELE BRASIL|12345678|||A|12345678901|fiscal@hafele.com|",
                    "|0100|Responsável Fiscal|12345678901|Rua HÄFELE, 100|3100000||99999999|contabilidade@hafele.com|"
                ]
                
                # Adiciona registros R-2010
                for idx, row in df_invoices.iterrows():
                    file_content.append(
                        f"|2010|{idx+1}|{row['cnpj_tomador']}|{row['cnpj_prestador']}|"
                        f"{row['data'].replace('-', '')}|{row['codigo_servico']}|"
                        f"{row['valor_servico']:.2f}|{row['aliquota_inss']:.2f}|"
                        f"{row['valor_inss']:.2f}|"
                    )
                
                # Adiciona registro R-4020
                file_content.append(
                    f"|4020|1|{datetime.now().strftime('%Y%m')}|"
                    f"{totals['inss']:.2f}|{totals['irrf']:.2f}|"
                    f"{totals['pis']:.2f}|{totals['cofins']:.2f}|"
                    f"{totals['csll']:.2f}|1|"
                )
                
                # Finaliza o arquivo
                file_content.extend([
                    "|9001|1|",
                    f"|9900|EFDREINF|{len(file_content) - 3}|",
                    "|9999|7|"
                ])
                
                final_content = "\n".join(file_content)
                
                # Cria o botão de download
                st.download_button(
                    label="⬇️ Baixar Arquivo EFD-REINF",
                    data=final_content.encode('utf-8'),
                    file_name=f"EFDREINF_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
                
                # Exibe os totais
                st.markdown("""
                <div class="card">
                    <h4>Resumo de Retenções</h4>
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-top: 1rem;">
                        <div style="background: #e8f5e9; padding: 1rem; border-radius: 0.5rem;">
                            <p style="margin: 0 0 0.25rem 0; font-weight: bold; color: var(--success-color);">INSS</p>
                            <p style="margin: 0; font-size: 1.25rem;">R$ {:.2f}</p>
                        </div>
                        <div style="background: #e8f5e9; padding: 1rem; border-radius: 0.5rem;">
                            <p style="margin: 0 0 0.25rem 0; font-weight: bold; color: var(--success-color);">IRRF</p>
                            <p style="margin: 0; font-size: 1.25rem;">R$ {:.2f}</p>
                        </div>
                        <div style="background: #e8f5e9; padding: 1rem; border-radius: 0.5rem;">
                            <p style="margin: 0 0 0.25rem 0; font-weight: bold; color: var(--success-color);">PIS</p>
                            <p style="margin: 0; font-size: 1.25rem;">R$ {:.2f}</p>
                        </div>
                        <div style="background: #e8f5e9; padding: 1rem; border-radius: 0.5rem;">
                            <p style="margin: 0 0 0.25rem 0; font-weight: bold; color: var(--success-color);">COFINS</p>
                            <p style="margin: 0; font-size: 1.25rem;">R$ {:.2f}</p>
                        </div>
                        <div style="background: #e8f5e9; padding: 1rem; border-radius: 0.5rem;">
                            <p style="margin: 0 0 0.25rem 0; font-weight: bold; color: var(--success-color);">CSLL</p>
                            <p style="margin: 0; font-size: 1.25rem;">R$ {:.2f}</p>
                        </div>
                    </div>
                </div>
                """.format(
                    totals['inss'], totals['irrf'], totals['pis'], 
                    totals['cofins'], totals['csll']
                ), unsafe_allow_html=True)
                
            except Exception as e:
                show_notification(f"Erro ao gerar arquivo: {str(e)}", "error")
    else:
        st.warning("Nenhuma nota fiscal cadastrada até o momento.")
    
    conn.close()

# =============================================
# MÓDULO DE ATIVIDADES FISCAIS
# =============================================

def fiscal_activities_module():
    st.markdown("""
    <div class="header-container fade-in">
        <h1>📅 Gestão de Obrigações Fiscais</h1>
        <p>Controle completo das atividades e prazos do departamento fiscal</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.warning("""
    **Módulo em Desenvolvimento**
    
    Esta funcionalidade está sendo desenvolvida e estará disponível em breve. 
    Entre em contato com o departamento de TI para mais informações.
    """)

# =============================================
# PÁGINA INICIAL
# =============================================

def home_page():
    st.markdown("""
    <div class="header-container fade-in">
        <h1>Sistema Fiscal HÄFELE</h1>
        <p>Solução integrada para gestão de processos fiscais e contábeis</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card fade-in">
        <h2>Bem-vindo ao Sistema Fiscal</h2>
        <p>Esta plataforma foi desenvolvida para otimizar e automatizar os processos fiscais da HÄFELE Brasil, 
        garantindo conformidade com a legislação e eficiência operacional.</p>
        
        <h3 style="margin-top: 1.5rem;">Módulos Disponíveis</h3>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; margin-top: 1rem;">
            <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.75rem; text-align: center;">
                <h4 style="margin: 0 0 0.5rem 0; color: var(--primary-color);">Processador TXT</h4>
                <p style="margin: 0;">Ferramenta para tratamento de arquivos textuais</p>
            </div>
            <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.75rem; text-align: center;">
                <h4 style="margin: 0 0 0.5rem 0; color: var(--primary-color);">EFD-REINF</h4>
                <p style="margin: 0;">Gestão de eventos do SPED Contribuições</p>
            </div>
            <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.75rem; text-align: center;">
                <h4 style="margin: 0 0 0.5rem 0; color: var(--primary-color);">Obrigações Fiscais</h4>
                <p style="margin: 0;">Controle de prazos e atividades (em breve)</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Acessar Processador TXT", use_container_width=True):
            st.session_state.current_page = "txt_processor"
    
    with col2:
        if st.button("📊 Acessar EFD-REINF", use_container_width=True):
            st.session_state.current_page = "reinf"
    
    with col3:
        if st.button("📅 Acessar Obrigações", use_container_width=True):
            st.session_state.current_page = "fiscal_activities"

# =============================================
# CONTROLE PRINCIPAL
# =============================================

def main():
    # Inicializa o estado da sessão
    if 'current_page' not in st.session_state:
        st.session_state.current_page = None
    
    # Renderiza a página atual
    if st.session_state.current_page is None:
        home_page()
    else:
        # Botão de retorno
        if st.button("← Voltar ao Menu Principal"):
            st.session_state.current_page = None
            st.rerun()
        
        # Renderiza o módulo selecionado
        if st.session_state.current_page == "txt_processor":
            txt_processor_module()
        elif st.session_state.current_page == "reinf":
            reinf_module()
        elif st.session_state.current_page == "fiscal_activities":
            fiscal_activities_module()

if __name__ == "__main__":
    main()
