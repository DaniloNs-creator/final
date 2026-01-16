import streamlit as st
import fitz  # PyMuPDF
import re
from lxml import etree
import io

# --- Configuração da Página ---
st.set_page_config(page_title="Conversor DUIMP Pro (Layout Rígido)", layout="wide")

# --- Definição da Ordem Estrita das Tags (Baseado no XML Modelo DUIMP_25BR...) ---
# Esta lista garante que as tags sejam escritas EXATAMENTE nesta sequência.
TAGS_ORDER_ADICAO = [
    "acrescimo", "cideValorAliquotaEspecifica", "cideValorDevido", "cideValorRecolher",
    "codigoRelacaoCompradorVendedor", "codigoVinculoCompradorVendedor", "cofinsAliquotaAdValorem",
    "cofinsAliquotaEspecificaQuantidadeUnidade", "cofinsAliquotaEspecificaValor", "cofinsAliquotaReduzida",
    "cofinsAliquotaValorDevido", "cofinsAliquotaValorRecolher", "condicaoVendaIncoterm",
    "condicaoVendaLocal", "condicaoVendaMetodoValoracaoCodigo", "condicaoVendaMetodoValoracaoNome",
    "condicaoVendaMoedaCodigo", "condicaoVendaMoedaNome", "condicaoVendaValorMoeda",
    "condicaoVendaValorReais", "dadosCambiaisCoberturaCambialCodigo", "dadosCambiaisCoberturaCambialNome",
    "dadosCambiaisInstituicaoFinanciadoraCodigo", "dadosCambiaisInstituicaoFinanciadoraNome",
    "dadosCambiaisMotivoSemCoberturaCodigo", "dadosCambiaisMotivoSemCoberturaNome",
    "dadosCambiaisValorRealCambio", "dadosCargaPaisProcedenciaCodigo", "dadosCargaUrfEntradaCodigo",
    "dadosCargaViaTransporteCodigo", "dadosCargaViaTransporteNome", "dadosMercadoriaAplicacao",
    "dadosMercadoriaCodigoNaladiNCCA", "dadosMercadoriaCodigoNaladiSH", "dadosMercadoriaCodigoNcm",
    "dadosMercadoriaCondicao", "dadosMercadoriaDescricaoTipoCertificado", "dadosMercadoriaIndicadorTipoCertificado",
    "dadosMercadoriaMedidaEstatisticaQuantidade", "dadosMercadoriaMedidaEstatisticaUnidade",
    "dadosMercadoriaNomeNcm", "dadosMercadoriaPesoLiquido", "dcrCoeficienteReducao",
    "dcrIdentificacao", "dcrValorDevido", "dcrValorDolar", "dcrValorReal", "dcrValorRecolher",
    "fornecedorCidade", "fornecedorLogradouro", "fornecedorNome", "fornecedorNumero",
    "freteMoedaNegociadaCodigo", "freteMoedaNegociadaNome", "freteValorMoedaNegociada",
    "freteValorReais", "iiAcordoTarifarioTipoCodigo", "iiAliquotaAcordo", "iiAliquotaAdValorem",
    "iiAliquotaPercentualReducao", "iiAliquotaReduzida", "iiAliquotaValorCalculado",
    "iiAliquotaValorDevido", "iiAliquotaValorRecolher", "iiAliquotaValorReduzido",
    "iiBaseCalculo", "iiFundamentoLegalCodigo", "iiMotivoAdmissaoTemporariaCodigo",
    "iiRegimeTributacaoCodigo", "iiRegimeTributacaoNome", "ipiAliquotaAdValorem",
    "ipiAliquotaEspecificaCapacidadeRecipciente", "ipiAliquotaEspecificaQuantidadeUnidadeMedida",
    "ipiAliquotaEspecificaTipoRecipienteCodigo", "ipiAliquotaEspecificaValorUnidadeMedida",
    "ipiAliquotaNotaComplementarTIPI", "ipiAliquotaReduzida", "ipiAliquotaValorDevido",
    "ipiAliquotaValorRecolher", "ipiRegimeTributacaoCodigo", "ipiRegimeTributacaoNome",
    "numeroAdicao", "numeroDUIMP", "numeroLI", "paisAquisicaoMercadoriaCodigo",
    "paisAquisicaoMercadoriaNome", "paisOrigemMercadoriaCodigo", "paisOrigemMercadoriaNome",
    "pisCofinsBaseCalculoAliquotaICMS", "pisCofinsBaseCalculoFundamentoLegalCodigo",
    "pisCofinsBaseCalculoPercentualReducao", "pisCofinsBaseCalculoValor",
    "pisCofinsFundamentoLegalReducaoCodigo", "pisCofinsRegimeTributacaoCodigo",
    "pisCofinsRegimeTributacaoNome", "pisPasepAliquotaAdValorem",
    "pisPasepAliquotaEspecificaQuantidadeUnidade", "pisPasepAliquotaEspecificaValor",
    "pisPasepAliquotaReduzida", "pisPasepAliquotaValorDevido", "pisPasepAliquotaValorRecolher",
    "relacaoCompradorVendedor", "seguroMoedaNegociadaCodigo", "seguroMoedaNegociadaNome",
    "seguroValorMoedaNegociada", "seguroValorReais", "sequencialRetificacao",
    "valorMultaARecolher", "valorMultaARecolherAjustado", "valorReaisFreteInternacional",
    "valorReaisSeguroInternacional", "valorTotalCondicaoVenda", "vinculoCompradorVendedor",
    "mercadoria", # Tag complexa
    "icmsBaseCalculoValor", "icmsBaseCalculoAliquota", "icmsBaseCalculoValorImposto",
    "icmsBaseCalculoValorDiferido", "cbsIbsCst", "cbsIbsClasstrib", "cbsBaseCalculoValor",
    "cbsBaseCalculoAliquota", "cbsBaseCalculoAliquotaReducao", "cbsBaseCalculoValorImposto",
    "ibsBaseCalculoValor", "ibsBaseCalculoAliquota", "ibsBaseCalculoAliquotaReducao",
    "ibsBaseCalculoValorImposto"
]

