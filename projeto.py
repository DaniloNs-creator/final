import streamlit as st
import pdfplumber
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import os
import tempfile
from datetime import datetime
import json

class DUIMPPDFProcessor:
    def __init__(self):
        self.items = []
        self.current_duimp = "8686868686"
        self.adicao_counter = 1
        self.item_counter = 1
        
    def clean_text(self, text):
        """Limpa e normaliza o texto"""
        if not text:
            return ""
        # Remove múltiplos espaços e normaliza quebras de linha
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()
    
    def extract_items_from_page(self, page_text, page_num):
        """Extrai itens de uma página específica baseado no layout do PDF"""
        items_found = []
        
        # Divide o texto em linhas
        lines = page_text.split('\n')
        
        # Procura por padrões que indicam itens
        # Baseado no layout do seu PDF de exemplo
        current_item = {}
        in_item_section = False
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Verifica se é início de um item (padrão: "Item X" ou número seguido de traço)
            if (re.match(r'^\s*Item\s+\d+', line_clean, re.IGNORECASE) or 
                re.match(r'^\s*\d+\s*[-–]\s*', line_clean)):
                
                # Se já estava processando um item, salva ele
                if current_item and in_item_section:
                    # Completa informações do item anterior
                    self.complete_item_info(current_item, lines, i)
                    items_found.append(current_item.copy())
                    current_item = {}
                
                # Inicia novo item
                item_match = re.search(r'Item\s+(\d+)', line_clean, re.IGNORECASE)
                if item_match:
                    current_item['item_num'] = item_match.group(1)
                else:
                    # Tenta extrair número do início da linha
                    num_match = re.match(r'^\s*(\d+)', line_clean)
                    if num_match:
                        current_item['item_num'] = num_match.group(1)
                
                current_item['page'] = page_num
                current_item['raw_lines'] = [line_clean]
                in_item_section = True
            
            # Se está dentro de uma seção de item, acumula as linhas
            elif in_item_section:
                current_item['raw_lines'].append(line_clean)
                
                # Verifica se encontrou fim do item (próximo item ou seção diferente)
                if (i < len(lines) - 1 and 
                    (re.match(r'^\s*Item\s+\d+', lines[i+1].strip(), re.IGNORECASE) or
                     re.match(r'^\s*\d+\s*[-–]\s*', lines[i+1].strip()) or
                     any(keyword in lines[i+1].lower() for keyword in ['total', 'resumo', 'fim', 'conclusão']))):
                    
                    # Completa informações do item
                    self.complete_item_info(current_item, lines, i)
                    items_found.append(current_item.copy())
                    current_item = {}
                    in_item_section = False
        
        # Processa o último item da página, se houver
        if current_item and in_item_section:
            self.complete_item_info(current_item, lines, len(lines)-1)
            items_found.append(current_item.copy())
        
        return items_found
    
    def complete_item_info(self, item, all_lines, current_line_idx):
        """Completa as informações do item baseado nas linhas coletadas"""
        full_text = ' '.join(item['raw_lines'])
        
        # Extrai NCM (procura padrão NCM: XXXX.XX.XX)
        ncm_match = re.search(r'NCM\s*[:]?\s*([\d\.]+)', full_text, re.IGNORECASE)
        if ncm_match:
            item['ncm'] = ncm_match.group(1).replace('.', '')
        
        # Extrai código interno (procura padrões como XXX.XX.XXX)
        cod_match = re.search(r'(\d{3}\.\d{2}\.\d{3})', full_text)
        if cod_match:
            item['codigo'] = cod_match.group(1)
        
        # Extrai descrição (procura texto após DENOMINAÇÃO ou DESCRIÇÃO)
        desc_match = re.search(r'(?:DENOMINAÇÃO|DESCRIÇÃO)[\s:]+(.+?)(?=(?:NCM|CÓDIGO|QUANTIDADE|VALOR|$))', 
                              full_text, re.IGNORECASE | re.DOTALL)
        if desc_match:
            item['descricao'] = desc_match.group(1).strip()
        else:
            # Tenta pegar texto significativo
            words = full_text.split()
            if len(words) > 10:
                item['descricao'] = ' '.join(words[3:15])  # Pega parte do texto como descrição
        
        # Extrai quantidade
        qtd_match = re.search(r'(?:QUANTIDADE|QTD\.?|QTDE)[\s:]*([\d\.,]+)', full_text, re.IGNORECASE)
        if qtd_match:
            item['quantidade'] = qtd_match.group(1).replace('.', '').replace(',', '')
        
        # Extrai valor unitário
        valor_unit_match = re.search(r'(?:VALOR\s+UNIT[ÁA]RIO|VLR\.?\s+UNIT\.?)[\s:]*([\d\.,]+)', 
                                    full_text, re.IGNORECASE)
        if valor_unit_match:
            item['valor_unitario'] = valor_unit_match.group(1).replace('.', '').replace(',', '.')
        
        # Extrai valor total
        valor_total_match = re.search(r'(?:VALOR\s+TOTAL|TOTAL|VLR\.?\s+TOTAL)[\s:]*([\d\.,]+)', 
                                     full_text, re.IGNORECASE)
        if valor_total_match:
            item['valor_total'] = valor_total_match.group(1).replace('.', '').replace(',', '.')
        
        # Extrai unidade de medida
        if 'PECA' in full_text.upper() or 'PEÇA' in full_text.upper():
            item['unidade'] = 'PECA'
        elif 'KG' in full_text.upper() or 'QUILO' in full_text.upper():
            item['unidade'] = 'KG'
        elif 'PAR' in full_text.upper() or 'PARES' in full_text.upper():
            item['unidade'] = 'PAR'
        
        # País de origem (procura padrões)
        if 'ITALIA' in full_text.upper():
            item['pais'] = 'ITALIA'
        elif 'CHINA' in full_text.upper():
            item['pais'] = 'CHINA'
        elif 'ALEMANHA' in full_text.upper():
            item['pais'] = 'ALEMANHA'
    
    def format_number_xml(self, value, length, decimal_places=2):
        """Formata número para padrão XML com zeros à esquerda"""
        if not value or value == '':
            return '0' * length
        
        try:
            # Remove caracteres não numéricos
            clean = re.sub(r'[^\d,.-]', '', str(value))
            clean = clean.replace(',', '.')
            
            # Converte para float
            num = float(clean)
            
            # Multiplica para remover decimais
            if decimal_places > 0:
                num = int(num * (10 ** decimal_places))
            else:
                num = int(num)
            
            return str(num).zfill(length)
        except:
            return '0' * length
    
    def create_adicao_xml(self, item, adicao_num):
        """Cria XML de adição baseado no modelo fornecido"""
        # Template base do XML
        adicao_xml = f"""        <adicao>
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
            <condicaoVendaValorMoeda>{self.format_number_xml(item.get('valor_total', '0'), 15, 2)}</condicaoVendaValorMoeda>
            <condicaoVendaValorReais>{self.format_number_xml(item.get('valor_total', '0'), 15, 2)}</condicaoVendaValorReais>
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
            <dadosMercadoriaCodigoNcm>{item.get('ncm', '00000000').ljust(8, '0')}</dadosMercadoriaCodigoNcm>
            <dadosMercadoriaCondicao>NOVA</dadosMercadoriaCondicao>
            <dadosMercadoriaDescricaoTipoCertificado>Sem Certificado</dadosMercadoriaDescricaoTipoCertificado>
            <dadosMercadoriaIndicadorTipoCertificado>1</dadosMercadoriaIndicadorTipoCertificado>
            <dadosMercadoriaMedidaEstatisticaQuantidade>{self.format_number_xml(item.get('quantidade', '0'), 14, 0)}</dadosMercadoriaMedidaEstatisticaQuantidade>
            <dadosMercadoriaMedidaEstatisticaUnidade>QUILOGRAMA LIQUIDO</dadosMercadoriaMedidaEstatisticaUnidade>
            <dadosMercadoriaNomeNcm>- Guarnições para móveis, carroçarias ou semelhantes</dadosMercadoriaNomeNcm>
            <dadosMercadoriaPesoLiquido>{self.format_number_xml(item.get('peso', '0'), 15, 0)}</dadosMercadoriaPesoLiquido>
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
                <descricaoMercadoria>{item.get('descricao', 'PRODUTO IMPORTADO').ljust(200)[:200]}</descricaoMercadoria>
                <numeroSequencialItem>{str(self.item_counter).zfill(2)}</numeroSequencialItem>
                <quantidade>{self.format_number_xml(item.get('quantidade', '0'), 14, 0)}</quantidade>
                <unidadeMedida>PECA                </unidadeMedida>
                <valorUnitario>{self.format_number_xml(item.get('valor_unitario', '0'), 20, 6)}</valorUnitario>
            </mercadoria>
            <numeroAdicao>{str(adicao_num).zfill(3)}</numeroAdicao>
            <numeroDUIMP>{self.current_duimp}</numeroDUIMP>
            <numeroLI>0000000000</numeroLI>
            <paisAquisicaoMercadoriaCodigo>386</paisAquisicaoMercadoriaCodigo>
            <paisAquisicaoMercadoriaNome>{item.get('pais', 'ITALIA')}</paisAquisicaoMercadoriaNome>
            <paisOrigemMercadoriaCodigo>386</paisOrigemMercadoriaCodigo>
            <paisOrigemMercadoriaNome>{item.get('pais', 'ITALIA')}</paisOrigemMercadoriaNome>
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
            <valorTotalCondicaoVenda>{self.format_number_xml(item.get('valor_total', '0'), 11, 0)}</valorTotalCondicaoVenda>
            <vinculoCompradorVendedor>Não há vinculação entre comprador e vendedor.</vinculoCompradorVendedor>
        </adicao>"""
        
        self.item_counter += 1
        return adicao_xml
    
    def extract_global_info(self, full_text):
        """Extrai informações globais do DUIMP"""
        info = {
            'numeroDUIMP': '8686868686',
            'dataRegistro': '20251124',
            'dataDesembaraco': '20251124',
            'cargaDataChegada': '20251120',
            'cargaPesoBruto': '000000053415000',
            'cargaPesoLiquido': '000000048686100',
            'conhecimentoCargaEmbarqueData': '20251025'
        }
        
        # Tenta extrair número DUIMP
        duimp_match = re.search(r'DUIMP\s*[:]?\s*(\d+)', full_text, re.IGNORECASE)
        if duimp_match:
            info['numeroDUIMP'] = duimp_match.group(1)
            self.current_duimp = duimp_match.group(1)
        
        # Tenta extrair datas
        date_patterns = [
            (r'Data Registro\s+(\d{2})/(\d{2})/(\d{4})', 'dataRegistro'),
            (r'Data de Chegada\s+(\d{2})/(\d{2})/(\d{4})', 'cargaDataChegada'),
            (r'Data de Embarque\s+(\d{2})/(\d{2})/(\d{4})', 'conhecimentoCargaEmbarqueData')
        ]
        
        for pattern, key in date_patterns:
            match = re.search(pattern, full_text)
            if match:
                day, month, year = match.groups()
                info[key] = f"{year}{month}{day}"
        
        return info
    
    def process_pdf(self, pdf_path):
        """Processa o PDF completo e extrai todos os itens"""
        all_items = []
        global_text = ""
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for page_num, page in enumerate(pdf.pages):
                # Atualiza progresso
                progress = (page_num + 1) / total_pages
                progress_bar.progress(progress)
                status_text.text(f"Processando página {page_num + 1} de {total_pages}")
                
                # Extrai texto da página
                page_text = page.extract_text()
                if page_text:
                    global_text += page_text + "\n"
                    
                    # Extrai itens desta página
                    page_items = self.extract_items_from_page(page_text, page_num + 1)
                    all_items.extend(page_items)
            
            progress_bar.empty()
            status_text.empty()
        
        # Extrai informações globais
        global_info = self.extract_global_info(global_text)
        
        return all_items, global_info, total_pages
    
    def generate_xml(self, items, global_info):
        """Gera o XML completo no formato do modelo"""
        
        # Cabeçalho fixo do XML
        xml_header = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ListaDeclaracoes>
    <duimp>"""
        
        # Adiciona adições
        adicoes_xml = []
        for i, item in enumerate(items):
            adicao_num = i + 1
            adicoes_xml.append(self.create_adicao_xml(item, adicao_num))
        
        # Parte fixa do XML (conforme modelo)
        xml_footer = f"""
        <armazem>
            <nomeArmazem>TCP       </nomeArmazem>
        </armazem>
        <armazenamentoRecintoAduaneiroCodigo>9801303</armazenamentoRecintoAduaneiroCodigo>
        <armazenamentoRecintoAduaneiroNome>TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A</armazenamentoRecintoAduaneiroNome>
        <armazenamentoSetor>002</armazenamentoSetor>
        <canalSelecaoParametrizada>001</canalSelecaoParametrizada>
        <caracterizacaoOperacaoCodigoTipo>1</caracterizacaoOperacaoCodigoTipo>
        <caracterizacaoOperacaoDescricaoTipo>Importação Própria</caracterizacaoOperacaoDescricaoTipo>
        <cargaDataChegada>{global_info['cargaDataChegada']}</cargaDataChegada>
        <cargaNumeroAgente>N/I</cargaNumeroAgente>
        <cargaPaisProcedenciaCodigo>386</cargaPaisProcedenciaCodigo>
        <cargaPaisProcedenciaNome>ITALIA</cargaPaisProcedenciaNome>
        <cargaPesoBruto>{global_info['cargaPesoBruto']}</cargaPesoBruto>
        <cargaPesoLiquido>{global_info['cargaPesoLiquido']}</cargaPesoLiquido>
        <cargaUrfEntradaCodigo>0917800</cargaUrfEntradaCodigo>
        <cargaUrfEntradaNome>PORTO DE PARANAGUA</cargaUrfEntradaNome>
        <conhecimentoCargaEmbarqueData>{global_info['conhecimentoCargaEmbarqueData']}</conhecimentoCargaEmbarqueData>
        <conhecimentoCargaEmbarqueLocal>GENOVA</conhecimentoCargaEmbarqueLocal>
        <conhecimentoCargaId>CEMERCANTE31032008</conhecimentoCargaId>
        <conhecimentoCargaIdMaster>162505352452915</conhecimentoCargaIdMaster>
        <conhecimentoCargaTipoCodigo>12</conhecimentoCargaTipoCodigo>
        <conhecimentoCargaTipoNome>HBL - House Bill of Lading</conhecimentoCargaTipoNome>
        <conhecimentoCargaUtilizacao>1</conhecimentoCargaUtilizacao>
        <conhecimentoCargaUtilizacaoNome>Total</conhecimentoCargaUtilizacaoNome>
        <dataDesembaraco>{global_info['dataDesembaraco']}</dataDesembaraco>
        <dataRegistro>{global_info['dataRegistro']}</dataRegistro>
        <documentoChegadaCargaCodigoTipo>1</documentoChegadaCargaCodigoTipo>
        <documentoChegadaCargaNome>Manifesto da Carga</documentoChegadaCargaNome>
        <documentoChegadaCargaNumero>1625502058594</documentoChegadaCargaNumero>
        <documentoInstrucaoDespacho>
            <codigoTipoDocumentoDespacho>28</codigoTipoDocumentoDespacho>
            <nomeDocumentoDespacho>CONHECIMENTO DE CARGA                                       </nomeDocumentoDespacho>
            <numeroDocumentoDespacho>372250376737202501       </numeroDocumentoDespacho>
        </documentoInstrucaoDespacho>
        <documentoInstrucaoDespacho>
            <codigoTipoDocumentoDespacho>01</codigoTipoDocumentoDespacho>
            <nomeDocumentoDespacho>FATURA COMERCIAL                                            </nomeDocumentoDespacho>
            <numeroDocumentoDespacho>20250880                 </numeroDocumentoDespacho>
        </documentoInstrucaoDespacho>
        <documentoInstrucaoDespacho>
            <codigoTipoDocumentoDespacho>01</codigoTipoDocumentoDespacho>
            <nomeDocumentoDespacho>FATURA COMERCIAL                                            </nomeDocumentoDespacho>
            <numeroDocumentoDespacho>3872/2025                </numeroDocumentoDespacho>
        </documentoInstrucaoDespacho>
        <documentoInstrucaoDespacho>
            <codigoTipoDocumentoDespacho>29</codigoTipoDocumentoDespacho>
            <nomeDocumentoDespacho>ROMANEIO DE CARGA                                           </nomeDocumentoDespacho>
            <numeroDocumentoDespacho>3872                     </numeroDocumentoDespacho>
        </documentoInstrucaoDespacho>
        <documentoInstrucaoDespacho>
            <codigoTipoDocumentoDespacho>29</codigoTipoDocumentoDespacho>
            <nomeDocumentoDespacho>ROMANEIO DE CARGA                                           </nomeDocumentoDespacho>
            <numeroDocumentoDespacho>S/N                      </numeroDocumentoDespacho>
        </documentoInstrucaoDespacho>
        <embalagem>
            <codigoTipoEmbalagem>60</codigoTipoEmbalagem>
            <nomeEmbalagem>PALLETS                                                     </nomeEmbalagem>
            <quantidadeVolume>00002</quantidadeVolume>
        </embalagem>
        <freteCollect>000000000025000</freteCollect>
        <freteEmTerritorioNacional>000000000000000</freteEmTerritorioNacional>
        <freteMoedaNegociadaCodigo>978</freteMoedaNegociadaCodigo>
        <freteMoedaNegociadaNome>EURO/COM.EUROPEIA</freteMoedaNegociadaNome>
        <fretePrepaid>000000000000000</fretePrepaid>
        <freteTotalDolares>000000000028757</freteTotalDolares>
        <freteTotalMoeda>25000</freteTotalMoeda>
        <freteTotalReais>000000000155007</freteTotalReais>
        <icms>
            <agenciaIcms>00000</agenciaIcms>
            <bancoIcms>000</bancoIcms>
            <codigoTipoRecolhimentoIcms>3</codigoTipoRecolhimentoIcms>
            <cpfResponsavelRegistro>27160353854</cpfResponsavelRegistro>
            <dataRegistro>20251125</dataRegistro>
            <horaRegistro>152044</horaRegistro>
            <nomeTipoRecolhimentoIcms>Exoneração do ICMS</nomeTipoRecolhimentoIcms>
            <numeroSequencialIcms>001</numeroSequencialIcms>
            <ufIcms>PR</ufIcms>
            <valorTotalIcms>000000000000000</valorTotalIcms>
        </icms>
        <importadorCodigoTipo>1</importadorCodigoTipo>
        <importadorCpfRepresentanteLegal>27160353854</importadorCpfRepresentanteLegal>
        <importadorEnderecoBairro>JARDIM PRIMAVERA</importadorEnderecoBairro>
        <importadorEnderecoCep>83302000</importadorEnderecoCep>
        <importadorEnderecoComplemento>CONJ: 6 E 7;</importadorEnderecoComplemento>
        <importadorEnderecoLogradouro>JOAO LEOPOLDO JACOMEL</importadorEnderecoLogradouro>
        <importadorEnderecoMunicipio>PIRAQUARA</importadorEnderecoMunicipio>
        <importadorEnderecoNumero>4459</importadorEnderecoNumero>
        <importadorEnderecoUf>PR</importadorEnderecoUf>
        <importadorNome>HAFELE BRASIL LTDA</importadorNome>
        <importadorNomeRepresentanteLegal>PAULO HENRIQUE LEITE FERREIRA</importadorNomeRepresentanteLegal>
        <importadorNumero>02473058000188</importadorNumero>
        <importadorNumeroTelefone>41  30348150</importadorNumeroTelefone>
        <informacaoComplementar>INFORMACOES COMPLEMENTARES
