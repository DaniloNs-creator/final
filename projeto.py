import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Conversor DUIMP PDF -> XML", layout="wide")

# --- CLASSES UTILITÁRIAS ---
class Utils:
    @staticmethod
    def format_money(value_str, length=15):
        """
        Formata valor monetário para o padrão XML (sem vírgula, preenchido com zeros à esquerda).
        Ex: '1.409,60' -> '000000000140960'
        """
        if not value_str: return "0" * length
        # Remove pontos de milhar e substitui vírgula decimal
        clean = value_str.replace('.', '').replace(',', '')
        return clean.zfill(length)

    @staticmethod
    def format_quantity(value_str, length=14):
        """
        Formata quantidades e pesos (5 casas decimais implícitas ou conforme XML).
        Remove pontos e vírgulas.
        """
        if not value_str: return "0" * length
        clean = re.sub(r'[^\d]', '', value_str)
        return clean.zfill(length)

    @staticmethod
    def clean_text(text):
        """Limpa espaços extras e quebras de linha"""
        if not text: return ""
        return " ".join(text.split()).upper()

    @staticmethod
    def extract_value_by_label(text_block, label_pattern):
        """Busca um valor numérico adjacente a um rótulo no texto"""
        match = re.search(label_pattern, text_block, re.MULTILINE)
        return match.group(1) if match else None