# --- Classes de Processamento ---

class DataFormatter:
    @staticmethod
    def clean_text(text):
        """Limpa espaços extras e quebras de linha."""
        if not text: return ""
        return " ".join(text.split()).strip()

    @staticmethod
    def format_number(value, length=15):
        """Formata numeros para o padrão '000000000100000' (sem ponto/virgula)."""
        if not value: return "0" * length
        # Mantém apenas digitos
        clean = re.sub(r'\D', '', value)
        return clean.zfill(length)

    @staticmethod
    def format_ncm(value):
        """Remove pontos do NCM."""
        if not value: return ""
        return re.sub(r'\D', '', value).strip()[:8]

class PDFProcessor:
    def __init__(self, file_bytes):
        self.doc = fitz.open(stream=file_bytes, filetype="pdf")
        self.full_text = ""
        self.header_info = {}
        self.items = []

    def preprocess_text(self):
        """
        Lê o PDF e remove cabeçalhos/rodapés repetitivos ANTES de processar.
        Isso evita que dados de cabeçalho 'sujem' as adições.
        """
        raw_lines = []
        for page in self.doc:
            text = page.get_text("text")
            lines = text.split('\n')
            for line in lines:
                l = line.strip()
                # Remove linhas de "lixo" identificadas no extrato
                if "Extrato da DUIMP" in l: continue
                if "Data, hora e responsável" in l: continue
                if "Extrato da Duimp" in l and "Versão" in l: continue
                if re.match(r'^\d+\s*/\s*\d+$', l): continue # Paginação 1/14
                
                raw_lines.append(line) # Mantém original para regex funcionar melhor com espaços
        
        self.full_text = "\n".join(raw_lines)

    def extract_header(self):
        """Extrai dados gerais da capa (DUIMP, Importador, Totais)."""
        txt = self.full_text
        
        # Regex ajustados para o layout do PDF limpo
        self.header_info["numeroDUIMP"] = re.search(r"Extrato da Duimp\s+([\w\-\/]+)", self.doc[0].get_text("text")) # Pega da pág 1 bruta
        if self.header_info["numeroDUIMP"]:
            self.header_info["numeroDUIMP"] = self.header_info["numeroDUIMP"].group(1).split('/')[0].strip()
        
        self.header_info["cnpj"] = re.search(r"CNPJ do importador:\s*([\d\.\/\-]+)", txt)
        self.header_info["nomeImportador"] = re.search(r"Nome do importador:\s*\n?(.+)", txt)
        self.header_info["pesoBruto"] = re.search(r"Peso Bruto \(kg\):\s*([\d\.,]+)", txt)
        self.header_info["pesoLiquido"] = re.search(r"Peso Liquido \(kg\):\s*([\d\.,]+)", txt)
        self.header_info["urf"] = re.search(r"Unidade de despacho:\s*([\d]+)", txt)
        self.header_info["paisProcedencia"] = re.search(r"País de Procedência:\s*\n?(.+)", txt)

        # Limpeza
        for k, v in self.header_info.items():
            if hasattr(v, 'group'):
                self.header_info[k] = v.group(1).strip()

    def extract_items(self):
        """Extrai cada item (Adição) usando regex de bloco."""
        # Divide o texto pelos marcadores de Item (ex: "Item 00001")
        # Regex busca "Item" seguido de 5 digitos
        blocks = re.split(r"Item\s+(\d{5})", self.full_text)
        
        # blocks[0] é lixo inicial. blocks[1]=NumItem1, blocks[2]=TextoItem1, blocks[3]=NumItem2...
        if len(blocks) > 1:
            for i in range(1, len(blocks), 2):
                num_item = blocks[i]
                content = blocks[i+1]
                
                item_data = {"numeroAdicao": num_item}
                
                # Extração de campos específicos dentro do bloco do item
                patterns = {
                    "ncm": r"NCM:\s*([\d\.]+)",
                    "paisOrigem": r"País de origem:\s*\n?(.+)",
                    "quantidade": r"Quantidade na unidade estatística:\s*([\d\.,]+)",
                    "unidade": r"Unidade estatística:\s*(.+)",
                    "pesoLiquidoItem": r"Peso líquido \(kg\):\s*([\d\.,]+)",
                    "valorMoeda": r"Valor total na condição de venda:\s*([\d\.,]+)",
                    "valorUnitario": r"Valor unitário na condição de venda:\s*([\d\.,]+)",
                    "moeda": r"Moeda negociada:\s*(.+)",
                    "condicaoVenda": r"Condição de venda:\s*(.+)", # Se houver
                    # Descrição: Pega tudo entre "Detalhamento" e o próximo label forte
                    "descricao": r"Detalhamento do Produto:\s*(.+?)(?=\n\s*(?:Número de Identificação|Versão|Código de Class|Descrição complementar))"
                }

                for key, pattern in patterns.items():
                    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                    if match:
                        item_data[key] = match.group(1).strip()
                    else:
                        item_data[key] = ""

                self.items.append(item_data)

