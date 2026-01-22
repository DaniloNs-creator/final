import streamlit as st
import pdfplumber
import re
from lxml import etree
from xml.dom import minidom
import io

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Häfele | DUIMP Architect V31", page_icon="🏗️", layout="wide")

# ==============================================================================
# 0. CONSTANTES & LAYOUT
# ==============================================================================

# Dados FIXOS do Importador (Conforme solicitado)
IMPORTADOR_FIXO = {
    "importadorNome": "HAFELE BRASIL LTDA",
    "importadorNumero": "02473058000188", # CNPJ
    "importadorNomeRepresentanteLegal": "PAULO HENRIQUE LEITE FERREIRA",
    "importadorNumeroTelefone": "41 30348150",
    "importadorEnderecoLogradouro": "JOAO LEOPOLDO JACOMEL",
    "importadorEnderecoNumero": "4459",
    "importadorEnderecoComplemento": "CONJ: 6 E 7;",
    "importadorEnderecoBairro": "JARDIM PRIMAVERA",
    "importadorEnderecoMunicipio": "PIRAQUARA",
    "importadorEnderecoUf": "PR",
    "importadorEnderecoCep": "83302000",
    "importadorCodigoTipo": "1",
    "importadorCpfRepresentanteLegal": "00000000000"
}

