import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pdfplumber
import re
import base64
import io
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import tempfile
import os

# ==============================================
# CONSTANTES E CONFIGURAÇÕES
# ==============================================

XML_TEMPLATE = {
    'adicao': {
        'acrescimo': {
            'codigoAcrescimo': '17',
            'denominacao': 'OUTROS ACRESCIMOS AO VALOR ADUANEIRO                        ',
            'moedaNegociadaCodigo': '978',
            'moedaNegociadaNome': 'EURO/COM.EUROPEIA',
            'valorMoedaNegociada': '000000000000000',
            'valorReais': '000000000000000'
        },
        'cideValorAliquotaEspecifica': '00000000000',
        'cideValorDevido': '000000000000000',
        'cideValorRecolher': '000000000000000',
        'codigoRelacaoCompradorVendedor': '3',
        'codigoVinculoCompradorVendedor': '1',
        'cofinsAliquotaAdValorem': '00965',
        'cofinsAliquotaEspecificaQuantidadeUnidade': '000000000',
        'cofinsAliquotaEspecificaValor': '0000000000',
        'cofinsAliquotaReduzida': '00000',
        'cofinsAliquotaValorDevido': '000000000000000',
        'cofinsAliquotaValorRecolher': '000000000000000',
        'condicaoVendaIncoterm': 'FCA',
        'condicaoVendaLocal': 'INF NAO ENCONTRADA',
        'condicaoVendaMetodoValoracaoCodigo': '01',
        'condicaoVendaMetodoValoracaoNome': 'METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)',
        'condicaoVendaMoedaCodigo': '978',
        'condicaoVendaMoedaNome': 'EURO/COM.EUROPEIA',
        'condicaoVendaValorMoeda': '000000000000000',
        'condicaoVendaValorReais': '000000000000000',
        'dadosCambiaisCoberturaCambialCodigo': '1',
        'dadosCambiaisCoberturaCambialNome': "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180",
        'dadosCambiaisInstituicaoFinanciadoraCodigo': '00',
        'dadosCambiaisInstituicaoFinanciadoraNome': 'N/I',
        'dadosCambiaisMotivoSemCoberturaCodigo': '00',
        'dadosCambiaisMotivoSemCoberturaNome': 'N/I',
        'dadosCambiaisValorRealCambio': '000000000000000',
        'dadosCargaPaisProcedenciaCodigo': '000',
        'dadosCargaUrfEntradaCodigo': '0000000',
        'dadosCargaViaTransporteCodigo': '01',
        'dadosCargaViaTransporteNome': 'MARÍTIMA',
        'dadosMercadoriaAplicacao': 'REVENDA',
        'dadosMercadoriaCodigoNaladiNCCA': '0000000',
        'dadosMercadoriaCodigoNaladiSH': '00000000',
        'dadosMercadoriaCodigoNcm': '00000000',
        'dadosMercadoriaCondicao': 'NOVA',
        'dadosMercadoriaDescricaoTipoCertificado': 'Sem Certificado',
        'dadosMercadoriaIndicadorTipoCertificado': '1',
        'dadosMercadoriaMedidaEstatisticaQuantidade': '000000000000000',
        'dadosMercadoriaMedidaEstatisticaUnidade': 'QUILOGRAMA LIQUIDO',
        'dadosMercadoriaNomeNcm': 'INF NAO ENCONTRADA',
        'dadosMercadoriaPesoLiquido': '000000000000000',
        'dcrCoeficienteReducao': '00000',
        'dcrIdentificacao': '00000000',
        'dcrValorDevido': '000000000000000',
        'dcrValorDolar': '000000000000000',
        'dcrValorReal': '000000000000000',
        'dcrValorRecolher': '000000000000000',
        'fornecedorCidade': 'INF NAO ENCONTRADA',
        'fornecedorLogradouro': 'INF NAO ENCONTRADA',
        'fornecedorNome': 'INF NAO ENCONTRADA',
        'fornecedorNumero': '000',
        'freteMoedaNegociadaCodigo': '978',
        'freteMoedaNegociadaNome': 'EURO/COM.EUROPEIA',
        'freteValorMoedaNegociada': '000000000000000',
        'freteValorReais': '000000000000000',
        'iiAcordoTarifarioTipoCodigo': '0',
        'iiAliquotaAcordo': '00000',
        'iiAliquotaAdValorem': '01800',
        'iiAliquotaPercentualReducao': '00000',
        'iiAliquotaReduzida': '00000',
        'iiAliquotaValorCalculado': '000000000000000',
        'iiAliquotaValorDevido': '000000000000000',
        'iiAliquotaValorRecolher': '000000000000000',
        'iiAliquotaValorReduzido': '000000000000000',
        'iiBaseCalculo': '000000000000000',
        'iiFundamentoLegalCodigo': '00',
        'iiMotivoAdmissaoTemporariaCodigo': '00',
        'iiRegimeTributacaoCodigo': '1',
        'iiRegimeTributacaoNome': 'RECOLHIMENTO INTEGRAL',
        'ipiAliquotaAdValorem': '00325',
        'ipiAliquotaEspecificaCapacidadeRecipciente': '00000',
        'ipiAliquotaEspecificaQuantidadeUnidadeMedida': '000000000',
        'ipiAliquotaEspecificaTipoRecipienteCodigo': '00',
        'ipiAliquotaEspecificaValorUnidadeMedida': '0000000000',
        'ipiAliquotaNotaComplementarTIPI': '00',
        'ipiAliquotaReduzida': '00000',
        'ipiAliquotaValorDevido': '000000000000000',
        'ipiAliquotaValorRecolher': '000000000000000',
        'ipiRegimeTributacaoCodigo': '4',
        'ipiRegimeTributacaoNome': 'SEM BENEFICIO',
        'mercadoria': {
            'descricaoMercadoria': 'INF NAO ENCONTRADA                                                                                                     ',
            'numeroSequencialItem': '01',
            'quantidade': '00000000000000',
            'unidadeMedida': 'PECA                ',
            'valorUnitario': '00000000000000000000'
        },
        'numeroAdicao': '001',
        'numeroDUIMP': '0000000000',
        'numeroLI': '0000000000',
        'paisAquisicaoMercadoriaCodigo': '000',
        'paisAquisicaoMercadoriaNome': 'INF NAO ENCONTRADA',
        'paisOrigemMercadoriaCodigo': '000',
        'paisOrigemMercadoriaNome': 'INF NAO ENCONTRADA',
        'pisCofinsBaseCalculoAliquotaICMS': '00000',
        'pisCofinsBaseCalculoFundamentoLegalCodigo': '00',
        'pisCofinsBaseCalculoPercentualReducao': '00000',
        'pisCofinsBaseCalculoValor': '000000000000000',
        'pisCofinsFundamentoLegalReducaoCodigo': '00',
        'pisCofinsRegimeTributacaoCodigo': '1',
        'pisCofinsRegimeTributacaoNome': 'RECOLHIMENTO INTEGRAL',
        'pisPasepAliquotaAdValorem': '00210',
        'pisPasepAliquotaEspecificaQuantidadeUnidade': '000000000',
        'pisPasepAliquotaEspecificaValor': '0000000000',
        'pisPasepAliquotaReduzida': '00000',
        'pisPasepAliquotaValorDevido': '000000000000000',
        'pisPasepAliquotaValorRecolher': '000000000000000',
        'icmsBaseCalculoValor': '000000000000000',
        'icmsBaseCalculoAliquota': '01800',
        'icmsBaseCalculoValorImposto': '000000000000000',
        'icmsBaseCalculoValorDiferido': '000000000000000',
        'cbsIbsCst': '000',
        'cbsIbsClasstrib': '000001',
        'cbsBaseCalculoValor': '000000000000000',
        'cbsBaseCalculoAliquota': '00090',
        'cbsBaseCalculoAliquotaReducao': '00000',
        'cbsBaseCalculoValorImposto': '000000000000000',
        'ibsBaseCalculoValor': '000000000000000',
        'ibsBaseCalculoAliquota': '00010',
        'ibsBaseCalculoAliquotaReducao': '00000',
        'ibsBaseCalculoValorImposto': '000000000000000',
        'relacaoCompradorVendedor': 'Fabricante é desconhecido',
        'seguroMoedaNegociadaCodigo': '220',
        'seguroMoedaNegociadaNome': 'DOLAR DOS EUA',
        'seguroValorMoedaNegociada': '000000000000000',
        'seguroValorReais': '000000000000000',
        'sequencialRetificacao': '00',
        'valorMultaARecolher': '000000000000000',
        'valorMultaARecolherAjustado': '000000000000000',
        'valorReaisFreteInternacional': '000000000000000',
        'valorReaisSeguroInternacional': '000000000000000',
        'valorTotalCondicaoVenda': '00000000000',
        'vinculoCompradorVendedor': 'Não há vinculação entre comprador e vendedor.'
    },
    'duimp': {
        'armazem': {'nomeArmazem': 'INF NAO ENCONTRADA'},
        'armazenamentoRecintoAduaneiroCodigo': '0000000',
        'armazenamentoRecintoAduaneiroNome': 'INF NAO ENCONTRADA',
        'armazenamentoSetor': '002',
        'canalSelecaoParametrizada': '001',
        'caracterizacaoOperacaoCodigoTipo': '1',
        'caracterizacaoOperacaoDescricaoTipo': 'Importação Própria',
        'cargaDataChegada': '00000000',
        'cargaNumeroAgente': 'N/I',
        'cargaPaisProcedenciaCodigo': '000',
        'cargaPaisProcedenciaNome': 'INF NAO ENCONTRADA',
        'cargaPesoBruto': '000000000000000',
        'cargaPesoLiquido': '000000000000000',
        'cargaUrfEntradaCodigo': '0000000',
        'cargaUrfEntradaNome': 'INF NAO ENCONTRADA',
        'conhecimentoCargaEmbarqueData': '00000000',
        'conhecimentoCargaEmbarqueLocal': 'INF NAO ENCONTRADA',
        'conhecimentoCargaId': 'INF NAO ENCONTRADA',
        'conhecimentoCargaIdMaster': 'INF NAO ENCONTRADA',
        'conhecimentoCargaTipoCodigo': '12',
        'conhecimentoCargaTipoNome': 'HBL - House Bill of Lading',
        'conhecimentoCargaUtilizacao': '1',
        'conhecimentoCargaUtilizacaoNome': 'Total',
        'dataDesembaraco': '00000000',
        'dataRegistro': '00000000',
        'documentoChegadaCargaCodigoTipo': '1',
        'documentoChegadaCargaNome': 'Manifesto da Carga',
        'documentoChegadaCargaNumero': 'INF NAO ENCONTRADA',
        'documentoInstrucaoDespacho': [],
        'embalagem': {
            'codigoTipoEmbalagem': '60',
            'nomeEmbalagem': 'PALLETS                                                     ',
            'quantidadeVolume': '00000'
        },
        'freteCollect': '000000000000000',
        'freteEmTerritorioNacional': '000000000000000',
        'freteMoedaNegociadaCodigo': '978',
        'freteMoedaNegociadaNome': 'EURO/COM.EUROPEIA',
        'fretePrepaid': '000000000000000',
        'freteTotalDolares': '000000000000000',
        'freteTotalMoeda': '00000',
        'freteTotalReais': '000000000000000',
        'icms': {
            'agenciaIcms': '00000',
            'bancoIcms': '000',
            'codigoTipoRecolhimentoIcms': '3',
            'cpfResponsavelRegistro': '00000000000',
            'dataRegistro': '00000000',
            'horaRegistro': '000000',
            'nomeTipoRecolhimentoIcms': 'Exoneração do ICMS',
            'numeroSequencialIcms': '001',
            'ufIcms': 'XX',
            'valorTotalIcms': '000000000000000'
        },
        'importadorCodigoTipo': '1',
        'importadorCpfRepresentanteLegal': '00000000000',
        'importadorEnderecoBairro': 'INF NAO ENCONTRADA',
        'importadorEnderecoCep': '00000000',
        'importadorEnderecoComplemento': 'INF NAO ENCONTRADA',
        'importadorEnderecoLogradouro': 'INF NAO ENCONTRADA',
        'importadorEnderecoMunicipio': 'INF NAO ENCONTRADA',
        'importadorEnderecoNumero': '0000',
        'importadorEnderecoUf': 'XX',
        'importadorNome': 'INF NAO ENCONTRADA',
        'importadorNomeRepresentanteLegal': 'INF NAO ENCONTRADA',
        'importadorNumero': '00000000000000',
        'importadorNumeroTelefone': '00  00000000',
        'informacaoComplementar': 'INFORMACOES COMPLEMENTARES\n--------------------------\nINF NAO ENCONTRADA',
        'localDescargaTotalDolares': '000000000000000',
        'localDescargaTotalReais': '000000000000000',
        'localEmbarqueTotalDolares': '000000000000000',
        'localEmbarqueTotalReais': '000000000000000',
        'modalidadeDespachoCodigo': '1',
        'modalidadeDespachoNome': 'Normal',
        'numeroDUIMP': '0000000000',
        'operacaoFundap': 'N',
        'pagamento': [],
        'seguroMoedaNegociadaCodigo': '220',
        'seguroMoedaNegociadaNome': 'DOLAR DOS EUA',
        'seguroTotalDolares': '000000000000000',
        'seguroTotalMoedaNegociada': '000000000000000',
        'seguroTotalReais': '000000000000000',
        'sequencialRetificacao': '00',
        'situacaoEntregaCarga': 'INF NAO ENCONTRADA',
        'tipoDeclaracaoCodigo': '01',
        'tipoDeclaracaoNome': 'CONSUMO',
        'totalAdicoes': '000',
        'urfDespachoCodigo': '0000000',
        'urfDespachoNome': 'INF NAO ENCONTRADA',
        'valorTotalMultaARecolherAjustado': '000000000000000',
        'viaTransporteCodigo': '01',
        'viaTransporteMultimodal': 'N',
        'viaTransporteNome': 'MARÍTIMA',
        'viaTransporteNomeTransportador': 'INF NAO ENCONTRADA',
        'viaTransporteNomeVeiculo': 'INF NAO ENCONTRADA',
        'viaTransportePaisTransportadorCodigo': '000',
        'viaTransportePaisTransportadorNome': 'INF NAO ENCONTRADA'
    }
}

