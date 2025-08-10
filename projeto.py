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
    initial_sidebar_state="expanded"
)

# CSS personalizado com animações profissionais
st.markdown("""
<style>
    :root {
        --primary-color: #1e3a8a;
        --secondary-color: #f0f2f6;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
        --dark-color: #343a40;
        --light-color: #f8f9fa;
    }
    
    .header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 2rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        animation: fadeInDown 0.8s ease-out;
    }
    
    .header-txt {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 2rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        animation: fadeInDown 0.8s ease-out;
    }
    
    .header-reinf {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 2rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        animation: fadeInDown 0.8s ease-out;
    }
    
    .welcome-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 70vh;
        animation: fadeIn 1.5s ease-in;
    }
    
    .welcome-message {
        font-size: 3rem;
        font-weight: 700;
        color: var(--primary-color);
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
        background: linear-gradient(to right, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: pulse 2s infinite;
    }
    
    .card {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
    }
    
    .status-badge {
        padding: 0.35rem 0.7rem;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-pendente {
        background-color: var(--warning-color);
        color: var(--dark-color);
    }
    
    .status-andamento {
        background-color: var(--primary-color);
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
    
    .dificuldade-badge {
        padding: 0.35rem 0.7rem;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .dificuldade-baixa {
        background-color: var(--success-color);
        color: white;
    }
    
    .dificuldade-media {
        background-color: var(--warning-color);
        color: var(--dark-color);
    }
    
    .dificuldade-alta {
        background-color: var(--danger-color);
        color: white;
    }
    
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
    
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #1d4ed8;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stTextInput>div>div>input {
        border-radius: 0.5rem !important;
    }
    
    .stSelectbox>div>div>select {
        border-radius: 0.5rem !important;
    }
    
    .stDateInput>div>div>input {
        border-radius: 0.5rem !important;
    }
    
    .stTextArea>div>div>textarea {
        border-radius: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================
# FUNÇÕES DO PROCESSADOR DE ARQUIVOS TXT
# =============================================

def processador_txt():
    st.markdown('<div class="header-txt"><h1>📄 Processador de Arquivos TXT</h1></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        Remova linhas indesejadas de arquivos TXT. Carregue seu arquivo e defina os padrões a serem removidos.
    </div>
    """, unsafe_allow_html=True)

    def detectar_encoding(conteudo):
        """Detecta o encoding do conteúdo do arquivo"""
        resultado = chardet.detect(conteudo)
        return resultado['encoding']

    def processar_arquivo(conteudo, padroes):
        """
        Processa o conteúdo do arquivo removendo linhas indesejadas e realizando substituições
        """
        try:
            # Dicionário de substituições
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN"
            }
            
            # Detecta o encoding
            encoding = detectar_encoding(conteudo)
            
            # Decodifica o conteúdo
            try:
                texto = conteudo.decode(encoding)
            except UnicodeDecodeError:
                texto = conteudo.decode('latin-1')
            
            # Processa as linhas
            linhas = texto.splitlines()
            linhas_processadas = []
            
            for linha in linhas:
                linha = linha.strip()
                # Verifica se a linha contém algum padrão a ser removido
                if not any(padrao in linha for padrao in padroes):
                    # Aplica as substituições
                    for original, substituto in substituicoes.items():
                        linha = linha.replace(original, substituto)
                    linhas_processadas.append(linha)
            
            return "\n".join(linhas_processadas), len(linhas)
        
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            return None, 0

    # Padrões padrão para remoção
    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
    
    # Upload do arquivo
    arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'])
    
    # Opções avançadas
    with st.expander("⚙️ Configurações avançadas", expanded=False):
        padroes_adicionais = st.text_input(
            "Padrões adicionais para remoção (separados por vírgula)",
            help="Exemplo: padrão1, padrão2, padrão3"
        )
        
        padroes = padroes_default + [
            p.strip() for p in padroes_adicionais.split(",") 
            if p.strip()
        ] if padroes_adicionais else padroes_default

    if arquivo is not None:
        try:
            # Lê o conteúdo do arquivo
            conteudo = arquivo.read()
            
            # Processa o arquivo
            resultado, total_linhas = processar_arquivo(conteudo, padroes)
            
            if resultado is not None:
                # Mostra estatísticas
                linhas_processadas = len(resultado.splitlines())
                st.success(f"""
                **Processamento concluído!**  
                ✔️ Linhas originais: {total_linhas}  
                ✔️ Linhas processadas: {linhas_processadas}  
                ✔️ Linhas removidas: {total_linhas - linhas_processadas}
                """)

                # Prévia do resultado
                st.subheader("Prévia do resultado")
                st.text_area("Conteúdo processado", resultado, height=300)

                # Botão de download
                buffer = BytesIO()
                buffer.write(resultado.encode('utf-8'))
                buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Baixar arquivo processado",
                    data=buffer,
                    file_name=f"processado_{arquivo.name}",
                    mime="text/plain"
                )
        
        except Exception as e:
            st.error(f"Erro inesperado: {str(e)}")
            st.info("Tente novamente ou verifique o arquivo.")