# --- NÚCLEO DE PROCESSAMENTO ---
class DuimpConverter:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.full_text = ""
        self.data = {
            "adicoes": [],
            "capa": {}
        }

    def extract_text(self):
        """Extrai todo o texto do PDF mantendo fluxo linear"""
        with pdfplumber.open(self.pdf_file) as pdf:
            text_content = []
            for page in pdf.pages:
                text_content.append(page.extract_text())
            self.full_text = "\n".join(text_content)
        return self.full_text

    def parse_data(self):
        text = self.full_text
        
        # --- 1. Extração da Capa (Dados Gerais) ---
        # Exemplo: Extração do número do processo ou identificação
        proc_match = re.search(r'PROCESSO #(\d+)', text)
        self.data['capa']['numero_processo'] = proc_match.group(1) if proc_match else "00000"
        
        # Tenta extrair Número da DUIMP (No PDF de exemplo aparece "TESTE DUIMP" ou números)
        duimp_match = re.search(r'DUIMP\s*[:#]?\s*(\d+)', text)
        self.data['capa']['numero_duimp'] = duimp_match.group(1) if duimp_match else "8686868686"

        # Totais (Frete, Seguro, FOB) - Busca no Resumo
        # Ex: "1.059,31 Total (R$)" sob SEGURO
        seguro_match = re.search(r'SEGURO.*?([\d\.,]+)\s+Total \(R\$\)', text, re.DOTALL)
        self.data['capa']['seguro_total_reais'] = seguro_match.group(1) if seguro_match else "0,00"

        frete_match = re.search(r'FRETE.*?([\d\.,]+)\s+NAO Total \(R\$\)', text, re.DOTALL)
        self.data['capa']['frete_total_reais'] = frete_match.group(1) if frete_match else "0,00"

        # --- 2. Extração das Adições (Iterando por 'ITENS DA DUIMP') ---
        # Divide o texto pelos blocos de itens
        item_blocks = re.split(r'ITENS DA DUIMP - (\d+)', text)
        
        # O split retorna: [intro, num_item_1, conteudo_1, num_item_2, conteudo_2...]
        # Ignoramos a intro (índice 0) e iteramos em pares (número, conteúdo)
        for i in range(1, len(item_blocks), 2):
            num_item = item_blocks[i]
            block = item_blocks[i+1]
            
            item_data = {
                "numero": num_item.zfill(3),
                "ncm": "00000000",
                "valor_mercadoria_reais": "0,00",
                "peso_liquido": "0",
                "quantidade": "0",
                "desc_mercadoria": "",
                "tributos": {}
            }

            # NCM (Geralmente na primeira linha do bloco do item)
            # Padrão: 3926.30.00
            ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', block)
            if ncm_match:
                item_data['ncm'] = ncm_match.group(1).replace('.', '')

            # Quantidade Estatística
            # Padrão: "433,82800 Qtde Unid. Estatística"
            qtd_match = re.search(r'([\d\.,]+)\s+Qtde Unid\. Estatística', block)
            if qtd_match:
                item_data['quantidade'] = qtd_match.group(1)

            # Peso Líquido
            # Padrão: "433,82800 Peso Líquido (KG)"
            peso_match = re.search(r'([\d\.,]+)\s+Peso Líquido \(KG\)', block)
            if peso_match:
                item_data['peso_liquido'] = peso_match.group(1)

            # Valor Total Condição de Venda (Reais)
            # Padrão: "8.729,79 Vlr Cond Venda (R$)"
            val_match = re.search(r'([\d\.,]+)\s+Vlr Cond Venda \(R\$\)', block)
            if val_match:
                item_data['valor_mercadoria_reais'] = val_match.group(1)

            # Descrição (Denominação do Produto)
            # Padrão: Linha após "DENOMINACAO DO PRODUTO"
            desc_match = re.search(r'DENOMINACAO DO PRODUTO\n(.*)', block)
            if desc_match:
                item_data['desc_mercadoria'] = desc_match.group(1).strip()

            # --- Extração de Tributos (II, IPI, PIS, COFINS) ---
            # A lógica busca o valor "A Recolher" dentro da seção de cada imposto no bloco do item
            
            # II
            ii_block = re.search(r'CALCULOS DOS TRIBUTOS - MERCADORIA.*?II(.*?)SIM Tributado', block, re.DOTALL)
            if ii_block:
                recolher = re.findall(r'([\d\.,]+)\s+Valor A Recolher', ii_block.group(1))
                item_data['tributos']['II'] = recolher[-1] if recolher else "0,00"
            
            # IPI
            ipi_block = re.search(r'IPI(.*?)SIM Tributado', block, re.DOTALL)
            if ipi_block:
                recolher = re.findall(r'([\d\.,]+)\s+Valor A Recolher', ipi_block.group(1))
                item_data['tributos']['IPI'] = recolher[-1] if recolher else "0,00"

            # PIS
            pis_block = re.search(r'PIS(.*?)SIM Tributado', block, re.DOTALL)
            if pis_block:
                recolher = re.findall(r'([\d\.,]+)\s+Valor A Recolher', pis_block.group(1))
                item_data['tributos']['PIS'] = recolher[-1] if recolher else "0,00"

            # COFINS
            cofins_block = re.search(r'COFINS(.*?)SIM Tributado', block, re.DOTALL)
            if cofins_block:
                recolher = re.findall(r'([\d\.,]+)\s+Valor A Recolher', cofins_block.group(1))
                item_data['tributos']['COFINS'] = recolher[-1] if recolher else "0,00"
            
            self.data['adicoes'].append(item_data)

    def build_xml(self):
        """Monta a árvore XML baseada estritamente no Layout Obrigatório do Projeto 01"""
        
        root = ET.Element("ListaDeclaracoes")
        duimp = ET.SubElement(root, "duimp")

        # --- SEÇÃO 1: ADIÇÕES ---
        for item in self.data['adicoes']:
            adicao = ET.SubElement(duimp, "adicao")
            
            # Acrescimo (Fixo conforme modelo ou extraído se houver lógica)
            acrescimo = ET.SubElement(adicao, "acrescimo")
            ET.SubElement(acrescimo, "codigoAcrescimo").text = "17"
            ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
            ET.SubElement(acrescimo, "moedaNegociadaCodigo").text = "978"
            ET.SubElement(acrescimo, "moedaNegociadaNome").text = "EURO/COM.EUROPEIA"
            ET.SubElement(acrescimo, "valorMoedaNegociada").text = "0"*15 
            ET.SubElement(acrescimo, "valorReais").text = "0"*15

            # CIDE (Zeros conforme modelo)
            ET.SubElement(adicao, "cideValorAliquotaEspecifica").text = "0"*11
            ET.SubElement(adicao, "cideValorDevido").text = "0"*15
            ET.SubElement(adicao, "cideValorRecolher").text = "0"*15
            
            ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
            ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
            
            # COFINS
            cofins_val = Utils.format_money(item['tributos'].get('COFINS', '0,00'))
            ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965"
            ET.SubElement(adicao, "cofinsAliquotaEspecificaQuantidadeUnidade").text = "0"*9
            ET.SubElement(adicao, "cofinsAliquotaEspecificaValor").text = "0"*10
            ET.SubElement(adicao, "cofinsAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "cofinsAliquotaValorDevido").text = cofins_val
            ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = cofins_val

            # Condição de Venda
            ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
            ET.SubElement(adicao, "condicaoVendaLocal").text = "BRUGNERA"
            ET.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
            ET.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"
            ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
            ET.SubElement(adicao, "condicaoVendaMoedaNome").text = "EURO/COM.EUROPEIA"
            ET.SubElement(adicao, "condicaoVendaValorMoeda").text = "0"*15
            ET.SubElement(adicao, "condicaoVendaValorReais").text = Utils.format_money(item['valor_mercadoria_reais'])

            # Dados Cambiais
            ET.SubElement(adicao, "dadosCambiaisCoberturaCambialCodigo").text = "1"
            ET.SubElement(adicao, "dadosCambiaisCoberturaCambialNome").text = "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"
            ET.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraCodigo").text = "00"
            ET.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraNome").text = "N/I"
            ET.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaCodigo").text = "00"
            ET.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaNome").text = "N/I"
            ET.SubElement(adicao, "dadosCambiaisValorRealCambio").text = "0"*15

            # Dados Carga
            ET.SubElement(adicao, "dadosCargaPaisProcedenciaCodigo").text = "000"
            ET.SubElement(adicao, "dadosCargaUrfEntradaCodigo").text = "0000000"
            ET.SubElement(adicao, "dadosCargaViaTransporteCodigo").text = "01"
            ET.SubElement(adicao, "dadosCargaViaTransporteNome").text = "MARÍTIMA"

            # Dados Mercadoria
            ET.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
            ET.SubElement(adicao, "dadosMercadoriaCodigoNaladiNCCA").text = "0000000"
            ET.SubElement(adicao, "dadosMercadoriaCodigoNaladiSH").text = "00000000"
            ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item['ncm']
            ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
            ET.SubElement(adicao, "dadosMercadoriaDescricaoTipoCertificado").text = "Sem Certificado"
            ET.SubElement(adicao, "dadosMercadoriaIndicadorTipoCertificado").text = "1"
            ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaQuantidade").text = Utils.format_quantity(item['quantidade'])
            ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaUnidade").text = "QUILOGRAMA LIQUIDO"
            ET.SubElement(adicao, "dadosMercadoriaNomeNcm").text = item['desc_mercadoria'][:60] # Truncar se necessário
            ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = Utils.format_quantity(item['peso_liquido'])

            # DCR
            ET.SubElement(adicao, "dcrCoeficienteReducao").text = "00000"
            ET.SubElement(adicao, "dcrIdentificacao").text = "00000000"
            ET.SubElement(adicao, "dcrValorDevido").text = "0"*15
            ET.SubElement(adicao, "dcrValorDolar").text = "0"*15
            ET.SubElement(adicao, "dcrValorReal").text = "0"*15
            ET.SubElement(adicao, "dcrValorRecolher").text = "0"*15

            # Fornecedor
            ET.SubElement(adicao, "fornecedorCidade").text = "BRUGNERA"
            ET.SubElement(adicao, "fornecedorLogradouro").text = "VIALE EUROPA"
            ET.SubElement(adicao, "fornecedorNome").text = "ITALIANA FERRAMENTA S.R.L."
            ET.SubElement(adicao, "fornecedorNumero").text = "17"

            # Frete Adição (Usando placeholder ou pro-rata se necessário, aqui fixo conforme modelo)
            ET.SubElement(adicao, "freteMoedaNegociadaCodigo").text = "978"
            ET.SubElement(adicao, "freteMoedaNegociadaNome").text = "EURO/COM.EUROPEIA"
            ET.SubElement(adicao, "freteValorMoedaNegociada").text = "0"*15
            ET.SubElement(adicao, "freteValorReais").text = "0"*15

            # II
            ii_val = Utils.format_money(item['tributos'].get('II', '0,00'))
            ET.SubElement(adicao, "iiAcordoTarifarioTipoCodigo").text = "0"
            ET.SubElement(adicao, "iiAliquotaAcordo").text = "00000"
            ET.SubElement(adicao, "iiAliquotaAdValorem").text = "01800"
            ET.SubElement(adicao, "iiAliquotaPercentualReducao").text = "00000"
            ET.SubElement(adicao, "iiAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "iiAliquotaValorCalculado").text = ii_val
            ET.SubElement(adicao, "iiAliquotaValorDevido").text = ii_val
            ET.SubElement(adicao, "iiAliquotaValorRecolher").text = ii_val
            ET.SubElement(adicao, "iiAliquotaValorReduzido").text = "0"*15
            ET.SubElement(adicao, "iiBaseCalculo").text = "0"*15 # Calcular se necessário
            ET.SubElement(adicao, "iiFundamentoLegalCodigo").text = "00"
            ET.SubElement(adicao, "iiMotivoAdmissaoTemporariaCodigo").text = "00"
            ET.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
            ET.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"

            # IPI
            ipi_val = Utils.format_money(item['tributos'].get('IPI', '0,00'))
            ET.SubElement(adicao, "ipiAliquotaAdValorem").text = "00325"
            ET.SubElement(adicao, "ipiAliquotaEspecificaCapacidadeRecipciente").text = "00000"
            ET.SubElement(adicao, "ipiAliquotaEspecificaQuantidadeUnidadeMedida").text = "0"*9
            ET.SubElement(adicao, "ipiAliquotaEspecificaTipoRecipienteCodigo").text = "00"
            ET.SubElement(adicao, "ipiAliquotaEspecificaValorUnidadeMedida").text = "0"*10
            ET.SubElement(adicao, "ipiAliquotaNotaComplementarTIPI").text = "00"
            ET.SubElement(adicao, "ipiAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "ipiAliquotaValorDevido").text = ipi_val
            ET.SubElement(adicao, "ipiAliquotaValorRecolher").text = ipi_val
            ET.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "4"
            ET.SubElement(adicao, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"

            # Mercadoria Detalhe
            merc = ET.SubElement(adicao, "mercadoria")
            ET.SubElement(merc, "descricaoMercadoria").text = Utils.clean_text(item['desc_mercadoria'])
            ET.SubElement(merc, "numeroSequencialItem").text = "01"
            ET.SubElement(merc, "quantidade").text = Utils.format_quantity(item['quantidade'])
            ET.SubElement(merc, "unidadeMedida").text = "PECA"
            ET.SubElement(merc, "valorUnitario").text = "0"*20 # Calcular Unitário

            # Tags Finais da Adição
            ET.SubElement(adicao, "numeroAdicao").text = item['numero']
            ET.SubElement(adicao, "numeroDUIMP").text = self.data['capa']['numero_duimp']
            ET.SubElement(adicao, "numeroLI").text = "0000000000"
            
            ET.SubElement(adicao, "paisAquisicaoMercadoriaCodigo").text = "386"
            ET.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = "ITALIA"
            ET.SubElement(adicao, "paisOrigemMercadoriaCodigo").text = "386"
            ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = "ITALIA"

            # PIS
            pis_val = Utils.format_money(item['tributos'].get('PIS', '0,00'))
            ET.SubElement(adicao, "pisCofinsBaseCalculoAliquotaICMS").text = "00000"
            ET.SubElement(adicao, "pisCofinsBaseCalculoFundamentoLegalCodigo").text = "00"
            ET.SubElement(adicao, "pisCofinsBaseCalculoPercentualReducao").text = "00000"
            ET.SubElement(adicao, "pisCofinsBaseCalculoValor").text = "0"*15
            ET.SubElement(adicao, "pisCofinsFundamentoLegalReducaoCodigo").text = "00"
            ET.SubElement(adicao, "pisCofinsRegimeTributacaoCodigo").text = "1"
            ET.SubElement(adicao, "pisCofinsRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
            ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
            ET.SubElement(adicao, "pisPasepAliquotaEspecificaQuantidadeUnidade").text = "0"*9
            ET.SubElement(adicao, "pisPasepAliquotaEspecificaValor").text = "0"*10
            ET.SubElement(adicao, "pisPasepAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "pisPasepAliquotaValorDevido").text = pis_val
            ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = pis_val

            # ICMS
            ET.SubElement(adicao, "icmsBaseCalculoValor").text = "0"*15
            ET.SubElement(adicao, "icmsBaseCalculoAliquota").text = "01800"
            ET.SubElement(adicao, "icmsBaseCalculoValorImposto").text = "0"*15
            ET.SubElement(adicao, "icmsBaseCalculoValorDiferido").text = "0"*15

            # CBS/IBS (Reforma Tributária - placeholders)
            ET.SubElement(adicao, "cbsIbsCst").text = "000"
            ET.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
            ET.SubElement(adicao, "cbsBaseCalculoValor").text = "0"*15
            ET.SubElement(adicao, "cbsBaseCalculoAliquota").text = "00090"
            ET.SubElement(adicao, "cbsBaseCalculoAliquotaReducao").text = "00000"
            ET.SubElement(adicao, "cbsBaseCalculoValorImposto").text = "0"*15
            ET.SubElement(adicao, "ibsBaseCalculoValor").text = "0"*15
            ET.SubElement(adicao, "ibsBaseCalculoAliquota").text = "00010"
            ET.SubElement(adicao, "ibsBaseCalculoAliquotaReducao").text = "00000"
            ET.SubElement(adicao, "ibsBaseCalculoValorImposto").text = "0"*15

            ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
            ET.SubElement(adicao, "seguroMoedaNegociadaCodigo").text = "220"
            ET.SubElement(adicao, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
            ET.SubElement(adicao, "seguroValorMoedaNegociada").text = "0"*15
            ET.SubElement(adicao, "seguroValorReais").text = "0"*15
            ET.SubElement(adicao, "sequencialRetificacao").text = "00"
            ET.SubElement(adicao, "valorMultaARecolher").text = "0"*15
            ET.SubElement(adicao, "valorMultaARecolherAjustado").text = "0"*15
            ET.SubElement(adicao, "valorReaisFreteInternacional").text = "0"*15
            ET.SubElement(adicao, "valorReaisSeguroInternacional").text = "0"*15
            ET.SubElement(adicao, "valorTotalCondicaoVenda").text = "0"*15
            ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

        # --- SEÇÃO 2: DADOS GERAIS DUIMP ---
        armazem = ET.SubElement(duimp, "armazem")
        ET.SubElement(armazem, "nomeArmazem").text = "TCP"
        
        ET.SubElement(duimp, "armazenamentoRecintoAduaneiroCodigo").text = "9801303"
        ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
        ET.SubElement(duimp, "armazenamentoSetor").text = "002"
        ET.SubElement(duimp, "canalSelecaoParametrizada").text = "001"
        ET.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
        ET.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importação Própria"
        ET.SubElement(duimp, "cargaDataChegada").text = "20251120"
        ET.SubElement(duimp, "cargaNumeroAgente").text = "N/I"
        ET.SubElement(duimp, "cargaPaisProcedenciaCodigo").text = "386"
        ET.SubElement(duimp, "cargaPaisProcedenciaNome").text = "ITALIA"
        ET.SubElement(duimp, "cargaPesoBruto").text = "000000053415000"
        ET.SubElement(duimp, "cargaPesoLiquido").text = "000000048686100"
        ET.SubElement(duimp, "cargaUrfEntradaCodigo").text = "0917800"
        ET.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
        
        # Conhecimento Carga (Dados Fixos ou extraídos)
        ET.SubElement(duimp, "conhecimentoCargaEmbarqueData").text = "20251025"
        ET.SubElement(duimp, "conhecimentoCargaEmbarqueLocal").text = "GENOVA"
        ET.SubElement(duimp, "conhecimentoCargaId").text = "CEMERCANTE31032008"
        ET.SubElement(duimp, "conhecimentoCargaIdMaster").text = "162505352452915"
        ET.SubElement(duimp, "conhecimentoCargaTipoCodigo").text = "12"
        ET.SubElement(duimp, "conhecimentoCargaTipoNome").text = "HBL - House Bill of Lading"
        ET.SubElement(duimp, "conhecimentoCargaUtilizacao").text = "1"
        ET.SubElement(duimp, "conhecimentoCargaUtilizacaoNome").text = "Total"
        
        ET.SubElement(duimp, "dataDesembaraco").text = "20251124"
        ET.SubElement(duimp, "dataRegistro").text = "20251124"
        ET.SubElement(duimp, "documentoChegadaCargaCodigoTipo").text = "1"
        ET.SubElement(duimp, "documentoChegadaCargaNome").text = "Manifesto da Carga"
        ET.SubElement(duimp, "documentoChegadaCargaNumero").text = "1625502058594"

        # Documentos Instrutivos
        for cod, nome, num in [("28", "CONHECIMENTO DE CARGA", "372250376737202501"), ("01", "FATURA COMERCIAL", "20250880")]:
            doc_node = ET.SubElement(duimp, "documentoInstrucaoDespacho")
            ET.SubElement(doc_node, "codigoTipoDocumentoDespacho").text = cod
            ET.SubElement(doc_node, "nomeDocumentoDespacho").text = nome.ljust(60)
            ET.SubElement(doc_node, "numeroDocumentoDespacho").text = num.ljust(25)

        # Embalagem
        emb = ET.SubElement(duimp, "embalagem")
        ET.SubElement(emb, "codigoTipoEmbalagem").text = "60"
        ET.SubElement(emb, "nomeEmbalagem").text = "PALLETS".ljust(60)
        ET.SubElement(emb, "quantidadeVolume").text = "00002"

        # Fretes Totais (Capa)
        ET.SubElement(duimp, "freteCollect").text = "0"*15
        ET.SubElement(duimp, "freteEmTerritorioNacional").text = "0"*15
        ET.SubElement(duimp, "freteMoedaNegociadaCodigo").text = "978"
        ET.SubElement(duimp, "freteMoedaNegociadaNome").text = "EURO/COM.EUROPEIA"
        ET.SubElement(duimp, "fretePrepaid").text = "0"*15
        ET.SubElement(duimp, "freteTotalDolares").text = "0"*15
        ET.SubElement(duimp, "freteTotalMoeda").text = "00000"
        ET.SubElement(duimp, "freteTotalReais").text = Utils.format_money(self.data['capa'].get('frete_total_reais', '0'))

        # ICMS Capa
        icms_node = ET.SubElement(duimp, "icms")
        ET.SubElement(icms_node, "agenciaIcms").text = "00000"
        ET.SubElement(icms_node, "bancoIcms").text = "000"
        ET.SubElement(icms_node, "codigoTipoRecolhimentoIcms").text = "3"
        ET.SubElement(icms_node, "cpfResponsavelRegistro").text = "27160353854"
        ET.SubElement(icms_node, "dataRegistro").text = "20251125"
        ET.SubElement(icms_node, "horaRegistro").text = "152044"
        ET.SubElement(icms_node, "nomeTipoRecolhimentoIcms").text = "Exoneração do ICMS"
        ET.SubElement(icms_node, "numeroSequencialIcms").text = "001"
        ET.SubElement(icms_node, "ufIcms").text = "PR"
        ET.SubElement(icms_node, "valorTotalIcms").text = "0"*15

        # Importador
        ET.SubElement(duimp, "importadorCodigoTipo").text = "1"
        ET.SubElement(duimp, "importadorCpfRepresentanteLegal").text = "27160353854"
        ET.SubElement(duimp, "importadorEnderecoBairro").text = "JARDIM PRIMAVERA"
        ET.SubElement(duimp, "importadorEnderecoCep").text = "83302000"
        ET.SubElement(duimp, "importadorEnderecoComplemento").text = "CONJ: 6 E 7;"
        ET.SubElement(duimp, "importadorEnderecoLogradouro").text = "JOAO LEOPOLDO JACOMEL"
        ET.SubElement(duimp, "importadorEnderecoMunicipio").text = "PIRAQUARA"
        ET.SubElement(duimp, "importadorEnderecoNumero").text = "4459"
        ET.SubElement(duimp, "importadorEnderecoUf").text = "PR"
        ET.SubElement(duimp, "importadorNome").text = "HAFELE BRASIL LTDA"
        ET.SubElement(duimp, "importadorNomeRepresentanteLegal").text = "PAULO HENRIQUE LEITE FERREIRA"
        ET.SubElement(duimp, "importadorNumero").text = "02473058000188"
        ET.SubElement(duimp, "importadorNumeroTelefone").text = "41  30348150"
        ET.SubElement(duimp, "informacaoComplementar").text = "INFORMACOES COMPLEMENTARES..."

        # Totais Finais
        ET.SubElement(duimp, "localDescargaTotalDolares").text = "0"*15
        ET.SubElement(duimp, "localDescargaTotalReais").text = "0"*15
        ET.SubElement(duimp, "localEmbarqueTotalDolares").text = "0"*15
        ET.SubElement(duimp, "localEmbarqueTotalReais").text = "0"*15
        ET.SubElement(duimp, "modalidadeDespachoCodigo").text = "1"
        ET.SubElement(duimp, "modalidadeDespachoNome").text = "Normal"
        ET.SubElement(duimp, "numeroDUIMP").text = self.data['capa']['numero_duimp']
        ET.SubElement(duimp, "operacaoFundap").text = "N"

        # Pagamentos
        pag = ET.SubElement(duimp, "pagamento")
        ET.SubElement(pag, "agenciaPagamento").text = "3715 "
        ET.SubElement(pag, "bancoPagamento").text = "341"
        ET.SubElement(pag, "codigoReceita").text = "0086"
        ET.SubElement(pag, "codigoTipoPagamento").text = "1"
        ET.SubElement(pag, "contaPagamento").text = "             316273"
        ET.SubElement(pag, "dataPagamento").text = "20251124"
        ET.SubElement(pag, "nomeTipoPagamento").text = "Débito em Conta"
        ET.SubElement(pag, "numeroRetificacao").text = "00"
        ET.SubElement(pag, "valorJurosEncargos").text = "0"*9
        ET.SubElement(pag, "valorMulta").text = "0"*9
        ET.SubElement(pag, "valorReceita").text = "0"*15

        # Rodapé
        ET.SubElement(duimp, "seguroMoedaNegociadaCodigo").text = "220"
        ET.SubElement(duimp, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
        ET.SubElement(duimp, "seguroTotalDolares").text = "0"*15
        ET.SubElement(duimp, "seguroTotalMoedaNegociada").text = "0"*15
        ET.SubElement(duimp, "seguroTotalReais").text = Utils.format_money(self.data['capa'].get('seguro_total_reais', '0'))
        ET.SubElement(duimp, "sequencialRetificacao").text = "00"
        ET.SubElement(duimp, "situacaoEntregaCarga").text = "ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE EXONERACAO DO ICMS"
        ET.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
        ET.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
        ET.SubElement(duimp, "totalAdicoes").text = str(len(self.data['adicoes'])).zfill(3)
        ET.SubElement(duimp, "urfDespachoCodigo").text = "0917800"
        ET.SubElement(duimp, "urfDespachoNome").text = "PORTO DE PARANAGUA"
        ET.SubElement(duimp, "valorTotalMultaARecolherAjustado").text = "0"*15
        ET.SubElement(duimp, "viaTransporteCodigo").text = "01"
        ET.SubElement(duimp, "viaTransporteMultimodal").text = "N"
        ET.SubElement(duimp, "viaTransporteNome").text = "MARÍTIMA"
        ET.SubElement(duimp, "viaTransporteNomeTransportador").text = "MAERSK A/S"
        ET.SubElement(duimp, "viaTransporteNomeVeiculo").text = "MAERSK MEMPHIS"
        ET.SubElement(duimp, "viaTransportePaisTransportadorCodigo").text = "741"
        ET.SubElement(duimp, "viaTransportePaisTransportadorNome").text = "CINGAPURA"

        # Pretty Print
        xml_str = ET.tostring(root, encoding='utf-8')
        parsed = minidom.parseString(xml_str)
        return parsed.toprettyxml(indent="    ")

# --- INTERFACE STREAMLIT ---
st.title("📄 Extrator Profissional DUIMP: PDF -> XML")
st.markdown("Importe o Extrato de Conferência Padrão para gerar o XML no layout obrigatório.")

uploaded_file = st.file_uploader("Selecione o arquivo PDF", type="pdf")

if uploaded_file is not None:
    try:
        with st.spinner('Analisando documento e extraindo dados...'):
            converter = DuimpConverter(uploaded_file)
            
            # 1. Extração
            raw_text = converter.extract_text()
            
            # 2. Parsing (Regex)
            converter.parse_data()
            
            # 3. Geração XML
            xml_output = converter.build_xml()
            
            st.success(f"XML Gerado! Processadas {len(converter.data['adicoes'])} adições.")
            
            # Botão de Download
            st.download_button(
                label="📥 Baixar XML (M-DUIMP-Formatado.xml)",
                data=xml_output,
                file_name=f"M-DUIMP-{converter.data['capa']['numero_duimp']}.xml",
                mime="application/xml"
            )
            
            # Preview (Apenas primeiras linhas)
            with st.expander("Visualizar Preview do XML"):
                st.code(xml_output[:3000] + "\n...", language='xml')

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
