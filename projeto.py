import streamlit as st
import fitz  # PyMuPDF (Alta performance para PDFs grandes)
from lxml import etree
import re
import io
import time
from typing import List, Dict, Any

# --- CONFIGURAÇÃO E ESTILO (Mantendo a identidade Häfele) ---
st.set_page_config(page_title="Häfele | DUIMP to SAP Converter", page_icon="📦", layout="wide")

def apply_custom_ui():
    st.markdown("""
    <style>
        .main { background-color: #f8fafc; }
        .stApp { font-family: 'Inter', sans-serif; }
        .header-container {
            background: #ffffff;
            padding: 2rem;
            border-radius: 15px;
            border-left: 8px solid #d50000; /* Vermelho Häfele ajustado */
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .hafele-logo { max-width: 200px; margin-bottom: 1rem; }
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES (REGRA SAP) ---
def fmt_sap(value, length=15):
    """Formata valores para padrão SAP: Sem pontuação, zeros à esquerda."""
    if not value: return "0" * length
    digits = re.sub(r'[^\d]', '', str(value))
    return digits.zfill(length)

def clean_text(text):
    if not text: return ""
    return " ".join(text.split())

def extract_regex(pattern, text, default=""):
    match = re.search(pattern, text, re.IGNORECASE)
    if match: return match.group(1).strip()
    return default

# --- ENGINE DE PROCESSAMENTO (CORE) ---
class DuimpSapEngine:
    """Processador otimizado para extração de PDF DUIMP e conversão para XML SAP."""
    
    def __init__(self):
        pass

    def extract_data_from_pdf(self, pdf_bytes):
        """Lê o PDF (suporta 500+ pgs) e estrutura os dados."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = ""
        
        # Leitura linear otimizada (C++)
        for page in doc:
            full_text += page.get_text("text", sort=True) + "\n"
            
        data = {
            "header": {},
            "adicoes": [],
            "totais": {}
        }

        # 1. Extração Cabeçalho
        data['header']['numero'] = extract_regex(r"DUIMP\s*[:]\s*([\d\.\/-]+)", full_text).replace('.', '').replace('/', '').replace('-', '')
        data['header']['importador'] = extract_regex(r"Importador\s*[:]\s*(.+?)\n", full_text)
        data['header']['peso_bruto'] = extract_regex(r"Peso Bruto Total\s*[:]\s*([\d,\.]+)", full_text)
        data['header']['peso_liq'] = extract_regex(r"Peso Líquido Total\s*[:]\s*([\d,\.]+)", full_text)

        # 2. Loop de Adições (Detecta múltiplos itens)
        split_pattern = r"(?:Adição|Item)\s*[:nNº°]*\s*(\d{3})"
        blocks = re.split(split_pattern, full_text)
        
        if len(blocks) > 1:
            # Pula o cabeçalho (índice 0) e pega pares (Número, Conteúdo)
            for i in range(1, len(blocks), 2):
                adi_num = blocks[i]
                content = blocks[i+1]
                
                adi = {
                    "numero": adi_num,
                    "ncm": extract_regex(r"NCM\s*[:]\s*([\d\.]+)", content).replace('.', ''),
                    "valor_aduan": extract_regex(r"Valor Aduaneiro\s*[:]\s*([\d,\.]+)", content),
                    "incoterm": extract_regex(r"Incoterm\s*[:]\s*([A-Z]{3})", content),
                    "peso_liq": extract_regex(r"Peso Líquido\s*[:]\s*([\d,\.]+)", content),
                    "qtd_estat": extract_regex(r"Quantidade Estatística\s*[:]\s*([\d,\.]+)", content),
                    "fornecedor": extract_regex(r"Exportador|Fornecedor\s*[:]\s*(.+?)\n", content),
                    "descricao": extract_regex(r"Descrição da Mercadoria\s*[:]\s*(.+?)(?:\n|$)", content),
                    
                    # Impostos do Item
                    "val_ii": extract_regex(r"II.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", content),
                    "val_ipi": extract_regex(r"IPI.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", content),
                    "val_pis": extract_regex(r"PIS.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", content),
                    "val_cofins": extract_regex(r"COFINS.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", content),
                    "frete_item": extract_regex(r"Frete\s*[:]\s*([\d,\.]+)", content),
                    "seguro_item": extract_regex(r"Seguro\s*[:]\s*([\d,\.]+)", content),
                }
                data['adicoes'].append(adi)
        
        # 3. Totais Rodapé
        data['totais']['frete_total'] = extract_regex(r"Total Frete\s*\(R\$\)\s*[:]\s*([\d,\.]+)", full_text)
        data['totais']['seguro_total'] = extract_regex(r"Total Seguro\s*\(R\$\)\s*[:]\s*([\d,\.]+)", full_text)

        return data

    def generate_xml(self, data):
        """Constrói a árvore XML estrita exigida pelo SAP."""
        root = etree.Element("ListaDeclaracoes")
        duimp = etree.SubElement(root, "duimp")

        # --- BLOCO ADIÇÕES (Mandatório ser o primeiro) ---
        for item in data['adicoes']:
            adicao = etree.SubElement(duimp, "adicao")
            
            # Acrescimo
            acr = etree.SubElement(adicao, "acrescimo")
            etree.SubElement(acr, "codigoAcrescimo").text = "17"
            etree.SubElement(acr, "denominacao").text = "OUTROS ACRESCIMOS"
            etree.SubElement(acr, "moedaNegociadaCodigo").text = "978"
            etree.SubElement(acr, "moedaNegociadaNome").text = "EURO"
            etree.SubElement(acr, "valorMoedaNegociada").text = fmt_sap("0")
            etree.SubElement(acr, "valorReais").text = fmt_sap("0")

            # Impostos
            etree.SubElement(adicao, "cideValorAliquotaEspecifica").text = fmt_sap("0", 11)
            etree.SubElement(adicao, "cideValorDevido").text = fmt_sap("0")
            etree.SubElement(adicao, "cideValorRecolher").text = fmt_sap("0")
            etree.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
            etree.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"

            # COFINS
            etree.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965"
            etree.SubElement(adicao, "cofinsAliquotaEspecificaQuantidadeUnidade").text = fmt_sap("0", 9)
            etree.SubElement(adicao, "cofinsAliquotaEspecificaValor").text = fmt_sap("0", 10)
            etree.SubElement(adicao, "cofinsAliquotaReduzida").text = "00000"
            etree.SubElement(adicao, "cofinsAliquotaValorDevido").text = fmt_sap(item['val_cofins'])
            etree.SubElement(adicao, "cofinsAliquotaValorRecolher").text = fmt_sap(item['val_cofins'])

            # Venda
            etree.SubElement(adicao, "condicaoVendaIncoterm").text = item['incoterm'] or "FCA"
            etree.SubElement(adicao, "condicaoVendaLocal").text = "LOCAL"
            etree.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
            etree.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = "METODO 1"
            etree.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
            etree.SubElement(adicao, "condicaoVendaMoedaNome").text = "EURO"
            etree.SubElement(adicao, "condicaoVendaValorMoeda").text = fmt_sap("0")
            etree.SubElement(adicao, "condicaoVendaValorReais").text = fmt_sap(item['valor_aduan'])

            # Carga Item
            etree.SubElement(adicao, "dadosCargaPaisProcedenciaCodigo").text = "000"
            etree.SubElement(adicao, "dadosCargaUrfEntradaCodigo").text = "0000000"
            etree.SubElement(adicao, "dadosCargaViaTransporteCodigo").text = "01"
            etree.SubElement(adicao, "dadosCargaViaTransporteNome").text = "MARITIMA"

            # Mercadoria
            etree.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
            etree.SubElement(adicao, "dadosMercadoriaCodigoNaladiNCCA").text = "0000000"
            etree.SubElement(adicao, "dadosMercadoriaCodigoNaladiSH").text = "00000000"
            etree.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item['ncm']
            etree.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
            etree.SubElement(adicao, "dadosMercadoriaDescricaoTipoCertificado").text = "Sem Certificado"
            etree.SubElement(adicao, "dadosMercadoriaIndicadorTipoCertificado").text = "1"
            etree.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaQuantidade").text = fmt_sap(item['qtd_estat'], 14)
            etree.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaUnidade").text = "UNIDADE"
            etree.SubElement(adicao, "dadosMercadoriaNomeNcm").text = "GENERICO"
            etree.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = fmt_sap(item['peso_liq'])

            # DCR (placeholder)
            etree.SubElement(adicao, "dcrCoeficienteReducao").text = "00000"
            etree.SubElement(adicao, "dcrIdentificacao").text = "00000000"
            etree.SubElement(adicao, "dcrValorDevido").text = fmt_sap("0")
            etree.SubElement(adicao, "dcrValorDolar").text = fmt_sap("0")
            etree.SubElement(adicao, "dcrValorReal").text = fmt_sap("0")
            etree.SubElement(adicao, "dcrValorRecolher").text = fmt_sap("0")

            # Fornecedor
            etree.SubElement(adicao, "fornecedorCidade").text = "CIDADE"
            etree.SubElement(adicao, "fornecedorLogradouro").text = "RUA"
            etree.SubElement(adicao, "fornecedorNome").text = clean_text(item['fornecedor'])[:60]
            etree.SubElement(adicao, "fornecedorNumero").text = "00"

            # Frete Item
            etree.SubElement(adicao, "freteMoedaNegociadaCodigo").text = "978"
            etree.SubElement(adicao, "freteMoedaNegociadaNome").text = "EURO"
            etree.SubElement(adicao, "freteValorMoedaNegociada").text = fmt_sap("0")
            etree.SubElement(adicao, "freteValorReais").text = fmt_sap(item['frete_item'])

            # II
            etree.SubElement(adicao, "iiAcordoTarifarioTipoCodigo").text = "0"
            etree.SubElement(adicao, "iiAliquotaAcordo").text = "00000"
            etree.SubElement(adicao, "iiAliquotaAdValorem").text = "01800"
            etree.SubElement(adicao, "iiAliquotaPercentualReducao").text = "00000"
            etree.SubElement(adicao, "iiAliquotaReduzida").text = "00000"
            etree.SubElement(adicao, "iiAliquotaValorCalculado").text = fmt_sap(item['val_ii'])
            etree.SubElement(adicao, "iiAliquotaValorDevido").text = fmt_sap(item['val_ii'])
            etree.SubElement(adicao, "iiAliquotaValorRecolher").text = fmt_sap(item['val_ii'])
            etree.SubElement(adicao, "iiAliquotaValorReduzido").text = fmt_sap("0")
            etree.SubElement(adicao, "iiBaseCalculo").text = fmt_sap(item['valor_aduan'])
            etree.SubElement(adicao, "iiFundamentoLegalCodigo").text = "00"
            etree.SubElement(adicao, "iiMotivoAdmissaoTemporariaCodigo").text = "00"
            etree.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
            etree.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"

            # IPI
            etree.SubElement(adicao, "ipiAliquotaAdValorem").text = "00000"
            etree.SubElement(adicao, "ipiAliquotaEspecificaCapacidadeRecipciente").text = "00000"
            etree.SubElement(adicao, "ipiAliquotaEspecificaQuantidadeUnidadeMedida").text = "000000000"
            etree.SubElement(adicao, "ipiAliquotaEspecificaTipoRecipienteCodigo").text = "00"
            etree.SubElement(adicao, "ipiAliquotaEspecificaValorUnidadeMedida").text = "0000000000"
            etree.SubElement(adicao, "ipiAliquotaNotaComplementarTIPI").text = "00"
            etree.SubElement(adicao, "ipiAliquotaReduzida").text = "00000"
            etree.SubElement(adicao, "ipiAliquotaValorDevido").text = fmt_sap(item['val_ipi'])
            etree.SubElement(adicao, "ipiAliquotaValorRecolher").text = fmt_sap(item['val_ipi'])
            etree.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "4"
            etree.SubElement(adicao, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"

            # Detalhes
            merc = etree.SubElement(adicao, "mercadoria")
            etree.SubElement(merc, "descricaoMercadoria").text = clean_text(item['descricao'])[:100]
            etree.SubElement(merc, "numeroSequencialItem").text = "01"
            etree.SubElement(merc, "quantidade").text = fmt_sap(item['qtd_estat'], 14)
            etree.SubElement(merc, "unidadeMedida").text = "PECA"
            etree.SubElement(merc, "valorUnitario").text = fmt_sap("0", 20)

            # IDs
            etree.SubElement(adicao, "numeroAdicao").text = item['numero']
            etree.SubElement(adicao, "numeroDUIMP").text = data['header'].get('numero')
            etree.SubElement(adicao, "numeroLI").text = "0000000000"
            etree.SubElement(adicao, "paisAquisicaoMercadoriaCodigo").text = "386"
            etree.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = "ITALIA"
            etree.SubElement(adicao, "paisOrigemMercadoriaCodigo").text = "386"
            etree.SubElement(adicao, "paisOrigemMercadoriaNome").text = "ITALIA"

            # PIS
            etree.SubElement(adicao, "pisCofinsBaseCalculoAliquotaICMS").text = "00000"
            etree.SubElement(adicao, "pisCofinsBaseCalculoFundamentoLegalCodigo").text = "00"
            etree.SubElement(adicao, "pisCofinsBaseCalculoPercentualReducao").text = "00000"
            etree.SubElement(adicao, "pisCofinsBaseCalculoValor").text = fmt_sap(item['valor_aduan'])
            etree.SubElement(adicao, "pisCofinsFundamentoLegalReducaoCodigo").text = "00"
            etree.SubElement(adicao, "pisCofinsRegimeTributacaoCodigo").text = "1"
            etree.SubElement(adicao, "pisCofinsRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
            etree.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
            etree.SubElement(adicao, "pisPasepAliquotaEspecificaQuantidadeUnidade").text = "000000000"
            etree.SubElement(adicao, "pisPasepAliquotaEspecificaValor").text = "0000000000"
            etree.SubElement(adicao, "pisPasepAliquotaReduzida").text = "00000"
            etree.SubElement(adicao, "pisPasepAliquotaValorDevido").text = fmt_sap(item['val_pis'])
            etree.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = fmt_sap(item['val_pis'])

            # ICMS
            etree.SubElement(adicao, "icmsBaseCalculoValor").text = fmt_sap("0")
            etree.SubElement(adicao, "icmsBaseCalculoAliquota").text = "01800"
            etree.SubElement(adicao, "icmsBaseCalculoValorImposto").text = fmt_sap("0")
            etree.SubElement(adicao, "icmsBaseCalculoValorDiferido").text = fmt_sap("0")

            # CBS/IBS (Reforma Tributária - placeholders)
            etree.SubElement(adicao, "cbsIbsCst").text = "000"
            etree.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
            etree.SubElement(adicao, "cbsBaseCalculoValor").text = fmt_sap("0")
            etree.SubElement(adicao, "cbsBaseCalculoAliquota").text = "00090"
            etree.SubElement(adicao, "cbsBaseCalculoAliquotaReducao").text = "00000"
            etree.SubElement(adicao, "cbsBaseCalculoValorImposto").text = fmt_sap("0")
            etree.SubElement(adicao, "ibsBaseCalculoValor").text = fmt_sap("0")
            etree.SubElement(adicao, "ibsBaseCalculoAliquota").text = "00010"
            etree.SubElement(adicao, "ibsBaseCalculoAliquotaReducao").text = "00000"
            etree.SubElement(adicao, "ibsBaseCalculoValorImposto").text = fmt_sap("0")

            # Final Adição
            etree.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
            etree.SubElement(adicao, "seguroMoedaNegociadaCodigo").text = "220"
            etree.SubElement(adicao, "seguroMoedaNegociadaNome").text = "DOLAR"
            etree.SubElement(adicao, "seguroValorMoedaNegociada").text = fmt_sap("0")
            etree.SubElement(adicao, "seguroValorReais").text = fmt_sap(item['seguro_item'])
            etree.SubElement(adicao, "sequencialRetificacao").text = "00"
            etree.SubElement(adicao, "valorMultaARecolher").text = fmt_sap("0")
            etree.SubElement(adicao, "valorMultaARecolherAjustado").text = fmt_sap("0")
            etree.SubElement(adicao, "valorReaisFreteInternacional").text = fmt_sap(item['frete_item'])
            etree.SubElement(adicao, "valorReaisSeguroInternacional").text = fmt_sap(item['seguro_item'])
            etree.SubElement(adicao, "valorTotalCondicaoVenda").text = fmt_sap("0")
            etree.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação"

        # --- DADOS GERAIS (HEADER) ---
        arm = etree.SubElement(duimp, "armazem")
        etree.SubElement(arm, "nomeArmazem").text = "TCP"
        
        etree.SubElement(duimp, "armazenamentoRecintoAduaneiroCodigo").text = "9801303"
        etree.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP"
        etree.SubElement(duimp, "armazenamentoSetor").text = "002"
        etree.SubElement(duimp, "canalSelecaoParametrizada").text = "001"
        etree.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
        etree.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importação Própria"
        etree.SubElement(duimp, "cargaDataChegada").text = "20251120"
        etree.SubElement(duimp, "cargaNumeroAgente").text = "N/I"
        etree.SubElement(duimp, "cargaPaisProcedenciaCodigo").text = "386"
        etree.SubElement(duimp, "cargaPaisProcedenciaNome").text = "ITALIA"
        etree.SubElement(duimp, "cargaPesoBruto").text = fmt_sap(data['header'].get('peso_bruto'))
        etree.SubElement(duimp, "cargaPesoLiquido").text = fmt_sap(data['header'].get('peso_liq'))
        etree.SubElement(duimp, "cargaUrfEntradaCodigo").text = "0917800"
        etree.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
        
        # Conhecimento (Fixos de Exemplo)
        etree.SubElement(duimp, "conhecimentoCargaEmbarqueData").text = "20251025"
        etree.SubElement(duimp, "conhecimentoCargaEmbarqueLocal").text = "GENOVA"
        etree.SubElement(duimp, "conhecimentoCargaId").text = "CEMERCANTE"
        etree.SubElement(duimp, "conhecimentoCargaIdMaster").text = "MASTER"
        etree.SubElement(duimp, "conhecimentoCargaTipoCodigo").text = "12"
        etree.SubElement(duimp, "conhecimentoCargaTipoNome").text = "HBL"
        etree.SubElement(duimp, "conhecimentoCargaUtilizacao").text = "1"
        etree.SubElement(duimp, "conhecimentoCargaUtilizacaoNome").text = "Total"
        etree.SubElement(duimp, "dataDesembaraco").text = "20251124"
        etree.SubElement(duimp, "dataRegistro").text = "20251124"
        etree.SubElement(duimp, "documentoChegadaCargaCodigoTipo").text = "1"
        etree.SubElement(duimp, "documentoChegadaCargaNome").text = "Manifesto"
        etree.SubElement(duimp, "documentoChegadaCargaNumero").text = "1625502058594"

        # Embalagem
        emb = etree.SubElement(duimp, "embalagem")
        etree.SubElement(emb, "codigoTipoEmbalagem").text = "60"
        etree.SubElement(emb, "nomeEmbalagem").text = "PALLETS"
        etree.SubElement(emb, "quantidadeVolume").text = "00002"

        # Totais Globais
        etree.SubElement(duimp, "freteCollect").text = fmt_sap("0")
        etree.SubElement(duimp, "freteEmTerritorioNacional").text = fmt_sap("0")
        etree.SubElement(duimp, "freteMoedaNegociadaCodigo").text = "978"
        etree.SubElement(duimp, "freteMoedaNegociadaNome").text = "EURO"
        etree.SubElement(duimp, "fretePrepaid").text = fmt_sap("0")
        etree.SubElement(duimp, "freteTotalDolares").text = fmt_sap("0")
        etree.SubElement(duimp, "freteTotalMoeda").text = fmt_sap("0")
        etree.SubElement(duimp, "freteTotalReais").text = fmt_sap(data['totais'].get('frete_total'))

        # Importador
        etree.SubElement(duimp, "importadorCodigoTipo").text = "1"
        etree.SubElement(duimp, "importadorCpfRepresentanteLegal").text = "00000000000"
        etree.SubElement(duimp, "importadorEnderecoBairro").text = "BAIRRO"
        etree.SubElement(duimp, "importadorEnderecoCep").text = "00000000"
        etree.SubElement(duimp, "importadorEnderecoComplemento").text = "COMPL"
        etree.SubElement(duimp, "importadorEnderecoLogradouro").text = "RUA"
        etree.SubElement(duimp, "importadorEnderecoMunicipio").text = "CIDADE"
        etree.SubElement(duimp, "importadorEnderecoNumero").text = "00"
        etree.SubElement(duimp, "importadorEnderecoUf").text = "UF"
        etree.SubElement(duimp, "importadorNome").text = clean_text(data['header'].get('importador'))
        etree.SubElement(duimp, "importadorNomeRepresentanteLegal").text = "REPRESENTANTE"
        etree.SubElement(duimp, "importadorNumero").text = "00000000000000"
        etree.SubElement(duimp, "importadorNumeroTelefone").text = "0000000000"
        etree.SubElement(duimp, "informacaoComplementar").text = "INFO COMPLEMENTAR"

        # Rodapé
        etree.SubElement(duimp, "localDescargaTotalDolares").text = fmt_sap("0")
        etree.SubElement(duimp, "localDescargaTotalReais").text = fmt_sap("0")
        etree.SubElement(duimp, "localEmbarqueTotalDolares").text = fmt_sap("0")
        etree.SubElement(duimp, "localEmbarqueTotalReais").text = fmt_sap("0")
        etree.SubElement(duimp, "modalidadeDespachoCodigo").text = "1"
        etree.SubElement(duimp, "modalidadeDespachoNome").text = "Normal"
        etree.SubElement(duimp, "numeroDUIMP").text = data['header'].get('numero')
        etree.SubElement(duimp, "operacaoFundap").text = "N"

        # Pagamento (Genérico, necessário ajustar se houver dados)
        pag = etree.SubElement(duimp, "pagamento")
        etree.SubElement(pag, "agenciaPagamento").text = "0000"
        etree.SubElement(pag, "bancoPagamento").text = "000"
        etree.SubElement(pag, "codigoReceita").text = "0000"
        etree.SubElement(pag, "codigoTipoPagamento").text = "1"
        etree.SubElement(pag, "contaPagamento").text = "000000"
        etree.SubElement(pag, "dataPagamento").text = "20251124"
        etree.SubElement(pag, "nomeTipoPagamento").text = "Débito"
        etree.SubElement(pag, "numeroRetificacao").text = "00"
        etree.SubElement(pag, "valorJurosEncargos").text = fmt_sap("0", 9)
        etree.SubElement(pag, "valorMulta").text = fmt_sap("0", 9)
        etree.SubElement(pag, "valorReceita").text = fmt_sap("0")

        etree.SubElement(duimp, "seguroMoedaNegociadaCodigo").text = "220"
        etree.SubElement(duimp, "seguroMoedaNegociadaNome").text = "DOLAR"
        etree.SubElement(duimp, "seguroTotalDolares").text = fmt_sap("0")
        etree.SubElement(duimp, "seguroTotalMoedaNegociada").text = fmt_sap("0")
        etree.SubElement(duimp, "seguroTotalReais").text = fmt_sap(data['totais'].get('seguro_total'))
        etree.SubElement(duimp, "sequencialRetificacao").text = "00"
        etree.SubElement(duimp, "situacaoEntregaCarga").text = "ENTREGA"
        etree.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
        etree.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
        etree.SubElement(duimp, "totalAdicoes").text = str(len(data['adicoes'])).zfill(3)
        etree.SubElement(duimp, "urfDespachoCodigo").text = "0917800"
        etree.SubElement(duimp, "urfDespachoNome").text = "PORTO DE PARANAGUA"
        etree.SubElement(duimp, "valorTotalMultaARecolherAjustado").text = fmt_sap("0")
        etree.SubElement(duimp, "viaTransporteCodigo").text = "01"
        etree.SubElement(duimp, "viaTransporteMultimodal").text = "N"
        etree.SubElement(duimp, "viaTransporteNome").text = "MARÍTIMA"
        etree.SubElement(duimp, "viaTransporteNomeTransportador").text = "MAERSK"
        etree.SubElement(duimp, "viaTransporteNomeVeiculo").text = "MAERSK"
        etree.SubElement(duimp, "viaTransportePaisTransportadorCodigo").text = "741"
        etree.SubElement(duimp, "viaTransportePaisTransportadorNome").text = "CINGAPURA"

        return etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# --- INTERFACE PRINCIPAL ---
def main():
    apply_custom_ui()
    
    # Header Häfele Style
    st.markdown(f"""
    <div class="header-container">
        <h1>Sistema Integrado de Processamento DUIMP</h1>
        <p>Conversor PDF para XML (Layout SAP Estrito)</p>
    </div>
    """, unsafe_allow_html=True)

    engine = DuimpSapEngine()
    
    col_up, col_action = st.columns([1, 1])
    
    with col_up:
        st.subheader("Importação de Documento")
        uploaded_file = st.file_uploader("Carregue o Extrato DUIMP (PDF)", type="pdf")

    if uploaded_file:
        with col_action:
            st.write("##") # Espaçamento
            if st.button("🚀 Processar e Gerar XML"):
                try:
                    with st.spinner("Processando páginas do PDF..."):
                        # 1. Extrair Dados
                        start_time = time.time()
                        pdf_bytes = uploaded_file.read()
                        extracted_data = engine.extract_data_from_pdf(pdf_bytes)
                        
                        # 2. Gerar XML
                        xml_bytes = engine.generate_xml(extracted_data)
                        
                        end_time = time.time()
                        
                        st.success(f"Sucesso! {len(extracted_data['adicoes'])} adições processadas em {end_time - start_time:.2f}s")
                        
                        # Salvar no session state para não perder ao clicar em download
                        st.session_state['xml_output'] = xml_bytes
                        st.session_state['duimp_num'] = extracted_data['header'].get('numero', 'SAP')
                        st.session_state['preview_data'] = extracted_data

                except Exception as e:
                    st.error(f"Erro Crítico: {e}")

    # Área de Resultados
    if 'xml_output' in st.session_state:
        st.markdown("---")
        c1, c2 = st.columns(2)
        
        with c1:
            st.download_button(
                label="📥 Baixar XML SAP",
                data=st.session_state['xml_output'],
                file_name=f"DUIMP_{st.session_state['duimp_num']}.xml",
                mime="application/xml"
            )
            
        with c2:
            with st.expander("🔍 Visualizar Dados Extraídos"):
                st.json(st.session_state['preview_data'])

if __name__ == "__main__":
    main()
