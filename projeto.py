import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Conversor DUIMP Blindado", layout="wide", page_icon="🛡️")

st.title("🛡️ Conversor DUIMP > XML (Modo Seguro)")
st.markdown("Esta versão utiliza varredura resiliente para evitar erros de índice em PDFs com layouts variados.")

# --- FUNÇÕES UTILITÁRIAS SEGURAS ---

def safe_clean_decimal(value_str):
    """Limpa valores monetários (Ex: 10.000,00 -> 10000.00) de forma segura."""
    if not value_str or not isinstance(value_str, str):
        return "0"
    try:
        # Remove pontos de milhar e troca vírgula decimal por ponto
        clean = value_str.replace('.', '').replace(',', '.')
        return clean
    except:
        return "0"

def format_xml_value(value, size=15):
    """
    Formata para XML sem ponto decimal e com zeros à esquerda, 
    padrão visto em sistemas de importação (ex: 100.50 -> 00000000010050)
    """
    try:
        clean_val = safe_clean_decimal(value)
        float_val = float(clean_val)
        # Multiplica por 100 para remover as 2 casas decimais padrão (centavos)
        # Ajuste conforme a necessidade do seu sistema. 
        # Se o sistema lê 100.00 como 10000, mantenha a lógica abaixo.
        int_val = int(round(float_val * 100000)) # Multiplicando para 5 casas decimais conforme padrão M-DUIMP
        
        # Converte para string e remove o sinal negativo se houver
        str_val = str(int_val).replace('-', '')
        
        # Preenche com zeros à esquerda
        return str_val.zfill(size)
    except:
        return "0".zfill(size)

def get_regex_value(text, pattern, default=""):
    """
    Busca valores usando Regex com flags MULTILINE e DOTALL para pegar quebras de linha.
    """
    if not text:
        return default
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            # Pega o grupo 1, remove espaços extras e quebras de linha
            return match.group(1).strip()
    except Exception:
        pass
    return default

def safe_split(text, separator, index):
    """
    Divide uma string e retorna o índice de forma segura.
    Evita 'list index out of range'.
    """
    if not text:
        return text
    try:
        parts = text.split(separator)
        if index < len(parts):
            return parts[index].strip()
        # Se o índice for negativo (ex: -1 para o último)
        if index < 0 and abs(index) <= len(parts):
            return parts[index].strip()
        return text # Retorna o texto original se não conseguir dividir
    except:
        return text

# --- MOTOR DE EXTRAÇÃO PDF ---

