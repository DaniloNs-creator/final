import streamlit as st
import fitz  # PyMuPDF
from lxml import etree
import re
import io

# ==============================================================================
# 1. CLASSE DE EXTRAÇÃO E PROCESSAMENTO (CORE LÓGICO)
# ==============================================================================

class DuimpPdfProcessor:
    def __init__(self, pdf_bytes):
        self.doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        self.data = {
            "header": {},
            "adicoes": [],
            "footer": {}
        }
    
    def extract_text_optimized(self):
        """
        Extrai texto de forma otimizada para performance em arquivos grandes.
        """
        full_text = ""
        # Itera sobre as páginas com barra de progresso no frontend
        progress_bar = st.progress(0)
        total_pages = len(self.doc)
        
        for i, page in enumerate(self.doc):
            # Extrai texto preservando layout físico aproximado
            full_text += page.get_text("text") + "\n"
            
            # Atualiza barra a cada 10 páginas para não travar a UI
            if i % 10 == 0:
                progress_bar.progress((i + 1) / total_pages)
        
        progress_bar.progress(100)
        return full_text

    def parse_data(self):
        text = self.extract_text_optimized()
        
        # --- REGEX PATTERNS (Adaptados para o padrão visual do extrato DUIMP) ---
        # Estes padrões buscam os rótulos comuns em PDFs de extrato Siscomex
        
        # 1. Dados Gerais (Header)
        self.data['header']['numeroDUIMP'] = self._find_value(r"DUIMP\s*[:]\s*(\d+[\.\d]*)", text)
        self.data['header']['importadorNome'] = self._find_value(r"Importador\s*[:]\s*(.+?)\n", text)
        self.data['header']['viaTransporteNome'] = self._find_value(r"Via de Transporte\s*[:]\s*(.+?)\n", text)
        self.data['header']['cargaPesoLiquido'] = self._find_value(r"Peso Líquido Total\s*[:]\s*([\d,\.]+)", text)
        self.data['header']['cargaPesoBruto'] = self._find_value(r"Peso Bruto Total\s*[:]\s*([\d,\.]+)", text)
        
        # 2. Iteração sobre Adições (Lógica Complexa de Múltiplos Itens)
        # Dividimos o texto pelos blocos de "Número da Adição" ou similar
        adicao_blocks = re.split(r"Adição\s*n[º°]?\s*", text)
        
        if len(adicao_blocks) > 1:
            # O primeiro bloco geralmente é cabeçalho, ignoramos ou processamos separado
            for block in adicao_blocks[1:]:
                adicao_data = {}
                
                # Extrai número da adição (estará logo no início do bloco)
                adicao_num_match = re.match(r"^(\d+)", block)
                if adicao_num_match:
                    adicao_data['numeroAdicao'] = adicao_num_match.group(1).zfill(3)
                
                # Extrai dados específicos da adição dentro deste bloco
                adicao_data['ncm'] = self._find_value(r"NCM\s*[:]\s*(\d+)", block)
                adicao_data['valorReais'] = self._find_value(r"Valor na Condição de Venda \(R\$\)\s*[:]\s*([\d,\.]+)", block)
                adicao_data['incoterm'] = self._find_value(r"Incoterm\s*[:]\s*([A-Z]{3})", block)
                
                # Limpeza de formatação numérica (Remove pontos de milhar, troca vírgula por ponto se necessário)
                # OBS: Para o XML SAP, muitas vezes é sem ponto decimal, apenas string numérica.
                # Ajuste conforme necessidade do SAP aqui.
                
                self.data['adicoes'].append(adicao_data)

        return self.data

    def _find_value(self, pattern, text):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "000000" # Valor default para evitar quebra do XML

# ==============================================================================
# 2. GERADOR DE XML (ESTRUTURA RÍGIDA SAP)
# ==============================================================================

def format_currency_sap(value_str):
    """
    Formata valores monetários para o padrão SAP (ex: remove pontuação, ajusta zeros).
    Entrada: '1.234,56' -> Saída XML (exemplo): '00000000123456'
    Este formatador deve ser ajustado conforme a regra exata do seu SAP.
    """
    if not value_str: return "000000000000000"
    clean = re.sub(r'[^\d]', '', value_str)
    return clean.zfill(15) # Exemplo de padding de 15 dígitos

