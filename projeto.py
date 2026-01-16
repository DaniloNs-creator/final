import streamlit as st
import fitz  # PyMuPDF
import re
from lxml import etree
from datetime import datetime
import io

# Configuração da Página
st.set_page_config(page_title="Conversor DUIMP PDF > XML", layout="wide")

# --- CSS para melhorar a interface ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
    }
    .reportview-container {
        background: #f0f2f6;
    }
    </style>
""", unsafe_allow_html=True)

class DuimpParser:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.full_text = ""
        self.data = {
            "header": {},
            "adicoes": []
        }

    def extract_text_fast(self):
        """Extrai texto usando PyMuPDF para alta performance."""
        doc = fitz.open(stream=self.pdf_file.read(), filetype="pdf")
        text_parts = []
        
        # Barra de progresso para arquivos grandes
        progress_bar = st.progress(0)
        total_pages = len(doc)
        
        for i, page in enumerate(doc):
            # Extrai texto preservando layout físico aproximado
            text_parts.append(page.get_text("text"))
            
            # Atualiza barra a cada 10 páginas para não travar a UI
            if i % 10 == 0:
                progress_bar.progress((i + 1) / total_pages)
                
        progress_bar.progress(100)
        self.full_text = "\n".join(text_parts)
        doc.close()

    def parse_header(self):
        """Extrai dados gerais da DUIMP (Capa)."""
        text = self.full_text
        
        # Padrões Regex baseados no layout do PDF fornecido
        patterns = {
            "numeroDUIMP": r"Extrato da DUIMP\s+([\w\-\/]+)",
            "cnpjImportador": r"CNPJ do importador:\s*\n\s*([\d\.\/\-]+)",
            "nomeImportador": r"Nome do importador:\s*\n\s*(.+)",
            "pesoBruto": r"Peso Bruto \(kg\):\s*\n\s*\"?([\d\.]+,\d+)\"?",
            "pesoLiquido": r"Peso Liquido \(kg\):\s*\n\s*\"?([\d\.]+,\d+)\"?",
            "unidadeDespacho": r"Unidade de despacho:\s*\n\s*([\d]+-[A-Z\s]+)",
            "paisProcedencia": r"País de Procedência:\s*\n\s*\"?([^\"]+)\"?"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                self.data["header"][key] = match.group(1).strip().replace('"', '')

    def parse_items(self):
        """Extrai as adições (Itens) iterando pelo texto."""
        # Divide o texto pelos marcadores de Item para processamento isolado
        # O padrão busca "Extrato da Duimp ... : Item 00001"
        item_chunks = re.split(r"Extrato da Duimp .+ : Item (\d+)", self.full_text)
        
        # O split gera [lixo, numero_item_1, conteudo_1, numero_item_2, conteudo_2...]
        if len(item_chunks) > 1:
            # Ignora o primeiro elemento (cabeçalho geral antes do item 1)
            for i in range(1, len(item_chunks), 2):
                item_num = item_chunks[i]
                content = item_chunks[i+1]
                
                adicao = {
                    "numeroAdicao": item_num,
                    "numeroSequencialItem": item_num, # Assumindo 1:1
                    "mercadoria": {}
                }

                # Regex específicos para dentro do Item
                item_patterns = {
                    "codigoNcm": r"NCM:\s*\n\s*([\d\.]+)",
                    "paisOrigem": r"País de origem:\s*\n\s*(.+)",
                    "condicaoVendaValorReais": r"Valor total na condição de venda:\s*\n\s*([\d\.,]+)", # Ajustar conforme layout
                    "valorUnitario": r"Valor unitário na condição de venda:\s*\n\s*([\d\.,]+)",
                    "quantidade": r"Quantidade na unidade estatística:\s*\n\s*([\d\.,]+)",
                    "descricaoMercadoria": r"Detalhamento do Produto:\s*\n\s*(.+?)(?=\n\s*Número de Identificação|\n\s*Código de Class)",
                    "unidadeMedida": r"Unidade estatística:\s*\n\s*(.+)"
                }

                for key, pattern in item_patterns.items():
                    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
                    if match:
                        value = match.group(1).strip().replace('\n', ' ')
                        if key in ["descricaoMercadoria"]:
                             adicao["mercadoria"][key] = value
                        else:
                            adicao[key] = value
                
                self.data["adicoes"].append(adicao)

    def generate_xml(self):
        """Gera o XML seguindo a estrutura estrita solicitada."""
        
        # Namespace e Raiz
        root = etree.Element("ListaDeclaracoes")
        duimp = etree.SubElement(root, "duimp")

        h = self.data["header"]
        
        # --- Preenchimento do Cabeçalho (Adições contêm os dados gerais no XML de exemplo) ---
        # No XML de exemplo, muitos dados gerais se repetem dentro da tag <adicao>.
        # Vamos iterar sobre as adições extraídas e montar a estrutura.
        
        for item in self.data["adicoes"]:
            adicao_node = etree.SubElement(duimp, "adicao")
            
            # Mapeamento campos Item
            etree.SubElement(adicao_node, "numeroAdicao").text = item.get("numeroAdicao", "")
            etree.SubElement(adicao_node, "numeroDUIMP").text = h.get("numeroDUIMP", "").split("/")[0].replace("-", "").replace(".", "") # Limpa formatação
            
            # Dados de Carga (Repetidos do Header)
            etree.SubElement(adicao_node, "dadosCargaPaisProcedenciaNome").text = h.get("paisProcedencia", "")
            etree.SubElement(adicao_node, "dadosCargaUrfEntradaCodigo").text = h.get("unidadeDespacho", "").split("-")[0]
            
            # Dados Mercadoria Específicos
            etree.SubElement(adicao_node, "dadosMercadoriaCodigoNcm").text = item.get("codigoNcm", "").replace(".", "")
            etree.SubElement(adicao_node, "paisOrigemMercadoriaNome").text = item.get("paisOrigem", "")
            
            # Sub-nó Mercadoria
            mercadoria_node = etree.SubElement(adicao_node, "mercadoria")
            etree.SubElement(mercadoria_node, "descricaoMercadoria").text = item["mercadoria"].get("descricaoMercadoria", "")
            etree.SubElement(mercadoria_node, "numeroSequencialItem").text = item.get("numeroSequencialItem", "")
            etree.SubElement(mercadoria_node, "quantidade").text = item.get("quantidade", "").replace(",", ".")
            etree.SubElement(mercadoria_node, "unidadeMedida").text = item.get("unidadeMedida", "")
            etree.SubElement(mercadoria_node, "valorUnitario").text = item.get("valorUnitario", "").replace(",", ".")

            # Valores Financeiros (Exemplo de mapeamento)
            etree.SubElement(adicao_node, "condicaoVendaValorMoeda").text = item.get("condicaoVendaValorReais", "").replace(",", ".")
            
            # Adicione aqui o restante das tags fixas ou calculadas conforme o XML modelo
            # Exemplo de tags fixas para manter estrutura:
            etree.SubElement(adicao_node, "condicaoVendaIncoterm").text = "FCA" # Exemplo, extrair se disponível
            
        # --- Dados Gerais da DUIMP (Fora das adições, se houver no layout alvo) ---
        # Baseado no XML enviado anteriormente, algumas tags ficam fora, outras dentro.
        # Ajuste conforme necessidade exata.
        
        armazem = etree.SubElement(duimp, "armazem")
        etree.SubElement(armazem, "nomeArmazem").text = "TCP" # Extrair do PDF se possível
        
        etree.SubElement(duimp, "cargaPesoBruto").text = h.get("pesoBruto", "").replace(".", "").replace(",", "")
        etree.SubElement(duimp, "cargaPesoLiquido").text = h.get("pesoLiquido", "").replace(".", "").replace(",", "")
        
        # Importador
        etree.SubElement(duimp, "importadorNome").text = h.get("nomeImportador", "")
        etree.SubElement(duimp, "importadorNumero").text = h.get("cnpjImportador", "").replace(".", "").replace("/", "").replace("-", "")

        return etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# --- Lógica do Streamlit ---

st.title("📄 Conversor DUIMP (PDF) para XML")
st.markdown("Extração de dados de importação com manutenção rigorosa de layout.")

uploaded_file = st.file_uploader("Arraste seu arquivo PDF aqui (Suporta 500+ páginas)", type=["pdf"])

if uploaded_file is not None:
    st.info(f"Arquivo carregado: {uploaded_file.name}")
    
    if st.button("Processar e Gerar XML"):
        try:
            with st.spinner("Lendo PDF e estruturando dados..."):
                # 1. Instancia o Parser
                parser = DuimpParser(uploaded_file)
                
                # 2. Extração Rápida (PyMuPDF)
                parser.extract_text_fast()
                
                # 3. Parsing Lógico
                parser.parse_header()
                parser.parse_items()
                
                # 4. Geração XML
                xml_content = parser.generate_xml()
                
                # 5. Visualização e Download
                st.success(f"Processamento concluído! Encontrados {len(parser.data['adicoes'])} itens.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Prévia dos Dados Extraídos (JSON)")
                    st.json(parser.data, expanded=False)
                
                with col2:
                    st.subheader("Download XML")
                    st.download_button(
                        label="📥 Baixar XML Formatado",
                        data=xml_content,
                        file_name=f"DUIMP_{parser.data['header'].get('numeroDUIMP', 'processada').replace('/', '-')}.xml",
                        mime="application/xml"
                    )
                    
                    st.text_area("Prévia do XML", value=xml_content.decode("utf-8"), height=300)

        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
            st.warning("Verifique se o PDF é um Extrato de DUIMP válido.")

else:
    st.markdown("""
    ### Instruções:
    1. Faça upload do extrato da DUIMP em PDF.
    2. O sistema extrairá cabeçalho, pesos, importador e detalhes de cada item.
    3. O XML gerado seguirá a estrutura hierárquica `ListaDeclaracoes > duimp > adicao`.
    """)
