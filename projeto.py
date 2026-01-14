import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pdfplumber
import re
import json
from datetime import datetime
import pytz
import tempfile
import os
from typing import Dict, List, Any, Optional
import base64

class DUIMPConverter:
    """Classe para converter PDF de DUIMP para XML estruturado"""
    
    def __init__(self):
        self.namespaces = {
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:noNamespaceSchemaLocation': 'schema_duimp.xsd'
        }
        
        # Mapeamento de países para códigos
        self.paises_codigos = {
            "CHINA, REPUBLICA POPULAR": "156",
            "ALEMANHA": "276",
            "ITALIA": "386",
            "CINGAPURA": "741",
            "MARSHALL,ILHAS": "584"
        }
        
        # Mapeamento de moedas para códigos
        self.moedas_codigos = {
            "DOLAR DOS EUA": "220",
            "EURO/COM.EUROPEIA": "978"
        }
        
        # Layout fixo do PDF (baseado na estrutura fornecida)
        self.layout_campos = {
            "identificacao": {
                "numero": "25BR00001916620",
                "data_cadastro": "13/10/2025",
                "versao": "0",
                "canal": "PROPRIA",
                "tipo": "CONSUMO",
                "responsavel": "PAULO HENRIQUE LEITE FERREIRA",
                "ref_importador": "TESTE DUIMP"
            },
            "moedas": {
                "moeda_negociada": "220 - DOLAR DOS EUA",
                "cotacao_moeda": "5,3843000",
                "data_cotacao": "01/11/2025"
            },
            "importador": {
                "nome": "HAFELE BRASIL LTDA",
                "cnpj": "02.473.058/0001-88"
            }
        }
    
    def extrair_texto_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extrai texto do PDF com layout fixo"""
        dados = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Processar todas as páginas
                texto_completo = ""
                for pagina in pdf.pages:
                    texto_pagina = pagina.extract_text()
                    if texto_pagina:
                        texto_completo += texto_pagina + "\n"
                
                # Extrair dados usando regex baseado no layout conhecido
                dados = self._parse_texto_fixo(texto_completo)
                
                return dados
                
        except Exception as e:
            st.error(f"Erro ao processar PDF: {str(e)}")
            return {}
    
    def _parse_texto_fixo(self, texto: str) -> Dict[str, Any]:
        """Parse do texto do PDF com layout fixo"""
        dados = {}
        
        try:
            # Extrair informações básicas
            dados["processo"] = self._extrair_regex(texto, r"PROCESSO #(\d+)")
            dados["importador_nome"] = self._extrair_regex(texto, r"\*\*IMPORTADOR\*\* (.+?)\n")
            dados["importador_cnpj"] = self._extrair_regex(texto, r"\*\*CNPJ\*\* (.+?)\n")
            
            # Extrair identificação
            dados["identificacao_numero"] = self._extrair_regex(texto, r"Numero(.+?)Versao")
            dados["data_cadastro"] = self._extrair_regex(texto, r"Data de Cadastro(.+?)Numero")
            dados["versao"] = self._extrair_regex(texto, r"Versao(.+?)Data Registro")
            
            # Moedas
            dados["moeda_negociada"] = self._extrair_regex(texto, r"Moeda Negociada(.+?)Cotacao")
            dados["cotacao_moeda"] = self._extrair_regex(texto, r"Cotacao (.+?)\n")
            
            # Resumo
            dados["numero_adicao"] = self._extrair_regex(texto, r"N° Adição(.+?)\n")
            dados["numero_item"] = self._extrair_regex(texto, r"N° do Item(.+?)\n")
            
            # Valores CIF
            cif_usd = self._extrair_regex(texto, r"CIF \(US\$\)(.+?)\n")
            cif_brl = self._extrair_regex(texto, r"CIF \(R\$\)(.+?)\n")
            dados["cif_usd"] = self._formatar_valor(cif_usd)
            dados["cif_brl"] = self._formatar_valor(cif_brl)
            
            # VMLE
            vmle_usd = self._extrair_regex(texto, r"VMLE \(US\$\)(.+?)\n")
            vmle_brl = self._extrair_regex(texto, r"VMLE \(R\$\)(.+?)\n")
            dados["vmle_usd"] = self._formatar_valor(vmle_usd)
            dados["vmle_brl"] = self._formatar_valor(vmle_brl)
            
            # VMLD
            vmld_usd = self._extrair_regex(texto, r"VMLD \(US\$\)(.+?)\n")
            vmld_brl = self._extrair_regex(texto, r"VMLD \(R\$\)(.+?)\n")
            dados["vmld_usd"] = self._formatar_valor(vmld_usd)
            dados["vmld_brl"] = self._formatar_valor(vmld_brl)
            
            # Tributos
            dados["ii_calculado"] = self._extrair_valor_tabela(texto, "II", "Calculado")
            dados["ii_devido"] = self._extrair_valor_tabela(texto, "II", "Devido")
            dados["ii_recolher"] = self._extrair_valor_tabela(texto, "II", "A Recolher")
            
            dados["ipi_calculado"] = self._extrair_valor_tabela(texto, "IPI", "Calculado")
            dados["ipi_devido"] = self._extrair_valor_tabela(texto, "IPI", "Devido")
            
            dados["pis_calculado"] = self._extrair_valor_tabela(texto, "PIS", "Calculado")
            dados["pis_devido"] = self._extrair_valor_tabela(texto, "PIS", "Devido")
            dados["pis_recolher"] = self._extrair_valor_tabela(texto, "PIS", "A Recolher")
            
            dados["cofins_calculado"] = self._extrair_valor_tabela(texto, "COFINS", "Calculado")
            dados["cofins_devido"] = self._extrair_valor_tabela(texto, "COFINS", "Devido")
            dados["cofins_recolher"] = self._extrair_valor_tabela(texto, "COFINS", "A Recolher")
            
            dados["taxa_utilizacao"] = self._extrair_valor_tabela(texto, "TAXA DE UTILIZACAO", "A Recolher")
            
            # Dados da Carga
            dados["via_transporte"] = self._extrair_regex(texto, r"Via de Transporte(.+?)\n")
            dados["num_identificacao"] = self._extrair_regex(texto, r"Num. Identificacao(.+?)Data de Embarque")
            dados["data_embarque"] = self._extrair_regex(texto, r"Data de Embarque(.+?)\n")
            dados["data_chegada"] = self._extrair_regex(texto, r"Data de Chegada(.+?)\n")
            
            peso_bruto = self._extrair_regex(texto, r"Peso Bruto(.+?)\n")
            peso_liquido = self._extrair_regex(texto, r"Peso Liquido(.+?)\n")
            dados["peso_bruto"] = self._formatar_valor(peso_bruto)
            dados["peso_liquido"] = self._formatar_valor(peso_liquido)
            
            dados["pais_procedencia"] = self._extrair_regex(texto, r"Pais de Procedencia(.+?)\n")
            dados["unidade_despacho"] = self._extrair_regex(texto, r"Unidade de Despacho(.+?)\n")
            
            # Transporte
            dados["tipo_conhecimento"] = self._extrair_regex(texto, r"Tipo Conhecimento(.+?)Bandeira Embarcacao")
            dados["bandeira_embarcacao"] = self._extrair_regex(texto, r"Bandeira Embarcacao(.+?)Local Embarque")
            dados["local_embarque"] = self._extrair_regex(texto, r"Local Embarque(.+?)\n")
            
            # Seguro
            seguro_moeda = self._extrair_regex(texto, r"Total \(Moeda\)(.+?)\n")
            seguro_brl = self._extrair_regex(texto, r"Total \(R\$\)(.+?)\n")
            dados["seguro_moeda"] = self._formatar_valor(seguro_moeda)
            dados["seguro_brl"] = self._formatar_valor(seguro_brl)
            dados["moeda_seguro"] = self._extrair_regex(texto, r"Moeda(.+?)\n")
            
            # Frete
            frete_moeda = self._extrair_regex(texto, r"Total \(Moeda\)(.+?)Total \(US\$\)")
            frete_usd = self._extrair_regex(texto, r"Total \(US\$\)(.+?)Total \(R\$\)")
            frete_brl = self._extrair_regex(texto, r"Total \(R\$\)(.+?)Afrmm/Tum Quit/Exon")
            dados["frete_moeda"] = self._formatar_valor(frete_moeda)
            dados["frete_usd"] = self._formatar_valor(frete_usd)
            dados["frete_brl"] = self._formatar_valor(frete_brl)
            
            # Componentes do Frete (simplificado para este exemplo)
            # Em produção, seria necessário parse mais detalhado
            
            # Embalagem
            dados["tipo_embalagem"] = self._extrair_regex(texto, r"Tipo(.+?)Quantidade")
            dados["quantidade_embalagem"] = self._extrair_regex(texto, r"Quantidade(.+?)Peso Bruto KG")
            
            # Documentos
            dados["conhecimento_numero"] = self._extrair_regex(texto, r"CONHECIMENTO DE EMBARQUE(.+?)NUMEROS")
            dados["fatura_numero"] = self._extrair_regex(texto, r"FATURA COMERCIAL(.+?)NUMERO")
            
            # Itens
            dados["ncm"] = self._extrair_regex(texto, r"NCM(.+?)Codigo Produto")
            dados["codigo_produto"] = self._extrair_regex(texto, r"Codigo Produto(.+?)Versao")
            
            # Produto
            produto_match = re.search(r"DENOMINACAO DO PRODUTO\n(.+?)\n##", texto, re.DOTALL)
            if produto_match:
                dados["denominacao_produto"] = produto_match.group(1).strip()
            
            descricao_match = re.search(r"DESCRICAO DO PRODUTO\n(.+?)\n##", texto, re.DOTALL)
            if descricao_match:
                dados["descricao_produto"] = descricao_match.group(1).strip()
            
            # Código interno
            codigo_match = re.search(r"Código interno(.+?)\n", texto)
            if codigo_match:
                dados["codigo_interno"] = codigo_match.group(1).strip()
            
            # Fabricante
            fabricante_match = re.search(r"FABRICANTE/PRODUTOR\n(.+?)Conhecido", texto, re.DOTALL)
            if fabricante_match:
                dados["fabricante_info"] = fabricante_match.group(1).strip()
            
            dados["conhecido"] = self._extrair_regex(texto, r"Conhecido(.+?)Pais Origem")
            dados["pais_origem"] = self._extrair_regex(texto, r"Pais Origem(.+?)\n")
            
            # Caracterização da importação
            dados["caracterizacao_importacao"] = self._extrair_regex(texto, r"Importação(.+?)\n")
            
            # Dados do exportador
            relacao_match = re.search(r"RELAÇÃO EXPORTADOR E FABRIC./PRODUTOR\n(.+?)\n", texto)
            if relacao_match:
                dados["relacao_exportador"] = relacao_match.group(1).strip()
            
            exportador_match = re.search(r"EXPORTADOR ESTRANGEIRO\n(.+?)VINCULAÇÃO", texto, re.DOTALL)
            if exportador_match:
                dados["exportador_estrangeiro"] = exportador_match.group(1).strip()
            
            vinculo_match = re.search(r"VINCULAÇÃO ENTRE COMPRADOR/VENDEDOR\n(.+?)\n", texto)
            if vinculo_match:
                dados["vinculo_comprador_vendedor"] = vinculo_match.group(1).strip()
            
            # Dados da mercadoria
            dados["aplicacao"] = self._extrair_regex(texto, r"Aplicação(.+?)\n")
            dados["condicao_mercadoria"] = self._extrair_regex(texto, r"Condição Mercadoria(.+?)\n")
            
            qtd_estatistica = self._extrair_regex(texto, r"Qtde Unid. Estatística(.+?)\n")
            dados["qtd_estatistica"] = self._formatar_valor(qtd_estatistica)
            
            dados["unidade_estatistica"] = self._extrair_regex(texto, r"Unidad Estatística(.+?)\n")
            
            qtd_comercial = self._extrair_regex(texto, r"Qtde Unid. Comercial(.+?)\n")
            dados["qtd_comercial"] = self._formatar_valor(qtd_comercial)
            
            dados["unidade_comercial"] = self._extrair_regex(texto, r"Unidade Comercial(.+?)\n")
            
            peso_liquido_kg = self._extrair_regex(texto, r"Peso Líquido \(KG\)(.+?)\n")
            dados["peso_liquido_kg"] = self._formatar_valor(peso_liquido_kg)
            
            dados["moeda_negociada_merc"] = self._extrair_regex(texto, r"Moeda Negociada(.+?)Valor Unit Cond Venda")
            
            valor_unit = self._extrair_regex(texto, r"Valor Unit Cond Venda(.+?)\n")
            dados["valor_unit_cond_venda"] = self._formatar_valor(valor_unit)
            
            valor_total = self._extrair_regex(texto, r"Valor Tot. Cond Venda(.+?)\n")
            dados["valor_total_cond_venda"] = self._formatar_valor(valor_total)
            
            # Condição de venda
            dados["metodo_valoracao"] = self._extrair_regex(texto, r"Método de Valoração(.+?)\n")
            dados["condicao_venda"] = self._extrair_regex(texto, r"Condição de Venda(.+?)\n")
            
            vir_cond_moeda = self._extrair_regex(texto, r"Vir Cond Venda \(Moeda(.+?)\n")
            vir_cond_brl = self._extrair_regex(texto, r"Vir Cond Venda \(R\$\)(.+?)\n")
            dados["vir_cond_moeda"] = self._formatar_valor(vir_cond_moeda)
            dados["vir_cond_brl"] = self._formatar_valor(vir_cond_brl)
            
            frete_internac = self._extrair_regex(texto, r"Frete Internac. \(R\$\)(.+?)\n")
            seguro_internac = self._extrair_regex(texto, r"Seguro Internac. \(R\$\)(.+?)\n")
            dados["frete_internac_brl"] = self._formatar_valor(frete_internac)
            dados["seguro_internac_brl"] = self._formatar_valor(seguro_internac)
            
            # Dados cambiais
            dados["cobertura_cambial"] = self._extrair_regex(texto, r"Cobertura Cambial(.+?)\n")
            
            # Informações complementares
            dados["nossa_referencia"] = self._extrair_regex(texto, r"NOSSA REFERENCIA(.+?)\n")
            dados["referencia_importador"] = self._extrair_regex(texto, r"REFERENCIA DO IMPORTADOR(.+?)\n")
            
            # Limpar e formatar dados
            dados = self._limpar_dados(dados)
            
            return dados
            
        except Exception as e:
            st.error(f"Erro ao parsear texto: {str(e)}")
            return {}
    
    def _extrair_regex(self, texto: str, padrao: str) -> str:
        """Extrai valor usando regex"""
        try:
            match = re.search(padrao, texto)
            return match.group(1).strip() if match else ""
        except:
            return ""
    
    def _extrair_valor_tabela(self, texto: str, tributo: str, coluna: str) -> str:
        """Extrai valor específico de tabela de tributos"""
        try:
            # Padrão para encontrar valores na tabela de tributos
            padrao = fr"{tributo}(.+?){coluna}"
            match = re.search(padrao, texto)
            if match:
                valor = match.group(1).strip()
                # Remover pontos extras
                valor = valor.replace(' ', '').replace('.', '')
                return valor
            return "0"
        except:
            return "0"
    
    def _formatar_valor(self, valor_str: str) -> str:
        """Formata valores numéricos"""
        if not valor_str:
            return "0"
        
        try:
            # Remover espaços e caracteres não numéricos (exceto vírgula e ponto)
            valor_str = valor_str.strip()
            valor_str = re.sub(r'[^\d,\.\-]', '', valor_str)
            
            # Converter vírgula para ponto se necessário
            if ',' in valor_str and '.' in valor_str:
                # Se ambos existem, assumir que vírgula é decimal
                valor_str = valor_str.replace('.', '').replace(',', '.')
            elif ',' in valor_str:
                # Se só tem vírgula, pode ser decimal
                valor_str = valor_str.replace(',', '.')
            
            # Converter para float e depois formatar sem decimais
            try:
                valor_float = float(valor_str)
                # Formatar como inteiro (sem decimais)
                return f"{valor_float:.0f}".replace('.', '')
            except:
                return "0"
                
        except Exception as e:
            st.warning(f"Erro ao formatar valor '{valor_str}': {str(e)}")
            return "0"
    
    def _limpar_dados(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Limpa e padroniza os dados extraídos"""
        dados_limpos = {}
        
        for chave, valor in dados.items():
            if isinstance(valor, str):
                # Remover múltiplos espaços e quebras de linha extras
                valor = re.sub(r'\s+', ' ', valor.strip())
                # Remover caracteres especiais problemáticos
                valor = valor.replace('&#xD;', '').replace('\r', '').replace('\n', ' ')
            dados_limpos[chave] = valor
        
        return dados_limpos
    
    def _formatar_valor_xml(self, valor: str, tamanho: int = 15) -> str:
        """Formata valor para padrão XML (zeros à esquerda)"""
        try:
            # Remover caracteres não numéricos
            valor_limpo = re.sub(r'[^\d]', '', str(valor))
            
            # Se estiver vazio, retornar zeros
            if not valor_limpo:
                valor_limpo = "0"
            
            # Garantir que seja inteiro
            valor_int = int(float(valor_limpo))
            
            # Formatar com zeros à esquerda
            return str(valor_int).zfill(tamanho)
            
        except:
            return "0".zfill(tamanho)
    
    def _formatar_moeda(self, nome_moeda: str) -> tuple:
        """Retorna código e nome formatado da moeda"""
        for nome, codigo in self.moedas_codigos.items():
            if nome in nome_moeda.upper():
                return codigo, nome
        return "220", "DOLAR DOS EUA"  # Padrão
    
    def _formatar_pais(self, nome_pais: str) -> tuple:
        """Retorna código e nome formatado do país"""
        for nome, codigo in self.paises_codigos.items():
            if nome in nome_pais.upper():
                return codigo, nome
        return "000", nome_pais  # Padrão
    
    def _formatar_data(self, data_str: str) -> str:
        """Formata data para AAAAMMDD"""
        try:
            # Tentar diferentes formatos
            formatos = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"]
            
            for formato in formatos:
                try:
                    data_obj = datetime.strptime(data_str.strip(), formato)
                    return data_obj.strftime("%Y%m%d")
                except:
                    continue
            
            # Se não conseguir parse, usar data atual
            return datetime.now().strftime("%Y%m%d")
            
        except:
            return datetime.now().strftime("%Y%m%d")
    
    def criar_xml(self, dados: Dict[str, Any]) -> str:
        """Cria XML estruturado a partir dos dados extraídos"""
        
        try:
            # Criar elemento raiz
            lista_declaracoes = ET.Element("ListaDeclaracoes")
            duimp = ET.SubElement(lista_declaracoes, "duimp")
            
            # ===== SEÇÃO 1: ADIÇÕES =====
            adicao = ET.SubElement(duimp, "adicao")
            
            # Numeração
            ET.SubElement(adicao, "numeroAdicao").text = dados.get("numero_adicao", "001").zfill(3)
            ET.SubElement(adicao, "numeroDUIMP").text = dados.get("identificacao_numero", "25BR00001916620")
            ET.SubElement(adicao, "numeroLI").text = "0000000000"
            ET.SubElement(adicao, "sequencialRetificacao").text = "00"
            
            # Condição de Venda
            ET.SubElement(adicao, "condicaoVendaIncoterm").text = dados.get("condicao_venda", "FOB").split()[0]
            ET.SubElement(adicao, "condicaoVendaLocal").text = dados.get("local_embarque", "CNYTN")
            ET.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
            ET.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = dados.get("metodo_valoracao", "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)")
            
            cod_moeda, nome_moeda = self._formatar_moeda(dados.get("moeda_negociada_merc", "DOLAR DOS EUA"))
            ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = cod_moeda
            ET.SubElement(adicao, "condicaoVendaMoedaNome").text = nome_moeda
            
            ET.SubElement(adicao, "condicaoVendaValorMoeda").text = self._formatar_valor_xml(dados.get("vir_cond_moeda", "0"))
            ET.SubElement(adicao, "condicaoVendaValorReais").text = self._formatar_valor_xml(dados.get("vir_cond_brl", "0"))
            ET.SubElement(adicao, "valorTotalCondicaoVenda").text = self._formatar_valor_xml(dados.get("valor_total_cond_venda", "0"), 11)
            
            # Dados Cambiais
            ET.SubElement(adicao, "dadosCambiaisCoberturaCambialCodigo").text = "1"
            ET.SubElement(adicao, "dadosCambiaisCoberturaCambialNome").text = dados.get("cobertura_cambial", "ATÉ 180 DIAS")
            ET.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraCodigo").text = "00"
            ET.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraNome").text = "N/I"
            ET.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaCodigo").text = "00"
            ET.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaNome").text = "N/I"
            ET.SubElement(adicao, "dadosCambiaisValorRealCambio").text = "000000000000000"
            
            # Dados da Carga
            ET.SubElement(adicao, "dadosCargaViaTransporteCodigo").text = "01"
            ET.SubElement(adicao, "dadosCargaViaTransporteNome").text = "MARÍTIMA"
            ET.SubElement(adicao, "dadosCargaPaisProcedenciaCodigo").text = "000"
            ET.SubElement(adicao, "dadosCargaUrfEntradaCodigo").text = "0000000"
            
            # Dados da Mercadoria
            ET.SubElement(adicao, "dadosMercadoriaAplicacao").text = dados.get("aplicacao", "REVENDA")
            ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = dados.get("ncm", "83021000").replace(".", "")
            ET.SubElement(adicao, "dadosMercadoriaNomeNcm").text = dados.get("denominacao_produto", "DOBRADICA INVISIVEL EM LIGA DE ZINCO")
            ET.SubElement(adicao, "dadosMercadoriaCondicao").text = dados.get("condicao_mercadoria", "NOVA")
            
            ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaQuantidade").text = self._formatar_valor_xml(dados.get("qtd_estatistica", "0"))
            ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaUnidade").text = dados.get("unidade_estatistica", "QUILOGRAMA LIQUIDO")
            ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = self._formatar_valor_xml(dados.get("peso_liquido_kg", "0"))
            
            # Relação Comprador/Vendedor
            ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
            ET.SubElement(adicao, "relacaoCompradorVendedor").text = dados.get("relacao_exportador", "EXPORTADOR NAO EH O FABRICANTE DO PRODUTO")
            ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
            ET.SubElement(adicao, "vinculoCompradorVendedor").text = dados.get("vinculo_comprador_vendedor", "VINCULAÇÃO SEM INFLUENCIA NO PRECO")
            
            # Fornecedor
            ET.SubElement(adicao, "fornecedorNome").text = dados.get("exportador_estrangeiro", "HAFELE ENGINEERING ASIA LTD.")
            ET.SubElement(adicao, "fornecedorCidade").text = "N/I"
            ET.SubElement(adicao, "fornecedorLogradouro").text = "N/I"
            ET.SubElement(adicao, "fornecedorNumero").text = "0"
            
            # Países
            cod_pais_aquisicao, nome_pais_aquisicao = self._formatar_pais(dados.get("pais_procedencia", "CHINA"))
            ET.SubElement(adicao, "paisAquisicaoMercadoriaCodigo").text = cod_pais_aquisicao
            ET.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = nome_pais_aquisicao
            
            cod_pais_origem, nome_pais_origem = self._formatar_pais(dados.get("pais_origem", "ALEMANHA"))
            ET.SubElement(adicao, "paisOrigemMercadoriaCodigo").text = cod_pais_origem
            ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = nome_pais_origem
            
            # Frete
            cod_moeda_frete, nome_moeda_frete = self._formatar_moeda(dados.get("moeda_negociada", "DOLAR DOS EUA"))
            ET.SubElement(adicao, "freteMoedaNegociadaCodigo").text = cod_moeda_frete
            ET.SubElement(adicao, "freteMoedaNegociadaNome").text = nome_moeda_frete
            ET.SubElement(adicao, "freteValorMoedaNegociada").text = self._formatar_valor_xml(dados.get("frete_moeda", "0"))
            ET.SubElement(adicao, "freteValorReais").text = self._formatar_valor_xml(dados.get("frete_brl", "0"))
            ET.SubElement(adicao, "valorReaisFreteInternacional").text = self._formatar_valor_xml(dados.get("frete_internac_brl", "0"))
            
            # Seguro
            cod_moeda_seguro, nome_moeda_seguro = self._formatar_moeda(dados.get("moeda_seguro", "DOLAR DOS EUA"))
            ET.SubElement(adicao, "seguroMoedaNegociadaCodigo").text = cod_moeda_seguro
            ET.SubElement(adicao, "seguroMoedaNegociadaNome").text = nome_moeda_seguro
            ET.SubElement(adicao, "seguroValorMoedaNegociada").text = self._formatar_valor_xml(dados.get("seguro_moeda", "0"))
            ET.SubElement(adicao, "seguroValorReais").text = self._formatar_valor_xml(dados.get("seguro_brl", "0"))
            ET.SubElement(adicao, "valorReaisSeguroInternacional").text = self._formatar_valor_xml(dados.get("seguro_internac_brl", "0"))
            
            # II - Imposto de Importação
            ET.SubElement(adicao, "iiAcordoTarifarioTipoCodigo").text = "0"
            ET.SubElement(adicao, "iiAliquotaAcordo").text = "00000"
            ET.SubElement(adicao, "iiAliquotaAdValorem").text = "00000"
            ET.SubElement(adicao, "iiAliquotaPercentualReducao").text = "00000"
            ET.SubElement(adicao, "iiAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "iiAliquotaValorCalculado").text = self._formatar_valor_xml(dados.get("ii_calculado", "0"))
            ET.SubElement(adicao, "iiAliquotaValorDevido").text = self._formatar_valor_xml(dados.get("ii_devido", "0"))
            ET.SubElement(adicao, "iiAliquotaValorRecolher").text = self._formatar_valor_xml(dados.get("ii_recolher", "0"))
            ET.SubElement(adicao, "iiAliquotaValorReduzido").text = "000000000000000"
            ET.SubElement(adicao, "iiBaseCalculo").text = self._formatar_valor_xml(dados.get("cif_brl", "0"))
            ET.SubElement(adicao, "iiFundamentoLegalCodigo").text = "00"
            ET.SubElement(adicao, "iiMotivoAdmissaoTemporariaCodigo").text = "00"
            ET.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
            ET.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
            
            # IPI
            ET.SubElement(adicao, "ipiAliquotaAdValorem").text = "00000"
            ET.SubElement(adicao, "ipiAliquotaEspecificaCapacidadeRecipciente").text = "00000"
            ET.SubElement(adicao, "ipiAliquotaEspecificaQuantidadeUnidadeMedida").text = "000000000"
            ET.SubElement(adicao, "ipiAliquotaEspecificaTipoRecipienteCodigo").text = "00"
            ET.SubElement(adicao, "ipiAliquotaEspecificaValorUnidadeMedida").text = "0000000000"
            ET.SubElement(adicao, "ipiAliquotaNotaComplementarTIPI").text = "00"
            ET.SubElement(adicao, "ipiAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "ipiAliquotaValorDevido").text = self._formatar_valor_xml(dados.get("ipi_devido", "0"))
            ET.SubElement(adicao, "ipiAliquotaValorRecolher").text = self._formatar_valor_xml(dados.get("ipi_devido", "0"))
            ET.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "4"
            ET.SubElement(adicao, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"
            
            # PIS/PASEP
            ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00000"
            ET.SubElement(adicao, "pisPasepAliquotaEspecificaQuantidadeUnidade").text = "000000000"
            ET.SubElement(adicao, "pisPasepAliquotaEspecificaValor").text = "0000000000"
            ET.SubElement(adicao, "pisPasepAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "pisPasepAliquotaValorDevido").text = self._formatar_valor_xml(dados.get("pis_devido", "0"))
            ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = self._formatar_valor_xml(dados.get("pis_recolher", "0"))
            
            # COFINS
            ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00000"
            ET.SubElement(adicao, "cofinsAliquotaEspecificaQuantidadeUnidade").text = "000000000"
            ET.SubElement(adicao, "cofinsAliquotaEspecificaValor").text = "0000000000"
            ET.SubElement(adicao, "cofinsAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "cofinsAliquotaValorDevido").text = self._formatar_valor_xml(dados.get("cofins_devido", "0"))
            ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = self._formatar_valor_xml(dados.get("cofins_recolher", "0"))
            
            # ICMS
            ET.SubElement(adicao, "icmsBaseCalculoValor").text = "000000000000000"
            ET.SubElement(adicao, "icmsBaseCalculoAliquota").text = "00000"
            ET.SubElement(adicao, "icmsBaseCalculoValorImposto").text = "000000000000000"
            ET.SubElement(adicao, "icmsBaseCalculoValorDiferido").text = "000000000000000"
            
            # CBS/IBS
            ET.SubElement(adicao, "cbsIbsCst").text = "000"
            ET.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
            ET.SubElement(adicao, "cbsBaseCalculoValor").text = "000000000000000"
            ET.SubElement(adicao, "cbsBaseCalculoAliquota").text = "00090"
            ET.SubElement(adicao, "cbsBaseCalculoAliquotaReducao").text = "00000"
            ET.SubElement(adicao, "cbsBaseCalculoValorImposto").text = "000000000000000"
            
            ET.SubElement(adicao, "ibsBaseCalculoValor").text = "000000000000000"
            ET.SubElement(adicao, "ibsBaseCalculoAliquota").text = "00010"
            ET.SubElement(adicao, "ibsBaseCalculoAliquotaReducao").text = "00000"
            ET.SubElement(adicao, "ibsBaseCalculoValorImposto").text = "000000000000000"
            
            # Outros campos adicao
            ET.SubElement(adicao, "pisCofinsRegimeTributacaoCodigo").text = "1"
            ET.SubElement(adicao, "pisCofinsRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
            ET.SubElement(adicao, "pisCofinsBaseCalculoAliquotaICMS").text = "00000"
            ET.SubElement(adicao, "pisCofinsBaseCalculoFundamentoLegalCodigo").text = "00"
            ET.SubElement(adicao, "pisCofinsBaseCalculoPercentualReducao").text = "00000"
            ET.SubElement(adicao, "pisCofinsBaseCalculoValor").text = self._formatar_valor_xml(dados.get("cif_brl", "0"))
            ET.SubElement(adicao, "pisCofinsFundamentoLegalReducaoCodigo").text = "00"
            
            ET.SubElement(adicao, "acrescimo").text = ""
            acr = ET.SubElement(adicao, "acrescimo")
            ET.SubElement(acr, "codigoAcrescimo").text = "17"
            ET.SubElement(acr, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO                        "
            ET.SubElement(acr, "moedaNegociadaCodigo").text = cod_moeda
            ET.SubElement(acr, "moedaNegociadaNome").text = nome_moeda
            ET.SubElement(acr, "valorMoedaNegociada").text = "000000000000000"
            ET.SubElement(acr, "valorReais").text = "000000000000000"
            
            ET.SubElement(adicao, "cideValorAliquotaEspecifica").text = "00000000000"
            ET.SubElement(adicao, "cideValorDevido").text = "000000000000000"
            ET.SubElement(adicao, "cideValorRecolher").text = "000000000000000"
            
            ET.SubElement(adicao, "dcrCoeficienteReducao").text = "00000"
            ET.SubElement(adicao, "dcrIdentificacao").text = "00000000"
            ET.SubElement(adicao, "dcrValorDevido").text = "000000000000000"
            ET.SubElement(adicao, "dcrValorDolar").text = "000000000000000"
            ET.SubElement(adicao, "dcrValorReal").text = "000000000000000"
            ET.SubElement(adicao, "dcrValorRecolher").text = "000000000000000"
            
            ET.SubElement(adicao, "valorMultaARecolher").text = "000000000000000"
            ET.SubElement(adicao, "valorMultaARecolherAjustado").text = "000000000000000"
            
            # Mercadoria
            mercadoria = ET.SubElement(adicao, "mercadoria")
            ET.SubElement(mercadoria, "descricaoMercadoria").text = dados.get("descricao_produto", "DOBRADICA INVISIVEL EM LIGA DE ZINCO")
            ET.SubElement(mercadoria, "numeroSequencialItem").text = dados.get("numero_item", "01").zfill(2)
            ET.SubElement(mercadoria, "quantidade").text = self._formatar_valor_xml(dados.get("qtd_comercial", "0"), 14)
            ET.SubElement(mercadoria, "unidadeMedida").text = dados.get("unidade_comercial", "PECA").ljust(20)
            ET.SubElement(mercadoria, "valorUnitario").text = self._formatar_valor_xml(dados.get("valor_unit_cond_venda", "0"), 20)
            
            # Nomenclatura (se houver no futuro)
            # ET.SubElement(adicao, "nomenclaturaValorAduaneiro")
            
            # ===== SEÇÃO 2: DADOS GERAIS DA DUIMP =====
            
            # Armazem
            armazem = ET.SubElement(duimp, "armazem")
            ET.SubElement(armazem, "nomeArmazem").text = "TCP       "
            
            ET.SubElement(duimp, "armazenamentoRecintoAduaneiroCodigo").text = "9801303"
            ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
            ET.SubElement(duimp, "armazenamentoSetor").text = "002"
            
            ET.SubElement(duimp, "canalSelecaoParametrizada").text = "001"
            ET.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
            ET.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importação Própria"
            
            # Carga
            ET.SubElement(duimp, "cargaDataChegada").text = self._formatar_data(dados.get("data_chegada", ""))
            ET.SubElement(duimp, "cargaNumeroAgente").text = "N/I"
            
            cod_pais_procedencia, nome_pais_procedencia = self._formatar_pais(dados.get("pais_procedencia", "CHINA"))
            ET.SubElement(duimp, "cargaPaisProcedenciaCodigo").text = cod_pais_procedencia
            ET.SubElement(duimp, "cargaPaisProcedenciaNome").text = nome_pais_procedencia
            
            ET.SubElement(duimp, "cargaPesoBruto").text = self._formatar_valor_xml(dados.get("peso_bruto", "0"))
            ET.SubElement(duimp, "cargaPesoLiquido").text = self._formatar_valor_xml(dados.get("peso_liquido", "0"))
            ET.SubElement(duimp, "cargaUrfEntradaCodigo").text = dados.get("unidade_despacho", "0917800").split()[0]
            ET.SubElement(duimp, "cargaUrfEntradaNome").text = dados.get("unidade_despacho", "PORTO DE PARANAGUA")
            
            # Conhecimento de Carga
            ET.SubElement(duimp, "conhecimentoCargaEmbarqueData").text = self._formatar_data(dados.get("data_embarque", ""))
            ET.SubElement(duimp, "conhecimentoCargaEmbarqueLocal").text = dados.get("local_embarque", "CNYTN")
            ET.SubElement(duimp, "conhecimentoCargaId").text = dados.get("conhecimento_numero", "SZXS069034").replace("S", "")
            ET.SubElement(duimp, "conhecimentoCargaIdMaster").text = "000000000000000"
            ET.SubElement(duimp, "conhecimentoCargaTipoCodigo").text = "12"
            ET.SubElement(duimp, "conhecimentoCargaTipoNome").text = "HBL - House Bill of Lading"
            ET.SubElement(duimp, "conhecimentoCargaUtilizacao").text = "1"
            ET.SubElement(duimp, "conhecimentoCargaUtilizacaoNome").text = "Total"
            
            # Datas
            ET.SubElement(duimp, "dataDesembaraco").text = self._formatar_data(dados.get("data_chegada", ""))
            ET.SubElement(duimp, "dataRegistro").text = datetime.now().strftime("%Y%m%d")
            
            # Documento Chegada
            ET.SubElement(duimp, "documentoChegadaCargaCodigoTipo").text = "1"
            ET.SubElement(duimp, "documentoChegadaCargaNome").text = "Manifesto da Carga"
            ET.SubElement(duimp, "documentoChegadaCargaNumero").text = "0000000000"
            
            # Documentos Instrução Despacho
            doc1 = ET.SubElement(duimp, "documentoInstrucaoDespacho")
            ET.SubElement(doc1, "codigoTipoDocumentoDespacho").text = "28"
            ET.SubElement(doc1, "nomeDocumentoDespacho").text = "CONHECIMENTO DE CARGA                                       "
            ET.SubElement(doc1, "numeroDocumentoDespacho").text = dados.get("conhecimento_numero", "SZXS069034").ljust(24)
            
            doc2 = ET.SubElement(duimp, "documentoInstrucaoDespacho")
            ET.SubElement(doc2, "codigoTipoDocumentoDespacho").text = "01"
            ET.SubElement(doc2, "nomeDocumentoDespacho").text = "FATURA COMERCIAL                                            "
            ET.SubElement(doc2, "numeroDocumentoDespacho").text = dados.get("fatura_numero", "554060729").ljust(24)
            
            doc3 = ET.SubElement(duimp, "documentoInstrucaoDespacho")
            ET.SubElement(doc3, "codigoTipoDocumentoDespacho").text = "29"
            ET.SubElement(doc3, "nomeDocumentoDespacho").text = "ROMANEIO DE CARGA                                           "
            ET.SubElement(doc3, "numeroDocumentoDespacho").text = "S/N                      "
            
            # Embalagem
            embalagem = ET.SubElement(duimp, "embalagem")
            ET.SubElement(embalagem, "codigoTipoEmbalagem").text = dados.get("tipo_embalagem", "01")
            ET.SubElement(embalagem, "nomeEmbalagem").text = "AMARRADO/ATADO/FEIXE                                          "
            ET.SubElement(embalagem, "quantidadeVolume").text = dados.get("quantidade_embalagem", "1").zfill(5)
            
            # Frete
            ET.SubElement(duimp, "freteCollect").text = self._formatar_valor_xml(dados.get("frete_moeda", "0"))
            ET.SubElement(duimp, "freteEmTerritorioNacional").text = "000000000000000"
            ET.SubElement(duimp, "freteMoedaNegociadaCodigo").text = cod_moeda_frete
            ET.SubElement(duimp, "freteMoedaNegociadaNome").text = nome_moeda_frete
            ET.SubElement(duimp, "fretePrepaid").text = "000000000000000"
            ET.SubElement(duimp, "freteTotalDolares").text = self._formatar_valor_xml(dados.get("frete_usd", "0"))
            ET.SubElement(duimp, "freteTotalMoeda").text = self._formatar_valor_xml(dados.get("frete_moeda", "0"), 5)
            ET.SubElement(duimp, "freteTotalReais").text = self._formatar_valor_xml(dados.get("frete_brl", "0"))
            
            # ICMS
            icms = ET.SubElement(duimp, "icms")
            ET.SubElement(icms, "agenciaIcms").text = "00000"
            ET.SubElement(icms, "bancoIcms").text = "000"
            ET.SubElement(icms, "codigoTipoRecolhimentoIcms").text = "3"
            ET.SubElement(icms, "cpfResponsavelRegistro").text = "00000000000"
            ET.SubElement(icms, "dataRegistro").text = datetime.now().strftime("%Y%m%d")
            ET.SubElement(icms, "horaRegistro").text = datetime.now().strftime("%H%M%S")
            ET.SubElement(icms, "nomeTipoRecolhimentoIcms").text = "Exoneração do ICMS"
            ET.SubElement(icms, "numeroSequencialIcms").text = "001"
            ET.SubElement(icms, "ufIcms").text = "PR"
            ET.SubElement(icms, "valorTotalIcms").text = "000000000000000"
            
            # Importador
            ET.SubElement(duimp, "importadorCodigoTipo").text = "1"
            ET.SubElement(duimp, "importadorCpfRepresentanteLegal").text = "00000000000"
            ET.SubElement(duimp, "importadorEnderecoBairro").text = "JARDIM PRIMAVERA"
            ET.SubElement(duimp, "importadorEnderecoCep").text = "83302000"
            ET.SubElement(duimp, "importadorEnderecoComplemento").text = "CONJ: 6 E 7;"
            ET.SubElement(duimp, "importadorEnderecoLogradouro").text = "JOAO LEOPOLDO JACOMEL"
            ET.SubElement(duimp, "importadorEnderecoMunicipio").text = "PIRAQUARA"
            ET.SubElement(duimp, "importadorEnderecoNumero").text = "4459"
            ET.SubElement(duimp, "importadorEnderecoUf").text = "PR"
            ET.SubElement(duimp, "importadorNome").text = dados.get("importador_nome", "HAFELE BRASIL LTDA")
            ET.SubElement(duimp, "importadorNomeRepresentanteLegal").text = "PAULO HENRIQUE LEITE FERREIRA"
            ET.SubElement(duimp, "importadorNumero").text = dados.get("importador_cnpj", "02473058000188").replace(".", "").replace("/", "").replace("-", "")
            ET.SubElement(duimp, "importadorNumeroTelefone").text = "41  30348150"
            
            # Informação Complementar
            info_text = f"""INFORMACOES COMPLEMENTARES
--------------------------
PROCESSO :{dados.get('processo', '28523')}
REF. IMPORTADOR :{dados.get('ref_importador', 'TESTE DUIMP')}
IMPORTADOR :{dados.get('importador_nome', 'HAFELE BRASIL LTDA')}
PESO LIQUIDO :{dados.get('peso_liquido', '0')}
PESO BRUTO :{dados.get('peso_bruto', '0')}
FORNECEDOR :{dados.get('exportador_estrangeiro', 'HAFELE ENGINEERING ASIA LTD.')}
PAIS PROCEDENCIA :{dados.get('pais_procedencia', 'CHINA')}
VIA TRANSPORTE :{dados.get('via_transporte', 'MARITIMA')}
DATA EMBARQUE :{dados.get('data_embarque', '')}
DATA CHEGADA :{dados.get('data_chegada', '')}
DOCUMENTOS ANEXOS - MARITIMO
----------------------------
CONHECIMENTO DE CARGA :{dados.get('conhecimento_numero', 'SZXS069034')}
FATURA COMERCIAL :{dados.get('fatura_numero', '554060729')}
ROMANEIO DE CARGA :S/N
VALORES EM MOEDA
----------------
FOB :{dados.get('vir_cond_moeda', '0')} {cod_moeda} - {nome_moeda}
FRETE COLLECT :{dados.get('frete_moeda', '0')} {cod_moeda_frete} - {nome_moeda_frete}
SEGURO :{dados.get('seguro_moeda', '0')} {cod_moeda_seguro} - {nome_moeda_seguro}
VALORES EM MOEDA NACIONAL
-------------------------------------------
FOB :{dados.get('vir_cond_brl', '0')}
FRETE :{dados.get('frete_brl', '0')}
SEGURO :{dados.get('seguro_brl', '0')}
VALOR CIF :{dados.get('cif_brl', '0')}
TAXA SISCOMEX :{dados.get('taxa_utilizacao', '154,23')}
I.I. :{dados.get('ii_recolher', '0')}
PIS/PASEP :{dados.get('pis_recolher', '0')}
COFINS :{dados.get('cofins_recolher', '0')}
OUTROS ACRESCIMOS :0,00
TAXA DOLAR DOS EUA :{dados.get('cotacao_moeda', '5,3843000')}
**************************************************"""
            
            ET.SubElement(duimp, "informacaoComplementar").text = info_text
            
            # Totais
            ET.SubElement(duimp, "localDescargaTotalDolares").text = self._formatar_valor_xml(dados.get("vmld_usd", "0"))
            ET.SubElement(duimp, "localDescargaTotalReais").text = self._formatar_valor_xml(dados.get("vmld_brl", "0"))
            ET.SubElement(duimp, "localEmbarqueTotalDolares").text = self._formatar_valor_xml(dados.get("vmle_usd", "0"))
            ET.SubElement(duimp, "localEmbarqueTotalReais").text = self._formatar_valor_xml(dados.get("vmle_brl", "0"))
            
            ET.SubElement(duimp, "modalidadeDespachoCodigo").text = "1"
            ET.SubElement(duimp, "modalidadeDespachoNome").text = "Normal"
            ET.SubElement(duimp, "numeroDUIMP").text = dados.get("identificacao_numero", "25BR00001916620")
            ET.SubElement(duimp, "operacaoFundap").text = "N"
            
            # Pagamentos
            pag1 = ET.SubElement(duimp, "pagamento")
            ET.SubElement(pag1, "agenciaPagamento").text = "3715 "
            ET.SubElement(pag1, "bancoPagamento").text = "341"
            ET.SubElement(pag1, "codigoReceita").text = "0086"
            ET.SubElement(pag1, "codigoTipoPagamento").text = "1"
            ET.SubElement(pag1, "contaPagamento").text = "             316273"
            ET.SubElement(pag1, "dataPagamento").text = datetime.now().strftime("%Y%m%d")
            ET.SubElement(pag1, "nomeTipoPagamento").text = "Débito em Conta"
            ET.SubElement(pag1, "numeroRetificacao").text = "00"
            ET.SubElement(pag1, "valorJurosEncargos").text = "000000000"
            ET.SubElement(pag1, "valorMulta").text = "000000000"
            ET.SubElement(pag1, "valorReceita").text = self._formatar_valor_xml(dados.get("ii_recolher", "0"), 9)
            
            pag2 = ET.SubElement(duimp, "pagamento")
            ET.SubElement(pag2, "agenciaPagamento").text = "3715 "
            ET.SubElement(pag2, "bancoPagamento").text = "341"
            ET.SubElement(pag2, "codigoReceita").text = "5602"
            ET.SubElement(pag2, "codigoTipoPagamento").text = "1"
            ET.SubElement(pag2, "contaPagamento").text = "             316273"
            ET.SubElement(pag2, "dataPagamento").text = datetime.now().strftime("%Y%m%d")
            ET.SubElement(pag2, "nomeTipoPagamento").text = "Débito em Conta"
            ET.SubElement(pag2, "numeroRetificacao").text = "00"
            ET.SubElement(pag2, "valorJurosEncargos").text = "000000000"
            ET.SubElement(pag2, "valorMulta").text = "000000000"
            ET.SubElement(pag2, "valorReceita").text = self._formatar_valor_xml(dados.get("pis_recolher", "0"), 9)
            
            pag3 = ET.SubElement(duimp, "pagamento")
            ET.SubElement(pag3, "agenciaPagamento").text = "3715 "
            ET.SubElement(pag3, "bancoPagamento").text = "341"
            ET.SubElement(pag3, "codigoReceita").text = "5629"
            ET.SubElement(pag3, "codigoTipoPagamento").text = "1"
            ET.SubElement(pag3, "contaPagamento").text = "             316273"
            ET.SubElement(pag3, "dataPagamento").text = datetime.now().strftime("%Y%m%d")
            ET.SubElement(pag3, "nomeTipoPagamento").text = "Débito em Conta"
            ET.SubElement(pag3, "numeroRetificacao").text = "00"
            ET.SubElement(pag3, "valorJurosEncargos").text = "000000000"
            ET.SubElement(pag3, "valorMulta").text = "000000000"
            ET.SubElement(pag3, "valorReceita").text = self._formatar_valor_xml(dados.get("cofins_recolher", "0"), 9)
            
            pag4 = ET.SubElement(duimp, "pagamento")
            ET.SubElement(pag4, "agenciaPagamento").text = "3715 "
            ET.SubElement(pag4, "bancoPagamento").text = "341"
            ET.SubElement(pag4, "codigoReceita").text = "7811"
            ET.SubElement(pag4, "codigoTipoPagamento").text = "1"
            ET.SubElement(pag4, "contaPagamento").text = "             316273"
            ET.SubElement(pag4, "dataPagamento").text = datetime.now().strftime("%Y%m%d")
            ET.SubElement(pag4, "nomeTipoPagamento").text = "Débito em Conta"
            ET.SubElement(pag4, "numeroRetificacao").text = "00"
            ET.SubElement(pag4, "valorJurosEncargos").text = "000000000"
            ET.SubElement(pag4, "valorMulta").text = "000000000"
            ET.SubElement(pag4, "valorReceita").text = self._formatar_valor_xml(dados.get("taxa_utilizacao", "0"), 9)
            
            # Seguro
            ET.SubElement(duimp, "seguroMoedaNegociadaCodigo").text = cod_moeda_seguro
            ET.SubElement(duimp, "seguroMoedaNegociadaNome").text = nome_moeda_seguro
            ET.SubElement(duimp, "seguroTotalDolares").text = self._formatar_valor_xml(dados.get("seguro_moeda", "0"))
            ET.SubElement(duimp, "seguroTotalMoedaNegociada").text = self._formatar_valor_xml(dados.get("seguro_moeda", "0"))
            ET.SubElement(duimp, "seguroTotalReais").text = self._formatar_valor_xml(dados.get("seguro_brl", "0"))
            
            ET.SubElement(duimp, "sequencialRetificacao").text = "00"
            ET.SubElement(duimp, "situacaoEntregaCarga").text = "ENTREGA NORMAL"
            ET.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
            ET.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
            ET.SubElement(duimp, "totalAdicoes").text = "001"
            ET.SubElement(duimp, "urfDespachoCodigo").text = dados.get("unidade_despacho", "0917800").split()[0]
            ET.SubElement(duimp, "urfDespachoNome").text = dados.get("unidade_despacho", "PORTO DE PARANAGUA")
            ET.SubElement(duimp, "valorTotalMultaARecolherAjustado").text = "000000000000000"
            
            # Via Transporte
            ET.SubElement(duimp, "viaTransporteCodigo").text = "01"
            ET.SubElement(duimp, "viaTransporteMultimodal").text = "N"
            ET.SubElement(duimp, "viaTransporteNome").text = "MARÍTIMA"
            ET.SubElement(duimp, "viaTransporteNomeTransportador").text = "N/I"
            ET.SubElement(duimp, "viaTransporteNomeVeiculo").text = "N/I"
            
            cod_pais_transp, nome_pais_transp = self._formatar_pais(dados.get("bandeira_embarcacao", "MARSHALL,ILHAS"))
            ET.SubElement(duimp, "viaTransportePaisTransportadorCodigo").text = cod_pais_transp
            ET.SubElement(duimp, "viaTransportePaisTransportadorNome").text = nome_pais_transp
            
            # Converter para string XML formatada
            xml_string = self._prettify_xml(lista_declaracoes)
            
            return xml_string
            
        except Exception as e:
            st.error(f"Erro ao criar XML: {str(e)}")
            return ""
    
    def _prettify_xml(self, elem):
        """Retorna uma string XML formatada"""
        rough_string = ET.tostring(elem, encoding='utf-8', method='xml')
        reparsed = minidom.parseString(rough_string)
        
        # Formatar o XML
        xml_pretty = reparsed.toprettyxml(indent="  ", encoding='utf-8')
        
        # Remover linhas em branco extras
        lines = xml_pretty.decode('utf-8').split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        return '\n'.join(non_empty_lines)


def main():
    """Função principal do aplicativo Streamlit"""
    
    st.set_page_config(
        page_title="Conversor DUIMP PDF para XML",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("🔄 Conversor de DUIMP - PDF para XML")
    st.markdown("""
    Converta extratos de DUIMP em formato PDF para XML estruturado seguindo o layout obrigatório.
    **Layout fixo do PDF** - O sistema espera o formato específico do extrato de conferência.
    """)
    
    # Inicializar conversor
    converter = DUIMPConverter()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        st.markdown("""
        ### Instruções:
        1. Faça upload do PDF do extrato de DUIMP
        2. O sistema extrairá automaticamente os dados
        3. Gere o XML no formato correto
        4. Baixe o arquivo XML
        """)
        
        st.divider()
        
        st.info("""
        **Formato PDF Esperado:**
        - Extrato de conferência de DUIMP
        - Layout fixo (não altera)
        - Conteúdo em português
        - Campos específicos da Receita Federal
        """)
    
    # Área principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📤 Upload do PDF")
        uploaded_file = st.file_uploader(
            "Selecione o arquivo PDF do extrato de DUIMP",
            type=['pdf'],
            help="Arquivo PDF com layout fixo do extrato de conferência"
        )
        
        if uploaded_file is not None:
            # Salvar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                pdf_path = tmp_file.name
            
            st.success(f"✅ PDF carregado: {uploaded_file.name}")
            
            # Botão para processar
            if st.button("🔍 Processar PDF e Gerar XML", type="primary", use_container_width=True):
                with st.spinner("Processando PDF e gerando XML..."):
                    try:
                        # Extrair dados do PDF
                        dados = converter.extrair_texto_pdf(pdf_path)
                        
                        if dados:
                            # Mostrar resumo dos dados extraídos
                            with st.expander("📊 Dados Extraídos do PDF", expanded=False):
                                st.json(dados, expanded=False)
                            
                            # Gerar XML
                            xml_content = converter.criar_xml(dados)
                            
                            if xml_content:
                                # Salvar XML temporário
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.xml', mode='w', encoding='utf-8') as xml_file:
                                    xml_file.write(xml_content)
                                    xml_path = xml_file.name
                                
                                # Mostrar preview do XML
                                with st.expander("👁️ Preview do XML Gerado", expanded=False):
                                    st.code(xml_content, language='xml', line_numbers=True)
                                
                                # Botão de download
                                st.subheader("📥 Download do XML")
                                
                                # Preparar arquivo para download
                                b64_xml = base64.b64encode(xml_content.encode()).decode()
                                href = f'<a href="data:application/xml;base64,{b64_xml}" download="duimp_{dados.get("identificacao_numero", "output")}.xml" style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">⬇️ Baixar Arquivo XML</a>'
                                
                                st.markdown(href, unsafe_allow_html=True)
                                
                                # Estatísticas
                                col_stat1, col_stat2, col_stat3 = st.columns(3)
                                with col_stat1:
                                    st.metric("Tags XML", str(xml_content.count('<')))
                                with col_stat2:
                                    st.metric("Linhas", str(xml_content.count('\n') + 1))
                                with col_stat3:
                                    st.metric("Tamanho", f"{len(xml_content) / 1024:.1f} KB")
                                
                                st.success("✅ XML gerado com sucesso!")
                            else:
                                st.error("❌ Falha ao gerar XML")
                        else:
                            st.error("❌ Não foi possível extrair dados do PDF")
                            
                    except Exception as e:
                        st.error(f"❌ Erro no processamento: {str(e)}")
                        st.exception(e)
                    
                    finally:
                        # Limpar arquivos temporários
                        try:
                            os.unlink(pdf_path)
                            if 'xml_path' in locals():
                                os.unlink(xml_path)
                        except:
                            pass
    
    with col2:
        st.subheader("📋 Layout Esperado")
        st.markdown("""
        **Seções do XML:**
        
        1. **Adições (adicao)**
           - Dados da mercadoria
           - Tributos (II, IPI, PIS, COFINS)
           - Valores e moedas
           - Informações de frete e seguro
        
        2. **Dados Gerais**
           - Identificação da DUIMP
           - Importador
           - Transporte
           - Documentação
        
        3. **Pagamentos**
           - Impostos devidos
           - Valores a recolher
        
        **Campos Obrigatórios:**
        - Todas as tags do mapeamento original
        - Valores formatados com zeros
        - Estrutura hierárquica preservada
        """)
        
        st.divider()
        
        st.caption("""
        **Tecnologias utilizadas:**
        - Streamlit para interface
        - pdfplumber para extração de PDF
        - ElementTree para geração de XML
        - Regex para parsing de texto fixo
        """)
    
    # Rodapé
    st.divider()
    st.caption("Desenvolvido para conversão de extratos de DUIMP - Layout Fixo 📄→📊")


if __name__ == "__main__":
    main()