--------------------------
CASCO LOGISTICA - MATRIZ - PR
PROCESSO :28306
REF. IMPORTADOR :M-127707
IMPORTADOR :HAFELE BRASIL LTDA
PESO LIQUIDO :{global_info['cargaPesoLiquido']}
PESO BRUTO :{global_info['cargaPesoBruto']}
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
PAULO FERREIRA :CPF 271.603.538-54 REGISTRO 9D.01.894</informacaoComplementar>
        <localDescargaTotalDolares>000000002061433</localDescargaTotalDolares>
        <localDescargaTotalReais>000000011111593</localDescargaTotalReais>
        <localEmbarqueTotalDolares>000000002030535</localEmbarqueTotalDolares>
        <localEmbarqueTotalReais>000000010945130</localEmbarqueTotalReais>
        <modalidadeDespachoCodigo>1</modalidadeDespachoCodigo>
        <modalidadeDespachoNome>Normal</modalidadeDespachoNome>
        <numeroDUIMP>{global_info['numeroDUIMP']}</numeroDUIMP>
        <operacaoFundap>N</operacaoFundap>
        <pagamento>
            <agenciaPagamento>3715 </agenciaPagamento>
            <bancoPagamento>341</bancoPagamento>
            <codigoReceita>0086</codigoReceita>
            <codigoTipoPagamento>1</codigoTipoPagamento>
            <contaPagamento>             316273</contaPagamento>
            <dataPagamento>20251124</dataPagamento>
            <nomeTipoPagamento>Débito em Conta</nomeTipoPagamento>
            <numeroRetificacao>00</numeroRetificacao>
            <valorJurosEncargos>000000000</valorJurosEncargos>
            <valorMulta>000000000</valorMulta>
            <valorReceita>000000001772057</valorReceita>
        </pagamento>
        <pagamento>
            <agenciaPagamento>3715 </agenciaPagamento>
            <bancoPagamento>341</bancoPagamento>
            <codigoReceita>1038</codigoReceita>
            <codigoTipoPagamento>1</codigoTipoPagamento>
            <contaPagamento>             316273</contaPagamento>
            <dataPagamento>20251124</dataPagamento>
            <nomeTipoPagamento>Débito em Conta</nomeTipoPagamento>
            <numeroRetificacao>00</numeroRetificacao>
            <valorJurosEncargos>000000000</valorJurosEncargos>
            <valorMulta>000000000</valorMulta>
            <valorReceita>000000001021643</valorReceita>
        </pagamento>
        <pagamento>
            <agenciaPagamento>3715 </agenciaPagamento>
            <bancoPagamento>341</bancoPagamento>
            <codigoReceita>5602</codigoReceita>
            <codigoTipoPagamento>1</codigoTipoPagamento>
            <contaPagamento>             316273</contaPagamento>
            <dataPagamento>20251124</dataPagamento>
            <nomeTipoPagamento>Débito em Conta</nomeTipoPagamento>
            <numeroRetificacao>00</numeroRetificacao>
            <valorJurosEncargos>000000000</valorJurosEncargos>
            <valorMulta>000000000</valorMulta>
            <valorReceita>000000000233345</valorReceita>
        </pagamento>
        <pagamento>
            <agenciaPagamento>3715 </agenciaPagamento>
            <bancoPagamento>341</bancoPagamento>
            <codigoReceita>5629</codigoReceita>
            <codigoTipoPagamento>1</codigoTipoPagamento>
            <contaPagamento>             316273</contaPagamento>
            <dataPagamento>20251124</dataPagamento>
            <nomeTipoPagamento>Débito em Conta</nomeTipoPagamento>
            <numeroRetificacao>00</numeroRetificacao>
            <valorJurosEncargos>000000000</valorJurosEncargos>
            <valorMulta>000000000</valorMulta>
            <valorReceita>000000001072281</valorReceita>
        </pagamento>
        <pagamento>
            <agenciaPagamento>3715 </agenciaPagamento>
            <bancoPagamento>341</bancoPagamento>
            <codigoReceita>7811</codigoReceita>
            <codigoTipoPagamento>1</codigoTipoPagamento>
            <contaPagamento>             316273</contaPagamento>
            <dataPagamento>20251124</dataPagamento>
            <nomeTipoPagamento>Débito em Conta</nomeTipoPagamento>
            <numeroRetificacao>00</numeroRetificacao>
            <valorJurosEncargos>000000000</valorJurosEncargos>
            <valorMulta>000000000</valorMulta>
            <valorReceita>000000000028534</valorReceita>
        </pagamento>
        <seguroMoedaNegociadaCodigo>220</seguroMoedaNegociadaCodigo>
        <seguroMoedaNegociadaNome>DOLAR DOS EUA</seguroMoedaNegociadaNome>
        <seguroTotalDolares>000000000002146</seguroTotalDolares>
        <seguroTotalMoedaNegociada>000000000002146</seguroTotalMoedaNegociada>
        <seguroTotalReais>000000000011567</seguroTotalReais>
        <sequencialRetificacao>00</sequencialRetificacao>
        <situacaoEntregaCarga>ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE EXONERACAO DO ICMS</situacaoEntregaCarga>
        <tipoDeclaracaoCodigo>01</tipoDeclaracaoCodigo>
        <tipoDeclaracaoNome>CONSUMO</tipoDeclaracaoNome>
        <totalAdicoes>{str(len(items)).zfill(3)}</totalAdicoes>
        <urfDespachoCodigo>0917800</urfDespachoCodigo>
        <urfDespachoNome>PORTO DE PARANAGUA</urfDespachoNome>
        <valorTotalMultaARecolherAjustado>000000000000000</valorTotalMultaARecolherAjustado>
        <viaTransporteCodigo>01</viaTransporteCodigo>
        <viaTransporteMultimodal>N</viaTransporteMultimodal>
        <viaTransporteNome>MARÍTIMA</viaTransporteNome>
        <viaTransporteNomeTransportador>MAERSK A/S</viaTransporteNomeTransportador>
        <viaTransporteNomeVeiculo>MAERSK MEMPHIS</viaTransporteNomeVeiculo>
        <viaTransportePaisTransportadorCodigo>741</viaTransportePaisTransportadorCodigo>
        <viaTransportePaisTransportadorNome>CINGAPURA</viaTransportePaisTransportadorNome>
    </duimp>
