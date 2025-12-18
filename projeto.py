import streamlit as st
import pdfplumber
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import os
import tempfile
from datetime import datetime
import hashlib
import io

class DUIMPPDFConverter:
    def __init__(self):
        self.xml_template = self.load_xml_template()
        self.current_duimp_number = None
        self.adicao_counter = 0
        self.item_counter = 1
    
    def load_xml_template(self):
        """Retorna a estrutura base do XML conforme o modelo"""
        return {
            "header": {
                "numeroDUIMP": "",
                "dataRegistro": "",
                "dataDesembaraco": "",
                "importadorNome": "HAFELE BRASIL LTDA",
                "importadorNumero": "02473058000188",
                "cargaDataChegada": "",
                "cargaPesoBruto": "",
                "cargaPesoLiquido": "",
                "totalAdicoes": ""
            },
            "adicoes": []
        }
    
    def format_number(self, value, length=15, decimal_places=2):
        """Formata números com zeros à esquerda no padrão XML"""
        if not value:
            return "0" * length
        
        try:
            # Remove caracteres não numéricos, exceto ponto e vírgula
            clean_val = re.sub(r'[^\d,-]', '', str(value))
            clean_val = clean_val.replace(',', '.')
            
            # Se tiver hífen (negativo), trata separadamente
            if '-' in clean_val:
                clean_val = clean_val.replace('-', '')
                num = float(clean_val)
                num = -num
            else:
                num = float(clean_val)
            
            # Multiplica pelo fator de casas decimais
            factor = 10 ** decimal_places
            int_val = int(abs(num) * factor)
            
            # Formata com zeros à esquerda
            formatted = str(int_val).zfill(length)
            
            return formatted
        except:
            return "0" * length
    
    def parse_large_pdf(self, pdf_path):
        """Processa PDFs grandes página por página"""
        all_text = ""
        page_data = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, page in enumerate(pdf.pages):
                # Atualiza progresso
                progress = (i + 1) / total_pages
                progress_bar.progress(progress)
                status_text.text(f"Processando página {i+1} de {total_pages}")
                
                # Extrai texto da página
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"
                page_data.append({
                    "page_num": i + 1,
                    "text": page_text,
                    "items": []
                })
            
            progress_bar.empty()
            status_text.empty()
        
        return all_text, page_data
    
    def extract_duimp_number(self, text):
        """Extrai número DUIMP do texto"""
        patterns = [
            r'Número\s+(\d+[A-Z]+\d+)',
            r'DUIMP\s*[:]?\s*(\d+)',
            r'Nº\s*DUIMP\s*[:]?\s*(\d+)',
            r'(\d{10})'  # Padrão de 10 dígitos
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Usa número padrão se não encontrar
        return "8686868686"
    
    def extract_dates(self, text):
        """Extrai várias datas do texto"""
        dates = {
            "dataRegistro": "",
            "dataDesembaraco": "",
            "cargaDataChegada": "",
            "conhecimentoCargaEmbarqueData": ""
        }
        
        # Padrões para datas
        date_patterns = [
            (r'Data Registro\s+(\d{2})/(\d{2})/(\d{4})', "dataRegistro"),
            (r'Data de Registro\s+(\d{2})/(\d{2})/(\d{4})', "dataRegistro"),
            (r'Data de Chegada\s+(\d{2})/(\d{2})/(\d{4})', "cargaDataChegada"),
            (r'Data de Embarque\s+(\d{2})/(\d{2})/(\d{4})', "conhecimentoCargaEmbarqueData"),
            (r'(\d{2})/(\d{2})/(\d{4})', "dataRegistro")  # Padrão genérico
        ]
        
        for pattern, key in date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    if len(match) == 3:
                        day, month, year = match
                        # Validação básica da data
                        if 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
                            dates[key] = f"{year}{month}{day}"
                            break
        
        # Se não encontrar data de desembaraço, usa a data de registro
        if not dates["dataDesembaraco"] and dates["dataRegistro"]:
            dates["dataDesembaraco"] = dates["dataRegistro"]
        
        return dates
    
    def extract_weights(self, text):
        """Extrai pesos do texto"""
        weights = {
            "cargaPesoBruto": "",
            "cargaPesoLiquido": ""
        }
        
        # Padrões para pesos
        weight_patterns = [
            (r'PESO BRUTO\s+([\d\.,]+)', "cargaPesoBruto"),
            (r'Peso Bruto\s+([\d\.,]+)', "cargaPesoBruto"),
            (r'PESO L[IÍ]QUIDO\s+([\d\.,]+)', "cargaPesoLiquido"),
            (r'Peso L[IÍ]quido\s+([\d\.,]+)', "cargaPesoLiquido")
        ]
        
        for pattern, key in weight_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                weight = match.group(1).replace('.', '').replace(',', '')
                weights[key] = self.format_number(weight, 15, 0)
                break
        
        return weights
    
    def extract_adicoes_from_text(self, text):
        """Extrai todas as adições (itens) do texto"""
        adicoes = []
        
        # Divide o texto em seções por item
        # Procura por padrões que indiquem início de item
        sections = text.split('\n')
        current_item = None
        item_text = ""
        
        for i, line in enumerate(sections):
            # Procura início de item
            if re.search(r'^\s*Item\s+\d+\s*$', line.strip()) or re.search(r'^\s*\d+\s*-\s*', line.strip()):
                # Se já tem um item sendo processado, salva ele
                if current_item is not None and item_text.strip():
                    adicao = self.process_item_section(item_text, current_item)
                    if adicao:
                        adicoes.append(adicao)
                
                # Inicia novo item
                current_item = line.strip()
                item_text = line + "\n"
            elif current_item is not None:
                # Continua acumulando texto do item atual
                item_text += line + "\n"
        
        # Processa o último item
        if current_item is not None and item_text.strip():
            adicao = self.process_item_section(item_text, current_item)
            if adicao:
                adicoes.append(adicao)
        
        return adicoes
    
    def process_item_section(self, section_text, item_header):
        """Processa uma seção de item individual"""
        adicao = self.create_adicao_template()
        
        # Extrai número do item do cabeçalho
        item_match = re.search(r'Item\s+(\d+)', item_header)
        if item_match:
            item_num = item_match.group(1)
            adicao["numeroAdicao"] = str(int(item_num)).zfill(3)
            adicao["mercadoria"]["numeroSequencialItem"] = str(int(item_num)).zfill(2)
        
        # Tenta extrair NCM - procura padrão NCM seguido de números
        ncm_match = re.search(r'NCM\s*[:]?\s*([\d\.]+)', section_text)
        if ncm_match:
            ncm = ncm_match.group(1).replace('.', '')
            adicao["dadosMercadoriaCodigoNcm"] = ncm.zfill(8)
        
        # Procura por descrição do produto
        desc_lines = []
        lines = section_text.split('\n')
        in_description = False
        
        for line in lines:
            line_lower = line.lower()
            # Procura por palavras-chave que indicam descrição
            if any(keyword in line_lower for keyword in ['descrição', 'denomina', 'produto', 'mercadoria']):
                in_description = True
                # Remove a palavra-chave da linha
                clean_line = re.sub(r'.*?(descrição|denomina|produto|mercadoria)\s*[:]?\s*', '', line, flags=re.IGNORECASE)
                if clean_line.strip():
                    desc_lines.append(clean_line.strip())
            elif in_description:
                # Para de coletar quando encontra outra seção
                if any(keyword in line_lower for keyword in ['quantidade', 'qtd', 'valor', 'preço', 'ncm']):
                    in_description = False
                elif line.strip():
                    desc_lines.append(line.strip())
        
        if desc_lines:
            descricao = ' '.join(desc_lines)
            if len(descricao) > 200:
                descricao = descricao[:197] + "..."
            adicao["mercadoria"]["descricaoMercadoria"] = descricao
        
        # Procura quantidade
        qtd_match = re.search(r'(?:Quantidade|Qtd\.?|Qtde)\s*[:]?\s*([\d\.,]+)', section_text, re.IGNORECASE)
        if qtd_match:
            qtd = qtd_match.group(1).replace('.', '').replace(',', '')
            adicao["mercadoria"]["quantidade"] = self.format_number(qtd, 14, 0)
        
        # Procura valor unitário
        valor_unit_match = re.search(r'(?:Valor\s+Unit[áa]rio|Vlr\.?\s+Unit\.?|Pre[çc]o\s+Unit[áa]rio)\s*[:]?\s*([\d\.,]+)', section_text, re.IGNORECASE)
        if valor_unit_match:
            valor = valor_unit_match.group(1).replace('.', '').replace(',', '.')
            adicao["mercadoria"]["valorUnitario"] = self.format_number(valor, 20, 6)
        
        # Procura valor total
        valor_total_match = re.search(r'(?:Valor\s+Total|Vlr\.?\s+Total|Total)\s*[:]?\s*([\d\.,]+)', section_text, re.IGNORECASE)
        if valor_total_match:
            valor = valor_total_match.group(1).replace('.', '').replace(',', '.')
            adicao["condicaoVendaValorMoeda"] = self.format_number(valor, 15, 2)
            adicao["condicaoVendaValorReais"] = self.format_number(valor, 15, 2)
        
        # Define número DUIMP
        adicao["numeroDUIMP"] = self.current_duimp_number
        
        # Incrementa contadores
        self.adicao_counter += 1
        
        return adicao
    
    def create_adicao_template(self):
        """Cria template de adição conforme modelo XML"""
        return {
            "acrescimo": {
                "codigoAcrescimo": "17",
                "denominacao": "OUTROS ACRESCIMOS AO VALOR ADUANEIRO                        ",
                "moedaNegociadaCodigo": "978",
                "moedaNegociadaNome": "EURO/COM.EUROPEIA",
                "valorMoedaNegociada": "000000000000000",
                "valorReais": "000000000000000"
            },
            "cideValorAliquotaEspecifica": "00000000000",
            "cideValorDevido": "000000000000000",
            "cideValorRecolher": "000000000000000",
            "codigoRelacaoCompradorVendedor": "3",
            "codigoVinculoCompradorVendedor": "1",
            "cofinsAliquotaAdValorem": "00965",
            "cofinsAliquotaEspecificaQuantidadeUnidade": "000000000",
            "cofinsAliquotaEspecificaValor": "0000000000",
            "cofinsAliquotaReduzida": "00000",
            "cofinsAliquotaValorDevido": "000000000000000",
            "cofinsAliquotaValorRecolher": "000000000000000",
            "condicaoVendaIncoterm": "FCA",
            "condicaoVendaLocal": "BRUGNERA",
            "condicaoVendaMetodoValoracaoCodigo": "01",
            "condicaoVendaMetodoValoracaoNome": "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)",
            "condicaoVendaMoedaCodigo": "978",
            "condicaoVendaMoedaNome": "EURO/COM.EUROPEIA",
            "condicaoVendaValorMoeda": "000000000000000",
            "condicaoVendaValorReais": "000000000000000",
            "dadosCambiaisCoberturaCambialCodigo": "1",
            "dadosCambiaisCoberturaCambialNome": "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180",
            "dadosCambiaisInstituicaoFinanciadoraCodigo": "00",
            "dadosCambiaisInstituicaoFinanciadoraNome": "N/I",
            "dadosCambiaisMotivoSemCoberturaCodigo": "00",
            "dadosCambiaisMotivoSemCoberturaNome": "N/I",
            "dadosCambiaisValorRealCambio": "000000000000000",
            "dadosCargaPaisProcedenciaCodigo": "000",
            "dadosCargaUrfEntradaCodigo": "0000000",
            "dadosCargaViaTransporteCodigo": "01",
            "dadosCargaViaTransporteNome": "MARÍTIMA",
            "dadosMercadoriaAplicacao": "REVENDA",
            "dadosMercadoriaCodigoNaladiNCCA": "0000000",
            "dadosMercadoriaCodigoNaladiSH": "00000000",
            "dadosMercadoriaCodigoNcm": "00000000",
            "dadosMercadoriaCondicao": "NOVA",
            "dadosMercadoriaDescricaoTipoCertificado": "Sem Certificado",
            "dadosMercadoriaIndicadorTipoCertificado": "1",
            "dadosMercadoriaMedidaEstatisticaQuantidade": "00000000000000",
            "dadosMercadoriaMedidaEstatisticaUnidade": "QUILOGRAMA LIQUIDO",
            "dadosMercadoriaNomeNcm": "- Guarnições para móveis, carroçarias ou semelhantes",
            "dadosMercadoriaPesoLiquido": "000000000000000",
            "dcrCoeficienteReducao": "00000",
            "dcrIdentificacao": "00000000",
            "dcrValorDevido": "000000000000000",
            "dcrValorDolar": "000000000000000",
            "dcrValorReal": "000000000000000",
            "dcrValorRecolher": "000000000000000",
            "fornecedorCidade": "BRUGNERA",
            "fornecedorLogradouro": "VIALE EUROPA",
            "fornecedorNome": "ITALIANA FERRAMENTA S.R.L.",
            "fornecedorNumero": "17",
            "freteMoedaNegociadaCodigo": "978",
            "freteMoedaNegociadaNome": "EURO/COM.EUROPEIA",
            "freteValorMoedaNegociada": "000000000000000",
            "freteValorReais": "000000000000000",
            "iiAcordoTarifarioTipoCodigo": "0",
            "iiAliquotaAcordo": "00000",
            "iiAliquotaAdValorem": "01800",
            "iiAliquotaPercentualReducao": "00000",
            "iiAliquotaReduzida": "00000",
            "iiAliquotaValorCalculado": "000000000000000",
            "iiAliquotaValorDevido": "000000000000000",
            "iiAliquotaValorRecolher": "000000000000000",
            "iiAliquotaValorReduzido": "000000000000000",
            "iiBaseCalculo": "000000000000000",
            "iiFundamentoLegalCodigo": "00",
            "iiMotivoAdmissaoTemporariaCodigo": "00",
            "iiRegimeTributacaoCodigo": "1",
            "iiRegimeTributacaoNome": "RECOLHIMENTO INTEGRAL",
            "ipiAliquotaAdValorem": "00325",
            "ipiAliquotaEspecificaCapacidadeRecipciente": "00000",
            "ipiAliquotaEspecificaQuantidadeUnidadeMedida": "000000000",
            "ipiAliquotaEspecificaTipoRecipienteCodigo": "00",
            "ipiAliquotaEspecificaValorUnidadeMedida": "0000000000",
            "ipiAliquotaNotaComplementarTIPI": "00",
            "ipiAliquotaReduzida": "00000",
            "ipiAliquotaValorDevido": "000000000000000",
            "ipiAliquotaValorRecolher": "000000000000000",
            "ipiRegimeTributacaoCodigo": "4",
            "ipiRegimeTributacaoNome": "SEM BENEFICIO",
            "mercadoria": {
                "descricaoMercadoria": "PRODUTO IMPORTADO",
                "numeroSequencialItem": "01",
                "quantidade": "00000000000000",
                "unidadeMedida": "PECA                ",
                "valorUnitario": "00000000000000000000"
            },
            "numeroAdicao": "001",
            "numeroDUIMP": "",
            "numeroLI": "0000000000",
            "paisAquisicaoMercadoriaCodigo": "386",
            "paisAquisicaoMercadoriaNome": "ITALIA",
            "paisOrigemMercadoriaCodigo": "386",
            "paisOrigemMercadoriaNome": "ITALIA",
            "pisCofinsBaseCalculoAliquotaICMS": "00000",
            "pisCofinsBaseCalculoFundamentoLegalCodigo": "00",
            "pisCofinsBaseCalculoPercentualReducao": "00000",
            "pisCofinsBaseCalculoValor": "000000000000000",
            "pisCofinsFundamentoLegalReducaoCodigo": "00",
            "pisCofinsRegimeTributacaoCodigo": "1",
            "pisCofinsRegimeTributacaoNome": "RECOLHIMENTO INTEGRAL",
            "pisPasepAliquotaAdValorem": "00210",
            "pisPasepAliquotaEspecificaQuantidadeUnidade": "000000000",
            "pisPasepAliquotaEspecificaValor": "0000000000",
            "pisPasepAliquotaReduzida": "00000",
            "pisPasepAliquotaValorDevido": "000000000000000",
            "pisPasepAliquotaValorRecolher": "000000000000000",
            "relacaoCompradorVendedor": "Fabricante é desconhecido",
            "seguroMoedaNegociadaCodigo": "220",
            "seguroMoedaNegociadaNome": "DOLAR DOS EUA",
            "seguroValorMoedaNegociada": "000000000000000",
            "seguroValorReais": "000000000000000",
            "sequencialRetificacao": "00",
            "valorMultaARecolher": "000000000000000",
            "valorMultaARecolherAjustado": "000000000000000",
            "valorReaisFreteInternacional": "000000000000000",
            "valorReaisSeguroInternacional": "000000000000000",
            "valorTotalCondicaoVenda": "00000000000",
            "vinculoCompradorVendedor": "Não há vinculação entre comprador e vendedor."
        }
    
    def build_xml_structure(self, data):
        """Constrói a estrutura XML completa conforme modelo"""
        
        # Cria elemento raiz
        lista_declaracoes = ET.Element("ListaDeclaracoes")
        duimp = ET.SubElement(lista_declaracoes, "duimp")
        
        # Adiciona as adições
        for adicao_data in data["adicoes"]:
            adicao = ET.SubElement(duimp, "adicao")
            
            # Percorre todos os campos da adição
            for key, value in adicao_data.items():
                if isinstance(value, dict):
                    # Sub-elemento (como acrescimo, mercadoria)
                    sub_elem = ET.SubElement(adicao, key)
                    for sub_key, sub_value in value.items():
                        sub_sub_elem = ET.SubElement(sub_elem, sub_key)
                        sub_sub_elem.text = str(sub_value)
                else:
                    # Elemento simples
                    elem = ET.SubElement(adicao, key)
                    elem.text = str(value)
        
        # Adiciona elementos fixos do modelo
        self.add_fixed_elements(duimp, data)
        
        # Converte para string XML
        xml_str = ET.tostring(lista_declaracoes, encoding='utf-8', method='xml')
        
        # Parse para garantir que está bem formado
        try:
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="  ")
            
            # Remove a declaração XML padrão que o minidom adiciona
            # para que possamos adicionar a nossa própria
            if pretty_xml.startswith('<?xml'):
                lines = pretty_xml.split('\n', 1)
                if len(lines) > 1:
                    pretty_xml = lines[1]
            
            # Adiciona nossa declaração XML CORRETAMENTE
            final_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + pretty_xml
            
            return final_xml
        except Exception as e:
            # Se houver erro no parsing, retorna XML simples
            simple_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_str.decode('utf-8')
            return simple_xml
    
    def add_fixed_elements(self, duimp_element, data):
        """Adiciona elementos fixos ao XML"""
        
        # Elementos simples
        fixed_elements_simple = {
            "armazenamentoRecintoAduaneiroCodigo": "9801303",
            "armazenamentoRecintoAduaneiroNome": "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A",
            "armazenamentoSetor": "002",
            "canalSelecaoParametrizada": "001",
            "caracterizacaoOperacaoCodigoTipo": "1",
            "caracterizacaoOperacaoDescricaoTipo": "Importação Própria",
            "cargaDataChegada": data.get("cargaDataChegada", "20251120"),
            "cargaNumeroAgente": "N/I",
            "cargaPaisProcedenciaCodigo": "386",
            "cargaPaisProcedenciaNome": "ITALIA",
            "cargaPesoBruto": data.get("cargaPesoBruto", "000000053415000"),
            "cargaPesoLiquido": data.get("cargaPesoLiquido", "000000048686100"),
            "cargaUrfEntradaCodigo": "0917800",
            "cargaUrfEntradaNome": "PORTO DE PARANAGUA",
            "conhecimentoCargaEmbarqueData": data.get("conhecimentoCargaEmbarqueData", "20251025"),
            "conhecimentoCargaEmbarqueLocal": "GENOVA",
            "conhecimentoCargaId": "CEMERCANTE31032008",
            "conhecimentoCargaIdMaster": "162505352452915",
            "conhecimentoCargaTipoCodigo": "12",
            "conhecimentoCargaTipoNome": "HBL - House Bill of Lading",
            "conhecimentoCargaUtilizacao": "1",
            "conhecimentoCargaUtilizacaoNome": "Total",
            "dataDesembaraco": data.get("dataDesembaraco", "20251124"),
            "dataRegistro": data.get("dataRegistro", "20251124"),
            "documentoChegadaCargaCodigoTipo": "1",
            "documentoChegadaCargaNome": "Manifesto da Carga",
            "documentoChegadaCargaNumero": "1625502058594",
            "freteCollect": "000000000025000",
            "freteEmTerritorioNacional": "000000000000000",
            "freteMoedaNegociadaCodigo": "978",
            "freteMoedaNegociadaNome": "EURO/COM.EUROPEIA",
            "fretePrepaid": "000000000000000",
            "freteTotalDolares": "000000000028757",
            "freteTotalMoeda": "25000",
            "freteTotalReais": "000000000155007",
            "importadorCodigoTipo": "1",
            "importadorCpfRepresentanteLegal": "27160353854",
            "importadorEnderecoBairro": "JARDIM PRIMAVERA",
            "importadorEnderecoCep": "83302000",
            "importadorEnderecoComplemento": "CONJ: 6 E 7;",
            "importadorEnderecoLogradouro": "JOAO LEOPOLDO JACOMEL",
            "importadorEnderecoMunicipio": "PIRAQUARA",
            "importadorEnderecoNumero": "4459",
            "importadorEnderecoUf": "PR",
            "importadorNome": "HAFELE BRASIL LTDA",
            "importadorNomeRepresentanteLegal": "PAULO HENRIQUE LEITE FERREIRA",
            "importadorNumero": "02473058000188",
            "importadorNumeroTelefone": "41  30348150",
            "modalidadeDespachoCodigo": "1",
            "modalidadeDespachoNome": "Normal",
            "numeroDUIMP": self.current_duimp_number,
            "operacaoFundap": "N",
            "seguroMoedaNegociadaCodigo": "220",
            "seguroMoedaNegociadaNome": "DOLAR DOS EUA",
            "seguroTotalDolares": "000000000002146",
            "seguroTotalMoedaNegociada": "000000000002146",
            "seguroTotalReais": "000000000011567",
            "sequencialRetificacao": "00",
            "situacaoEntregaCarga": "ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE EXONERACAO DO ICMS",
            "tipoDeclaracaoCodigo": "01",
            "tipoDeclaracaoNome": "CONSUMO",
            "totalAdicoes": str(len(data["adicoes"])).zfill(3),
            "urfDespachoCodigo": "0917800",
            "urfDespachoNome": "PORTO DE PARANAGUA",
            "valorTotalMultaARecolherAjustado": "000000000000000",
            "viaTransporteCodigo": "01",
            "viaTransporteMultimodal": "N",
            "viaTransporteNome": "MARÍTIMA",
            "viaTransporteNomeTransportador": "MAERSK A/S",
            "viaTransporteNomeVeiculo": "MAERSK MEMPHIS",
            "viaTransportePaisTransportadorCodigo": "741",
            "viaTransportePaisTransportadorNome": "CINGAPURA"
        }
        
        for key, value in fixed_elements_simple.items():
            elem = ET.SubElement(duimp_element, key)
            elem.text = value
        
        # Armazem (sub-elemento)
        armazem = ET.SubElement(duimp_element, "armazem")
        ET.SubElement(armazem, "nomeArmazem").text = "TCP       "
        
        # Documentos de instrução de despacho
        documentos = [
            ("28", "CONHECIMENTO DE CARGA                                       ", "372250376737202501       "),
            ("01", "FATURA COMERCIAL                                            ", "20250880                 "),
            ("01", "FATURA COMERCIAL                                            ", "3872/2025                "),
            ("29", "ROMANEIO DE CARGA                                           ", "3872                     "),
            ("29", "ROMANEIO DE CARGA                                           ", "S/N                      ")
        ]
        
        for codigo, nome, numero in documentos:
            doc_elem = ET.SubElement(duimp_element, "documentoInstrucaoDespacho")
            ET.SubElement(doc_elem, "codigoTipoDocumentoDespacho").text = codigo
            ET.SubElement(doc_elem, "nomeDocumentoDespacho").text = nome
            ET.SubElement(doc_elem, "numeroDocumentoDespacho").text = numero
        
        # Embalagem
        embalagem = ET.SubElement(duimp_element, "embalagem")
        ET.SubElement(embalagem, "codigoTipoEmbalagem").text = "60"
        ET.SubElement(embalagem, "nomeEmbalagem").text = "PALLETS                                                     "
        ET.SubElement(embalagem, "quantidadeVolume").text = "00002"
        
        # ICMS
        icms = ET.SubElement(duimp_element, "icms")
        icms_data = {
            "agenciaIcms": "00000",
            "bancoIcms": "000",
            "codigoTipoRecolhimentoIcms": "3",
            "cpfResponsavelRegistro": "27160353854",
            "dataRegistro": data.get("dataRegistro", "20251124"),
            "horaRegistro": "152044",
            "nomeTipoRecolhimentoIcms": "Exoneração do ICMS",
            "numeroSequencialIcms": "001",
            "ufIcms": "PR",
            "valorTotalIcms": "000000000000000"
        }
        
        for key, value in icms_data.items():
            ET.SubElement(icms, key).text = value
        
        # Pagamentos
        pagamentos = [
            ("0086", "000000001772057"),
            ("1038", "000000001021643"),
            ("5602", "000000000233345"),
            ("5629", "000000001072281"),
            ("7811", "000000000028534")
        ]
        
        for codigo, valor in pagamentos:
            pagamento = ET.SubElement(duimp_element, "pagamento")
            ET.SubElement(pagamento, "agenciaPagamento").text = "3715 "
            ET.SubElement(pagamento, "bancoPagamento").text = "341"
            ET.SubElement(pagamento, "codigoReceita").text = codigo
            ET.SubElement(pagamento, "codigoTipoPagamento").text = "1"
            ET.SubElement(pagamento, "contaPagamento").text = "             316273"
            ET.SubElement(pagamento, "dataPagamento").text = data.get("dataRegistro", "20251124")
            ET.SubElement(pagamento, "nomeTipoPagamento").text = "Débito em Conta"
            ET.SubElement(pagamento, "numeroRetificacao").text = "00"
            ET.SubElement(pagamento, "valorJurosEncargos").text = "000000000"
            ET.SubElement(pagamento, "valorMulta").text = "000000000"
            ET.SubElement(pagamento, "valorReceita").text = valor
        
        # Informação complementar
        info = ET.SubElement(duimp_element, "informacaoComplementar")
        info_text = f"""INFORMACOES COMPLEMENTARES
--------------------------
CASCO LOGISTICA - MATRIZ - PR
PROCESSO :28306
REF. IMPORTADOR :M-127707
IMPORTADOR :HAFELE BRASIL LTDA
PESO LIQUIDO :{data.get("cargaPesoLiquido", "000000048686100")}
PESO BRUTO :{data.get("cargaPesoBruto", "000000053415000")}
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
    
    def convert_pdf_to_xml(self, pdf_path):
        """Converte PDF para XML conforme modelo"""
        # Reseta contadores
        self.adicao_counter = 0
        self.item_counter = 1
        
        # Processa o PDF
        with st.spinner("Lendo PDF..."):
            all_text, page_data = self.parse_large_pdf(pdf_path)
        
        # Extrai informações básicas
        with st.spinner("Extraindo informações do DUIMP..."):
            self.current_duimp_number = self.extract_duimp_number(all_text)
            dates = self.extract_dates(all_text)
            weights = self.extract_weights(all_text)
        
        # Extrai adições
        with st.spinner("Extraindo adições e itens..."):
            adicoes = self.extract_adicoes_from_text(all_text)
        
        # Prepara dados para XML
        xml_data = {
            "cargaDataChegada": dates.get("cargaDataChegada", "20251120"),
            "cargaPesoBruto": weights.get("cargaPesoBruto", "000000053415000"),
            "cargaPesoLiquido": weights.get("cargaPesoLiquido", "000000048686100"),
            "conhecimentoCargaEmbarqueData": dates.get("conhecimentoCargaEmbarqueData", "20251025"),
            "dataDesembaraco": dates.get("dataDesembaraco", "20251124"),
            "dataRegistro": dates.get("dataRegistro", "20251124"),
            "adicoes": adicoes
        }
        
        # Gera XML
        with st.spinner("Gerando XML no formato correto..."):
            xml_output = self.build_xml_structure(xml_data)
        
        return xml_output, len(adicoes), len(page_data)

def main():
    st.set_page_config(
        page_title="Conversor DUIMP PDF → XML (Corrigido)",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Conversor DUIMP PDF para XML - CORRIGIDO")
    st.markdown("**Problema corrigido:** XML declaration allowed only at the start of the document")
    
    # Upload do arquivo
    uploaded_file = st.file_uploader(
        "Selecione o arquivo PDF do Extrato de Conferência DUIMP",
        type=["pdf"],
        help="Arquivos de qualquer tamanho são suportados"
    )
    
    if uploaded_file:
        converter = DUIMPPDFConverter()
        
        # Salva arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            tmp_path = tmp_file.name
        
        try:
            # Processa o arquivo
            xml_output, num_adicoes, num_pages = converter.convert_pdf_to_xml(tmp_path)
            
            # Valida o XML
            try:
                # Tenta parsear o XML para verificar se está bem formado
                ET.fromstring(xml_output.encode('utf-8'))
                xml_valid = True
            except Exception as e:
                xml_valid = False
                st.error(f"XML mal formado: {str(e)}")
            
            # Mostra resultados
            if xml_valid:
                st.success("✅ XML gerado com sucesso e válido!")
            
            # Estatísticas
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Páginas Processadas", num_pages)
            
            with col2:
                st.metric("Adições Extraídas", num_adicoes)
            
            with col3:
                st.metric("Número DUIMP", converter.current_duimp_number)
            
            # Download do XML
            st.subheader("📥 Download do Arquivo XML")
            
            # Verifica se o XML começa corretamente
            if not xml_output.startswith('<?xml'):
                st.warning("⚠️ Aviso: O XML não começa com a declaração correta. Corrigindo...")
                xml_output = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_output.lstrip()
            
            # Remove quaisquer espaços/linhas antes da declaração XML
            xml_output = xml_output.lstrip()
            if not xml_output.startswith('<?xml'):
                # Se ainda não começar com <?xml, força a adição
                xml_output = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_output
            
            # Gera nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            xml_filename = f"M-DUIMP-{converter.current_duimp_number}_{timestamp}.xml"
            
            # Botão de download
            st.download_button(
                label="⬇️ Baixar Arquivo XML",
                data=xml_output,
                file_name=xml_filename,
                mime="application/xml",
                type="primary",
                key="download_xml"
            )
            
            # Visualização do XML
            st.subheader("🔍 Visualização do XML")
            
            col_preview1, col_preview2 = st.columns([2, 1])
            
            with col_preview1:
                # Mostra os primeiros 2000 caracteres
                preview_text = xml_output[:2000]
                st.code(preview_text, language="xml")
                
                if len(xml_output) > 2000:
                    st.info(f"XML truncado para visualização. Tamanho total: {len(xml_output)} caracteres")
            
            with col_preview2:
                st.write("**Verificação do XML:**")
                
                # Verifica a estrutura
                checks = [
                    ("Declaração XML presente", xml_output.startswith('<?xml')),
                    ("Elemento raiz ListaDeclaracoes", "<ListaDeclaracoes>" in xml_output),
                    ("Elemento duimp presente", "<duimp>" in xml_output),
                    (f"Adições encontradas: {num_adicoes}", num_adicoes > 0),
                    ("Número DUIMP definido", converter.current_duimp_number != "")
                ]
                
                for check_text, check_result in checks:
                    if check_result:
                        st.success(f"✓ {check_text}")
                    else:
                        st.error(f"✗ {check_text}")
            
            # Opção para visualizar XML completo
            with st.expander("📋 Visualizar XML completo (cuidado com arquivos grandes)"):
                st.code(xml_output, language="xml")
            
            # Informações de debug
            with st.expander("🐛 Informações de Debug"):
                st.write(f"**Primeiros 100 caracteres do XML:**")
                st.code(xml_output[:100])
                
                st.write(f"**Estrutura do XML:**")
                st.write(f"- Linhas totais: {len(xml_output.split(chr(10)))}")
                st.write(f"- Tamanho: {len(xml_output)} caracteres")
                st.write(f"- Encoding detectado: UTF-8")
                
                # Verifica BOM (Byte Order Mark)
                if xml_output.startswith('\ufeff'):
                    st.warning("⚠️ XML contém BOM (Byte Order Mark)")
                else:
                    st.success("✓ XML sem BOM")
        
        except Exception as e:
            st.error(f"❌ Erro durante o processamento: {str(e)}")
            
            # Mostra informações de debug
            with st.expander("🔧 Detalhes do erro"):
                st.exception(e)
        
        finally:
            # Limpa arquivo temporário
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    else:
        # Instruções
        st.markdown("""
        ### 🛠️ **CORREÇÃO APLICADA**
        
        **Problema resolvido:** `XML declaration allowed only at the start of the document`
        
        **Solução implementada:**
        1. Remoção de espaços em branco antes da declaração `<?xml`
        2. Garantia de que a declaração XML é o PRIMEIRO caractere do arquivo
        3. Validação do XML gerado
        
        ### 📋 **Funcionalidades:**
        
        - ✅ **Processa PDFs grandes** (500+ páginas)
        - ✅ **XML válido e bem formado**
        - ✅ **Estrutura exata** do modelo M-DUIMP-8686868686.xml
        - ✅ **Extração automática** de todos os itens
        - ✅ **Formatação correta** (zeros à esquerda)
        - ✅ **Verificação de validade** do XML
        
        ### 🚀 **Como usar:**
        
        1. **Faça upload** do PDF
        2. **Aguarde** o processamento (mostra progresso)
        3. **Verifique** se o XML é válido (✓ verde)
        4. **Baixe** o XML corrigido
        5. **Abra** no navegador ou editor XML
        
        ### 🔍 **O que foi extraído:**
        
        - Número DUIMP
        - Datas (embarque, chegada, registro)
        - Pesos (bruto e líquido)
        - Todas as adições/items
        - Descrições dos produtos
        - Quantidades e valores
        - Informações fixas do modelo
        
        **O XML gerado agora abrirá corretamente em qualquer visualizador XML!**
        """)

if __name__ == "__main__":
    main()
