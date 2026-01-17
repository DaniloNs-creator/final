import streamlit as st
import fitz  # PyMuPDF (Substituindo pdfplumber para performance em 500pgs)
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time

# --- UI PROFESSIONAL & CLEAN (MODERN SAAS STYLE) ---
def apply_clean_ui():
    st.markdown("""
    <style>
    /* Reset e Fundo Sóbrio */
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
    }

    /* Container Principal */
    .main-box {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        margin-top: 2rem;
    }

    /* Cabeçalhos */
    h1 {
        color: #0f172a;
        font-weight: 700;
        font-size: 1.75rem !important;
        letter-spacing: -0.025em;
    }

    /* Botão Primário Estilo Profissional */
    .stButton > button {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 6px !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        font-weight: 500 !important;
        transition: background-color 0.2s;
    }
    .stButton > button:hover {
        background-color: #1d4ed8 !important;
    }

    /* Barra de Progresso Discreta */
    .stProgress > div > div > div > div {
        background-color: #2563eb;
    }

    /* Inputs e Upload */
    .stFileUploader {
        border: 1px dashed #cbd5e1;
        border-radius: 8px;
        padding: 10px;
    }

    /* Alertas e Badges */
    .stAlert {
        border-radius: 6px;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE APOIO ---
def clean_val(val):
    if not val: return "0"
    # Remove tudo que não for dígito
    return re.sub(r'[^\d]', '', str(val))

def format_xml_num(val, length):
    """Formata para SAP: Apenas números com zeros à esquerda"""
    return clean_val(val).zfill(length)

def clean_text(text):
    if not text: return ""
    return " ".join(text.split())

def extract_regex(pattern, text, default=""):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return default

# --- EXTRAÇÃO DO PDF (OTIMIZADO PARA 500 PÁGINAS) ---
def parse_pdf(pdf_file):
    # Uso do PyMuPDF (fitz) para velocidade extrema em arquivos grandes
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text", sort=True) + "\n"
    
    data = {
        "header": {}, 
        "itens": [],
        "totais": {}
    }

    # 1. Dados Gerais (Header)
    # Ajuste os regex conforme o PDF real, aqui simulando a captura
    data["header"]["numero"] = extract_regex(r"DUIMP\s*[:]\s*([\d\.\/-]+)", text).replace('.', '').replace('/', '').replace('-', '')
    data["header"]["importador"] = extract_regex(r"Importador\s*[:]\s*(.+?)\n", text)
    data["header"]["peso_bruto"] = extract_regex(r"Peso Bruto Total\s*[:]\s*([\d,\.]+)", text)
    data["header"]["peso_liq"] = extract_regex(r"Peso Líquido Total\s*[:]\s*([\d,\.]+)", text)
    
    # 2. Extração de Itens (Adições)
    # Divide o texto onde encontrar "Adição" ou "Item"
    parts = re.split(r"(?:Adição|Item)\s*[:nNº°]*\s*(\d{3})", text)
    
    if len(parts) > 1:
        # Pula o cabeçalho (index 0) e itera pares (Número, Conteúdo)
        for i in range(1, len(parts), 2):
            num_adi = parts[i]
            block = parts[i+1]
            
            # Tenta extrair descrição e Part Number
            raw_desc = extract_regex(r"DENOMINACAO DO PRODUTO\s+(.*?)\s+C[ÓO]DIGO", block)
            if not raw_desc: raw_desc = extract_regex(r"Descrição.*[:]\s*(.+?)\n", block)

            adi = {
                "seq": num_adi,
                "descricao": raw_desc[:200], # Limita tamanho
                "ncm": extract_regex(r"NCM\s*[:]\s*([\d\.]+)", block).replace('.', ''),
                "peso": extract_regex(r"Peso Líquido.*?[:]\s*([\d,\.]+)", block),
                "qtd": extract_regex(r"Quantidade Estatística\s*[:]\s*([\d,\.]+)", block),
                "v_unit": "0", # Calculado ou extraído se houver campo explicito
                "valor_aduan": extract_regex(r"Valor Aduaneiro\s*[:]\s*([\d,\.]+)", block),
                "frete_item": extract_regex(r"Frete\s*[:]\s*([\d,\.]+)", block),
                "seguro_item": extract_regex(r"Seguro\s*[:]\s*([\d,\.]+)", block),
                "incoterm": extract_regex(r"Incoterm\s*[:]\s*([A-Z]{3})", block),
                # Impostos Item
                "ii_rec": extract_regex(r"II.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", block),
                "ipi_rec": extract_regex(r"IPI.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", block),
                "pis_rec": extract_regex(r"PIS.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", block),
                "cof_rec": extract_regex(r"COFINS.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", block)
            }
            data["itens"].append(adi)
    
    # 3. Totais Globais
    data["totais"]["frete"] = extract_regex(r"Total Frete\s*\(R\$\)\s*[:]\s*([\d,\.]+)", text)
    data["totais"]["seguro"] = extract_regex(r"Total Seguro\s*\(R\$\)\s*[:]\s*([\d,\.]+)", text)

    return data

# --- GERADOR XML (ESTRUTURA COMPLETA E RIGOROSA) ---
def generate_xml(data):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")
    
    # === 1. ADIÇÕES (Devem vir primeiro na sequência) ===
    for item in data["itens"]:
        ad = ET.SubElement(duimp, "adicao")
        
        # Acrescimo
        acr = ET.SubElement(ad, "acrescimo")
        ET.SubElement(acr, "codigoAcrescimo").text = "17"
        ET.SubElement(acr, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        ET.SubElement(acr, "moedaNegociadaCodigo").text = "978"
        ET.SubElement(acr, "moedaNegociadaNome").text = "EURO/COM.EUROPEIA"
        ET.SubElement(acr, "valorMoedaNegociada").text = format_xml_num("0", 15)
        ET.SubElement(acr, "valorReais").text = format_xml_num("106601", 15) # Exemplo fixo ou extrair rateio
        
        # Tributos e Dados Básicos da Adição
        ET.SubElement(ad, "cideValorAliquotaEspecifica").text = format_xml_num("0", 11)
        ET.SubElement(ad, "cideValorDevido").text = format_xml_num("0", 15)
        ET.SubElement(ad, "cideValorRecolher").text = format_xml_num("0", 15)
        ET.SubElement(ad, "codigoRelacaoCompradorVendedor").text = "3"
        ET.SubElement(ad, "codigoVinculoCompradorVendedor").text = "1"
        
        # COFINS
        ET.SubElement(ad, "cofinsAliquotaAdValorem").text = "00965"
        ET.SubElement(ad, "cofinsAliquotaEspecificaQuantidadeUnidade").text = format_xml_num("0", 9)
        ET.SubElement(ad, "cofinsAliquotaEspecificaValor").text = format_xml_num("0", 10)
        ET.SubElement(ad, "cofinsAliquotaReduzida").text = "00000"
        ET.SubElement(ad, "cofinsAliquotaValorDevido").text = format_xml_num(item["cof_rec"], 15)
        ET.SubElement(ad, "cofinsAliquotaValorRecolher").text = format_xml_num(item["cof_rec"], 15)
        
        # Condição de Venda
        ET.SubElement(ad, "condicaoVendaIncoterm").text = item["incoterm"] or "FCA"
        ET.SubElement(ad, "condicaoVendaLocal").text = "LOCAL"
        ET.SubElement(ad, "condicaoVendaMetodoValoracaoCodigo").text = "01"
        ET.SubElement(ad, "condicaoVendaMetodoValoracaoNome").text = "METODO 1"
        ET.SubElement(ad, "condicaoVendaMoedaCodigo").text = "978"
        ET.SubElement(ad, "condicaoVendaMoedaNome").text = "EURO"
        ET.SubElement(ad, "condicaoVendaValorMoeda").text = format_xml_num("0", 15)
        ET.SubElement(ad, "condicaoVendaValorReais").text = format_xml_num(item["valor_aduan"], 15)
        
        # Carga Item
        ET.SubElement(ad, "dadosCargaPaisProcedenciaCodigo").text = "000"
        ET.SubElement(ad, "dadosCargaUrfEntradaCodigo").text = "0000000"
        ET.SubElement(ad, "dadosCargaViaTransporteCodigo").text = "01"
        ET.SubElement(ad, "dadosCargaViaTransporteNome").text = "MARÍTIMA"
        
        # Dados Mercadoria
        ET.SubElement(ad, "dadosMercadoriaAplicacao").text = "REVENDA"
        ET.SubElement(ad, "dadosMercadoriaCodigoNaladiNCCA").text = "0000000"
        ET.SubElement(ad, "dadosMercadoriaCodigoNaladiSH").text = "00000000"
        ET.SubElement(ad, "dadosMercadoriaCodigoNcm").text = item["ncm"]
        ET.SubElement(ad, "dadosMercadoriaCondicao").text = "NOVA"
        ET.SubElement(ad, "dadosMercadoriaDescricaoTipoCertificado").text = "Sem Certificado"
        ET.SubElement(ad, "dadosMercadoriaIndicadorTipoCertificado").text = "1"
        ET.SubElement(ad, "dadosMercadoriaMedidaEstatisticaQuantidade").text = format_xml_num(item["qtd"], 14)
        ET.SubElement(ad, "dadosMercadoriaMedidaEstatisticaUnidade").text = "UNIDADE"
        ET.SubElement(ad, "dadosMercadoriaNomeNcm").text = "NOME GENERICO"
        ET.SubElement(ad, "dadosMercadoriaPesoLiquido").text = format_xml_num(item["peso"], 15)

        # Fornecedor
        ET.SubElement(ad, "fornecedorCidade").text = "BRUGNERA"
        ET.SubElement(ad, "fornecedorLogradouro").text = "VIALE EUROPA"
        ET.SubElement(ad, "fornecedorNome").text = "FORNECEDOR PADRAO"
        ET.SubElement(ad, "fornecedorNumero").text = "17"

        # Frete Item
        ET.SubElement(ad, "freteMoedaNegociadaCodigo").text = "978"
        ET.SubElement(ad, "freteMoedaNegociadaNome").text = "EURO"
        ET.SubElement(ad, "freteValorMoedaNegociada").text = format_xml_num("0", 15)
        ET.SubElement(ad, "freteValorReais").text = format_xml_num(item["frete_item"], 15)

        # II
        ET.SubElement(ad, "iiAcordoTarifarioTipoCodigo").text = "0"
        ET.SubElement(ad, "iiAliquotaAcordo").text = "00000"
        ET.SubElement(ad, "iiAliquotaAdValorem").text = "01800"
        ET.SubElement(ad, "iiAliquotaPercentualReducao").text = "00000"
        ET.SubElement(ad, "iiAliquotaReduzida").text = "00000"
        ET.SubElement(ad, "iiAliquotaValorCalculado").text = format_xml_num(item["ii_rec"], 15)
        ET.SubElement(ad, "iiAliquotaValorDevido").text = format_xml_num(item["ii_rec"], 15)
        ET.SubElement(ad, "iiAliquotaValorRecolher").text = format_xml_num(item["ii_rec"], 15)
        ET.SubElement(ad, "iiAliquotaValorReduzido").text = format_xml_num("0", 15)
        ET.SubElement(ad, "iiBaseCalculo").text = format_xml_num(item["valor_aduan"], 15)
        ET.SubElement(ad, "iiFundamentoLegalCodigo").text = "00"
        ET.SubElement(ad, "iiMotivoAdmissaoTemporariaCodigo").text = "00"
        ET.SubElement(ad, "iiRegimeTributacaoCodigo").text = "1"
        ET.SubElement(ad, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"

        # IPI
        ET.SubElement(ad, "ipiAliquotaAdValorem").text = "00000"
        ET.SubElement(ad, "ipiAliquotaEspecificaCapacidadeRecipciente").text = "00000"
        ET.SubElement(ad, "ipiAliquotaEspecificaQuantidadeUnidadeMedida").text = "000000000"
        ET.SubElement(ad, "ipiAliquotaEspecificaTipoRecipienteCodigo").text = "00"
        ET.SubElement(ad, "ipiAliquotaEspecificaValorUnidadeMedida").text = "0000000000"
        ET.SubElement(ad, "ipiAliquotaNotaComplementarTIPI").text = "00"
        ET.SubElement(ad, "ipiAliquotaReduzida").text = "00000"
        ET.SubElement(ad, "ipiAliquotaValorDevido").text = format_xml_num(item["ipi_rec"], 15)
        ET.SubElement(ad, "ipiAliquotaValorRecolher").text = format_xml_num(item["ipi_rec"], 15)
        ET.SubElement(ad, "ipiRegimeTributacaoCodigo").text = "4"
        ET.SubElement(ad, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"

        # Mercadoria Detalhe
        merc = ET.SubElement(ad, "mercadoria")
        ET.SubElement(merc, "descricaoMercadoria").text = item["descricao"]
        ET.SubElement(merc, "numeroSequencialItem").text = "01"
        ET.SubElement(merc, "quantidade").text = format_xml_num(item["qtd"], 14)
        ET.SubElement(merc, "unidadeMedida").text = "UNIDADE"
        ET.SubElement(merc, "valorUnitario").text = format_xml_num(item["v_unit"], 20)
        
        # Identificadores
        ET.SubElement(ad, "numeroAdicao").text = item["seq"].zfill(3)
        ET.SubElement(ad, "numeroDUIMP").text = data["header"]["numero"]
        ET.SubElement(ad, "numeroLI").text = "0000000000"
        ET.SubElement(ad, "paisAquisicaoMercadoriaCodigo").text = "386"
        ET.SubElement(ad, "paisAquisicaoMercadoriaNome").text = "ITALIA"
        ET.SubElement(ad, "paisOrigemMercadoriaCodigo").text = "386"
        ET.SubElement(ad, "paisOrigemMercadoriaNome").text = "ITALIA"
        
        # PIS
        ET.SubElement(ad, "pisCofinsBaseCalculoAliquotaICMS").text = "00000"
        ET.SubElement(ad, "pisCofinsBaseCalculoFundamentoLegalCodigo").text = "00"
        ET.SubElement(ad, "pisCofinsBaseCalculoPercentualReducao").text = "00000"
        ET.SubElement(ad, "pisCofinsBaseCalculoValor").text = format_xml_num(item["valor_aduan"], 15)
        ET.SubElement(ad, "pisCofinsFundamentoLegalReducaoCodigo").text = "00"
        ET.SubElement(ad, "pisCofinsRegimeTributacaoCodigo").text = "1"
        ET.SubElement(ad, "pisCofinsRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
        ET.SubElement(ad, "pisPasepAliquotaAdValorem").text = "00210"
        ET.SubElement(ad, "pisPasepAliquotaEspecificaQuantidadeUnidade").text = "000000000"
        ET.SubElement(ad, "pisPasepAliquotaEspecificaValor").text = "0000000000"
        ET.SubElement(ad, "pisPasepAliquotaReduzida").text = "00000"
        ET.SubElement(ad, "pisPasepAliquotaValorDevido").text = format_xml_num(item["pis_rec"], 15)
        ET.SubElement(ad, "pisPasepAliquotaValorRecolher").text = format_xml_num(item["pis_rec"], 15)
        
        # ICMS
        ET.SubElement(ad, "icmsBaseCalculoValor").text = format_xml_num("0", 15)
        ET.SubElement(ad, "icmsBaseCalculoAliquota").text = "01800"
        ET.SubElement(ad, "icmsBaseCalculoValorImposto").text = format_xml_num("0", 14)
        ET.SubElement(ad, "icmsBaseCalculoValorDiferido").text = format_xml_num("0", 14)

        # Reforma Tributaria (CBS/IBS) - Tags obrigatórias zeradas
        ET.SubElement(ad, "cbsIbsCst").text = "000"
        ET.SubElement(ad, "cbsIbsClasstrib").text = "000001"
        ET.SubElement(ad, "cbsBaseCalculoValor").text = format_xml_num("0", 15)
        ET.SubElement(ad, "cbsBaseCalculoAliquota").text = "00090"
        ET.SubElement(ad, "cbsBaseCalculoAliquotaReducao").text = "00000"
        ET.SubElement(ad, "cbsBaseCalculoValorImposto").text = format_xml_num("0", 14)
        ET.SubElement(ad, "ibsBaseCalculoValor").text = format_xml_num("0", 15)
        ET.SubElement(ad, "ibsBaseCalculoAliquota").text = "00010"
        ET.SubElement(ad, "ibsBaseCalculoAliquotaReducao").text = "00000"
        ET.SubElement(ad, "ibsBaseCalculoValorImposto").text = format_xml_num("0", 14)
        
        # Final Adicao
        ET.SubElement(ad, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
        ET.SubElement(ad, "seguroMoedaNegociadaCodigo").text = "220"
        ET.SubElement(ad, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
        ET.SubElement(ad, "seguroValorMoedaNegociada").text = format_xml_num("0", 15)
        ET.SubElement(ad, "seguroValorReais").text = format_xml_num(item["seguro_item"], 15)
        ET.SubElement(ad, "sequencialRetificacao").text = "00"
        ET.SubElement(ad, "valorMultaARecolher").text = format_xml_num("0", 15)
        ET.SubElement(ad, "valorMultaARecolherAjustado").text = format_xml_num("0", 15)
        ET.SubElement(ad, "valorReaisFreteInternacional").text = format_xml_num(item["frete_item"], 15)
        ET.SubElement(ad, "valorReaisSeguroInternacional").text = format_xml_num(item["seguro_item"], 15)
        ET.SubElement(ad, "valorTotalCondicaoVenda").text = format_xml_num("0", 11)
        ET.SubElement(ad, "vinculoCompradorVendedor").text = "Não há vinculação"

    # === 2. DADOS GERAIS (Após as Adições) ===
    arm = ET.SubElement(duimp, "armazem")
    ET.SubElement(arm, "nomeArmazem").text = "TCP"
    
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroCodigo").text = "9801303"
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP"
    ET.SubElement(duimp, "armazenamentoSetor").text = "002"
    ET.SubElement(duimp, "canalSelecaoParametrizada").text = "001"
    ET.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
    ET.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importação Própria"
    ET.SubElement(duimp, "cargaDataChegada").text = "20251120"
    ET.SubElement(duimp, "cargaNumeroAgente").text = "N/I"
    ET.SubElement(duimp, "cargaPaisProcedenciaCodigo").text = "386"
    ET.SubElement(duimp, "cargaPaisProcedenciaNome").text = "ITALIA"
    ET.SubElement(duimp, "cargaPesoBruto").text = format_xml_num(data["header"]["peso_bruto"], 15)
    ET.SubElement(duimp, "cargaPesoLiquido").text = format_xml_num(data["header"]["peso_liq"], 15)
    ET.SubElement(duimp, "cargaUrfEntradaCodigo").text = "0917800"
    ET.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
    
    # Docs e Datas (Fixos)
    ET.SubElement(duimp, "conhecimentoCargaEmbarqueData").text = "20251025"
    ET.SubElement(duimp, "conhecimentoCargaEmbarqueLocal").text = "GENOVA"
    ET.SubElement(duimp, "conhecimentoCargaId").text = "CEMERCANTE"
    ET.SubElement(duimp, "conhecimentoCargaIdMaster").text = "162505352452915"
    ET.SubElement(duimp, "conhecimentoCargaTipoCodigo").text = "12"
    ET.SubElement(duimp, "conhecimentoCargaTipoNome").text = "HBL"
    ET.SubElement(duimp, "conhecimentoCargaUtilizacao").text = "1"
    ET.SubElement(duimp, "conhecimentoCargaUtilizacaoNome").text = "Total"
    ET.SubElement(duimp, "dataDesembaraco").text = "20251124"
    ET.SubElement(duimp, "dataRegistro").text = "20251124"
    ET.SubElement(duimp, "documentoChegadaCargaCodigoTipo").text = "1"
    ET.SubElement(duimp, "documentoChegadaCargaNome").text = "Manifesto"
    ET.SubElement(duimp, "documentoChegadaCargaNumero").text = "1625502058594"

    # Embalagem
    emb = ET.SubElement(duimp, "embalagem")
    ET.SubElement(emb, "codigoTipoEmbalagem").text = "60"
    ET.SubElement(emb, "nomeEmbalagem").text = "PALLETS"
    ET.SubElement(emb, "quantidadeVolume").text = "00002"
    
    # Totais Globais
    ET.SubElement(duimp, "freteCollect").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "freteEmTerritorioNacional").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "freteMoedaNegociadaCodigo").text = "978"
    ET.SubElement(duimp, "freteMoedaNegociadaNome").text = "EURO/COM.EUROPEIA"
    ET.SubElement(duimp, "fretePrepaid").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "freteTotalDolares").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "freteTotalMoeda").text = format_xml_num("0", 5)
    ET.SubElement(duimp, "freteTotalReais").text = format_xml_num(data["totais"].get("frete"), 15)

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
    ET.SubElement(duimp, "importadorNome").text = data["header"]["importador"].strip()
    ET.SubElement(duimp, "importadorNomeRepresentanteLegal").text = "PAULO HENRIQUE LEITE FERREIRA"
    ET.SubElement(duimp, "importadorNumero").text = "02473058000188"
    ET.SubElement(duimp, "importadorNumeroTelefone").text = "41  30348150"
    ET.SubElement(duimp, "informacaoComplementar").text = "INFO COMPLEMENTAR..."

    # Rodapé
    ET.SubElement(duimp, "localDescargaTotalDolares").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "localDescargaTotalReais").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "localEmbarqueTotalDolares").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "localEmbarqueTotalReais").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "modalidadeDespachoCodigo").text = "1"
    ET.SubElement(duimp, "modalidadeDespachoNome").text = "Normal"
    ET.SubElement(duimp, "numeroDUIMP").text = data["header"]["numero"]
    ET.SubElement(duimp, "operacaoFundap").text = "N"

    # Pagamento (Bloco obrigatório para II, IPI, etc.)
    # Exemplo genérico, repetir para cada receita se necessário
    pag = ET.SubElement(duimp, "pagamento")
    ET.SubElement(pag, "agenciaPagamento").text = "3715"
    ET.SubElement(pag, "bancoPagamento").text = "341"
    ET.SubElement(pag, "codigoReceita").text = "0086"
    ET.SubElement(pag, "codigoTipoPagamento").text = "1"
    ET.SubElement(pag, "contaPagamento").text = "316273"
    ET.SubElement(pag, "dataPagamento").text = "20251124"
    ET.SubElement(pag, "nomeTipoPagamento").text = "Débito em Conta"
    ET.SubElement(pag, "numeroRetificacao").text = "00"
    ET.SubElement(pag, "valorJurosEncargos").text = format_xml_num("0", 9)
    ET.SubElement(pag, "valorMulta").text = format_xml_num("0", 9)
    ET.SubElement(pag, "valorReceita").text = format_xml_num("0", 15)

    ET.SubElement(duimp, "seguroMoedaNegociadaCodigo").text = "220"
    ET.SubElement(duimp, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
    ET.SubElement(duimp, "seguroTotalDolares").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "seguroTotalMoedaNegociada").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "seguroTotalReais").text = format_xml_num(data["totais"].get("seguro"), 15)
    ET.SubElement(duimp, "sequencialRetificacao").text = "00"
    ET.SubElement(duimp, "situacaoEntregaCarga").text = "ENTREGA CONDICIONADA"
    ET.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
    ET.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
    ET.SubElement(duimp, "totalAdicoes").text = str(len(data["itens"])).zfill(3)
    ET.SubElement(duimp, "urfDespachoCodigo").text = "0917800"
    ET.SubElement(duimp, "urfDespachoNome").text = "PORTO DE PARANAGUA"
    ET.SubElement(duimp, "valorTotalMultaARecolherAjustado").text = format_xml_num("0", 15)
    ET.SubElement(duimp, "viaTransporteCodigo").text = "01"
    ET.SubElement(duimp, "viaTransporteMultimodal").text = "N"
    ET.SubElement(duimp, "viaTransporteNome").text = "MARÍTIMA"
    ET.SubElement(duimp, "viaTransporteNomeTransportador").text = "MAERSK A/S"
    ET.SubElement(duimp, "viaTransporteNomeVeiculo").text = "MAERSK MEMPHIS"
    ET.SubElement(duimp, "viaTransportePaisTransportadorCodigo").text = "741"
    ET.SubElement(duimp, "viaTransportePaisTransportadorNome").text = "CINGAPURA"

    return root

# --- INTERFACE ---
def main():
    st.set_page_config(page_title="Hafele XML Parser", page_icon="📄", layout="centered")
    apply_clean_ui()
    
    st.markdown('<div class="main-box">', unsafe_allow_html=True)
    st.title("Conversor de DUIMP (Engine SAP)")
    st.markdown("Extração completa de 500+ páginas para o layout XML Hafele.")
    
    uploaded_file = st.file_uploader("Selecione o Extrato de Conferência (PDF)", type="pdf")
    
    if uploaded_file:
        if st.button("PROCESSAR ARQUIVO"):
            with st.spinner("Extraindo dados (Alta Performance)..."):
                # Barra de progresso visual
                progress = st.progress(0)
                for i in range(100):
                    time.sleep(0.005)
                    progress.progress(i + 1)
                
                try:
                    # 1. Extração
                    res = parse_pdf(uploaded_file)
                    
                    if res["itens"]:
                        # 2. Geração XML
                        xml_root = generate_xml(res)
                        
                        # Pretty Print para download
                        xml_str = ET.tostring(xml_root, 'utf-8')
                        xml_output = minidom.parseString(xml_str).toprettyxml(indent="    ")
                        
                        st.success("Arquivo processado com sucesso!")
                        
                        col1, col2 = st.columns(2)
                        col1.metric("Total de Adições", len(res["itens"]))
                        col2.metric("Nº DUIMP", res["header"]["numero"])
                        
                        st.markdown("---")
                        
                        st.download_button(
                            label="BAIXAR XML COMPATÍVEL",
                            data=xml_output,
                            file_name=f"DUIMP_{res['header']['numero']}.xml",
                            mime="text/xml"
                        )
                        
                        with st.expander("Ver Detalhes do Primeiro Item"):
                            st.json(res["itens"][0])
                    else:
                        st.error("Nenhum item identificado no PDF.")
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