def create_xml(data):
    # Root
    root = etree.Element("ListaDeclaracoes")
    duimp = etree.SubElement(root, "duimp")

    # --- Loop de Adições ---
    # O XML deve seguir a ordem: Adições primeiro, depois dados gerais (conforme seu layout anterior)
    for item in data['adicoes']:
        adicao = etree.SubElement(duimp, "adicao")
        
        # Subtags da Adição (Sequência Obrigatória do seu layout)
        # Exemplo de mapeamento:
        
        # Acrescimo
        acrescimo = etree.SubElement(adicao, "acrescimo")
        etree.SubElement(acrescimo, "codigoAcrescimo").text = "17" # Fixo ou extraído
        etree.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        
        # Tributos (Mockados ou extraídos se disponíveis no bloco da adição)
        etree.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
        
        # Mercadoria
        mercadoria = etree.SubElement(adicao, "mercadoria")
        # Tenta pegar NCM extraída, senão usa padrão
        etree.SubElement(mercadoria, "dadosMercadoriaCodigoNcm").text = item.get('ncm', '00000000')
        etree.SubElement(mercadoria, "numeroSequencialItem").text = "01"
        
        # Dados de identificação da adição
        etree.SubElement(adicao, "numeroAdicao").text = item.get('numeroAdicao', '000')
        etree.SubElement(adicao, "numeroDUIMP").text = data['header'].get('numeroDUIMP', '0000000000')
        
        # Dados de Venda
        etree.SubElement(adicao, "condicaoVendaIncoterm").text = item.get('incoterm', 'FCA')
        etree.SubElement(adicao, "condicaoVendaValorReais").text = format_currency_sap(item.get('valorReais'))

    # --- Dados Gerais da DUIMP (Fora do loop de adições) ---
    # Armazem
    armazem = etree.SubElement(duimp, "armazem")
    etree.SubElement(armazem, "nomeArmazem").text = "TCP" # Exemplo fixo ou extraído
    
    # Carga
    etree.SubElement(duimp, "cargaPesoBruto").text = format_currency_sap(data['header'].get('cargaPesoBruto'))
    etree.SubElement(duimp, "cargaPesoLiquido").text = format_currency_sap(data['header'].get('cargaPesoLiquido'))
    etree.SubElement(duimp, "numeroDUIMP").text = data['header'].get('numeroDUIMP')
    
    # Importador
    etree.SubElement(duimp, "importadorNome").text = data['header'].get('importadorNome')
    
    # Pagamentos (Exemplo de estrutura fixa ou iterada se extrair do rodapé)
    pagamento = etree.SubElement(duimp, "pagamento")
    etree.SubElement(pagamento, "codigoReceita").text = "0086"
    etree.SubElement(pagamento, "nomeTipoPagamento").text = "Débito em Conta"

    # Retorna XML string com identação
    return etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# ==============================================================================
# 3. INTERFACE STREAMLIT
# ==============================================================================

def main():
    st.set_page_config(page_title="Conversor DUIMP PDF -> SAP XML", layout="wide")
    
    st.title("📄 Conversor de Extrato DUIMP para XML (SAP)")
    st.markdown("""
    Esta ferramenta processa extratos de conferência de importação (DUIMP) e gera o XML estrito para integração SAP.
    **Capacidade:** Processamento otimizado para arquivos grandes (500+ páginas).
    """)

    uploaded_file = st.file_uploader("Carregue o Extrato DUIMP (PDF)", type=["pdf"])

    if uploaded_file is not None:
        st.success("Arquivo carregado com sucesso!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Processar e Gerar XML"):
                try:
                    with st.spinner("Lendo PDF e estruturando dados..."):
                        # Ler arquivo para memória
                        pdf_bytes = uploaded_file.read()
                        
                        # Processar
                        processor = DuimpPdfProcessor(pdf_bytes)
                        parsed_data = processor.parse_data()
                        
                        # Gerar XML
                        xml_bytes = create_xml(parsed_data)
                        
                        st.session_state['xml_output'] = xml_bytes
                        st.session_state['parsed_preview'] = parsed_data
                        
                    st.success("Processamento concluído!")
                
                except Exception as e:
                    st.error(f"Erro durante o processamento: {e}")

        # Área de Download e Preview
        if 'xml_output' in st.session_state:
            with col2:
                st.download_button(
                    label="⬇️ Baixar XML Formatado",
                    data=st.session_state['xml_output'],
                    file_name=f"DUIMP_{st.session_state['parsed_preview']['header'].get('numeroDUIMP', 'gerada')}.xml",
                    mime="application/xml"
                )
            
            st.divider()
            st.subheader("Pré-visualização dos Dados Extraídos")
            st.json(st.session_state['parsed_preview'])
            
            with st.expander("Ver XML Gerado (Snippet)"):
                st.code(st.session_state['xml_output'][:2000].decode("utf-8"), language='xml')

if __name__ == "__main__":
    main()
