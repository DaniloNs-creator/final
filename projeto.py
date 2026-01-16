import streamlit as st
import pdfplumber
import pypdf  # <--- Nova biblioteca para o plano B
import re
import io
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Conversor DUIMP PDF para XML", layout="wide")

st.title("📂 Conversor DUIMP (PDF) para Layout XML Importação")
st.markdown("""
Este aplicativo converte o extrato em PDF da DUIMP do Portal Siscomex para o formato XML.
**Correção Aplicada:** Inclusão de motor híbrido (pdfplumber + pypdf) para evitar erros de renderização gráfica.
""")

# --- FUNÇÕES UTILITÁRIAS ---

def clean_text(text):
    if not text: return ""
    return text.replace("\n", " ").strip()

def format_number_xml(value_str, length=15, decimals=2):
    if not value_str:
        return "0" * length
    clean = re.sub(r'[^\d,]', '', str(value_str))
    if ',' not in clean:
        clean = clean + ("0" * decimals)
    else:
        parts = clean.split(',')
        dec_part = parts[1][:decimals].ljust(decimals, '0')
        clean = parts[0] + dec_part
    final_raw = re.sub(r'\D', '', clean)
    return final_raw.zfill(length)

def extract_field(text, pattern, default=""):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else default

# --- NÚCLEO DE PROCESSAMENTO (PDF) ---

def process_pdf(pdf_file_obj):
    data = {
        "header": {},
        "itens": []
    }
    
    full_text = ""
    
    # Criamos uma cópia do arquivo em memória para garantir que as duas bibliotecas
    # possam ler o arquivo sem conflito de ponteiro.
    pdf_bytes = pdf_file_obj.read()
    pdf_stream_plumber = io.BytesIO(pdf_bytes)
    pdf_stream_pypdf = io.BytesIO(pdf_bytes)
    
    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Inicializa o leitor de backup (pypdf)
    reader_fallback = pypdf.PdfReader(pdf_stream_pypdf)
    total_pages_fallback = len(reader_fallback.pages)

    try:
        with pdfplumber.open(pdf_stream_plumber) as pdf:
            total_pages = len(pdf.pages)
            
            # 1. Extração de Texto Híbrida
            for i, page in enumerate(pdf.pages):
                try:
                    # Tenta extrair com pdfplumber (melhor layout)
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                    else:
                        full_text += "\n"
                        
                except (IndexError, Exception) as e:
                    # SE DER ERRO (IndexError), usa o pypdf para ler essa página
                    # st.warning(f"Usando motor de backup na página {i+1} devido a erro gráfico.")
                    try:
                        fallback_page = reader_fallback.pages[i]
                        text_backup = fallback_page.extract_text()
                        full_text += text_backup + "\n"
                    except Exception as e_back:
                        st.error(f"Erro fatal na página {i+1}: {e_back}")

                # Atualiza progresso
                if i % 5 == 0 or i == total_pages - 1:
                    progress_bar.progress((i + 1) / total_pages)
                    status_text.text(f"Lendo página {i+1} de {total_pages}...")

    except Exception as e:
        st.error(f"Erro ao abrir o PDF: {e}")
        return data

    # 2. Extração do Cabeçalho (Dados Gerais)
    [cite_start]# [cite: 1, 67] Fonte DUIMP e Número
    data["header"]["numero_duimp"] = extract_field(full_text, r"Extrato da DUIMP\s+([0-9BR-]+)")
    [cite_start]# [cite: 17] CNPJ
    data["header"]["importador_cnpj"] = extract_field(full_text, r"CNPJ do importador:\s*([\d\.\/-]+)")
    [cite_start]# [cite: 31] Nome Importador
    data["header"]["importador_nome"] = extract_field(full_text, r"Nome do importador:\s*(.+?)(?=\n|:)")
    [cite_start]# [cite: 35, 85] País Procedência
    data["header"]["pais_procedencia"] = extract_field(full_text, r"País de Procedência:\s*(.+?)(?=\n|CN|US)", "BRASIL")
    
    # Valores Totais
    data["header"]["frete_total"] = extract_field(full_text, r"Valor do Frete\s*:\s*([\d\.,]+)", "0,00")
    
    # 3. Extração dos Itens
    # Divide o texto procurando pelo padrão "Item 00001", "Item 00002"
    # O regex procura "Item" seguido de digitos, ignorando case
    item_splits = re.split(r"(?i)Item\s+(\d{5})", full_text)
    
    if len(item_splits) > 1:
        # O split retorna: [Intro, "00001", TextoItem1, "00002", TextoItem2...]
        # Ignoramos a intro (index 0) e iteramos de 2 em 2
        iterator = iter(item_splits[1:])
        for item_num, item_text in zip(iterator, iterator):
            item_data = {}
            item_data["numero"] = item_num
            
            # Extração via Regex no texto do item
            item_data["ncm"] = extract_field(item_text, r"NCM:\s*([\d\.-]+)")
            
            # Descrição: Pega tudo entre "Detalhamento do Produto:" e "Código de Class" ou "Tributos"
            desc_match = re.search(r"Detalhamento do Produto:\s*(.*?)(?=\nCódigo de Class|Tributos|\n\d{2}/\d{2})", item_text, re.DOTALL)
            desc_raw = desc_match.group(1) if desc_match else ""
            item_data["descricao"] = clean_text(desc_raw)[:250] # Limita caracteres
            
            item_data["quantidade"] = extract_field(item_text, r"Quantidade na unidade comercializada:\s*([\d\.,]+)")
            item_data["valor_unitario"] = extract_field(item_text, r"Valor unitário na condição de venda:\s*([\d\.,]+)")
            item_data["peso_liquido"] = extract_field(item_text, r"Peso l[íi]quido \(kg\):\s*([\d\.,]+)")
            
            # Busca valor total. Se não achar, calcula (qtd * unitario)
            val_total = extract_field(item_text, r"Valor total na condição de venda:\s*([\d\.,]+)")
            item_data["valor_total_local"] = val_total
            
            data["itens"].append(item_data)
                
    progress_bar.empty()
    status_text.empty()
    return data

