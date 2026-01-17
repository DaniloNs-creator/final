import streamlit as st
import fitz  # PyMuPDF
from lxml import etree
import re
import io

# ==============================================================================
# 1. FUNÇÕES DE FORMATAÇÃO (REGRA DE NEGÓCIO SAP)
# ==============================================================================

def clean_text(text):
    """Limpa espaços extras e quebras de linha indesejadas."""
    if not text: return ""
    return " ".join(text.split())

def fmt_sap(value, length=15):
    """
    Transforma valores monetários/numéricos do PDF para o layout SAP.
    Ex PDF: "1.234,56" -> Remove pontuação -> "123456" -> Zeros esq -> "000000000123456"
    Ex PDF: "123" (unidade) -> "123" -> Zeros esq -> "000000000000123"
    """
    if not value:
        return "0" * length
    
    # Remove qualquer coisa que não seja dígito (pontos, vírgulas, espaços, símbolos de moeda)
    digits_only = re.sub(r'[^\d]', '', value)
    
    # Preenche com zeros à esquerda até atingir o tamanho fixo
    return digits_only.zfill(length)

def extract_regex(pattern, text, default=""):
    """Função segura para extração via Regex."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return default

# ==============================================================================
# 2. CLASSE DE EXTRAÇÃO (PDF PARSER)
# ==============================================================================

class DuimpExtractor:
    def __init__(self, pdf_stream):
        self.doc = fitz.open(stream=pdf_stream, filetype="pdf")
        self.full_text = ""
        self.data = {
            "header": {},
            "adicoes": [],
            "totais": {},
            "pagamentos": []
        }

    def run_extraction(self):
        # 1. Extrair todo o texto mantendo a sequência física
        # Para 500 páginas, isso é muito rápido com PyMuPDF (segundos)
        full_content = []
        for page in self.doc:
            full_content.append(page.get_text("text", sort=True))
        self.full_text = "\n".join(full_content)

        # 2. Mapear Cabeçalho (Dados Gerais)
        # Ajuste os regex aqui baseados nos rótulos exatos do seu PDF
        self.data['header']['numero'] = extract_regex(r"DUIMP\s*[:]\s*([\d\.\/-]+)", self.full_text).replace('.', '').replace('/', '').replace('-', '')
        self.data['header']['importador'] = extract_regex(r"Importador\s*[:]\s*(.+?)\n", self.full_text)
        self.data['header']['peso_bruto_total'] = extract_regex(r"Peso Bruto Total\s*[:]\s*([\d,\.]+)", self.full_text)
        self.data['header']['peso_liq_total'] = extract_regex(r"Peso Líquido Total\s*[:]\s*([\d,\.]+)", self.full_text)
        self.data['header']['local_desembaraco'] = extract_regex(r"Local de Desembaraço\s*[:]\s*(.+?)\n", self.full_text)

        # 3. Mapear Adições (Lógica de Blocos)
        # A estratégia é dividir o texto onde aparece "Adição:" ou "Dados da Mercadoria"
        # Regex que identifica o início de uma adição (Ex: "Adição: 001")
        split_pattern = r"(?:Adição|Item)\s*[:nNº°]*\s*(\d{3})"
        blocks = re.split(split_pattern, self.full_text)
        
        # O split gera: [TextoAntes, NumeroAdi1, TextoAdi1, NumeroAdi2, TextoAdi2...]
        if len(blocks) > 1:
            # Pula o índice 0 (cabeçalho) e itera de 2 em 2 (Numero, Conteudo)
            for i in range(1, len(blocks), 2):
                num_adi = blocks[i]
                content = blocks[i+1]
                
                adi = {
                    "numero": num_adi,
                    "ncm": extract_regex(r"NCM\s*[:]\s*([\d\.]+)", content).replace('.', ''),
                    "valor_aduan": extract_regex(r"Valor Aduaneiro\s*[:]\s*([\d,\.]+)", content),
                    "incoterm": extract_regex(r"Incoterm\s*[:]\s*([A-Z]{3})", content),
                    "peso_liq": extract_regex(r"Peso Líquido\s*[:]\s*([\d,\.]+)", content),
                    "qtd_estat": extract_regex(r"Quantidade Estatística\s*[:]\s*([\d,\.]+)", content),
                    "frete_item": extract_regex(r"Frete\s*[:]\s*([\d,\.]+)", content), # Valor rateado
                    "seguro_item": extract_regex(r"Seguro\s*[:]\s*([\d,\.]+)", content), # Valor rateado
                    "descricao": extract_regex(r"Descrição da Mercadoria\s*[:]\s*(.+?)(?:\n|$)", content),
                    "pais_origem": extract_regex(r"País de Origem\s*[:]\s*(.+?)\n", content),
                    "fornecedor": extract_regex(r"Exportador|Fornecedor\s*[:]\s*(.+?)\n", content),
                    
                    # Tributos da Adição (II, IPI, PIS, COFINS)
                    # O regex busca o valor monetário associado ao rótulo dentro do bloco da adição
                    "val_ii": extract_regex(r"II.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", content),
                    "val_ipi": extract_regex(r"IPI.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", content),
                    "val_pis": extract_regex(r"PIS.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", content),
                    "val_cofins": extract_regex(r"COFINS.*?Valor a Recolher\s*[:]\s*([\d,\.]+)", content),
                }
                self.data['adicoes'].append(adi)

        # 4. Mapear Totais / Pagamentos (Rodapé)
        # Busca pagamentos globais se não estiverem por item
        self.data['totais']['frete_total_reais'] = extract_regex(r"Total Frete\s*\(R\$\)\s*[:]\s*([\d,\.]+)", self.full_text)
        self.data['totais']['seguro_total_reais'] = extract_regex(r"Total Seguro\s*\(R\$\)\s*[:]\s*([\d,\.]+)", self.full_text)
        self.data['totais']['fob_total_dolar'] = extract_regex(r"Valor FOB Total\s*\(USD\)\s*[:]\s*([\d,\.]+)", self.full_text)

        return self.data

# ==============================================================================
# 3. GERADOR XML (LAYOUT OBRIGATÓRIO)
# ==============================================================================

def build_xml(data):
    # Raiz
    root = etree.Element("ListaDeclaracoes")
    duimp = etree.SubElement(root, "duimp")

    # --- LOOP DE ADIÇÕES ---
    for item in data['adicoes']:
        adicao = etree.SubElement(duimp, "adicao")
        
        # Grupo: Acrescimo
        acrescimo = etree.SubElement(adicao, "acrescimo")
        etree.SubElement(acrescimo, "codigoAcrescimo").text = "17" # Fixo ou extrair se variar
        etree.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        etree.SubElement(acrescimo, "moedaNegociadaCodigo").text = "978" # Ideal: Mapear Euro/Dolar para código
        etree.SubElement(acrescimo, "moedaNegociadaNome").text = "EURO/COM.EUROPEIA"
        etree.SubElement(acrescimo, "valorMoedaNegociada").text = fmt_sap("0") # Extrair se disponível
        etree.SubElement(acrescimo, "valorReais").text = fmt_sap("0") # Extrair Rateio de Acréscimos

        # Tributos (CIDE, COFINS, II, IPI, PIS)
        # Nota: Preenchendo com valores extraídos do bloco da adição
        
        # CIDE (Geralmente zerado, manter fixo se não houver no PDF)
        etree.SubElement(adicao, "cideValorAliquotaEspecifica").text = fmt_sap("0", 11)
        etree.SubElement(adicao, "cideValorDevido").text = fmt_sap("0")
        etree.SubElement(adicao, "cideValorRecolher").text = fmt_sap("0")

        # Relação
        etree.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
        etree.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"

        # COFINS
        etree.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965" # Exemplo de alíquota fixa, ideal extrair
        etree.SubElement(adicao, "cofinsAliquotaEspecificaQuantidadeUnidade").text = fmt_sap("0", 9)
        etree.SubElement(adicao, "cofinsAliquotaEspecificaValor").text = fmt_sap("0", 10)
        etree.SubElement(adicao, "cofinsAliquotaReduzida").text = "00000"
        etree.SubElement(adicao, "cofinsAliquotaValorDevido").text = fmt_sap(item['val_cofins'])
        etree.SubElement(adicao, "cofinsAliquotaValorRecolher").text = fmt_sap(item['val_cofins'])

        # Condição de Venda
        etree.SubElement(adicao, "condicaoVendaIncoterm").text = item['incoterm'] or "FCA"
        etree.SubElement(adicao, "condicaoVendaLocal").text = "LOCAL_PADRAO"
        etree.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
        etree.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = "METODO 1 - VALOR DE TRANSACAO"
        etree.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "978"
        etree.SubElement(adicao, "condicaoVendaMoedaNome").text = "EURO"
        etree.SubElement(adicao, "condicaoVendaValorMoeda").text = fmt_sap("0") 
        etree.SubElement(adicao, "condicaoVendaValorReais").text = fmt_sap(item['valor_aduan']) # Aprox

        # Dados Carga (Item)
        etree.SubElement(adicao, "dadosCargaPaisProcedenciaCodigo").text = "000"
        etree.SubElement(adicao, "dadosCargaUrfEntradaCodigo").text = "0000000" # Preencher se houver no item
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
        etree.SubElement(adicao, "dadosMercadoriaNomeNcm").text = "NOME NCM"
        etree.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = fmt_sap(item['peso_liq'])

        # Fornecedor
        etree.SubElement(adicao, "fornecedorCidade").text = "CIDADE"
        etree.SubElement(adicao, "fornecedorLogradouro").text = "ENDERECO"
        etree.SubElement(adicao, "fornecedorNome").text = clean_text(item['fornecedor'])
        etree.SubElement(adicao, "fornecedorNumero").text = "00"

        # Frete Item
        etree.SubElement(adicao, "freteMoedaNegociadaCodigo").text = "978"
        etree.SubElement(adicao, "freteMoedaNegociadaNome").text = "EURO"
        etree.SubElement(adicao, "freteValorMoedaNegociada").text = fmt_sap("0")
        etree.SubElement(adicao, "freteValorReais").text = fmt_sap(item['frete_item'])

        # II (Imposto Importação)
        etree.SubElement(adicao, "iiAcordoTarifarioTipoCodigo").text = "0"
        etree.SubElement(adicao, "iiAliquotaAcordo").text = "00000"
        etree.SubElement(adicao, "iiAliquotaAdValorem").text = "01800" # Exemplo, extrair se possivel
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
        etree.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "1"
        etree.SubElement(adicao, "ipiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"

        # Detalhe Mercadoria
        merc = etree.SubElement(adicao, "mercadoria")
        etree.SubElement(merc, "descricaoMercadoria").text = clean_text(item['descricao'])[:100] # SAP limita caracteres?
        etree.SubElement(merc, "numeroSequencialItem").text = "01"
        etree.SubElement(merc, "quantidade").text = fmt_sap(item['qtd_estat'], 14)
        etree.SubElement(merc, "unidadeMedida").text = "UNIDADE"
        etree.SubElement(merc, "valorUnitario").text = fmt_sap("0", 20) # Calcular: valor_aduan / qtd

        # Identificadores da Adição
        etree.SubElement(adicao, "numeroAdicao").text = item['numero']
        etree.SubElement(adicao, "numeroDUIMP").text = data['header'].get('numero', '0000000000')
        etree.SubElement(adicao, "numeroLI").text = "0000000000"
        etree.SubElement(adicao, "paisAquisicaoMercadoriaCodigo").text = "000"
        etree.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = "PAIS"
        etree.SubElement(adicao, "paisOrigemMercadoriaCodigo").text = "000" # Mapear do texto "pais_origem"
        etree.SubElement(adicao, "paisOrigemMercadoriaNome").text = clean_text(item['pais_origem'])

        # PIS
        etree.SubElement(adicao, "pisCofinsBaseCalculoAliquotaICMS").text = "00000"
        etree.SubElement(adicao, "pisCofinsBaseCalculoFundamentoLegalCodigo").text = "00"
        etree.SubElement(adicao, "pisCofinsBaseCalculoPercentualReducao").text = "00000"
        etree.SubElement(adicao, "pisCofinsBaseCalculoValor").text = fmt_sap(item['valor_aduan'])
        etree.SubElement(adicao, "pisCofinsFundamentoLegalReducaoCodigo").text = "00"
        etree.SubElement(adicao, "pisCofinsRegimeTributacaoCodigo").text = "1"
        etree.SubElement(adicao, "pisCofinsRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
        etree.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00000"
        etree.SubElement(adicao, "pisPasepAliquotaEspecificaQuantidadeUnidade").text = "000000000"
        etree.SubElement(adicao, "pisPasepAliquotaEspecificaValor").text = "0000000000"
        etree.SubElement(adicao, "pisPasepAliquotaReduzida").text = "00000"
        etree.SubElement(adicao, "pisPasepAliquotaValorDevido").text = fmt_sap(item['val_pis'])
        etree.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = fmt_sap(item['val_pis'])

        # ICMS
        etree.SubElement(adicao, "icmsBaseCalculoValor").text = fmt_sap("0") # Extrair do PDF
        etree.SubElement(adicao, "icmsBaseCalculoAliquota").text = "00000"
        etree.SubElement(adicao, "icmsBaseCalculoValorImposto").text = fmt_sap("0")
        etree.SubElement(adicao, "icmsBaseCalculoValorDiferido").text = fmt_sap("0")

        # CBS/IBS (Tags obrigatórias mesmo que zeradas por enquanto)
        etree.SubElement(adicao, "cbsIbsCst").text = "000"
        etree.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
        etree.SubElement(adicao, "cbsBaseCalculoValor").text = fmt_sap("0")
        etree.SubElement(adicao, "cbsBaseCalculoAliquota").text = "00000"
        etree.SubElement(adicao, "cbsBaseCalculoAliquotaReducao").text = "00000"
        etree.SubElement(adicao, "cbsBaseCalculoValorImposto").text = fmt_sap("0")
        etree.SubElement(adicao, "ibsBaseCalculoValor").text = fmt_sap("0")
        etree.SubElement(adicao, "ibsBaseCalculoAliquota").text = "00000"
        etree.SubElement(adicao, "ibsBaseCalculoAliquotaReducao").text = "00000"
        etree.SubElement(adicao, "ibsBaseCalculoValorImposto").text = fmt_sap("0")

        # Final Adição
        etree.SubElement(adicao, "relacaoCompradorVendedor").text = "Nao ha vinculacao"
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
        etree.SubElement(adicao, "vinculoCompradorVendedor").text = "Nao Ha"

    # --- DADOS GERAIS (HEADER) ---
    armazem = etree.SubElement(duimp, "armazem")
    etree.SubElement(armazem, "nomeArmazem").text = "TCP" # Extrair do PDF
    
    etree.SubElement(duimp, "armazenamentoRecintoAduaneiroCodigo").text = "0000000"
    etree.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TERMINAL"
    etree.SubElement(duimp, "armazenamentoSetor").text = "000"
    etree.SubElement(duimp, "canalSelecaoParametrizada").text = "001" # Verde
    etree.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
    etree.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importacao Propria"
    etree.SubElement(duimp, "cargaDataChegada").text = "20250101" # Extrair data YYYYMMDD
    etree.SubElement(duimp, "cargaNumeroAgente").text = "0"
    etree.SubElement(duimp, "cargaPaisProcedenciaCodigo").text = "000"
    etree.SubElement(duimp, "cargaPaisProcedenciaNome").text = "PAIS"
    etree.SubElement(duimp, "cargaPesoBruto").text = fmt_sap(data['header'].get('peso_bruto_total'))
    etree.SubElement(duimp, "cargaPesoLiquido").text = fmt_sap(data['header'].get('peso_liq_total'))
    etree.SubElement(duimp, "cargaUrfEntradaCodigo").text = "0000000"
    etree.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO"
    
    # Conhecimento, Docs, Embalagem... (Preencher conforme PDF se disponível)
    # ... [Omitido por brevidade, seguir lógica acima para as tags restantes] ...
    
    # Totais Globais
    etree.SubElement(duimp, "freteCollect").text = fmt_sap("0")
    etree.SubElement(duimp, "freteEmTerritorioNacional").text = fmt_sap("0")
    etree.SubElement(duimp, "freteMoedaNegociadaCodigo").text = "978"
    etree.SubElement(duimp, "freteMoedaNegociadaNome").text = "EURO"
    etree.SubElement(duimp, "fretePrepaid").text = fmt_sap("0")
    etree.SubElement(duimp, "freteTotalDolares").text = fmt_sap("0")
    etree.SubElement(duimp, "freteTotalMoeda").text = fmt_sap("0")
    etree.SubElement(duimp, "freteTotalReais").text = fmt_sap(data['totais'].get('frete_total_reais'))

    # Importador
    etree.SubElement(duimp, "importadorNome").text = clean_text(data['header'].get('importador'))
    etree.SubElement(duimp, "numeroDUIMP").text = data['header'].get('numero')
    
    # Pagamentos (Aqui criamos um bloco para cada imposto federal geral, se o PDF tiver o resumo)
    # Exemplo: II, IPI, PIS, COFINS, Taxa Siscomex
    impostos_padrao = [("0086", "II"), ("1038", "IPI"), ("5602", "PIS"), ("5629", "COFINS"), ("7811", "TAXA")]
    for cod, nome in impostos_padrao:
        pag = etree.SubElement(duimp, "pagamento")
        etree.SubElement(pag, "codigoReceita").text = cod
        etree.SubElement(pag, "nomeTipoPagamento").text = "Debito em Conta"
        etree.SubElement(pag, "valorReceita").text = fmt_sap("0") # Extrair do PDF usando regex especifico para cada imposto no rodape

    # Final do XML
    etree.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
    etree.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
    etree.SubElement(duimp, "totalAdicoes").text = str(len(data['adicoes'])).zfill(3)

    return etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True)

# ==============================================================================
# 4. INTERFACE DO USUÁRIO
# ==============================================================================

def main():
    st.set_page_config(layout="wide", page_title="Conversor DUIMP SAP")
    st.title("Conversor de PDF DUIMP para XML SAP")
    st.markdown("**Regra:** Layout estrito, extração via Regex contextual, formatação sem pontuação.")

    uploaded_file = st.file_uploader("Arraste o PDF da DUIMP aqui", type="pdf")

    if uploaded_file:
        if st.button("Processar e Gerar XML"):
            try:
                with st.spinner("Lendo PDF e mapeando dados..."):
                    extractor = DuimpExtractor(uploaded_file.read())
                    structured_data = extractor.run_extraction()
                    
                    xml_content = build_xml(structured_data)
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.success("XML Gerado com Sucesso!")
                        st.download_button(
                            label="⬇️ Baixar XML",
                            data=xml_content,
                            file_name=f"DUIMP_{structured_data['header'].get('numero', 'SAP')}.xml",
                            mime="text/xml"
                        )
                    with col2:
                        with st.expander("Ver Dados Extraídos (Debug)"):
                            st.json(structured_data)
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

if __name__ == "__main__":
    main()
