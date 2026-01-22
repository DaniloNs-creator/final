import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pdfplumber
import re
import json
from typing import Dict, List, Tuple, Optional, Any
import tempfile
import os
import io
from dataclasses import dataclass
from collections import defaultdict
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da página
st.set_page_config(
    page_title="Sistema Completo de Análise Häfele - PDF APP2",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        color: #1E3A8A;
        font-weight: bold;
        margin-bottom: 1rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #2563EB;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 3px solid #E5E7EB;
        padding-bottom: 0.5rem;
        font-weight: 600;
    }
    .section-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
        border: 1px solid #E5E7EB;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: bold;
        color: #1E3A8A;
        line-height: 1;
    }
    .metric-label {
        font-size: 1rem;
        color: #6B7280;
        margin-top: 0.5rem;
        font-weight: 500;
    }
    .info-box {
        background-color: #F0F9FF;
        border-left: 4px solid #1E3A8A;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
    }
    .warning-box {
        background-color: #FEF3C7;
        border-left: 4px solid #D97706;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
    }
    .success-box {
        background-color: #D1FAE5;
        border-left: 4px solid #059669;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
    }
    .table-header {
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
        padding: 8px;
    }
</style>
""", unsafe_allow_html=True)

class HafelePDFParser:
    """Parser robusto para PDFs da Häfele (Layout APP2.pdf)"""
    
    def __init__(self):
        self.documento = {
            'cabecalho': {},
            'itens': [],
            'totais': {},
            'carga': {},
            'transporte': {},
            'moedas': {}
        }
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        """Parse completo do PDF"""
        try:
            logger.info(f"Iniciando parsing do PDF: {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"PDF com {total_pages} páginas")
                
                all_text = ""
                for page_num, page in enumerate(pdf.pages, 1):
                    logger.info(f"Processando página {page_num}/{total_pages}")
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n--- PAGE BREAK ---\n"
            
            # Processar todo o texto
            self._process_full_text(all_text)
            
            logger.info(f"Parsing concluído. {len(self.documento['itens'])} itens processados.")
            return self.documento
            
        except Exception as e:
            logger.error(f"Erro no parsing: {str(e)}")
            raise
    
    def _process_full_text(self, text: str):
        """Processa todo o texto do PDF"""
        # Extrair informações do cabeçalho
        self._extract_header_info(text)
        
        # Extrair informações de moedas
        self._extract_currency_info(text)
        
        # Extrair informações de carga
        self._extract_carga_info(text)
        
        # Encontrar todos os itens
        items = self._find_all_items(text)
        self.documento['itens'] = items
        
        # Extrair informações de transporte
        self._extract_transporte_info(text)
        
        # Extrair totais
        self._extract_totais(text)
        
        # Calcular totais
        self._calculate_totals()
    
    def _extract_header_info(self, text: str):
        """Extrai informações do cabeçalho"""
        header_info = {}
        
        # Processo
        processo_match = re.search(r'PROCESSO\s*#(\d+)', text)
        if processo_match:
            header_info['processo'] = processo_match.group(1)
        
        # Importador
        importador_match = re.search(r'IMPORTADOR\s+(.+?)\s+CNPJ', text, re.DOTALL)
        if importador_match:
            header_info['importador'] = importador_match.group(1).strip()
        
        cnpj_match = re.search(r'CNPJ\s+([\d\.\/\-]+)', text)
        if cnpj_match:
            header_info['cnpj'] = cnpj_match.group(1)
        
        # Identificação
        ident_match = re.search(r'Identificacao\s+(.+?)\s+Data de Cadastro', text)
        if ident_match:
            header_info['identificacao'] = ident_match.group(1).strip()
        
        data_cad_match = re.search(r'Data de Cadastro\s+(\d{2}/\d{2}/\d{4})', text)
        if data_cad_match:
            header_info['data_cadastro'] = data_cad_match.group(1)
        
        # Responsável
        responsavel_match = re.search(r'Responsavel Legal\s+(.+)', text)
        if responsavel_match:
            header_info['responsavel'] = responsavel_match.group(1).strip()
        
        self.documento['cabecalho'] = header_info
    
    def _extract_currency_info(self, text: str):
        """Extrai informações de moedas e cotações"""
        moedas_info = {}
        
        # Padrão para moedas
        moeda_patterns = [
            r'Moeda Negociada\s+(\d+)\s+-\s+(.+?)\s+Cotacao\s+([\d,\.]+)',
            r'Moeda Frete\s+(\d+)\s+-\s+(.+?)\s+Cotacao\s+([\d,\.]+)',
            r'Moeda Seguro\s+(\d+)\s+-\s+(.+?)\s+Cotacao\s+([\d,\.]+)'
        ]
        
        for pattern in moeda_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                codigo, nome, cotacao = match
                moedas_info[f"{nome.strip()}"] = {
                    'codigo': codigo,
                    'cotacao': self._parse_valor(cotacao)
                }
        
        # Data das cotações
        data_match = re.search(r'MOEDAS/COTACOES - \((\d{2}/\d{2}/\d{4})\)', text)
        if data_match:
            moedas_info['data_cotacao'] = data_match.group(1)
        
        self.documento['moedas'] = moedas_info
    
    def _extract_carga_info(self, text: str):
        """Extrai informações da carga"""
        carga_info = {}
        
        # Via de transporte
        via_match = re.search(r'Via de Transporte\s+(.+?)\s+Num.', text)
        if via_match:
            carga_info['via_transporte'] = via_match.group(1).strip()
        
        # Identificação
        ident_match = re.search(r'Num\. Identificacao\s+(\d+)', text)
        if ident_match:
            carga_info['identificacao_carga'] = ident_match.group(1)
        
        # Datas
        embarque_match = re.search(r'Data de Embarque\s+(\d{2}/\d{2}/\d{4})', text)
        if embarque_match:
            carga_info['data_embarque'] = embarque_match.group(1)
        
        chegada_match = re.search(r'Data de Chegada\s+(\d{2}/\d{2}/\d{4})', text)
        if chegada_match:
            carga_info['data_chegada'] = chegada_match.group(1)
        
        # Pesos
        peso_bruto_match = re.search(r'Peso Bruto\s+([\d\.,]+)', text)
        if peso_bruto_match:
            carga_info['peso_bruto'] = self._parse_valor(peso_bruto_match.group(1))
        
        peso_liquido_match = re.search(r'Peso Liquido\s+([\d\.,]+)', text)
        if peso_liquido_match:
            carga_info['peso_liquido'] = self._parse_valor(peso_liquido_match.group(1))
        
        # Países
        procedencia_match = re.search(r'Pais de Procedencia\s+(.+?)\s*\(', text)
        if procedencia_match:
            carga_info['pais_procedencia'] = procedencia_match.group(1).strip()
        
        # Unidades
        unidade_match = re.search(r'Unidade de Despacho\s+(.+?)\s+Recinto', text)
        if unidade_match:
            carga_info['unidade_despacho'] = unidade_match.group(1).strip()
        
        recinto_match = re.search(r'Recinto\s+(.+?)\s+Unid', text)
        if recinto_match:
            carga_info['recinto'] = recinto_match.group(1).strip()
        
        self.documento['carga'] = carga_info
    
    def _extract_transporte_info(self, text: str):
        """Extrai informações de transporte"""
        transporte_info = {}
        
        # Conhecimento
        conhecimento_match = re.search(r'Tipo Conhecimento\s+(\d+)\s+-\s+(.+)', text)
        if conhecimento_match:
            transporte_info['tipo_conhecimento'] = {
                'codigo': conhecimento_match.group(1),
                'descricao': conhecimento_match.group(2).strip()
            }
        
        # Bandeira/Embarcação
        bandeira_match = re.search(r'Bandeira Embarcacao\s+(.+?)\s+Local', text)
        if bandeira_match:
            transporte_info['bandeira'] = bandeira_match.group(1).strip()
        
        # Local de embarque
        local_emb_match = re.search(r'Local Embarque\s+(.+)', text)
        if local_emb_match:
            transporte_info['local_embarque'] = local_emb_match.group(1).strip()
        
        # Frete
        frete_match = re.search(r'FRETE.*?Total \(Moeda\)\s+([\d\.,]+).*?Total \(R\$\)\s+([\d\.,]+)', text, re.DOTALL)
        if frete_match:
            transporte_info['frete'] = {
                'valor_moeda': self._parse_valor(frete_match.group(1)),
                'valor_real': self._parse_valor(frete_match.group(2))
            }
        
        # Seguro
        seguro_match = re.search(r'SEGURO.*?Total \(Moeda\)\s+([\d\.,]+).*?Total \(R\$\)\s+([\d\.,]+)', text, re.DOTALL)
        if seguro_match:
            transporte_info['seguro'] = {
                'valor_moeda': self._parse_valor(seguro_match.group(1)),
                'valor_real': self._parse_valor(seguro_match.group(2))
            }
        
        self.documento['transporte'] = transporte_info
    
    def _extract_totais(self, text: str):
        """Extrai totais do documento"""
        totais_info = {}
        
        # Valores CIF
        cif_match = re.search(r'CIF \(US\$\)\s+([\d\.,]+).*?CIF \(R\$\)\s+([\d\.,]+)', text, re.DOTALL)
        if cif_match:
            totais_info['cif'] = {
                'usd': self._parse_valor(cif_match.group(1)),
                'brl': self._parse_valor(cif_match.group(2))
            }
        
        # Valores VMLE
        vmle_match = re.search(r'VMLE \(US\$\)\s+([\d\.,]+).*?VMLE \(R\$\)\s+([\d\.,]+)', text, re.DOTALL)
        if vmle_match:
            totais_info['vmle'] = {
                'usd': self._parse_valor(vmle_match.group(1)),
                'brl': self._parse_valor(vmle_match.group(2))
            }
        
        # Valores VMLD
        vmld_match = re.search(r'VMLD \(US\$\)\s+([\d\.,]+).*?VMLD \(R\$\)\s+([\d\.,]+)', text, re.DOTALL)
        if vmld_match:
            totais_info['vmld'] = {
                'usd': self._parse_valor(vmld_match.group(1)),
                'brl': self._parse_valor(vmld_match.group(2))
            }
        
        # Impostos totais
        impostos_section = self._find_impostos_section(text)
        if impostos_section:
            self._parse_total_impostos(impostos_section, totais_info)
        
        self.documento['totais_extraidos'] = totais_info
    
    def _find_all_items(self, text: str) -> List[Dict]:
        """Encontra todos os itens no texto do layout APP2.pdf"""
        items = []
        
        # Encontrar blocos de itens usando padrões específicos do APP2
        sections = text.split('--- PAGE BREAK ---')
        
        for section_num, section in enumerate(sections):
            # Procurar por padrões de itens no layout APP2
            item_matches = self._find_item_patterns_app2(section)
            
            if item_matches:
                for item_text in item_matches:
                    item_data = self._parse_item_app2(item_text, section_num)
                    if item_data:
                        items.append(item_data)
        
        return items
    
    def _find_item_patterns_app2(self, text: str) -> List[str]:
        """Encontra padrões de itens específicos do layout APP2.pdf"""
        patterns = [
            r'ITENS DA DUIMP - (\d+).*?(?=ITENS DA DUIMP|\*\*\*|\-{3,}|$)',  # Para múltiplos itens
            r'Item\s+Integracao\s+NCM.*?(?=Item\s+Integracao|\*\*\*|\-{3,}|$)',  # Para cabeçalhos de tabela
        ]
        
        items = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if match and len(match.strip()) > 100:  # Garantir que não é apenas ruído
                    items.append(match.strip())
        
        return items
    
    def _parse_item_app2(self, text: str, section_num: int) -> Optional[Dict]:
        """Parse de um item individual do layout APP2.pdf"""
        try:
            item = {
                'numero_item': '',
                'ncm': '',
                'codigo_produto': '',
                'nome_produto': '',
                'descricao_produto': '',
                'codigo_interno': '',
                'pais_origem': '',
                'fabricante_conhecido': '',
                'caracterizacao_importacao': '',
                'exportador': '',
                'fabricante_produtor': '',
                'vinculacao': '',
                'aplicacao': '',
                'condicao_mercadoria': '',
                'quantidade_estatistica': 0,
                'unidade_estatistica': '',
                'quantidade_comercial': 0,
                'unidade_comercial': '',
                'peso_liquido_kg': 0,
                'moeda_negociada': '',
                'valor_unitario_cond_venda': 0,
                'valor_total_cond_venda': 0,
                'cfop': '',
                'descricao_complementar': '',
                'metodo_valoracao': '',
                'valor_cond_venda_moeda': 0,
                'valor_cond_venda_real': 0,
                'frete_internacional_real': 0,
                'seguro_internacional_real': 0,
                'local_embarque_real': 0,
                'local_aduaneiro_real': 0,
                'cobertura_cambial': '',
                
                # Impostos
                'ii_base_calculo': 0,
                'ii_aliquota': 0,
                'ii_valor_devido': 0,
                'ipi_base_calculo': 0,
                'ipi_aliquota': 0,
                'ipi_valor_devido': 0,
                'pis_base_calculo': 0,
                'pis_aliquota': 0,
                'pis_valor_devido': 0,
                'cofins_base_calculo': 0,
                'cofins_aliquota': 0,
                'cofins_valor_devido': 0,
                
                # ICMS
                'icms_regime': '',
                'icms_aliquota': 0,
                'icms_base_calculo': 0,
                'icms_valor_devido': 0,
                
                'total_impostos': 0,
                'valor_total_com_impostos': 0
            }
            
            # Número do item
            item_num_match = re.search(r'ITENS DA DUIMP - (\d{5})', text)
            if item_num_match:
                item['numero_item'] = item_num_match.group(1)
            
            # NCM e código do produto
            ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})\s+(\d+)', text)
            if ncm_match:
                item['ncm'] = ncm_match.group(1)
                item['codigo_produto'] = ncm_match.group(2)
            
            # Nome do produto
            nome_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n(.*?)(?:\nDESCRICAO|\nCÓDIGO|\nFABRICANTE|\n\*\*\*)', 
                                  text, re.DOTALL | re.IGNORECASE)
            if nome_match:
                item['nome_produto'] = nome_match.group(1).replace('\n', ' ').strip()
            
            # Descrição do produto
            desc_match = re.search(r'DESCRICAO DO PRODUTO\s*\n(.*?)(?:\nCÓDIGO|\nFABRICANTE|\n\*\*\*|\nDADOS)', 
                                  text, re.DOTALL | re.IGNORECASE)
            if desc_match:
                item['descricao_produto'] = desc_match.group(1).replace('\n', ' ').strip()
            
            # Código interno
            codigo_match = re.search(r'Código interno\s*(\d+\.\d+\.\d+)', text)
            if codigo_match:
                item['codigo_interno'] = codigo_match.group(1)
            
            # Fabricante/Produtor
            fabricante_match = re.search(r'FABRICANTE/PRODUTOR.*?Conhecido\s+(SIM|NAO)', text, re.DOTALL | re.IGNORECASE)
            if fabricante_match:
                item['fabricante_conhecido'] = fabricante_match.group(1)
            
            # País de origem
            pais_match = re.search(r'Pais Origem\s+(IT ITALIA|.+?)($|\n|CARACTERIZAÇÃO)', text)
            if pais_match:
                item['pais_origem'] = pais_match.group(1).strip()
            
            # Caracterização da importação
            import_match = re.search(r'CARACTERIZAÇÃO DA IMPORTAÇÃO.*?Importação\s+(.+?)\n', text, re.DOTALL | re.IGNORECASE)
            if import_match:
                item['caracterizacao_importacao'] = import_match.group(1).strip()
            
            # Dados da mercadoria
            mercadoria_section = self._extract_mercadoria_section(text)
            if mercadoria_section:
                item.update(mercadoria_section)
            
            # Impostos
            impostos_section = self._find_impostos_section_item(text)
            if impostos_section:
                tax_data = self._parse_taxes_app2(impostos_section)
                item.update(tax_data)
            
            # ICMS
            icms_section = self._find_icms_section(text)
            if icms_section:
                icms_data = self._parse_icms_app2(icms_section)
                item.update(icms_data)
            
            # Calcular totais
            item['total_impostos'] = (
                item['ii_valor_devido'] + 
                item['ipi_valor_devido'] + 
                item['pis_valor_devido'] + 
                item['cofins_valor_devido']
            )
            
            item['valor_total_com_impostos'] = item['valor_total_cond_venda'] + item['total_impostos']
            
            return item
            
        except Exception as e:
            logger.error(f"Erro ao parsear item na seção {section_num}: {str(e)}")
            return None
    
    def _extract_mercadoria_section(self, text: str) -> Dict:
        """Extrai dados da mercadoria"""
        data = {}
        
        # Aplicação
        app_match = re.search(r'Aplicação\s+(.+?)\n', text)
        if app_match:
            data['aplicacao'] = app_match.group(1).strip()
        
        # Quantidade comercial
        qtd_match = re.search(r'Qtde Unid\. Comercial\s+([\d\.,]+)', text)
        if qtd_match:
            data['quantidade_comercial'] = self._parse_valor(qtd_match.group(1))
        
        # Unidade comercial
        unid_match = re.search(r'Unidade Comercial\s+(.+?)\n', text)
        if unid_match:
            data['unidade_comercial'] = unid_match.group(1).strip()
        
        # Peso líquido
        peso_match = re.search(r'Peso Líquido \(KG\)\s+([\d\.,]+)', text)
        if peso_match:
            data['peso_liquido_kg'] = self._parse_valor(peso_match.group(1))
        
        # Valor unitário
        valor_unit_match = re.search(r'Valor Unit Cond Venda\s+([\d\.,]+)', text)
        if valor_unit_match:
            data['valor_unitario_cond_venda'] = self._parse_valor(valor_unit_match.group(1))
        
        # Valor total
        valor_total_match = re.search(r'Valor Tot\. Cond Venda\s+([\d\.,]+)', text)
        if valor_total_match:
            data['valor_total_cond_venda'] = self._parse_valor(valor_total_match.group(1))
        
        # CFOP
        cfop_match = re.search(r'CFOP\s+(\d+)\s+-\s+(.+?)\n', text)
        if cfop_match:
            data['cfop'] = f"{cfop_match.group(1)} - {cfop_match.group(2).strip()}"
        
        # Local aduaneiro
        local_adu_match = re.search(r'Local Aduaneiro \(R\$\)\s+([\d\.,]+)', text)
        if local_adu_match:
            data['local_aduaneiro_real'] = self._parse_valor(local_adu_match.group(1))
        
        # Frete internacional
        frete_match = re.search(r'Frete Internac\. \(R\$\)\s+([\d\.,]+)', text)
        if frete_match:
            data['frete_internacional_real'] = self._parse_valor(frete_match.group(1))
        
        # Seguro internacional
        seguro_match = re.search(r'Seguro Internac\. \(R\$\)\s+([\d\.,]+)', text)
        if seguro_match:
            data['seguro_internacional_real'] = self._parse_valor(seguro_match.group(1))
        
        return data
    
    def _find_impostos_section_item(self, text: str) -> Optional[str]:
        """Encontra seção de impostos do item"""
        # Procura por blocos de cálculo de impostos
        patterns = [
            r'CALCULOS DOS TRIBUTOS - MERCADORIA.*?(?=INFORMAÇÕES DO ICMS|ITENS DA DUIMP|\*\*\*|\-{3,}|$)',
            r'TRIBUTOS DA MERCADORIA - TRIBUTAÇÃO.*?(?=INFORMAÇÕES DO ICMS|ITENS DA DUIMP|\*\*\*|\-{3,}|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _parse_taxes_app2(self, text: str) -> Dict:
        """Parse de impostos específico do APP2"""
        taxes = {
            'ii_base_calculo': 0, 'ii_aliquota': 0, 'ii_valor_devido': 0,
            'ipi_base_calculo': 0, 'ipi_aliquota': 0, 'ipi_valor_devido': 0,
            'pis_base_calculo': 0, 'pis_aliquota': 0, 'pis_valor_devido': 0,
            'cofins_base_calculo': 0, 'cofins_aliquota': 0, 'cofins_valor_devido': 0
        }
        
        # Padrões para cada imposto
        patterns = {
            'ii': r'II.*?Base de Cálculo \(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            'ipi': r'IPI.*?Base de Cálculo \(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            'pis': r'PIS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor Devido \(R\$\)\s*([\d\.,]+)',
            'cofins': r'COFINS.*?Base de Cálculo \(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor Devido \(R\$\)\s*([\d\.,]+)'
        }
        
        for tax, pattern in patterns.items():
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                taxes[f'{tax}_base_calculo'] = self._parse_valor(match.group(1))
                taxes[f'{tax}_aliquota'] = self._parse_valor(match.group(2))
                taxes[f'{tax}_valor_devido'] = self._parse_valor(match.group(3))
        
        return taxes
    
    def _find_icms_section(self, text: str) -> Optional[str]:
        """Encontra seção de ICMS"""
        pattern = r'INFORMAÇÕES DO ICMS.*?(?=ITENS DA DUIMP|\*\*\*|\-{3,}|$)'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(0)
        return None
    
    def _parse_icms_app2(self, text: str) -> Dict:
        """Parse de ICMS específico do APP2"""
        icms = {
            'icms_regime': '',
            'icms_aliquota': 0,
            'icms_base_calculo': 0,
            'icms_valor_devido': 0
        }
        
        regime_match = re.search(r'Regime de Tributacao\s+(.+?)\n', text)
        if regime_match:
            icms['icms_regime'] = regime_match.group(1).strip()
        
        aliquota_match = re.search(r'% Alíquota Ad Valorem\s+([\d\.,]+)', text)
        if aliquota_match:
            icms['icms_aliquota'] = self._parse_valor(aliquota_match.group(1))
        
        base_match = re.search(r'Base de Cálculo\s+([\d\.,]+)', text)
        if base_match:
            icms['icms_base_calculo'] = self._parse_valor(base_match.group(1))
        
        valor_match = re.search(r'Valor Devido\s+([\d\.,]+)', text)
        if valor_match:
            icms['icms_valor_devido'] = self._parse_valor(valor_match.group(1))
        
        return icms
    
    def _find_impostos_section(self, text: str) -> Optional[str]:
        """Encontra seção de impostos totais"""
        pattern = r'CÁLCULOS DOS TRIBUTOS.*?(?=RECEITA|TRANSPORTE|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(0)
        return None
    
    def _parse_total_impostos(self, text: str, totais_info: Dict):
        """Parse de impostos totais"""
        # Padrões para impostos
        imposto_patterns = {
            'ii': r'II.*?A Recolher\s+([\d\.,]+)',
            'ipi': r'IPI.*?A Recolher\s+([\d\.,]+)',
            'pis': r'PIS.*?A Recolher\s+([\d\.,]+)',
            'cofins': r'COFINS.*?A Recolher\s+([\d\.,]+)',
            'taxa': r'TAXA DE UTILIZACAO.*?A Recolher\s+([\d\.,]+)'
        }
        
        for imposto, pattern in imposto_patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            if match:
                totais_info[f'{imposto}_total'] = self._parse_valor(match.group(1))
    
    def _calculate_totals(self):
        """Calcula totais do documento"""
        totais = {
            'valor_total_mercadoria': 0,
            'peso_total': 0,
            'quantidade_total': 0,
            'total_impostos': 0,
            'ii_total': 0,
            'ipi_total': 0,
            'pis_total': 0,
            'cofins_total': 0,
            'valor_total_com_impostos': 0
        }
        
        for item in self.documento['itens']:
            totais['valor_total_mercadoria'] += item.get('valor_total_cond_venda', 0)
            totais['peso_total'] += item.get('peso_liquido_kg', 0)
            totais['quantidade_total'] += item.get('quantidade_comercial', 0)
            totais['ii_total'] += item.get('ii_valor_devido', 0)
            totais['ipi_total'] += item.get('ipi_valor_devido', 0)
            totais['pis_total'] += item.get('pis_valor_devido', 0)
            totais['cofins_total'] += item.get('cofins_valor_devido', 0)
            totais['total_impostos'] += item.get('total_impostos', 0)
            totais['valor_total_com_impostos'] += item.get('valor_total_com_impostos', 0)
        
        self.documento['totais'] = totais
    
    def _parse_valor(self, valor_str: str) -> float:
        """Converte string de valor para float"""
        try:
            if not valor_str or valor_str.strip() == '':
                return 0.0
            valor_limpo = valor_str.replace('.', '').replace(',', '.')
            return float(valor_limpo)
        except:
            return 0.0


class FinancialAnalyzer:
    """Analisador financeiro para APP2"""
    
    def __init__(self, documento: Dict):
        self.documento = documento
        self.itens_df = None
        
    def prepare_dataframe(self):
        """Prepara DataFrame para análise"""
        itens_data = []
        
        for item in self.documento['itens']:
            itens_data.append({
                'Item': item.get('numero_item', ''),
                'NCM': item.get('ncm', ''),
                'Código Produto': item.get('codigo_produto', ''),
                'Código Interno': item.get('codigo_interno', ''),
                'Produto': item.get('nome_produto', ''),
                'Descrição': item.get('descricao_produto', ''),
                'País Origem': item.get('pais_origem', ''),
                'Aplicação': item.get('aplicacao', ''),
                'Fabricante Conhecido': item.get('fabricante_conhecido', ''),
                'CFOP': item.get('cfop', ''),
                'Quantidade': item.get('quantidade_comercial', 0),
                'Unidade': item.get('unidade_comercial', ''),
                'Peso (kg)': item.get('peso_liquido_kg', 0),
                'Valor Unit. (R$)': item.get('valor_unitario_cond_venda', 0),
                'Valor Total (R$)': item.get('valor_total_cond_venda', 0),
                'Local Aduaneiro (R$)': item.get('local_aduaneiro_real', 0),
                'Frete (R$)': item.get('frete_internacional_real', 0),
                'Seguro (R$)': item.get('seguro_internacional_real', 0),
                
                # Impostos - Bases
                'II Base (R$)': item.get('ii_base_calculo', 0),
                'IPI Base (R$)': item.get('ipi_base_calculo', 0),
                'PIS Base (R$)': item.get('pis_base_calculo', 0),
                'COFINS Base (R$)': item.get('cofins_base_calculo', 0),
                
                # Impostos - Alíquotas
                'II Alíq. (%)': item.get('ii_aliquota', 0),
                'IPI Alíq. (%)': item.get('ipi_aliquota', 0),
                'PIS Alíq. (%)': item.get('pis_aliquota', 0),
                'COFINS Alíq. (%)': item.get('cofins_aliquota', 0),
                
                # Impostos - Valores
                'II (R$)': item.get('ii_valor_devido', 0),
                'IPI (R$)': item.get('ipi_valor_devido', 0),
                'PIS (R$)': item.get('pis_valor_devido', 0),
                'COFINS (R$)': item.get('cofins_valor_devido', 0),
                
                # ICMS
                'ICMS Regime': item.get('icms_regime', ''),
                'ICMS Alíq. (%)': item.get('icms_aliquota', 0),
                'ICMS Base (R$)': item.get('icms_base_calculo', 0),
                'ICMS (R$)': item.get('icms_valor_devido', 0),
                
                'Total Impostos (R$)': item.get('total_impostos', 0),
                'Valor c/ Impostos (R$)': item.get('valor_total_com_impostos', 0),
                'Descrição Complementar': item.get('descricao_complementar', '')
            })
        
        self.itens_df = pd.DataFrame(itens_data)
        return self.itens_df
    
    def create_summary_metrics(self):
        """Cria métricas resumidas"""
        metrics = {}
        
        if self.documento.get('totais'):
            metrics.update(self.documento['totais'])
        
        if self.documento.get('carga'):
            metrics['peso_bruto'] = self.documento['carga'].get('peso_bruto', 0)
            metrics['data_embarque'] = self.documento['carga'].get('data_embarque', '')
            metrics['data_chegada'] = self.documento['carga'].get('data_chegada', '')
        
        if self.documento.get('transporte'):
            if 'frete' in self.documento['transporte']:
                metrics['frete_total'] = self.documento['transporte']['frete'].get('valor_real', 0)
            if 'seguro' in self.documento['transporte']:
                metrics['seguro_total'] = self.documento['transporte']['seguro'].get('valor_real', 0)
        
        return metrics


def display_header_info(cabecalho: Dict):
    """Exibe informações do cabeçalho"""
    st.markdown('<h2 class="sub-header">📋 Informações do Processo</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info(f"**Processo:** {cabecalho.get('processo', 'N/A')}")
    
    with col2:
        st.info(f"**Importador:** {cabecalho.get('importador', 'N/A')}")
    
    with col3:
        st.info(f"**CNPJ:** {cabecalho.get('cnpj', 'N/A')}")
    
    with col4:
        st.info(f"**Responsável:** {cabecalho.get('responsavel', 'N/A')}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Identificação:** {cabecalho.get('identificacao', 'N/A')}")
    
    with col2:
        st.info(f"**Data Cadastro:** {cabecalho.get('data_cadastro', 'N/A')}")


def display_carga_info(carga: Dict):
    """Exibe informações da carga"""
    st.markdown('<h2 class="sub-header">📦 Informações da Carga</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info(f"**Via Transporte:** {carga.get('via_transporte', 'N/A')}")
        st.info(f"**Data Embarque:** {carga.get('data_embarque', 'N/A')}")
    
    with col2:
        st.info(f"**Identificação:** {carga.get('identificacao_carga', 'N/A')}")
        st.info(f"**Data Chegada:** {carga.get('data_chegada', 'N/A')}")
    
    with col3:
        st.info(f"**Peso Bruto:** {carga.get('peso_bruto', 0):,.2f} kg")
        st.info(f"**Peso Líquido:** {carga.get('peso_liquido', 0):,.2f} kg")
    
    with col4:
        st.info(f"**País Procedência:** {carga.get('pais_procedencia', 'N/A')}")
        st.info(f"**Unidade Despacho:** {carga.get('unidade_despacho', 'N/A')}")


def display_transporte_info(transporte: Dict):
    """Exibe informações de transporte"""
    st.markdown('<h2 class="sub-header">🚢 Informações de Transporte</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if transporte.get('tipo_conhecimento'):
            tipo = transporte['tipo_conhecimento']
            st.info(f"**Conhecimento:** {tipo.get('codigo', '')} - {tipo.get('descricao', '')}")
    
    with col2:
        st.info(f"**Bandeira:** {transporte.get('bandeira', 'N/A')}")
    
    with col3:
        st.info(f"**Local Embarque:** {transporte.get('local_embarque', 'N/A')}")
    
    with col4:
        if transporte.get('frete'):
            frete = transporte['frete']
            st.info(f"**Frete:** R$ {frete.get('valor_real', 0):,.2f}")
        
        if transporte.get('seguro'):
            seguro = transporte['seguro']
            st.info(f"**Seguro:** R$ {seguro.get('valor_real', 0):,.2f}")


def display_moedas_info(moedas: Dict):
    """Exibe informações de moedas"""
    st.markdown('<h2 class="sub-header">💰 Cotações de Moedas</h2>', unsafe_allow_html=True)
    
    if moedas.get('data_cotacao'):
        st.info(f"**Data das Cotações:** {moedas['data_cotacao']}")
    
    currency_data = []
    for key, value in moedas.items():
        if key != 'data_cotacao' and isinstance(value, dict):
            currency_data.append({
                'Moeda': key,
                'Código': value.get('codigo', ''),
                'Cotação': f"R$ {value.get('cotacao', 0):,.4f}"
            })
    
    if currency_data:
        df_currency = pd.DataFrame(currency_data)
        st.dataframe(df_currency, use_container_width=True)


def display_totais_info(totais_extraidos: Dict):
    """Exibe totais extraídos"""
    st.markdown('<h2 class="sub-header">🧮 Totais Extraídos</h2>', unsafe_allow_html=True)
    
    if 'cif' in totais_extraidos:
        cif = totais_extraidos['cif']
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**CIF (USD):** $ {cif.get('usd', 0):,.2f}")
        with col2:
            st.info(f"**CIF (R$):** R$ {cif.get('brl', 0):,.2f}")
    
    if 'vmle' in totais_extraidos:
        vmle = totais_extraidos['vmle']
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**VMLE (USD):** $ {vmle.get('usd', 0):,.2f}")
        with col2:
            st.info(f"**VMLE (R$):** R$ {vmle.get('brl', 0):,.2f}")
    
    if 'vmld' in totais_extraidos:
        vmld = totais_extraidos['vmld']
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**VMLD (USD):** $ {vmld.get('usd', 0):,.2f}")
        with col2:
            st.info(f"**VMLD (R$):** R$ {vmld.get('brl', 0):,.2f}")


def display_impostos_totais(totais_extraidos: Dict):
    """Exibe totais de impostos"""
    st.markdown('<h2 class="sub-header">🏛️ Totais de Impostos</h2>', unsafe_allow_html=True)
    
    impostos_keys = ['ii_total', 'ipi_total', 'pis_total', 'cofins_total', 'taxa_total']
    impostos_labels = {
        'ii_total': 'Imposto de Importação',
        'ipi_total': 'IPI',
        'pis_total': 'PIS',
        'cofins_total': 'COFINS',
        'taxa_total': 'Taxa de Utilização'
    }
    
    cols = st.columns(len([k for k in impostos_keys if k in totais_extraidos]))
    col_idx = 0
    
    for key in impostos_keys:
        if key in totais_extraidos and totais_extraidos[key] > 0:
            with cols[col_idx]:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">R$ {totais_extraidos[key]:,.2f}</div>
                    <div class="metric-label">{impostos_labels[key]}</div>
                </div>
                """, unsafe_allow_html=True)
                col_idx += 1


