import streamlit as st
import fitz  # PyMuPDF
from lxml import etree
import re
import io

# ==============================================================================
# 1. FUNÇÕES AUXILIARES DE FORMATAÇÃO SAP
# ==============================================================================

def fmt_sap(value, length=15, is_decimal=True):
    """
    Converte valores para o formato SAP (string numérica sem pontuação, com zeros à esquerda).
    Entrada: "1.066,01" -> Saída: "000000000106601"
    """
    if not value:
        return "0" * length
    
    # Remove caracteres não numéricos
    clean_val = re.sub(r'[^\d]', '', value)
    
    # Se o PDF trouxe "1066,01", o clean_val será "106601".
    # O SAP geralmente espera que os ultimos digitos sejam centavos implícitos.
    return clean_val.zfill(length)

def extract_field(pattern, text, default=""):
    """Busca um valor no texto usando Regex. Retorna default se não encontrar."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return default

# ==============================================================================
# 2. MOTOR DE PROCESSAMENTO (PDF -> ESTRUTURA DE DADOS)
# ==============================================================================

class SapDuimpProcessor:
    def __init__(self, pdf_bytes):
        self.doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        self.full_text = ""
        self.data = {
            "header": {},
            "adicoes": [],
            "pagamentos": [] # Lista para suportar múltiplos pagamentos
        }

    def process(self):
        # 1. Extração de Texto Otimizada (Concatena tudo para busca global)
        for page in self.doc:
            self.full_text += page.get_text("text") + "\n"

        # 2. Extração de Cabeçalho / Dados Gerais
        # Ajuste os REGEX abaixo conforme o layout visual exato do seu PDF
        self.data['header']['numeroDUIMP'] = extract_field(r"DUIMP\s*[:]\s*(\d+[\.\d]*)", self.full_text).replace('.', '')
        self.data['header']['importadorNome'] = extract_field(r"Importador\s*[:]\s*(.+?)\n", self.full_text)
        self.data['header']['pesoLiquido'] = extract_field(r"Peso Líquido Total\s*[:]\s*([\d,\.]+)", self.full_text)
        self.data['header']['pesoBruto'] = extract_field(r"Peso Bruto Total\s*[:]\s*([\d,\.]+)", self.full_text)
        
        # 3. Identificação e Loop de Adições
        # Divide o texto pelos blocos de Adição para processar itens individualmente
        # O Regex procura por "Adição n° X" ou similar
        parts = re.split(r"(?:Adição|Item)\s*n[º°]?\s*\d+", self.full_text)
        
        # A parte 0 geralmente é cabeçalho, as seguintes são adições
        if len(parts) > 1:
            for i, part in enumerate(parts[1:], start=1):
                adi = {}
                adi['numero'] = str(i).zfill(3)
                
                # Extração de campos específicos da adição
                adi['ncm'] = extract_field(r"NCM\s*[:]\s*(\d+)", part).replace('.', '')
                adi['valor_aduan'] = extract_field(r"Valor Aduaneiro\s*[:]\s*([\d,\.]+)", part)
                adi['incoterm'] = extract_field(r"Incoterm\s*[:]\s*([A-Z]{3})", part, default="FCA")
                adi['peso_liq_adi'] = extract_field(r"Peso Líquido\s*[:]\s*([\d,\.]+)", part)
                adi['qtd_estat'] = extract_field(r"Quantidade Estatística\s*[:]\s*([\d,\.]+)", part)
                
                # Exemplo: Pegando fornecedor dentro do bloco
                adi['fornecedor'] = extract_field(r"Fornecedor\s*[:]\s*(.+?)\n", part, default="FORNECEDOR PADRAO")
                
                self.data['adicoes'].append(adi)
        
        return self.data

# ==============================================================================
# 3. GERADOR DE XML (LAYOUT SAP OBRIGATÓRIO)
# ==============================================================================

def generate_sap_xml(data):
    # Raiz
    root = etree.Element("ListaDeclaracoes")
    duimp = etree.SubElement(root, "duimp")

    # --- BLOCO 1: ADIÇÕES (Loop Obrigatório) ---
    for item in data['adicoes']:
        adicao = etree.SubElement(duimp, "adicao")
        
        # 1.1 Acrescimo
        acr = etree.SubElement(adicao, "acrescimo")
        etree.SubElement(acr, "codigoAcrescimo").text = "17"
        etree.SubElement(acr, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        etree.SubElement(acr, "moedaNegociadaCodigo").text = "978"
        etree.SubElement(acr, "moedaNegociadaNome").text = "EURO/COM.EUROPEIA"
        etree.SubElement(acr, "valorMoedaNegociada").text = fmt_sap("17193") # Exemplo: extrair se possivel
        etree.SubElement(acr, "valorReais").text = fmt_sap("106601")

        # 1.2 Tributos e Vínculos
        etree.SubElement(adicao, "cideValorAliquotaEspecifica").text = "00000000000"
        etree.SubElement(adicao, "cideValorDevido").text = "000000000000000"
        etree.SubElement(adicao, "cideValorRecolher").text = "000000000000000"
        etree.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
        etree.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
        
        # COFINS
        etree.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965"
        etree.SubElement(adicao, "cofinsAliquotaEspecificaQuantidadeUnidade").text = "000000000"
        etree.SubElement(adicao, "cofinsAliquotaEspecificaValor").text = "0000000000"
        etree.SubElement(adicao, "cofinsAliquotaReduzida").text = "00000"
        etree.SubElement(adicao, "cofinsAliquotaValorDevido").text = fmt_sap("137574")
        etree.SubElement(adicao, "cofinsAliquotaValorRecolher").text = fmt_sap("137574")
        
        # Condição de Venda
        etree.SubElement(adicao, "condicaoVendaIncoterm").text = item['incoterm']
        etree.SubElement(adicao, "condicaoVendaLocal").text = "BRUGNERA" # Extrair do PDF se variar
        etree.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
        etree.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"
        etree.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
        etree.SubElement(adicao, "condicaoVendaMoedaNome").text = "EURO/COM.EUROPEIA"
        etree.SubElement(adicao, "condicaoVendaValorMoeda").text = fmt_sap("210145")
        etree.SubElement(adicao, "condicaoVendaValorReais").text = fmt_sap("1302962")
        
        # Dados Cambiais
        etree.SubElement(adicao, "dadosCambiaisCoberturaCambialCodigo").text = "1"
        etree.SubElement(adicao, "dadosCambiaisCoberturaCambialNome").text = "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"
        etree.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraCodigo").text = "00"
        etree.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraNome").text = "N/I"
        etree.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaCodigo").text = "00"
        etree.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaNome").text = "N/I"
        etree.SubElement(adicao, "dadosCambiaisValorRealCambio").text = "000000000000000"
        
        # Dados Carga (Adição)
        etree.SubElement(adicao, "dadosCargaPaisProcedenciaCodigo").text = "000"
        etree.SubElement(adicao, "dadosCargaUrfEntradaCodigo").text = "0000000"
        etree.SubElement(adicao, "dadosCargaViaTransporteCodigo").text = "01"
        etree.SubElement(adicao, "dadosCargaViaTransporteNome").text = "MARÍTIMA"
        
        # Dados Mercadoria
        etree.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
        etree.SubElement(adicao, "dadosMercadoriaCodigoNaladiNCCA").text = "0000000"
        etree.SubElement(adicao, "dadosMercadoriaCodigoNaladiSH").text = "00000000"
        etree.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item['ncm']
        etree.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
        etree.SubElement(adicao, "dadosMercadoriaDescricaoTipoCertificado").text = "Sem Certificado"
        etree.SubElement(adicao, "dadosMercadoriaIndicadorTipoCertificado").text = "1"
        etree.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaQuantidade").text = fmt_sap(item.get('qtd_estat', '0'), 14)
        etree.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaUnidade").text = "QUILOGRAMA LIQUIDO"
        etree.SubElement(adicao, "dadosMercadoriaNomeNcm").text = "Descricao NCM Generica" # Ideal ter tabela NCM
        etree.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = fmt_sap(item.get('peso_liq_adi', '0'))
        
        # DCR
        etree.SubElement(adicao, "dcrCoeficienteReducao").text = "00000"
        etree.SubElement(adicao, "dcrIdentificacao").text = "00000000"
        etree.SubElement(adicao, "dcrValorDevido").text = "000000000000000"
        etree.SubElement(adicao, "dcrValorDolar").text = "000000000000000"
        etree.SubElement(adicao, "dcrValorReal").text = "000000000000000"
        etree.SubElement(adicao, "dcrValorRecolher").text = "000000000000000"
        
        # Fornecedor
        etree.SubElement(adicao, "fornecedorCidade").text = "BRUGNERA"
        etree.SubElement(adicao, "fornecedorLogradouro").text = "VIALE EUROPA"
        etree.SubElement(adicao, "fornecedorNome").text = item['fornecedor']
        etree.SubElement(adicao, "fornecedorNumero").text = "17"
        
        # Frete (Adição)
        etree.SubElement(adicao, "freteMoedaNegociadaCodigo").text = "978"
        etree.SubElement(adicao, "freteMoedaNegociadaNome").text = "EURO/COM.EUROPEIA"
        etree.SubElement(adicao, "freteValorMoedaNegociada").text = fmt_sap("2353")
        etree.SubElement(adicao, "freteValorReais").text = fmt_sap("14595")
        
        # II (Imposto Importação)
        etree.SubElement(adicao, "iiAcordoTarifarioTipoCodigo").text = "0"
        etree.SubElement(adicao, "iiAliquotaAcordo").text = "00000"
        etree.SubElement(adicao, "iiAliquotaAdValorem").text = "01800"
        etree.SubElement(adicao, "iiAliquotaPercentualReducao").text = "00000"
        etree.SubElement(adicao, "iiAliquotaReduzida").text = "00000"
        etree.SubElement(adicao, "iiAliquotaValorCalculado").text = fmt_sap("256616")
        etree.SubElement(adicao, "iiAliquotaValorDevido").text = fmt_sap("256616")
        etree.SubElement(adicao, "iiAliquotaValorRecolher").text = fmt_sap("256616")
        etree.SubElement(adicao, "iiAliquotaValorReduzido").text = "000000000000000"
        etree.SubElement(adicao, "iiBaseCalculo").text = fmt_sap(item.get('valor_aduan', '0'))
        etree.SubElement(adicao, "iiFundamentoLegalCodigo").text = "00"
        etree.SubElement(adicao, "iiMotivoAdmissaoTemporariaCodigo").text = "00"
        etree.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
        etree.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
        
        # IPI
        etree.SubElement(adicao, "ipiAliquotaAdValorem").text = "00325"
        etree.SubElement(adicao, "ipiAliquotaEspecificaCapacidadeRecipciente").text = "00000"
        etree.SubElement(adicao, "ipiAliquotaEspecificaQuantidadeUnidadeMedida").text = "000000000"
        etree.SubElement(adicao, "ipiAliquotaEspecificaTipoRecipienteCodigo").text = "00"
        etree.SubElement(adicao, "ipiAliquotaEspecificaValorUnidadeMedida").text = "0000000000"
        etree.SubElement(adicao, "ipiAliquotaNotaComplementarTIPI").text = "00"
        etree.SubElement(adicao, "ipiAliquotaReduzida").text = "00000"
        etree.SubElement(adicao, "ipiAliquotaValorDevido").text = fmt_sap("54674")
        etree.SubElement(adicao, "ipiAliquotaValorRecolher").text = fmt_sap("54674")
        etree.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "4"
        etree.SubElement(adicao, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"
        
        # Detalhe Mercadoria
        merc = etree.SubElement(adicao, "mercadoria")
        etree.SubElement(merc, "descricaoMercadoria").text = "DESCRICAO EXTRAIDA DO PDF"
        etree.SubElement(merc, "numeroSequencialItem").text = "01"
        etree.SubElement(merc, "quantidade").text = fmt_sap("5000", 14)
        etree.SubElement(merc, "unidadeMedida").text = "PECA"
        etree.SubElement(merc, "valorUnitario").text = fmt_sap("321304", 20)
        
        # IDs Adição
        etree.SubElement(adicao, "numeroAdicao").text = item['numero']
        etree.SubElement(adicao, "numeroDUIMP").text = data['header'].get('numeroDUIMP', '0000000000')
        etree.SubElement(adicao, "numeroLI").text = "0000000000"
        etree.SubElement(adicao, "paisAquisicaoMercadoriaCodigo").text = "386"
        etree.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = "ITALIA"
        etree.SubElement(adicao, "paisOrigemMercadoriaCodigo").text = "386"
        etree.SubElement(adicao, "paisOrigemMercadoriaNome").text = "ITALIA"
        
        # PIS/COFINS (Base)
        etree.SubElement(adicao, "pisCofinsBaseCalculoAliquotaICMS").text = "00000"
        etree.SubElement(adicao, "pisCofinsBaseCalculoFundamentoLegalCodigo").text = "00"
        etree.SubElement(adicao, "pisCofinsBaseCalculoPercentualReducao").text = "00000"
        etree.SubElement(adicao, "pisCofinsBaseCalculoValor").text = fmt_sap(item.get('valor_aduan', '0'))
        etree.SubElement(adicao, "pisCofinsFundamentoLegalReducaoCodigo").text = "00"
        etree.SubElement(adicao, "pisCofinsRegimeTributacaoCodigo").text = "1"
        etree.SubElement(adicao, "pisCofinsRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
        
        # PIS
        etree.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
        etree.SubElement(adicao, "pisPasepAliquotaEspecificaQuantidadeUnidade").text = "000000000"
        etree.SubElement(adicao, "pisPasepAliquotaEspecificaValor").text = "0000000000"
        etree.SubElement(adicao, "pisPasepAliquotaReduzida").text = "00000"
        etree.SubElement(adicao, "pisPasepAliquotaValorDevido").text = fmt_sap("29938")
        etree.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = fmt_sap("29938")
        
        # ICMS
        etree.SubElement(adicao, "icmsBaseCalculoValor").text = fmt_sap("160652")
        etree.SubElement(adicao, "icmsBaseCalculoAliquota").text = "01800"
        etree.SubElement(adicao, "icmsBaseCalculoValorImposto").text = fmt_sap("19374")
        etree.SubElement(adicao, "icmsBaseCalculoValorDiferido").text = fmt_sap("9542")
        
        # CBS / IBS (Reforma Tributária - Tags Obrigatórias conforme seu XML)
        etree.SubElement(adicao, "cbsIbsCst").text = "000"
        etree.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
        etree.SubElement(adicao, "cbsBaseCalculoValor").text = fmt_sap("160652")
        etree.SubElement(adicao, "cbsBaseCalculoAliquota").text = "00090"
        etree.SubElement(adicao, "cbsBaseCalculoAliquotaReducao").text = "00000"
        etree.SubElement(adicao, "cbsBaseCalculoValorImposto").text = fmt_sap("1445")
        
        etree.SubElement(adicao, "ibsBaseCalculoValor").text = fmt_sap("160652")
        etree.SubElement(adicao, "ibsBaseCalculoAliquota").text = "00010"
        etree.SubElement(adicao, "ibsBaseCalculoAliquotaReducao").text = "00000"
        etree.SubElement(adicao, "ibsBaseCalculoValorImposto").text = fmt_sap("160")
        
        # Final Adição
        etree.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
        etree.SubElement(adicao, "seguroMoedaNegociadaCodigo").text = "220"
        etree.SubElement(adicao, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
        etree.SubElement(adicao, "seguroValorMoedaNegociada").text = "000000000000000"
        etree.SubElement(adicao, "seguroValorReais").text = fmt_sap("1489")
        etree.SubElement(adicao, "sequencialRetificacao").text = "00"
        etree.SubElement(adicao, "valorMultaARecolher").text = "000000000000000"
        etree.SubElement(adicao, "valorMultaARecolherAjustado").text = "000000000000000"
        etree.SubElement(adicao, "valorReaisFreteInternacional").text = fmt_sap("14595")
        etree.SubElement(adicao, "valorReaisSeguroInternacional").text = fmt_sap("1489")
        etree.SubElement(adicao, "valorTotalCondicaoVenda").text = fmt_sap("21014900800")
        etree.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

    # --- BLOCO 2: DADOS GERAIS (Após as Adições - Ordem do arquivo de amostra) ---
    
    # Armazem
    arm = etree.SubElement(duimp, "armazem")
    etree.SubElement(arm, "nomeArmazem").text = "TCP"
    etree.SubElement(duimp, "armazenamentoRecintoAduaneiroCodigo").text = "9801303"
    etree.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
    etree.SubElement(duimp, "armazenamentoSetor").text = "002"
    etree.SubElement(duimp, "canalSelecaoParametrizada").text = "001"
    etree.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
    etree.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importação Própria"
    etree.SubElement(duimp, "cargaDataChegada").text = "20251120"
    etree.SubElement(duimp, "cargaNumeroAgente").text = "N/I"
    etree.SubElement(duimp, "cargaPaisProcedenciaCodigo").text = "386"
    etree.SubElement(duimp, "cargaPaisProcedenciaNome").text = "ITALIA"
    etree.SubElement(duimp, "cargaPesoBruto").text = fmt_sap(data['header'].get('pesoBruto'))
    etree.SubElement(duimp, "cargaPesoLiquido").text = fmt_sap(data['header'].get('pesoLiquido'))
    etree.SubElement(duimp, "cargaUrfEntradaCodigo").text = "0917800"
    etree.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
    
    # Conhecimento Carga
    etree.SubElement(duimp, "conhecimentoCargaEmbarqueData").text = "20251025"
    etree.SubElement(duimp, "conhecimentoCargaEmbarqueLocal").text = "GENOVA"
    etree.SubElement(duimp, "conhecimentoCargaId").text = "CEMERCANTE31032008"
    etree.SubElement(duimp, "conhecimentoCargaIdMaster").text = "162505352452915"
    etree.SubElement(duimp, "conhecimentoCargaTipoCodigo").text = "12"
    etree.SubElement(duimp, "conhecimentoCargaTipoNome").text = "HBL - House Bill of Lading"
    etree.SubElement(duimp, "conhecimentoCargaUtilizacao").text = "1"
    etree.SubElement(duimp, "conhecimentoCargaUtilizacaoNome").text = "Total"
    
    # Datas e Docs
    etree.SubElement(duimp, "dataDesembaraco").text = "20251124"
    etree.SubElement(duimp, "dataRegistro").text = "20251124"
    etree.SubElement(duimp, "documentoChegadaCargaCodigoTipo").text = "1"
    etree.SubElement(duimp, "documentoChegadaCargaNome").text = "Manifesto da Carga"
    etree.SubElement(duimp, "documentoChegadaCargaNumero").text = "1625502058594"
    
    # Docs Instrução (Exemplo Fixo - Deve ser extraido do Loop)
    doc1 = etree.SubElement(duimp, "documentoInstrucaoDespacho")
    etree.SubElement(doc1, "codigoTipoDocumentoDespacho").text = "28"
    etree.SubElement(doc1, "nomeDocumentoDespacho").text = "CONHECIMENTO DE CARGA"
    etree.SubElement(doc1, "numeroDocumentoDespacho").text = "372250376737202501"
    
    # Embalagem
    emb = etree.SubElement(duimp, "embalagem")
    etree.SubElement(emb, "codigoTipoEmbalagem").text = "60"
    etree.SubElement(emb, "nomeEmbalagem").text = "PALLETS"
    etree.SubElement(emb, "quantidadeVolume").text = "00002"
    
    # Fretes Globais
    etree.SubElement(duimp, "freteCollect").text = fmt_sap("25000")
    etree.SubElement(duimp, "freteEmTerritorioNacional").text = "000000000000000"
    etree.SubElement(duimp, "freteMoedaNegociadaCodigo").text = "978"
    etree.SubElement(duimp, "freteMoedaNegociadaNome").text = "EURO/COM.EUROPEIA"
    etree.SubElement(duimp, "fretePrepaid").text = "000000000000000"
    etree.SubElement(duimp, "freteTotalDolares").text = fmt_sap("28757")
    etree.SubElement(duimp, "freteTotalMoeda").text = "25000"
    etree.SubElement(duimp, "freteTotalReais").text = fmt_sap("155007")
    
    # ICMS Global
    icms = etree.SubElement(duimp, "icms")
    etree.SubElement(icms, "agenciaIcms").text = "00000"
    etree.SubElement(icms, "bancoIcms").text = "000"
    etree.SubElement(icms, "codigoTipoRecolhimentoIcms").text = "3"
    etree.SubElement(icms, "cpfResponsavelRegistro").text = "27160353854"
    etree.SubElement(icms, "dataRegistro").text = "20251125"
    etree.SubElement(icms, "horaRegistro").text = "152044"
    etree.SubElement(icms, "nomeTipoRecolhimentoIcms").text = "Exoneração do ICMS"
    etree.SubElement(icms, "numeroSequencialIcms").text = "001"
    etree.SubElement(icms, "ufIcms").text = "PR"
    etree.SubElement(icms, "valorTotalIcms").text = "000000000000000"
    
    # Importador
    etree.SubElement(duimp, "importadorCodigoTipo").text = "1"
    etree.SubElement(duimp, "importadorCpfRepresentanteLegal").text = "27160353854"
    etree.SubElement(duimp, "importadorEnderecoBairro").text = "JARDIM PRIMAVERA"
    etree.SubElement(duimp, "importadorEnderecoCep").text = "83302000"
    etree.SubElement(duimp, "importadorEnderecoComplemento").text = "CONJ: 6 E 7;"
    etree.SubElement(duimp, "importadorEnderecoLogradouro").text = "JOAO LEOPOLDO JACOMEL"
    etree.SubElement(duimp, "importadorEnderecoMunicipio").text = "PIRAQUARA"
    etree.SubElement(duimp, "importadorEnderecoNumero").text = "4459"
    etree.SubElement(duimp, "importadorEnderecoUf").text = "PR"
    etree.SubElement(duimp, "importadorNome").text = data['header'].get('importadorNome', "HAFELE BRASIL LTDA").strip()
    etree.SubElement(duimp, "importadorNomeRepresentanteLegal").text = "PAULO HENRIQUE LEITE FERREIRA"
    etree.SubElement(duimp, "importadorNumero").text = "02473058000188"
    etree.SubElement(duimp, "importadorNumeroTelefone").text = "41 30348150"
    etree.SubElement(duimp, "informacaoComplementar").text = "INFORMACOES COMPLEMENTARES..."
    
    # Totais Locais
    etree.SubElement(duimp, "localDescargaTotalDolares").text = fmt_sap("2061433")
    etree.SubElement(duimp, "localDescargaTotalReais").text = fmt_sap("11111593")
    etree.SubElement(duimp, "localEmbarqueTotalDolares").text = fmt_sap("2030535")
    etree.SubElement(duimp, "localEmbarqueTotalReais").text = fmt_sap("10945130")
    etree.SubElement(duimp, "modalidadeDespachoCodigo").text = "1"
    etree.SubElement(duimp, "modalidadeDespachoNome").text = "Normal"
    etree.SubElement(duimp, "numeroDUIMP").text = data['header'].get('numeroDUIMP', '8686868686')
    etree.SubElement(duimp, "operacaoFundap").text = "N"
    
    # Pagamentos (Exemplo de um bloco - replicar via loop se extrair do PDF)
    pag = etree.SubElement(duimp, "pagamento")
    etree.SubElement(pag, "agenciaPagamento").text = "3715"
    etree.SubElement(pag, "bancoPagamento").text = "341"
    etree.SubElement(pag, "codigoReceita").text = "0086"
    etree.SubElement(pag, "codigoTipoPagamento").text = "1"
    etree.SubElement(pag, "contaPagamento").text = "316273"
    etree.SubElement(pag, "dataPagamento").text = "20251124"
    etree.SubElement(pag, "nomeTipoPagamento").text = "Débito em Conta"
    etree.SubElement(pag, "numeroRetificacao").text = "00"
    etree.SubElement(pag, "valorJurosEncargos").text = "000000000"
    etree.SubElement(pag, "valorMulta").text = "000000000"
    etree.SubElement(pag, "valorReceita").text = fmt_sap("1772057")
    
    # Seguro Global
    etree.SubElement(duimp, "seguroMoedaNegociadaCodigo").text = "220"
    etree.SubElement(duimp, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
    etree.SubElement(duimp, "seguroTotalDolares").text = fmt_sap("2146")
    etree.SubElement(duimp, "seguroTotalMoedaNegociada").text = fmt_sap("2146")
    etree.SubElement(duimp, "seguroTotalReais").text = fmt_sap("11567")
    etree.SubElement(duimp, "sequencialRetificacao").text = "00"
    etree.SubElement(duimp, "situacaoEntregaCarga").text = "ENTREGA CONDICIONADA..."
    etree.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
    etree.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
    etree.SubElement(duimp, "totalAdicoes").text = str(len(data['adicoes'])).zfill(3)
    etree.SubElement(duimp, "urfDespachoCodigo").text = "0917800"
    etree.SubElement(duimp, "urfDespachoNome").text = "PORTO DE PARANAGUA"
    etree.SubElement(duimp, "valorTotalMultaARecolherAjustado").text = "000000000000000"
    
    # Via Transporte Global
    etree.SubElement(duimp, "viaTransporteCodigo").text = "01"
    etree.SubElement(duimp, "viaTransporteMultimodal").text = "N"
    etree.SubElement(duimp, "viaTransporteNome").text = "MARÍTIMA"
    etree.SubElement(duimp, "viaTransporteNomeTransportador").text = "MAERSK A/S"
    etree.SubElement(duimp, "viaTransporteNomeVeiculo").text = "MAERSK MEMPHIS"
    etree.SubElement(duimp, "viaTransportePaisTransportadorCodigo").text = "741"
    etree.SubElement(duimp, "viaTransportePaisTransportadorNome").text = "CINGAPURA"

    return etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# ==============================================================================
# 4. INTERFACE STREAMLIT
# ==============================================================================

def main():
    st.set_page_config(page_title="SAP DUIMP Converter", layout="wide")
    st.title("Conversor DUIMP PDF para XML (SAP Compliance)")
    st.warning("Layout SAP Estrito: Mapeamento completo de tags e formatação de zeros à esquerda.")

    uploaded_file = st.file_uploader("Carregar Extrato PDF", type=["pdf"])

    if uploaded_file:
        if st.button("Gerar XML SAP"):
            try:
                # 1. Processar PDF
                processor = SapDuimpProcessor(uploaded_file.read())
                data = processor.process()
                
                # 2. Gerar XML
                xml_content = generate_sap_xml(data)
                
                st.success(f"Processado! {len(data['adicoes'])} adições encontradas.")
                
                st.download_button(
                    label="Baixar Arquivo XML Pronto",
                    data=xml_content,
                    file_name=f"DUIMP_{data['header'].get('numeroDUIMP', 'SAP')}.xml",
                    mime="application/xml"
                )
                
                with st.expander("Visualizar Estrutura Extraída (JSON)"):
                    st.json(data)

            except Exception as e:
                st.error(f"Erro Crítico: {e}")

if __name__ == "__main__":
    main()