# ==============================================
# CLASSES DE PROCESSAMENTO
# ==============================================

class PDFExtractor:
    """Classe para extrair informações de PDFs de DUIMP"""
    
    def __init__(self):
        self.extracted_data = {
            'duimp_info': {},
            'adicoes': [],
            'documentos': [],
            'tributos': {}
        }
    
    def extract_from_pdf(self, pdf_path: str, max_pages: int = 300) -> Dict[str, Any]:
        """Extrai informações do PDF"""
        all_text = ""
        total_pages = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = min(len(pdf.pages), max_pages)
                
                # Barra de progresso
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for page_num in range(total_pages):
                    status_text.text(f"Processando página {page_num + 1} de {total_pages}...")
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"
                    
                    # Atualizar progresso
                    progress_bar.progress((page_num + 1) / total_pages)
                
                progress_bar.empty()
                status_text.empty()
            
            # Processar texto extraído
            self._process_extracted_text(all_text)
            
            return self.extracted_data
            
        except Exception as e:
            st.error(f"Erro ao processar PDF: {str(e)}")
            return self.extracted_data
    
    def _process_extracted_text(self, text: str):
        """Processa o texto extraído do PDF"""
        # Dividir em linhas
        lines = text.split('\n')
        
        # Extrair informações básicas
        self._extract_basic_info(lines)
        
        # Extrair adições
        self._extract_adicoes(text)
        
        # Extrair documentos
        self._extract_documentos(lines)
        
        # Extrair tributos
        self._extract_tributos(text)
    
    def _extract_basic_info(self, lines: List[str]):
        """Extrai informações básicas da DUIMP"""
        info = {}
        
        # Procurar padrões em todas as linhas
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Número da DUIMP
            if 'Extrato da Duimp' in line_clean:
                parts = line_clean.split()
                for part in parts:
                    if '25BR' in part or 'BR' in part and len(part) > 10:
                        info['numero_duimp'] = part.strip('/')
                        break
            
            # CNPJ do importador
            elif 'CNPJ' in line_clean and ('importador' in line_clean.lower() or ':' in line_clean):
                if i + 1 < len(lines):
                    info['cnpj_importador'] = lines[i + 1].strip()
            
            # Nome do importador
            elif 'Nome do importador:' in line_clean or 'Nome do importador :' in line_clean:
                if i + 1 < len(lines):
                    info['nome_importador'] = lines[i + 1].strip()
            
            # Data de embarque
            elif 'DATA DE EMBARQUE' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    info['data_embarque'] = parts[-1].strip()
            
            # Data de chegada
            elif 'DATA DE CHEGADA' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    info['data_chegada'] = parts[-1].strip()
            
            # Peso bruto
            elif 'PESO BRUTO KG' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    info['peso_bruto'] = parts[-1].strip()
            
            # Peso líquido
            elif 'PESO LIQUIDO KG' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    info['peso_liquido'] = parts[-1].strip()
            
            # Via de transporte
            elif 'VIA DE TRANSPORTE' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    info['via_transporte'] = parts[-1].strip()
            
            # País de procedência
            elif 'PAIS DE PROCEDENCIA' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    info['pais_procedencia'] = parts[-1].strip()
            
            # Moeda negociada
            elif 'MOEDA NEGOCIADA' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    info['moeda'] = parts[-1].strip()
            
            # Valor VMLE
            elif 'VALOR NO LOCAL DE EMBARQUE (VMLE)' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    info['valor_vmle'] = parts[-1].strip()
            
            # Valor VMLD
            elif 'VALOR ADUANEIRO/LOCAL DE DESTINO (VMLD)' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    info['valor_vmld'] = parts[-1].strip()
        
        self.extracted_data['duimp_info'] = info
    
    def _extract_adicoes(self, text: str):
        """Extrai informações das adições"""
        adicoes = []
        
        # Procurar seções de itens usando regex
        # Padrão para encontrar itens
        item_patterns = [
            r'Item\s+0000\d.*?(?=Item\s+0000\d|$)',  # Item 00001, Item 00002, etc.
            r'# Extrato da Duimp.*?Item\s+\d+.*?(?=# Extrato da Duimp|$)'  # Formato alternativo
        ]
        
        for pattern in item_patterns:
            matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                section = match.group(0)
                adicao = self._parse_adicao_section(section)
                if adicao:
                    adicoes.append(adicao)
        
        # Se não encontrou com regex, tentar abordagem por linhas
        if not adicoes:
            lines = text.split('\n')
            current_item = {}
            in_item_section = False
            
            for i, line in enumerate(lines):
                line_clean = line.strip()
                
                # Detectar início de item
                if 'Item 0000' in line_clean or 'Item  0000' in line_clean:
                    if current_item:
                        adicoes.append(current_item)
                    current_item = {'item_number': line_clean.split()[-1][:5]}
                    in_item_section = True
                
                elif in_item_section:
                    # Extrair NCM
                    if 'NCM:' in line_clean:
                        parts = line_clean.split(':')
                        if len(parts) > 1:
                            current_item['ncm'] = parts[-1].strip()
                    
                    # Extrair valor total
                    elif 'Valor total na condição de venda:' in line_clean:
                        parts = line_clean.split(':')
                        if len(parts) > 1:
                            current_item['valor_total'] = parts[-1].strip()
                    
                    # Extrair quantidade
                    elif 'Quantidade na unidade estatística:' in line_clean:
                        parts = line_clean.split(':')
                        if len(parts) > 1:
                            current_item['quantidade'] = parts[-1].strip()
                    
                    # Extrair peso líquido
                    elif 'Peso líquido (kg):' in line_clean:
                        parts = line_clean.split(':')
                        if len(parts) > 1:
                            current_item['peso_liquido'] = parts[-1].strip()
                    
                    # Extrair descrição
                    elif 'Detalhamento do Produto:' in line_clean:
                        if i + 1 < len(lines) and lines[i + 1].strip():
                            current_item['descricao'] = lines[i + 1].strip()
                    
                    # Fim da seção (detectado por nova seção ou linha em branco)
                    elif line_clean == '' and current_item.get('descricao'):
                        in_item_section = False
            
            # Adicionar último item
            if current_item:
                adicoes.append(current_item)
        
        self.extracted_data['adicoes'] = adicoes
    
    def _parse_adicao_section(self, section: str) -> Dict[str, Any]:
        """Analisa uma seção de adição"""
        adicao = {}
        lines = section.split('\n')
        
        for line in lines:
            line_clean = line.strip()
            
            # Número do item
            if 'Item' in line_clean and '0000' in line_clean:
                parts = line_clean.split()
                for part in parts:
                    if part.isdigit() and len(part) >= 4:
                        adicao['item_number'] = part.zfill(5)
                        break
            
            # NCM
            elif 'NCM:' in line_clean:
                parts = line_clean.split(':')
                if len(parts) > 1:
                    adicao['ncm'] = parts[-1].strip().split()[0]  # Pegar apenas o código
            
            # Valor total
            elif 'Valor total' in line_clean.lower() and 'venda' in line_clean.lower():
                parts = line_clean.split(':')
                if len(parts) > 1:
                    adicao['valor_total'] = parts[-1].strip()
            
            # Quantidade
            elif 'Quantidade' in line_clean.lower() and 'unidade' in line_clean.lower():
                parts = line_clean.split(':')
                if len(parts) > 1:
                    adicao['quantidade'] = parts[-1].strip()
            
            # Peso líquido
            elif 'Peso líquido' in line_clean.lower():
                parts = line_clean.split(':')
                if len(parts) > 1:
                    adicao['peso_liquido'] = parts[-1].strip()
            
            # Descrição
            elif 'Detalhamento do Produto:' in line_clean:
                desc_start = line_clean.find(':')
                if desc_start > 0:
                    desc = line_clean[desc_start + 1:].strip()
                    if desc:
                        adicao['descricao'] = desc
        
        return adicao if adicao else None
    
    def _extract_documentos(self, lines: List[str]):
        """Extrai informações de documentos"""
        documentos = []
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Conhecimento de embarque
            if 'CONHECIMENTO DE EMBARQUE' in line_clean or 'Número:' in line_clean and 'NGBS' in line_clean:
                if 'NGBS' in line_clean:
                    num_start = line_clean.find('NGBS')
                    if num_start >= 0:
                        num = line_clean[num_start:num_start + 12]  # Aproximadamente
                        documentos.append({
                            'tipo': 'CONHECIMENTO DE CARGA',
                            'numero': num,
                            'codigo_tipo': '28'
                        })
            
            # Fatura comercial
            elif 'FATURA COMERCIAL' in line_clean or 'FHI' in line_clean:
                if 'FHI' in line_clean:
                    num_start = line_clean.find('FHI')
                    if num_start >= 0:
                        num = line_clean[num_start:num_start + 12]
                        documentos.append({
                            'tipo': 'FATURA COMERCIAL',
                            'numero': num,
                            'codigo_tipo': '01'
                        })
        
        self.extracted_data['documentos'] = documentos
    
    def _extract_tributos(self, text: str):
        """Extrai valores de tributos"""
        tributos = {}
        
        # Padrões para tributos
        patterns = {
            'II': r'II\s*:\s*([\d\.,]+)',
            'PIS': r'PIS\s*:\s*([\d\.,]+)',
            'COFINS': r'COFINS\s*:\s*([\d\.,]+)',
            'TAXA_UTILIZACAO': r'TAXA DE UTILIZACAO\s*:\s*([\d\.,]+)'
        }
        
        for tributo, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                tributos[tributo] = match.group(1).strip()
        
        self.extracted_data['tributos'] = tributos