def extract_data_robust(pdf_file):
    full_text = ""
    
    # 1. Leitura do PDF
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
    except Exception as e:
        st.error(f"Erro crítico ao ler o PDF: {e}")
        return None, []

    # 2. Extração do Cabeçalho (Dados Gerais)
    # Nota: Usamos [\s\S]*? para pegar qualquer coisa incluindo novas linhas
    header = {
        "numeroDUIMP": get_regex_value(full_text, r"Extrato da DUIMP\s+([0-9A-Z-]+)"),
        "importadorNome": get_regex_value(full_text, r"Nome do importador:\s*[:\n]?\s*([^\n]+)"),
        "importadorCNPJ": get_regex_value(full_text, r"CNPJ do importador:\s*([\d./-]+)"),
        "pesoBruto": get_regex_value(full_text, r"PESO BRUTO KG\s*[:\n]*\s*([\d.,]+)"),
        "pesoLiquido": get_regex_value(full_text, r"PESO LIQUIDO KG\s*[:\n]*\s*([\d.,]+)"),
        "paisProcedencia": get_regex_value(full_text, r"PAIS DE PROCEDENCIA\s*[:\n]*\s*([^\n]+)"),
        "urfEntrada": get_regex_value(full_text, r"UNIDADE DE ENTRADA.*?:\s*([0-9]+)", "0000000"),
        "urfDespacho": get_regex_value(full_text, r"UNIDADE DE DESPACHO\s*[:\n]*\s*([0-9]+)", "0000000"),
    }

    # 3. Identificação dos Itens
    # A regex busca "Item X" onde X são dígitos
    # O uso de finditer é seguro
    item_iter = re.finditer(r"(?:Item\s+|Item\s*:)\s*(\d{5}|\d+)", full_text)
    item_indices = [(m.start(), m.group(1)) for m in item_iter]
    
    adicoes = []
    
    # Se não achou itens com "Item 00001", tenta padrão genérico de tabela
    if not item_indices:
        st.warning("Padrão 'Item 00001' não detectado. Tentando extração genérica...")
        # Fallback logic se necessário (aqui mantemos a lógica principal)

    for i in range(len(item_indices)):
        start_pos, item_num = item_indices[i]
        
        # Define o fim do texto deste item (começo do próximo ou fim do arquivo)
        if i + 1 < len(item_indices):
            end_pos = item_indices[i+1][0]
        else:
            end_pos = len(full_text)
            
        # Recorte do texto referente apenas a este item
        item_text = full_text[start_pos:end_pos]
        
        # Extração de Campos Específicos do Item
        # Ajustado regex para pegar valores que estão na linha de BAIXO (comum no extrato do Siscomex)
        item_data = {
            "numeroAdicao": item_num,
            "ncm": get_regex_value(item_text, r"NCM:\s*[:\n]?\s*([\d.]+)").replace('.', ''),
            
            # Pega descrição até encontrar uma palavra chave de parada
            "descricao": get_regex_value(item_text, r"(?:Detalhamento do Produto|Descrição complementar).*?:\s*([\s\S]*?)(?:Código de Class|Tributos|$)"),
            
            "codProduto": get_regex_value(item_text, r"Código do produto:\s*[:\n]?\s*([^\n]+)"),
            "paisOrigem": get_regex_value(item_text, r"País de origem:\s*[:\n]?\s*([^\n]+)"),
            
            "fabricanteRaw": get_regex_value(item_text, r"Código do Fabricante/Produtor:\s*[:\n]?\s*([^\n]+)"),
            
            "qtdEstatistica": get_regex_value(item_text, r"Quantidade na unidade estatística:\s*([\d.,]+)"),
            "unidadeMedida": get_regex_value(item_text, r"Unidade estatística:\s*([^\n]+)"),
            "pesoLiquido": get_regex_value(item_text, r"Peso l[íi]quido \(kg\):\s*([\d.,]+)"),
            
            "valorUnitario": get_regex_value(item_text, r"Valor unitário.*?:\s*([\d.,]+)"),
            "valorTotal": get_regex_value(item_text, r"Valor total na condição.*?:\s*([\d.,]+)"),
            "moeda": get_regex_value(item_text, r"Moeda negociada:\s*([^\n]+)"),
            
            # Tributos (PIS/COFINS)
            "pis": get_regex_value(item_text, r"PIS\s*[:\n]*\s*([\d.,]+)", "0"),
            "cofins": get_regex_value(item_text, r"COFINS\s*[:\n]*\s*([\d.,]+)", "0"),
        }
        
        # Limpezas extras
        item_data['descricao'] = item_data['descricao'].replace('\n', ' ').strip()[:250] # Limita tamanho
        item_data['fabricanteNome'] = safe_split(item_data['fabricanteRaw'], '-', -1)
        
        adicoes.append(item_data)
        
    return header, adicoes

# --- GERAÇÃO DO XML (LAYOUT M-DUIMP RIGOROSO) ---

