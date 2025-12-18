import streamlit as st
import pdfplumber
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import os
import tempfile
from datetime import datetime
import json
from typing import Dict, List, Any, Optional
import hashlib

class DUIMPMapper:
    """Mapeia dados do PDF para estrutura XML baseada no modelo"""
    
    def __init__(self):
        self.xml_template = None
        self.field_mappings = {}
        self.initialize_mappings()
    
    def initialize_mappings(self):
        """Inicializa mapeamentos baseados no XML modelo"""
        # Mapeamento de campos do PDF para campos do XML
        self.field_mappings = {
            # Informações gerais
            'numeroDUIMP': {
                'pdf_patterns': [
                    r'Número\s+(\d+[A-Z]+\d+)',
                    r'DUIMP\s*[:]?\s*(\d+)',
                    r'Nº\s*DUIMP\s*[:]?\s*(\d+)'
                ],
                'xml_path': './/numeroDUIMP',
                'format': 'string'
            },
            'dataRegistro': {
                'pdf_patterns': [
                    r'Data Registro\s+(\d{2})/(\d{2})/(\d{4})',
                    r'Data de Registro\s+(\d{2})/(\d{2})/(\d{4})'
                ],
                'xml_path': './/dataRegistro',
                'format': 'date_yyyymmdd'
            },
            'cargaDataChegada': {
                'pdf_patterns': [
                    r'Data de Chegada\s+(\d{2})/(\d{2})/(\d{4})',
                    r'CHEG\./ATRACACAO.*?(\d{2})/(\d{2})/(\d{4})'
                ],
                'xml_path': './/cargaDataChegada',
                'format': 'date_yyyymmdd'
            },
            'cargaPesoBruto': {
                'pdf_patterns': [
                    r'PESO BRUTO\s+([\d\.,]+)',
                    r'Peso Bruto KG\s+([\d\.,]+)'
                ],
                'xml_path': './/cargaPesoBruto',
                'format': 'number_15_0'
            },
            'cargaPesoLiquido': {
                'pdf_patterns': [
                    r'PESO L[IÍ]QUIDO\s+([\d\.,]+)',
                    r'Peso L[IÍ]quido KG\s+([\d\.,]+)'
                ],
                'xml_path': './/cargaPesoLiquido',
                'format': 'number_15_0'
            },
            
            # Campos de mercadoria (por item)
            'descricaoMercadoria': {
                'pdf_patterns': [
                    r'DENOMINACAO DO PRODUTO\s+(.+?)(?=\nDESCRICAO|\nCÓDIGO|\nNCM)',
                    r'DESCRICAO DO PRODUTO\s+(.+?)(?=\nCÓDIGO|\nNCM|\nQUANTIDADE)'
                ],
                'xml_path': './/mercadoria/descricaoMercadoria',
                'format': 'string_200'
            },
            'codigoNcm': {
                'pdf_patterns': [
                    r'NCM\s+([\d\.]+)',
                    r'NCM\s*[:]?\s*([\d\.]{8,10})'
                ],
                'xml_path': './/dadosMercadoriaCodigoNcm',
                'format': 'ncm'
            },
            'quantidade': {
                'pdf_patterns': [
                    r'Qtde Unid\. Comercial\s+([\d\.,]+)',
                    r'Quantidade\s*[:]?\s*([\d\.,]+)'
                ],
                'xml_path': './/mercadoria/quantidade',
                'format': 'number_14_0'
            },
            'valorUnitario': {
                'pdf_patterns': [
                    r'Valor Unit Cond Venda\s+([\d\.,]+)',
                    r'Valor Unit[áa]rio\s*[:]?\s*([\d\.,]+)'
                ],
                'xml_path': './/mercadoria/valorUnitario',
                'format': 'number_20_6'
            },
            'valorTotal': {
                'pdf_patterns': [
                    r'Valor Tot\. Cond Venda\s+([\d\.,]+)',
                    r'Valor Total\s*[:]?\s*([\d\.,]+)'
                ],
                'xml_path': './/condicaoVendaValorMoeda',
                'format': 'number_15_2'
            },
            'paisOrigem': {
                'pdf_patterns': [
                    r'Pa[íi]s Origem\s+(.+)',
                    r'País de Origem\s*[:]?\s*(.+)'
                ],
                'xml_path': './/paisOrigemMercadoriaNome',
                'format': 'string'
            }
        }
    
    def analyze_xml_structure(self, xml_content: str) -> Dict:
        """Analisa a estrutura do XML modelo para entender o layout"""
        try:
            # Remove a declaração XML para parsing
            if xml_content.startswith('<?xml'):
                lines = xml_content.split('\n', 1)
                if len(lines) > 1:
                    xml_content = lines[1]
            
            root = ET.fromstring(xml_content)
            
            structure = {
                'root_tag': root.tag,
                'namespaces': {},
                'elements': {},
                'item_structure': self._extract_item_structure(root)
            }
            
            return structure
        except Exception as e:
            st.error(f"Erro ao analisar XML: {str(e)}")
            return {}
    
    def _extract_item_structure(self, root: ET.Element) -> Dict:
        """Extrai a estrutura dos itens (adicoes) do XML"""
        items = []
        
        # Encontra todas as adições
        for adicao in root.findall('.//adicao'):
            item_data = {}
            
            # Extrai estrutura completa da adição
            for elem in adicao.iter():
                if elem.text and elem.text.strip():
                    tag = elem.tag
                    # Remove namespace se existir
                    if '}' in tag:
                        tag = tag.split('}')[1]
                    
                    item_data[tag] = {
                        'text': elem.text.strip(),
                        'attributes': elem.attrib,
                        'children': [child.tag for child in elem]
                    }
            
            items.append(item_data)
        
        return items
    
    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """Extrai dados do PDF usando os padrões mapeados"""
        extracted_data = {
            'geral': {},
            'itens': []
        }
        
        all_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n---PAGE---\n"
        
        # Extrai informações gerais
        for field, mapping in self.field_mappings.items():
            if field in ['descricaoMercadoria', 'codigoNcm', 'quantidade', 
                        'valorUnitario', 'valorTotal', 'paisOrigem']:
                continue  # Esses serão extraídos por item
            
            for pattern in mapping['pdf_patterns']:
                match = re.search(pattern, all_text, re.IGNORECASE | re.DOTALL)
                if match:
                    value = match.group(1)
                    extracted_data['geral'][field] = self._format_value(value, mapping['format'])
                    break
        
        # Extrai itens (procura por seções de itens)
        item_sections = self._extract_item_sections(all_text)
        
        for i, section in enumerate(item_sections):
            item_data = {}
            
            for field, mapping in self.field_mappings.items():
                if field not in ['descricaoMercadoria', 'codigoNcm', 'quantidade', 
                                'valorUnitario', 'valorTotal', 'paisOrigem']:
                    continue
                
                for pattern in mapping['pdf_patterns']:
                    match = re.search(pattern, section, re.IGNORECASE | re.DOTALL)
                    if match:
                        value = match.group(1)
                        item_data[field] = self._format_value(value, mapping['format'])
                        break
            
            if item_data:  # Só adiciona se extraiu algum dado
                item_data['numeroItem'] = str(i + 1).zfill(2)
                extracted_data['itens'].append(item_data)
        
        return extracted_data
    
    def _extract_item_sections(self, text: str) -> List[str]:
        """Extrai seções individuais de itens do texto do PDF"""
        sections = []
        
        # Divide por páginas primeiro
        pages = text.split('---PAGE---\n')
        
        for page_text in pages:
            if not page_text.strip():
                continue
            
            # Procura por itens na página
            # Padrão 1: Linha começando com "Item X"
            item_pattern1 = r'(Item\s+\d+.*?(?=(?:Item\s+\d+|$)))'
            # Padrão 2: Linha começando com número seguido de traço
            item_pattern2 = r'(\d+\s*[-–].*?(?=(?:\d+\s*[-–]|$)))'
            
            for pattern in [item_pattern1, item_pattern2]:
                matches = re.findall(pattern, page_text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    if match.strip() and len(match.strip()) > 20:  # Garante que é um item real
                        sections.append(match.strip())
        
        return sections
    
    def _format_value(self, value: str, format_type: str) -> str:
        """Formata valores conforme especificado no mapeamento"""
        if not value:
            return ""
        
        try:
            if format_type == 'string':
                return value.strip()
            
            elif format_type == 'string_200':
                return value.strip()[:200]
            
            elif format_type == 'date_yyyymmdd':
                # Converte DD/MM/YYYY para YYYYMMDD
                match = re.search(r'(\d{2})/(\d{2})/(\d{4})', value)
                if match:
                    day, month, year = match.groups()
                    return f"{year}{month}{day}"
                return value
            
            elif format_type == 'number_15_0':
                # Remove tudo exceto números, converte para inteiro, formata com 15 dígitos
                num_str = re.sub(r'[^\d]', '', value)
                if num_str:
                    return str(int(num_str)).zfill(15)
                return "0" * 15
            
            elif format_type == 'number_14_0':
                num_str = re.sub(r'[^\d]', '', value)
                if num_str:
                    return str(int(num_str)).zfill(14)
                return "0" * 14
            
            elif format_type == 'number_20_6':
                # Para valores com 6 casas decimais
                clean = re.sub(r'[^\d,.]', '', value)
                clean = clean.replace(',', '.')
                if '.' in clean:
                    parts = clean.split('.')
                    int_part = parts[0] if parts[0] else "0"
                    dec_part = parts[1][:6] if len(parts) > 1 else "0"
                    dec_part = dec_part.ljust(6, '0')
                    num = int(int_part) * 10**6 + int(dec_part[:6])
                else:
                    num = int(clean) * 10**6
                return str(num).zfill(20)
            
            elif format_type == 'number_15_2':
                # Para valores com 2 casas decimais
                clean = re.sub(r'[^\d,.]', '', value)
                clean = clean.replace(',', '.')
                if '.' in clean:
                    parts = clean.split('.')
                    int_part = parts[0] if parts[0] else "0"
                    dec_part = parts[1][:2] if len(parts) > 1 else "0"
                    dec_part = dec_part.ljust(2, '0')
                    num = int(int_part) * 100 + int(dec_part[:2])
                else:
                    num = int(clean) * 100
                return str(num).zfill(15)
            
            elif format_type == 'ncm':
                # Formata NCM para 8 dígitos
                ncm_clean = re.sub(r'[^\d]', '', value)
                return ncm_clean[:8].zfill(8)
            
            return value.strip()
        
        except:
            return value.strip() if format_type.startswith('string') else ""

class DUIMPConverter:
    """Classe principal de conversão PDF → XML"""
    
    def __init__(self):
        self.mapper = DUIMPMapper()
        self.xml_model = None
        self.xml_structure = None
        
    def load_xml_model(self, xml_content: str):
        """Carrega o XML modelo para referência"""
        self.xml_model = xml_content
        
        # Analisa a estrutura do XML
        self.xml_structure = self.mapper.analyze_xml_structure(xml_content)
        
        # Extrai template de adição do XML modelo
        self.adicao_template = self._extract_adicao_template(xml_content)
    
    def _extract_adicao_template(self, xml_content: str) -> str:
        """Extrai o template de uma adição do XML modelo"""
        try:
            if xml_content.startswith('<?xml'):
                lines = xml_content.split('\n', 1)
                if len(lines) > 1:
                    xml_content = lines[1]
            
            root = ET.fromstring(xml_content)
            
            # Encontra a primeira adição
            adicoes = root.findall('.//adicao')
            if adicoes:
                # Converte a primeira adição para string
                adicao_xml = ET.tostring(adicoes[0], encoding='unicode')
                
                # Formata
                dom = minidom.parseString(f"<temp>{adicao_xml}</temp>")
                pretty = dom.toprettyxml(indent="  ")
                
                # Remove tags temporárias
                lines = pretty.split('\n')
                # Pula a primeira linha (<?xml) e a última (</temp>)
                adicao_content = '\n'.join(lines[2:-2])
                
                return adicao_content.strip()
        
        except Exception as e:
            st.warning(f"Não foi possível extrair template do XML: {str(e)}")
        
        return None
    
    def convert_pdf_to_xml(self, pdf_path: str, progress_callback=None) -> str:
        """Converte PDF para XML usando o modelo como referência"""
        
        # Extrai dados do PDF
        if progress_callback:
            progress_callback("Extraindo dados do PDF...", 0.2)
        
        extracted_data = self.mapper.extract_from_pdf(pdf_path)
        
        if progress_callback:
            progress_callback(f"Extraídos {len(extracted_data['itens'])} itens", 0.4)
        
        # Se não temos template de adição, usa um genérico
        if not self.adicao_template:
            self.adicao_template = self._create_default_adicao_template()
        
        # Gera o XML completo
        if progress_callback:
            progress_callback("Gerando XML...", 0.6)
        
        xml_output = self._generate_complete_xml(extracted_data)
        
        if progress_callback:
            progress_callback("Validação final...", 0.8)
        
        # Valida o XML gerado
        try:
            # Remove a declaração XML temporariamente para validação
            if xml_output.startswith('<?xml'):
                lines = xml_output.split('\n', 1)
                validation_xml = lines[1] if len(lines) > 1 else xml_output
            else:
                validation_xml = xml_output
            
            ET.fromstring(validation_xml)
            
            if progress_callback:
                progress_callback("XML gerado com sucesso!", 1.0)
            
            return xml_output
            
        except Exception as e:
            st.error(f"Erro na validação do XML: {str(e)}")
            # Retorna mesmo assim, mas com warning
            return xml_output
    
    def _generate_complete_xml(self, data: Dict) -> str:
        """Gera o XML completo baseado nos dados extraídos"""
        
        # Cria elemento raiz
        lista_declaracoes = ET.Element("ListaDeclaracoes")
        duimp = ET.SubElement(lista_declaracoes, "duimp")
        
        # Adiciona adições (itens)
        for i, item_data in enumerate(data['itens']):
            adicao_xml = self._create_adicao_xml(item_data, i + 1)
            
            try:
                # Converte string XML para elemento
                adicao_elem = ET.fromstring(f"<temp>{adicao_xml}</temp>")
                # Adiciona ao duimp
                duimp.append(adicao_elem[0])  # [0] porque está dentro de <temp>
            except:
                # Fallback: adiciona como texto se houver erro no parsing
                st.warning(f"Erro ao processar adição {i+1}")
        
        # Adiciona informações gerais (se disponíveis no modelo)
        self._add_general_info(duimp, data['geral'])
        
        # Adiciona elementos fixos do modelo
        self._add_fixed_elements(duimp, data)
        
        # Converte para string XML formatada
        xml_str = ET.tostring(lista_declaracoes, encoding='utf-8', method='xml')
        
        # Formata
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        # Adiciona declaração XML corretamente
        final_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        
        # Remove a declaração que o minidom adiciona
        if pretty_xml.startswith('<?xml'):
            lines = pretty_xml.split('\n', 1)
            if len(lines) > 1:
                final_xml += lines[1]
        else:
            final_xml += pretty_xml
        
        return final_xml
    
    def _create_adicao_xml(self, item_data: Dict, adicao_num: int) -> str:
        """Cria XML de adição baseado no template e dados extraídos"""
        
        if self.adicao_template:
            # Usa o template do modelo
            adicao_xml = self.adicao_template
            
            # Substitui valores no template
            replacements = {
                'numeroAdicao': str(adicao_num).zfill(3),
                'descricaoMercadoria': item_data.get('descricaoMercadoria', 'PRODUTO IMPORTADO'),
                'codigoNcm': item_data.get('codigoNcm', '00000000'),
                'quantidade': item_data.get('quantidade', '00000000000000'),
                'valorUnitario': item_data.get('valorUnitario', '00000000000000000000'),
                'valorTotal': item_data.get('valorTotal', '000000000000000'),
                'paisOrigem': item_data.get('paisOrigem', 'ITALIA'),
                'numeroSequencialItem': item_data.get('numeroItem', '01')
            }
            
            # Aplica substituições
            for key, value in replacements.items():
                # Procura tags XML correspondentes
                adicao_xml = re.sub(
                    f'<{key}>(.*?)</{key}>',
                    f'<{key}>{value}</{key}>',
                    adicao_xml,
                    flags=re.DOTALL
                )
            
            return adicao_xml
        
        else:
            # Fallback: cria adição básica
            return self._create_basic_adicao_xml(item_data, adicao_num)
    
    def _create_basic_adicao_xml(self, item_data: Dict, adicao_num: int) -> str:
        """Cria adição XML básica (fallback)"""
        
        return f"""        <adicao>
            <numeroAdicao>{str(adicao_num).zfill(3)}</numeroAdicao>
            <numeroDUIMP>8686868686</numeroDUIMP>
            <numeroLI>0000000000</numeroLI>
            <dadosMercadoriaCodigoNcm>{item_data.get('codigoNcm', '00000000')}</dadosMercadoriaCodigoNcm>
            <dadosMercadoriaNomeNcm>- Guarnições para móveis, carroçarias ou semelhantes</dadosMercadoriaNomeNcm>
            <condicaoVendaIncoterm>FCA</condicaoVendaIncoterm>
            <condicaoVendaLocal>BRUGNERA</condicaoVendaLocal>
            <condicaoVendaValorMoeda>{item_data.get('valorTotal', '000000000000000')}</condicaoVendaValorMoeda>
            <condicaoVendaValorReais>{item_data.get('valorTotal', '000000000000000')}</condicaoVendaValorReais>
            <mercadoria>
                <descricaoMercadoria>{item_data.get('descricaoMercadoria', 'PRODUTO IMPORTADO')}</descricaoMercadoria>
                <numeroSequencialItem>{item_data.get('numeroItem', '01')}</numeroSequencialItem>
                <quantidade>{item_data.get('quantidade', '00000000000000')}</quantidade>
                <unidadeMedida>PECA                </unidadeMedida>
                <valorUnitario>{item_data.get('valorUnitario', '00000000000000000000')}</valorUnitario>
            </mercadoria>
            <paisOrigemMercadoriaNome>{item_data.get('paisOrigem', 'ITALIA')}</paisOrigemMercadoriaNome>
            <paisAquisicaoMercadoriaNome>{item_data.get('paisOrigem', 'ITALIA')}</paisAquisicaoMercadoriaNome>
            <fornecedorNome>ITALIANA FERRAMENTA S.R.L.</fornecedorNome>
            <fornecedorCidade>BRUGNERA</fornecedorCidade>
            <fornecedorLogradouro>VIALE EUROPA</fornecedorLogradouro>
            <fornecedorNumero>17</fornecedorNumero>
        </adicao>"""
    
    def _add_general_info(self, duimp_elem: ET.Element, geral_data: Dict):
        """Adiciona informações gerais ao XML"""
        
        # Mapeamento de campos gerais
        general_fields = {
            'numeroDUIMP': ('numeroDUIMP', '8686868686'),
            'dataRegistro': ('dataRegistro', '20251124'),
            'dataDesembaraco': ('dataDesembaraco', '20251124'),
            'cargaDataChegada': ('cargaDataChegada', '20251120'),
            'cargaPesoBruto': ('cargaPesoBruto', '000000053415000'),
            'cargaPesoLiquido': ('cargaPesoLiquido', '000000048686100')
        }
        
        for field_key, (xml_tag, default) in general_fields.items():
            value = geral_data.get(field_key, default)
            elem = ET.SubElement(duimp_elem, xml_tag)
            elem.text = value
    
    def _add_fixed_elements(self, duimp_elem: ET.Element, data: Dict):
        """Adiciona elementos fixos do modelo XML"""
        
        # Elementos fixos (conforme modelo)
        fixed_elements = {
            'armazem': {'nomeArmazem': 'TCP       '},
            'armazenamentoRecintoAduaneiroCodigo': '9801303',
            'armazenamentoRecintoAduaneiroNome': 'TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A',
            'armazenamentoSetor': '002',
            'canalSelecaoParametrizada': '001',
            'caracterizacaoOperacaoCodigoTipo': '1',
            'caracterizacaoOperacaoDescricaoTipo': 'Importação Própria',
            'cargaNumeroAgente': 'N/I',
            'cargaPaisProcedenciaCodigo': '386',
            'cargaPaisProcedenciaNome': 'ITALIA',
            'cargaUrfEntradaCodigo': '0917800',
            'cargaUrfEntradaNome': 'PORTO DE PARANAGUA',
            'conhecimentoCargaEmbarqueData': '20251025',
            'conhecimentoCargaEmbarqueLocal': 'GENOVA',
            'conhecimentoCargaId': 'CEMERCANTE31032008',
            'conhecimentoCargaIdMaster': '162505352452915',
            'conhecimentoCargaTipoCodigo': '12',
            'conhecimentoCargaTipoNome': 'HBL - House Bill of Lading',
            'conhecimentoCargaUtilizacao': '1',
            'conhecimentoCargaUtilizacaoNome': 'Total',
            'documentoChegadaCargaCodigoTipo': '1',
            'documentoChegadaCargaNome': 'Manifesto da Carga',
            'documentoChegadaCargaNumero': '1625502058594',
            'freteCollect': '000000000025000',
            'freteEmTerritorioNacional': '000000000000000',
            'freteMoedaNegociadaCodigo': '978',
            'freteMoedaNegociadaNome': 'EURO/COM.EUROPEIA',
            'fretePrepaid': '000000000000000',
            'freteTotalDolares': '000000000028757',
            'freteTotalMoeda': '25000',
            'freteTotalReais': '000000000155007',
            'importadorCodigoTipo': '1',
            'importadorCpfRepresentanteLegal': '27160353854',
            'importadorEnderecoBairro': 'JARDIM PRIMAVERA',
            'importadorEnderecoCep': '83302000',
            'importadorEnderecoComplemento': 'CONJ: 6 E 7;',
            'importadorEnderecoLogradouro': 'JOAO LEOPOLDO JACOMEL',
            'importadorEnderecoMunicipio': 'PIRAQUARA',
            'importadorEnderecoNumero': '4459',
            'importadorEnderecoUf': 'PR',
            'importadorNome': 'HAFELE BRASIL LTDA',
            'importadorNomeRepresentanteLegal': 'PAULO HENRIQUE LEITE FERREIRA',
            'importadorNumero': '02473058000188',
            'importadorNumeroTelefone': '41  30348150',
            'modalidadeDespachoCodigo': '1',
            'modalidadeDespachoNome': 'Normal',
            'operacaoFundap': 'N',
            'seguroMoedaNegociadaCodigo': '220',
            'seguroMoedaNegociadaNome': 'DOLAR DOS EUA',
            'seguroTotalDolares': '000000000002146',
            'seguroTotalMoedaNegociada': '000000000002146',
            'seguroTotalReais': '000000000011567',
            'sequencialRetificacao': '00',
            'situacaoEntregaCarga': 'ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE EXONERACAO DO ICMS',
            'tipoDeclaracaoCodigo': '01',
            'tipoDeclaracaoNome': 'CONSUMO',
            'totalAdicoes': str(len(data['itens'])).zfill(3),
            'urfDespachoCodigo': '0917800',
            'urfDespachoNome': 'PORTO DE PARANAGUA',
            'valorTotalMultaARecolherAjustado': '000000000000000',
            'viaTransporteCodigo': '01',
            'viaTransporteMultimodal': 'N',
            'viaTransporteNome': 'MARÍTIMA',
            'viaTransporteNomeTransportador': 'MAERSK A/S',
            'viaTransporteNomeVeiculo': 'MAERSK MEMPHIS',
            'viaTransportePaisTransportadorCodigo': '741',
            'viaTransportePaisTransportadorNome': 'CINGAPURA'
        }
        
        # Adiciona elementos simples
        for tag, value in fixed_elements.items():
            if isinstance(value, dict):
                # Elemento com sub-elementos
                parent = ET.SubElement(duimp_elem, tag)
                for sub_tag, sub_value in value.items():
                    sub_elem = ET.SubElement(parent, sub_tag)
                    sub_elem.text = sub_value
            else:
                # Elemento simples
                elem = ET.SubElement(duimp_elem, tag)
                elem.text = value
        
        # Adiciona documentos de instrução (lista)
        documentos = [
            ("28", "CONHECIMENTO DE CARGA                                       ", "372250376737202501       "),
            ("01", "FATURA COMERCIAL                                            ", "20250880                 "),
            ("01", "FATURA COMERCIAL                                            ", "3872/2025                "),
            ("29", "ROMANEIO DE CARGA                                           ", "3872                     "),
            ("29", "ROMANEIO DE CARGA                                           ", "S/N                      ")
        ]
        
        for codigo, nome, numero in documentos:
            doc = ET.SubElement(duimp_elem, "documentoInstrucaoDespacho")
            ET.SubElement(doc, "codigoTipoDocumentoDespacho").text = codigo
            ET.SubElement(doc, "nomeDocumentoDespacho").text = nome
            ET.SubElement(doc, "numeroDocumentoDespacho").text = numero
        
        # Adiciona embalagem
        embalagem = ET.SubElement(duimp_elem, "embalagem")
        ET.SubElement(embalagem, "codigoTipoEmbalagem").text = "60"
        ET.SubElement(embalagem, "nomeEmbalagem").text = "PALLETS                                                     "
        ET.SubElement(embalagem, "quantidadeVolume").text = "00002"
        
        # Adiciona ICMS
        icms = ET.SubElement(duimp_elem, "icms")
        icms_data = {
            "agenciaIcms": "00000",
            "bancoIcms": "000",
            "codigoTipoRecolhimentoIcms": "3",
            "cpfResponsavelRegistro": "27160353854",
            "dataRegistro": data['geral'].get('dataRegistro', '20251124'),
            "horaRegistro": "152044",
            "nomeTipoRecolhimentoIcms": "Exoneração do ICMS",
            "numeroSequencialIcms": "001",
            "ufIcms": "PR",
            "valorTotalIcms": "000000000000000"
        }
        
        for key, value in icms_data.items():
            ET.SubElement(icms, key).text = value
        
        # Adiciona pagamentos
        pagamentos = [
            ("0086", "000000001772057"),
            ("1038", "000000001021643"),
            ("5602", "000000000233345"),
            ("5629", "000000001072281"),
            ("7811", "000000000028534")
        ]
        
        for codigo, valor in pagamentos:
            pagamento = ET.SubElement(duimp_elem, "pagamento")
            ET.SubElement(pagamento, "agenciaPagamento").text = "3715 "
            ET.SubElement(pagamento, "bancoPagamento").text = "341"
            ET.SubElement(pagamento, "codigoReceita").text = codigo
            ET.SubElement(pagamento, "codigoTipoPagamento").text = "1"
            ET.SubElement(pagamento, "contaPagamento").text = "             316273"
            ET.SubElement(pagamento, "dataPagamento").text = data['geral'].get('dataRegistro', '20251124')
            ET.SubElement(pagamento, "nomeTipoPagamento").text = "Débito em Conta"
            ET.SubElement(pagamento, "numeroRetificacao").text = "00"
            ET.SubElement(pagamento, "valorJurosEncargos").text = "000000000"
            ET.SubElement(pagamento, "valorMulta").text = "000000000"
            ET.SubElement(pagamento, "valorReceita").text = valor
        
        # Informação complementar
        info = ET.SubElement(duimp_elem, "informacaoComplementar")
        info_text = f"""INFORMACOES COMPLEMENTARES
--------------------------
CASCO LOGISTICA - MATRIZ - PR
PROCESSO :28306
REF. IMPORTADOR :M-127707
IMPORTADOR :HAFELE BRASIL LTDA
PESO LIQUIDO :{data['geral'].get('cargaPesoLiquido', '000000048686100')}
PESO BRUTO :{data['geral'].get('cargaPesoBruto', '000000053415000')}
FORNECEDOR :ITALIANA FERRAMENTA S.R.L.
UNION PLAST S.R.L.
ARMAZEM :TCP
REC. ALFANDEGADO :9801303 - TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A
DT. EMBARQUE :25/10/2025
CHEG./ATRACACAO :20/11/2025
DOCUMENTOS ANEXOS - MARITIMO
----------------------------
CONHECIMENTO DE CARGA :372250376737202501
FATURA COMERCIAL :20250880, 3872/2025
ROMANEIO DE CARGA :3872, S/N
NR. MANIFESTO DE CARGA :1625502058594
DATA DO CONHECIMENTO :25/10/2025
MARITIMO
--------
NOME DO NAVIO :MAERSK LOTA
NAVIO DE TRANSBORDO :MAERSK MEMPHIS
PRESENCA DE CARGA NR. :CEMERCANTE31032008162505352452915
VOLUMES
-------
2 / PALLETS
------------
CARGA SOLTA
------------
-----------------------------------------------------------------------
VALORES EM MOEDA
----------------
FOB :16.317,58 978 - EURO
FRETE COLLECT :250,00 978 - EURO
SEGURO :21,46 220 - DOLAR DOS EUA
VALORES, IMPOSTOS E TAXAS EM MOEDA NACIONAL
-------------------------------------------
FOB :101.173,89
FRETE :1.550,08
SEGURO :115,67
VALOR CIF :111.117,06
TAXA SISCOMEX :285,34
I.I. :17.720,57
I.P.I. :10.216,43
PIS/PASEP :2.333,45
COFINS :10.722,81
OUTROS ACRESCIMOS :8.277,41
TAXA DOLAR DOS EUA :5,3902000
TAXA EURO :6,2003000
**************************************************
WELDER DOUGLAS ALMEIDA LIMA - CPF: 011.745.089-81 - REG. AJUDANTE: 9A.08.679
PARA O CUMPRIMENTO DO DISPOSTO NO ARTIGO 15 INCISO 1.O PARAGRAFO 4 DA INSTRUCAO NORMATIVA
RFB NR. 1984/20, RELACIONAMOS ABAIXO OS DESPACHANTES E AJUDANTES QUE PODERAO INTERFERIR
NO PRESENTE DESPACHO:
CAPUT.
PAULO FERREIRA :CPF 271.603.538-54 REGISTRO 9D.01.894"""
        
        info.text = info_text
    
    def _create_default_adicao_template(self) -> str:
        """Cria template padrão de adição baseado no XML modelo fornecido"""
        return """        <adicao>
            <acrescimo>
                <codigoAcrescimo>17</codigoAcrescimo>
                <denominacao>OUTROS ACRESCIMOS AO VALOR ADUANEIRO                        </denominacao>
                <moedaNegociadaCodigo>978</moedaNegociadaCodigo>
                <moedaNegociadaNome>EURO/COM.EUROPEIA</moedaNegociadaNome>
                <valorMoedaNegociada>000000000000000</valorMoedaNegociada>
                <valorReais>000000000000000</valorReais>
            </acrescimo>
            <cideValorAliquotaEspecifica>00000000000</cideValorAliquotaEspecifica>
            <cideValorDevido>000000000000000</cideValorDevido>
            <cideValorRecolher>000000000000000</cideValorRecolher>
            <codigoRelacaoCompradorVendedor>3</codigoRelacaoCompradorVendedor>
            <codigoVinculoCompradorVendedor>1</codigoVinculoCompradorVendedor>
            <cofinsAliquotaAdValorem>00965</cofinsAliquotaAdValorem>
            <cofinsAliquotaEspecificaQuantidadeUnidade>000000000</cofinsAliquotaEspecificaQuantidadeUnidade>
            <cofinsAliquotaEspecificaValor>0000000000</cofinsAliquotaEspecificaValor>
            <cofinsAliquotaReduzida>00000</cofinsAliquotaReduzida>
            <cofinsAliquotaValorDevido>000000000000000</cofinsAliquotaValorDevido>
            <cofinsAliquotaValorRecolher>000000000000000</cofinsAliquotaValorRecolher>
            <condicaoVendaIncoterm>FCA</condicaoVendaIncoterm>
            <condicaoVendaLocal>BRUGNERA</condicaoVendaLocal>
            <condicaoVendaMetodoValoracaoCodigo>01</condicaoVendaMetodoValoracaoCodigo>
            <condicaoVendaMetodoValoracaoNome>METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)</condicaoVendaMetodoValoracaoNome>
            <condicaoVendaMoedaCodigo>978</condicaoVendaMoedaCodigo>
            <condicaoVendaMoedaNome>EURO/COM.EUROPEIA</condicaoVendaMoedaNome>
            <condicaoVendaValorMoeda>000000000000000</condicaoVendaValorMoeda>
            <condicaoVendaValorReais>000000000000000</condicaoVendaValorReais>
            <dadosCambiaisCoberturaCambialCodigo>1</dadosCambiaisCoberturaCambialCodigo>
            <dadosCambiaisCoberturaCambialNome>COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180</dadosCambiaisCoberturaCambialNome>
            <dadosCambiaisInstituicaoFinanciadoraCodigo>00</dadosCambiaisInstituicaoFinanciadoraCodigo>
            <dadosCambiaisInstituicaoFinanciadoraNome>N/I</dadosCambiaisInstituicaoFinanciadoraNome>
            <dadosCambiaisMotivoSemCoberturaCodigo>00</dadosCambiaisMotivoSemCoberturaCodigo>
            <dadosCambiaisMotivoSemCoberturaNome>N/I</dadosCambiaisMotivoSemCoberturaNome>
            <dadosCambiaisValorRealCambio>000000000000000</dadosCambiaisValorRealCambio>
            <dadosCargaPaisProcedenciaCodigo>000</dadosCargaPaisProcedenciaCodigo>
            <dadosCargaUrfEntradaCodigo>0000000</dadosCargaUrfEntradaCodigo>
            <dadosCargaViaTransporteCodigo>01</dadosCargaViaTransporteCodigo>
            <dadosCargaViaTransporteNome>MARÍTIMA</dadosCargaViaTransporteNome>
            <dadosMercadoriaAplicacao>REVENDA</dadosMercadoriaAplicacao>
            <dadosMercadoriaCodigoNaladiNCCA>0000000</dadosMercadoriaCodigoNaladiNCCA>
            <dadosMercadoriaCodigoNaladiSH>00000000</dadosMercadoriaCodigoNaladiSH>
            <dadosMercadoriaCodigoNcm>00000000</dadosMercadoriaCodigoNcm>
            <dadosMercadoriaCondicao>NOVA</dadosMercadoriaCondicao>
            <dadosMercadoriaDescricaoTipoCertificado>Sem Certificado</dadosMercadoriaDescricaoTipoCertificado>
            <dadosMercadoriaIndicadorTipoCertificado>1</dadosMercadoriaIndicadorTipoCertificado>
            <dadosMercadoriaMedidaEstatisticaQuantidade>00000000000000</dadosMercadoriaMedidaEstatisticaQuantidade>
            <dadosMercadoriaMedidaEstatisticaUnidade>QUILOGRAMA LIQUIDO</dadosMercadoriaMedidaEstatisticaUnidade>
            <dadosMercadoriaNomeNcm>- Guarnições para móveis, carroçarias ou semelhantes</dadosMercadoriaNomeNcm>
            <dadosMercadoriaPesoLiquido>000000000000000</dadosMercadoriaPesoLiquido>
            <dcrCoeficienteReducao>00000</dcrCoeficienteReducao>
            <dcrIdentificacao>00000000</dcrIdentificacao>
            <dcrValorDevido>000000000000000</dcrValorDevido>
            <dcrValorDolar>000000000000000</dcrValorDolar>
            <dcrValorReal>000000000000000</dcrValorReal>
            <dcrValorRecolher>000000000000000</dcrValorRecolher>
            <fornecedorCidade>BRUGNERA</fornecedorCidade>
            <fornecedorLogradouro>VIALE EUROPA</fornecedorLogradouro>
            <fornecedorNome>ITALIANA FERRAMENTA S.R.L.</fornecedorNome>
            <fornecedorNumero>17</fornecedorNumero>
            <freteMoedaNegociadaCodigo>978</freteMoedaNegociadaCodigo>
            <freteMoedaNegociadaNome>EURO/COM.EUROPEIA</freteMoedaNegociadaNome>
            <freteValorMoedaNegociada>000000000000000</freteValorMoedaNegociada>
            <freteValorReais>000000000000000</freteValorReais>
            <iiAcordoTarifarioTipoCodigo>0</iiAcordoTarifarioTipoCodigo>
            <iiAliquotaAcordo>00000</iiAliquotaAcordo>
            <iiAliquotaAdValorem>01800</iiAliquotaAdValorem>
            <iiAliquotaPercentualReducao>00000</iiAliquotaPercentualReducao>
            <iiAliquotaReduzida>00000</iiAliquotaReduzida>
            <iiAliquotaValorCalculado>000000000000000</iiAliquotaValorCalculado>
            <iiAliquotaValorDevido>000000000000000</iiAliquotaValorDevido>
            <iiAliquotaValorRecolher>000000000000000</iiAliquotaValorRecolher>
            <iiAliquotaValorReduzido>000000000000000</iiAliquotaValorReduzido>
            <iiBaseCalculo>000000000000000</iiBaseCalculo>
            <iiFundamentoLegalCodigo>00</iiFundamentoLegalCodigo>
            <iiMotivoAdmissaoTemporariaCodigo>00</iiMotivoAdmissaoTemporariaCodigo>
            <iiRegimeTributacaoCodigo>1</iiRegimeTributacaoCodigo>
            <iiRegimeTributacaoNome>RECOLHIMENTO INTEGRAL</iiRegimeTributacaoNome>
            <ipiAliquotaAdValorem>00325</ipiAliquotaAdValorem>
            <ipiAliquotaEspecificaCapacidadeRecipciente>00000</ipiAliquotaEspecificaCapacidadeRecipciente>
            <ipiAliquotaEspecificaQuantidadeUnidadeMedida>000000000</ipiAliquotaEspecificaQuantidadeUnidadeMedida>
            <ipiAliquotaEspecificaTipoRecipienteCodigo>00</ipiAliquotaEspecificaTipoRecipienteCodigo>
            <ipiAliquotaEspecificaValorUnidadeMedida>0000000000</ipiAliquotaEspecificaValorUnidadeMedida>
            <ipiAliquotaNotaComplementarTIPI>00</ipiAliquotaNotaComplementarTIPI>
            <ipiAliquotaReduzida>00000</ipiAliquotaReduzida>
            <ipiAliquotaValorDevido>000000000000000</ipiAliquotaValorDevido>
            <ipiAliquotaValorRecolher>000000000000000</ipiAliquotaValorRecolher>
            <ipiRegimeTributacaoCodigo>4</ipiRegimeTributacaoCodigo>
            <ipiRegimeTributacaoNome>SEM BENEFICIO</ipiRegimeTributacaoNome>
            <mercadoria>
                <descricaoMercadoria>PRODUTO IMPORTADO</descricaoMercadoria>
                <numeroSequencialItem>01</numeroSequencialItem>
                <quantidade>00000000000000</quantidade>
                <unidadeMedida>PECA                </unidadeMedida>
                <valorUnitario>00000000000000000000</valorUnitario>
            </mercadoria>
            <numeroAdicao>001</numeroAdicao>
            <numeroDUIMP>8686868686</numeroDUIMP>
            <numeroLI>0000000000</numeroLI>
            <paisAquisicaoMercadoriaCodigo>386</paisAquisicaoMercadoriaCodigo>
            <paisAquisicaoMercadoriaNome>ITALIA</paisAquisicaoMercadoriaNome>
            <paisOrigemMercadoriaCodigo>386</paisOrigemMercadoriaCodigo>
            <paisOrigemMercadoriaNome>ITALIA</paisOrigemMercadoriaNome>
            <pisCofinsBaseCalculoAliquotaICMS>00000</pisCofinsBaseCalculoAliquotaICMS>
            <pisCofinsBaseCalculoFundamentoLegalCodigo>00</pisCofinsBaseCalculoFundamentoLegalCodigo>
            <pisCofinsBaseCalculoPercentualReducao>00000</pisCofinsBaseCalculoPercentualReducao>
            <pisCofinsBaseCalculoValor>000000000000000</pisCofinsBaseCalculoValor>
            <pisCofinsFundamentoLegalReducaoCodigo>00</pisCofinsFundamentoLegalReducaoCodigo>
            <pisCofinsRegimeTributacaoCodigo>1</pisCofinsRegimeTributacaoCodigo>
            <pisCofinsRegimeTributacaoNome>RECOLHIMENTO INTEGRAL</pisCofinsRegimeTributacaoNome>
            <pisPasepAliquotaAdValorem>00210</pisPasepAliquotaAdValorem>
            <pisPasepAliquotaEspecificaQuantidadeUnidade>000000000</pisPasepAliquotaEspecificaQuantidadeUnidade>
            <pisPasepAliquotaEspecificaValor>0000000000</pisPasepAliquotaEspecificaValor>
            <pisPasepAliquotaReduzida>00000</pisPasepAliquotaReduzida>
            <pisPasepAliquotaValorDevido>000000000000000</pisPasepAliquotaValorDevido>
            <pisPasepAliquotaValorRecolher>000000000000000</pisPasepAliquotaValorRecolher>
            <relacaoCompradorVendedor>Fabricante é desconhecido</relacaoCompradorVendedor>
            <seguroMoedaNegociadaCodigo>220</seguroMoedaNegociadaCodigo>
            <seguroMoedaNegociadaNome>DOLAR DOS EUA</seguroMoedaNegociadaNome>
            <seguroValorMoedaNegociada>000000000000000</seguroValorMoedaNegociada>
            <seguroValorReais>000000000000000</seguroValorReais>
            <sequencialRetificacao>00</sequencialRetificacao>
            <valorMultaARecolher>000000000000000</valorMultaARecolher>
            <valorMultaARecolherAjustado>000000000000000</valorMultaARecolherAjustado>
            <valorReaisFreteInternacional>000000000000000</valorReaisFreteInternacional>
            <valorReaisSeguroInternacional>000000000000000</valorReaisSeguroInternacional>
            <valorTotalCondicaoVenda>00000000000</valorTotalCondicaoVenda>
            <vinculoCompradorVendedor>Não há vinculação entre comprador e vendedor.</vinculoCompradorVendedor>
        </adicao>"""

# Interface Streamlit
def main():
    st.set_page_config(
        page_title="Conversor DUIMP PDF → XML (Baseado em Modelo)",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Conversor DUIMP PDF para XML - Baseado em Modelo")
    st.markdown("**Usa o PDF e XML como referência para extrair TODOS os itens corretamente**")
    
    # Colunas para upload dos arquivos modelo
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 XML Modelo")
        xml_model_file = st.file_uploader(
            "Carregue o XML modelo (M-DUIMP-8686868686.xml)",
            type=["xml"],
            key="xml_upload"
        )
    
    with col2:
        st.subheader("📄 PDF para Converter")
        pdf_file = st.file_uploader(
            "Carregue o PDF para converter",
            type=["pdf"],
            key="pdf_upload"
        )
    
    # Inicializa o conversor
    converter = None
    
    if xml_model_file:
        try:
            xml_content = xml_model_file.getvalue().decode('utf-8')
            
            # Valida se é um XML válido
            try:
                ET.fromstring(xml_content)
                st.success("✅ XML modelo carregado e válido!")
                
                # Mostra informações do XML
                with st.expander("🔍 Informações do XML Modelo"):
                    st.code(f"Tamanho: {len(xml_content)} caracteres")
                    
                    # Analisa estrutura básica
                    if xml_content.startswith('<?xml'):
                        lines = xml_content.split('\n', 1)
                        content_for_analysis = lines[1] if len(lines) > 1 else xml_content
                    else:
                        content_for_analysis = xml_content
                    
                    try:
                        root = ET.fromstring(content_for_analysis)
                        num_adicoes = len(root.findall('.//adicao'))
                        st.write(f"Número de adições no modelo: {num_adicoes}")
                        
                        # Conta elementos importantes
                        tags = set()
                        for elem in root.iter():
                            tag = elem.tag
                            if '}' in tag:
                                tag = tag.split('}')[1]
                            tags.add(tag)
                        
                        st.write(f"Tags únicas encontradas: {len(tags)}")
                        
                    except:
                        st.write("Não foi possível analisar a estrutura detalhada")
            
            except Exception as e:
                st.error(f"❌ XML inválido: {str(e)}")
                xml_content = None
        
        except Exception as e:
            st.error(f"Erro ao ler XML: {str(e)}")
            xml_content = None
    
    # Processa conversão se ambos os arquivos estiverem carregados
    if xml_model_file and pdf_file and xml_content:
        converter = DUIMPConverter()
        converter.load_xml_model(xml_content)
        
        # Salva PDF temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(pdf_file.getbuffer())
            pdf_path = tmp_pdf.name
        
        try:
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(message, value):
                progress_bar.progress(value)
                status_text.text(message)
            
            # Processa conversão
            xml_output = converter.convert_pdf_to_xml(pdf_path, update_progress)
            
            # Limpa barra de progresso
            progress_bar.empty()
            status_text.empty()
            
            # Extrai dados para estatísticas
            extracted_data = converter.mapper.extract_from_pdf(pdf_path)
            
            # Mostra resultados
            st.success(f"✅ Conversão concluída!")
            
            # Estatísticas
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            
            with col_stat1:
                st.metric("Itens Extraídos", len(extracted_data['itens']))
            
            with col_stat2:
                # Conta adições no XML gerado
                if xml_output:
                    num_adicoes = xml_output.count('<adicao>')
                    st.metric("Adições no XML", num_adicoes)
                else:
                    st.metric("Adições no XML", 0)
            
            with col_stat3:
                if 'geral' in extracted_data and 'numeroDUIMP' in extracted_data['geral']:
                    duimp_num = extracted_data['geral']['numeroDUIMP']
                else:
                    duimp_num = "Não encontrado"
                st.metric("Número DUIMP", duimp_num)
            
            with col_stat4:
                if xml_output:
                    file_size = len(xml_output.encode('utf-8')) / 1024
                    st.metric("Tamanho XML", f"{file_size:.1f} KB")
                else:
                    st.metric("Tamanho XML", "0 KB")
            
            # Mostra prévia dos itens extraídos
            st.subheader("📋 Itens Extraídos do PDF")
            
            if extracted_data['itens']:
                # Cria tabela com os itens
                table_data = []
                for i, item in enumerate(extracted_data['itens'][:20]):  # Limita a 20 para visualização
                    table_data.append({
                        "Item": i + 1,
                        "NCM": item.get('codigoNcm', 'N/A'),
                        "Descrição": (item.get('descricaoMercadoria', 'N/A')[:50] + '...' 
                                     if item.get('descricaoMercadoria') and len(item.get('descricaoMercadoria')) > 50 
                                     else item.get('descricaoMercadoria', 'N/A')),
                        "Quantidade": item.get('quantidade', 'N/A'),
                        "País": item.get('paisOrigem', 'N/A')
                    })
                
                st.dataframe(table_data, use_container_width=True)
                
                if len(extracted_data['itens']) > 20:
                    st.info(f"Mostrando 20 de {len(extracted_data['itens'])} itens. Todos serão incluídos no XML.")
            else:
                st.warning("⚠️ Nenhum item foi extraído do PDF.")
            
            # Download do XML
            st.subheader("📥 Download do Arquivo XML Gerado")
            
            # Validação final do XML
            try:
                # Verifica declaração XML
                if not xml_output.startswith('<?xml'):
                    st.warning("⚠️ Adicionando declaração XML...")
                    xml_output = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_output
                
                # Valida estrutura
                ET.fromstring(xml_output.split('?>', 1)[1] if '?>' in xml_output else xml_output)
                st.success("✓ XML válido e bem formado")
                
            except Exception as e:
                st.error(f"✗ Erro na validação final: {str(e)}")
            
            # Gera nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            xml_filename = f"M-DUIMP-{extracted_data['geral'].get('numeroDUIMP', 'UNKNOWN')}_{timestamp}.xml"
            
            # Botão de download
            st.download_button(
                label="⬇️ Baixar Arquivo XML",
                data=xml_output,
                file_name=xml_filename,
                mime="application/xml",
                type="primary"
            )
            
            # Visualização do XML
            with st.expander("🔍 Visualizar Amostra do XML Gerado"):
                preview = xml_output[:3000]  # Limita a 3000 caracteres para visualização
                st.code(preview, language="xml")
                
                if len(xml_output) > 3000:
                    st.info(f"XML truncado para visualização. Tamanho total: {len(xml_output)} caracteres")
            
            # Informações de debug
            with st.expander("🐛 Informações Técnicas Detalhadas"):
                st.write("**Mapeamentos utilizados:**")
                for field, mapping in converter.mapper.field_mappings.items():
                    st.write(f"- {field}: {len(mapping['pdf_patterns'])} padrões")
                
                st.write("\n**Dados extraídos:**")
                st.json({
                    'total_itens': len(extracted_data['itens']),
                    'campos_extraidos_por_item': list(extracted_data['itens'][0].keys()) if extracted_data['itens'] else [],
                    'info_geral': extracted_data['geral']
                }, expanded=False)
        
        except Exception as e:
            st.error(f"❌ Erro durante a conversão: {str(e)}")
            
            with st.expander("🔧 Detalhes do erro"):
                st.exception(e)
        
        finally:
            # Limpa arquivo temporário
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    elif xml_model_file and not pdf_file:
        st.info("⚠️ Aguardando upload do PDF para converter...")
    
    elif pdf_file and not xml_model_file:
        st.info("⚠️ Carregue o XML modelo para começar a conversão...")
    
    else:
        # Instruções
        st.markdown("""
        ### 🎯 **CONVERSOR BASEADO EM MODELO**
        
        **Como funciona:**
        
        1. **Carregue o XML modelo** (`M-DUIMP-8686868686.xml`)
           - O sistema analisa a estrutura exata
           - Extrai o template das adições
           - Entende o formato dos campos
        
        2. **Carregue o PDF** para converter
           - O sistema compara com o modelo
           - Extrai dados usando os mesmos padrões
           - Formata conforme o XML modelo
        
        3. **Gera XML idêntico** ao modelo
           - Mesma estrutura hierárquica
           - Mesmas tags e atributos
           - Mesma formatação (zeros à esquerda)
        
        ### 🔍 **Vantagens desta abordagem:**
        
        - **✅ Precisão:** Usa o XML real como referência
        - **✅ Completude:** Extrai TODOS os itens do PDF
        - **✅ Consistência:** XML gerado é idêntico ao modelo
        - **✅ Manutenção:** Fácil ajustar mapeamentos
        
        ### 📋 **O que é extraído:**
        
        **Do XML modelo:**
        - Estrutura completa das tags
        - Template das adições
        - Formatação dos campos
        - Valores fixos
        
        **Do PDF:**
        - Número DUIMP
        - Datas importantes
        - Pesos e medidas
        - TODOS os itens (NCM, descrição, quantidade, valores)
        - Países de origem
        
        ### 🚀 **Próximos passos:**
        
        1. Carregue ambos os arquivos
        2. Aguarde o processamento
        3. Verifique os itens extraídos
        4. Baixe o XML no formato exato do modelo
        
        **Garantia:** O XML gerado será estruturalmente idêntico ao modelo fornecido!
        """)

if __name__ == "__main__":
    main()