# Estrutura dos Itens (Adições)
ADICAO_MAP = [
    {"tag": "acrescimo", "type": "complex", "children": [
        {"tag": "codigoAcrescimo", "default": "17"},
        {"tag": "denominacao", "default": "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"},
        {"tag": "moedaNegociadaCodigo", "default": "978"},
        {"tag": "moedaNegociadaNome", "default": "EURO/COM.EUROPEIA"},
        {"tag": "valorMoedaNegociada", "source": "v_frete_moeda", "default": "000000000000000"},
        {"tag": "valorReais", "source": "v_frete_reais", "default": "000000000000000"}
    ]},
    {"tag": "cideValorAliquotaEspecifica", "default": "00000000000"},
    {"tag": "cideValorDevido", "default": "000000000000000"},
    {"tag": "cideValorRecolher", "default": "000000000000000"},
    {"tag": "codigoRelacaoCompradorVendedor", "default": "3"},
    {"tag": "codigoVinculoCompradorVendedor", "default": "1"},
    
    # IMPOSTOS (Scan Local)
    {"tag": "cofinsAliquotaAdValorem", "source": "cofins_rate", "default": "00000"},
    {"tag": "cofinsAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "cofinsAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "cofinsAliquotaReduzida", "default": "00000"},
    {"tag": "cofinsAliquotaValorDevido", "source": "cofins_val", "default": "000000000000000"},
    {"tag": "cofinsAliquotaValorRecolher", "source": "cofins_val", "default": "000000000000000"},
    
    {"tag": "condicaoVendaIncoterm", "default": "FCA"},
    {"tag": "condicaoVendaLocal", "default": ""},
    {"tag": "condicaoVendaMetodoValoracaoCodigo", "default": "01"},
    {"tag": "condicaoVendaMetodoValoracaoNome", "default": "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"},
    {"tag": "condicaoVendaMoedaCodigo", "default": "978"},
    {"tag": "condicaoVendaMoedaNome", "default": "EURO/COM.EUROPEIA"},
    {"tag": "condicaoVendaValorMoeda", "source": "v_total_reais", "default": "000000000000000"},
    {"tag": "condicaoVendaValorReais", "source": "v_total_reais", "default": "000000000000000"},
    
    {"tag": "dadosCambiaisCoberturaCambialCodigo", "default": "1"},
    {"tag": "dadosCambiaisCoberturaCambialNome", "default": "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"},
    {"tag": "dadosCambiaisInstituicaoFinanciadoraCodigo", "default": "00"},
    {"tag": "dadosCambiaisInstituicaoFinanciadoraNome", "default": "N/I"},
    {"tag": "dadosCambiaisMotivoSemCoberturaCodigo", "default": "00"},
    {"tag": "dadosCambiaisMotivoSemCoberturaNome", "default": "N/I"},
    {"tag": "dadosCambiaisValorRealCambio", "default": "000000000000000"},
    {"tag": "dadosCargaPaisProcedenciaCodigo", "default": "249"},
    {"tag": "dadosCargaUrfEntradaCodigo", "default": "0917800"},
    {"tag": "dadosCargaViaTransporteCodigo", "default": "01"},
    {"tag": "dadosCargaViaTransporteNome", "default": "MARÍTIMA"},
    {"tag": "dadosMercadoriaAplicacao", "default": "REVENDA"},
    {"tag": "dadosMercadoriaCodigoNaladiNCCA", "default": "0000000"},
    {"tag": "dadosMercadoriaCodigoNaladiSH", "default": "00000000"},
    {"tag": "dadosMercadoriaCodigoNcm", "source": "ncm", "default": "00000000"},
    {"tag": "dadosMercadoriaCondicao", "default": "NOVA"},
    {"tag": "dadosMercadoriaDescricaoTipoCertificado", "default": "Sem Certificado"},
    {"tag": "dadosMercadoriaIndicadorTipoCertificado", "default": "1"},
    {"tag": "dadosMercadoriaMedidaEstatisticaQuantidade", "source": "quantidade_fmt", "default": "00000000000000"},
    {"tag": "dadosMercadoriaMedidaEstatisticaUnidade", "default": "UNIDADE"},
    {"tag": "dadosMercadoriaNomeNcm", "default": "DESCRIÇÃO PADRÃO NCM"},
    {"tag": "dadosMercadoriaPesoLiquido", "source": "peso_fmt", "default": "000000000000000"},
    
    {"tag": "dcrCoeficienteReducao", "default": "00000"},
    {"tag": "dcrIdentificacao", "default": "00000000"},
    {"tag": "dcrValorDevido", "default": "000000000000000"},
    {"tag": "dcrValorDolar", "default": "000000000000000"},
    {"tag": "dcrValorReal", "default": "000000000000000"},
    {"tag": "dcrValorRecolher", "default": "000000000000000"},
    {"tag": "fornecedorCidade", "source": "fornecedor_cidade", "default": "EXTERIOR"},
    {"tag": "fornecedorLogradouro", "source": "fornecedor_logradouro", "default": "RUA X"},
    {"tag": "fornecedorNome", "source": "fornecedor_nome", "default": "FORNECEDOR PADRAO"},
    {"tag": "fornecedorNumero", "source": "fornecedor_numero", "default": "00"},
    {"tag": "freteMoedaNegociadaCodigo", "default": "978"},
    {"tag": "freteMoedaNegociadaNome", "default": "EURO/COM.EUROPEIA"},
    {"tag": "freteValorMoedaNegociada", "default": "000000000000000"},
    {"tag": "freteValorReais", "default": "000000000000000"},
    
    {"tag": "iiAcordoTarifarioTipoCodigo", "default": "0"},
    {"tag": "iiAliquotaAcordo", "default": "00000"},
    {"tag": "iiAliquotaAdValorem", "source": "ii_rate", "default": "00000"},
    {"tag": "iiAliquotaPercentualReducao", "default": "00000"},
    {"tag": "iiAliquotaReduzida", "default": "00000"},
    {"tag": "iiAliquotaValorCalculado", "default": "000000000000000"},
    {"tag": "iiAliquotaValorDevido", "source": "ii_val", "default": "000000000000000"},
    {"tag": "iiAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "iiAliquotaValorReduzido", "default": "000000000000000"},
    {"tag": "iiBaseCalculo", "default": "000000000000000"},
    {"tag": "iiFundamentoLegalCodigo", "default": "00"},
    {"tag": "iiMotivoAdmissaoTemporariaCodigo", "default": "00"},
    {"tag": "iiRegimeTributacaoCodigo", "default": "1"},
    {"tag": "iiRegimeTributacaoNome", "default": "RECOLHIMENTO INTEGRAL"},
    
    {"tag": "ipiAliquotaAdValorem", "source": "ipi_rate", "default": "00000"},
    {"tag": "ipiAliquotaEspecificaCapacidadeRecipciente", "default": "00000"},
    {"tag": "ipiAliquotaEspecificaQuantidadeUnidadeMedida", "default": "000000000"},
    {"tag": "ipiAliquotaEspecificaTipoRecipienteCodigo", "default": "00"},
    {"tag": "ipiAliquotaEspecificaValorUnidadeMedida", "default": "0000000000"},
    {"tag": "ipiAliquotaNotaComplementarTIPI", "default": "00"},
    {"tag": "ipiAliquotaReduzida", "default": "00000"},
    {"tag": "ipiAliquotaValorDevido", "source": "ipi_val", "default": "000000000000000"},
    {"tag": "ipiAliquotaValorRecolher", "default": "000000000000000"},
    {"tag": "ipiRegimeTributacaoCodigo", "default": "4"},
    {"tag": "ipiRegimeTributacaoNome", "default": "SEM BENEFICIO"},
    
    {"tag": "mercadoria", "type": "complex", "children": [
        {"tag": "descricaoMercadoria", "source": "descricao_completa", "default": "ITEM"},
        {"tag": "numeroSequencialItem", "default": "01"},
        {"tag": "quantidade", "source": "quantidade_fmt", "default": "00000000000000"},
        {"tag": "unidadeMedida", "default": "UNIDADE"},
        {"tag": "valorUnitario", "source": "v_unit_fmt", "default": "00000000000000000000"}
    ]},
    
    {"tag": "numeroAdicao", "source": "numeroAdicao", "default": "000"},
    {"tag": "numeroDUIMP", "source": "numeroDUIMP", "default": "000"},
    {"tag": "numeroLI", "default": "0000000000"},
    {"tag": "paisAquisicaoMercadoriaCodigo", "default": "249"},
    {"tag": "paisAquisicaoMercadoriaNome", "default": "ESTADOS UNIDOS"},
    {"tag": "paisOrigemMercadoriaCodigo", "default": "249"},
    {"tag": "paisOrigemMercadoriaNome", "default": "ESTADOS UNIDOS"},
    {"tag": "pisCofinsBaseCalculoAliquotaICMS", "default": "00000"},
    {"tag": "pisCofinsBaseCalculoFundamentoLegalCodigo", "default": "00"},
    {"tag": "pisCofinsBaseCalculoPercentualReducao", "default": "00000"},
    {"tag": "pisCofinsBaseCalculoValor", "default": "000000000000000"},
    {"tag": "pisCofinsFundamentoLegalReducaoCodigo", "default": "00"},
    {"tag": "pisCofinsRegimeTributacaoCodigo", "default": "1"},
    {"tag": "pisCofinsRegimeTributacaoNome", "default": "RECOLHIMENTO INTEGRAL"},
    {"tag": "pisPasepAliquotaAdValorem", "source": "pis_rate", "default": "00000"},
    {"tag": "pisPasepAliquotaEspecificaQuantidadeUnidade", "default": "000000000"},
    {"tag": "pisPasepAliquotaEspecificaValor", "default": "0000000000"},
    {"tag": "pisPasepAliquotaReduzida", "default": "00000"},
    {"tag": "pisPasepAliquotaValorDevido", "source": "pis_val", "default": "000000000000000"},
    {"tag": "pisPasepAliquotaValorRecolher", "source": "pis_val", "default": "000000000000000"},
    
    {"tag": "icmsBaseCalculoValor", "source": "icms_base", "default": "000000000000000"},
    {"tag": "icmsBaseCalculoAliquota", "default": "01800"},
    {"tag": "icmsBaseCalculoValorImposto", "default": "00000000000000"},
    {"tag": "icmsBaseCalculoValorDiferido", "default": "00000000000000"},
    
    {"tag": "cbsIbsCst", "default": "000"},
    {"tag": "cbsIbsClasstrib", "default": "000001"},
    {"tag": "cbsBaseCalculoValor", "source": "icms_base", "default": "000000000000000"},
    {"tag": "cbsBaseCalculoAliquota", "default": "00090"},
    {"tag": "cbsBaseCalculoAliquotaReducao", "default": "00000"},
    {"tag": "cbsBaseCalculoValorImposto", "source": "cbs_val", "default": "00000000000000"},
    
    {"tag": "ibsBaseCalculoValor", "source": "icms_base", "default": "000000000000000"},
    {"tag": "ibsBaseCalculoAliquota", "default": "00010"},
    {"tag": "ibsBaseCalculoAliquotaReducao", "default": "00000"},
    {"tag": "ibsBaseCalculoValorImposto", "source": "ibs_val", "default": "00000000000000"},
    
    {"tag": "relacaoCompradorVendedor", "default": "Fabricante é desconhecido"},
    {"tag": "seguroMoedaNegociadaCodigo", "default": "220"},
    {"tag": "seguroMoedaNegociadaNome", "default": "DOLAR DOS EUA"},
    {"tag": "seguroValorMoedaNegociada", "default": "000000000000000"},
    {"tag": "seguroValorReais", "default": "000000000000000"},
    {"tag": "sequencialRetificacao", "default": "00"},
    {"tag": "valorMultaARecolher", "default": "000000000000000"},
    {"tag": "valorMultaARecolherAjustado", "default": "000000000000000"},
    {"tag": "valorReaisFreteInternacional", "default": "000000000000000"},
    {"tag": "valorReaisSeguroInternacional", "default": "000000000000000"},
    {"tag": "valorTotalCondicaoVenda", "source": "v_total_11", "default": "00000000000"},
    {"tag": "vinculoCompradorVendedor", "default": "Não há vinculação entre comprador e vendedor."}
]

FOOTER_TAGS = {
    "armazem": {"tag": "nomeArmazem", "default": "TCP"},
    "armazenamentoRecintoAduaneiroCodigo": "9801303",
    "armazenamentoRecintoAduaneiroNome": "TCP - TERMINAL",
    "armazenamentoSetor": "002",
    "canalSelecaoParametrizada": "001",
    "caracterizacaoOperacaoCodigoTipo": "1",
    "caracterizacaoOperacaoDescricaoTipo": "Importação Própria",
    "cargaDataChegada": "20251120",
    "cargaNumeroAgente": "N/I",
    "cargaPaisProcedenciaCodigo": "386",
    "cargaPaisProcedenciaNome": "",
    "cargaPesoBruto": "000000000000000",
    "cargaPesoLiquido": "000000000000000",
    "cargaUrfEntradaCodigo": "0917800",
    "cargaUrfEntradaNome": "PORTO DE PARANAGUA",
    "conhecimentoCargaEmbarqueData": "20251025",
    "conhecimentoCargaEmbarqueLocal": "EXTERIOR",
    "conhecimentoCargaId": "CE123456",
    "conhecimentoCargaIdMaster": "CE123456",
    "conhecimentoCargaTipoCodigo": "12",
    "conhecimentoCargaTipoNome": "HBL - House Bill of Lading",
    "conhecimentoCargaUtilizacao": "1",
    "conhecimentoCargaUtilizacaoNome": "Total",
    "dataDesembaraco": "20251124",
    "dataRegistro": "20251124",
    "documentoChegadaCargaCodigoTipo": "1",
    "documentoChegadaCargaNome": "Manifesto da Carga",
    "documentoChegadaCargaNumero": "1625502058594",
    "embalagem": [{"tag": "codigoTipoEmbalagem", "default": "60"}, {"tag": "nomeEmbalagem", "default": "PALLETS"}, {"tag": "quantidadeVolume", "default": "00001"}],
    "freteCollect": "000000000000000",
    "freteEmTerritorioNacional": "000000000000000",
    "freteMoedaNegociadaCodigo": "978",
    "freteMoedaNegociadaNome": "EURO/COM.EUROPEIA",
    "fretePrepaid": "000000000000000",
    "freteTotalDolares": "000000000000000",
    "freteTotalMoeda": "000000000000000",
    "freteTotalReais": "000000000000000",
    "icms": [{"tag": "agenciaIcms", "default": "00000"}, {"tag": "codigoTipoRecolhimentoIcms", "default": "3"}, {"tag": "nomeTipoRecolhimentoIcms", "default": "Exoneração do ICMS"}, {"tag": "numeroSequencialIcms", "default": "001"}, {"tag": "ufIcms", "default": "PR"}, {"tag": "valorTotalIcms", "default": "000000000000000"}],
    "informacaoComplementar": "Informações extraídas do Extrato Conferência.",
    "localDescargaTotalDolares": "000000000000000",
    "localDescargaTotalReais": "000000000000000",
    "localEmbarqueTotalDolares": "000000000000000",
    "localEmbarqueTotalReais": "000000000000000",
    "modalidadeDespachoCodigo": "1",
    "modalidadeDespachoNome": "Normal",
    "numeroDUIMP": "",
    "operacaoFundap": "N",
    "pagamento": [{"tag": "agenciaPagamento", "default": "3715"}, {"tag": "bancoPagamento", "default": "341"}, {"tag": "codigoReceita", "default": "0086"}, {"tag": "valorReceita", "default": "000000000000000"}],
    "seguroMoedaNegociadaCodigo": "220",
    "seguroMoedaNegociadaNome": "DOLAR DOS EUA",
    "seguroTotalDolares": "000000000000000",
    "seguroTotalMoedaNegociada": "000000000000000",
    "seguroTotalReais": "000000000000000",
    "sequencialRetificacao": "00",
    "situacaoEntregaCarga": "ENTREGA CONDICIONADA",
    "tipoDeclaracaoCodigo": "01",
    "tipoDeclaracaoNome": "CONSUMO",
    "totalAdicoes": "000",
    "urfDespachoCodigo": "0917800",
    "urfDespachoNome": "PORTO DE PARANAGUA",
    "valorTotalMultaARecolherAjustado": "000000000000000",
    "viaTransporteCodigo": "01",
    "viaTransporteMultimodal": "N",
    "viaTransporteNome": "MARÍTIMA",
    "viaTransporteNomeTransportador": "MAERSK A/S",
    "viaTransporteNomeVeiculo": "MAERSK",
    "viaTransportePaisTransportadorCodigo": "741",
    "viaTransportePaisTransportadorNome": "CINGAPURA"
}

# ==============================================================================
# 2. UTILITÁRIOS (FORMATAÇÃO)
# ==============================================================================

class DataFormatter:
    @staticmethod
    def clean_text(text):
        if not text: return ""
        return re.sub(r'\s+', ' ', str(text).replace('\n', ' ')).strip()

    @staticmethod
    def format_number(value, length=15):
        if not value: return "0" * length
        clean = re.sub(r'\D', '', str(value))
        return clean.zfill(length)
    
    @staticmethod
    def format_rate_xml(value):
        if not value: return "00000"
        val_clean = str(value).replace(",", ".").strip()
        try:
            val_float = float(val_clean)
            val_int = int(round(val_float * 100))
            return str(val_int).zfill(5)
        except: return "00000"

    @staticmethod
    def format_ncm(value):
        if not value: return "00000000"
        return re.sub(r'\D', '', str(value))[:8]

    @staticmethod
    def calculate_cbs_ibs(base_xml_string):
        try:
            base_int = int(base_xml_string)
            base_float = base_int / 100.0
            cbs = str(int(round(base_float * 0.009 * 100))).zfill(14)
            ibs = str(int(round(base_float * 0.001 * 100))).zfill(14)
            return cbs, ibs
        except: return "0".zfill(14), "0".zfill(14)

    @staticmethod
    def clean_partnumber(text):
        if not text: return ""
        # Remove lixo ao redor do código
        words = ["CÓDIGO", "CODIGO", "INTERNO", "PARTNUMBER", r"\(", r"\)"]
        for w in words:
            match = re.search(f"{w}(.*)", text, re.I | re.S)
            if match:
                text = match.group(1)
        return re.sub(r'\s+', ' ', text).strip().lstrip("- ").strip()

# ==============================================================================
# 3. MOTOR DE EXTRAÇÃO (AGRESSIVO)
# ==============================================================================

class DeepMiner:
    def __init__(self, file):
        self.file = file
        self.text = ""
        self.header = {}
        self.items = []

    def extract(self):
        # 1. Leitura Completa
        with pdfplumber.open(self.file) as pdf:
            pages = []
            total = len(pdf.pages)
            bar = st.progress(0)
            
            # Limpeza
            garbage = [r"Extrato de conferencia", r"Data, hora", r"Versão \d+", r"--- PAGE \d+", r"^\s*\d+\s*$", r"^\s*\/ \d+\s*$"]
            
            for i, page in enumerate(pdf.pages):
                txt = page.extract_text() or ""
                lines = [l for l in txt.split('\n') if not any(re.search(g, l, re.I) for g in garbage)]
                pages.append("\n".join(lines))
                if i % 5 == 0: bar.progress((i+1)/total)
            bar.progress(100)
            
        self.text = "\n".join(pages)
        
        # 2. Header
        duimp = re.search(r"Numero\s*[:\n]*\s*([\dBR]+)", self.text, re.I)
        self.header["duimp"] = duimp.group(1) if duimp else "00000000000"
        
        cnpj = re.search(r"CNPJ\s*[:\n]*\s*([\d./-]+)", self.text, re.IGNORECASE)
        self.header["cnpj"] = cnpj.group(1) if cnpj else ""
        
        pb = re.search(r"PESO BRUTO KG\s*[:]?\s*([\d.,]+)", self.text, re.I)
        self.header["pb"] = pb.group(1) if pb else "0"
        pl = re.search(r"PESO LIQUIDO KG\s*[:]?\s*([\d.,]+)", self.text, re.I)
        self.header["pl"] = pl.group(1) if pl else "0"

        # 3. Itens (Split Agressivo)
        # Quebra por "Nº Adição" ou "Nº do Item"
        splits = re.split(r"(Nº\s*Adição\s*[:\n]?\s*\d+)", self.text, flags=re.I)
        
        if len(splits) > 1:
            for i in range(1, len(splits), 2):
                marker = splits[i]
                content = splits[i+1]
                
                adi_num = re.search(r"\d+", marker).group()
                
                # Campos Chave
                pn_match = re.search(r"CÓDIGO INTERNO\s*\(PARTNUMBER\)\s*[:\n]?\s*(.+?)(?=\n)", content, re.I)
                if not pn_match: pn_match = re.search(r"PARTNUMBER\)\s*(.*?)\s*(?:PAIS|FABRICANTE)", content, re.I | re.S)
                pn = DataFormatter.clean_partnumber(pn_match.group(1)) if pn_match else ""
                
                desc_match = re.search(r"DENOMINACAO DO PRODUTO\s*[:\n]?\s*(.+?)(?=\n|CÓDIGO)", content, re.I | re.S)
                raw_desc = DataFormatter.clean_text(desc_match.group(1)) if desc_match else f"ITEM {adi_num}"
                
                full_desc = f"{pn} - {raw_desc}" if pn else raw_desc
                
                ncm = re.search(r"NCM\s*[:\n]*\s*([\d\.]+)", content)
                qtd = re.search(r"Qtde Unid\. Estatística\s*[:\n]?\s*([\d.,]+)", content, re.I)
                peso = re.search(r"Peso Líquido \(KG\)\s*[:\n]?\s*([\d.,]+)", content, re.I)
                val_tot = re.search(r"Valor Tot\. Cond Venda\s*[:\n]?\s*([\d.,]+)", content, re.I)
                
                # Valores Unitários Calculados se faltar
                v_unit = "0"
                if val_tot and qtd:
                    try:
                        vt = float(val_tot.group(1).replace('.','').replace(',','.'))
                        qt = float(qtd.group(1).replace('.','').replace(',','.'))
                        v_unit = f"{vt/qt:.5f}".replace('.', ',')
                    except: pass
                
                taxes = self._get_taxes(content)
                
                self.items.append({
                    "numeroAdicao": adi_num.zfill(3),
                    "descricao_completa": full_desc,
                    "ncm": ncm.group(1) if ncm else "00000000",
                    "quantidade_fmt": DataFormatter.format_number(qtd.group(1), 14) if qtd else "0"*14,
                    "peso_fmt": DataFormatter.format_number(peso.group(1), 15) if peso else "0"*15,
                    "v_total_reais": DataFormatter.format_number(val_tot.group(1), 15) if val_tot else "0"*15,
                    "v_total_11": DataFormatter.format_number(val_tot.group(1), 11) if val_tot else "0"*11,
                    "v_unit_fmt": DataFormatter.format_number(v_unit, 20),
                    "v_frete_reais": "0"*15,
                    "v_frete_moeda": "0"*15,
                    # Dados Fornecedor Padrão (se não achar no item)
                    "fornecedor_nome": "FORNECEDOR PADRAO",
                    "fornecedor_logradouro": "ENDERECO",
                    "fornecedor_numero": "00",
                    "fornecedor_cidade": "EXTERIOR",
                    **taxes
                })

    def _get_taxes(self, text):
        res = {}
        map_tax = {"ii": "IMPOSTO DE IMPORTAÇÃO", "ipi": "IPI", "pis": "PIS/PASEP", "cofins": "COFINS"}
        
        for k, label in map_tax.items():
            res[f"{k}_rate"] = "00000"
            res[f"{k}_val"] = "0"*15
            
            # Procura o bloco do imposto
            idx = text.find(label)
            if idx != -1:
                sub = text[idx:idx+350] # Janela de busca
                # Busca todos os números decimais brasileiros
                nums = re.findall(r"([\d]{1,3}(?:[.]\d{3})*,\d{2,4})", sub)
                
                candidates = []
                for n in nums:
                    try:
                        v = float(n.replace('.', '').replace(',', '.'))
                        candidates.append((v, n))
                    except: pass
                
                if candidates:
                    # Ordena: Menor = Alíquota, Valor = Segundo Menor ou Maior dependendo do contexto
                    candidates.sort(key=lambda x: x[0])
                    
                    # Alíquota é sempre o menor valor (ex: 1,65)
                    res[f"{k}_rate"] = str(candidates[0][1])
                    
                    # Valor do imposto:
                    # Se tiver 3 números (Base, Alíquota, Valor), o valor é o do meio.
                    # Se tiver 2 números (Alíquota, Valor), o valor é o maior.
                    if len(candidates) >= 2:
                        # Pega o segundo da lista ordenada (taxa < imposto < base)
                        res[f"{k}_val"] = str(candidates[1][1])
        return res

# ==============================================================================
# 4. GERADOR XML
# ==============================================================================

class XMLGenerator:
    def generate(self, parser):
        root = etree.Element("ListaDeclaracoes")
        duimp = etree.SubElement(root, "duimp")
        
        # 1. Adições
        for item in parser.items:
            ad = etree.SubElement(duimp, "adicao")
            
            # Cálculos
            cbs, ibs = DataFormatter.calculate_cbs_ibs(item["v_total_reais"])
            item["cbs_val"] = cbs
            item["ibs_val"] = ibs
            item["icms_base"] = item["v_total_reais"]
            item["numeroDUIMP"] = re.sub(r'[^a-zA-Z0-9]', '', parser.header["duimp"])

            # Preenchimento
            for field in ADICAO_FIELDS_ORDER:
                t = field["tag"]
                if field.get("type") == "complex":
                    parent = etree.SubElement(ad, t)
                    for child in field["children"]:
                        val = self._resolve(child, item)
                        etree.SubElement(parent, child["tag"]).text = val
                else:
                    val = self._resolve(field, item)
                    etree.SubElement(ad, t).text = val

        # 2. Rodapé + Importador Fixo
        for k, v in IMPORTADOR_FIXO.items():
            etree.SubElement(duimp, k).text = v

        for tag, config in FOOTER_TAGS.items():
            if isinstance(config, list):
                parent = etree.SubElement(duimp, tag)
                for sub in config: etree.SubElement(parent, sub["tag"]).text = sub["default"]
            elif isinstance(config, dict):
                parent = etree.SubElement(duimp, tag)
                etree.SubElement(parent, config["tag"]).text = config["default"]
            else:
                if tag not in IMPORTADOR_FIXO:
                    val = config
                    if tag == "numeroDUIMP": val = re.sub(r'[^a-zA-Z0-9]', '', parser.header["duimp"])
                    if tag == "cargaPesoBruto": val = DataFormatter.format_number(parser.header["pb"], 15)
                    if tag == "cargaPesoLiquido": val = DataFormatter.format_number(parser.header["pl"], 15)
                    if tag == "totalAdicoes": val = str(len(parser.items)).zfill(3)
                    etree.SubElement(duimp, tag).text = str(val)

        # 3. Finalização
        raw = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
        try:
            parsed = minidom.parseString(raw)
            pretty = parsed.toprettyxml(indent="    ")
            return re.sub(r'<\?xml.*?\?>', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', pretty, count=1)
        except: return raw

    def _resolve(self, config, data):
        if "source" in config:
            key = config["source"]
            if key in data:
                raw = data[key]
                if "rate" in key: return DataFormatter.format_rate_xml(raw)
                if "val" in key and "fmt" not in key: return DataFormatter.format_number(raw, 15)
                return str(raw)
        return config.get("default", "")

# ==============================================================================
# 5. APP
# ==============================================================================

def main():
    apply_custom_ui()
    st.markdown('<div class="header-container"><h1>Häfele | DUIMP Architect V31</h1></div>', unsafe_allow_html=True)
    
    f = st.file_uploader("Upload PDF", type="pdf")
    if f and st.button("PROCESSAR"):
        with st.spinner("Minerando PDF (Modo Agressivo)..."):
            proc = DeepMiner(f)
            proc.extract()
            
            if not proc.items:
                st.error("Erro: Nenhum item detectado. O PDF pode estar como imagem.")
            else:
                gen = XMLGenerator()
                xml = gen.generate(proc)
                
                st.success(f"Sucesso! {len(proc.items)} itens processados.")
                
                # Preview para validar a extração real
                with st.expander("Verificar Extração (Item 1)"):
                    st.write(proc.items[0])
                
                st.download_button("Baixar XML", xml, f"DUIMP_{proc.header['duimp']}.xml", "text/xml")

if __name__ == "__main__":
    main()
