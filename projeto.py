import streamlit as st
import chardet
from io import BytesIO
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import numpy as np
import plotly.express as px
import base64
import time

# Configuração inicial da página
st.set_page_config(
    page_title="Sistema Fiscal HÄFELE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado com animações profissionais
st.markdown("""
<style>
    :root {
        --primary: #1e3a8a;
        --primary-light: #3b82f6;
        --secondary: #f0f2f6;
        --success: #28a745;
        --warning: #ffc107;
        --danger: #dc3545;
        --dark: #343a40;
        --light: #f8f9fa;
        --white: #ffffff;
        --gray: #6c757d;
        --transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    
    /* Estilos gerais */
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f5f7fa;
        color: #333;
    }
    
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 15px;
    }
    
    /* Header */
    .main-header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        color: var(--white);
        padding: 1.5rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        animation: fadeInDown 0.8s ease-out;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        text-align: center;
    }
    
    /* Cards */
    .card {
        background: var(--white);
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: var(--transition);
        border: none;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
    }
    
    .card-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: var(--primary);
    }
    
    /* Botões */
    .btn {
        display: inline-block;
        font-weight: 500;
        text-align: center;
        white-space: nowrap;
        vertical-align: middle;
        user-select: none;
        border: 1px solid transparent;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        line-height: 1.5;
        border-radius: 0.5rem;
        transition: var(--transition);
        cursor: pointer;
    }
    
    .btn-primary {
        color: var(--white);
        background-color: var(--primary);
        border-color: var(--primary);
    }
    
    .btn-primary:hover {
        background-color: #1d4ed8;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(30, 58, 138, 0.2);
    }
    
    .btn-lg {
        padding: 1rem 2rem;
        font-size: 1.1rem;
    }
    
    /* Menu principal */
    .menu-container {
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .menu-btn {
        flex: 1;
        max-width: 300px;
        background: var(--white);
        border-radius: 10px;
        padding: 2rem 1rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: var(--transition);
        border: 1px solid rgba(0, 0, 0, 0.1);
        cursor: pointer;
    }
    
    .menu-btn:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-light);
    }
    
    .menu-btn i {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: var(--primary);
    }
    
    .menu-btn h3 {
        margin: 0;
        font-size: 1.25rem;
        color: var(--dark);
    }
    
    .menu-btn p {
        color: var(--gray);
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    /* Animações */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.35em 0.65em;
        font-size: 0.75em;
        font-weight: 700;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: 0.5rem;
    }
    
    .badge-primary {
        color: var(--white);
        background-color: var(--primary);
    }
    
    .badge-success {
        color: var(--white);
        background-color: var(--success);
    }
    
    .badge-warning {
        color: var(--dark);
        background-color: var(--warning);
    }
    
    .badge-danger {
        color: var(--white);
        background-color: var(--danger);
    }
    
    /* Formulários */
    .form-group {
        margin-bottom: 1.5rem;
    }
    
    .form-label {
        display: block;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    
    /* Tabelas */
    .dataframe {
        width: 100%;
        border-collapse: collapse;
    }
    
    .dataframe th {
        background-color: var(--primary);
        color: var(--white);
        padding: 0.75rem;
        text-align: left;
    }
    
    .dataframe td {
        padding: 0.75rem;
        border-bottom: 1px solid #dee2e6;
    }
    
    .dataframe tr:hover {
        background-color: rgba(0, 0, 0, 0.02);
    }
    
    /* Página de boas-vindas */
    .welcome-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 60vh;
        text-align: center;
        animation: fadeIn 1s ease-in;
    }
    
    .welcome-title {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        background: linear-gradient(to right, var(--primary), var(--primary-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: pulse 2s infinite;
    }
    
    .welcome-subtitle {
        font-size: 1.25rem;
        color: var(--gray);
        max-width: 700px;
        margin-bottom: 2rem;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .menu-container {
            flex-direction: column;
            align-items: center;
        }
        
        .menu-btn {
            max-width: 100%;
            width: 100%;
        }
        
        .welcome-title {
            font-size: 2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# =============================================
# COMPONENTES REUTILIZÁVEIS
# =============================================

def show_header(title):
    st.markdown(f"""
    <div class="main-header">
        <div class="container">
            <h1>{title}</h1>
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_menu():
    st.markdown("""
    <div class="menu-container">
        <div class="menu-btn" onclick="window.streamlitApi.runMethod('set_module', 'txt')">
            <i>📄</i>
            <h3>Processador TXT</h3>
            <p>Processe arquivos de texto removendo linhas indesejadas</p>
        </div>
        
        <div class="menu-btn" onclick="window.streamlitApi.runMethod('set_module', 'reinf')">
            <i>📊</i>
            <h3>EFD REINF</h3>
            <p>Lançamentos fiscais e geração de arquivos</p>
        </div>
        
        <div class="menu-btn" onclick="window.streamlitApi.runMethod('set_module', 'atividades')">
            <i>📅</i>
            <h3>Atividades Fiscais</h3>
            <p>Controle de obrigações e prazos fiscais</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # JavaScript para comunicação com Streamlit
    st.markdown("""
    <script>
    function set_module(module) {
        window.streamlitApi.runMethod('set_current_module', module);
    }
    </script>
    """, unsafe_allow_html=True)

# =============================================
# PÁGINA INICIAL
# =============================================

def home_page():
    st.markdown("""
    <div class="welcome-container">
        <h1 class="welcome-title">Sistema Fiscal HÄFELE</h1>
        <p class="welcome-subtitle">
            Solução completa para gestão de processos fiscais, com ferramentas especializadas
            para otimizar seu fluxo de trabalho e garantir conformidade com as obrigações legais.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    show_menu()

# =============================================
# MÓDULO: PROCESSADOR DE ARQUIVOS TXT
# =============================================

def txt_processor():
    show_header("📄 Processador de Arquivos TXT")
    
    st.markdown("""
    <div class="card">
        <div class="card-title">Processamento de Arquivos Texto</div>
        <p>Remova linhas indesejadas de arquivos TXT e realize substituições automáticas.</p>
    </div>
    """, unsafe_allow_html=True)

    def detect_encoding(content):
        result = chardet.detect(content)
        return result['encoding']

    def process_file(content, patterns):
        try:
            substitutions = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN"
            }
            
            encoding = detect_encoding(content)
            
            try:
                text = content.decode(encoding)
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            
            lines = text.splitlines()
            processed_lines = []
            
            for line in lines:
                line = line.strip()
                if not any(pattern in line for pattern in patterns):
                    for original, substitute in substitutions.items():
                        line = line.replace(original, substitute)
                    processed_lines.append(line)
            
            return "\n".join(processed_lines), len(lines)
        
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            return None, 0

    # Configurações padrão
    default_patterns = ["-------", "SPED EFD-ICMS/IPI"]
    
    # Upload do arquivo
    uploaded_file = st.file_uploader("Selecione o arquivo TXT", type=['txt'])
    
    # Opções avançadas
    with st.expander("⚙️ Configurações Avançadas", expanded=False):
        additional_patterns = st.text_input(
            "Padrões adicionais para remoção (separados por vírgula)",
            help="Exemplo: padrão1, padrão2, padrão3"
        )
        
        patterns = default_patterns + [
            p.strip() for p in additional_patterns.split(",") 
            if p.strip()
        ] if additional_patterns else default_patterns

    if uploaded_file is not None:
        try:
            # Processa o arquivo
            file_content = uploaded_file.read()
            result, total_lines = process_file(file_content, patterns)
            
            if result is not None:
                # Mostra estatísticas
                processed_lines = len(result.splitlines())
                st.success(f"""
                **Processamento concluído com sucesso!**  
                ✔️ Linhas originais: {total_lines}  
                ✔️ Linhas processadas: {processed_lines}  
                ✔️ Linhas removidas: {total_lines - processed_lines}
                """)

                # Prévia do resultado
                st.subheader("Prévia do Resultado")
                st.text_area("Conteúdo processado", result, height=300, key="preview_area")

                # Botão de download
                buffer = BytesIO()
                buffer.write(result.encode('utf-8'))
                buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Baixar arquivo processado",
                    data=buffer,
                    file_name=f"processado_{uploaded_file.name}",
                    mime="text/plain",
                    key="download_btn"
                )
        
        except Exception as e:
            st.error(f"Erro inesperado: {str(e)}")
            st.info("Verifique o arquivo e tente novamente.")

# =============================================
# MÓDULO: LANÇAMENTOS EFD REINF
# =============================================

def reinf_module():
    show_header("📊 Lançamentos EFD REINF")
    
    st.markdown("""
    <div class="card">
        <div class="card-title">Sistema de Lançamentos Fiscais</div>
        <p>Cadastro de notas fiscais de serviço tomados e geração de arquivos R2010 e R4020.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Conexão com o banco de dados
    conn = sqlite3.connect('fiscal_hefele.db')
    c = conn.cursor()
    
    # Criar tabela se não existir
    c.execute('''
        CREATE TABLE IF NOT EXISTS notas_fiscais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            cnpj_tomador TEXT,
            cnpj_prestador TEXT,
            valor_servico REAL,
            descricao_servico TEXT,
            codigo_servico TEXT,
            aliquota_inss REAL,
            valor_inss REAL,
            retem_irrf INTEGER,
            aliquota_irrf REAL,
            valor_irrf REAL,
            retem_pis INTEGER,
            aliquota_pis REAL,
            valor_pis REAL,
            retem_cofins INTEGER,
            aliquota_cofins REAL,
            valor_cofins REAL,
            retem_csll INTEGER,
            aliquota_csll REAL,
            valor_csll REAL
        )
    ''')
    conn.commit()
    
    # Carregar dados existentes
    df_notes = pd.read_sql_query("SELECT * FROM notas_fiscais", conn)
    
    # Formulário para nova nota fiscal
    with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("Data da Nota Fiscal")
            cnpj_taker = st.text_input("CNPJ Tomador (14 dígitos)", max_chars=14)
            cnpj_provider = st.text_input("CNPJ Prestador (14 dígitos)", max_chars=14)
            service_value = st.number_input("Valor do Serviço (R$)", min_value=0.0, format="%.2f")
            service_description = st.text_input("Descrição do Serviço")
            service_code = st.text_input("Código do Serviço (LC 116)")
        
        with col2:
            st.subheader("Tributos")
            
            # INSS
            st.markdown("**INSS**")
            inss_rate = st.slider("Alíquota INSS (%)", 0.0, 100.0, 4.5, 0.01)
            inss_value = service_value * (inss_rate / 100)
            st.info(f"Valor INSS: R$ {inss_value:.2f}")
            
            # IRRF
            st.markdown("**IRRF**")
            withhold_irrf = st.checkbox("Retém IRRF?")
            irrf_rate = st.slider("Alíquota IRRF (%)", 0.0, 100.0, 1.5, 0.01, disabled=not withhold_irrf)
            irrf_value = service_value * (irrf_rate / 100) if withhold_irrf else 0.0
            st.info(f"Valor IRRF: R$ {irrf_value:.2f}")
            
            # PIS
            st.markdown("**PIS**")
            withhold_pis = st.checkbox("Retém PIS?")
            pis_rate = st.slider("Alíquota PIS (%)", 0.0, 100.0, 0.65, 0.01, disabled=not withhold_pis)
            pis_value = service_value * (pis_rate / 100) if withhold_pis else 0.0
            st.info(f"Valor PIS: R$ {pis_value:.2f}")
            
            # COFINS
            st.markdown("**COFINS**")
            withhold_cofins = st.checkbox("Retém COFINS?")
            cofins_rate = st.slider("Alíquota COFINS (%)", 0.0, 100.0, 3.0, 0.01, disabled=not withhold_cofins)
            cofins_value = service_value * (cofins_rate / 100) if withhold_cofins else 0.0
            st.info(f"Valor COFINS: R$ {cofins_value:.2f}")
            
            # CSLL
            st.markdown("**CSLL**")
            withhold_csll = st.checkbox("Retém CSLL?")
            csll_rate = st.slider("Alíquota CSLL (%)", 0.0, 100.0, 1.0, 0.01, disabled=not withhold_csll)
            csll_value = service_value * (csll_rate / 100) if withhold_csll else 0.0
            st.info(f"Valor CSLL: R$ {csll_value:.2f}")
        
        if st.button("Adicionar Nota Fiscal", key="add_note_btn"):
            c.execute('''
                INSERT INTO notas_fiscais (
                    data, cnpj_tomador, cnpj_prestador, valor_servico, descricao_servico, codigo_servico,
                    aliquota_inss, valor_inss, retem_irrf, aliquota_irrf, valor_irrf,
                    retem_pis, aliquota_pis, valor_pis, retem_cofins, aliquota_cofins, valor_cofins,
                    retem_csll, aliquota_csll, valor_csll
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date.strftime('%Y-%m-%d'), cnpj_taker, cnpj_provider, service_value, 
                service_description, service_code, inss_rate, inss_value, 
                int(withhold_irrf), irrf_rate, irrf_value, int(withhold_pis), 
                pis_rate, pis_value, int(withhold_cofins), cofins_rate, 
                cofins_value, int(withhold_csll), csll_rate, csll_value
            ))
            conn.commit()
            st.success("Nota fiscal adicionada com sucesso!")
            st.experimental_rerun()
    
    # Visualização das notas cadastradas
    st.subheader("Notas Fiscais Cadastradas")
    df_notes = pd.read_sql_query("SELECT * FROM notas_fiscais", conn)
    
    if not df_notes.empty:
        main_cols = ['data', 'cnpj_tomador', 'cnpj_prestador', 'valor_servico', 'descricao_servico', 'codigo_servico']
        st.dataframe(df_notes[main_cols])
        
        # Opções para editar/excluir
        col1, col2 = st.columns(2)
        with col1:
            edit_row = st.number_input("Número da linha para editar", 0, len(df_notes)-1, 0)
            if st.button("Editar Linha"):
                st.session_state.editing = edit_row
                
        with col2:
            delete_row = st.number_input("Número da linha para excluir", 0, len(df_notes)-1, 0)
            if st.button("Excluir Linha"):
                delete_id = df_notes.iloc[delete_row]['id']
                c.execute("DELETE FROM notas_fiscais WHERE id = ?", (delete_id,))
                conn.commit()
                st.success("Linha excluída com sucesso!")
                st.experimental_rerun()
        
        # Formulário de edição
        if 'editing' in st.session_state:
            with st.expander("✏️ Editar Nota Fiscal", expanded=True):
                note_to_edit = df_notes.iloc[st.session_state.editing]
                
                col1, col2 = st.columns(2)
                with col1:
                    edit_date = st.date_input("Data", value=datetime.strptime(note_to_edit['data'], '%Y-%m-%d'), key='edit_date')
                    edit_taker = st.text_input("CNPJ Tomador", value=note_to_edit['cnpj_tomador'], key='edit_taker')
                    edit_provider = st.text_input("CNPJ Prestador", value=note_to_edit['cnpj_prestador'], key='edit_provider')
                    edit_value = st.number_input("Valor do Serviço (R$)", value=float(note_to_edit['valor_servico']), key='edit_value')
                    edit_description = st.text_input("Descrição do Serviço", value=note_to_edit['descricao_servico'], key='edit_description')
                    edit_code = st.text_input("Código do Serviço", value=note_to_edit['codigo_servico'], key='edit_code')
                
                with col2:
                    st.subheader("Tributos")
                    
                    # INSS
                    st.markdown("**INSS**")
                    edit_inss_rate = st.slider("Alíquota INSS (%)", 0.0, 100.0, float(note_to_edit['aliquota_inss']), 0.01, key='edit_inss_rate')
                    edit_inss_value = edit_value * (edit_inss_rate / 100)
                    st.info(f"Valor INSS: R$ {edit_inss_value:.2f}")
                    
                    # IRRF
                    st.markdown("**IRRF**")
                    edit_withhold_irrf = st.checkbox("Retém IRRF?", value=bool(note_to_edit['retem_irrf']), key='edit_withhold_irrf')
                    edit_irrf_rate = st.slider("Alíquota IRRF (%)", 0.0, 100.0, float(note_to_edit['aliquota_irrf']), 0.01, disabled=not edit_withhold_irrf, key='edit_irrf_rate')
                    edit_irrf_value = edit_value * (edit_irrf_rate / 100) if edit_withhold_irrf else 0.0
                    st.info(f"Valor IRRF: R$ {edit_irrf_value:.2f}")
                    
                    # PIS
                    st.markdown("**PIS**")
                    edit_withhold_pis = st.checkbox("Retém PIS?", value=bool(note_to_edit['retem_pis']), key='edit_withhold_pis')
                    edit_pis_rate = st.slider("Alíquota PIS (%)", 0.0, 100.0, float(note_to_edit['aliquota_pis']), 0.01, disabled=not edit_withhold_pis, key='edit_pis_rate')
                    edit_pis_value = edit_value * (edit_pis_rate / 100) if edit_withhold_pis else 0.0
                    st.info(f"Valor PIS: R$ {edit_pis_value:.2f}")
                    
                    # COFINS
                    st.markdown("**COFINS**")
                    edit_withhold_cofins = st.checkbox("Retém COFINS?", value=bool(note_to_edit['retem_cofins']), key='edit_withhold_cofins')
                    edit_cofins_rate = st.slider("Alíquota COFINS (%)", 0.0, 100.0, float(note_to_edit['aliquota_cofins']), 0.01, disabled=not edit_withhold_cofins, key='edit_cofins_rate')
                    edit_cofins_value = edit_value * (edit_cofins_rate / 100) if edit_withhold_cofins else 0.0
                    st.info(f"Valor COFINS: R$ {edit_cofins_value:.2f}")
                    
                    # CSLL
                    st.markdown("**CSLL**")
                    edit_withhold_csll = st.checkbox("Retém CSLL?", value=bool(note_to_edit['retem_csll']), key='edit_withhold_csll')
                    edit_csll_rate = st.slider("Alíquota CSLL (%)", 0.0, 100.0, float(note_to_edit['aliquota_csll']), 0.01, disabled=not edit_withhold_csll, key='edit_csll_rate')
                    edit_csll_value = edit_value * (edit_csll_rate / 100) if edit_withhold_csll else 0.0
                    st.info(f"Valor CSLL: R$ {edit_csll_value:.2f}")
                
                if st.button("Salvar Alterações"):
                    c.execute('''
                        UPDATE notas_fiscais SET
                            data = ?, cnpj_tomador = ?, cnpj_prestador = ?, valor_servico = ?,
                            descricao_servico = ?, codigo_servico = ?, aliquota_inss = ?,
                            valor_inss = ?, retem_irrf = ?, aliquota_irrf = ?, valor_irrf = ?,
                            retem_pis = ?, aliquota_pis = ?, valor_pis = ?, retem_cofins = ?,
                            aliquota_cofins = ?, valor_cofins = ?, retem_csll = ?,
                            aliquota_csll = ?, valor_csll = ?
                        WHERE id = ?
                    ''', (
                        edit_date.strftime('%Y-%m-%d'), edit_taker, edit_provider, edit_value,
                        edit_description, edit_code, edit_inss_rate, edit_inss_value, 
                        int(edit_withhold_irrf), edit_irrf_rate, edit_irrf_value,
                        int(edit_withhold_pis), edit_pis_rate, edit_pis_value, 
                        int(edit_withhold_cofins), edit_cofins_rate, edit_cofins_value,
                        int(edit_withhold_csll), edit_csll_rate, edit_csll_value, 
                        note_to_edit['id']
                    ))
                    conn.commit()
                    del st.session_state.editing
                    st.success("Alterações salvas com sucesso!")
                    st.experimental_rerun()
    else:
        st.warning("Nenhuma nota fiscal cadastrada ainda.")
    
    # Geração do arquivo EFD REINF
    st.subheader("Gerar Arquivo EFD REINF")
    
    if st.button("🔄 Gerar Arquivo para Entrega (R2010 e R4020)", key="generate_file_btn"):
        if df_notes.empty:
            st.error("Nenhuma nota fiscal cadastrada para gerar o arquivo.")
        else:
            # Simulação da geração do arquivo
            generation_date = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"EFD_REINF_{generation_date}.txt"
            
            # Cabeçalho do arquivo
            content = [
                "|EFDREINF|0100|1|",
                "|0001|1|12345678901234|Empresa Teste|12345678|||A|12345678901|email@empresa.com|",
                "|0100|Fulano de Tal|12345678901|Rua Teste, 123|3100000||99999999|email@contador.com|"
            ]
            
            # Adiciona registros R2010
            for idx, note in df_notes.iterrows():
                content.append(f"|2010|{idx+1}|{note['cnpj_tomador']}|{note['cnpj_prestador']}|{note['data'].replace('-', '')}|{note['codigo_servico']}|{note['valor_servico']:.2f}|{note['aliquota_inss']:.2f}|{note['valor_inss']:.2f}|")
            
            # Adiciona registros R4020
            total_inss = df_notes['valor_inss'].sum()
            total_irrf = df_notes['valor_irrf'].sum()
            total_pis = df_notes['valor_pis'].sum()
            total_cofins = df_notes['valor_cofins'].sum()
            total_csll = df_notes['valor_csll'].sum()
            
            content.append(f"|4020|1|{datetime.now().strftime('%Y%m')}|{total_inss:.2f}|{total_irrf:.2f}|{total_pis:.2f}|{total_cofins:.2f}|{total_csll:.2f}|1|")
            
            # Rodapé do arquivo
            content.append("|9001|1|")
            content.append(f"|9900|EFDREINF|{len(content) - 3}|")
            content.append("|9999|7|")
            
            final_file = "\n".join(content)
            
            # Cria o botão de download
            b64 = base64.b64encode(final_file.encode('utf-8')).decode()
            href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">⬇️ Baixar Arquivo EFD REINF</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            st.success("Arquivo gerado com sucesso!")
            
            # Resumo dos totais
            st.subheader("Resumo dos Tributos")
            cols = st.columns(5)
            cols[0].metric("Total INSS", f"R$ {total_inss:.2f}")
            cols[1].metric("Total IRRF", f"R$ {total_irrf:.2f}")
            cols[2].metric("Total PIS", f"R$ {total_pis:.2f}")
            cols[3].metric("Total COFINS", f"R$ {total_cofins:.2f}")
            cols[4].metric("Total CSLL", f"R$ {total_csll:.2f}")
            
            # Prévia do arquivo
            st.subheader("Prévia do Arquivo")
            st.text_area("Conteúdo do Arquivo", final_file, height=300, key="file_preview")
    
    conn.close()

# =============================================
# MÓDULO: ATIVIDADES FISCAIS
# =============================================

def fiscal_activities():
    show_header("📅 Atividades Fiscais")
    
    st.markdown("""
    <div class="card">
        <div class="card-title">Controle de Atividades Fiscais</div>
        <p>Gerencie todas as obrigações fiscais da empresa com acompanhamento de prazos e status.</p>
    </div>
    """, unsafe_allow_html=True)

    # Conexão com o banco de dados
    DATABASE = 'fiscal_activities.db'

    def create_connection():
        try:
            conn = sqlite3.connect(DATABASE)
            return conn
        except sqlite3.Error as e:
            st.error(f"Erro ao conectar ao banco de dados: {e}")
            return None

    def create_table():
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS atividades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        Obrigacao TEXT NOT NULL,
                        Descricao TEXT,
                        Periodicidade TEXT,
                        OrgaoResponsavel TEXT,
                        DataLimite TEXT,
                        Status TEXT,
                        Dificuldade TEXT,
                        Prazo TEXT,
                        DataInicio TEXT,
                        DataConclusao TEXT,
                        MesAnoReferencia TEXT NOT NULL
                    )
                """)
                conn.commit()
            except sqlite3.Error as e:
                st.error(f"Erro ao criar tabela: {e}")
            finally:
                conn.close()

    def load_data(month_year):
        conn = create_connection()
        df = pd.DataFrame()
        if conn is not None:
            try:
                query = "SELECT * FROM atividades WHERE MesAnoReferencia = ?"
                df = pd.read_sql_query(query, conn, params=(month_year,))
                
                date_cols = ['Prazo', 'DataInicio', 'DataConclusao']
                for col in date_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    else:
                        df[col] = pd.NaT
            except sqlite3.Error as e:
                st.error(f"Erro ao carregar dados: {e}")
            finally:
                conn.close()
        return df

    def update_activity(activity_id, updates):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                values = list(updates.values())
                values.append(activity_id)
                
                query = f"UPDATE atividades SET {set_clause} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
                return True
            except sqlite3.Error as e:
                st.error(f"Erro ao atualizar atividade: {e}")
                return False
            finally:
                conn.close()
        return False

    def add_activity(activity):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO atividades (
                        Obrigacao, Descricao, Periodicidade, OrgaoResponsavel, DataLimite,
                        Status, Dificuldade, Prazo, DataInicio, DataConclusao, MesAnoReferencia
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    activity['Obrigação'], activity['Descrição'], activity['Periodicidade'],
                    activity['Órgão Responsável'], activity['Data Limite'], activity['Status'],
                    activity['Dificuldade'], activity['Prazo'], activity['Data Início'],
                    activity['Data Conclusão'], activity['MesAnoReferencia']
                ))
                conn.commit()
                return True
            except sqlite3.Error as e:
                st.error(f"Erro ao adicionar atividade: {e}")
                return False
            finally:
                conn.close()
        return False

    def get_template_data():
        return [
            {
                "Obrigação": "Sped Fiscal",
                "Descrição": "Entrega do arquivo digital da EFD ICMS/IPI",
                "Periodicidade": "Mensal",
                "Órgão Responsável": "SEFAZ-PR",
                "Data Limite": "Até o dia 10 do mês subsequente",
                "Status": "Pendente",
                "Dificuldade": "Média",
                "Prazo": None,
                "Data Início": None,
                "Data Conclusão": None,
                "MesAnoReferencia": None
            },
            {
                "Obrigação": "DCTF",
                "Descrição": "Declaração de Débitos e Créditos Tributários Federais",
                "Periodicidade": "Mensal",
                "Órgão Responsável": "RFB",
                "Data Limite": "Até o dia 15 do mês subsequente",
                "Status": "Pendente",
                "Dificuldade": "Alta",
                "Prazo": None,
                "Data Início": None,
                "Data Conclusão": None,
                "MesAnoReferencia": None
            },
            {
                "Obrigação": "EFD Contribuições",
                "Descrição": "Escrituração Fiscal Digital de Contribuições",
                "Periodicidade": "Mensal",
                "Órgão Responsável": "RFB",
                "Data Limite": "Até o dia 15 do mês subsequente",
                "Status": "Pendente",
                "Dificuldade": "Média",
                "Prazo": None,
                "Data Início": None,
                "Data Conclusão": None,
                "MesAnoReferencia": None
            }
        ]

    def next_month(current_month_year):
        month, year = map(int, current_month_year.split('/'))
        return f"{str(month + 1).zfill(2)}/{year + 1}" if month == 12 else f"{str(month + 1).zfill(2)}/{year}"

    def prev_month(current_month_year):
        month, year = map(int, current_month_year.split('/'))
        return f"12/{year - 1}" if month == 1 else f"{str(month - 1).zfill(2)}/{year}"

    def calculate_deadline(deadline_text, month_year):
        month, year = map(int, month_year.split('/'))
        
        if "dia 10 do mês subsequente" in deadline_text:
            date = datetime(year, month, 1) + pd.DateOffset(months=1)
            return date.replace(day=10)
        elif "dia 15 do mês subsequente" in deadline_text:
            date = datetime(year, month, 1) + pd.DateOffset(months=1)
            return date.replace(day=15)
        return datetime(year, month, 1) + timedelta(days=90)

    def style_status(status):
        if status == "Pendente":
            return '<span class="badge badge-warning">Pendente</span>'
        elif status == "Em Andamento":
            return '<span class="badge badge-primary">Em Andamento</span>'
        elif status == "Finalizado":
            return '<span class="badge badge-success">Finalizado</span>'
        elif status == "Fechado":
            return '<span class="badge badge-secondary">Fechado</span>'
        return f'<span class="badge">{status}</span>'

    def style_difficulty(difficulty):
        if difficulty == "Baixa":
            return '<span class="badge badge-success">Baixa</span>'
        elif difficulty == "Média":
            return '<span class="badge badge-warning">Média</span>'
        elif difficulty == "Alta":
            return '<span class="badge badge-danger">Alta</span>'
        return f'<span class="badge">{difficulty}</span>'

    def days_remaining(row):
        today = datetime.now()
        if pd.isna(row['Prazo']) or row['Status'] in ['Finalizado', 'Fechado']:
            return None
        deadline = row['Prazo']
        days = (deadline - today).days
        return days if days >= 0 else 0

    # Inicialização
    if 'month_year' not in st.session_state:
        st.session_state.month_year = datetime.now().strftime('%m/%Y')
    
    if 'df_activities' not in st.session_state:
        st.session_state.df_activities = load_data(st.session_state.month_year)

    create_table()

    # Habilitar mês se não houver dados
    if st.session_state.df_activities.empty:
        st.warning(f"Nenhuma atividade cadastrada para {st.session_state.month_year}.")
        if st.button(f"🔄 Habilitar Mês {st.session_state.month_year}"):
            activities = get_template_data()
            for activity in activities:
                deadline = calculate_deadline(activity['Data Limite'], st.session_state.month_year)
                activity.update({
                    'Prazo': deadline.strftime('%Y-%m-%d %H:%M:%S') if deadline else None,
                    'MesAnoReferencia': st.session_state.month_year,
                    'Data Início': None,
                    'Data Conclusão': None
                })
            
            conn = create_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    for activity in activities:
                        cursor.execute("""
                            INSERT INTO atividades (
                                Obrigacao, Descricao, Periodicidade, OrgaoResponsavel, DataLimite,
                                Status, Dificuldade, Prazo, DataInicio, DataConclusao, MesAnoReferencia
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            activity['Obrigação'], activity['Descrição'], activity['Periodicidade'],
                            activity['Órgão Responsável'], activity['Data Limite'], activity['Status'],
                            activity['Dificuldade'], activity['Prazo'], activity['Data Início'],
                            activity['Data Conclusão'], activity['MesAnoReferencia']
                        ))
                    conn.commit()
                except sqlite3.Error as e:
                    st.error(f"Erro ao inserir atividades: {e}")
                finally:
                    conn.close()
            
            st.session_state.df_activities = load_data(st.session_state.month_year)
            st.success("Atividades habilitadas com sucesso!")
            st.rerun()

    # Navegação entre meses
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️ Mês Anterior"):
            st.session_state.month_year = prev_month(st.session_state.month_year)
            st.session_state.df_activities = load_data(st.session_state.month_year)
            st.rerun()
    
    with col2:
        st.markdown(f"<h2 style='text-align: center;'>Mês/Ano: {st.session_state.month_year}</h2>", unsafe_allow_html=True)
    
    with col3:
        if st.button("Próximo Mês ▶️"):
            st.session_state.month_year = next_month(st.session_state.month_year)
            st.session_state.df_activities = load_data(st.session_state.month_year)
            st.rerun()

    # Métricas
    cols = st.columns(5)
    metrics = [
        ("Total", ""),
        ("Pendentes", "Pendente"),
        ("Em Andamento", "Em Andamento"),
        ("Finalizadas", "Finalizado"),
        ("Fechadas", "Fechado")
    ]
    
    for (label, status), col in zip(metrics, cols):
        count = len(st.session_state.df_activities[st.session_state.df_activities['Status'] == status]) if status else len(st.session_state.df_activities)
        col.metric(label, count)

    # Gráficos
    st.markdown("---")
    st.markdown('<div class="card"><h3>📊 Análise Gráfica</h3></div>', unsafe_allow_html=True)
    
    if not st.session_state.df_activities.empty:
        tab1, tab2, tab3 = st.tabs(["Status", "Dificuldade", "Prazos"])
        
        with tab1:
            status_counts = st.session_state.df_activities['Status'].value_counts().reset_index()
            fig_status = px.pie(
                status_counts, 
                values='count', 
                names='Status',
                title='Distribuição por Status',
                color='Status',
                color_discrete_map={
                    'Pendente': '#ffc107',
                    'Em Andamento': '#007bff',
                    'Finalizado': '#28a745',
                    'Fechado': '#6c757d'
                }
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        with tab2:
            difficulty_counts = st.session_state.df_activities['Dificuldade'].value_counts().reset_index()
            fig_diff = px.bar(
                difficulty_counts,
                x='Dificuldade',
                y='count',
                title='Distribuição por Dificuldade',
                color='Dificuldade',
                color_discrete_map={
                    'Baixa': '#28a745',
                    'Média': '#ffc107',
                    'Alta': '#dc3545'
                }
            )
            st.plotly_chart(fig_diff, use_container_width=True)
        
        with tab3:
            deadline_df = st.session_state.df_activities.dropna(subset=['Prazo'])
            if not deadline_df.empty:
                deadline_df['PrazoFmt'] = deadline_df['Prazo'].dt.strftime('%d/%m/%Y')
                deadline_df['InicioVisual'] = deadline_df['DataInicio'].fillna(deadline_df['Prazo'] - timedelta(days=1))
                
                fig_deadline = px.timeline(
                    deadline_df,
                    x_start="InicioVisual",
                    x_end="Prazo",
                    y="Obrigacao",
                    color="Status",
                    title='Linha do Tempo das Atividades',
                    color_discrete_map={
                        'Pendente': '#ffc107',
                        'Em Andamento': '#007bff',
                        'Finalizado': '#28a745',
                        'Fechado': '#6c757d'
                    },
                    hover_name="Obrigacao",
                    hover_data={
                        "Status": True,
                        "Dificuldade": True,
                        "PrazoFmt": True,
                        "InicioVisual": False
                    }
                )
                fig_deadline.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_deadline, use_container_width=True)
            else:
                st.info("Nenhuma atividade com prazo definido.")
    else:
        st.info("Adicione atividades para ver análises gráficas.")

    # Tabela de atividades
    st.markdown("---")
    st.markdown('<div class="card"><h3>📋 Lista de Atividades</h3></div>', unsafe_allow_html=True)

    if st.session_state.df_activities.empty:
        st.info("Nenhuma atividade encontrada.")
    else:
        with st.expander("🔍 Filtros", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.selectbox("Status", ["Todos", "Pendente", "Em Andamento", "Finalizado", "Fechado"])
            with col2:
                difficulty_filter = st.selectbox("Dificuldade", ["Todos", "Baixa", "Média", "Alta"])
            with col3:
                org_options = ["Todos"] + list(st.session_state.df_activities['OrgaoResponsavel'].unique())
                org_filter = st.selectbox("Órgão Responsável", org_options)

        filtered_df = st.session_state.df_activities.copy()
        
        if status_filter != "Todos":
            filtered_df = filtered_df[filtered_df['Status'] == status_filter]
        if difficulty_filter != "Todos":
            filtered_df = filtered_df[filtered_df['Dificuldade'] == difficulty_filter]
        if org_filter != "Todos":
            filtered_df = filtered_df[filtered_df['OrgaoResponsavel'] == org_filter]
        
        filtered_df['DiasRestantes'] = filtered_df.apply(days_remaining, axis=1)

        display_df = filtered_df.copy()
        display_df['Status'] = display_df['Status'].apply(style_status)
        display_df['Dificuldade'] = display_df['Dificuldade'].apply(style_difficulty)
        
        for col in ['Prazo', 'DataInicio', 'DataConclusao']:
            display_df[col] = display_df[col].dt.strftime('%d/%m/%Y').replace({pd.NaT: ''})

        cols_to_show = [
            'Obrigacao', 'Descricao', 'Periodicidade', 'OrgaoResponsavel',
            'DataLimite', 'Status', 'Dificuldade', 'Prazo', 'DiasRestantes'
        ]
        
        st.write(display_df[cols_to_show].to_html(escape=False, index=False), unsafe_allow_html=True)

    # Adicionar nova atividade
    st.markdown("---")
    with st.expander("➕ Adicionar Nova Atividade", expanded=False):
        with st.form("new_activity_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                obligation = st.text_input("Obrigação*", placeholder="Nome da obrigação")
                description = st.text_area("Descrição*", placeholder="Descrição detalhada")
                frequency = st.selectbox("Periodicidade*", ["Mensal", "Trimestral", "Anual", "Eventual"])
            with col2:
                org = st.text_input("Órgão Responsável*", placeholder="Órgão responsável")
                deadline_text = st.text_input("Data Limite*", placeholder="Ex: Até o dia 10 do mês subsequente")
                status = st.selectbox("Status*", ["Pendente", "Em Andamento", "Finalizado", "Fechado"])
                difficulty = st.selectbox("Dificuldade*", ["Baixa", "Média", "Alta"])
                deadline = st.date_input("Prazo Final*")

            if st.form_submit_button("Adicionar Atividade"):
                if obligation and description and org and deadline_text and deadline:
                    calculated_deadline = calculate_deadline(deadline_text, st.session_state.month_year)
                    
                    new_activity = {
                        "Obrigação": obligation,
                        "Descrição": description,
                        "Periodicidade": frequency,
                        "Órgão Responsável": org,
                        "Data Limite": deadline_text,
                        "Status": status,
                        "Dificuldade": difficulty,
                        "Prazo": calculated_deadline.strftime('%Y-%m-%d %H:%M:%S') if calculated_deadline else None,
                        "Data Início": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == "Em Andamento" else None,
                        "Data Conclusão": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == "Finalizado" else None,
                        "MesAnoReferencia": st.session_state.month_year
                    }

                    if add_activity(new_activity):
                        st.session_state.df_activities = load_data(st.session_state.month_year)
                        st.success("Atividade adicionada com sucesso!")
                        st.rerun()
                else:
                    st.error("Preencha todos os campos obrigatórios.")

    # Fechar período
    st.markdown("---")
    st.markdown('<div class="card"><h3>🗓️ Fechamento de Período</h3></div>', unsafe_allow_html=True)

    if not st.session_state.df_activities.empty:
        all_finished = all(st.session_state.df_activities['Status'].isin(["Finalizado", "Fechado"]))
        
        if all_finished:
            st.success(f"✅ Todas as atividades para {st.session_state.month_year} estão concluídas!")
            
            if st.button("Fechar Período e Habilitar Próximo Mês"):
                conn = create_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE atividades
                            SET Status = 'Fechado'
                            WHERE MesAnoReferencia = ?
                        """, (st.session_state.month_year,))
                        conn.commit()
                    except sqlite3.Error as e:
                        st.error(f"Erro ao fechar período: {e}")
                    finally:
                        conn.close()

                st.session_state.month_year = next_month(st.session_state.month_year)
                st.session_state.df_activities = load_data(st.session_state.month_year)

                if st.session_state.df_activities.empty:
                    activities = get_template_data()
                    for activity in activities:
                        deadline = calculate_deadline(activity['Data Limite'], st.session_state.month_year)
                        activity.update({
                            'Prazo': deadline.strftime('%Y-%m-%d %H:%M:%S') if deadline else None,
                            'MesAnoReferencia': st.session_state.month_year,
                            'Data Início': None,
                            'Data Conclusão': None
                        })
                    
                    conn = create_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            for activity in activities:
                                cursor.execute("""
                                    INSERT INTO atividades (
                                        Obrigacao, Descricao, Periodicidade, OrgaoResponsavel, DataLimite,
                                        Status, Dificuldade, Prazo, DataInicio, DataConclusao, MesAnoReferencia
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    activity['Obrigação'], activity['Descrição'], activity['Periodicidade'],
                                    activity['Órgão Responsável'], activity['Data Limite'], activity['Status'],
                                    activity['Dificuldade'], activity['Prazo'], activity['Data Início'],
                                    activity['Data Conclusão'], activity['MesAnoReferencia']
                                ))
                            conn.commit()
                        except sqlite3.Error as e:
                            st.error(f"Erro ao inserir atividades: {e}")
                        finally:
                            conn.close()
                    
                    st.session_state.df_activities = load_data(st.session_state.month_year)
                    st.success("Novas atividades habilitadas!")
                
                st.rerun()
        else:
            st.warning(f"Ainda há atividades pendentes para {st.session_state.month_year}.")

# =============================================
# FUNÇÃO PRINCIPAL
# =============================================

def main():
    # Inicializa o estado da sessão
    if 'current_module' not in st.session_state:
        st.session_state.current_module = None
    
    # Mostra a página inicial ou o módulo selecionado
    if st.session_state.current_module is None:
        home_page()
    else:
        # Botão para voltar à página inicial
        if st.button("🏠 Voltar ao Início"):
            st.session_state.current_module = None
            st.rerun()
        
        # Mostra o módulo selecionado
        if st.session_state.current_module == "txt":
            txt_processor()
        elif st.session_state.current_module == "reinf":
            reinf_module()
        elif st.session_state.current_module == "atividades":
            fiscal_activities()

# JavaScript para comunicação com Streamlit
st.markdown("""
<script>
// Função para definir o módulo atual via Streamlit
function set_current_module(module) {
    const data = {module: module};
    window.parent.postMessage({
        type: 'streamlit:setComponentValue',
        apikey: 'set_module',
        data: data,
    }, '*');
}

// Captura mensagens do Streamlit
window.addEventListener('message', function(event) {
    if (event.data.type === 'streamlit:setComponentValue') {
        if (event.data.apikey === 'set_module') {
            set_current_module(event.data.data.module);
        }
    }
});
</script>
""", unsafe_allow_html=True)

# Verifica se houve mudança de módulo via JavaScript
if 'module' in st.session_state:
    st.session_state.current_module = st.session_state.module
    del st.session_state.module
    st.rerun()

if __name__ == "__main__":
    main()