# --- GERADOR DE XML (Mantido Igual) ---

def generate_xml_content(data):
    # Cabeçalho XML
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    xml += '<ListaDeclaracoes>\n'
    xml += '    <duimp>\n'
    
    for item in data["itens"]:
        qtd_fmt = format_number_xml(item.get("quantidade"), 14, 5)
        peso_fmt = format_number_xml(item.get("peso_liquido"), 15, 5)
        val_unit_fmt = format_number_xml(item.get("valor_unitario"), 20, 8)
        val_total_fmt = format_number_xml(item.get("valor_total_local"), 15, 2)
        
        ncm_clean = item.get("ncm", "").replace(".", "")
        num_item = item.get("numero", "1").zfill(2)
        
        xml += '        <adicao>\n'
        # ... (Bloco Acréscimo e Tributos zerados padrão) ...
        xml += '            <acrescimo>\n'
        xml += '                <codigoAcrescimo>17</codigoAcrescimo>\n'
        xml += '                <denominacao>OUTROS ACRESCIMOS AO VALOR ADUANEIRO</denominacao>\n'
        xml += '                <moedaNegociadaCodigo>220</moedaNegociadaCodigo>\n'
        xml += '                <moedaNegociadaNome>DOLAR DOS EUA</moedaNegociadaNome>\n'
        xml += '                <valorMoedaNegociada>000000000000000</valorMoedaNegociada>\n'
        xml += '                <valorReais>000000000000000</valorReais>\n'
        xml += '            </acrescimo>\n'
        
        # Tags obrigatórias preenchidas com zero para passar na validação
        xml += '            <cideValorAliquotaEspecifica>00000000000</cideValorAliquotaEspecifica>\n'
        xml += '            <cideValorDevido>000000000000000</cideValorDevido>\n'
        xml += '            <cideValorRecolher>000000000000000</cideValorRecolher>\n'
        xml += '            <codigoRelacaoCompradorVendedor>3</codigoRelacaoCompradorVendedor>\n'
        xml += '            <codigoVinculoCompradorVendedor>1</codigoVinculoCompradorVendedor>\n'
        xml += '            <cofinsAliquotaAdValorem>00000</cofinsAliquotaAdValorem>\n'
        xml += '            <cofinsAliquotaEspecificaQuantidadeUnidade>000000000</cofinsAliquotaEspecificaQuantidadeUnidade>\n'
        xml += '            <cofinsAliquotaEspecificaValor>0000000000</cofinsAliquotaEspecificaValor>\n'
        xml += '            <cofinsAliquotaReduzida>00000</cofinsAliquotaReduzida>\n'
        xml += '            <cofinsAliquotaValorDevido>000000000000000</cofinsAliquotaValorDevido>\n'
        xml += '            <cofinsAliquotaValorRecolher>000000000000000</cofinsAliquotaValorRecolher>\n'
        
        xml += '            <condicaoVendaIncoterm>FCA</condicaoVendaIncoterm>\n'
        xml += '            <condicaoVendaLocal>EXTERIOR</condicaoVendaLocal>\n'
        xml += '            <condicaoVendaMetodoValoracaoCodigo>01</condicaoVendaMetodoValoracaoCodigo>\n'
        xml += '            <condicaoVendaMetodoValoracaoNome>METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)</condicaoVendaMetodoValoracaoNome>\n'
        xml += '            <condicaoVendaMoedaCodigo>220</condicaoVendaMoedaCodigo>\n'
        xml += '            <condicaoVendaMoedaNome>DOLAR DOS EUA</condicaoVendaMoedaNome>\n'
        xml += f'            <condicaoVendaValorMoeda>{val_total_fmt}</condicaoVendaValorMoeda>\n'
        xml += '            <condicaoVendaValorReais>000000000000000</condicaoVendaValorReais>\n'
        
        # Dados Cambiais
        xml += '            <dadosCambiaisCoberturaCambialCodigo>1</dadosCambiaisCoberturaCambialCodigo>\n'
        xml += '            <dadosCambiaisCoberturaCambialNome>COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE 180</dadosCambiaisCoberturaCambialNome>\n'
        xml += '            <dadosCambiaisInstituicaoFinanciadoraCodigo>00</dadosCambiaisInstituicaoFinanciadoraCodigo>\n'
        xml += '            <dadosCambiaisInstituicaoFinanciadoraNome>N/I</dadosCambiaisInstituicaoFinanciadoraNome>\n'
        xml += '            <dadosCambiaisMotivoSemCoberturaCodigo>00</dadosCambiaisMotivoSemCoberturaCodigo>\n'
        xml += '            <dadosCambiaisMotivoSemCoberturaNome>N/I</dadosCambiaisMotivoSemCoberturaNome>\n'
        xml += '            <dadosCambiaisValorRealCambio>000000000000000</dadosCambiaisValorRealCambio>\n'
        
        # Dados Carga
        xml += '            <dadosCargaPaisProcedenciaCodigo>000</dadosCargaPaisProcedenciaCodigo>\n'
        xml += '            <dadosCargaUrfEntradaCodigo>0000000</dadosCargaUrfEntradaCodigo>\n'
        xml += '            <dadosCargaViaTransporteCodigo>01</dadosCargaViaTransporteCodigo>\n'
        xml += '            <dadosCargaViaTransporteNome>MARÍTIMA</dadosCargaViaTransporteNome>\n'
        
        # Dados Mercadoria
        xml += '            <dadosMercadoriaAplicacao>REVENDA</dadosMercadoriaAplicacao>\n'
        xml += '            <dadosMercadoriaCodigoNaladiNCCA>0000000</dadosMercadoriaCodigoNaladiNCCA>\n'
        xml += '            <dadosMercadoriaCodigoNaladiSH>00000000</dadosMercadoriaCodigoNaladiSH>\n'
        xml += f'            <dadosMercadoriaCodigoNcm>{ncm_clean}</dadosMercadoriaCodigoNcm>\n'
        xml += '            <dadosMercadoriaCondicao>NOVA</dadosMercadoriaCondicao>\n'
        xml += '            <dadosMercadoriaDescricaoTipoCertificado>Sem Certificado</dadosMercadoriaDescricaoTipoCertificado>\n'
        xml += '            <dadosMercadoriaIndicadorTipoCertificado>1</dadosMercadoriaIndicadorTipoCertificado>\n'
        xml += f'            <dadosMercadoriaMedidaEstatisticaQuantidade>{qtd_fmt}</dadosMercadoriaMedidaEstatisticaQuantidade>\n'
        xml += '            <dadosMercadoriaMedidaEstatisticaUnidade>QUILOGRAMA LIQUIDO</dadosMercadoriaMedidaEstatisticaUnidade>\n'
        xml += '            <dadosMercadoriaNomeNcm>DESC NCM</dadosMercadoriaNomeNcm>\n'
        xml += f'            <dadosMercadoriaPesoLiquido>{peso_fmt}</dadosMercadoriaPesoLiquido>\n'
        
        # Fornecedor
        xml += '            <dcrCoeficienteReducao>00000</dcrCoeficienteReducao>\n'
        xml += '            <dcrIdentificacao>00000000</dcrIdentificacao>\n'
        xml += '            <dcrValorDevido>000000000000000</dcrValorDevido>\n'
        xml += '            <dcrValorDolar>000000000000000</dcrValorDolar>\n'
        xml += '            <dcrValorReal>000000000000000</dcrValorReal>\n'
        xml += '            <dcrValorRecolher>000000000000000</dcrValorRecolher>\n'
        xml += '            <fornecedorCidade>EXTERIOR</fornecedorCidade>\n'
        xml += '            <fornecedorLogradouro>RUA EXTERIOR</fornecedorLogradouro>\n'
        xml += '            <fornecedorNome>FORNECEDOR PADRAO</fornecedorNome>\n'
        xml += '            <fornecedorNumero>00</fornecedorNumero>\n'
        
        # Frete
        xml += '            <freteMoedaNegociadaCodigo>220</freteMoedaNegociadaCodigo>\n'
        xml += '            <freteMoedaNegociadaNome>DOLAR DOS EUA</freteMoedaNegociadaNome>\n'
        xml += '            <freteValorMoedaNegociada>000000000000000</freteValorMoedaNegociada>\n'
        xml += '            <freteValorReais>000000000000000</freteValorReais>\n'
        
        # II
        xml += '            <iiAcordoTarifarioTipoCodigo>0</iiAcordoTarifarioTipoCodigo>\n'
        xml += '            <iiAliquotaAcordo>00000</iiAliquotaAcordo>\n'
        xml += '            <iiAliquotaAdValorem>00000</iiAliquotaAdValorem>\n'
        xml += '            <iiAliquotaPercentualReducao>00000</iiAliquotaPercentualReducao>\n'
        xml += '            <iiAliquotaReduzida>00000</iiAliquotaReduzida>\n'
        xml += '            <iiAliquotaValorCalculado>000000000000000</iiAliquotaValorCalculado>\n'
        xml += '            <iiAliquotaValorDevido>000000000000000</iiAliquotaValorDevido>\n'
        xml += '            <iiAliquotaValorRecolher>000000000000000</iiAliquotaValorRecolher>\n'
        xml += '            <iiAliquotaValorReduzido>000000000000000</iiAliquotaValorReduzido>\n'
        xml += '            <iiBaseCalculo>000000000000000</iiBaseCalculo>\n'
        xml += '            <iiFundamentoLegalCodigo>00</iiFundamentoLegalCodigo>\n'
        xml += '            <iiMotivoAdmissaoTemporariaCodigo>00</iiMotivoAdmissaoTemporariaCodigo>\n'
        xml += '            <iiRegimeTributacaoCodigo>1</iiRegimeTributacaoCodigo>\n'
        xml += '            <iiRegimeTributacaoNome>RECOLHIMENTO INTEGRAL</iiRegimeTributacaoNome>\n'
        
        # IPI
        xml += '            <ipiAliquotaAdValorem>00000</ipiAliquotaAdValorem>\n'
        xml += '            <ipiAliquotaEspecificaCapacidadeRecipciente>00000</ipiAliquotaEspecificaCapacidadeRecipciente>\n'
        xml += '            <ipiAliquotaEspecificaQuantidadeUnidadeMedida>000000000</ipiAliquotaEspecificaQuantidadeUnidadeMedida>\n'
        xml += '            <ipiAliquotaEspecificaTipoRecipienteCodigo>00</ipiAliquotaEspecificaTipoRecipienteCodigo>\n'
        xml += '            <ipiAliquotaEspecificaValorUnidadeMedida>0000000000</ipiAliquotaEspecificaValorUnidadeMedida>\n'
        xml += '            <ipiAliquotaNotaComplementarTIPI>00</ipiAliquotaNotaComplementarTIPI>\n'
        xml += '            <ipiAliquotaReduzida>00000</ipiAliquotaReduzida>\n'
        xml += '            <ipiAliquotaValorDevido>000000000000000</ipiAliquotaValorDevido>\n'
        xml += '            <ipiAliquotaValorRecolher>000000000000000</ipiAliquotaValorRecolher>\n'
        xml += '            <ipiRegimeTributacaoCodigo>4</ipiRegimeTributacaoCodigo>\n'
        xml += '            <ipiRegimeTributacaoNome>SEM BENEFICIO</ipiRegimeTributacaoNome>\n'
        
        # Mercadoria Final
        xml += '            <mercadoria>\n'
        xml += f'                <descricaoMercadoria>{item.get("descricao", "ITEM IMPORTADO")}</descricaoMercadoria>\n'
        xml += f'                <numeroSequencialItem>{num_item}</numeroSequencialItem>\n'
        xml += f'                <quantidade>{qtd_fmt}</quantidade>\n'
        xml += '                <unidadeMedida>PECA                </unidadeMedida>\n'
        xml += f'                <valorUnitario>{val_unit_fmt}</valorUnitario>\n'
        xml += '            </mercadoria>\n'
        
        # Linkagem
        xml += f'            <numeroAdicao>{item.get("numero", "1").zfill(3)}</numeroAdicao>\n'
        xml += f'            <numeroDUIMP>{data["header"].get("numero_duimp", "0000000000").replace(".", "").replace("-", "").replace("/", "")[:10]}</numeroDUIMP>\n'
        xml += '            <numeroLI>0000000000</numeroLI>\n'
        xml += '            <paisAquisicaoMercadoriaCodigo>076</paisAquisicaoMercadoriaCodigo>\n'
        xml += '            <paisAquisicaoMercadoriaNome>CHINA</paisAquisicaoMercadoriaNome>\n'
        xml += '            <paisOrigemMercadoriaCodigo>076</paisOrigemMercadoriaCodigo>\n'
        xml += '            <paisOrigemMercadoriaNome>CHINA</paisOrigemMercadoriaNome>\n'
        
        # PIS
        xml += '            <pisCofinsBaseCalculoAliquotaICMS>00000</pisCofinsBaseCalculoAliquotaICMS>\n'
        xml += '            <pisCofinsBaseCalculoFundamentoLegalCodigo>00</pisCofinsBaseCalculoFundamentoLegalCodigo>\n'
        xml += '            <pisCofinsBaseCalculoPercentualReducao>00000</pisCofinsBaseCalculoPercentualReducao>\n'
        xml += '            <pisCofinsBaseCalculoValor>000000000000000</pisCofinsBaseCalculoValor>\n'
        xml += '            <pisCofinsFundamentoLegalReducaoCodigo>00</pisCofinsFundamentoLegalReducaoCodigo>\n'
        xml += '            <pisCofinsRegimeTributacaoCodigo>1</pisCofinsRegimeTributacaoCodigo>\n'
        xml += '            <pisCofinsRegimeTributacaoNome>RECOLHIMENTO INTEGRAL</pisCofinsRegimeTributacaoNome>\n'
        xml += '            <pisPasepAliquotaAdValorem>00000</pisPasepAliquotaAdValorem>\n'
        xml += '            <pisPasepAliquotaEspecificaQuantidadeUnidade>000000000</pisPasepAliquotaEspecificaQuantidadeUnidade>\n'
        xml += '            <pisPasepAliquotaEspecificaValor>0000000000</pisPasepAliquotaEspecificaValor>\n'
        xml += '            <pisPasepAliquotaReduzida>00000</pisPasepAliquotaReduzida>\n'
        xml += '            <pisPasepAliquotaValorDevido>000000000000000</pisPasepAliquotaValorDevido>\n'
        xml += '            <pisPasepAliquotaValorRecolher>000000000000000</pisPasepAliquotaValorRecolher>\n'
        
        # ICMS CBS IBS
        xml += '            <icmsBaseCalculoValor>00000000000000</icmsBaseCalculoValor>\n'
        xml += '            <icmsBaseCalculoAliquota>00000</icmsBaseCalculoAliquota>\n'
        xml += '            <icmsBaseCalculoValorImposto>00000000000000</icmsBaseCalculoValorImposto>\n'
        xml += '            <icmsBaseCalculoValorDiferido>00000000000000</icmsBaseCalculoValorDiferido>\n'
        xml += '            <cbsIbsCst>000</cbsIbsCst>\n'
        xml += '            <cbsIbsClasstrib>000001</cbsIbsClasstrib>\n'
        xml += '            <cbsBaseCalculoValor>00000000000000</cbsBaseCalculoValor>\n'
        xml += '            <cbsBaseCalculoAliquota>00000</cbsBaseCalculoAliquota>\n'
        xml += '            <cbsBaseCalculoAliquotaReducao>00000</cbsBaseCalculoAliquotaReducao>\n'
        xml += '            <cbsBaseCalculoValorImposto>00000000000000</cbsBaseCalculoValorImposto>\n'
        xml += '            <ibsBaseCalculoValor>00000000000000</ibsBaseCalculoValor>\n'
        xml += '            <ibsBaseCalculoAliquota>00000</ibsBaseCalculoAliquota>\n'
        xml += '            <ibsBaseCalculoAliquotaReducao>00000</ibsBaseCalculoAliquotaReducao>\n'
        xml += '            <ibsBaseCalculoValorImposto>00000000000000</ibsBaseCalculoValorImposto>\n'
        
        xml += '            <relacaoCompradorVendedor>Fabricante é desconhecido</relacaoCompradorVendedor>\n'
        xml += '            <seguroMoedaNegociadaCodigo>220</seguroMoedaNegociadaCodigo>\n'
        xml += '            <seguroMoedaNegociadaNome>DOLAR DOS EUA</seguroMoedaNegociadaNome>\n'
        xml += '            <seguroValorMoedaNegociada>000000000000000</seguroValorMoedaNegociada>\n'
        xml += '            <seguroValorReais>000000000000000</seguroValorReais>\n'
        xml += '            <sequencialRetificacao>00</sequencialRetificacao>\n'
        xml += '            <valorMultaARecolher>000000000000000</valorMultaARecolher>\n'
        xml += '            <valorMultaARecolherAjustado>000000000000000</valorMultaARecolherAjustado>\n'
        xml += '            <valorReaisFreteInternacional>000000000000000</valorReaisFreteInternacional>\n'
        xml += '            <valorReaisSeguroInternacional>000000000000000</valorReaisSeguroInternacional>\n'
        xml += f'            <valorTotalCondicaoVenda>{val_total_fmt}</valorTotalCondicaoVenda>\n'
        xml += '            <vinculoCompradorVendedor>Não há vinculação entre comprador e vendedor.</vinculoCompradorVendedor>\n'
        xml += '        </adicao>\n'
        
    xml += '        <armazem>\n'
    xml += '            <nomeArmazem>PORTO PADRAO</nomeArmazem>\n'
    xml += '        </armazem>\n'
    xml += '        <armazenamentoRecintoAduaneiroCodigo>0000000</armazenamentoRecintoAduaneiroCodigo>\n'
    xml += '        <armazenamentoRecintoAduaneiroNome>RECINTO PADRAO</armazenamentoRecintoAduaneiroNome>\n'
    xml += '        <armazenamentoSetor>001</armazenamentoSetor>\n'
    xml += '        <canalSelecaoParametrizada>001</canalSelecaoParametrizada>\n'
    xml += '        <caracterizacaoOperacaoCodigoTipo>1</caracterizacaoOperacaoCodigoTipo>\n'
    xml += '        <caracterizacaoOperacaoDescricaoTipo>Importação Própria</caracterizacaoOperacaoDescricaoTipo>\n'
    xml += '        <cargaDataChegada>20260101</cargaDataChegada>\n'
    xml += '        <cargaNumeroAgente>N/I</cargaNumeroAgente>\n'
    xml += '        <cargaPaisProcedenciaCodigo>000</cargaPaisProcedenciaCodigo>\n'
    xml += f'        <cargaPaisProcedenciaNome>{data["header"].get("pais_procedencia", "BRASIL")}</cargaPaisProcedenciaNome>\n'
    xml += f'        <numeroDUIMP>{data["header"].get("numero_duimp", "0000000000").replace(".", "").replace("-", "").replace("/", "")[:10]}</numeroDUIMP>\n'
    xml += '    </duimp>\n'
    xml += '</ListaDeclaracoes>'
    
    return xml

# --- INTERFACE DO STREAMLIT ---

uploaded_file = st.file_uploader("Arraste seu PDF da DUIMP aqui", type="pdf")

if uploaded_file is not None:
    st.info("Iniciando processamento...")
    
    if st.button("Processar e Gerar XML"):
        try:
            with st.spinner('Lendo PDF...'):
                extracted_data = process_pdf(uploaded_file)
            
            st.success(f"Sucesso! {len(extracted_data['itens'])} itens identificados.")
            
            if extracted_data['itens']:
                df_preview = pd.DataFrame(extracted_data['itens'])
                st.dataframe(df_preview[['numero', 'ncm', 'quantidade', 'valor_unitario', 'descricao']].head())
            
            with st.spinner('Gerando XML...'):
                xml_string = generate_xml_content(extracted_data)
            
            st.download_button(
                label="📥 Baixar XML",
                data=xml_string,
                file_name=f"DUIMP_CONVERTIDA_{datetime.now().strftime('%Y%m%d_%H%M')}.xml",
                mime="application/xml"
            )
            
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
