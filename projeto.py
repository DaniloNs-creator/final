# app.py - Aplicativo Streamlit para conversão PDF para XML de DUIMP (Versão Corrigida)

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
    .error-box {
        background-color: #FEE2E2;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #EF4444;
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
    st.caption("v1.0.1 - Desenvolvido para Receita Federal")

class DUIMPProcessor:
    """Processador especializado para DUIMP - Versão Corrigida"""
    
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
        """Extrai texto do PDF organizado por seções - Versão corrigida"""
        extracted_data = {
            "identificacao": {},
            "dados_gerais": {},
            "mercadorias": [],
            "tributos": {},
            "historico": []
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                all_text = ""
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"
                
                # Processar todo o texto de uma vez
                if all_text:
                    self._process_complete_text(all_text, extracted_data)
                        
        except Exception as e:
            st.error(f"Erro ao extrair texto do PDF: {str(e)}")
            return None
            
        return extracted_data
    
    def _process_complete_text(self, text: str, data: Dict):
        """Processa todo o texto de uma vez - mais robusto"""
        lines = text.split('\n')
        
        # Padrões de busca mais flexíveis
        patterns = {
            "cnpj": r"CNPJ\s*do\s*importador\s*:?\s*([\d./-]+)",
            "nome": r"Nome\s*do\s*importador\s*:?\s*(.+)",
            "processo": r"PROCESSO\s*:?\s*(\d+)",
            "moeda": r"MOEDA\s*NEGOCIADA\s*:?\s*(.+)",
            "pais": r"PAIS\s*DE\s*PROCEDENCIA\s*:?\s*(.+)",
            "transporte": r"VIA\s*DE\s*TRANSPORTE\s*:?\s*(.+)",
            "embarque": r"DATA\s*DE\s*EMBARQUE\s*:?\s*(\d{2}/\d{2}/\d{4})",
            "chegada": r"DATA\s*DE\s*CHEGADA\s*:?\s*(\d{2}/\d{2}/\d{4})",
            "valor_embarque": r"VALOR\s*NO\s*LOCAL\s*DE\s*EMBARQUE.*?:\s*([\d.,]+)",
            "valor_destino": r"VALOR\s*ADUANEIRO.*?:\s*([\d.,]+)",
            "frete": r"VALOR\s*DO\s*FRETE.*?:\s*([\d.,]+)",
            "ii": r"II\s*:?\s*([\d.,]+)",
            "pis": r"PIS\s*:?\s*([\d.,]+)",
            "cofins": r"COFINS\s*:?\s*([\d.,]+)"
        }
        
        # Processar cada linha com os padrões
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Buscar CNPJ
            match = re.search(patterns["cnpj"], line, re.IGNORECASE)
            if match:
                data["identificacao"]["CNPJ"] = match.group(1)
                continue
            
            # Buscar Nome do Importador
            match = re.search(patterns["nome"], line)
            if match and len(line) < 100:  # Evitar pegar linhas muito longas
                data["identificacao"]["Nome"] = match.group(1).strip()
                continue
            
            # Buscar Processo
            match = re.search(patterns["processo"], line)
            if match:
                data["identificacao"]["Processo"] = match.group(1)
                continue
            
            # Buscar Moeda
            match = re.search(patterns["moeda"], line)
            if match:
                data["dados_gerais"]["Moeda"] = match.group(1)
                continue
            
            # Buscar País
            match = re.search(patterns["pais"], line)
            if match:
                data["dados_gerais"]["Pais"] = match.group(1)
                continue
            
            # Buscar Transporte
            match = re.search(patterns["transporte"], line)
            if match:
                data["dados_gerais"]["Transporte"] = match.group(1)
                continue
            
            # Buscar datas
            match = re.search(patterns["embarque"], line)
            if match:
                data["dados_gerais"]["DataEmbarque"] = match.group(1)
                continue
            
            match = re.search(patterns["chegada"], line)
            if match:
                data["dados_gerais"]["DataChegada"] = match.group(1)
                continue
            
            # Buscar valores financeiros
            match = re.search(patterns["valor_embarque"], line)
            if match:
                data["dados_gerais"]["ValorEmbarque"] = self._clean_numeric_value(match.group(1))
                continue
            
            match = re.search(patterns["valor_destino"], line)
            if match:
                data["dados_gerais"]["ValorDestino"] = self._clean_numeric_value(match.group(1))
                continue
            
            match = re.search(patterns["frete"], line)
            if match:
                data["dados_gerais"]["Frete"] = self._clean_numeric_value(match.group(1))
                continue
            
            # Buscar tributos
            match = re.search(patterns["ii"], line)
            if match:
                data["tributos"]["II"] = self._clean_numeric_value(match.group(1))
                continue
            
            match = re.search(patterns["pis"], line)
            if match:
                data["tributos"]["PIS"] = self._clean_numeric_value(match.group(1))
                continue
            
            match = re.search(patterns["cofins"], line)
            if match:
                data["tributos"]["COFINS"] = self._clean_numeric_value(match.group(1))
                continue
        
        # Extrair mercadorias usando abordagem mais robusta
        self._extract_mercadorias_robust(text, data)
        
        # Extrair histórico
        self._extract_historico_robust(text, data)
        
        # Debug: mostrar dados extraídos
        st.write("### Dados extraídos para depuração:")
        st.json(data)
    
    def _clean_numeric_value(self, value: str) -> str:
        """Limpa e converte valor numérico"""
        try:
            # Remove pontos de milhar e converte vírgula para ponto
            clean = value.replace('.', '').replace(',', '.')
            return str(float(clean))
        except:
            return "0.00"
    
    def _extract_mercadorias_robust(self, text: str, data: Dict):
        """Extrai dados das mercadorias de forma mais robusta"""
        # Padrões para encontrar mercadorias
        mercadoria_sections = re.split(r'Item 0000\d|Mercadoria', text)
        
        for section in mercadoria_sections[1:]:  # Ignorar primeira seção
            mercadoria = {}
            
            # Buscar NCM
            ncm_match = re.search(r'NCM:\s*(\d{4}\.\d{2}\.\d{2})', section)
            if ncm_match:
                mercadoria["NCM"] = ncm_match.group(1).replace('.', '')
            
            # Buscar quantidade
            qtd_match = re.search(r'Quantidade.*?(\d+[\.,]?\d*)', section)
            if qtd_match:
                mercadoria["Quantidade"] = self._clean_numeric_value(qtd_match.group(1))
            
            # Buscar valor total
            valor_match = re.search(r'Valor total.*?(\d+[\.,]?\d*)', section)
            if valor_match:
                mercadoria["ValorTotal"] = self._clean_numeric_value(valor_match.group(1))
            
            # Buscar descrição
            desc_match = re.search(r'Código do produto:\s*\d+\s*-\s*(.+?)(?:\n|$)', section)
            if desc_match:
                mercadoria["Descricao"] = desc_match.group(1).strip()
            
            if mercadoria:  # Só adicionar se encontrou algo
                data["mercadorias"].append(mercadoria)
    
    def _extract_historico_robust(self, text: str, data: Dict):
        """Extrai histórico de forma mais robusta"""
        historico_pattern = r'(\d{2}/\d{2}/\d{4},?\s*\d{2}:\d{2})\s+(.+?)\s+(\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2}|\w+)'
        matches = re.findall(historico_pattern, text, re.MULTILINE)
        
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
        
        # Adicionar número da DUIMP (usar processo ou gerar)
        numero_duimp = ET.SubElement(duimp, "numeroDUIMP")
        processo = data.get("identificacao", {}).get("Processo", "")
        if processo:
            numero_duimp.text = processo
        else:
            numero_duimp.text = "25BR" + datetime.now().strftime("%y%m%d") + "000001"
        
        # Adicionar dados do importador
        importador_numero = ET.SubElement(duimp, "importadorNumero")
        cnpj = data.get("identificacao", {}).get("CNPJ", "")
        importador_numero.text = self._clean_cnpj(cnpj) if cnpj else "00000000000000"
        
        importador_nome = ET.SubElement(duimp, "importadorNome")
        nome = data.get("identificacao", {}).get("Nome", "")
        importador_nome.text = nome if nome else "IMPORTADOR NAO IDENTIFICADO"
        
        # Adicionar endereço básico
        importador_endereco = ET.SubElement(duimp, "importadorEnderecoLogradouro")
        importador_endereco.text = "ENDEREÇO NAO IDENTIFICADO"
        
        importador_numero_end = ET.SubElement(duimp, "importadorEnderecoNumero")
        importador_numero_end.text = "S/N"
        
        importador_municipio = ET.SubElement(duimp, "importadorEnderecoMunicipio")
        importador_municipio.text = "MUNICIPIO NAO IDENTIFICADO"
        
        importador_uf = ET.SubElement(duimp, "importadorEnderecoUf")
        importador_uf.text = "UF"
        
        importador_cep = ET.SubElement(duimp, "importadorEnderecoCep")
        importador_cep.text = "00000000"
        
        # Adicionar dados gerais
        via_transporte = ET.SubElement(duimp, "viaTransporteNome")
        transporte = data.get("dados_gerais", {}).get("Transporte", "MARÍTIMA")
        via_transporte.text = transporte if transporte else "MARÍTIMA"
        
        carga_pais = ET.SubElement(duimp, "cargaPaisProcedenciaNome")
        pais = data.get("dados_gerais", {}).get("Pais", "")
        carga_pais.text = pais if pais else "PAIS NAO IDENTIFICADO"
        
        # Adicionar valores financeiros
        local_embarque = ET.SubElement(duimp, "localEmbarqueTotalReais")
        valor_emb = data.get("dados_gerais", {}).get("ValorEmbarque", "0")
        local_embarque.text = self._format_number(valor_emb)
        
        local_descarga = ET.SubElement(duimp, "localDescargaTotalReais")
        valor_dest = data.get("dados_gerais", {}).get("ValorDestino", "0")
        local_descarga.text = self._format_number(valor_dest)
        
        frete_total = ET.SubElement(duimp, "freteTotalReais")
        frete = data.get("dados_gerais", {}).get("Frete", "0")
        frete_total.text = self._format_number(frete)
        
        # Adicionar datas
        if data.get("dados_gerais", {}).get("DataEmbarque"):
            embarque_date = ET.SubElement(duimp, "conhecimentoCargaEmbarqueData")
            data_emb = data["dados_gerais"]["DataEmbarque"]
            embarque_date.text = self._format_date(data_emb)
        
        if data.get("dados_gerais", {}).get("DataChegada"):
            chegada_date = ET.SubElement(duimp, "cargaDataChegada")
            data_cheg = data["dados_gerais"]["DataChegada"]
            chegada_date.text = self._format_date(data_cheg)
        
        # Adicionar adições (mercadorias)
        mercadorias = data.get("mercadorias", [])
        for idx, merc in enumerate(mercadorias, 1):
            adicao = ET.SubElement(duimp, "adicao")
            
            numero_adicao = ET.SubElement(adicao, "numeroAdicao")
            numero_adicao.text = f"{idx:03d}"
            
            # Dados da mercadoria
            mercadoria_elem = ET.SubElement(adicao, "mercadoria")
            
            descricao = ET.SubElement(mercadoria_elem, "descricaoMercadoria")
            descricao.text = merc.get("Descricao", f"Mercadoria {idx}")
            
            # Dados NCM
            dados_merc = ET.SubElement(adicao, "dadosMercadoriaCodigoNcm")
            dados_merc.text = merc.get("NCM", "00000000")
            
            quantidade = ET.SubElement(mercadoria_elem, "quantidade")
            qtd = merc.get("Quantidade", "0")
            quantidade.text = self._format_number(qtd, 14)
            
            valor_unitario = ET.SubElement(mercadoria_elem, "valorUnitario")
            # Calcular valor unitário aproximado
            try:
                valor_total = float(merc.get("ValorTotal", "0"))
                qtd_num = float(qtd)
                if qtd_num > 0:
                    unitario = valor_total / qtd_num
                else:
                    unitario = 0
                valor_unitario.text = self._format_number(str(unitario), 20)
            except:
                valor_unitario.text = "0" * 20
            
            valor_total_elem = ET.SubElement(adicao, "valorTotalCondicaoVenda")
            valor_total_elem.text = self._format_number(merc.get("ValorTotal", "0"), 11)
        
        # Adicionar tributos
        ii_valor = ET.SubElement(duimp, "iiAliquotaValorRecolher")
        ii_valor.text = self._format_number(data.get("tributos", {}).get("II", "0"), 15)
        
        pis_valor = ET.SubElement(duimp, "pisPasepAliquotaValorRecolher")
        pis_valor.text = self._format_number(data.get("tributos", {}).get("PIS", "0"), 15)
        
        cofins_valor = ET.SubElement(duimp, "cofinsAliquotaValorRecolher")
        cofins_valor.text = self._format_number(data.get("tributos", {}).get("COFINS", "0"), 15)
        
        # Informações complementares
        info_comp = ET.SubElement(duimp, "informacaoComplementar")
        info_text = f"PROCESSO: {data.get('identificacao', {}).get('Processo', 'NÃO INFORMADO')}\n"
        info_text += f"EXTRATO DUIMP GERADO EM: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        info_text += f"ORIGEM: PDF CONVERTIDO AUTOMATICAMENTE\n"
        if mercadorias:
            info_text += f"TOTAL DE MERCADORIAS: {len(mercadorias)}\n"
        info_comp.text = info_text
        
        # Elementos obrigatórios adicionais
        elementos_obrigatorios = {
            "totalAdicoes": f"{len(mercadorias):03d}",
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
            "canalSelecaoParametrizada": "001",
            "urfDespachoCodigo": "0417902",
            "urfDespachoNome": "IRF - PORTO DE SUAPE",
            "cargaUrfEntradaCodigo": "0417902",
            "cargaUrfEntradaNome": "IRF - PORTO DE SUAPE",
            "armazenamentoRecintoAduaneiroCodigo": "4931303",
            "armazenamentoRecintoAduaneiroNome": "INST.PORT.MAR.ALF.USO PUBLICO-TECON SUAPE S/A-IPOJUCA/PE",
            "dataDesembaraco": datetime.now().strftime("%Y%m%d"),
            "dataRegistro": datetime.now().strftime("%Y%m%d")
        }
        
        for elem, valor in elementos_obrigatorios.items():
            elemento = ET.SubElement(duimp, elem)
            elemento.text = valor
        
        # Adicionar armazem
        armazem = ET.SubElement(duimp, "armazem")
        nome_armazem = ET.SubElement(armazem, "nomeArmazem")
        nome_armazem.text = "TECON SUAPE       "
        
        # Adicionar ICMS
        icms = ET.SubElement(duimp, "icms")
        agencia_icms = ET.SubElement(icms, "agenciaIcms")
        agencia_icms.text = "00000"
        banco_icms = ET.SubElement(icms, "bancoIcms")
        banco_icms.text = "000"
        tipo_recolhimento = ET.SubElement(icms, "codigoTipoRecolhimentoIcms")
        tipo_recolhimento.text = "3"
        nome_tipo = ET.SubElement(icms, "nomeTipoRecolhimentoIcms")
        nome_tipo.text = "Exoneração do ICMS"
        uf_icms = ET.SubElement(icms, "ufIcms")
        uf_icms.text = "AL"
        valor_total_icms = ET.SubElement(icms, "valorTotalIcms")
        valor_total_icms.text = "000000000000000"
        
        return root
    
    def _clean_cnpj(self, cnpj: str) -> str:
        """Limpa e formata CNPJ"""
        # Remove todos os caracteres não numéricos
        clean = re.sub(r'\D', '', cnpj)
        return clean.zfill(14)
    
    def _format_date(self, date_str: str) -> str:
        """Converte data de DD/MM/YYYY para YYYYMMDD"""
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            return dt.strftime("%Y%m%d")
        except:
            return datetime.now().strftime("%Y%m%d")
    
    def _format_number(self, value: str, length: int = 15) -> str:
        """Formata número para o padrão XML (zeros à esquerda)"""
        try:
            # Converte para float e depois para centavos
            num = float(value)
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
            error_msg = str(e)
            st.markdown(f'<div class="error-box"><strong>Erro na validação XML:</strong> {error_msg}</div>', unsafe_allow_html=True)
            return False
    
    def pretty_xml(self, element: ET.Element) -> str:
        """Retorna XML formatado de forma legível"""
        rough_string = ET.tostring(element, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

class StreamlitApp:
    """Classe principal da aplicação Streamlit - Versão Corrigida"""
    
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
            <p><strong>Nota:</strong> Se encontrar erros, verifique se o PDF segue o layout oficial.</p>
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
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Tamanho do arquivo", f"{uploaded_file.size / 1024:.2f} KB")
            with col2:
                st.metric("Tipo", uploaded_file.type)
            
            # Pré-visualizar primeira página
            with st.expander("👁️ Visualizar primeira página do PDF"):
                try:
                    with pdfplumber.open(self.temp_pdf_path) as pdf:
                        first_page = pdf.pages[0]
                        st.text(first_page.extract_text()[:2000])
                except:
                    st.warning("Não foi possível pré-visualizar o PDF")
            
            return True
        
        return False
    
    def process_pdf(self):
        """Processa o PDF e extrai dados"""
        st.markdown('<h3 class="sub-header">2. Processamento e Extração</h3>', unsafe_allow_html=True)
        
        with st.spinner("Processando PDF... Isso pode levar alguns segundos."):
            try:
                # Extrair dados
                self.extracted_data = self.processor.extract_text_from_pdf(self.temp_pdf_path)
                
                if self.extracted_data and any(self.extracted_data.values()):
                    # Criar XML
                    xml_structure = self.processor.create_xml_structure(self.extracted_data)
                    self.xml_string = self.processor.pretty_xml(xml_structure)
                    
                    st.success("✅ PDF processado com sucesso!")
                    return True
                else:
                    st.error("❌ Não foi possível extrair dados do PDF. Verifique o formato do arquivo.")
                    return False
                    
            except Exception as e:
                st.error(f"❌ Erro durante o processamento: {str(e)}")
                st.info("Dica: Verifique se o PDF possui texto extraível e segue o layout oficial da DUIMP.")
                return False
    
    def display_extracted_data(self):
        """Exibe os dados extraídos para revisão"""
        st.markdown('<h3 class="sub-header">3. Dados Extraídos</h3>', unsafe_allow_html=True)
        
        if self.extracted_data:
            # Criar abas para diferentes seções
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📋 Identificação", 
                "📦 Mercadorias", 
                "💰 Valores", 
                "📊 Tributos",
                "📜 Histórico"
            ])
            
            with tab1:
                self._display_identificacao()
            
            with tab2:
                self._display_mercadorias()
            
            with tab3:
                self._display_valores()
            
            with tab4:
                self._display_tributos()
            
            with tab5:
                self._display_historico()
    
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
            st.write(f"**Data Embarque:** {dados_gerais.get('DataEmbarque', 'Não encontrado')}")
            st.write(f"**Data Chegada:** {dados_gerais.get('DataChegada', 'Não encontrado')}")
    
    def _display_mercadorias(self):
        """Exibe dados das mercadorias"""
        mercadorias = self.extracted_data.get("mercadorias", [])
        
        if mercadorias:
            df_data = []
            for i, merc in enumerate(mercadorias, 1):
                df_data.append({
                    "Item": i,
                    "NCM": merc.get("NCM", "00000000"),
                    "Descrição": merc.get("Descricao", "Sem descrição"),
                    "Quantidade": merc.get("Quantidade", "0"),
                    "Valor Total": f"R$ {float(merc.get('ValorTotal', 0)):,.2f}"
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, height=300)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Itens", len(mercadorias))
            with col2:
                total_valor = sum(float(m.get("ValorTotal", 0)) for m in mercadorias)
                st.metric("Valor Total Mercadorias", f"R$ {total_valor:,.2f}")
        else:
            st.warning("Nenhuma mercadoria encontrada no PDF")
    
    def _display_valores(self):
        """Exibe valores financeiros"""
        dados = self.extracted_data.get("dados_gerais", {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            valor_emb = float(dados.get("ValorEmbarque", 0))
            st.metric("Valor no Embarque", f"R$ {valor_emb:,.2f}")
        
        with col2:
            valor_dest = float(dados.get("ValorDestino", 0))
            st.metric("Valor no Destino", f"R$ {valor_dest:,.2f}")
        
        with col3:
            frete = float(dados.get("Frete", 0))
            st.metric("Frete", f"R$ {frete:,.2f}")
        
        with col4:
            total = valor_emb + valor_dest + frete
            st.metric("Valor Total", f"R$ {total:,.2f}")
    
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
    
    def _display_historico(self):
        """Exibe histórico de eventos"""
        historico = self.extracted_data.get("historico", [])
        
        if historico:
            df_data = []
            for evento in historico[:10]:  # Mostrar apenas os 10 primeiros
                df_data.append({
                    "Data/Hora": evento.get("data_hora", ""),
                    "Evento": evento.get("evento", ""),
                    "Responsável": evento.get("responsavel", "")
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            st.metric("Total de Eventos", len(historico))
        else:
            st.info("Nenhum evento histórico encontrado")
    
    def generate_output_files(self):
        """Gera e disponibiliza os arquivos de saída"""
        st.markdown('<h3 class="sub-header">4. Download dos Arquivos</h3>', unsafe_allow_html=True)
        
        if hasattr(self, 'xml_string'):
            # Validar XML se necessário
            if st.sidebar.checkbox("Validar XML gerado", value=True):
                validation_result = self.processor.validate_xml(self.xml_string)
                if validation_result:
                    st.success("✅ XML validado com sucesso!")
                else:
                    st.warning("⚠️ XML pode conter problemas de formatação")
            
            # Exibir preview do XML
            with st.expander("📄 Visualizar XML Gerado (primeiras 1000 linhas)"):
                lines = self.xml_string.split('\n')
                preview = '\n'.join(lines[:100])
                st.code(preview, language='xml')
                if len(lines) > 100:
                    st.caption(f"... e mais {len(lines)-100} linhas")
            
            # Botões de download
            st.markdown("### 📥 Download dos Arquivos")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Download XML
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"DUIMP_{timestamp}.xml"
                
                st.download_button(
                    label="📄 Baixar XML",
                    data=self.xml_string,
                    file_name=filename,
                    mime="application/xml",
                    help="Download do arquivo XML no layout obrigatório",
                    use_container_width=True
                )
            
            with col2:
                # Download JSON (se habilitado)
                if st.sidebar.checkbox("Gerar JSON intermediário", value=False):
                    try:
                        json_data = json.dumps(self.extracted_data, indent=2, ensure_ascii=False)
                        st.download_button(
                            label="📊 Baixar JSON",
                            data=json_data,
                            file_name=f"DUIMP_{timestamp}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    except:
                        st.warning("Não foi possível gerar JSON")
            
            with col3:
                # Download ZIP (se habilitado)
                if st.sidebar.checkbox("Compactar arquivos em ZIP", value=False):
                    try:
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            # Adicionar XML
                            zip_file.writestr(f"DUIMP_{timestamp}.xml", self.xml_string)
                            
                            # Adicionar JSON se existir
                            if st.sidebar.checkbox("Gerar JSON intermediário", value=False):
                                json_data = json.dumps(self.extracted_data, indent=2, ensure_ascii=False)
                                zip_file.writestr(f"DUIMP_{timestamp}.json", json_data)
                        
                        zip_buffer.seek(0)
                        
                        st.download_button(
                            label="📦 Baixar ZIP",
                            data=zip_buffer,
                            file_name=f"DUIMP_{timestamp}.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                    except:
                        st.warning("Não foi possível criar arquivo ZIP")
            
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
        
        # Inicializar estado da sessão
        if 'processed' not in st.session_state:
            st.session_state.processed = False
        if 'xml_generated' not in st.session_state:
            st.session_state.xml_generated = False
        
        # Passo 1: Upload
        file_uploaded = self.upload_section()
        
        if file_uploaded:
            # Botão de processamento
            if st.button("🔍 Processar PDF", type="primary", use_container_width=True):
                with st.spinner("Processando..."):
                    # Passo 2: Processamento
                    if self.process_pdf():
                        st.session_state.processed = True
                        
                        # Passo 3: Exibir dados
                        self.display_extracted_data()
                        
                        # Passo 4: Gerar arquivos
                        self.generate_output_files()
                    else:
                        st.session_state.processed = False
                        
        # Rodapé
        st.markdown("---")
        st.caption("""
        **Sistema desenvolvido para conversão de DUIMP** | 
        Compatível com layout fixo da Receita Federal |
        Versão 1.0.1 - Corrigido erro de índice |
        © 2024 - Todos os direitos reservados
        """)

# Executar aplicação
if __name__ == "__main__":
    try:
        app = StreamlitApp()
        app.run()
    except Exception as e:
        st.error(f"Erro fatal na aplicação: {str(e)}")
        st.info("""
        **Solução de problemas:**
        1. Verifique se todas as dependências estão instaladas
        2. Reinicie a aplicação
        3. Verifique o formato do PDF
        """)
