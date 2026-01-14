# app.py - Aplicativo Streamlit para conversão PDF para XML de DUIMP

import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pdfplumber
import re
from datetime import datetime
import json
import os
from typing import Dict, List, Any, Optional
import tempfile
import zipfile
import io

# Configuração da página
st.set_page_config(
    page_title="Conversor DUIMP PDF → XML",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #374151;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #D1FAE5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #10B981;
    }
    .info-box {
        background-color: #DBEAFE;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3B82F6;
    }
    .stButton > button {
        background-color: #3B82F6;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 0.5rem;
    }
    .stButton > button:hover {
        background-color: #2563EB;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-header">🔄 Conversor DUIMP - PDF para XML</h1>', unsafe_allow_html=True)
st.markdown("### Sistema profissional para conversão de extratos DUIMP em formato PDF para XML estruturado")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2936/2936886.png", width=100)
    st.markdown("## Configurações")
    
    st.markdown("### Opções de Processamento")
    validar_xml = st.checkbox("Validar XML gerado", value=True)
    gerar_json = st.checkbox("Gerar JSON intermediário", value=False)
    compactar_output = st.checkbox("Compactar arquivos em ZIP", value=False)
    
    st.markdown("---")
    st.markdown("### Informações")
    st.info("""
    **Formato PDF Suportado:**
    - Layout fixo da DUIMP
    - Até 20 páginas
    - Formato A4
    - Texto extraível
    """)
    
    st.markdown("---")
    st.markdown("### Versão")
    st.caption("v1.0.0 - Desenvolvido para Receita Federal")

# Classes para processamento
class DUIMPProcessor:
    """Processador especializado para DUIMP"""
    
    def __init__(self):
        self.template_xml = self._get_template_structure()
        self.mapping_rules = self._get_mapping_rules()
        
    def _get_template_structure(self) -> Dict:
        """Retorna a estrutura base do XML"""
        return {
            "ListaDeclaracoes": {
                "duimp": {
                    "adicao": [],
                    "dados_gerais": {}
                }
            }
        }
    
    def _get_mapping_rules(self) -> Dict:
        """Regras de mapeamento dos campos do PDF para XML"""
        return {
            "identificacao": {
                "CNPJ do importador": "importadorNumero",
                "Nome do importador": "importadorNome",
                "Endereço do importador": ["importadorEnderecoLogradouro", "importadorEnderecoNumero"],
                "PROCESSO": "informacaoComplementar"
            },
            "dados_operacao": {
                "MOEDA NEGOCIADA": "condicaoVendaMoedaNome",
                "PAIS DE PROCEDENCIA": "cargaPaisProcedenciaNome",
                "VIA DE TRANSPORTE": "viaTransporteNome",
                "DATA DE EMBARQUE": "conhecimentoCargaEmbarqueData",
                "DATA DE CHEGADA": "cargaDataChegada"
            },
            "valores": {
                "VALOR NO LOCAL DE EMBARQUE": "localEmbarqueTotalReais",
                "VALOR ADUANEIRO": "localDescargaTotalReais",
                "VALOR DO FRETE": "freteTotalReais"
            },
            "tributos": {
                "II": "iiAliquotaValorRecolher",
                "PIS": "pisPasepAliquotaValorRecolher",
                "COFINS": "cofinsAliquotaValorRecolher",
                "TAXA DE UTILIZACAO": "valorReceita"
            }
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extrai texto do PDF organizado por seções"""
        extracted_data = {
            "identificacao": {},
            "dados_gerais": {},
            "mercadorias": [],
            "tributos": {},
            "historico": []
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        self._process_page_text(text, extracted_data, page_num)
                        
        except Exception as e:
            st.error(f"Erro ao extrair texto do PDF: {str(e)}")
            return None
            
        return extracted_data
    
    def _process_page_text(self, text: str, data: Dict, page_num: int):
        """Processa o texto de uma página"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Identificação básica
            if "CNPJ do importador:" in line:
                data["identificacao"]["CNPJ"] = self._extract_value(line, "CNPJ do importador:")
            
            elif "Nome do importador:" in line:
                data["identificacao"]["Nome"] = self._extract_value(line, "Nome do importador:")
            
            elif "PROCESSO :" in line:
                data["identificacao"]["Processo"] = self._extract_value(line, "PROCESSO :")
            
            # Dados da operação
            elif "MOEDA NEGOCIADA :" in line:
                data["dados_gerais"]["Moeda"] = self._extract_value(line, "MOEDA NEGOCIADA :")
            
            elif "PAIS DE PROCEDENCIA :" in line:
                data["dados_gerais"]["Pais"] = self._extract_value(line, "PAIS DE PROCEDENCIA :")
            
            elif "VIA DE TRANSPORTE :" in line:
                data["dados_gerais"]["Transporte"] = self._extract_value(line, "VIA DE TRANSPORTE :")
            
            # Valores
            elif "VALOR NO LOCAL DE EMBARQUE (VMLE) :" in line:
                data["dados_gerais"]["ValorEmbarque"] = self._extract_numeric_value(line)
            
            elif "VALOR ADUANEIRO/LOCAL DE DESTINO (VMLD) :" in line:
                data["dados_gerais"]["ValorDestino"] = self._extract_numeric_value(line)
            
            elif "VALOR DO FRETE :" in line:
                data["dados_gerais"]["Frete"] = self._extract_numeric_value(line)
            
            # Tributos
            elif "II :" in line:
                data["tributos"]["II"] = self._extract_numeric_value(line)
            
            elif "PIS :" in line:
                data["tributos"]["PIS"] = self._extract_numeric_value(line)
            
            elif "COFINS :" in line:
                data["tributos"]["COFINS"] = self._extract_numeric_value(line)
            
            # Mercadorias
            elif "Item 0000" in line or "Mercadoria" in line:
                if i + 1 < len(lines):
                    mercadoria = self._extract_mercadoria(lines[i:i+10])
                    if mercadoria:
                        data["mercadorias"].append(mercadoria)
        
        # Processar histórico
        self._process_historico(text, data)
    
    def _extract_value(self, line: str, key: str) -> str:
        """Extrai valor após uma chave"""
        try:
            return line.split(key)[1].strip()
        except:
            return ""
    
    def _extract_numeric_value(self, line: str) -> str:
        """Extrai valor numérico de uma linha"""
        match = re.search(r'[\d.,]+', line)
        if match:
            return match.group().replace('.', '').replace(',', '.')
        return "0"
    
    def _extract_mercadoria(self, lines: List[str]) -> Optional[Dict]:
        """Extrai dados de uma mercadoria"""
        mercadoria = {}
        
        for line in lines:
            if "NCM:" in line:
                mercadoria["NCM"] = self._extract_value(line, "NCM:")
            elif "Quantidade na unidade estatística:" in line:
                mercadoria["Quantidade"] = self._extract_numeric_value(line)
            elif "Valor total na condição de venda:" in line:
                mercadoria["ValorTotal"] = self._extract_numeric_value(line)
        
        return mercadoria if mercadoria else None
    
    def _process_historico(self, text: str, data: Dict):
        """Processa o histórico da DUIMP"""
        historico_pattern = r'(\d{2}/\d{2}/\d{4}, \d{2}:\d{2})\s+(.+?)\s+(\d{2}\.\d{3}\.\d{3}-\d{2}|\w+)$'
        matches = re.findall(historico_pattern, text, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            data["historico"].append({
                "data_hora": match[0],
                "evento": match[1].strip(),
                "responsavel": match[2]
            })
    
    def create_xml_structure(self, data: Dict) -> ET.Element:
        """Cria a estrutura XML completa a partir dos dados extraídos"""
        
        # Criar elemento raiz
        root = ET.Element("ListaDeclaracoes")
        duimp = ET.SubElement(root, "duimp")
        
        # Adicionar número da DUIMP
        numero_duimp = ET.SubElement(duimp, "numeroDUIMP")
        numero_duimp.text = data.get("identificacao", {}).get("Processo", "000000000000")
        
        # Adicionar dados do importador
        importador_numero = ET.SubElement(duimp, "importadorNumero")
        importador_numero.text = data.get("identificacao", {}).get("CNPJ", "00000000000000")
        
        importador_nome = ET.SubElement(duimp, "importadorNome")
        importador_nome.text = data.get("identificacao", {}).get("Nome", "")
        
        # Adicionar dados gerais
        via_transporte = ET.SubElement(duimp, "viaTransporteNome")
        via_transporte.text = data.get("dados_gerais", {}).get("Transporte", "MARÍTIMA")
        
        carga_pais = ET.SubElement(duimp, "cargaPaisProcedenciaNome")
        carga_pais.text = data.get("dados_gerais", {}).get("Pais", "")
        
        # Adicionar valores
        local_embarque = ET.SubElement(duimp, "localEmbarqueTotalReais")
        local_embarque.text = self._format_number(data.get("dados_gerais", {}).get("ValorEmbarque", "0"))
        
        local_descarga = ET.SubElement(duimp, "localDescargaTotalReais")
        local_descarga.text = self._format_number(data.get("dados_gerais", {}).get("ValorDestino", "0"))
        
        frete_total = ET.SubElement(duimp, "freteTotalReais")
        frete_total.text = self._format_number(data.get("dados_gerais", {}).get("Frete", "0"))
        
        # Adicionar adições (mercadorias)
        for idx, merc in enumerate(data.get("mercadorias", []), 1):
            adicao = ET.SubElement(duimp, "adicao")
            
            numero_adicao = ET.SubElement(adicao, "numeroAdicao")
            numero_adicao.text = f"{idx:03d}"
            
            # Dados da mercadoria
            mercadoria_elem = ET.SubElement(adicao, "mercadoria")
            
            descricao = ET.SubElement(mercadoria_elem, "descricaoMercadoria")
            descricao.text = merc.get("Descricao", f"Mercadoria {idx}")
            
            ncm = ET.SubElement(mercadoria_elem, "dadosMercadoriaCodigoNcm")
            ncm.text = merc.get("NCM", "00000000")
            
            quantidade = ET.SubElement(mercadoria_elem, "quantidade")
            quantidade.text = self._format_number(merc.get("Quantidade", "0"), 14)
            
            valor_total = ET.SubElement(adicao, "valorTotalCondicaoVenda")
            valor_total.text = self._format_number(merc.get("ValorTotal", "0"), 11)
        
        # Adicionar tributos
        ii_valor = ET.SubElement(duimp, "iiAliquotaValorRecolher")
        ii_valor.text = self._format_number(data.get("tributos", {}).get("II", "0"), 15)
        
        pis_valor = ET.SubElement(duimp, "pisPasepAliquotaValorRecolher")
        pis_valor.text = self._format_number(data.get("tributos", {}).get("PIS", "0"), 15)
        
        cofins_valor = ET.SubElement(duimp, "cofinsAliquotaValorRecolher")
        cofins_valor.text = self._format_number(data.get("tributos", {}).get("COFINS", "0"), 15)
        
        # Informações complementares
        info_comp = ET.SubElement(duimp, "informacaoComplementar")
        info_text = f"PROCESSO: {data.get('identificacao', {}).get('Processo', '')}\n"
        info_text += f"EXTRATO DUIMP GERADO EM: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        info_comp.text = info_text
        
        # Elementos obrigatórios adicionais
        elementos_obrigatorios = {
            "totalAdicoes": f"{len(data.get('mercadorias', [])):03d}",
            "tipoDeclaracaoCodigo": "01",
            "tipoDeclaracaoNome": "CONSUMO",
            "modalidadeDespachoCodigo": "1",
            "modalidadeDespachoNome": "Normal",
            "sequencialRetificacao": "00",
            "operacaoFundap": "N",
            "viaTransporteCodigo": "01",
            "viaTransporteMultimodal": "N",
            "caracterizacaoOperacaoCodigoTipo": "1",
            "caracterizacaoOperacaoDescricaoTipo": "Importação Própria",
            "canalSelecaoParametrizada": "001"
        }
        
        for elem, valor in elementos_obrigatorios.items():
            elemento = ET.SubElement(duimp, elem)
            elemento.text = valor
        
        return root
    
    def _format_number(self, value: str, length: int = 15) -> str:
        """Formata número para o padrão XML (zeros à esquerda)"""
        try:
            # Remove caracteres não numéricos, exceto ponto
            clean_value = re.sub(r'[^\d.]', '', str(value))
            num = float(clean_value)
            # Converte para centavos (2 casas decimais)
            cents = int(num * 100)
            return str(cents).zfill(length)
        except:
            return "0".zfill(length)
    
    def validate_xml(self, xml_string: str) -> bool:
        """Valida o XML gerado"""
        try:
            ET.fromstring(xml_string)
            return True
        except ET.ParseError as e:
            st.error(f"Erro na validação XML: {str(e)}")
            return False
    
    def pretty_xml(self, element: ET.Element) -> str:
        """Retorna XML formatado de forma legível"""
        rough_string = ET.tostring(element, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def save_to_file(self, xml_string: str, filename: str):
        """Salva XML em arquivo"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml_string)

class StreamlitApp:
    """Classe principal da aplicação Streamlit"""
    
    def __init__(self):
        self.processor = DUIMPProcessor()
        self.uploaded_file = None
        self.extracted_data = None
        
    def render_header(self):
        """Renderiza o cabeçalho da aplicação"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="info-box">
            <h4>📋 Instruções de Uso:</h4>
            <ol>
                <li>Faça upload do PDF da DUIMP</li>
                <li>Aguarde o processamento automático</li>
                <li>Revise os dados extraídos</li>
                <li>Baixe o XML gerado</li>
            </ol>
            </div>
            """, unsafe_allow_html=True)
    
    def upload_section(self):
        """Seção de upload de arquivo"""
        st.markdown('<h3 class="sub-header">1. Upload do Arquivo PDF</h3>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo PDF da DUIMP",
            type=['pdf'],
            help="Somente arquivos PDF com layout fixo da DUIMP"
        )
        
        if uploaded_file is not None:
            self.uploaded_file = uploaded_file
            
            # Salvar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                self.temp_pdf_path = tmp_file.name
            
            # Exibir informações do arquivo
            file_info = uploaded_file.__dict__
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Tamanho do arquivo", f"{uploaded_file.size / 1024:.2f} KB")
            with col2:
                st.metric("Tipo", uploaded_file.type)
            
            return True
        
        return False
    
    def process_pdf(self):
        """Processa o PDF e extrai dados"""
        st.markdown('<h3 class="sub-header">2. Processamento e Extração</h3>', unsafe_allow_html=True)
        
        with st.spinner("Processando PDF... Isso pode levar alguns segundos."):
            progress_bar = st.progress(0)
            
            # Extrair dados
            self.extracted_data = self.processor.extract_text_from_pdf(self.temp_pdf_path)
            progress_bar.progress(50)
            
            if self.extracted_data:
                # Criar XML
                xml_structure = self.processor.create_xml_structure(self.extracted_data)
                self.xml_string = self.processor.pretty_xml(xml_structure)
                progress_bar.progress(100)
                
                return True
            else:
                st.error("Não foi possível extrair dados do PDF.")
                return False
    
    def display_extracted_data(self):
        """Exibe os dados extraídos para revisão"""
        st.markdown('<h3 class="sub-header">3. Dados Extraídos</h3>', unsafe_allow_html=True)
        
        if self.extracted_data:
            # Criar abas para diferentes seções
            tab1, tab2, tab3, tab4 = st.tabs([
                "📋 Identificação", 
                "📦 Mercadorias", 
                "💰 Valores", 
                "📊 Tributos"
            ])
            
            with tab1:
                self._display_identificacao()
            
            with tab2:
                self._display_mercadorias()
            
            with tab3:
                self._display_valores()
            
            with tab4:
                self._display_tributos()
    
    def _display_identificacao(self):
        """Exibe dados de identificação"""
        ident = self.extracted_data.get("identificacao", {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("**Importador**")
            st.write(f"**CNPJ:** {ident.get('CNPJ', 'Não encontrado')}")
            st.write(f"**Nome:** {ident.get('Nome', 'Não encontrado')}")
            st.write(f"**Processo:** {ident.get('Processo', 'Não encontrado')}")
        
        with col2:
            st.info("**Operação**")
            dados_gerais = self.extracted_data.get("dados_gerais", {})
            st.write(f"**Moeda:** {dados_gerais.get('Moeda', 'Não encontrado')}")
            st.write(f"**País:** {dados_gerais.get('Pais', 'Não encontrado')}")
            st.write(f"**Transporte:** {dados_gerais.get('Transporte', 'Não encontrado')}")
    
    def _display_mercadorias(self):
        """Exibe dados das mercadorias"""
        mercadorias = self.extracted_data.get("mercadorias", [])
        
        if mercadorias:
            df_data = []
            for i, merc in enumerate(mercadorias, 1):
                df_data.append({
                    "Item": i,
                    "NCM": merc.get("NCM", "00000000"),
                    "Quantidade": merc.get("Quantidade", "0"),
                    "Valor Total": f"R$ {float(merc.get('ValorTotal', 0)):,.2f}"
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            st.metric("Total de Itens", len(mercadorias))
        else:
            st.warning("Nenhuma mercadoria encontrada no PDF")
    
    def _display_valores(self):
        """Exibe valores financeiros"""
        dados = self.extracted_data.get("dados_gerais", {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            valor_emb = float(dados.get("ValorEmbarque", 0))
            st.metric("Valor no Embarque", f"R$ {valor_emb:,.2f}")
        
        with col2:
            valor_dest = float(dados.get("ValorDestino", 0))
            st.metric("Valor no Destino", f"R$ {valor_dest:,.2f}")
        
        with col3:
            frete = float(dados.get("Frete", 0))
            st.metric("Frete", f"R$ {frete:,.2f}")
    
    def _display_tributos(self):
        """Exibe dados tributários"""
        tributos = self.extracted_data.get("tributos", {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            ii = float(tributos.get("II", 0))
            st.metric("Imposto de Importação", f"R$ {ii:,.2f}")
        
        with col2:
            pis = float(tributos.get("PIS", 0))
            st.metric("PIS", f"R$ {pis:,.2f}")
        
        with col3:
            cofins = float(tributos.get("COFINS", 0))
            st.metric("COFINS", f"R$ {cofins:,.2f}")
        
        with col4:
            total = ii + pis + cofins
            st.metric("Total Tributos", f"R$ {total:,.2f}")
    
    def generate_output_files(self):
        """Gera e disponibiliza os arquivos de saída"""
        st.markdown('<h3 class="sub-header">4. Download dos Arquivos</h3>', unsafe_allow_html=True)
        
        if hasattr(self, 'xml_string'):
            # Validar XML se necessário
            if st.session_state.get('validar_xml', True):
                if self.processor.validate_xml(self.xml_string):
                    st.success("✅ XML validado com sucesso!")
                else:
                    st.error("❌ XML com problemas de formatação")
            
            # Exibir preview do XML
            with st.expander("📄 Visualizar XML Gerado"):
                st.code(self.xml_string, language='xml')
            
            # Botões de download
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Download XML
                st.download_button(
                    label="📥 Baixar XML",
                    data=self.xml_string,
                    file_name=f"DUIMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
                    mime="application/xml",
                    help="Download do arquivo XML no layout obrigatório"
                )
            
            with col2:
                # Download JSON (se habilitado)
                if st.session_state.get('gerar_json', False):
                    json_data = json.dumps(self.extracted_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📥 Baixar JSON",
                        data=json_data,
                        file_name=f"DUIMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            
            with col3:
                # Download ZIP (se habilitado)
                if st.session_state.get('compactar_output', False):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        zip_file.writestr(
                            f"DUIMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
                            self.xml_string
                        )
                        
                        if st.session_state.get('gerar_json', False):
                            json_data = json.dumps(self.extracted_data, indent=2, ensure_ascii=False)
                            zip_file.writestr(
                                f"DUIMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                json_data
                            )
                    
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label="📦 Baixar ZIP",
                        data=zip_buffer,
                        file_name=f"DUIMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip"
                    )
            
            # Estatísticas
            st.markdown("---")
            self._display_statistics()
    
    def _display_statistics(self):
        """Exibe estatísticas do processamento"""
        st.markdown("### 📊 Estatísticas do Processamento")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            merc_count = len(self.extracted_data.get("mercadorias", []))
            st.metric("Mercadorias Processadas", merc_count)
        
        with col2:
            xml_size = len(self.xml_string.encode('utf-8'))
            st.metric("Tamanho do XML", f"{xml_size / 1024:.1f} KB")
        
        with col3:
            historico_count = len(self.extracted_data.get("historico", []))
            st.metric("Eventos Históricos", historico_count)
        
        with col4:
            st.metric("Status", "✅ Concluído")
    
    def run(self):
        """Executa a aplicação completa"""
        self.render_header()
        
        # Passo 1: Upload
        if self.upload_section():
            # Passo 2: Processamento
            if st.button("🔍 Processar PDF", type="primary"):
                if self.process_pdf():
                    # Passo 3: Exibir dados
                    self.display_extracted_data()
                    
                    # Passo 4: Gerar arquivos
                    self.generate_output_files()
        
        # Rodapé
        st.markdown("---")
        st.caption("""
        **Sistema desenvolvido para conversão de DUIMP** | 
        Compatível com layout fixo da Receita Federal |
        © 2024 - Todos os direitos reservados
        """)

# Executar aplicação
if __name__ == "__main__":
    app = StreamlitApp()
    app.run()
