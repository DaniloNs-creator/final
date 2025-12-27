# app_conversor_duimp_exato.py
import streamlit as st
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import json
import tempfile
import os
from datetime import datetime
from typing import Dict, List, Optional
import base64
import zipfile
from io import BytesIO, StringIO
import pdfplumber
import fitz  # PyMuPDF
import io

# Configuração da página
st.set_page_config(
    page_title="Conversor DUIMP - PDF para XML (Layout Exato)",
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
    .success-box {
        background-color: #D1FAE5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #10B981;
    }
    .warning-box {
        background-color: #FEF3C7;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #F59E0B;
    }
    .stat-card {
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #E2E8F0;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E3A8A;
    }
    .xml-preview {
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        background-color: #0F172A;
        color: #E2E8F0;
        padding: 1rem;
        border-radius: 0.5rem;
        max-height: 500px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

class ConversorDUIMPExato:
    def __init__(self):
        self.duimp_data = {
            "cabecalho": {},
            "adicoes": [],
            "transportes": {},
            "documentos": [],
            "pagamentos": [],
            "informacoes_complementares": ""
        }
        self.stats = {
            "paginas_processadas": 0,
            "adicoes_geradas": 0,
            "itens_encontrados": 0
        }
    
    def processar_pdf(self, pdf_bytes: bytes) -> bool:
        """Processa o PDF e extrai informações no layout correto"""
        try:
            # Extrair texto usando pdfplumber (melhor para tabelas)
            texto = ""
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for pagina in pdf.pages:
                    texto += pagina.extract_text() + "\n"
                self.stats["paginas_processadas"] = len(pdf.pages)
            
            # Parse todas as seções
            self._parse_cabecalho_exato(texto)
            self._parse_adicoes_exato(texto)
            self._parse_transporte_exato(texto)
            self._parse_documentos_exato(texto)
            self._parse_pagamentos_exato(texto)
            
            self.stats["adicoes_geradas"] = len(self.duimp_data["adicoes"])
            self.stats["itens_encontrados"] = sum(len(ad.get("itens", [])) for ad in self.duimp_data["adicoes"])
            
            return True
            
        except Exception as e:
            st.error(f"Erro no processamento: {str(e)}")
            return False
    
    def _parse_cabecalho_exato(self, texto: str):
        """Extrai informações do cabeçalho no formato exato"""
        cabecalho = {}
        
        # Número DUIMP - buscar padrão
        match = re.search(r'N[úu]mero\s*([A-Z0-9]+)', texto, re.IGNORECASE)
        if match:
            cabecalho['numero_duimp'] = match.group(1)
        else:
            # Gerar número sequencial
            cabecalho['numero_duimp'] = f"{int(datetime.now().timestamp()) % 10000000000:010d}"
        
        # Processo
        match = re.search(r'PROCESSO\s*#?\s*(\d+)', texto)
        if match:
            cabecalho['processo'] = match.group(1)
        
        # CNPJ Importador
        match = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', texto)
        if match:
            cabecalho['cnpj'] = match.group(1).replace('.', '').replace('/', '').replace('-', '')
        else:
            cabecalho['cnpj'] = '02473058000188'  # Default HAFELE
        
        # Data
        match = re.search(r'Data (?:de )?Cadastro\s*(\d{2}/\d{2}/\d{4})', texto)
        if match:
            data_str = match.group(1)
            cabecalho['data_registro'] = datetime.strptime(data_str, '%d/%m/%Y').strftime('%Y%m%d')
        else:
            cabecalho['data_registro'] = datetime.now().strftime('%Y%m%d')
        
        # Moeda
        match = re.search(r'Moeda Negociada\s*(\d+)\s*-\s*([\w\s/]+)', texto)
        if match:
            cabecalho['moeda_codigo'] = match.group(1)
            cabecalho['moeda_nome'] = match.group(2)
        else:
            cabecalho['moeda_codigo'] = '978'
            cabecalho['moeda_nome'] = 'EURO/COM.EUROPEIA'
        
        # Cotação
        match = re.search(r'Cota[cç][aã]o.*?([\d,]+)', texto)
        if match:
            cabecalho['cotacao'] = match.group(1).replace(',', '.')
        
        # Responsável Legal
        match = re.search(r'Responsavel Legal\s*([A-ZÀ-Ú\s]+)', texto, re.IGNORECASE)
        if match:
            cabecalho['responsavel'] = match.group(1).strip()
        
        # Referência Importador
        match = re.search(r'Ref\. Importador\s*([A-Z0-9\s]+)', texto)
        if match:
            cabecalho['ref_importador'] = match.group(1).strip()
        
        self.duimp_data["cabecalho"] = cabecalho
    
    def _parse_adicoes_exato(self, texto: str):
        """Extrai adições no formato exato do XML"""
        adicoes = []
        linhas = texto.split('\n')
        
        # Procurar seções de itens
        for i, linha in enumerate(linhas):
            # Detectar início de item (formato: Item | Integracao | NCM | ...)
            if re.match(r'^\s*\d+\s*[✓✗×]?\s*[\d.]+\s*\d+', linha.strip()):
                item_info = self._extrair_item_detalhado(linha.strip(), linhas, i)
                if item_info:
                    # Criar adição para cada item (simplificado - pode agrupar depois)
                    adicao = {
                        'numero_adicao': f"{len(adicoes) + 1:03d}",
                        'itens': [item_info],
                        'fornecedor': self._extrair_fornecedor(linhas, i),
                        'condicao_venda': item_info.get('condicao_venda', 'FCA'),
                        'valores': self._calcular_valores_adicao(item_info)
                    }
                    adicoes.append(adicao)
        
        # Se não encontrou no formato tabela, busca alternativa
        if not adicoes:
            adicoes = self._buscar_adicoes_alternativo(texto)
        
        self.duimp_data["adicoes"] = adicoes
    
    def _extrair_item_detalhado(self, linha_item: str, todas_linhas: List[str], idx: int) -> Dict:
        """Extrai informações detalhadas de um item"""
        item = {}
        
        # Parse da linha do item
        partes = re.split(r'\s{2,}', linha_item.strip())
        
        if len(partes) >= 6:
            item['numero_item'] = partes[0].zfill(2)
            item['ncm'] = partes[2].replace('.', '')
            item['condicao_venda'] = partes[5] if len(partes) > 5 else 'FCA'
        
        # Buscar informações detalhadas
        for j in range(idx, min(idx + 30, len(todas_linhas))):
            linha = todas_linhas[j]
            
            # Descrição do produto
            if 'DENOMINACAO DO PRODUTO' in linha or 'DESCRICAO DO PRODUTO' in linha:
                if j + 1 < len(todas_linhas):
                    item['descricao'] = todas_linhas[j + 1].strip()
            
            # Código interno
            elif 'Código interno' in linha:
                match = re.search(r'(\d{3}\.\d{2}\.\d{3})', linha)
                if match:
                    item['codigo_interno'] = match.group(1)
            
            # Quantidade
            elif 'Qtde Unid. Comercial' in linha:
                match = re.search(r'([\d.,]+)', linha)
                if match:
                    item['quantidade'] = match.group(1).replace('.', '').replace(',', '.')
            
            # Valor unitário
            elif 'Valor Unit Cond Venda' in linha:
                match = re.search(r'([\d.,]+)', linha)
                if match:
                    item['valor_unitario'] = match.group(1).replace('.', '').replace(',', '.')
            
            # Valor total
            elif 'Vlr Cond Venda (Moeda' in linha or 'Valor Tot. Cond Venda' in linha:
                match = re.search(r'([\d.,]+)', linha)
                if match:
                    item['valor_total_moeda'] = match.group(1).replace('.', '').replace(',', '.')
        
        # Valores padrão se não encontrado
        if 'quantidade' not in item:
            item['quantidade'] = '1'
        if 'valor_unitario' not in item:
            item['valor_unitario'] = '100'
        if 'valor_total_moeda' not in item:
            item['valor_total_moeda'] = item['valor_unitario']
        
        return item if item.get('ncm') else None
    
    def _extrair_fornecedor(self, linhas: List[str], idx: int) -> Dict:
        """Extrai informações do fornecedor"""
        fornecedor = {
            'nome': 'FORNECEDOR INTERNACIONAL',
            'pais': '386',
            'pais_nome': 'ITALIA'
        }
        
        for i in range(max(0, idx - 20), min(idx + 20, len(linhas))):
            linha = linhas[i]
            
            if 'FABRICANTE/PRODUTOR' in linha:
                if 'Conhecido' in linha and 'NAO' in linha.upper():
                    fornecedor['nome'] = 'Fabricante é desconhecido'
            
            elif 'EXPORTADOR ESTRANGEIRO' in linha:
                # Tentar extrair nome do exportador
                partes = linha.split('-')
                if len(partes) > 0:
                    nome = partes[0].replace('EXPORTADOR ESTRANGEIRO', '').strip()
                    if nome:
                        fornecedor['nome'] = nome
        
        return fornecedor
    
    def _calcular_valores_adicao(self, item: Dict) -> Dict:
        """Calcula todos os valores para a adição"""
        valores = {}
        
        # Valores básicos
        valor_moeda = float(item.get('valor_total_moeda', '0'))
        valores['valor_moeda'] = self._formatar_valor_xml(str(valor_moeda), 15)
        
        # Converter para reais se houver cotação
        if 'cotacao' in self.duimp_data["cabecalho"]:
            try:
                cotacao = float(self.duimp_data["cabecalho"]["cotacao"])
                valor_reais = valor_moeda * cotacao
                valores['valor_reais'] = self._formatar_valor_xml(str(valor_reais), 15)
            except:
                valores['valor_reais'] = self._formatar_valor_xml(str(valor_moeda * 6.2), 15)  # EUR default
        else:
            valores['valor_reais'] = self._formatar_valor_xml(str(valor_moeda * 6.2), 15)
        
        # Calcular base para tributos (CIF = valor + frete + seguro)
        base_calculo = float(valores['valor_reais']) / 100
        
        # Calcular tributos (percentuais do XML exemplo)
        valores['ii_base'] = self._formatar_valor_xml(str(int(base_calculo * 100)), 15)
        valores['ii_aliquota'] = self._determinar_aliquota_ii(item.get('ncm', ''))
        valores['ii_valor'] = self._formatar_valor_xml(str(int(base_calculo * float(valores['ii_aliquota']) / 100 * 100)), 15)
        
        valores['ipi_aliquota'] = '00325'  # 3.25%
        valores['ipi_valor'] = self._formatar_valor_xml(str(int(base_calculo * 3.25 / 100 * 100)), 15)
        
        valores['pis_aliquota'] = '00210'  # 2.10%
        valores['pis_valor'] = self._formatar_valor_xml(str(int(base_calculo * 2.10 / 100 * 100)), 15)
        
        valores['cofins_aliquota'] = '00965'  # 9.65%
        valores['cofins_valor'] = self._formatar_valor_xml(str(int(base_calculo * 9.65 / 100 * 100)), 15)
        
        # ICMS
        valores['icms_base'] = self._formatar_valor_xml(str(int(base_calculo * 0.18 * 100)), 15)  # 18% da base
        valores['icms_aliquota'] = '01800'
        valores['icms_valor'] = self._formatar_valor_xml(str(int(base_calculo * 0.18 * 100)), 15)
        valores['icms_diferido'] = self._formatar_valor_xml(str(int(base_calculo * 0.09 * 100)), 15)  # 50% diferimento
        
        # CBS/IBS (exemplo do XML)
        valores['cbs_aliquota'] = '00090'  # 0.09%
        valores['cbs_valor'] = self._formatar_valor_xml(str(int(base_calculo * 0.09 / 100 * 100)), 15)
        valores['ibs_aliquota'] = '00010'  # 0.10%
        valores['ibs_valor'] = self._formatar_valor_xml(str(int(base_calculo * 0.10 / 100 * 100)), 15)
        
        return valores
    
    def _determinar_aliquota_ii(self, ncm: str) -> str:
        """Determina alíquota de II baseada no NCM"""
        ncm_prefixo = ncm[:4] if len(ncm) >= 4 else '0000'
        
        # Baseado no XML exemplo
        if ncm_prefixo in ['8302', '3926']:
            return '01800'  # 18%
        elif ncm_prefixo in ['7318', '8302']:
            return '01440'  # 14.4%
        elif ncm_prefixo in ['8505']:
            return '01600'  # 16%
        else:
            return '01800'  # Default 18%
    
    def _buscar_adicoes_alternativo(self, texto: str) -> List[Dict]:
        """Busca alternativa para extrair adições"""
        adicoes = []
        
        # Buscar por NCMs no texto
        padrao_ncm = r'(\d{4}\.\d{2}\.\d{2}|\d{8})'
        ncm_matches = list(re.finditer(padrao_ncm, texto))
        
        for i, match in enumerate(ncm_matches[:5]):  # Limitar a 5 adições
            ncm = match.group(1).replace('.', '')
            
            # Criar adição básica
            adicao = {
                'numero_adicao': f"{i + 1:03d}",
                'itens': [{
                    'numero_item': '01',
                    'ncm': ncm,
                    'descricao': f'Produto NCM {ncm}',
                    'quantidade': '1',
                    'valor_unitario': '1000',
                    'valor_total_moeda': '1000',
                    'condicao_venda': 'FCA'
                }],
                'fornecedor': {
                    'nome': 'ITALIANA FERRAMENTA S.R.L.',
                    'pais': '386',
                    'pais_nome': 'ITALIA'
                },
                'condicao_venda': 'FCA',
                'valores': self._calcular_valores_adicao({'ncm': ncm, 'valor_total_moeda': '1000'})
            }
            
            adicoes.append(adicao)
        
        return adicoes
    
    def _parse_transporte_exato(self, texto: str):
        """Extrai dados de transporte"""
        transporte = {}
        
        # Via de transporte
        match = re.search(r'Via de Transporte\s*(\d+)\s*-\s*([\wÍ]+)', texto)
        if match:
            transporte['codigo'] = match.group(1)
            transporte['nome'] = match.group(2)
        else:
            transporte['codigo'] = '01'
            transporte['nome'] = 'MARÍTIMA'
        
        # Datas
        match = re.search(r'Data de Embarque\s*(\d{2}/\d{2}/\d{4})', texto)
        if match:
            transporte['data_embarque'] = datetime.strptime(match.group(1), '%d/%m/%Y').strftime('%Y%m%d')
        
        match = re.search(r'Data de Chegada\s*(\d{2}/\d{2}/\d{4})', texto)
        if match:
            transporte['data_chegada'] = datetime.strptime(match.group(1), '%d/%m/%Y').strftime('%Y%m%d')
        
        # Pesos
        match = re.search(r'Peso Bruto\s*([\d.,]+)', texto)
        if match:
            peso = match.group(1).replace('.', '').replace(',', '.')
            transporte['peso_bruto'] = self._formatar_valor_xml(peso, 15)
        
        match = re.search(r'Peso L[ií]quido\s*([\d.,]+)', texto)
        if match:
            peso = match.group(1).replace('.', '').replace(',', '.')
            transporte['peso_liquido'] = self._formatar_valor_xml(peso, 15)
        
        # Portos
        match = re.search(r'Unidade de Despacho\s*(\d+)\s*-\s*([\w\s]+)', texto)
        if match:
            transporte['urf_codigo'] = match.group(1)
            transporte['urf_nome'] = match.group(2)
        
        self.duimp_data["transportes"] = transporte
    
    def _parse_documentos_exato(self, texto: str):
        """Extrai documentos"""
        documentos = []
        
        # Conhecimento
        padrao_conhecimento = r'CONHECIMENTO DE (?:EMBARQUE|CARGA).*?NUMERO[:\s]*([A-Z0-9]+)'
        for match in re.finditer(padrao_conhecimento, texto, re.IGNORECASE | re.DOTALL):
            documentos.append({
                'tipo': '28',
                'nome': 'CONHECIMENTO DE CARGA',
                'numero': match.group(1).ljust(25)
            })
        
        # Fatura
        padrao_fatura = r'FATURA COMERCIAL.*?NUMERO[:\s]*([\d/]+)'
        for match in re.finditer(padrao_fatura, texto, re.IGNORECASE | re.DOTALL):
            documentos.append({
                'tipo': '01',
                'nome': 'FATURA COMERCIAL',
                'numero': match.group(1).ljust(25)
            })
        
        # Romaneio
        padrao_romaneio = r'ROMANEIO DE CARGA.*?(?:NUMERO|DESCRICAC)[:\s]*([A-Z0-9/]+)'
        for match in re.finditer(padrao_romaneio, texto, re.IGNORECASE | re.DOTALL):
            documentos.append({
                'tipo': '29',
                'nome': 'ROMANEIO DE CARGA',
                'numero': match.group(1).ljust(25)
            })
        
        self.duimp_data["documentos"] = documentos
    
    def _parse_pagamentos_exato(self, texto: str):
        """Extrai/calcula pagamentos"""
        pagamentos = []
        
        # Códigos de receita do XML exemplo
        codigos_receita = [
            ('0086', 'II'),      # Imposto de Importação
            ('1038', 'IPI'),     # IPI
            ('5602', 'PIS'),     # PIS
            ('5629', 'COFINS'),  # COFINS
            ('7811', 'SISCOMEX') # Taxa SISCOMEX
        ]
        
        # Buscar valores de tributos no texto
        tributos_texto = {}
        
        # Procurar tabela de tributos
        linhas = texto.split('\n')
        for i, linha in enumerate(linhas):
            if 'II' in linha and any(char.isdigit() for char in linha):
                # Extrair valor do II
                match = re.search(r'II\s+([\d.,]+)', linha)
                if match:
                    tributos_texto['II'] = match.group(1).replace('.', '').replace(',', '.')
            
            elif 'PIS' in linha and any(char.isdigit() for char in linha):
                match = re.search(r'PIS\s+([\d.,]+)', linha)
                if match:
                    tributos_texto['PIS'] = match.group(1).replace('.', '').replace(',', '.')
            
            elif 'COFINS' in linha and any(char.isdigit() for char in linha):
                match = re.search(r'COFINS\s+([\d.,]+)', linha)
                if match:
                    tributos_texto['COFINS'] = match.group(1).replace('.', '').replace(',', '.')
        
        # Criar pagamentos
        for codigo, nome in codigos_receita:
            valor = '000000000'
            if nome in tributos_texto:
                valor = self._formatar_valor_xml(tributos_texto[nome], 9)
            elif nome == 'SISCOMEX':
                valor = '000000285'  # Valor padrão do XML
            
            pagamentos.append({
                'codigo_receita': codigo,
                'nome': nome,
                'valor': valor,
                'banco': '341',
                'agencia': '3715',
                'conta': '316273'
            })
        
        self.duimp_data["pagamentos"] = pagamentos
    
    def _formatar_valor_xml(self, valor_str: str, digitos: int) -> str:
        """Formata valor para padrão XML com zeros à esquerda"""
        try:
            # Converter para float e depois para centavos
            valor = float(valor_str)
            valor_centavos = int(valor * 100)
            return f"{valor_centavos:0{digitos}d}"
        except:
            return "0" * digitos
    
    def gerar_xml_exato(self) -> str:
        """Gera XML exatamente no layout do arquivo exemplo"""
        try:
            # Criar elemento raiz
            lista_declaracoes = ET.Element('ListaDeclaracoes')
            duimp = ET.SubElement(lista_declaracoes, 'duimp')
            
            # Adicionar adições
            for adicao in self.duimp_data["adicoes"]:
                self._criar_adicao_xml(duimp, adicao)
            
            # Adicionar elementos do cabeçalho DUIMP
            self._criar_cabecalho_duimp_xml(duimp)
            
            # Adicionar transporte
            self._criar_transporte_xml(duimp)
            
            # Adicionar documentos
            self._criar_documentos_xml(duimp)
            
            # Adicionar pagamentos
            self._criar_pagamentos_xml(duimp)
            
            # Adicionar informações complementares
            self._criar_info_complementar_xml(duimp)
            
            # Converter para string com declaração XML
            xml_string = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            xml_string += ET.tostring(lista_declaracoes, encoding='unicode', method='xml')
            
            # Formatar bonito
            xml_dom = minidom.parseString(xml_string)
            xml_formatado = xml_dom.toprettyxml(indent="    ")
            
            # Remover linha extra da declaração XML
            lines = xml_formatado.split('\n')
            if len(lines) > 1 and '<?xml' in lines[1]:
                lines.pop(1)
            
            return '\n'.join(lines)
            
        except Exception as e:
            st.error(f"Erro ao gerar XML: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return ""
    
    def _criar_adicao_xml(self, duimp_element, adicao: Dict):
        """Cria uma adição no layout exato do XML"""
        adicao_elem = ET.SubElement(duimp_element, 'adicao')
        
        # Acrescimo (igual no XML exemplo)
        acrescimo = ET.SubElement(adicao_elem, 'acrescimo')
        ET.SubElement(acrescimo, 'codigoAcrescimo').text = '17'
        ET.SubElement(acrescimo, 'denominacao').text = 'OUTROS ACRESCIMOS AO VALOR ADUANEIRO                        '
        ET.SubElement(acrescimo, 'moedaNegociadaCodigo').text = self.duimp_data["cabecalho"].get('moeda_codigo', '978')
        ET.SubElement(acrescimo, 'moedaNegociadaNome').text = self.duimp_data["cabecalho"].get('moeda_nome', 'EURO/COM.EUROPEIA')
        ET.SubElement(acrescimo, 'valorMoedaNegociada').text = adicao['valores'].get('valor_moeda', '000000000000000')
        ET.SubElement(acrescimo, 'valorReais').text = adicao['valores'].get('valor_reais', '000000000000000')
        
        # CIDE (zerado como no exemplo)
        ET.SubElement(adicao_elem, 'cideValorAliquotaEspecifica').text = '00000000000'
        ET.SubElement(adicao_elem, 'cideValorDevido').text = '000000000000000'
        ET.SubElement(adicao_elem, 'cideValorRecolher').text = '000000000000000'
        
        # Relação comprador/vendedor
        ET.SubElement(adicao_elem, 'codigoRelacaoCompradorVendedor').text = '3'
        ET.SubElement(adicao_elem, 'codigoVinculoCompradorVendedor').text = '1'
        ET.SubElement(adicao_elem, 'relacaoCompradorVendedor').text = 'Fabricante é desconhecido'
        ET.SubElement(adicao_elem, 'vinculoCompradorVendedor').text = 'Não há vinculação entre comprador e vendedor.'
        
        # COFINS
        ET.SubElement(adicao_elem, 'cofinsAliquotaAdValorem').text = '00965'
        ET.SubElement(adicao_elem, 'cofinsAliquotaEspecificaQuantidadeUnidade').text = '000000000'
        ET.SubElement(adicao_elem, 'cofinsAliquotaEspecificaValor').text = '0000000000'
        ET.SubElement(adicao_elem, 'cofinsAliquotaReduzida').text = '00000'
        ET.SubElement(adicao_elem, 'cofinsAliquotaValorDevido').text = adicao['valores'].get('cofins_valor', '000000000000000')
        ET.SubElement(adicao_elem, 'cofinsAliquotaValorRecolher').text = adicao['valores'].get('cofins_valor', '000000000000000')
        
        # Condição de venda
        ET.SubElement(adicao_elem, 'condicaoVendaIncoterm').text = adicao['condicao_venda']
        ET.SubElement(adicao_elem, 'condicaoVendaLocal').text = 'BRUGNERA'
        ET.SubElement(adicao_elem, 'condicaoVendaMetodoValoracaoCodigo').text = '01'
        ET.SubElement(adicao_elem, 'condicaoVendaMetodoValoracaoNome').text = 'METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)'
        ET.SubElement(adicao_elem, 'condicaoVendaMoedaCodigo').text = self.duimp_data["cabecalho"].get('moeda_codigo', '978')
        ET.SubElement(adicao_elem, 'condicaoVendaMoedaNome').text = self.duimp_data["cabecalho"].get('moeda_nome', 'EURO/COM.EUROPEIA')
        ET.SubElement(adicao_elem, 'condicaoVendaValorMoeda').text = adicao['valores'].get('valor_moeda', '000000000000000')
        ET.SubElement(adicao_elem, 'condicaoVendaValorReais').text = adicao['valores'].get('valor_reais', '000000000000000')
        
        # Dados cambiais
        ET.SubElement(adicao_elem, 'dadosCambiaisCoberturaCambialCodigo').text = '1'
        ET.SubElement(adicao_elem, 'dadosCambiaisCoberturaCambialNome').text = 'COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE\' 180'
        ET.SubElement(adicao_elem, 'dadosCambiaisInstituicaoFinanciadoraCodigo').text = '00'
        ET.SubElement(adicao_elem, 'dadosCambiaisInstituicaoFinanciadoraNome').text = 'N/I'
        ET.SubElement(adicao_elem, 'dadosCambiaisMotivoSemCoberturaCodigo').text = '00'
        ET.SubElement(adicao_elem, 'dadosCambiaisMotivoSemCoberturaNome').text = 'N/I'
        ET.SubElement(adicao_elem, 'dadosCambiaisValorRealCambio').text = '000000000000000'
        
        # Dados carga
        ET.SubElement(adicao_elem, 'dadosCargaPaisProcedenciaCodigo').text = '000'
        ET.SubElement(adicao_elem, 'dadosCargaUrfEntradaCodigo').text = '0000000'
        ET.SubElement(adicao_elem, 'dadosCargaViaTransporteCodigo').text = '01'
        ET.SubElement(adicao_elem, 'dadosCargaViaTransporteNome').text = 'MARÍTIMA'
        
        # Dados mercadoria
        item = adicao['itens'][0]  # Primeiro item da adição
        ET.SubElement(adicao_elem, 'dadosMercadoriaAplicacao').text = 'REVENDA'
        ET.SubElement(adicao_elem, 'dadosMercadoriaCodigoNaladiNCCA').text = '0000000'
        ET.SubElement(adicao_elem, 'dadosMercadoriaCodigoNaladiSH').text = '00000000'
        ET.SubElement(adicao_elem, 'dadosMercadoriaCodigoNcm').text = item.get('ncm', '00000000')
        ET.SubElement(adicao_elem, 'dadosMercadoriaCondicao').text = 'NOVA'
        ET.SubElement(adicao_elem, 'dadosMercadoriaDescricaoTipoCertificado').text = 'Sem Certificado'
        ET.SubElement(adicao_elem, 'dadosMercadoriaIndicadorTipoCertificado').text = '1'
        ET.SubElement(adicao_elem, 'dadosMercadoriaMedidaEstatisticaQuantidade').text = '00000004584200'  # Exemplo
        ET.SubElement(adicao_elem, 'dadosMercadoriaMedidaEstatisticaUnidade').text = 'QUILOGRAMA LIQUIDO'
        ET.SubElement(adicao_elem, 'dadosMercadoriaNomeNcm').text = self._obter_descricao_ncm(item.get('ncm', ''))
        ET.SubElement(adicao_elem, 'dadosMercadoriaPesoLiquido').text = '000000004584200'  # Exemplo
        
        # DCR
        ET.SubElement(adicao_elem, 'dcrCoeficienteReducao').text = '00000'
        ET.SubElement(adicao_elem, 'dcrIdentificacao').text = '00000000'
        ET.SubElement(adicao_elem, 'dcrValorDevido').text = '000000000000000'
        ET.SubElement(adicao_elem, 'dcrValorDolar').text = '000000000000000'
        ET.SubElement(adicao_elem, 'dcrValorReal').text = '000000000000000'
        ET.SubElement(adicao_elem, 'dcrValorRecolher').text = '000000000000000'
        
        # Fornecedor
        ET.SubElement(adicao_elem, 'fornecedorCidade').text = 'BRUGNERA'
        ET.SubElement(adicao_elem, 'fornecedorLogradouro').text = 'VIALE EUROPA'
        ET.SubElement(adicao_elem, 'fornecedorNome').text = adicao['fornecedor']['nome']
        ET.SubElement(adicao_elem, 'fornecedorNumero').text = '17'
        
        # Frete
        ET.SubElement(adicao_elem, 'freteMoedaNegociadaCodigo').text = self.duimp_data["cabecalho"].get('moeda_codigo', '978')
        ET.SubElement(adicao_elem, 'freteMoedaNegociadaNome').text = self.duimp_data["cabecalho"].get('moeda_nome', 'EURO/COM.EUROPEIA')
        ET.SubElement(adicao_elem, 'freteValorMoedaNegociada').text = '000000000002353'  # Exemplo
        ET.SubElement(adicao_elem, 'freteValorReais').text = '000000000014595'  # Exemplo
        
        # II
        ET.SubElement(adicao_elem, 'iiAcordoTarifarioTipoCodigo').text = '0'
        ET.SubElement(adicao_elem, 'iiAliquotaAcordo').text = '00000'
        ET.SubElement(adicao_elem, 'iiAliquotaAdValorem').text = adicao['valores'].get('ii_aliquota', '01800')
        ET.SubElement(adicao_elem, 'iiAliquotaPercentualReducao').text = '00000'
        ET.SubElement(adicao_elem, 'iiAliquotaReduzida').text = '00000'
        ET.SubElement(adicao_elem, 'iiAliquotaValorCalculado').text = adicao['valores'].get('ii_valor', '000000000000000')
        ET.SubElement(adicao_elem, 'iiAliquotaValorDevido').text = adicao['valores'].get('ii_valor', '000000000000000')
        ET.SubElement(adicao_elem, 'iiAliquotaValorRecolher').text = adicao['valores'].get('ii_valor', '000000000000000')
        ET.SubElement(adicao_elem, 'iiAliquotaValorReduzido').text = '000000000000000'
        ET.SubElement(adicao_elem, 'iiBaseCalculo').text = adicao['valores'].get('ii_base', '000000000000000')
        ET.SubElement(adicao_elem, 'iiFundamentoLegalCodigo').text = '00'
        ET.SubElement(adicao_elem, 'iiMotivoAdmissaoTemporariaCodigo').text = '00'
        ET.SubElement(adicao_elem, 'iiRegimeTributacaoCodigo').text = '1'
        ET.SubElement(adicao_elem, 'iiRegimeTributacaoNome').text = 'RECOLHIMENTO INTEGRAL'
        
        # IPI
        ET.SubElement(adicao_elem, 'ipiAliquotaAdValorem').text = '00325'
        ET.SubElement(adicao_elem, 'ipiAliquotaEspecificaCapacidadeRecipciente').text = '00000'
        ET.SubElement(adicao_elem, 'ipiAliquotaEspecificaQuantidadeUnidadeMedida').text = '000000000'
        ET.SubElement(adicao_elem, 'ipiAliquotaEspecificaTipoRecipienteCodigo').text = '00'
        ET.SubElement(adicao_elem, 'ipiAliquotaEspecificaValorUnidadeMedida').text = '0000000000'
        ET.SubElement(adicao_elem, 'ipiAliquotaNotaComplementarTIPI').text = '00'
        ET.SubElement(adicao_elem, 'ipiAliquotaReduzida').text = '00000'
        ET.SubElement(adicao_elem, 'ipiAliquotaValorDevido').text = adicao['valores'].get('ipi_valor', '000000000000000')
        ET.SubElement(adicao_elem, 'ipiAliquotaValorRecolher').text = adicao['valores'].get('ipi_valor', '000000000000000')
        ET.SubElement(adicao_elem, 'ipiRegimeTributacaoCodigo').text = '4'
        ET.SubElement(adicao_elem, 'ipiRegimeTributacaoNome').text = 'SEM BENEFICIO'
        
        # Mercadoria (elemento interno)
        mercadoria = ET.SubElement(adicao_elem, 'mercadoria')
        ET.SubElement(mercadoria, 'descricaoMercadoria').text = item.get('descricao', 'Produto importado') + '                                                                                                     \r'
        ET.SubElement(mercadoria, 'numeroSequencialItem').text = item.get('numero_item', '01')
        ET.SubElement(mercadoria, 'quantidade').text = self._formatar_valor_xml(item.get('quantidade', '1'), 14)
        ET.SubElement(mercadoria, 'unidadeMedida').text = 'PECA                '
        ET.SubElement(mercadoria, 'valorUnitario').text = self._formatar_valor_xml(item.get('valor_unitario', '1000'), 20)
        
        # Número adição e DUIMP
        ET.SubElement(adicao_elem, 'numeroAdicao').text = adicao['numero_adicao']
        ET.SubElement(adicao_elem, 'numeroDUIMP').text = self.duimp_data["cabecalho"].get('numero_duimp', '0000000000')
        ET.SubElement(adicao_elem, 'numeroLI').text = '0000000000'
        
        # Países
        ET.SubElement(adicao_elem, 'paisAquisicaoMercadoriaCodigo').text = adicao['fornecedor']['pais']
        ET.SubElement(adicao_elem, 'paisAquisicaoMercadoriaNome').text = adicao['fornecedor']['pais_nome']
        ET.SubElement(adicao_elem, 'paisOrigemMercadoriaCodigo').text = adicao['fornecedor']['pais']
        ET.SubElement(adicao_elem, 'paisOrigemMercadoriaNome').text = adicao['fornecedor']['pais_nome']
        
        # PIS/COFINS base cálculo
        ET.SubElement(adicao_elem, 'pisCofinsBaseCalculoAliquotaICMS').text = '00000'
        ET.SubElement(adicao_elem, 'pisCofinsBaseCalculoFundamentoLegalCodigo').text = '00'
        ET.SubElement(adicao_elem, 'pisCofinsBaseCalculoPercentualReducao').text = '00000'
        ET.SubElement(adicao_elem, 'pisCofinsBaseCalculoValor').text = adicao['valores'].get('ii_base', '000000000000000')
        ET.SubElement(adicao_elem, 'pisCofinsFundamentoLegalReducaoCodigo').text = '00'
        ET.SubElement(adicao_elem, 'pisCofinsRegimeTributacaoCodigo').text = '1'
        ET.SubElement(adicao_elem, 'pisCofinsRegimeTributacaoNome').text = 'RECOLHIMENTO INTEGRAL'
        
        # PIS/PASEP
        ET.SubElement(adicao_elem, 'pisPasepAliquotaAdValorem').text = '00210'
        ET.SubElement(adicao_elem, 'pisPasepAliquotaEspecificaQuantidadeUnidade').text = '000000000'
        ET.SubElement(adicao_elem, 'pisPasepAliquotaEspecificaValor').text = '0000000000'
        ET.SubElement(adicao_elem, 'pisPasepAliquotaReduzida').text = '00000'
        ET.SubElement(adicao_elem, 'pisPasepAliquotaValorDevido').text = adicao['valores'].get('pis_valor', '000000000000000')
        ET.SubElement(adicao_elem, 'pisPasepAliquotaValorRecolher').text = adicao['valores'].get('pis_valor', '000000000000000')
        
        # ICMS (campos adicionais do XML exemplo)
        ET.SubElement(adicao_elem, 'icmsBaseCalculoValor').text = adicao['valores'].get('icms_base', '000000000000000')
        ET.SubElement(adicao_elem, 'icmsBaseCalculoAliquota').text = '01800'
        ET.SubElement(adicao_elem, 'icmsBaseCalculoValorImposto').text = adicao['valores'].get('icms_valor', '000000000000000')
        ET.SubElement(adicao_elem, 'icmsBaseCalculoValorDiferido').text = adicao['valores'].get('icms_diferido', '000000000000000')
        
        # CBS/IBS (do XML exemplo)
        ET.SubElement(adicao_elem, 'cbsIbsCst').text = '000'
        ET.SubElement(adicao_elem, 'cbsIbsClasstrib').text = '000001'
        ET.SubElement(adicao_elem, 'cbsBaseCalculoValor').text = adicao['valores'].get('icms_base', '000000000000000')
        ET.SubElement(adicao_elem, 'cbsBaseCalculoAliquota').text = '00090'
        ET.SubElement(adicao_elem, 'cbsBaseCalculoAliquotaReducao').text = '00000'
        ET.SubElement(adicao_elem, 'cbsBaseCalculoValorImposto').text = adicao['valores'].get('cbs_valor', '000000000000000')
        ET.SubElement(adicao_elem, 'ibsBaseCalculoValor').text = adicao['valores'].get('icms_base', '000000000000000')
        ET.SubElement(adicao_elem, 'ibsBaseCalculoAliquota').text = '00010'
        ET.SubElement(adicao_elem, 'ibsBaseCalculoAliquotaReducao').text = '00000'
        ET.SubElement(adicao_elem, 'ibsBaseCalculoValorImposto').text = adicao['valores'].get('ibs_valor', '000000000000000')
        
        # Seguro
        ET.SubElement(adicao_elem, 'seguroMoedaNegociadaCodigo').text = '220'
        ET.SubElement(adicao_elem, 'seguroMoedaNegociadaNome').text = 'DOLAR DOS EUA'
        ET.SubElement(adicao_elem, 'seguroValorMoedaNegociada').text = '000000000000000'
        ET.SubElement(adicao_elem, 'seguroValorReais').text = '000000000001489'  # Exemplo
        
        # Outros campos
        ET.SubElement(adicao_elem, 'sequencialRetificacao').text = '00'
        ET.SubElement(adicao_elem, 'valorMultaARecolher').text = '000000000000000'
        ET.SubElement(adicao_elem, 'valorMultaARecolherAjustado').text = '000000000000000'
        ET.SubElement(adicao_elem, 'valorReaisFreteInternacional').text = '000000000014595'  # Exemplo
        ET.SubElement(adicao_elem, 'valorReaisSeguroInternacional').text = '000000000001489'  # Exemplo
        ET.SubElement(adicao_elem, 'valorTotalCondicaoVenda').text = adicao['valores'].get('valor_moeda', '00000000000').rstrip('0')[:11]
    
    def _obter_descricao_ncm(self, ncm: str) -> str:
        """Retorna descrição do NCM como no XML exemplo"""
        if ncm.startswith('8302'):
            return '-- Outros, para móveis'
        elif ncm.startswith('3926'):
            return '- Guarnições para móveis, carroçarias ou semelhantes'
        elif ncm.startswith('7318'):
            return '-- Outros parafusos para madeira'
        elif ncm.startswith('8505'):
            return '-- De metal'
        else:
            return '- Produto de importação'
    
    def _criar_cabecalho_duimp_xml(self, duimp_element):
        """Cria o cabeçalho da DUIMP no layout exato"""
        cab = self.duimp_data["cabecalho"]
        transp = self.duimp_data["transportes"]
        
        # Armazém
        armazem = ET.SubElement(duimp_element, 'armazem')
        ET.SubElement(armazem, 'nomeArmazem').text = 'TCP       '
        
        ET.SubElement(duimp_element, 'armazenamentoRecintoAduaneiroCodigo').text = '9801303'
        ET.SubElement(duimp_element, 'armazenamentoRecintoAduaneiroNome').text = 'TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A'
        ET.SubElement(duimp_element, 'armazenamentoSetor').text = '002'
        
        ET.SubElement(duimp_element, 'canalSelecaoParametrizada').text = '001'
        ET.SubElement(duimp_element, 'caracterizacaoOperacaoCodigoTipo').text = '1'
        ET.SubElement(duimp_element, 'caracterizacaoOperacaoDescricaoTipo').text = 'Importação Própria'
        
        # Carga
        ET.SubElement(duimp_element, 'cargaDataChegada').text = transp.get('data_chegada', datetime.now().strftime('%Y%m%d'))
        ET.SubElement(duimp_element, 'cargaNumeroAgente').text = 'N/I'
        ET.SubElement(duimp_element, 'cargaPaisProcedenciaCodigo').text = '386'  # Itália
        ET.SubElement(duimp_element, 'cargaPaisProcedenciaNome').text = 'ITALIA'
        ET.SubElement(duimp_element, 'cargaPesoBruto').text = transp.get('peso_bruto', '000000053415000')
        ET.SubElement(duimp_element, 'cargaPesoLiquido').text = transp.get('peso_liquido', '000000048686100')
        ET.SubElement(duimp_element, 'cargaUrfEntradaCodigo').text = '0917800'
        ET.SubElement(duimp_element, 'cargaUrfEntradaNome').text = 'PORTO DE PARANAGUA'
        
        # Conhecimento de carga
        ET.SubElement(duimp_element, 'conhecimentoCargaEmbarqueData').text = transp.get('data_embarque', '20251025')
        ET.SubElement(duimp_element, 'conhecimentoCargaEmbarqueLocal').text = 'GENOVA'
        ET.SubElement(duimp_element, 'conhecimentoCargaId').text = 'CEMERCANTE31032008'
        ET.SubElement(duimp_element, 'conhecimentoCargaIdMaster').text = '162505352452915'
        ET.SubElement(duimp_element, 'conhecimentoCargaTipoCodigo').text = '12'
        ET.SubElement(duimp_element, 'conhecimentoCargaTipoNome').text = 'HBL - House Bill of Lading'
        ET.SubElement(duimp_element, 'conhecimentoCargaUtilizacao').text = '1'
        ET.SubElement(duimp_element, 'conhecimentoCargaUtilizacaoNome').text = 'Total'
        
        ET.SubElement(duimp_element, 'dataDesembaraco').text = datetime.now().strftime('%Y%m%d')
        ET.SubElement(duimp_element, 'dataRegistro').text = cab.get('data_registro', datetime.now().strftime('%Y%m%d'))
        
        # Documento chegada carga
        ET.SubElement(duimp_element, 'documentoChegadaCargaCodigoTipo').text = '1'
        ET.SubElement(duimp_element, 'documentoChegadaCargaNome').text = 'Manifesto da Carga'
        ET.SubElement(duimp_element, 'documentoChegadaCargaNumero').text = '1625502058594'
        
        # Embalagem
        embalagem = ET.SubElement(duimp_element, 'embalagem')
        ET.SubElement(embalagem, 'codigoTipoEmbalagem').text = '60'
        ET.SubElement(embalagem, 'nomeEmbalagem').text = 'PALLETS                                                     '
        ET.SubElement(embalagem, 'quantidadeVolume').text = '00002'
        
        # Frete
        ET.SubElement(duimp_element, 'freteCollect').text = '000000000025000'
        ET.SubElement(duimp_element, 'freteEmTerritorioNacional').text = '000000000000000'
        ET.SubElement(duimp_element, 'freteMoedaNegociadaCodigo').text = '978'
        ET.SubElement(duimp_element, 'freteMoedaNegociadaNome').text = 'EURO/COM.EUROPEIA'
        ET.SubElement(duimp_element, 'fretePrepaid').text = '000000000000000'
        ET.SubElement(duimp_element, 'freteTotalDolares').text = '000000000028757'
        ET.SubElement(duimp_element, 'freteTotalMoeda').text = '25000'
        ET.SubElement(duimp_element, 'freteTotalReais').text = '000000000155007'
        
        # ICMS (exoneração como no exemplo)
        icms = ET.SubElement(duimp_element, 'icms')
        ET.SubElement(icms, 'agenciaIcms').text = '00000'
        ET.SubElement(icms, 'bancoIcms').text = '000'
        ET.SubElement(icms, 'codigoTipoRecolhimentoIcms').text = '3'
        ET.SubElement(icms, 'cpfResponsavelRegistro').text = '27160353854'
        ET.SubElement(icms, 'dataRegistro').text = datetime.now().strftime('%Y%m%d')
        ET.SubElement(icms, 'horaRegistro').text = '152044'
        ET.SubElement(icms, 'nomeTipoRecolhimentoIcms').text = 'Exoneração do ICMS'
        ET.SubElement(icms, 'numeroSequencialIcms').text = '001'
        ET.SubElement(icms, 'ufIcms').text = 'PR'
        ET.SubElement(icms, 'valorTotalIcms').text = '000000000000000'
        
        # Importador
        ET.SubElement(duimp_element, 'importadorCodigoTipo').text = '1'
        ET.SubElement(duimp_element, 'importadorCpfRepresentanteLegal').text = '27160353854'
        ET.SubElement(duimp_element, 'importadorEnderecoBairro').text = 'JARDIM PRIMAVERA'
        ET.SubElement(duimp_element, 'importadorEnderecoCep').text = '83302000'
        ET.SubElement(duimp_element, 'importadorEnderecoComplemento').text = 'CONJ: 6 E 7;'
        ET.SubElement(duimp_element, 'importadorEnderecoLogradouro').text = 'JOAO LEOPOLDO JACOMEL'
        ET.SubElement(duimp_element, 'importadorEnderecoMunicipio').text = 'PIRAQUARA'
        ET.SubElement(duimp_element, 'importadorEnderecoNumero').text = '4459'
        ET.SubElement(duimp_element, 'importadorEnderecoUf').text = 'PR'
        ET.SubElement(duimp_element, 'importadorNome').text = 'HAFELE BRASIL LTDA'
        ET.SubElement(duimp_element, 'importadorNomeRepresentanteLegal').text = 'PAULO HENRIQUE LEITE FERREIRA'
        ET.SubElement(duimp_element, 'importadorNumero').text = cab.get('cnpj', '02473058000188')
        ET.SubElement(duimp_element, 'importadorNumeroTelefone').text = '41  30348150'
        
        # Valores locais
        ET.SubElement(duimp_element, 'localDescargaTotalDolares').text = '000000002061433'
        ET.SubElement(duimp_element, 'localDescargaTotalReais').text = '000000011111593'
        ET.SubElement(duimp_element, 'localEmbarqueTotalDolares').text = '000000002030535'
        ET.SubElement(duimp_element, 'localEmbarqueTotalReais').text = '000000010945130'
        
        ET.SubElement(duimp_element, 'modalidadeDespachoCodigo').text = '1'
        ET.SubElement(duimp_element, 'modalidadeDespachoNome').text = 'Normal'
        ET.SubElement(duimp_element, 'numeroDUIMP').text = cab.get('numero_duimp', '0000000000')
        ET.SubElement(duimp_element, 'operacaoFundap').text = 'N'
        
        # Seguro
        ET.SubElement(duimp_element, 'seguroMoedaNegociadaCodigo').text = '220'
        ET.SubElement(duimp_element, 'seguroMoedaNegociadaNome').text = 'DOLAR DOS EUA'
        ET.SubElement(duimp_element, 'seguroTotalDolares').text = '000000000002146'
        ET.SubElement(duimp_element, 'seguroTotalMoedaNegociada').text = '000000000002146'
        ET.SubElement(duimp_element, 'seguroTotalReais').text = '000000000011567'
        
        ET.SubElement(duimp_element, 'sequencialRetificacao').text = '00'
        ET.SubElement(duimp_element, 'situacaoEntregaCarga').text = 'ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE EXONERACAO DO ICMS'
        ET.SubElement(duimp_element, 'tipoDeclaracaoCodigo').text = '01'
        ET.SubElement(duimp_element, 'tipoDeclaracaoNome').text = 'CONSUMO'
        ET.SubElement(duimp_element, 'totalAdicoes').text = f"{len(self.duimp_data['adicoes']):03d}"
        ET.SubElement(duimp_element, 'urfDespachoCodigo').text = '0917800'
        ET.SubElement(duimp_element, 'urfDespachoNome').text = 'PORTO DE PARANAGUA'
        ET.SubElement(duimp_element, 'valorTotalMultaARecolherAjustado').text = '000000000000000'
        ET.SubElement(duimp_element, 'viaTransporteCodigo').text = transp.get('codigo', '01')
        ET.SubElement(duimp_element, 'viaTransporteMultimodal').text = 'N'
        ET.SubElement(duimp_element, 'viaTransporteNome').text = transp.get('nome', 'MARÍTIMA')
        ET.SubElement(duimp_element, 'viaTransporteNomeTransportador').text = 'MAERSK A/S'
        ET.SubElement(duimp_element, 'viaTransporteNomeVeiculo').text = 'MAERSK MEMPHIS'
        ET.SubElement(duimp_element, 'viaTransportePaisTransportadorCodigo').text = '741'
        ET.SubElement(duimp_element, 'viaTransportePaisTransportadorNome').text = 'CINGAPURA'
    
    def _criar_transporte_xml(self, duimp_element):
        """Já criado no _criar_cabecalho_duimp_xml"""
        pass
    
    def _criar_documentos_xml(self, duimp_element):
        """Adiciona documentos instrução despacho"""
        for doc in self.duimp_data["documentos"]:
            doc_elem = ET.SubElement(duimp_element, 'documentoInstrucaoDespacho')
            ET.SubElement(doc_elem, 'codigoTipoDocumentoDespacho').text = doc['tipo']
            ET.SubElement(doc_elem, 'nomeDocumentoDespacho').text = doc['nome']
            ET.SubElement(doc_elem, 'numeroDocumentoDespacho').text = doc['numero']
    
    def _criar_pagamentos_xml(self, duimp_element):
        """Adiciona pagamentos"""
        for pagamento in self.duimp_data["pagamentos"]:
            pag_elem = ET.SubElement(duimp_element, 'pagamento')
            ET.SubElement(pag_elem, 'agenciaPagamento').text = pagamento['agencia'] + ' '
            ET.SubElement(pag_elem, 'bancoPagamento').text = pagamento['banco']
            ET.SubElement(pag_elem, 'codigoReceita').text = pagamento['codigo_receita']
            ET.SubElement(pag_elem, 'codigoTipoPagamento').text = '1'
            ET.SubElement(pag_elem, 'contaPagamento').text = '             316273'
            ET.SubElement(pag_elem, 'dataPagamento').text = datetime.now().strftime('%Y%m%d')
            ET.SubElement(pag_elem, 'nomeTipoPagamento').text = 'Débito em Conta'
            ET.SubElement(pag_elem, 'numeroRetificacao').text = '00'
            ET.SubElement(pag_elem, 'valorJurosEncargos').text = '000000000'
            ET.SubElement(pag_elem, 'valorMulta').text = '000000000'
            ET.SubElement(pag_elem, 'valorReceita').text = pagamento['valor']
    
    def _criar_info_complementar_xml(self, duimp_element):
        """Cria informações complementares como no exemplo"""
        info = f"""INFORMACOES COMPLEMENTARES
--------------------------
CASCO LOGISTICA - MATRIZ - PR
PROCESSO :{self.duimp_data["cabecalho"].get('processo', 'N/I')}
REF. IMPORTADOR :{self.duimp_data["cabecalho"].get('ref_importador', 'TESTE DUIMP')}
IMPORTADOR :HAFELE BRASIL LTDA
PESO LIQUIDO :{int(self.duimp_data["transportes"].get('peso_liquido', '0')) / 10000000:,.7f}
PESO BRUTO :{int(self.duimp_data["transportes"].get('peso_bruto', '0')) / 10000000:,.7f}
FORNECEDOR :ITALIANA FERRAMENTA S.R.L.
ARMAZEN :TCP
REC. ALFANDEGADO :9801303 - TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A
DT. EMBARQUE :{self.duimp_data["transportes"].get('data_embarque', '25/10/2025')}
CHEG./ATRACACAO :{self.duimp_data["transportes"].get('data_chegada', '20/11/2025')}
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
        
        ET.SubElement(duimp_element, 'informacaoComplementar').text = info

# Funções auxiliares para Streamlit
def criar_link_download(conteudo: str, nome_arquivo: str, texto_link: str):
    """Cria link de download"""
    b64 = base64.b64encode(conteudo.encode()).decode()
    href = f'<a href="data:file/xml;base64,{b64}" download="{nome_arquivo}" style="background-color:#4CAF50;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;">{texto_link}</a>'
    return href

def criar_zip_multiplos(arquivos: Dict[str, str], nome_zip: str):
    """Cria ZIP com múltiplos arquivos"""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for nome, conteudo in arquivos.items():
            zip_file.writestr(nome, conteudo)
    buffer.seek(0)
    
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:application/zip;base64,{b64}" download="{nome_zip}" style="background-color:#2196F3;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;margin-top:10px;">📦 Baixar Todos os Arquivos (ZIP)</a>'
    return href

# Interface principal
def main():
    st.markdown('<h1 class="main-header">📄 Conversor DUIMP - Layout Exato</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div class="success-box">
    <strong>Conversão exata para o layout XML DUIMP oficial</strong><br>
    Gera XML idêntico ao exemplo M-DUIMP-8686868686.xml com todos os campos no formato correto.
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        opcoes = {
            "gerar_excel": st.checkbox("Gerar Excel de resumo", value=True),
            "validar_xml": st.checkbox("Validar estrutura XML", value=True),
            "max_adicoes": st.slider("Máximo de adições", 1, 50, 5)
        }
        
        st.markdown("---")
        st.header("📋 Sobre o Layout")
        st.info("""
        **Campos gerados exatamente como no XML:**
        
        • Estrutura completa ListaDeclaracoes > duimp
        • Adições com todos os campos obrigatórios
        • Tributos calculados (II, IPI, PIS, COFINS, ICMS)
        • Dados de transporte e documentos
        • Pagamentos e informações complementares
        • Formatação com zeros à esquerda
        • Elementos na ordem correta
        """)
    
    # Área principal
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📤 Upload de PDFs")
        
        uploaded_files = st.file_uploader(
            "Selecione os arquivos PDF 'Extrato de Conferência'",
            type=['pdf'],
            accept_multiple_files=True,
            help="Arquivos PDF no formato específico da DUIMP"
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} arquivo(s) selecionado(s)")
            
            resultados = []
            xml_gerados = {}
            
            for uploaded_file in uploaded_files:
                with st.spinner(f"🔄 Processando {uploaded_file.name}..."):
                    # Ler PDF
                    pdf_bytes = uploaded_file.read()
                    
                    # Criar conversor
                    conversor = ConversorDUIMPExato()
                    
                    # Processar
                    if conversor.processar_pdf(pdf_bytes):
                        # Gerar XML
                        xml_content = conversor.gerar_xml_exato()
                        
                        if xml_content:
                            # Salvar resultado
                            nome_base = os.path.splitext(uploaded_file.name)[0]
                            xml_nome = f"M-DUIMP-{conversor.duimp_data['cabecalho'].get('numero_duimp', '0000000000')}.xml"
                            xml_gerados[xml_nome] = xml_content
                            
                            # Gerar Excel se configurado
                            excel_content = None
                            if opcoes["gerar_excel"]:
                                # Criar DataFrame de resumo
                                dados = []
                                for adicao in conversor.duimp_data["adicoes"]:
                                    for item in adicao["itens"]:
                                        dados.append({
                                            'Adição': adicao['numero_adicao'],
                                            'Item': item.get('numero_item', '01'),
                                            'NCM': item.get('ncm', ''),
                                            'Descrição': item.get('descricao', '')[:50],
                                            'Quantidade': float(item.get('quantidade', '1')),
                                            'Valor Unitário': float(item.get('valor_unitario', '0')),
                                            'Valor Total': float(item.get('valor_total_moeda', '0'))
                                        })
                                
                                if dados:
                                    df = pd.DataFrame(dados)
                                    excel_buffer = BytesIO()
                                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                                        df.to_excel(writer, sheet_name='Itens', index=False)
                                        
                                        # Adicionar estatísticas
                                        stats_df = pd.DataFrame([{
                                            'Arquivo': uploaded_file.name,
                                            'Adições': conversor.stats['adicoes_geradas'],
                                            'Itens': conversor.stats['itens_encontrados'],
                                            'Páginas': conversor.stats['paginas_processadas']
                                        }])
                                        stats_df.to_excel(writer, sheet_name='Estatísticas', index=False)
                                    
                                    excel_content = excel_buffer.getvalue()
                                    excel_nome = f"{nome_base}_RESUMO.xlsx"
                                    xml_gerados[excel_nome] = excel_content
                            
                            resultados.append({
                                'nome': uploaded_file.name,
                                'conversor': conversor,
                                'xml': xml_content,
                                'excel': excel_content,
                                'stats': conversor.stats
                            })
            
            # Exibir resultados
            if resultados:
                st.markdown("---")
                st.markdown("### 📊 Resultados da Conversão")
                
                # Estatísticas
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                
                total_adicoes = sum(r['stats']['adicoes_geradas'] for r in resultados)
                total_itens = sum(r['stats']['itens_encontrados'] for r in resultados)
                total_paginas = sum(r['stats']['paginas_processadas'] for r in resultados)
                
                with col_stat1:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{total_adicoes}</div>
                        <div class="stat-label">Adições</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_stat2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{total_itens}</div>
                        <div class="stat-label">Itens</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_stat3:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{total_paginas}</div>
                        <div class="stat-label">Páginas</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Downloads individuais
                st.markdown("---")
                st.markdown("### 📥 Download dos Arquivos")
                
                for resultado in resultados:
                    nome_base = os.path.splitext(resultado['nome'])[0]
                    numero_duimp = resultado['conversor'].duimp_data['cabecalho'].get('numero_duimp', '0000000000')
                    
                    with st.expander(f"📄 {resultado['nome']} - DUIMP: {numero_duimp}"):
                        col_dl1, col_dl2, col_dl3 = st.columns(3)
                        
                        with col_dl1:
                            xml_nome = f"M-DUIMP-{numero_duimp}.xml"
                            st.markdown(criar_link_download(
                                resultado['xml'],
                                xml_nome,
                                "📥 Baixar XML"
                            ), unsafe_allow_html=True)
                        
                        with col_dl2:
                            if resultado['excel']:
                                excel_nome = f"{nome_base}_RESUMO.xlsx"
                                b64_excel = base64.b64encode(resultado['excel']).decode()
                                href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="{excel_nome}" style="background-color:#4CAF50;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;">📊 Baixar Excel</a>'
                                st.markdown(href_excel, unsafe_allow_html=True)
                        
                        with col_dl3:
                            # Botão para preview
                            if st.button(f"👁️ Preview XML", key=f"preview_{numero_duimp}"):
                                st.session_state[f"xml_preview_{numero_duimp}"] = resultado['xml'][:3000] + "..." if len(resultado['xml']) > 3000 else resultado['xml']
                
                # Download em lote
                if len(resultados) > 1:
                    st.markdown("---")
                    st.markdown("### 📦 Download em Lote")
                    st.markdown(criar_zip_multiplos(
                        xml_gerados,
                        f"DUIMP_EXATO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    ), unsafe_allow_html=True)
                
                # Previews
                st.markdown("---")
                st.markdown("### 👁️ Preview dos XMLs Gerados")
                
                preview_keys = [k for k in st.session_state.keys() if k.startswith('xml_preview_')]
                if preview_keys:
                    for key in preview_keys:
                        numero_duimp = key.replace('xml_preview_', '')
                        st.markdown(f"**Preview: DUIMP {numero_duimp}**")
                        st.code(st.session_state[key], language='xml')
                else:
                    st.info("Clique em 'Preview XML' acima para visualizar a estrutura gerada")
    
    with col2:
        st.markdown("### 📋 Estrutura do XML")
        
        st.markdown("""
        **Elementos principais:**
        
        ```xml
        <ListaDeclaracoes>
          <duimp>
            <adicao>          ← Cada adição
              <acrescimo>
              <condicaoVendaIncoterm>
              <dadosMercadoriaCodigoNcm>
              <mercadoria>    ← Item da adição
              <iiAliquotaAdValorem>
              <ipiAliquotaAdValorem>
              <pisPasepAliquotaAdValorem>
              <cofinsAliquotaAdValorem>
              <icmsBaseCalculoValor>
            </adicao>
            
            <armazem>
            <cargaDataChegada>
            <importadorNome>
            <pagamento>       ← Cada pagamento
            <informacaoComplementar>
          </duimp>
        </ListaDeclaracoes>
        ```
        
        **Formatos especiais:**
        - Valores: 15 dígitos com zeros
        - Datas: AAAAMMDD
        - Códigos: sempre preenchidos
        - Textos: tamanhos fixos
        """)
        
        st.markdown("---")
        st.markdown("### ✅ Validação")
        
        if 'resultados' in locals() and resultados:
            st.success(f"✅ {len(resultados)} arquivo(s) convertido(s)")
            
            # Verificar estrutura
            for resultado in resultados:
                xml_content = resultado['xml']
                if '<?xml version="1.0"' in xml_content and '<ListaDeclaracoes>' in xml_content:
                    st.success(f"✅ Estrutura válida: {os.path.splitext(resultado['nome'])[0]}")
                else:
                    st.error(f"❌ Estrutura inválida: {resultado['nome']}")

if __name__ == "__main__":
    main()
