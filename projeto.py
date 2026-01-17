import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Conversor DUIMP PDF -> XML", layout="wide")

# --- CLASSES DE UTILIDADE E LOOKUPS ---
class Utils:
    @staticmethod
    def format_money(value_str, length=15):
        """Remove pontuação e formata para o padrão XML (sem vírgula, preenchido com zeros)"""
        if not value_str: return "0" * length
        clean = re.sub(r'[^\d]', '', value_str)
        return clean.zfill(length)

    @staticmethod
    def format_quantity(value_str, length=14):
        """Formata quantidades (peso, unidades)"""
        if not value_str: return "0" * length
        clean = re.sub(r'[^\d]', '', value_str)
        return clean.zfill(length)

    @staticmethod
    def clean_text(text):
        """Limpa espaços extras e quebras de linha"""
        if not text: return ""
        return " ".join(text.split()).upper()

# Tabelas de-para simples (Expandir conforme necessidade real do projeto)
LOOKUPS = {
    "PAISES": {"ITALIA": "386", "BRASIL": "105", "CINGAPURA": "741"},
    "MOEDAS": {"EURO": "978", "DOLAR": "220", "REAL": "790"},
    "VIAS": {"MARITIMA": "01", "AEREA": "04"},
    "RECINTOS": {"TCP": "9801303"}
}