class XMLGenerator:
    def __init__(self, pdf_processor):
        self.pp = pdf_processor
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self):
        h = self.pp.header_info
        duimp_clean = h.get("numeroDUIMP", "").replace("-", "").replace(".", "")

        # --- Geração das Adições ---
        for it in self.pp.items:
            adicao = etree.SubElement(self.duimp, "adicao")
            
            # Prepara dados para preencher na ordem correta
            data_map = {
                "numeroAdicao": it["numeroAdicao"][-3:], # Ex: 001
                "numeroDUIMP": duimp_clean,
                "numeroLI": "0000000000",
                "condicaoVendaIncoterm": "FCA", # Default ou extrair se tiver
                "condicaoVendaMoedaNome": it.get("moeda", "DOLAR DOS EUA").upper(),
                "condicaoVendaValorMoeda": DataFormatter.format_number(it.get("valorMoeda"), 15),
                "dadosCargaPaisProcedenciaCodigo": "076", # Exemplo fixo ou extrair de tabela de-para
                "dadosMercadoriaAplicacao": "REVENDA",
                "dadosMercadoriaCodigoNcm": DataFormatter.format_ncm(it.get("ncm")),
                "dadosMercadoriaCondicao": "NOVA",
                "dadosMercadoriaMedidaEstatisticaQuantidade": DataFormatter.format_number(it.get("quantidade"), 15),
                "dadosMercadoriaMedidaEstatisticaUnidade": it.get("unidade", "UNIDADE").upper(),
                "dadosMercadoriaPesoLiquido": DataFormatter.format_number(it.get("pesoLiquidoItem"), 15),
                "dadosMercadoriaNomeNcm": "Descrição Padrão NCM", # PDF não costuma trazer nome NCM limpo
                "paisOrigemMercadoriaNome": it.get("paisOrigem", "CHINA, REPUBLICA POPULAR").upper(),
                "paisAquisicaoMercadoriaNome": it.get("paisOrigem", "CHINA, REPUBLICA POPULAR").upper(), # Geralmente igual origem
                "valorTotalCondicaoVenda": DataFormatter.format_number(it.get("valorMoeda"), 11), # Tamanho variavel no XML modelo?
                "vinculoCompradorVendedor": "Não há vinculação entre comprador e vendedor.",
                # Valores padrão para tags obrigatórias que não estão no extrato PDF simplificado
                "iiRegimeTributacaoNome": "RECOLHIMENTO INTEGRAL",
                "pisCofinsRegimeTributacaoNome": "RECOLHIMENTO INTEGRAL",
                "ipiRegimeTributacaoNome": "SEM BENEFICIO",
                "codigoRelacaoCompradorVendedor": "3",
                "codigoVinculoCompradorVendedor": "1"
            }

            # Itera sobre a LISTA ESTRITA de tags para criar na ordem
            for tag in TAGS_ORDER_ADICAO:
                if tag == "mercadoria":
                    # Sub-bloco mercadoria
                    merc = etree.SubElement(adicao, "mercadoria")
                    
                    # Descrição Limpa (sem quebras)
                    desc_clean = DataFormatter.clean_text(it.get("descricao", "DESCRIÇÃO NÃO ENCONTRADA"))
                    etree.SubElement(merc, "descricaoMercadoria").text = desc_clean[:3999] # Truncate safe
                    
                    etree.SubElement(merc, "numeroSequencialItem").text = it["numeroAdicao"][-2:]
                    etree.SubElement(merc, "quantidade").text = DataFormatter.format_number(it.get("quantidade"), 14)
                    etree.SubElement(merc, "unidadeMedida").text = it.get("unidade", "UNIDADE").upper()
                    etree.SubElement(merc, "valorUnitario").text = DataFormatter.format_number(it.get("valorUnitario"), 20)
                
                elif tag == "acrescimo":
                    # Bloco Acrescimo (Exemplo Fixo para estrutura)
                    acr = etree.SubElement(adicao, "acrescimo")
                    etree.SubElement(acr, "codigoAcrescimo").text = "17"
                    etree.SubElement(acr, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
                    etree.SubElement(acr, "moedaNegociadaCodigo").text = "978"
                    etree.SubElement(acr, "moedaNegociadaNome").text = "DOLAR DOS EUA"
                    etree.SubElement(acr, "valorMoedaNegociada").text = "000000000000000"
                    etree.SubElement(acr, "valorReais").text = "000000000000000"
                
                else:
                    # Tags normais
                    val = data_map.get(tag)
                    if val is not None:
                         etree.SubElement(adicao, tag).text = val
                    else:
                        # Se não tem mapeado, preenche com Zeros ou Vazio conforme padrão do modelo
                        if "Valor" in tag or "Quantidade" in tag or "Peso" in tag:
                            etree.SubElement(adicao, tag).text = "0" * 15
                        elif "Codigo" in tag and "Moeda" not in tag:
                             etree.SubElement(adicao, tag).text = "00"
                        else:
                            etree.SubElement(adicao, tag).text = "" # Tag vazia para manter estrutura

        # --- Dados Gerais da DUIMP (Fim do XML) ---
        armazem = etree.SubElement(self.duimp, "armazem")
        etree.SubElement(armazem, "nomeArmazem").text = "IRF - PORTO DE SUAPE"
        
        etree.SubElement(self.duimp, "armazenamentoRecintoAduaneiroCodigo").text = h.get("urf", "0000000")
        etree.SubElement(self.duimp, "cargaPesoBruto").text = DataFormatter.format_number(h.get("pesoBruto"), 15)
        etree.SubElement(self.duimp, "cargaPesoLiquido").text = DataFormatter.format_number(h.get("pesoLiquido"), 15)
        etree.SubElement(self.duimp, "importadorNome").text = h.get("nomeImportador", "")
        etree.SubElement(self.duimp, "importadorNumero").text = DataFormatter.clean_text(h.get("cnpj")).replace(".", "").replace("/", "").replace("-", "")
        etree.SubElement(self.duimp, "numeroDUIMP").text = duimp_fmt
        
        # Tags finais obrigatórias
        etree.SubElement(self.duimp, "totalAdicoes").text = str(len(self.pp.items)).zfill(3)
        etree.SubElement(self.duimp, "viaTransporteNome").text = "MARÍTIMA"
        
        return etree.tostring(self.root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# --- Interface Streamlit ---

st.header("🚀 Extrator de DUIMP com Layout Rígido")
st.markdown("""
Esta ferramenta foi ajustada para:
1. **Remover cabeçalhos repetitivos** do PDF que quebram os dados.
2. **Forçar a sequência exata de tags** conforme o XML modelo `DUIMP_25BR...`.
3. **Formatar números** com zeros à esquerda (ex: `0000001000`).
""")

uploaded_file = st.file_uploader("Carregue o Extrato DUIMP (PDF)", type="pdf")

if uploaded_file:
    if st.button("Gerar XML"):
        with st.spinner("Processando..."):
            try:
                # 1. Processamento
                processor = PDFProcessor(uploaded_file.read())
                processor.preprocess_text() # Limpeza crucial
                processor.extract_header()
                processor.extract_items()
                
                # 2. Geração XML
                generator = XMLGenerator(processor)
                xml_data = generator.build()
                
                # 3. Output
                st.success(f"XML Gerado com {len(processor.items)} adições!")
                
                # Botão Download
                st.download_button(
                    label="📥 Baixar XML Formatado",
                    data=xml_data,
                    file_name="DUIMP_Formatada.xml",
                    mime="text/xml"
                )
                
                # Preview
                with st.expander("Visualizar XML (Primeiras 50 linhas)"):
                    st.code(xml_data.decode("utf-8")[:3000], language="xml")
                    
                with st.expander("Debug: Dados Extraídos"):
                    st.json(processor.items)
                    
            except Exception as e:
                st.error(f"Erro Crítico: {e}")