class XMLBuilder:
    """Classe para construir o XML completo"""
    
    def __init__(self):
        self.template = XML_TEMPLATE.copy()
    
    def build_xml(self, extracted_data: Dict[str, Any]) -> str:
        """Constrói o XML completo a partir dos dados extraídos"""
        # Criar elemento raiz
        lista_declaracoes = ET.Element('ListaDeclaracoes')
        duimp = ET.SubElement(lista_declaracoes, 'duimp')
        
        # Adicionar adições
        self._add_adicoes(duimp, extracted_data)
        
        # Adicionar dados gerais da DUIMP
        self._add_duimp_data(duimp, extracted_data)
        
        # Adicionar documentos
        self._add_documentos(duimp, extracted_data)
        
        # Adicionar pagamentos
        self._add_pagamentos(duimp, extracted_data)
        
        # Converter para string formatada
        xml_string = ET.tostring(lista_declaracoes, encoding='utf-8', method='xml')
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ", encoding='utf-8')
        
        return pretty_xml.decode('utf-8')
    
    def _add_adicoes(self, parent, data: Dict[str, Any]):
        """Adiciona as adições ao XML"""
        adicoes_data = data.get('adicoes', [])
        duimp_info = data.get('duimp_info', {})
        
        for idx, adicao_data in enumerate(adicoes_data, 1):
            adicao = ET.SubElement(parent, 'adicao')
            
            # Usar template e atualizar com dados reais
            adicao_template = self.template['adicao'].copy()
            
            # Atualizar campos com dados extraídos
            self._update_adicao_template(adicao_template, adicao_data, duimp_info, idx)
            
            # Adicionar todos os elementos da adição
            self._add_adicao_elements(adicao, adicao_template)
    
    def _update_adicao_template(self, template: Dict, data: Dict, duimp_info: Dict, idx: int):
        """Atualiza o template da adição com dados reais"""
        # Número da adição
        template['numeroAdicao'] = f"{idx:03d}"
        
        # Número da DUIMP
        if 'numero_duimp' in duimp_info:
            template['numeroDUIMP'] = duimp_info['numero_duimp'].replace('-', '').replace('/', '').replace('.', '')
        
        # NCM
        if 'ncm' in data:
            ncm_clean = data['ncm'].replace('.', '').replace(' ', '')
            template['dadosMercadoriaCodigoNcm'] = ncm_clean[:8].ljust(8, '0')
            template['dadosMercadoriaNomeNcm'] = data.get('descricao', 'INF NAO ENCONTRADA')[:100]
        
        # Valor total
        if 'valor_total' in data:
            valor_clean = self._clean_number(data['valor_total'])
            template['condicaoVendaValorMoeda'] = valor_clean.zfill(15)
            template['valorTotalCondicaoVenda'] = valor_clean[:11].zfill(11)
        
        # Quantidade
        if 'quantidade' in data:
            qtd_clean = self._clean_number(data['quantidade'], decimal_places=5)
            template['mercadoria']['quantidade'] = qtd_clean.zfill(14)
        
        # Peso líquido
        if 'peso_liquido' in data:
            peso_clean = self._clean_number(data['peso_liquido'], decimal_places=5)
            template['dadosMercadoriaPesoLiquido'] = peso_clean.zfill(15)
            template['dadosMercadoriaMedidaEstatisticaQuantidade'] = peso_clean.zfill(15)
        
        # Descrição da mercadoria
        if 'descricao' in data:
            template['mercadoria']['descricaoMercadoria'] = data['descricao'].ljust(200)[:200]
        
        # Número sequencial do item
        template['mercadoria']['numeroSequencialItem'] = f"{idx:02d}"
        
        # Países
        if 'pais_procedencia' in duimp_info:
            template['paisOrigemMercadoriaNome'] = duimp_info['pais_procedencia']
            template['paisAquisicaoMercadoriaNome'] = duimp_info['pais_procedencia']
        
        # Moeda
        if 'moeda' in duimp_info:
            if 'DOLAR' in duimp_info['moeda'].upper():
                template['condicaoVendaMoedaCodigo'] = '220'
                template['condicaoVendaMoedaNome'] = 'DOLAR DOS EUA'
                template['acrescimo']['moedaNegociadaCodigo'] = '220'
                template['acrescimo']['moedaNegociadaNome'] = 'DOLAR DOS EUA'
                template['freteMoedaNegociadaCodigo'] = '220'
                template['freteMoedaNegociadaNome'] = 'DOLAR DOS EUA'
    
    def _add_adicao_elements(self, parent, template: Dict):
        """Adiciona todos os elementos de uma adição"""
        # Acrescimo
        acrescimo = ET.SubElement(parent, 'acrescimo')
        for key, value in template['acrescimo'].items():
            elem = ET.SubElement(acrescimo, key)
            elem.text = str(value)
        
        # Adicionar todos os outros campos
        fields_to_skip = ['acrescimo', 'mercadoria']
        for key, value in template.items():
            if key not in fields_to_skip:
                elem = ET.SubElement(parent, key)
                elem.text = str(value)
        
        # Mercadoria
        mercadoria = ET.SubElement(parent, 'mercadoria')
        for key, value in template['mercadoria'].items():
            elem = ET.SubElement(mercadoria, key)
            elem.text = str(value)
    
    def _add_duimp_data(self, parent, data: Dict[str, Any]):
        """Adiciona dados gerais da DUIMP"""
        duimp_info = data.get('duimp_info', {})
        adicoes = data.get('adicoes', [])
        tributos = data.get('tributos', {})
        
        # Usar template e atualizar com dados reais
        duimp_template = self.template['duimp'].copy()
        
        # Atualizar campos com dados extraídos
        self._update_duimp_template(duimp_template, duimp_info, adicoes, tributos)
        
        # Adicionar todos os elementos da DUIMP
        self._add_duimp_elements(parent, duimp_template)
    
    def _update_duimp_template(self, template: Dict, duimp_info: Dict, adicoes: List, tributos: Dict):
        """Atualiza o template da DUIMP com dados reais"""
        # Número da DUIMP
        if 'numero_duimp' in duimp_info:
            template['numeroDUIMP'] = duimp_info['numero_duimp'].replace('-', '').replace('/', '').replace('.', '')
        
        # Nome do importador
        if 'nome_importador' in duimp_info:
            template['importadorNome'] = duimp_info['nome_importador'][:100]
        
        # CNPJ do importador
        if 'cnpj_importador' in duimp_info:
            cnpj_clean = duimp_info['cnpj_importador'].replace('.', '').replace('/', '').replace('-', '')
            template['importadorNumero'] = cnpj_clean.ljust(14, '0')
        
        # Datas
        if 'data_embarque' in duimp_info:
            data_emb = self._format_date(duimp_info['data_embarque'])
            template['conhecimentoCargaEmbarqueData'] = data_emb
        
        if 'data_chegada' in duimp_info:
            data_cheg = self._format_date(duimp_info['data_chegada'])
            template['cargaDataChegada'] = data_cheg
        
        # Usar data atual para registro
        today = datetime.now().strftime('%Y%m%d')
        template['dataRegistro'] = today
        template['dataDesembaraco'] = today
        template['icms']['dataRegistro'] = today
        
        # Pesos
        if 'peso_bruto' in duimp_info:
            peso_bruto_clean = self._clean_number(duimp_info['peso_bruto'], decimal_places=4)
            template['cargaPesoBruto'] = peso_bruto_clean.zfill(15)
        
        if 'peso_liquido' in duimp_info:
            peso_liq_clean = self._clean_number(duimp_info['peso_liquido'], decimal_places=4)
            template['cargaPesoLiquido'] = peso_liq_clean.zfill(15)
        
        # País de procedência
        if 'pais_procedencia' in duimp_info:
            template['cargaPaisProcedenciaNome'] = duimp_info['pais_procedencia']
        
        # Via de transporte
        if 'via_transporte' in duimp_info:
            if 'MAR' in duimp_info['via_transporte'].upper():
                template['viaTransporteNome'] = 'MARÍTIMA'
                template['viaTransporteCodigo'] = '01'
        
        # Valores
        if 'valor_vmle' in duimp_info:
            vmle_clean = self._clean_number(duimp_info['valor_vmle'])
            template['localEmbarqueTotalDolares'] = vmle_clean.zfill(15)
        
        if 'valor_vmld' in duimp_info:
            vmld_clean = self._clean_number(duimp_info['valor_vmld'])
            template['localDescargaTotalDolares'] = vmld_clean.zfill(15)
        
        # Total de adições
        template['totalAdicoes'] = f"{len(adicoes):03d}"
        
        # Informação complementar
        info_complementar = "INFORMACOES COMPLEMENTARES\n--------------------------\n"
        for key, value in duimp_info.items():
            info_complementar += f"{key}: {value}\n"
        
        if tributos:
            info_complementar += "\nTRIBUTOS:\n"
            for tributo, valor in tributos.items():
                info_complementar += f"{tributo}: {valor}\n"
        
        template['informacaoComplementar'] = info_complementar
    
    def _add_duimp_elements(self, parent, template: Dict):
        """Adiciona todos os elementos da DUIMP"""
        # Campos especiais (estruturas aninhadas)
        special_fields = ['armazem', 'embalagem', 'icms', 'documentoInstrucaoDespacho', 'pagamento']
        
        for key, value in template.items():
            if key in special_fields:
                if key == 'armazem':
                    armazem = ET.SubElement(parent, 'armazem')
                    elem = ET.SubElement(armazem, 'nomeArmazem')
                    elem.text = str(value['nomeArmazem'])
                
                elif key == 'embalagem':
                    embalagem = ET.SubElement(parent, 'embalagem')
                    for sub_key, sub_value in value.items():
                        elem = ET.SubElement(embalagem, sub_key)
                        elem.text = str(sub_value)
                
                elif key == 'icms':
                    icms = ET.SubElement(parent, 'icms')
                    for sub_key, sub_value in value.items():
                        elem = ET.SubElement(icms, sub_key)
                        elem.text = str(sub_value)
                
                elif key == 'documentoInstrucaoDespacho':
                    for doc in value:
                        documento = ET.SubElement(parent, 'documentoInstrucaoDespacho')
                        for doc_key, doc_value in doc.items():
                            elem = ET.SubElement(documento, doc_key)
                            elem.text = str(doc_value)
                
                elif key == 'pagamento':
                    for pag in value:
                        pagamento = ET.SubElement(parent, 'pagamento')
                        for pag_key, pag_value in pag.items():
                            elem = ET.SubElement(pagamento, pag_key)
                            elem.text = str(pag_value)
            
            else:
                elem = ET.SubElement(parent, key)
                elem.text = str(value)
    
    def _add_documentos(self, parent, data: Dict[str, Any]):
        """Adiciona documentos ao XML"""
        documentos = data.get('documentos', [])
        
        for doc in documentos:
            documento = ET.SubElement(parent, 'documentoInstrucaoDespacho')
            
            ET.SubElement(documento, 'codigoTipoDocumentoDespacho').text = doc.get('codigo_tipo', '00')
            ET.SubElement(documento, 'nomeDocumentoDespacho').text = doc.get('tipo', 'DOCUMENTO NAO IDENTIFICADO').ljust(60)
            ET.SubElement(documento, 'numeroDocumentoDespacho').text = doc.get('numero', 'S/N').ljust(25)
    
    def _add_pagamentos(self, parent, data: Dict[str, Any]):
        """Adiciona pagamentos ao XML"""
        tributos = data.get('tributos', {})
        
        # Criar pagamentos baseados nos tributos
        receitas = [
            ('0086', 'II'),
            ('1038', 'IPI'),
            ('5602', 'PIS'),
            ('5629', 'COFINS'),
            ('7811', 'TAXA DE UTILIZACAO')
        ]
        
        for codigo, tributo in receitas:
            if tributo in tributos:
                valor_clean = self._clean_number(tributos[tributo])
            else:
                valor_clean = '000000000000000'
            
            pagamento = ET.SubElement(parent, 'pagamento')
            
            ET.SubElement(pagamento, 'agenciaPagamento').text = '3715 '
            ET.SubElement(pagamento, 'bancoPagamento').text = '341'
            ET.SubElement(pagamento, 'codigoReceita').text = codigo
            ET.SubElement(pagamento, 'codigoTipoPagamento').text = '1'
            ET.SubElement(pagamento, 'contaPagamento').text = '             316273'
            ET.SubElement(pagamento, 'dataPagamento').text = datetime.now().strftime('%Y%m%d')
            ET.SubElement(pagamento, 'nomeTipoPagamento').text = 'Débito em Conta'
            ET.SubElement(pagamento, 'numeroRetificacao').text = '00'
            ET.SubElement(pagamento, 'valorJurosEncargos').text = '000000000'
            ET.SubElement(pagamento, 'valorMulta').text = '000000000'
            ET.SubElement(pagamento, 'valorReceita').text = valor_clean.zfill(15)
    
    def _clean_number(self, number_str: str, decimal_places: int = 2) -> str:
        """Limpa e formata números"""
        if not number_str:
            return '0'
        
        # Remover todos os caracteres não numéricos exceto vírgula e ponto
        cleaned = re.sub(r'[^\d,]', '', number_str)
        
        # Substituir vírgula por nada (para formato sem decimais no XML)
        if ',' in cleaned:
            # Separar parte inteira e decimal
            parts = cleaned.split(',')
            inteira = parts[0]
            decimal = parts[1][:decimal_places] if len(parts) > 1 else '0'
            
            # Combinar (sem separador decimal)
            cleaned = inteira + decimal.ljust(decimal_places, '0')
        else:
            # Se não tem vírgula, adicionar zeros decimais
            cleaned = cleaned + '0' * decimal_places
        
        return cleaned
    
    def _format_date(self, date_str: str) -> str:
        """Formata data para AAAAMMDD"""
        if not date_str:
            return '00000000'
        
        # Tentar diferentes formatos
        patterns = [
            r'(\d{2})/(\d{2})/(\d{4})',
            r'(\d{2})-(\d{2})-(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, date_str)
            if match:
                groups = match.groups()
                if len(groups[0]) == 4:  # Formato AAAA-MM-DD
                    return f"{groups[0]}{groups[1]}{groups[2]}"
                else:  # Formato DD/MM/AAAA
                    return f"{groups[2]}{groups[1]}{groups[0]}"
        
        return datetime.now().strftime('%Y%m%d')

# ==============================================
# FUNÇÕES AUXILIARES
# ==============================================

def save_uploaded_file(uploaded_file) -> str:
    """Salva arquivo upload em temp file"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name

def generate_pdf_preview(pdf_path: str):
    """Gera preview da primeira página do PDF"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        img_data = pix.tobytes("png")
        doc.close()
        return img_data
    except:
        return None

def get_download_link(xml_content: str, filename: str) -> str:
    """Gera link para download do XML"""
    b64 = base64.b64encode(xml_content.encode()).decode()
    return f'<a href="data:application/xml;base64,{b64}" download="{filename}" style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">📥 Baixar XML</a>'

# ==============================================
# APLICAÇÃO STREAMLIT
# ==============================================

def main():
    """Função principal da aplicação"""
    st.set_page_config(
        page_title="Conversor PDF DUIMP para XML",
        page_icon="🔄",
        layout="wide"
    )
    
    # CSS personalizado
    st.markdown("""
    <style>
    .main-title {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #4B5563;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #EFF6FF;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #3B82F6;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #D1FAE5;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #10B981;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #FEF3C7;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #F59E0B;
        margin-bottom: 1rem;
    }
    .stButton > button {
        background-color: #3B82F6;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 5px;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #2563EB;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Cabeçalho
    st.markdown('<h1 class="main-title">🔄 CONVERSOR PDF DUIMP PARA XML</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="sub-title">Converte extratos de DUIMP em PDF para XML estruturado completo</h3>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Layout principal
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📤 UPLOAD DO PDF")
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo PDF da DUIMP",
            type=['pdf'],
            help="Faça upload do extrato da DUIMP no formato PDF (suporte até 300 páginas)"
        )
        
        if uploaded_file is not None:
            # Salvar arquivo temporariamente
            temp_file_path = save_uploaded_file(uploaded_file)
            
            # Informações do arquivo
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.markdown(f"""
            <div class="info-box">
            <h4>📄 Arquivo Carregado</h4>
            <p><strong>Nome:</strong> {uploaded_file.name}</p>
            <p><strong>Tamanho:</strong> {file_size_mb:.2f} MB</p>
            <p><strong>Formato:</strong> PDF</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Preview do PDF
            st.markdown("### 👁️ PREVIEW DO PDF")
            try:
                img_data = generate_pdf_preview(temp_file_path)
                if img_data:
                    st.image(img_data, caption="Primeira página do PDF", use_column_width=True)
                else:
                    st.info("⚠️ Não foi possível gerar o preview do PDF. Certifique-se de que o arquivo é um PDF válido.")
            except:
                st.info("⚠️ A visualização do PDF requer a biblioteca PyMuPDF. Use 'pip install PyMuPDF' para habilitar.")
            
            # Botão de conversão
            st.markdown("---")
            if st.button("🚀 CONVERTER PDF PARA XML", use_container_width=True):
                with st.spinner("🔄 Processando PDF..."):
                    try:
                        # Inicializar extrator
                        extractor = PDFExtractor()
                        
                        # Extrair dados do PDF
                        extracted_data = extractor.extract_from_pdf(temp_file_path, max_pages=300)
                        
                        # Inicializar builder XML
                        builder = XMLBuilder()
                        
                        # Gerar XML
                        xml_content = builder.build_xml(extracted_data)
                        
                        # Salvar em session state
                        st.session_state.xml_content = xml_content
                        st.session_state.extracted_data = extracted_data
                        st.session_state.filename = f"DUIMP_{extracted_data['duimp_info'].get('numero_duimp', 'DESCONHECIDO').replace('-', '_')}.xml"
                        
                        st.markdown('<div class="success-box"><h4>✅ CONVERSÃO CONCLUÍDA!</h4><p>O XML foi gerado com todas as tags necessárias.</p></div>', unsafe_allow_html=True)
                        
                        # Limpar arquivo temporário
                        os.unlink(temp_file_path)
                        
                    except Exception as e:
                        st.error(f"❌ ERRO NA CONVERSÃO: {str(e)}")
                        st.markdown("""
                        <div class="warning-box">
                        <h4>⚠️ TENTANDO ESTRUTURA PADRÃO</h4>
                        <p>O sistema tentará gerar um XML com estrutura padrão.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        try:
                            # Usar dados mínimos para gerar XML
                            builder = XMLBuilder()
                            xml_content = builder.build_xml({'duimp_info': {}, 'adicoes': [], 'documentos': [], 'tributos': {}})
                            st.session_state.xml_content = xml_content
                            st.session_state.extracted_data = {}
                            st.session_state.filename = "DUIMP_PADRAO.xml"
                            
                            # Limpar arquivo temporário
                            if os.path.exists(temp_file_path):
                                os.unlink(temp_file_path)
                                
                        except Exception as e2:
                            st.error(f"❌ ERRO CRÍTICO: {str(e2)}")
    
    with col2:
        st.markdown("### 📄 RESULTADO XML")
        
        if 'xml_content' in st.session_state:
            xml_content = st.session_state.xml_content
            
            # Estatísticas
            st.markdown("#### 📊 ESTATÍSTICAS DO XML")
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            
            with col_stat1:
                total_adicoes = len(st.session_state.extracted_data.get('adicoes', [])) if 'extracted_data' in st.session_state else 0
                st.markdown(f"""
                <div class="metric-card">
                <h3>{total_adicoes}</h3>
                <p>Adições</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_stat2:
                lines = len(xml_content.split('\n'))
                st.markdown(f"""
                <div class="metric-card">
                <h3>{lines:,}</h3>
                <p>Linhas</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_stat3:
                tags = len(re.findall(r'<(\w+)>', xml_content))
                st.markdown(f"""
                <div class="metric-card">
                <h3>{tags:,}</h3>
                <p>Tags</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Visualização do XML
            with st.expander("👁️ VISUALIZAR XML COMPLETO", expanded=True):
                # Mostrar primeiras 500 linhas para performance
                preview_lines = xml_content.split('\n')[:500]
                preview = '\n'.join(preview_lines)
                if len(xml_content.split('\n')) > 500:
                    preview += f"\n\n... [{len(xml_content.split('\n')) - 500} linhas restantes - baixe o arquivo para ver completo] ..."
                
                st.code(preview, language="xml")
            
            # Download
            st.markdown("---")
            st.markdown("#### 💾 DOWNLOAD DO XML")
            st.markdown(get_download_link(xml_content, st.session_state.filename), unsafe_allow_html=True)
            
            # Validação
            st.markdown("---")
            st.markdown("#### ✅ VALIDAÇÃO DO XML")
            try:
                ET.fromstring(xml_content)
                st.markdown('<div class="success-box"><h4>✅ XML VÁLIDO</h4><p>O arquivo XML está bem formado e pronto para uso.</p></div>', unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f'<div class="warning-box"><h4>⚠️ PROBLEMA NA VALIDAÇÃO</h4><p>{str(e)[:200]}</p></div>', unsafe_allow_html=True)
            
            # Informações extraídas
            if 'extracted_data' in st.session_state and st.session_state.extracted_data:
                with st.expander("📋 INFORMAÇÕES EXTRAÍDAS DO PDF"):
                    st.json(st.session_state.extracted_data)
        
        else:
            st.markdown("""
            <div class="info-box">
            <h4>📋 AGUARDANDO CONVERSÃO</h4>
            <p>Após o upload e conversão do PDF, o XML será gerado aqui.</p>
            <p><strong>Características do XML gerado:</strong></p>
            <ul>
            <li>✅ Layout completo conforme especificação</li>
            <li>✅ Todas as tags obrigatórias incluídas</li>
            <li>✅ "INF NAO ENCONTRADA" para campos não identificados</li>
            <li>✅ Suporte a PDFs de até 300 páginas</li>
            <li>✅ Processamento robusto com tratamento de erros</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
    
    # Informações adicionais
    st.markdown("---")
    with st.expander("📚 INFORMAÇÕES TÉCNICAS"):
        st.markdown("""
        ### 🏗️ ESTRUTURA DO XML GERADO
        
        **Tags Incluídas (100% completas):**
        
        **1. Adições (adicao):**
        - acrescimo (com todos os sub-elementos)
        - cideValorAliquotaEspecifica
        - codigoRelacaoCompradorVendedor
        - cofinsAliquotaAdValorem (e todos os campos relacionados)
        - condicaoVendaIncoterm
        - dadosCambiais (todos os campos)
        - dadosCarga (todos os campos)
        - dadosMercadoria (todos os campos)
        - dcr (todos os campos)
        - fornecedor (todos os campos)
        - frete (todos os campos)
        - ii (todos os campos - Imposto de Importação)
        - ipi (todos os campos)
        - mercadoria (com descricaoMercadoria, quantidade, etc.)
        - numeroAdicao, numeroDUIMP, numeroLI
        - paisAquisicaoMercadoria, paisOrigemMercadoria
        - pisCofins (todos os campos)
        - pisPasep (todos os campos)
        - icmsBaseCalculo (todos os campos)
        - cbsIbs (todos os campos)
        - relacaoCompradorVendedor, vinculoCompradorVendedor
        - seguro (todos os campos)
        - sequencialRetificacao
        - valorMultaARecolher, valorReaisFreteInternacional, etc.
        - valorTotalCondicaoVenda
        
        **2. Dados Gerais da DUIMP:**
        - armazem
        - armazenamentoRecintoAduaneiro
        - canalSelecaoParametrizada
        - caracterizacaoOperacao
        - carga (todos os campos)
        - conhecimentoCarga (todos os campos)
        - dataDesembaraco, dataRegistro
        - documentoChegadaCarga
        - documentoInstrucaoDespacho (múltiplos)
        - embalagem
        - freteCollect, freteTotalDolares, etc.
        - icms (estrutura completa)
        - importador (todos os campos)
        - informacaoComplementar
        - localDescargaTotalDolares, localEmbarqueTotalDolares
        - modalidadeDespacho
        - operacaoFundap
        - pagamento (múltiplos)
        - seguroMoedaNegociadaCodigo, seguroTotalDolares, etc.
        - situacaoEntregaCarga
        - tipoDeclaracao
        - totalAdicoes
        - urfDespacho
        - viaTransporte (todos os campos)
        
        ### 🔍 PROCESSAMENTO DO PDF
        
        **Campos Extraídos Automaticamente:**
        - Número da DUIMP
        - CNPJ e nome do importador
        - Datas de embarque e chegada
        - Pesos bruto e líquido
        - Valores (VMLE, VMLD)
        - Itens (NCM, descrição, quantidade, valor)
        - Documentos (conhecimento, fatura)
        - Tributos (II, PIS, COFINS, etc.)
        
        **Fallback para Campos Não Encontrados:**
        - Todos os campos não identificados recebem "INF NAO ENCONTRADA"
        - Valores numéricos recebem zeros
        - Estrutura XML sempre completa
        
        ### ⚙️ DESEMPENHO
        
        - Processa PDFs de até 300 páginas
        - Barra de progresso durante extração
        - Uso eficiente de memória
        - Geração rápida de XML
        - Preview da primeira página do PDF
        
        ### 🛡️ TRATAMENTO DE ERROS
        
        - Processamento seguro sem erros de índice
        - Fallback para estrutura padrão em caso de falha
        - Validação do XML gerado
        - Mensagens de erro claras
        """)
    
    # Footer
    st.markdown("---")
    st.caption("🛠️ Sistema de Conversão PDF DUIMP para XML Completo | v4.0 | Suporte a 300+ páginas")

if __name__ == "__main__":
    main()