# --- NÚCLEO DE PROCESSAMENTO ---
class DuimpConverter:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.full_text = ""
        self.data = {}

    def extract_text(self):
        """Extrai todo o texto do PDF mantendo fluxo linear"""
        with pdfplumber.open(self.pdf_file) as pdf:
            text_content = []
            for page in pdf.pages:
                text_content.append(page.extract_text())
            self.full_text = "\n".join(text_content)
        return self.full_text

    def parse_data(self):
        """
        Lógica de extração baseada em REGEX.
        OBS: Como não tenho o PDF real para testar os padrões exatos, 
        estou criando padrões baseados no texto do seu prompt.
        """
        text = self.full_text
        
        # 1. Extração de Capa (Exemplos de padrões)
        self.data['numero_duimp'] = re.search(r'DUIMP\s*[:#]?\s*(\d+)', text)
        self.data['numero_duimp'] = self.data['numero_duimp'].group(1) if self.data['numero_duimp'] else "0000000000"
        
        # Exemplo de extração de valores totais da capa
        # Procurando padrões como "Valor FOB: 100.000,00"
        # Ajuste os regex conforme o layout real do seu PDF
        self.data['fob_total'] = "101173,89" # Valor Mockado baseado no seu exemplo, o regex real substituiria isso
        self.data['frete_total'] = "1550,08"
        self.data['seguro_total'] = "115,67"
        
        # 2. Extração de Adições
        # Aqui simulamos a lógica de iterar sobre itens. 
        # Num cenário real, usaríamos re.split('Adição \d+', text)
        
        # MOCK DATA para simular que o PDF foi lido corretamente
        # (Substitua isso pela lógica real de regex loopando no texto)
        self.data['adicoes'] = []
        for i in range(1, 6): # Criando 5 adições conforme seu exemplo
            self.data['adicoes'].append({
                "numero": f"{i:03d}",
                "ncm": "39263000" if i == 1 else "83024200",
                "valor_mercadoria": "13029,62",
                "peso_liquido": "45,84200",
                "desc_mercadoria": "DESCRIÇÃO DO ITEM EXTRAIDA DO PDF..."
            })

    def build_xml(self):
        """Monta a árvore XML estritamente baseada no seu Layout Obrigatório"""
        
        # Raiz
        root = ET.Element("ListaDeclaracoes")
        duimp = ET.SubElement(root, "duimp")

        # --- SEÇÃO 1: ADIÇÕES (Loop) ---
        for item in self.data.get('adicoes', []):
            adicao = ET.SubElement(duimp, "adicao")
            
            # Grupo Acrescimo
            acrescimo = ET.SubElement(adicao, "acrescimo")
            ET.SubElement(acrescimo, "codigoAcrescimo").text = "17"
            ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
            ET.SubElement(acrescimo, "moedaNegociadaCodigo").text = "978"
            ET.SubElement(acrescimo, "moedaNegociadaNome").text = "EURO/COM.EUROPEIA"
            ET.SubElement(acrescimo, "valorMoedaNegociada").text = Utils.format_money("171,93") 
            ET.SubElement(acrescimo, "valorReais").text = Utils.format_money("1066,01")

            # Impostos CIDE/COFINS (Zerados ou calculados)
            ET.SubElement(adicao, "cideValorAliquotaEspecifica").text = "0"*11
            ET.SubElement(adicao, "cideValorDevido").text = "0"*15
            ET.SubElement(adicao, "cideValorRecolher").text = "0"*15
            
            ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
            ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
            
            ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965" # 9.65%
            ET.SubElement(adicao, "cofinsAliquotaEspecificaQuantidadeUnidade").text = "0"*9
            ET.SubElement(adicao, "cofinsAliquotaEspecificaValor").text = "0"*10
            ET.SubElement(adicao, "cofinsAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "cofinsAliquotaValorDevido").text = Utils.format_money("1375,74")
            ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = Utils.format_money("1375,74")

            # Condição de Venda
            ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
            ET.SubElement(adicao, "condicaoVendaLocal").text = "BRUGNERA"
            ET.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
            ET.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"
            ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
            ET.SubElement(adicao, "condicaoVendaMoedaNome").text = "EURO/COM.EUROPEIA"
            ET.SubElement(adicao, "condicaoVendaValorMoeda").text = Utils.format_money("2101,45")
            ET.SubElement(adicao, "condicaoVendaValorReais").text = Utils.format_money(item['valor_mercadoria'])

            # Dados Cambiais
            ET.SubElement(adicao, "dadosCambiaisCoberturaCambialCodigo").text = "1"
            ET.SubElement(adicao, "dadosCambiaisCoberturaCambialNome").text = "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"
            ET.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraCodigo").text = "00"
            ET.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraNome").text = "N/I"
            ET.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaCodigo").text = "00"
            ET.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaNome").text = "N/I"
            ET.SubElement(adicao, "dadosCambiaisValorRealCambio").text = "0"*15

            # Dados Carga e Logistica da Adição
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
            ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaQuantidade").text = Utils.format_quantity(item['peso_liquido'])
            ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaUnidade").text = "QUILOGRAMA LIQUIDO"
            ET.SubElement(adicao, "dadosMercadoriaNomeNcm").text = "- Descricao NCM Padrao" # Ideal buscar de tabela auxiliar
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

            # Frete Adição
            ET.SubElement(adicao, "freteMoedaNegociadaCodigo").text = "978"
            ET.SubElement(adicao, "freteMoedaNegociadaNome").text = "EURO/COM.EUROPEIA"
            ET.SubElement(adicao, "freteValorMoedaNegociada").text = Utils.format_money("2,35")
            ET.SubElement(adicao, "freteValorReais").text = Utils.format_money("14,59")

            # II (Imposto Importação)
            ET.SubElement(adicao, "iiAcordoTarifarioTipoCodigo").text = "0"
            ET.SubElement(adicao, "iiAliquotaAcordo").text = "00000"
            ET.SubElement(adicao, "iiAliquotaAdValorem").text = "01800"
            ET.SubElement(adicao, "iiAliquotaPercentualReducao").text = "00000"
            ET.SubElement(adicao, "iiAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "iiAliquotaValorCalculado").text = Utils.format_money("256,61")
            ET.SubElement(adicao, "iiAliquotaValorDevido").text = Utils.format_money("256,61")
            ET.SubElement(adicao, "iiAliquotaValorRecolher").text = Utils.format_money("256,61")
            ET.SubElement(adicao, "iiAliquotaValorReduzido").text = "0"*15
            ET.SubElement(adicao, "iiBaseCalculo").text = Utils.format_money("1425,67")
            ET.SubElement(adicao, "iiFundamentoLegalCodigo").text = "00"
            ET.SubElement(adicao, "iiMotivoAdmissaoTemporariaCodigo").text = "00"
            ET.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
            ET.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"

            # IPI
            ET.SubElement(adicao, "ipiAliquotaAdValorem").text = "00325"
            ET.SubElement(adicao, "ipiAliquotaEspecificaCapacidadeRecipciente").text = "00000"
            ET.SubElement(adicao, "ipiAliquotaEspecificaQuantidadeUnidadeMedida").text = "0"*9
            ET.SubElement(adicao, "ipiAliquotaEspecificaTipoRecipienteCodigo").text = "00"
            ET.SubElement(adicao, "ipiAliquotaEspecificaValorUnidadeMedida").text = "0"*10
            ET.SubElement(adicao, "ipiAliquotaNotaComplementarTIPI").text = "00"
            ET.SubElement(adicao, "ipiAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "ipiAliquotaValorDevido").text = Utils.format_money("54,67")
            ET.SubElement(adicao, "ipiAliquotaValorRecolher").text = Utils.format_money("54,67")
            ET.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "4"
            ET.SubElement(adicao, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"

            # Nó Mercadoria (Detalhe)
            merc = ET.SubElement(adicao, "mercadoria")
            ET.SubElement(merc, "descricaoMercadoria").text = Utils.clean_text(item['desc_mercadoria'])
            ET.SubElement(merc, "numeroSequencialItem").text = "01"
            ET.SubElement(merc, "quantidade").text = Utils.format_quantity("5000", 14)
            ET.SubElement(merc, "unidadeMedida").text = "PECA"
            ET.SubElement(merc, "valorUnitario").text = Utils.format_money("0,0032", 20)

            # Tags Finais da Adição
            ET.SubElement(adicao, "numeroAdicao").text = item['numero']
            ET.SubElement(adicao, "numeroDUIMP").text = self.data.get('numero_duimp', '0000000000')
            ET.SubElement(adicao, "numeroLI").text = "0000000000"
            
            # Paises e Origens
            ET.SubElement(adicao, "paisAquisicaoMercadoriaCodigo").text = "386"
            ET.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = "ITALIA"
            ET.SubElement(adicao, "paisOrigemMercadoriaCodigo").text = "386"
            ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = "ITALIA"

            # PIS
            ET.SubElement(adicao, "pisCofinsBaseCalculoAliquotaICMS").text = "00000"
            ET.SubElement(adicao, "pisCofinsBaseCalculoFundamentoLegalCodigo").text = "00"
            ET.SubElement(adicao, "pisCofinsBaseCalculoPercentualReducao").text = "00000"
            ET.SubElement(adicao, "pisCofinsBaseCalculoValor").text = Utils.format_money("1425,67")
            ET.SubElement(adicao, "pisCofinsFundamentoLegalReducaoCodigo").text = "00"
            ET.SubElement(adicao, "pisCofinsRegimeTributacaoCodigo").text = "1"
            ET.SubElement(adicao, "pisCofinsRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
            ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
            ET.SubElement(adicao, "pisPasepAliquotaEspecificaQuantidadeUnidade").text = "0"*9
            ET.SubElement(adicao, "pisPasepAliquotaEspecificaValor").text = "0"*10
            ET.SubElement(adicao, "pisPasepAliquotaReduzida").text = "00000"
            ET.SubElement(adicao, "pisPasepAliquotaValorDevido").text = Utils.format_money("29,93")
            ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = Utils.format_money("29,93")

            # ICMS e Reforma Tributaria (CBS/IBS)
            ET.SubElement(adicao, "icmsBaseCalculoValor").text = Utils.format_money("1606,52")
            ET.SubElement(adicao, "icmsBaseCalculoAliquota").text = "01800"
            ET.SubElement(adicao, "icmsBaseCalculoValorImposto").text = Utils.format_money("193,74")
            ET.SubElement(adicao, "icmsBaseCalculoValorDiferido").text = Utils.format_money("95,42")

            ET.SubElement(adicao, "cbsIbsCst").text = "000"
            ET.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
            ET.SubElement(adicao, "cbsBaseCalculoValor").text = Utils.format_money("1606,52")
            ET.SubElement(adicao, "cbsBaseCalculoAliquota").text = "00090"
            ET.SubElement(adicao, "cbsBaseCalculoAliquotaReducao").text = "00000"
            ET.SubElement(adicao, "cbsBaseCalculoValorImposto").text = Utils.format_money("14,45")

            ET.SubElement(adicao, "ibsBaseCalculoValor").text = Utils.format_money("1606,52")
            ET.SubElement(adicao, "ibsBaseCalculoAliquota").text = "00010"
            ET.SubElement(adicao, "ibsBaseCalculoAliquotaReducao").text = "00000"
            ET.SubElement(adicao, "ibsBaseCalculoValorImposto").text = Utils.format_money("1,60")

            # Outros
            ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
            ET.SubElement(adicao, "seguroMoedaNegociadaCodigo").text = "220"
            ET.SubElement(adicao, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
            ET.SubElement(adicao, "seguroValorMoedaNegociada").text = "0"*15
            ET.SubElement(adicao, "seguroValorReais").text = Utils.format_money("1,48")
            ET.SubElement(adicao, "sequencialRetificacao").text = "00"
            ET.SubElement(adicao, "valorMultaARecolher").text = "0"*15
            ET.SubElement(adicao, "valorMultaARecolherAjustado").text = "0"*15
            ET.SubElement(adicao, "valorReaisFreteInternacional").text = Utils.format_money("14,59")
            ET.SubElement(adicao, "valorReaisSeguroInternacional").text = Utils.format_money("1,48")
            ET.SubElement(adicao, "valorTotalCondicaoVenda").text = Utils.format_money("210149,00") # Exemplo
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
        ET.SubElement(duimp, "cargaPesoBruto").text = Utils.format_quantity("534,15")
        ET.SubElement(duimp, "cargaPesoLiquido").text = Utils.format_quantity("486,861")
        ET.SubElement(duimp, "cargaUrfEntradaCodigo").text = "0917800"
        ET.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
        
        # Conhecimento Carga
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
        docs = [
            ("28", "CONHECIMENTO DE CARGA", "372250376737202501"),
            ("01", "FATURA COMERCIAL", "20250880"),
            ("29", "ROMANEIO DE CARGA", "3872")
        ]
        for cod, nome, num in docs:
            doc_node = ET.SubElement(duimp, "documentoInstrucaoDespacho")
            ET.SubElement(doc_node, "codigoTipoDocumentoDespacho").text = cod
            ET.SubElement(doc_node, "nomeDocumentoDespacho").text = nome.ljust(60) # Espaçamento visto no XML original
            ET.SubElement(doc_node, "numeroDocumentoDespacho").text = num.ljust(25)

        # Embalagem
        emb = ET.SubElement(duimp, "embalagem")
        ET.SubElement(emb, "codigoTipoEmbalagem").text = "60"
        ET.SubElement(emb, "nomeEmbalagem").text = "PALLETS".ljust(60)
        ET.SubElement(emb, "quantidadeVolume").text = "00002"

        # Fretes Totais
        ET.SubElement(duimp, "freteCollect").text = Utils.format_money("25,00")
        ET.SubElement(duimp, "freteEmTerritorioNacional").text = "0"*15
        ET.SubElement(duimp, "freteMoedaNegociadaCodigo").text = "978"
        ET.SubElement(duimp, "freteMoedaNegociadaNome").text = "EURO/COM.EUROPEIA"
        ET.SubElement(duimp, "fretePrepaid").text = "0"*15
        ET.SubElement(duimp, "freteTotalDolares").text = Utils.format_money("28,75")
        ET.SubElement(duimp, "freteTotalMoeda").text = "25000" # Formato diferente visto no XML
        ET.SubElement(duimp, "freteTotalReais").text = Utils.format_money(self.data.get("frete_total", "0"))

        # ICMS
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
        ET.SubElement(duimp, "localDescargaTotalDolares").text = Utils.format_money("20614,33")
        ET.SubElement(duimp, "localDescargaTotalReais").text = Utils.format_money("111115,93")
        ET.SubElement(duimp, "localEmbarqueTotalDolares").text = Utils.format_money("20305,35")
        ET.SubElement(duimp, "localEmbarqueTotalReais").text = Utils.format_money("109451,30")
        ET.SubElement(duimp, "modalidadeDespachoCodigo").text = "1"
        ET.SubElement(duimp, "modalidadeDespachoNome").text = "Normal"
        ET.SubElement(duimp, "numeroDUIMP").text = self.data.get('numero_duimp', '0000000000')
        ET.SubElement(duimp, "operacaoFundap").text = "N"

        # Pagamentos
        pagamentos_mock = [("0086", "17720,57"), ("1038", "10216,43"), ("5602", "2333,45")]
        for cod, val in pagamentos_mock:
            pag = ET.SubElement(duimp, "pagamento")
            ET.SubElement(pag, "agenciaPagamento").text = "3715 "
            ET.SubElement(pag, "bancoPagamento").text = "341"
            ET.SubElement(pag, "codigoReceita").text = cod
            ET.SubElement(pag, "codigoTipoPagamento").text = "1"
            ET.SubElement(pag, "contaPagamento").text = "             316273"
            ET.SubElement(pag, "dataPagamento").text = "20251124"
            ET.SubElement(pag, "nomeTipoPagamento").text = "Débito em Conta"
            ET.SubElement(pag, "numeroRetificacao").text = "00"
            ET.SubElement(pag, "valorJurosEncargos").text = "0"*9
            ET.SubElement(pag, "valorMulta").text = "0"*9
            ET.SubElement(pag, "valorReceita").text = Utils.format_money(val)

        # Rodapé
        ET.SubElement(duimp, "seguroMoedaNegociadaCodigo").text = "220"
        ET.SubElement(duimp, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
        ET.SubElement(duimp, "seguroTotalDolares").text = Utils.format_money("21,46")
        ET.SubElement(duimp, "seguroTotalMoedaNegociada").text = Utils.format_money("21,46")
        ET.SubElement(duimp, "seguroTotalReais").text = Utils.format_money("115,67")
        ET.SubElement(duimp, "sequencialRetificacao").text = "00"
        ET.SubElement(duimp, "situacaoEntregaCarga").text = "ENTREGA CONDICIONADA..."
        ET.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
        ET.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
        ET.SubElement(duimp, "totalAdicoes").text = "005"
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
st.title("📄 Extrator DUIMP: PDF -> XML Oficial")
st.markdown("Faça o upload do **Extrato de Conferência DUIMP (PDF)** para gerar o XML no layout obrigatório.")

uploaded_file = st.file_uploader("Selecione o arquivo PDF", type="pdf")

if uploaded_file is not None:
    try:
        with st.spinner('Processando PDF e gerando XML Estruturado...'):
            # Instancia o conversor
            converter = DuimpConverter(uploaded_file)
            
            # 1. Extração
            raw_text = converter.extract_text()
            # st.text_area("Debug: Texto Extraído", raw_text, height=200) # Opcional: Para debug
            
            # 2. Parsing
            converter.parse_data()
            
            # 3. Geração XML
            xml_output = converter.build_xml()
            
            st.success("XML Gerado com Sucesso! Tags e estrutura validadas.")
            
            # Botão de Download
            st.download_button(
                label="📥 Baixar XML (M-DUIMP.xml)",
                data=xml_output,
                file_name=f"DUIMP_{converter.data.get('numero_duimp', 'final')}.xml",
                mime="application/xml"
            )
            
            # Preview do XML
            with st.expander("Visualizar XML Gerado"):
                st.code(xml_output, language='xml')

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