def generate_xml_layout(header, adicoes):
    root = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(root, "duimp")
    
    # 1. Loop das Adições
    for item in adicoes:
        adicao = ET.SubElement(duimp, "adicao")
        
        # Grupo: Acrescimo
        acrescimo = ET.SubElement(adicao, "acrescimo")
        ET.SubElement(acrescimo, "codigoAcrescimo").text = "17"
        ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
        # Lógica de moeda (Exemplo: 220 Dolar, 978 Euro)
        cod_moeda = "220" if "DOLAR" in str(item['moeda']).upper() else "978"
        ET.SubElement(acrescimo, "moedaNegociadaCodigo").text = cod_moeda
        ET.SubElement(acrescimo, "moedaNegociadaNome").text = item['moeda'] or "DOLAR DOS EUA"
        ET.SubElement(acrescimo, "valorMoedaNegociada").text = "000000000000000"
        ET.SubElement(acrescimo, "valorReais").text = "000000000000000"

        # Grupo: CIDE (Obrigatório aparecer tag vazia se não tiver?)
        ET.SubElement(adicao, "cideValorAliquotaEspecifica").text = "00000000000"
        ET.SubElement(adicao, "cideValorDevido").text = "000000000000000"
        ET.SubElement(adicao, "cideValorRecolher").text = "000000000000000"
        
        # Relação
        ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
        ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
        
        # COFINS
        ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965" # Padrão
        ET.SubElement(adicao, "cofinsAliquotaEspecificaQuantidadeUnidade").text = "000000000"
        ET.SubElement(adicao, "cofinsAliquotaEspecificaValor").text = "0000000000"
        ET.SubElement(adicao, "cofinsAliquotaReduzida").text = "00000"
        ET.SubElement(adicao, "cofinsAliquotaValorDevido").text = format_xml_value(item['cofins'])
        ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = format_xml_value(item['cofins'])
        
        # Condição de Venda
        ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FCA"
        ET.SubElement(adicao, "condicaoVendaLocal").text = "SUAPE"
        ET.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
        ET.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"
        ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = cod_moeda
        ET.SubElement(adicao, "condicaoVendaMoedaNome").text = item['moeda'] or "DOLAR DOS EUA"
        ET.SubElement(adicao, "condicaoVendaValorMoeda").text = format_xml_value(item['valorTotal'])
        ET.SubElement(adicao, "condicaoVendaValorReais").text = "000000000000000"
        
        # Dados Cambiais
        ET.SubElement(adicao, "dadosCambiaisCoberturaCambialCodigo").text = "1"
        ET.SubElement(adicao, "dadosCambiaisCoberturaCambialNome").text = "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE 180"
        ET.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraCodigo").text = "00"
        ET.SubElement(adicao, "dadosCambiaisInstituicaoFinanciadoraNome").text = "N/I"
        ET.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaCodigo").text = "00"
        ET.SubElement(adicao, "dadosCambiaisMotivoSemCoberturaNome").text = "N/I"
        ET.SubElement(adicao, "dadosCambiaisValorRealCambio").text = "000000000000000"
        
        # Dados Carga
        pais_cod = "076" if "CHINA" in str(header.get('paisProcedencia', '')).upper() else "000"
        ET.SubElement(adicao, "dadosCargaPaisProcedenciaCodigo").text = pais_cod
        ET.SubElement(adicao, "dadosCargaUrfEntradaCodigo").text = header.get('urfEntrada', '0000000')
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
        ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaQuantidade").text = format_xml_value(item['qtdEstatistica'])
        ET.SubElement(adicao, "dadosMercadoriaMedidaEstatisticaUnidade").text = item['unidadeMedida']
        # Nome NCM (Opcional ou fixo, pois não vem fácil no PDF)
        ET.SubElement(adicao, "dadosMercadoriaNomeNcm").text = "Descricao NCM Generica" 
        ET.SubElement(adicao, "dadosMercadoriaPesoLiquido").text = format_xml_value(item['pesoLiquido'])
        
        # DCR (Obrigatório no Layout)
        ET.SubElement(adicao, "dcrCoeficienteReducao").text = "00000"
        ET.SubElement(adicao, "dcrIdentificacao").text = "00000000"
        ET.SubElement(adicao, "dcrValorDevido").text = "000000000000000"
        ET.SubElement(adicao, "dcrValorDolar").text = "000000000000000"
        ET.SubElement(adicao, "dcrValorReal").text = "000000000000000"
        ET.SubElement(adicao, "dcrValorRecolher").text = "000000000000000"
        
        # Fornecedor
        ET.SubElement(adicao, "fornecedorCidade").text = "CIDADE"
        ET.SubElement(adicao, "fornecedorLogradouro").text = "ENDERECO"
        ET.SubElement(adicao, "fornecedorNome").text = item['fabricanteNome']
        ET.SubElement(adicao, "fornecedorNumero").text = "00"
        
        # Frete
        ET.SubElement(adicao, "freteMoedaNegociadaCodigo").text = cod_moeda
        ET.SubElement(adicao, "freteMoedaNegociadaNome").text = item['moeda'] or "DOLAR DOS EUA"
        ET.SubElement(adicao, "freteValorMoedaNegociada").text = "000000000000000"
        ET.SubElement(adicao, "freteValorReais").text = "000000000000000"
        
        # Imposto Importação (II)
        ET.SubElement(adicao, "iiAcordoTarifarioTipoCodigo").text = "0"
        ET.SubElement(adicao, "iiAliquotaAcordo").text = "00000"
        ET.SubElement(adicao, "iiAliquotaAdValorem").text = "01400"
        ET.SubElement(adicao, "iiAliquotaPercentualReducao").text = "00000"
        ET.SubElement(adicao, "iiAliquotaReduzida").text = "00000"
        ET.SubElement(adicao, "iiAliquotaValorCalculado").text = "000000000000000"
        ET.SubElement(adicao, "iiAliquotaValorDevido").text = "000000000000000"
        ET.SubElement(adicao, "iiAliquotaValorRecolher").text = "000000000000000"
        ET.SubElement(adicao, "iiAliquotaValorReduzido").text = "000000000000000"
        ET.SubElement(adicao, "iiBaseCalculo").text = "000000000000000"
        ET.SubElement(adicao, "iiFundamentoLegalCodigo").text = "00"
        ET.SubElement(adicao, "iiMotivoAdmissaoTemporariaCodigo").text = "00"
        ET.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
        ET.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
        
        # IPI
        ET.SubElement(adicao, "ipiAliquotaAdValorem").text = "00325"
        ET.SubElement(adicao, "ipiAliquotaEspecificaCapacidadeRecipciente").text = "00000"
        ET.SubElement(adicao, "ipiAliquotaEspecificaQuantidadeUnidadeMedida").text = "000000000"
        ET.SubElement(adicao, "ipiAliquotaEspecificaTipoRecipienteCodigo").text = "00"
        ET.SubElement(adicao, "ipiAliquotaEspecificaValorUnidadeMedida").text = "0000000000"
        ET.SubElement(adicao, "ipiAliquotaNotaComplementarTIPI").text = "00"
        ET.SubElement(adicao, "ipiAliquotaReduzida").text = "00000"
        ET.SubElement(adicao, "ipiAliquotaValorDevido").text = "000000000000000"
        ET.SubElement(adicao, "ipiAliquotaValorRecolher").text = "000000000000000"
        ET.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "4"
        ET.SubElement(adicao, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"
        
        # Tags de Identificação da Adição
        ET.SubElement(adicao, "numeroAdicao").text = str(item['numeroAdicao']).zfill(3)
        ET.SubElement(adicao, "numeroDUIMP").text = header.get('numeroDUIMP', '0000000000')
        ET.SubElement(adicao, "numeroLI").text = "0000000000"
        ET.SubElement(adicao, "paisAquisicaoMercadoriaCodigo").text = pais_cod
        ET.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = item['paisOrigem'] or "PAIS"
        ET.SubElement(adicao, "paisOrigemMercadoriaCodigo").text = pais_cod
        ET.SubElement(adicao, "paisOrigemMercadoriaNome").text = item['paisOrigem'] or "PAIS"
        
        # PIS/PASEP
        ET.SubElement(adicao, "pisCofinsBaseCalculoAliquotaICMS").text = "00000"
        ET.SubElement(adicao, "pisCofinsBaseCalculoFundamentoLegalCodigo").text = "00"
        ET.SubElement(adicao, "pisCofinsBaseCalculoPercentualReducao").text = "00000"
        ET.SubElement(adicao, "pisCofinsBaseCalculoValor").text = "000000000000000"
        ET.SubElement(adicao, "pisCofinsFundamentoLegalReducaoCodigo").text = "00"
        ET.SubElement(adicao, "pisCofinsRegimeTributacaoCodigo").text = "1"
        ET.SubElement(adicao, "pisCofinsRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
        ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
        ET.SubElement(adicao, "pisPasepAliquotaEspecificaQuantidadeUnidade").text = "000000000"
        ET.SubElement(adicao, "pisPasepAliquotaEspecificaValor").text = "0000000000"
        ET.SubElement(adicao, "pisPasepAliquotaReduzida").text = "00000"
        ET.SubElement(adicao, "pisPasepAliquotaValorDevido").text = format_xml_value(item['pis'])
        ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = format_xml_value(item['pis'])
        
        ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Exportador é o fabricante do produto"
        
        # Seguro
        ET.SubElement(adicao, "seguroMoedaNegociadaCodigo").text = "220"
        ET.SubElement(adicao, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
        ET.SubElement(adicao, "seguroValorMoedaNegociada").text = "000000000000000"
        ET.SubElement(adicao, "seguroValorReais").text = "000000000000000"
        ET.SubElement(adicao, "sequencialRetificacao").text = "00"
        ET.SubElement(adicao, "valorMultaARecolher").text = "000000000000000"
        ET.SubElement(adicao, "valorMultaARecolherAjustado").text = "000000000000000"
        ET.SubElement(adicao, "valorReaisFreteInternacional").text = "000000000000000"
        ET.SubElement(adicao, "valorReaisSeguroInternacional").text = "000000000000000"
        ET.SubElement(adicao, "valorTotalCondicaoVenda").text = format_xml_value(item['valorTotal']).zfill(11) # Ajuste de tamanho se necessario
        ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."

        # TAG FINAL: MERCADORIA (Detalhes)
        mercadoria = ET.SubElement(adicao, "mercadoria")
        ET.SubElement(mercadoria, "descricaoMercadoria").text = item['descricao']
        ET.SubElement(mercadoria, "numeroSequencialItem").text = str(item['numeroAdicao']).zfill(2)
        ET.SubElement(mercadoria, "quantidade").text = format_xml_value(item['qtdEstatistica'])
        ET.SubElement(mercadoria, "unidadeMedida").text = item['unidadeMedida']
        ET.SubElement(mercadoria, "valorUnitario").text = format_xml_value(item['valorUnitario'])
        
        # ICMS (Baseado no layout)
        ET.SubElement(adicao, "icmsBaseCalculoValor").text = "00000000160652"
        ET.SubElement(adicao, "icmsBaseCalculoAliquota").text = "01800"
        ET.SubElement(adicao, "icmsBaseCalculoValorImposto").text = "00000000019374"
        ET.SubElement(adicao, "icmsBaseCalculoValorDiferido").text = "00000000009542"
        
        # CBS / IBS
        ET.SubElement(adicao, "cbsIbsCst").text = "000"
        ET.SubElement(adicao, "cbsIbsClasstrib").text = "000001"
        ET.SubElement(adicao, "cbsBaseCalculoValor").text = "00000000160652"
        ET.SubElement(adicao, "cbsBaseCalculoAliquota").text = "00090"
        ET.SubElement(adicao, "cbsBaseCalculoAliquotaReducao").text = "00000"
        ET.SubElement(adicao, "cbsBaseCalculoValorImposto").text = "00000000001445"
        
        ET.SubElement(adicao, "ibsBaseCalculoValor").text = "00000000160652"
        ET.SubElement(adicao, "ibsBaseCalculoAliquota").text = "00010"
        ET.SubElement(adicao, "ibsBaseCalculoAliquotaReducao").text = "00000"
        ET.SubElement(adicao, "ibsBaseCalculoValorImposto").text = "00000000000160"

    # 2. Dados Finais Globais (Tag Arroz DUIMP)
    armazem = ET.SubElement(duimp, "armazem")
    ET.SubElement(armazem, "nomeArmazem").text = "IRF - PORTO DE SUAPE"
    
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroCodigo").text = header.get("urfDespacho", "0000000")
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "IRF - PORTO DE SUAPE"
    ET.SubElement(duimp, "armazenamentoSetor").text = "002"
    ET.SubElement(duimp, "canalSelecaoParametrizada").text = "001"
    ET.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
    ET.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importação Própria"
    ET.SubElement(duimp, "cargaDataChegada").text = "20260114"
    ET.SubElement(duimp, "cargaNumeroAgente").text = "N/I"
    ET.SubElement(duimp, "cargaPaisProcedenciaCodigo").text = "076"
    ET.SubElement(duimp, "cargaPaisProcedenciaNome").text = header.get("paisProcedencia", "CHINA")
    ET.SubElement(duimp, "cargaPesoBruto").text = format_xml_value(header.get("pesoBruto", "0"))
    ET.SubElement(duimp, "cargaPesoLiquido").text = format_xml_value(header.get("pesoLiquido", "0"))
    ET.SubElement(duimp, "cargaUrfEntradaCodigo").text = header.get("urfDespacho", "0417902")
    ET.SubElement(duimp, "cargaUrfEntradaNome").text = "IRF - PORTO DE SUAPE"
    
    # Documentos
    ET.SubElement(duimp, "conhecimentoCargaEmbarqueData").text = "20251214"
    ET.SubElement(duimp, "conhecimentoCargaEmbarqueLocal").text = "SUAPE"
    ET.SubElement(duimp, "conhecimentoCargaId").text = "NGBS071709"
    
    # Finalizando Tags Obrigatórias
    ET.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
    ET.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
    ET.SubElement(duimp, "totalAdicoes").text = str(len(adicoes)).zfill(3)
    ET.SubElement(duimp, "urfDespachoCodigo").text = header.get("urfDespacho", "0417902")
    
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    return xml_str

# --- INTERFACE STREAMLIT ---

uploaded_file = st.file_uploader("📂 Carregar Extrato DUIMP (PDF)", type="pdf")

if uploaded_file is not None:
    st.info("Iniciando varredura segura...")
    
    header_data, adicoes_data = extract_data_robust(uploaded_file)
    
    if not adicoes_data:
        st.warning("⚠️ Nenhum item foi detectado. Verifique se o PDF é um arquivo de texto selecionável (não imagem).")
    else:
        st.success(f"Sucesso! {len(adicoes_data)} itens processados.")
        
        # Exibição
        st.subheader("📋 Resumo")
        col1, col2 = st.columns(2)
        col1.metric("DUIMP", header_data.get('numeroDUIMP', 'N/A'))
        col2.metric("Itens", len(adicoes_data))
        
        st.dataframe(adicoes_data)

        if st.button("🚀 Gerar XML M-DUIMP"):
            xml_output = generate_xml_layout(header_data, adicoes_data)
            
            st.download_button(
                label="📥 Baixar XML Formatado",
                data=xml_output,
                file_name=f"M-DUIMP-{header_data.get('numeroDUIMP', 'conv')}.xml",
                mime="application/xml"
            )