def main():
    """Função principal"""
    
    st.markdown('<h1 class="main-header">🏭 Sistema de Análise de Extratos Häfele - APP2</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>📄 Especificação:</strong> Este sistema foi ajustado especificamente para o layout do arquivo APP2.pdf.
        <br><strong>🔍 Funcionalidades:</strong> Extração completa de cabeçalho, carga, transporte, moedas, itens e impostos.
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### 📁 Upload do Documento APP2")
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo PDF (Formato APP2)",
            type=['pdf'],
            help="Documento PDF no formato padrão APP2.pdf da Häfele"
        )
        
        st.markdown("---")
        st.markdown("### ⚙️ Opções de Análise")
        
        show_details = st.checkbox("Mostrar detalhes completos", value=True)
        show_raw_data = st.checkbox("Mostrar dados brutos", value=False)
        
        st.markdown("---")
        
        if uploaded_file:
            file_size = uploaded_file.size / (1024 * 1024)
            st.success(f"📄 Arquivo: {uploaded_file.name}")
            st.info(f"📊 Tamanho: {file_size:.2f} MB")
    
    if uploaded_file is not None:
        try:
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Etapa 1: Análise do documento
            status_text.text("📄 Analisando documento PDF (Layout APP2)...")
            progress_bar.progress(20)
            
            parser = HafelePDFParser()
            documento = parser.parse_pdf(tmp_path)
            
            # Etapa 2: Processamento dos dados
            status_text.text("📊 Processando dados...")
            progress_bar.progress(50)
            
            analyser = FinancialAnalyzer(documento)
            df = analyser.prepare_dataframe()
            metrics = analyser.create_summary_metrics()
            
            # Etapa 3: Cálculos finais
            status_text.text("🔢 Calculando métricas...")
            progress_bar.progress(80)
            
            # Limpar arquivo temporário
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            progress_bar.progress(100)
            status_text.text("✅ Processamento concluído!")
            
            # Exibir informações gerais
            st.success(f"✅ **{len(documento['itens'])} itens** extraídos com sucesso do documento APP2!")
            
            # Métricas principais
            st.markdown('<h2 class="sub-header">📊 Métricas Principais</h2>', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">R$ {metrics.get('valor_total_mercadoria', 0):,.2f}</div>
                    <div class="metric-label">Valor Mercadoria</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">R$ {metrics.get('total_impostos', 0):,.2f}</div>
                    <div class="metric-label">Total Impostos</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">R$ {metrics.get('valor_total_com_impostos', 0):,.2f}</div>
                    <div class="metric-label">Valor c/ Impostos</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="section-card">
                    <div class="metric-value">{metrics.get('quantidade_total', 0):,.0f}</div>
                    <div class="metric-label">Quantidade Total</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Abas para diferentes seções
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "📋 Cabeçalho", "📦 Carga", "🚢 Transporte", "💰 Moedas", "📊 Itens", "📈 Análises"
            ])
            
            with tab1:
                if documento.get('cabecalho'):
                    display_header_info(documento['cabecalho'])
            
            with tab2:
                if documento.get('carga'):
                    display_carga_info(documento['carga'])
            
            with tab3:
                if documento.get('transporte'):
                    display_transporte_info(documento['transporte'])
            
            with tab4:
                if documento.get('moedas'):
                    display_moedas_info(documento['moedas'])
            
            with tab5:
                st.markdown('<h2 class="sub-header">📦 Lista de Itens Detalhada</h2>', unsafe_allow_html=True)
                
                # Configurar colunas para exibição
                if not df.empty:
                    # Ordenar colunas para melhor visualização
                    col_order = [
                        'Item', 'Código Interno', 'Produto', 'Descrição',
                        'Quantidade', 'Unidade', 'Peso (kg)',
                        'Valor Unit. (R$)', 'Valor Total (R$)',
                        'II Base (R$)', 'II Alíq. (%)', 'II (R$)',
                        'IPI Base (R$)', 'IPI Alíq. (%)', 'IPI (R$)',
                        'PIS Base (R$)', 'PIS Alíq. (%)', 'PIS (R$)',
                        'COFINS Base (R$)', 'COFINS Alíq. (%)', 'COFINS (R$)',
                        'Total Impostos (R$)', 'Valor c/ Impostos (R$)'
                    ]
                    
                    display_cols = [c for c in col_order if c in df.columns]
                    remaining_cols = [c for c in df.columns if c not in display_cols]
                    final_cols = display_cols + remaining_cols
                    
                    display_df = df[final_cols].copy()
                    
                    # Formatação de moeda
                    currency_cols = [col for col in display_df.columns if '(R$)' in col]
                    for col in currency_cols:
                        display_df[col] = display_df[col].apply(lambda x: f"R$ {x:,.2f}" if pd.notnull(x) else "")
                    
                    # Formatação de porcentagem
                    pct_cols = [col for col in display_df.columns if '(%)' in col]
                    for col in pct_cols:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}%" if pd.notnull(x) else "")
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        height=600
                    )
                else:
                    st.warning("Nenhum item encontrado no documento.")
            
            with tab6:
                st.markdown('<h2 class="sub-header">📈 Análises Financeiras</h2>', unsafe_allow_html=True)
                
                if not df.empty:
                    # Análise de impostos por item
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("##### 💰 Distribuição de Impostos por Item")
                        impostos_items = df[['Produto', 'II (R$)', 'IPI (R$)', 'PIS (R$)', 'COFINS (R$)']].copy()
                        for col in ['II (R$)', 'IPI (R$)', 'PIS (R$)', 'COFINS (R$)']:
                            impostos_items[col] = impostos_items[col].replace(r'[R\$, ]', '', regex=True).astype(float)
                        
                        impostos_sum = impostos_items[['II (R$)', 'IPI (R$)', 'PIS (R$)', 'COFINS (R$)']].sum()
                        
                        fig1 = px.pie(
                            values=impostos_sum.values,
                            names=impostos_sum.index,
                            title="Distribuição dos Impostos Totais",
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        st.markdown("##### 📊 Valores por Produto")
                        valores_items = df[['Produto', 'Valor Total (R$)', 'Total Impostos (R$)']].copy()
                        valores_items['Valor Total (R$)'] = valores_items['Valor Total (R$)'].replace(r'[R\$, ]', '', regex=True).astype(float)
                        valores_items['Total Impostos (R$)'] = valores_items['Total Impostos (R$)'].replace(r'[R\$, ]', '', regex=True).astype(float)
                        
                        fig2 = px.bar(
                            valores_items.nlargest(10, 'Valor Total (R$)'),
                            x='Produto',
                            y=['Valor Total (R$)', 'Total Impostos (R$)'],
                            title="Top 10 Produtos por Valor",
                            barmode='group',
                            color_discrete_sequence=['#1E3A8A', '#2563EB']
                        )
                        fig2.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    # Tabela de resumo
                    st.markdown("##### 📋 Resumo por Tipo de Imposto")
                    resumo_impostos = pd.DataFrame({
                        'Imposto': ['II', 'IPI', 'PIS', 'COFINS', 'Total'],
                        'Valor Total (R$)': [
                            metrics.get('ii_total', 0),
                            metrics.get('ipi_total', 0),
                            metrics.get('pis_total', 0),
                            metrics.get('cofins_total', 0),
                            metrics.get('total_impostos', 0)
                        ],
                        '% sobre Mercadoria': [
                            (metrics.get('ii_total', 0) / metrics.get('valor_total_mercadoria', 1) * 100) if metrics.get('valor_total_mercadoria', 0) > 0 else 0,
                            (metrics.get('ipi_total', 0) / metrics.get('valor_total_mercadoria', 1) * 100) if metrics.get('valor_total_mercadoria', 0) > 0 else 0,
                            (metrics.get('pis_total', 0) / metrics.get('valor_total_mercadoria', 1) * 100) if metrics.get('valor_total_mercadoria', 0) > 0 else 0,
                            (metrics.get('cofins_total', 0) / metrics.get('valor_total_mercadoria', 1) * 100) if metrics.get('valor_total_mercadoria', 0) > 0 else 0,
                            (metrics.get('total_impostos', 0) / metrics.get('valor_total_mercadoria', 1) * 100) if metrics.get('valor_total_mercadoria', 0) > 0 else 0
                        ]
                    })
                    
                    # Formatar a tabela
                    resumo_impostos['Valor Total (R$)'] = resumo_impostos['Valor Total (R$)'].apply(lambda x: f"R$ {x:,.2f}")
                    resumo_impostos['% sobre Mercadoria'] = resumo_impostos['% sobre Mercadoria'].apply(lambda x: f"{x:,.2f}%")
                    
                    st.dataframe(resumo_impostos, use_container_width=True)
            
            # Exportação de dados
            st.markdown('<h2 class="sub-header">💾 Exportação de Dados</h2>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Exportar CSV completo
                csv_data = df.to_csv(index=False, encoding='utf-8-sig', sep=';')
                st.download_button(
                    label="📥 Baixar CSV (Completo)",
                    data=csv_data,
                    file_name="app2_hafele_completo.csv",
                    mime="text/csv",
                    help="Baixar todos os dados em formato CSV"
                )
            
            with col2:
                # Exportar Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Dados principais
                    df.to_excel(writer, sheet_name='Itens', index=False)
                    
                    # Resumo
                    resumo_data = {
                        'Métrica': [
                            'Valor Total Mercadoria',
                            'Total Impostos',
                            'Valor com Impostos',
                            'Quantidade Total',
                            'Peso Total (kg)',
                            'II Total',
                            'IPI Total',
                            'PIS Total',
                            'COFINS Total'
                        ],
                        'Valor (R$)': [
                            metrics.get('valor_total_mercadoria', 0),
                            metrics.get('total_impostos', 0),
                            metrics.get('valor_total_com_impostos', 0),
                            metrics.get('quantidade_total', 0),
                            metrics.get('peso_total', 0),
                            metrics.get('ii_total', 0),
                            metrics.get('ipi_total', 0),
                            metrics.get('pis_total', 0),
                            metrics.get('cofins_total', 0)
                        ]
                    }
                    resumo_df = pd.DataFrame(resumo_data)
                    resumo_df.to_excel(writer, sheet_name='Resumo', index=False)
                
                st.download_button(
                    label="📊 Baixar Excel",
                    data=output.getvalue(),
                    file_name="app2_hafele_completo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Baixar todos os dados em formato Excel com múltiplas abas"
                )
            
            with col3:
                # Exportar JSON
                json_data = json.dumps(documento, default=str, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📋 Baixar JSON",
                    data=json_data,
                    file_name="app2_hafele_documento.json",
                    mime="application/json",
                    help="Baixar dados estruturados em formato JSON"
                )
            
            # Dados brutos (opcional)
            if show_raw_data:
                st.markdown('<h2 class="sub-header">🔍 Dados Brutos</h2>', unsafe_allow_html=True)
                with st.expander("Visualizar dados brutos extraídos"):
                    st.json(documento, expanded=False)
        
        except Exception as e:
            st.error(f"❌ Erro no processamento: {str(e)}")
            logger.error(f"Erro detalhado: {str(e)}", exc_info=True)
    
    else:
        st.info("📁 Aguardando upload do arquivo PDF no formato APP2...")
        st.markdown("""
        <div class="warning-box">
            <strong>⚠️ Instruções:</strong>
            <ol>
                <li>Clique em <strong>"Browse files"</strong> no menu à esquerda</li>
                <li>Selecione um arquivo PDF no formato <strong>APP2.pdf</strong></li>
                <li>Aguarde o processamento automático</li>
                <li>Explore os dados nas diferentes abas</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