# =============================================
# FUNÇÕES DE LANÇAMENTOS EFD REINF
# =============================================

def lancamentos_efd_reinf():
    st.markdown('<div class="header-reinf"><h1>📊 Lançamentos EFD REINF</h1></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        Sistema para lançamento de notas fiscais de serviço tomados e geração de arquivos R2010 e R4020 (com IRRF, PIS, COFINS e CSLL).
    </div>
    """, unsafe_allow_html=True)
    
    # Conexão com o banco de dados SQLite
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
    df_notas = pd.read_sql_query("SELECT * FROM notas_fiscais", conn)
    
    # Formulário para adicionar nova nota fiscal
    with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data da Nota Fiscal")
            cnpj_tomador = st.text_input("CNPJ Tomador (14 dígitos)", max_chars=14)
            cnpj_prestador = st.text_input("CNPJ Prestador (14 dígitos)", max_chars=14)
            valor_servico = st.number_input("Valor do Serviço (R$)", min_value=0.0, format="%.2f")
            descricao_servico = st.text_input("Descrição do Serviço")
            codigo_servico = st.text_input("Código do Serviço (LC 116)")
        
        with col2:
            st.subheader("Tributos")
            
            # INSS
            st.markdown("**INSS**")
            aliquota_inss = st.slider("Alíquota INSS (%)", min_value=0.0, max_value=100.0, step=0.01, value=4.5, key='aliquota_inss')
            valor_inss = valor_servico * (aliquota_inss / 100)
            st.info(f"Valor INSS: R$ {valor_inss:.2f}")
            
            # IRRF
            st.markdown("**IRRF**")
            retem_irrf = st.checkbox("Retém IRRF?", value=False, key='retem_irrf')
            aliquota_irrf = st.slider("Alíquota IRRF (%)", min_value=0.0, max_value=100.0, step=0.01, value=1.5, key='aliquota_irrf', disabled=not retem_irrf)
            valor_irrf = valor_servico * (aliquota_irrf / 100) if retem_irrf else 0.0
            st.info(f"Valor IRRF: R$ {valor_irrf:.2f}")
            
            # PIS
            st.markdown("**PIS**")
            retem_pis = st.checkbox("Retém PIS?", value=False, key='retem_pis')
            aliquota_pis = st.slider("Alíquota PIS (%)", min_value=0.0, max_value=100.0, step=0.01, value=0.65, key='aliquota_pis', disabled=not retem_pis)
            valor_pis = valor_servico * (aliquota_pis / 100) if retem_pis else 0.0
            st.info(f"Valor PIS: R$ {valor_pis:.2f}")
            
            # COFINS
            st.markdown("**COFINS**")
            retem_cofins = st.checkbox("Retém COFINS?", value=False, key='retem_cofins')
            aliquota_cofins = st.slider("Alíquota COFINS (%)", min_value=0.0, max_value=100.0, step=0.01, value=3.0, key='aliquota_cofins', disabled=not retem_cofins)
            valor_cofins = valor_servico * (aliquota_cofins / 100) if retem_cofins else 0.0
            st.info(f"Valor COFINS: R$ {valor_cofins:.2f}")
            
            # CSLL
            st.markdown("**CSLL**")
            retem_csll = st.checkbox("Retém CSLL?", value=False, key='retem_csll')
            aliquota_csll = st.slider("Alíquota CSLL (%)", min_value=0.0, max_value=100.0, step=0.01, value=1.0, key='aliquota_csll', disabled=not retem_csll)
            valor_csll = valor_servico * (aliquota_csll / 100) if retem_csll else 0.0
            st.info(f"Valor CSLL: R$ {valor_csll:.2f}")
        
        if st.button("Adicionar Nota Fiscal"):
            # Inserir no banco de dados
            c.execute('''
                INSERT INTO notas_fiscais (
                    data, cnpj_tomador, cnpj_prestador, valor_servico, descricao_servico, codigo_servico,
                    aliquota_inss, valor_inss, retem_irrf, aliquota_irrf, valor_irrf,
                    retem_pis, aliquota_pis, valor_pis, retem_cofins, aliquota_cofins, valor_cofins,
                    retem_csll, aliquota_csll, valor_csll
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.strftime('%Y-%m-%d'), cnpj_tomador, cnpj_prestador, valor_servico, descricao_servico, codigo_servico,
                aliquota_inss, valor_inss, int(retem_irrf), aliquota_irrf, valor_irrf,
                int(retem_pis), aliquota_pis, valor_pis, int(retem_cofins), aliquota_cofins, valor_cofins,
                int(retem_csll), aliquota_csll, valor_csll
            ))
            conn.commit()
            st.success("Nota fiscal adicionada com sucesso!")
            st.experimental_rerun()
    
    # Visualização das notas fiscais cadastradas
    st.subheader("Notas Fiscais Cadastradas")
    df_notas = pd.read_sql_query("SELECT * FROM notas_fiscais", conn)
    
    if not df_notas.empty:
        # Mostra apenas as colunas principais na visualização
        cols_principais = ['data', 'cnpj_tomador', 'cnpj_prestador', 'valor_servico', 'descricao_servico', 'codigo_servico']
        st.dataframe(df_notas[cols_principais])
        
        # Opções para editar/excluir notas
        col1, col2 = st.columns(2)
        with col1:
            linha_editar = st.number_input("Número da linha para editar", min_value=0, max_value=len(df_notas)-1, key='linha_editar')
            if st.button("Editar Linha"):
                st.session_state.editando = linha_editar
                
        with col2:
            linha_excluir = st.number_input("Número da linha para excluir", min_value=0, max_value=len(df_notas)-1, key='linha_excluir')
            if st.button("Excluir Linha"):
                id_excluir = df_notas.iloc[linha_excluir]['id']
                c.execute("DELETE FROM notas_fiscais WHERE id = ?", (id_excluir,))
                conn.commit()
                st.success("Linha excluída com sucesso!")
                st.experimental_rerun()
        
        # Formulário de edição
        if 'editando' in st.session_state:
            with st.expander("✏️ Editar Nota Fiscal", expanded=True):
                nota_editar = df_notas.iloc[st.session_state.editando]
                
                col1, col2 = st.columns(2)
                with col1:
                    data_edit = st.date_input("Data", value=datetime.strptime(nota_editar['data'], '%Y-%m-%d'), key='data_edit')
                    cnpj_tomador_edit = st.text_input("CNPJ Tomador", value=nota_editar['cnpj_tomador'], key='cnpj_tomador_edit')
                    cnpj_prestador_edit = st.text_input("CNPJ Prestador", value=nota_editar['cnpj_prestador'], key='cnpj_prestador_edit')
                    valor_servico_edit = st.number_input("Valor do Serviço (R$)", value=float(nota_editar['valor_servico']), key='valor_servico_edit')
                    descricao_servico_edit = st.text_input("Descrição do Serviço", value=nota_editar['descricao_servico'], key='descricao_servico_edit')
                    codigo_servico_edit = st.text_input("Código do Serviço", value=nota_editar['codigo_servico'], key='codigo_servico_edit')
                
                with col2:
                    st.subheader("Tributos")
                    
                    # INSS
                    st.markdown("**INSS**")
                    aliquota_inss_edit = st.slider("Alíquota INSS (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                value=float(nota_editar['aliquota_inss']), key='aliquota_inss_edit')
                    valor_inss_edit = valor_servico_edit * (aliquota_inss_edit / 100)
                    st.info(f"Valor INSS: R$ {valor_inss_edit:.2f}")
                    
                    # IRRF
                    st.markdown("**IRRF**")
                    retem_irrf_edit = st.checkbox("Retém IRRF?", value=bool(nota_editar['retem_irrf']), key='retem_irrf_edit')
                    aliquota_irrf_edit = st.slider("Alíquota IRRF (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                  value=float(nota_editar['aliquota_irrf']), key='aliquota_irrf_edit', disabled=not retem_irrf_edit)
                    valor_irrf_edit = valor_servico_edit * (aliquota_irrf_edit / 100) if retem_irrf_edit else 0.0
                    st.info(f"Valor IRRF: R$ {valor_irrf_edit:.2f}")
                    
                    # PIS
                    st.markdown("**PIS**")
                    retem_pis_edit = st.checkbox("Retém PIS?", value=bool(nota_editar['retem_pis']), key='retem_pis_edit')
                    aliquota_pis_edit = st.slider("Alíquota PIS (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                value=float(nota_editar['aliquota_pis']), key='aliquota_pis_edit', disabled=not retem_pis_edit)
                    valor_pis_edit = valor_servico_edit * (aliquota_pis_edit / 100) if retem_pis_edit else 0.0
                    st.info(f"Valor PIS: R$ {valor_pis_edit:.2f}")
                    
                    # COFINS
                    st.markdown("**COFINS**")
                    retem_cofins_edit = st.checkbox("Retém COFINS?", value=bool(nota_editar['retem_cofins']), key='retem_cofins_edit')
                    aliquota_cofins_edit = st.slider("Alíquota COFINS (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                    value=float(nota_editar['aliquota_cofins']), key='aliquota_cofins_edit', disabled=not retem_cofins_edit)
                    valor_cofins_edit = valor_servico_edit * (aliquota_cofins_edit / 100) if retem_cofins_edit else 0.0
                    st.info(f"Valor COFINS: R$ {valor_cofins_edit:.2f}")
                    
                    # CSLL
                    st.markdown("**CSLL**")
                    retem_csll_edit = st.checkbox("Retém CSLL?", value=bool(nota_editar['retem_csll']), key='retem_csll_edit')
                    aliquota_csll_edit = st.slider("Alíquota CSLL (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                  value=float(nota_editar['aliquota_csll']), key='aliquota_csll_edit', disabled=not retem_csll_edit)
                    valor_csll_edit = valor_servico_edit * (aliquota_csll_edit / 100) if retem_csll_edit else 0.0
                    st.info(f"Valor CSLL: R$ {valor_csll_edit:.2f}")
                
                if st.button("Salvar Alterações"):
                    # Atualizar no banco de dados
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
                        data_edit.strftime('%Y-%m-%d'), cnpj_tomador_edit, cnpj_prestador_edit, valor_servico_edit,
                        descricao_servico_edit, codigo_servico_edit, aliquota_inss_edit,
                        valor_inss_edit, int(retem_irrf_edit), aliquota_irrf_edit, valor_irrf_edit,
                        int(retem_pis_edit), aliquota_pis_edit, valor_pis_edit, int(retem_cofins_edit),
                        aliquota_cofins_edit, valor_cofins_edit, int(retem_csll_edit),
                        aliquota_csll_edit, valor_csll_edit, nota_editar['id']
                    ))
                    conn.commit()
                    del st.session_state.editando
                    st.success("Alterações salvas com sucesso!")
                    st.experimental_rerun()
    else:
        st.warning("Nenhuma nota fiscal cadastrada ainda.")
    
    # Geração do arquivo EFD REINF
    st.subheader("Gerar Arquivo EFD REINF")
    
    if st.button("🔄 Gerar Arquivo para Entrega (R2010 e R4020)"):
        if df_notas.empty:
            st.error("Nenhuma nota fiscal cadastrada para gerar o arquivo.")
        else:
            # Simulação da geração do arquivo
            data_geracao = datetime.now().strftime('%Y%m%d%H%M%S')
            nome_arquivo = f"EFD_REINF_{data_geracao}.txt"
            
            # Cabeçalho do arquivo
            conteudo = [
                "|EFDREINF|0100|1|",
                "|0001|1|12345678901234|Empresa Teste|12345678|||A|12345678901|email@empresa.com|",
                "|0100|Fulano de Tal|12345678901|Rua Teste, 123|3100000||99999999|email@contador.com|"
            ]
            
            # Adiciona registros R2010 para cada nota
            for idx, nota in df_notas.iterrows():
                conteudo.append(f"|2010|{idx+1}|{nota['cnpj_tomador']}|{nota['cnpj_prestador']}|{nota['data'].replace('-', '')}|{nota['codigo_servico']}|{nota['valor_servico']:.2f}|{nota['aliquota_inss']:.2f}|{nota['valor_inss']:.2f}|")
            
            # Adiciona registros R4020 com todos os tributos
            total_inss = df_notas['valor_inss'].sum()
            total_irrf = df_notas['valor_irrf'].sum()
            total_pis = df_notas['valor_pis'].sum()
            total_cofins = df_notas['valor_cofins'].sum()
            total_csll = df_notas['valor_csll'].sum()
            
            conteudo.append(f"|4020|1|{datetime.now().strftime('%Y%m')}|{total_inss:.2f}|{total_irrf:.2f}|{total_pis:.2f}|{total_cofins:.2f}|{total_csll:.2f}|1|")
            
            # Rodapé do arquivo
            conteudo.append("|9001|1|")
            conteudo.append(f"|9900|EFDREINF|{len(conteudo) - 3}|")
            conteudo.append("|9999|7|")
            
            arquivo_final = "\n".join(conteudo)
            
            # Cria o botão de download
            b64 = base64.b64encode(arquivo_final.encode('utf-8')).decode()
            href = f'<a href="data:file/txt;base64,{b64}" download="{nome_arquivo}">⬇️ Baixar Arquivo EFD REINF</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            st.success("Arquivo gerado com sucesso!")
            
            # Resumo dos totais
            st.subheader("Resumo dos Tributos")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total INSS", f"R$ {total_inss:.2f}")
            col2.metric("Total IRRF", f"R$ {total_irrf:.2f}")
            col3.metric("Total PIS", f"R$ {total_pis:.2f}")
            col4.metric("Total COFINS", f"R$ {total_cofins:.2f}")
            col5.metric("Total CSLL", f"R$ {total_csll:.2f}")
            
            # Prévia do arquivo
            st.subheader("Prévia do Arquivo")
            st.text_area("Conteúdo do Arquivo", arquivo_final, height=300)
    
    conn.close()

# =============================================
# FUNÇÕES DE ATIVIDADES FISCAIS
# =============================================

def atividades_fiscais():
    st.markdown('<div class="header"><h1>📊 Controle de Atividades Fiscais - HÄFELE BRASIL</h1></div>', unsafe_allow_html=True)

    # Conexão com o banco de dados SQLite
    DATABASE = 'atividades_fiscais.db'

    def create_connection():
        """Cria e retorna uma conexão com o banco de dados."""
        try:
            conn = sqlite3.connect(DATABASE)
            return conn
        except sqlite3.Error as e:
            st.error(f"Erro ao conectar ao banco de dados: {e}")
            return None

    def create_table():
        """Cria a tabela de atividades se não existir."""
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

    def load_data_from_db(mes_ano_referencia):
        """Carrega dados do banco de dados para um DataFrame."""
        conn = create_connection()
        df = pd.DataFrame()
        if conn is not None:
            try:
                query = "SELECT * FROM atividades WHERE MesAnoReferencia = ?"
                df = pd.read_sql_query(query, conn, params=(mes_ano_referencia,))
                
                # Converter colunas de data
                date_columns = ['Prazo', 'DataInicio', 'DataConclusao']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    else:
                        df[col] = pd.NaT
            except sqlite3.Error as e:
                st.error(f"Erro ao carregar dados do banco de dados: {e}")
            finally:
                conn.close()
        return df

    def update_activity_in_db(activity_id, updates):
        """Atualiza uma atividade no banco de dados."""
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

    def add_activity_to_db(activity):
        """Adiciona uma nova atividade ao banco de dados."""
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

    def load_initial_data_template():
        """Retorna o template de dados iniciais."""
        return [
            {
                "Obrigação": "Sped Fiscal",
                "Descrição": "Entrega do arquivo digital da EFD ICMS/IPI com registros fiscais de entradas, saídas, apuração de ICMS e IPI.",
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

    def get_next_month_year(current_month_year):
        """Calcula o próximo mês/ano."""
        month, year = map(int, current_month_year.split('/'))
        if month == 12:
            return f"01/{year + 1}"
        return f"{str(month + 1).zfill(2)}/{year}"

    def get_previous_month_year(current_month_year):
        """Calcula o mês/ano anterior."""
        month, year = map(int, current_month_year.split('/'))
        if month == 1:
            return f"12/{year - 1}"
        return f"{str(month - 1).zfill(2)}/{year}"

    def calculate_deadline(data_limite_text, mes_ano_referencia):
        """Calcula a data limite com base no texto descritivo."""
        ref_month, ref_year = map(int, mes_ano_referencia.split('/'))
        
        if "dia 10 do mês subsequente" in data_limite_text:
            date_for_calc = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=1)
            return date_for_calc.replace(day=10)
        elif "dia 15 do mês subsequente" in data_limite_text:
            date_for_calc = datetime(ref_year, ref_month, 1) + pd.DateOffset(months=1)
            return date_for_calc.replace(day=15)
        return datetime(ref_year, ref_month, 1) + timedelta(days=90)

    def apply_status_style(status):
        """Aplica estilo CSS ao status."""
        if status == "Pendente":
            return '<span class="status-badge status-pendente">Pendente</span>'
        elif status == "Em Andamento":
            return '<span class="status-badge status-andamento">Em Andamento</span>'
        elif status == "Finalizado":
            return '<span class="status-badge status-finalizado">Finalizado</span>'
        elif status == "Fechado":
            return '<span class="status-badge status-fechado">Fechado</span>'
        return f'<span class="status-badge">{status}</span>'

    def apply_difficulty_style(dificuldade):
        """Aplica estilo CSS à dificuldade."""
        if dificuldade == "Baixa":
            return '<span class="dificuldade-badge dificuldade-baixa">Baixa</span>'
        elif dificuldade == "Média":
            return '<span class="dificuldade-badge dificuldade-media">Média</span>'
        elif dificuldade == "Alta":
            return '<span class="dificuldade-badge dificuldade-alta">Alta</span>'
        return f'<span class="dificuldade-badge">{dificuldade}</span>'

    def calculate_days_remaining(row):
        """Calcula dias restantes para conclusão."""
        hoje = datetime.now()
        if pd.isna(row['Prazo']) or row['Status'] in ['Finalizado', 'Fechado']:
            return None
        prazo = row['Prazo']
        days = (prazo - hoje).days
        return days if days >= 0 else 0

    def initialize_session_state():
        """Inicializa o estado da sessão."""
        if 'mes_ano_referencia' not in st.session_state:
            st.session_state.mes_ano_referencia = datetime.now().strftime('%m/%Y')
        
        if 'df_atividades' not in st.session_state:
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)

    def show_navigation():
        """Mostra a navegação entre meses."""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀️ Mês Anterior"):
                st.session_state.mes_ano_referencia = get_previous_month_year(st.session_state.mes_ano_referencia)
                st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                st.rerun()
        
        with col2:
            st.markdown(f"<h2 style='text-align: center;'>Mês/Ano de Referência: {st.session_state.mes_ano_referencia}</h2>", unsafe_allow_html=True)
        
        with col3:
            if st.button("Próximo Mês ▶️"):
                st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
                st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                st.rerun()

    def show_metrics():
        """Mostra as métricas de status."""
        cols = st.columns(5)
        metrics = [
            ("Total de Atividades", ""),
            ("Pendentes", "Pendente"),
            ("Em Andamento", "Em Andamento"),
            ("Finalizadas", "Finalizado"),
            ("Fechadas", "Fechado")
        ]
        
        for (label, status), col in zip(metrics, cols):
            if status:
                count = len(st.session_state.df_atividades[st.session_state.df_atividades['Status'] == status])
            else:
                count = len(st.session_state.df_atividades)
            col.metric(label, count)

    def show_charts():
        """Mostra os gráficos de análise."""
        st.markdown("---")
        st.markdown('<div class="card"><h3>📈 Análise Gráfica</h3></div>', unsafe_allow_html=True)
        
        if st.session_state.df_atividades.empty:
            st.info("Adicione atividades ou habilite um mês para ver as análises gráficas.")
            return

        tab1, tab2, tab3 = st.tabs(["Status", "Dificuldade", "Prazo"])

        with tab1:
            status_counts = st.session_state.df_atividades['Status'].value_counts().reset_index()
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
            dificuldade_counts = st.session_state.df_atividades['Dificuldade'].value_counts().reset_index()
            fig_dificuldade = px.bar(
                dificuldade_counts,
                x='Dificuldade',
                y='count',
                title='Distribuição por Nível de Dificuldade',
                color='Dificuldade',
                color_discrete_map={
                    'Baixa': '#28a745',
                    'Média': '#ffc107',
                    'Alta': '#dc3545'
                }
            )
            st.plotly_chart(fig_dificuldade, use_container_width=True)

        with tab3:
            prazo_df = st.session_state.df_atividades.copy()
            prazo_df = prazo_df.dropna(subset=['Prazo'])
            
            if not prazo_df.empty:
                prazo_df['Prazo Formatado'] = prazo_df['Prazo'].dt.strftime('%d/%m/%Y')
                prazo_df['Data Início Visual'] = prazo_df['DataInicio'].fillna(prazo_df['Prazo'] - timedelta(days=1))
                
                fig_prazo = px.timeline(
                    prazo_df,
                    x_start="Data Início Visual",
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
                        "Prazo Formatado": True,
                        "Data Início Visual": False
                    }
                )
                fig_prazo.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_prazo, use_container_width=True)
            else:
                st.info("Não há atividades com prazo definido para exibir na linha do tempo.")

    def show_activities_table():
        """Mostra a tabela de atividades com filtros."""
        st.markdown("---")
        st.markdown('<div class="card"><h3>📋 Lista de Atividades</h3></div>', unsafe_allow_html=True)

        if st.session_state.df_atividades.empty:
            st.info("Nenhuma atividade encontrada para o mês selecionado.")
            return

        with st.expander("🔍 Filtros", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.selectbox("Status", ["Todos", "Pendente", "Em Andamento", "Finalizado", "Fechado"])
            with col2:
                difficulty_filter = st.selectbox("Dificuldade", ["Todos", "Baixa", "Média", "Alta"])
            with col3:
                orgao_options = ["Todos"] + list(st.session_state.df_atividades['OrgaoResponsavel'].unique())
                orgao_filter = st.selectbox("Órgão Responsável", orgao_options)

        filtered_df = st.session_state.df_atividades.copy()
        
        if status_filter != "Todos":
            filtered_df = filtered_df[filtered_df['Status'] == status_filter]
        if difficulty_filter != "Todos":
            filtered_df = filtered_df[filtered_df['Dificuldade'] == difficulty_filter]
        if orgao_filter != "Todos":
            filtered_df = filtered_df[filtered_df['OrgaoResponsavel'] == orgao_filter]
        
        filtered_df['Dias Restantes'] = filtered_df.apply(calculate_days_remaining, axis=1)

        display_df = filtered_df.copy()
        display_df['Status'] = display_df['Status'].apply(apply_status_style)
        display_df['Dificuldade'] = display_df['Dificuldade'].apply(apply_difficulty_style)
        
        for col in ['Prazo', 'DataInicio', 'DataConclusao']:
            display_df[col] = display_df[col].dt.strftime('%d/%m/%Y').replace({pd.NaT: ''})

        cols_to_display = [
            'Obrigacao', 'Descricao', 'Periodicidade', 'OrgaoResponsavel',
            'DataLimite', 'Status', 'Dificuldade', 'Prazo', 'Dias Restantes'
        ]
        
        st.write(display_df[cols_to_display].to_html(escape=False, index=False), unsafe_allow_html=True)

    def show_add_activity_form():
        """Mostra o formulário para adicionar nova atividade."""
        st.markdown("---")
        with st.expander("➕ Adicionar Nova Atividade", expanded=False):
            with st.form("nova_atividade_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    obrigacao = st.text_input("Obrigação*", placeholder="Nome da obrigação fiscal")
                    descricao = st.text_area("Descrição*", placeholder="Descrição detalhada da atividade")
                    periodicidade = st.selectbox("Periodicidade*", ["Mensal", "Trimestral", "Anual", "Eventual", "Extinta"])
                with col2:
                    orgao = st.text_input("Órgão Responsável*", placeholder="Órgão responsável")
                    data_limite = st.text_input("Data Limite de Entrega*", placeholder="Ex: Até o dia 10 do mês subsequente")
                    status = st.selectbox("Status*", ["Pendente", "Em Andamento", "Finalizado", "Fechado"])
                    dificuldade = st.selectbox("Dificuldade*", ["Baixa", "Média", "Alta"])
                    prazo = st.date_input("Prazo Final*")

                if st.form_submit_button("Adicionar Atividade"):
                    if obrigacao and descricao and orgao and data_limite and prazo:
                        prazo_calculado = calculate_deadline(data_limite, st.session_state.mes_ano_referencia)
                        
                        nova_atividade = {
                            "Obrigação": obrigacao,
                            "Descrição": descricao,
                            "Periodicidade": periodicidade,
                            "Órgão Responsável": orgao,
                            "Data Limite": data_limite,
                            "Status": status,
                            "Dificuldade": dificuldade,
                            "Prazo": prazo_calculado.strftime('%Y-%m-%d %H:%M:%S') if prazo_calculado else None,
                            "Data Início": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == "Em Andamento" else None,
                            "Data Conclusão": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == "Finalizado" else None,
                            "MesAnoReferencia": st.session_state.mes_ano_referencia
                        }

                        if add_activity_to_db(nova_atividade):
                            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                            st.success("✅ Atividade adicionada com sucesso!")
                            st.rerun()
                    else:
                        st.error("⚠️ Preencha todos os campos obrigatórios (marcados com *)")

    def show_edit_activity_form():
        """Mostra o formulário para editar atividades existentes."""
        st.markdown("---")
        with st.expander("✏️ Editar Atividades", expanded=False):
            if st.session_state.df_atividades.empty:
                st.info("Nenhuma atividade para editar. Adicione atividades ou habilite um novo mês.")
                return

            atividade_selecionada = st.selectbox(
                "Selecione a atividade para editar",
                st.session_state.df_atividades['Obrigacao'].unique()
            )

            atividade = st.session_state.df_atividades[
                st.session_state.df_atividades['Obrigacao'] == atividade_selecionada
            ].iloc[0]

            col1, col2 = st.columns(2)
            with col1:
                novo_status = st.selectbox(
                    "Novo Status",
                    ["Pendente", "Em Andamento", "Finalizado", "Fechado"],
                    index=["Pendente", "Em Andamento", "Finalizado", "Fechado"].index(atividade['Status'])
                )
            with col2:
                novo_prazo = st.date_input(
                    "Novo Prazo Final",
                    value=atividade['Prazo'].date() if pd.notna(atividade['Prazo']) else datetime.now().date()
                )

            if st.button("Atualizar Atividade"):
                updates = {}
                
                if novo_status != atividade['Status']:
                    updates['Status'] = novo_status
                    
                    if novo_status == "Em Andamento" and pd.isna(atividade['DataInicio']):
                        updates['DataInicio'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    elif novo_status != "Em Andamento" and pd.notna(atividade['DataInicio']):
                        updates['DataInicio'] = None
                    
                    if novo_status == "Finalizado":
                        updates['DataConclusao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    elif novo_status != "Finalizado" and pd.notna(atividade['DataConclusao']):
                        updates['DataConclusao'] = None
                
                novo_prazo_dt = datetime.combine(novo_prazo, datetime.min.time())
                if pd.isna(atividade['Prazo']) or novo_prazo_dt != atividade['Prazo']:
                    updates['Prazo'] = novo_prazo_dt.strftime('%Y-%m-%d %H:%M:%S')
                
                if updates:
                    if update_activity_in_db(atividade['id'], updates):
                        st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                        st.success("✅ Atividade atualizada com sucesso!")
                        st.rerun()
                else:
                    st.info("Nenhuma alteração detectada para atualizar.")

    def show_close_period_section():
        """Mostra a seção para fechar o período atual."""
        st.markdown("---")
        st.markdown('<div class="card"><h3>🗓️ Fechamento e Habilitação de Período</h3></div>', unsafe_allow_html=True)

        if st.session_state.df_atividades.empty:
            st.info("Nenhuma atividade para fechar. Habilite um mês primeiro.")
            return

        todas_finalizadas = all(st.session_state.df_atividades['Status'].isin(["Finalizado", "Fechado"]))

        if todas_finalizadas:
            st.success(f"🎉 Todas as atividades para {st.session_state.mes_ano_referencia} estão finalizadas ou fechadas!")
            
            if st.button("Fechar Período e Habilitar Próximo Mês"):
                conn = create_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE atividades
                            SET Status = 'Fechado'
                            WHERE MesAnoReferencia = ?
                        """, (st.session_state.mes_ano_referencia,))
                        conn.commit()
                    except sqlite3.Error as e:
                        st.error(f"Erro ao fechar período: {e}")
                    finally:
                        conn.close()

                st.session_state.mes_ano_referencia = get_next_month_year(st.session_state.mes_ano_referencia)
                st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)

                if st.session_state.df_atividades.empty:
                    atividades = load_initial_data_template()
                    for atividade in atividades:
                        prazo = calculate_deadline(atividade['Data Limite'], st.session_state.mes_ano_referencia)
                        atividade.update({
                            'Prazo': prazo.strftime('%Y-%m-%d %H:%M:%S') if prazo else None,
                            'MesAnoReferencia': st.session_state.mes_ano_referencia,
                            'Data Início': None,
                            'Data Conclusão': None
                        })
                    
                    conn = create_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            for atividade in atividades:
                                cursor.execute("""
                                    INSERT INTO atividades (
                                        Obrigacao, Descricao, Periodicidade, OrgaoResponsavel, DataLimite,
                                        Status, Dificuldade, Prazo, DataInicio, DataConclusao, MesAnoReferencia
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    atividade['Obrigação'], atividade['Descrição'], atividade['Periodicidade'],
                                    atividade['Órgão Responsável'], atividade['Data Limite'], atividade['Status'],
                                    atividade['Dificuldade'], atividade['Prazo'], atividade['Data Início'],
                                    atividade['Data Conclusão'], atividade['MesAnoReferencia']
                                ))
                            conn.commit()
                        except sqlite3.Error as e:
                            st.error(f"Erro ao inserir atividades iniciais: {e}")
                        finally:
                            conn.close()
                    
                    st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
                    st.success("Atividades padrão habilitadas para o novo mês!")
                
                st.rerun()
        else:
            st.warning(f"Ainda há atividades pendentes ou em andamento para {st.session_state.mes_ano_referencia}. Finalize-as para fechar o período.")

    # Inicialização
    create_table()
    initialize_session_state()

    # Habilitar mês se não houver dados
    if st.session_state.df_atividades.empty:
        st.warning(f"Não há atividades cadastradas para {st.session_state.mes_ano_referencia}.")
        if st.button(f"Habilitar Mês {st.session_state.mes_ano_referencia}"):
            atividades = load_initial_data_template()
            for atividade in atividades:
                prazo = calculate_deadline(atividade['Data Limite'], st.session_state.mes_ano_referencia)
                atividade.update({
                    'Prazo': prazo.strftime('%Y-%m-%d %H:%M:%S') if prazo else None,
                    'MesAnoReferencia': st.session_state.mes_ano_referencia,
                    'Data Início': None,
                    'Data Conclusão': None
                })
            
            conn = create_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    for atividade in atividades:
                        cursor.execute("""
                            INSERT INTO atividades (
                                Obrigacao, Descricao, Periodicidade, OrgaoResponsavel, DataLimite,
                                Status, Dificuldade, Prazo, DataInicio, DataConclusao, MesAnoReferencia
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            atividade['Obrigação'], atividade['Descrição'], atividade['Periodicidade'],
                            atividade['Órgão Responsável'], atividade['Data Limite'], atividade['Status'],
                            atividade['Dificuldade'], atividade['Prazo'], atividade['Data Início'],
                            atividade['Data Conclusão'], atividade['MesAnoReferencia']
                        ))
                    conn.commit()
                except sqlite3.Error as e:
                    st.error(f"Erro ao inserir atividades iniciais: {e}")
                finally:
                    conn.close()
            
            st.session_state.df_atividades = load_data_from_db(st.session_state.mes_ano_referencia)
            st.success("Atividades padrão habilitadas com sucesso!")
            st.rerun()

    # Componentes da interface
    show_navigation()
    show_metrics()
    show_charts()
    show_activities_table()
    show_add_activity_form()
    show_edit_activity_form()
    show_close_period_section()

# =============================================
# FUNÇÃO PRINCIPAL
# =============================================

def main():
    # Mostrar tela inicial se nenhum módulo foi selecionado
    if 'modulo_selecionado' not in st.session_state:
        st.session_state.modulo_selecionado = None
    
    if st.session_state.modulo_selecionado is None:
        st.markdown("""
        <div class="welcome-container">
            <div class="welcome-message">
                Bem vindo ao sistema fiscal
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Menu de navegação
    st.sidebar.title("Menu de Navegação")
    opcao = st.sidebar.radio("Selecione o módulo:", 
                            ["Início", "Processador de arquivos TXT", "Lançamentos EFD REINF", "Atividades Fiscais"])
    
    if opcao != "Início":
        st.session_state.modulo_selecionado = opcao
    
    # Mostrar o módulo selecionado
    if st.session_state.modulo_selecionado == "Processador de arquivos TXT":
        processador_txt()
    elif st.session_state.modulo_selecionado == "Lançamentos EFD REINF":
        lancamentos_efd_reinf()
    elif st.session_state.modulo_selecionado == "Atividades Fiscais":
        atividades_fiscais()

if __name__ == "__main__":
    main()