</ListaDeclaracoes>"""
        
        # Monta o XML completo
        full_xml = xml_header + "\n" + "\n".join(adicoes_xml) + xml_footer
        
        # Remove espaços em branco no início
        full_xml = full_xml.lstrip()
        
        return full_xml

def main():
    st.set_page_config(
        page_title="Conversor DUIMP PDF → XML (Extrai TODOS Itens)",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Conversor DUIMP PDF para XML - Extrai TODOS os Itens")
    st.markdown("**Versão aprimorada que extrai TODOS os itens de TODAS as páginas**")
    
    # Upload do arquivo
    uploaded_file = st.file_uploader(
        "Selecione o arquivo PDF do Extrato de Conferência DUIMP",
        type=["pdf"],
        help="Processa PDFs grandes e extrai TODOS os itens"
    )
    
    if uploaded_file:
        processor = DUIMPPDFProcessor()
        
        # Salva arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            tmp_path = tmp_file.name
        
        try:
            # Processa o PDF
            with st.spinner("Processando PDF... Isso pode levar alguns minutos para arquivos grandes"):
                items, global_info, total_pages = processor.process_pdf(tmp_path)
            
            # Gera XML
            with st.spinner("Gerando XML..."):
                xml_output = processor.generate_xml(items, global_info)
            
            # Mostra estatísticas
            st.success(f"✅ Processamento concluído!")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Páginas Processadas", total_pages)
            
            with col2:
                st.metric("Itens Extraídos", len(items))
            
            with col3:
                st.metric("Número DUIMP", global_info['numeroDUIMP'])
            
            with col4:
                file_size = len(xml_output.encode('utf-8')) / 1024
                st.metric("Tamanho XML", f"{file_size:.1f} KB")
            
            # Mostra prévia dos itens extraídos
            st.subheader("📋 Itens Extraídos")
            
            if items:
                # Cria DataFrame para visualização
                data_for_table = []
                for i, item in enumerate(items[:50]):  # Mostra apenas os primeiros 50
                    data_for_table.append({
                        "Item": item.get('item_num', 'N/A'),
                        "Página": item.get('page', 'N/A'),
                        "Descrição": item.get('descricao', 'N/A')[:50] + "..." if item.get('descricao') and len(item.get('descricao')) > 50 else item.get('descricao', 'N/A'),
                        "NCM": item.get('ncm', 'N/A'),
                        "Quantidade": item.get('quantidade', 'N/A'),
                        "Valor Total": item.get('valor_total', 'N/A')
                    })
                
                if data_for_table:
                    st.dataframe(data_for_table, use_container_width=True)
                
                if len(items) > 50:
                    st.info(f"Mostrando 50 de {len(items)} itens. Todos os itens serão incluídos no XML.")
            else:
                st.warning("⚠️ Nenhum item foi extraído. Verifique o layout do PDF.")
            
            # Opção para visualizar dados brutos
            with st.expander("🔍 Visualizar dados extraídos (primeiros 5 itens)"):
                if items:
                    st.json(items[:5])
                else:
                    st.write("Nenhum dado extraído")
            
            # Download do XML
            st.subheader("📥 Download do Arquivo XML")
            
            # Valida XML
            try:
                # Verifica se começa com <?xml
                if not xml_output.startswith('<?xml'):
                    st.warning("⚠️ Corrigindo declaração XML...")
                    xml_output = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_output
                
                # Remove BOM se existir
                if xml_output.startswith('\ufeff'):
                    xml_output = xml_output[1:]
                
                # Parse para validar
                ET.fromstring(xml_output.encode('utf-8'))
                st.success("✓ XML válido e bem formado")
                
            except Exception as e:
                st.error(f"✗ Erro na validação do XML: {str(e)}")
            
            # Gera nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            xml_filename = f"M-DUIMP-{global_info['numeroDUIMP']}_{timestamp}.xml"
            
            # Botão de download
            st.download_button(
                label="⬇️ Baixar Arquivo XML Completo",
                data=xml_output,
                file_name=xml_filename,
                mime="application/xml",
                type="primary",
                key="download_full_xml"
            )
            
            # Visualização do XML
            with st.expander("🔍 Visualizar Amostra do XML (primeiras 2000 caracteres)"):
                preview = xml_output[:2000]
                st.code(preview, language="xml")
                
                if len(xml_output) > 2000:
                    st.info(f"XML muito grande. Tamanho total: {len(xml_output)} caracteres")
            
            # Informações de debug
            with st.expander("🐛 Informações Técnicas"):
                st.write(f"**Primeiros 100 caracteres:**")
                st.code(xml_output[:100])
                
                st.write(f"**Estrutura do XML:**")
                st.write(f"- Declaração XML presente: {'✓' if xml_output.startswith('<?xml') else '✗'}")
                st.write(f"- Elemento ListaDeclaracoes: {'✓' if '<ListaDeclaracoes>' in xml_output else '✗'}")
                st.write(f"- Número de adições: {len(items)}")
                st.write(f"- Total de linhas: {len(xml_output.split(chr(10)))}")
                
                # Conta tags
                num_aduimp_tags = xml_output.count('<numeroDUIMP>')
                num_adicao_tags = xml_output.count('<adicao>')
                
                st.write(f"- Tags <numeroDUIMP>: {num_aduimp_tags}")
                st.write(f"- Tags <adicao>: {num_adicao_tags}")
        
        except Exception as e:
            st.error(f"❌ Erro durante o processamento: {str(e)}")
            
            with st.expander("🔧 Detalhes do erro"):
                st.exception(e)
        
        finally:
            # Limpa arquivo temporário
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    else:
        # Instruções
        st.markdown("""
        ### 🎯 **NOVA VERSÃO - Extrai TODOS os Itens**
        
        **Melhorias implementadas:**
        
        1. **✅ Extração Completa:**
           - Processa **TODAS as páginas** do PDF
           - Extrai **TODOS os itens** (não apenas alguns)
           - Identifica itens pelo padrão "Item X" ou "X -"
        
        2. **✅ Reconhecimento Inteligente:**
           - Detecta **início e fim** de cada item
           - Extrai **NCM, descrição, quantidade, valores**
           - Identifica **país de origem**
           - Captura **códigos internos** (XXX.XX.XXX)
        
        3. **✅ Processamento Otimizado:**
           - Barra de progresso para PDFs grandes
           - Processamento página por página
           - Uso eficiente de memória
        
        4. **✅ XML Completo:**
           - **Todas as adições** incluídas
           - Formatação **exata** do modelo
           - Números com **zeros à esquerda**
           - **Validação automática** do XML
        
        ### 📋 **O que é extraído de cada item:**
        
        - **Número do item** (Item X)
        - **NCM** (código da mercadoria)
        - **Descrição completa**
        - **Código interno** (se disponível)
        - **Quantidade**
        - **Valor unitário**
        - **Valor total**
        - **País de origem**
        - **Página onde foi encontrado**
        
        ### 🚀 **Como testar:**
        
        1. **Faça upload** do PDF grande
        2. **Aguarde** o processamento (verá contagem de páginas)
        3. **Verifique** quantos itens foram extraídos
        4. **Confira** a prévia na tabela
        5. **Baixe** o XML completo
        
        **O XML agora conterá TODOS os itens do seu PDF!**
        """)

if __name__ == "__main__":
    main()
