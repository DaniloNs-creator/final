import streamlit as st
import pandas as pd
import plotly.express as px
import time
import xml.etree.ElementTree as ET
import traceback
from io import BytesIO
import chardet
from datetime import datetime

# --- CONFIGURAÇÃO INICIAL DA PÁGINA ---
st.set_page_config(
    page_title="Sistema de Processamento",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Namespaces para CT-e (essencial para o parser XML)
CTE_NAMESPACES = {
    'cte': 'http://www.portalfiscal.inf.br/cte'
}

# --- PROCESSADOR DE ARQUIVOS TXT (SEM ALTERAÇÕES) ---
def processador_txt():
    st.title("📄 Processador de Arquivos TXT")
    st.markdown("""
    <div class="card">
        Remova linhas indesejadas de arquivos TXT. Carregue seu arquivo e defina os padrões a serem removidos.
    </div>
    """, unsafe_allow_html=True)

    def detectar_encoding(conteudo):
        resultado = chardet.detect(conteudo)
        return resultado['encoding']

    def processar_arquivo(conteudo, padroes):
        try:
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN"
            }
            encoding = detectar_encoding(conteudo)
            try:
                texto = conteudo.decode(encoding)
            except UnicodeDecodeError:
                texto = conteudo.decode('latin-1')
            
            linhas = texto.splitlines()
            linhas_processadas = []
            
            for linha in linhas:
                linha = linha.strip()
                if not any(padrao in linha for padrao in padroes):
                    for original, substituto in substituicoes.items():
                        linha = linha.replace(original, substituto)
                    linhas_processadas.append(linha)
            
            return "\n".join(linhas_processadas), len(linhas)
        
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            return None, 0

    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
    arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'], key="txt_uploader")
    
    with st.expander("⚙️ Configurações avançadas", expanded=False):
        padroes_adicionais = st.text_input(
            "Padrões adicionais para remoção (separados por vírgula)",
            help="Exemplo: padrão1, padrão2, padrão3"
        )
        padroes = padroes_default + [p.strip() for p in padroes_adicionais.split(",") if p.strip()] if padroes_adicionais else padroes_default

    if arquivo is not None:
        conteudo = arquivo.read()
        resultado, total_linhas = processar_arquivo(conteudo, padroes)
        
        if resultado is not None:
            linhas_processadas = len(resultado.splitlines())
            st.success(f"""
            **Processamento concluído!** ✔️ Linhas originais: {total_linhas}  
            ✔️ Linhas processadas: {linhas_processadas}  
            ✔️ Linhas removidas: {total_linhas - linhas_processadas}
            """)
            st.subheader("Prévia do resultado")
            st.text_area("Conteúdo processado", resultado, height=300)

            buffer = BytesIO(resultado.encode('utf-8'))
            st.download_button(
                label="⬇️ Baixar arquivo processado",
                data=buffer,
                file_name=f"processado_{arquivo.name}",
                mime="text/plain"
            )

# --- PROCESSADOR DE CT-e (CÓDIGO REESCRITO) ---
class CTeProcessor:
    def __init__(self):
        # Usar st.session_state para persistir dados entre reruns
        if 'processed_data' not in st.session_state:
            st.session_state.processed_data = []

    def extract_nfe_number_from_key(self, chave_acesso):
        """Extrai o número da NF-e (posições 26-34) da chave de acesso de 44 dígitos."""
        if isinstance(chave_acesso, str) and len(chave_acesso) == 44:
            return chave_acesso[25:34]
        return None

    def find_text(self, element, xpath):
        """Função auxiliar para encontrar texto em XML com namespaces."""
        node = element.find(xpath, CTE_NAMESPACES)
        return node.text if node is not None else None

    def extract_cte_data(self, xml_content, filename):
        """Extrai os dados do XML do CT-e, incluindo o Peso Bruto."""
        try:
            root = ET.fromstring(xml_content)
            infCte = root.find('.//cte:infCte', CTE_NAMESPACES)
            if infCte is None: return None

            # Extração dos dados principais
            ide = infCte.find('cte:ide', CTE_NAMESPACES)
            emit = infCte.find('cte:emit', CTE_NAMESPACES)
            rem = infCte.find('cte:rem', CTE_NAMESPACES)
            dest = infCte.find('cte:dest', CTE_NAMESPACES)
            vPrest = infCte.find('cte:vPrest', CTE_NAMESPACES)
            infCarga = infCte.find('.//cte:infCarga', CTE_NAMESPACES)
            infNFe = infCte.find('.//cte:infNFe', CTE_NAMESPACES)

            # --- NOVA EXTRAÇÃO: PESO BRUTO ---
            peso_bruto = 'N/A'
            if infCarga is not None:
                # Procura por todas as tags <infQ>
                for infQ in infCarga.findall('cte:infQ', CTE_NAMESPACES):
                    tpMed = self.find_text(infQ, 'cte:tpMed')
                    # Se encontrar a tag com 'PESO BRUTO', extrai a carga
                    if tpMed == 'PESO BRUTO':
                        qCarga = self.find_text(infQ, 'cte:qCarga')
                        try:
                            peso_bruto = float(qCarga) if qCarga else 0.0
                        except (ValueError, TypeError):
                            peso_bruto = 'N/A' # Caso o valor não seja numérico
                        break # Para o loop assim que encontrar

            # Extração dos demais dados
            nCT = self.find_text(ide, 'cte:nCT')
            dhEmi_str = self.find_text(ide, 'cte:dhEmi')
            vTPrest_str = self.find_text(vPrest, 'cte:vTPrest')
            chave_nfe = self.find_text(infNFe, 'cte:chave')
            
            # Formatação e tratamento dos dados
            data_formatada = datetime.fromisoformat(dhEmi_str).strftime('%d/%m/%Y') if dhEmi_str else 'N/A'
            valor_prestacao = float(vTPrest_str) if vTPrest_str else 0.0
            numero_nfe = self.extract_nfe_number_from_key(chave_nfe)

            dest_CNPJ = self.find_text(dest.find('cte:enderDest', CTE_NAMESPACES), 'cte:CNPJ') if dest else None
            dest_CPF = self.find_text(dest.find('cte:enderDest', CTE_NAMESPACES), 'cte:CPF') if dest else None

            # Retorna um dicionário com todos os dados extraídos
            return {
                'Arquivo': filename,
                'nCT': nCT,
                'Data Emissão': data_formatada,
                'Emitente': self.find_text(emit, 'cte:xNome'),
                'Remetente': self.find_text(rem, 'cte:xNome'),
                'Destinatário': self.find_text(dest, 'cte:xNome'),
                'Documento Destinatário': dest_CNPJ or dest_CPF or 'N/A',
                'Município Destino': self.find_text(dest.find('cte:enderDest', CTE_NAMESPACES), 'cte:xMun') if dest else 'N/A',
                'UF Destino': self.find_text(dest.find('cte:enderDest', CTE_NAMESPACES), 'cte:UF') if dest else 'N/A',
                'Valor Prestação': valor_prestacao,
                'Peso Bruto (KG)': peso_bruto,
                'Chave NFe': chave_nfe or 'N/A',
                'Número NFe': numero_nfe or 'N/A',
                'Data Processamento': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
        except Exception as e:
            st.warning(f"Erro ao processar o arquivo '{filename}': {e}")
            return None

    def process_file(self, uploaded_file):
        """Processa um único arquivo XML e adiciona os dados à sessão."""
        try:
            filename = uploaded_file.name
            if not filename.lower().endswith('.xml'):
                return False, f"'{filename}' não é um arquivo XML."

            xml_content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
            if 'CTe' not in xml_content:
                return False, f"'{filename}' não parece ser um CT-e."
                
            cte_data = self.extract_cte_data(xml_content, filename)
            
            if cte_data:
                st.session_state.processed_data.append(cte_data)
                return True, f"'{filename}' processado com sucesso!"
            else:
                return False, f"Falha ao extrair dados de '{filename}'."

        except Exception as e:
            return False, f"Erro crítico ao ler '{filename}': {e}"

    def get_dataframe(self):
        """Retorna os dados processados como um DataFrame pandas."""
        if st.session_state.processed_data:
            return pd.DataFrame(st.session_state.processed_data)
        return pd.DataFrame()

    def clear_data(self):
        """Limpa os dados da sessão."""
        st.session_state.processed_data = []

def processador_cte():
    """Interface Streamlit para o processador de CT-e."""
    processor = CTeProcessor()
    
    st.title("🚚 Processador de CT-e para Power BI")
    st.markdown("### Extraia dados de arquivos XML de CT-e e gere uma planilha para análise.")
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload", "👀 Visualizar Dados", "📥 Exportar"])
    
    with tab1:
        st.header("Upload de CT-es")
        
        uploaded_files = st.file_uploader(
            "Selecione um ou mais arquivos XML de CT-e",
            type=['xml'],
            accept_multiple_files=True,
            key="cte_uploader"
        )
        
        if uploaded_files:
            if st.button(f"📊 Processar {len(uploaded_files)} Arquivo(s)", type="primary"):
                # --- ANIMAÇÃO PARA PROCESSAMENTO EM LOTE ---
                progress_bar = st.progress(0, text="Iniciando processamento...")
                status_text = st.empty()
                
                success_count = 0
                error_count = 0
                
                for i, uploaded_file in enumerate(uploaded_files):
                    # Atualiza a UI com o status
                    progress_text = f"Processando: {uploaded_file.name} ({i+1}/{len(uploaded_files)})"
                    status_text.text(progress_text)
                    progress_bar.progress((i + 1) / len(uploaded_files), text=progress_text)
                    
                    # Simula um pequeno delay para a animação ser visível
                    time.sleep(0.1) 
                    
                    success, message = processor.process_file(uploaded_file)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        st.warning(message) # Mostra avisos de erro discretamente

                # Limpa os elementos de animação e mostra o resultado final
                status_text.empty()
                progress_bar.empty()
                st.success(f"**Processamento concluído!** ✅ {success_count} sucesso(s) | ❌ {error_count} erro(s).")
                st.info("Navegue para a aba 'Visualizar Dados' para ver os resultados.")

    with tab2:
        st.header("Dados Processados")
        df = processor.get_dataframe()
        
        if not df.empty:
            st.write(f"Total de CT-es processados: **{len(df)}**")
            
            # --- Exibição do DataFrame com a nova coluna ---
            colunas_principais = [
                'nCT', 'Data Emissão', 'Emitente', 'Remetente', 
                'Destinatário', 'UF Destino', 'Valor Prestação', 'Peso Bruto (KG)', 'Número NFe'
            ]
            # Garante que todas as colunas existam no DF antes de tentar exibi-las
            colunas_existentes = [col for col in colunas_principais if col in df.columns]
            st.dataframe(df[colunas_existentes], use_container_width=True)
            
            # Detalhes expandíveis
            with st.expander("📋 Ver todos os campos detalhados"):
                st.dataframe(df, use_container_width=True)
            
            # Estatísticas
            st.subheader("📈 Estatísticas Rápidas")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Valor Total", f"R$ {df['Valor Prestação'].sum():,.2f}")
            col2.metric("Peso Bruto Total", f"{df['Peso Bruto (KG)'].sum():,.2f} KG")
            col3.metric("Ticket Médio", f"R$ {df['Valor Prestação'].mean():,.2f}")
            col4.metric("CT-es com NFe", f"{df[df['Número NFe'].notna()].shape[0]}")
            
        else:
            st.info("Nenhum CT-e processado ainda. Faça o upload de arquivos na aba 'Upload'.")

    with tab3:
        st.header("Exportar para Excel")
        df = processor.get_dataframe()
        
        if not df.empty:
            st.success(f"Pronto para exportar {len(df)} registros.")
            
            # Converte o DataFrame para Excel em memória
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Dados_CTe', index=False)
            output.seek(0)
            
            st.download_button(
                label="📥 Baixar Planilha Excel",
                data=output,
                file_name="dados_processados_cte.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            with st.expander("📋 Prévia dos dados a serem exportados"):
                st.dataframe(df.head(10))
        else:
            st.warning("Nenhum dado disponível para exportação.")

    # Botão para limpar dados na sidebar ou no final
    if st.sidebar.button("🗑️ Limpar Todos os Dados Processados"):
        processor.clear_data()
        st.success("Dados limpos com sucesso!")
        st.rerun()

# --- CSS E CONFIGURAÇÃO DE ESTILO ---
def load_css():
    st.markdown("""
    <style>
        .cover-container {
            text-align: center;
            margin-bottom: 2rem;
        }
        .cover-title {
            font-size: 2.5rem;
            font-weight: 700;
        }
        .card {
            background: #f0f2f6;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .stButton>button {
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

# --- APLICAÇÃO PRINCIPAL ---
def main():
    """Função principal que gerencia o fluxo da aplicação."""
    load_css()
    
    st.sidebar.image("https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png", width=200)
    st.sidebar.title("Menu de Ferramentas")
    
    st.markdown('<div class="cover-container"><h1 class="cover-title">Sistema de Processamento de Arquivos</h1></div>', unsafe_allow_html=True)
    
    # Menu de navegação
    app_mode = st.sidebar.radio("Selecione o Processador:", ["🚚 Processador CT-e", "📄 Processador TXT"])

    if app_mode == "🚚 Processador CT-e":
        processador_cte()
    elif app_mode == "📄 Processador TXT":
        processador_txt()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado na aplicação: {str(e)}")
        st.code(traceback.format_exc())
