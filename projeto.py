import streamlit as st
import pdfplumber
import re
import io
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Conversor DUIMP PDF para XML", layout="wide")

st.title("📂 Conversor DUIMP (PDF) para Layout XML Importação")
st.markdown("""
Este aplicativo converte o extrato em PDF da DUIMP do Portal Siscomex para o formato XML 
obrigatório de importação de sistemas ERP.
**Capacidade:** Processa arquivos grandes (múltiplos itens).
**Layout:** Baseado no modelo M-DUIMP.
""")

# --- FUNÇÕES UTILITÁRIAS DE FORMATAÇÃO ---

def clean_text(text):
    if not text: return ""
    return text.replace("\n", " ").strip()

def format_number_xml(value_str, length=15, decimals=2):
    """
    Converte string numérica brasileira (1.000,00) para formato ERP (000000000100000).
    Remove pontos e vírgulas e preenche com zeros à esquerda.
    """
    if not value_str:
        return "0" * length
    
    # Remove caracteres não numéricos exceto virgula
    clean = re.sub(r'[^\d,]', '', str(value_str))
    
    # Se não tem vírgula, assume inteiro
    if ',' not in clean:
        clean = clean + ("0" * decimals)
    else:
        # Garante o numero certo de decimais
        parts = clean.split(',')
        dec_part = parts[1][:decimals].ljust(decimals, '0')
        clean = parts[0] + dec_part
    
    # Remove qualquer coisa que não seja digito agora
    final_raw = re.sub(r'\D', '', clean)
    
    # Preenche com zeros à esquerda (Zfill)
    return final_raw.zfill(length)

def extract_field(text, pattern, default=""):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else default

# --- NÚCLEO DE PROCESSAMENTO (PDF) ---

def process_pdf(pdf_file):
    data = {
        "header": {},
        "itens": []
    }
    
    full_text = ""
    
    # Barra de progresso para arquivos grandes
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with pdfplumber.open(pdf_file) as pdf:
        total_pages = len(pdf.pages)
        
        # 1. Extração de Texto Completo (Otimizada)
        for i, page in enumerate(pdf.pages):
            full_text += page.extract_text() + "\n"
            # Atualiza progresso a cada 10 paginas ou no final
            if i % 10 == 0 or i == total_pages - 1:
                progress_bar.progress((i + 1) / total_pages)
                status_text.text(f"Lendo página {i+1} de {total_pages}...")
        
        # 2. Extração do Cabeçalho (Dados Gerais)
        data["header"]["numero_duimp"] = extract_field(full_text, r"Extrato da DUIMP\s+([0-9BR-]+)")
        data["header"]["importador_cnpj"] = extract_field(full_text, r"CNPJ do importador:\s*([\d\.\/-]+)")
        data["header"]["importador_nome"] = extract_field(full_text, r"Nome do importador:\s*(.+?)(?=\n|:)")
        data["header"]["pais_procedencia"] = extract_field(full_text, r"País de Procedência:\s*(.+?)(?=\n|CN|US)", "BRASIL")
        
        # Valores Totais (Capturados das tabelas ou texto se disponíveis globalmente)
        data["header"]["frete_total"] = extract_field(full_text, r"Valor do Frete\s*:\s*([\d\.,]+)", "0,00")
        
        # 3. Extração dos Itens (Adições)
        # A estratégia aqui é dividir o texto pelos marcadores de "Item"
        # O padrão no PDF parece ser "Extrato da Duimp... : Item 00001"
        
        item_splits = re.split(r"Extrato da Duimp.*Item\s+(\d+)", full_text)
        
        # O split gera: [Intro, "00001", TextoItem1, "00002", TextoItem2...]
        # Ignoramos a intro (índice 0) e iteramos em pares (numero, texto)
        
        if len(item_splits) > 1:
            # Pula o primeiro elemento que é o header geral antes do item 1
            iterator = iter(item_splits[1:])
            for item_num, item_text in zip(iterator, iterator):
                item_data = {}
                
                item_data["numero"] = item_num
                
                # Dados Básicos do Item
                item_data["ncm"] = extract_field(item_text, r"NCM:\s*([\d\.-]+)")
                item_data["descricao"] = extract_field(item_text, r"Detalhamento do Produto:\s*(.*?)(?=\nCódigo de Class|Tributos)", "")
                item_data["descricao"] = item_data["descricao"].replace("\n", " ")[:200] # Limita tamanho
                
                item_data["quantidade"] = extract_field(item_text, r"Quantidade na unidade comercializada:\s*([\d\.,]+)")
                item_data["valor_unitario"] = extract_field(item_text, r"Valor unitário na condição de venda:\s*([\d\.,]+)")
                item_data["peso_liquido"] = extract_field(item_text, r"Peso líquido \(kg\):\s*([\d\.,]+)")
                
                # Valores Totais do Item (Cálculo aproximado se não explícito, ou extração)
                item_data["valor_total_local"] = extract_field(item_text, r"Valor total na condição de venda:\s*([\d\.,]+)")
                
                # --- Extração de Tributos (Tabelas dentro do texto do item) ---
                # Esta parte é crítica. O PDF tem tabelas. Regex simples falha.
                # Simplificação para o protótipo: Buscar valores próximos às keywords
                # Num cenário real, usaríamos pdf.pages[x].extract_table() focado na área.
                
                # Exemplo: Buscando II, IPI, PIS, COFINS no texto do item
                # Como o layout do XML exige valores calculados e a recolher:
                # O PDF de exemplo mostra "Tributação ... Nenhum resultado encontrado" em algumas paginas,
                # Mas nas páginas 2 temos tabela de impostos totais.
                # Vamos tentar extrair se existir, senão 0.
                
                item_data["ii_valor"] = "0,00" # Default
                item_data["ipi_valor"] = "0,00"
                item_data["pis_valor"] = "0,00"
                item_data["cofins_valor"] = "0,00"
                
                data["itens"].append(item_data)
                
    progress_bar.empty()
    return data

# --- GERADOR DE XML (LAYOUT M-DUIMP) ---

def generate_xml_content(data):
    """
    Gera a string XML respeitando RIGOROSAMENTE a estrutura do arquivo M-DUIMP.
    Utiliza f-strings para garantir a ordem das tags.
    """
    
    # Cabeçalho XML
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    xml += '<ListaDeclaracoes>\n'
    xml += '    <duimp>\n'
    
    # Loop de Adições (Itens)
    for item in data["itens"]:
        # Formatação de valores para o padrão XML (zeros à esquerda, sem pontuação)
        qtd_fmt = format_number_xml(item.get("quantidade"), 14, 5) # Ex: 14 digitos, 5 decimais
        peso_fmt = format_number_xml(item.get("peso_liquido"), 15, 5)
        val_unit_fmt = format_number_xml(item.get("valor_unitario"), 20, 8) # Exemplo de precisão alta
        val_total_fmt = format_number_xml(item.get("valor_total_local"), 15, 2)
        
        ncm_clean = item.get("ncm", "").replace(".", "")
        
        # Bloco ADICAO
        xml += '        <adicao>\n'
        
        # --- Bloco Acréscimo (Exemplo fixo ou derivado) ---
        xml += '            <acrescimo>\n'
        xml += '                <codigoAcrescimo>17</codigoAcrescimo>\n'
        xml += '                <denominacao>OUTROS ACRESCIMOS AO VALOR ADUANEIRO</denominacao>\n'
        xml += '                <moedaNegociadaCodigo>220</moedaNegociadaCodigo>\n' # 220 = USD
        xml += '                <moedaNegociadaNome>DOLAR DOS EUA</moedaNegociadaNome>\n'
        xml += '                <valorMoedaNegociada>000000000000000</valorMoedaNegociada>\n'
        xml += '                <valorReais>000000000000000</valorReais>\n'
        xml += '            </acrescimo>\n'
        
        # --- Dados Tributários (Zeros por padrão se não extraído) ---
        xml += '            <cideValorAliquotaEspecifica>00000000000</cideValorAliquotaEspecifica>\n'
        xml += '            <cideValorDevido>000000000000000</cideValorDevido>\n'
        xml += '            <cideValorRecolher>000000000000000</cideValorRecolher>\n'
        
        # --- Dados Venda/Compra ---
        xml += '            <codigoRelacaoCompradorVendedor>3</codigoRelacaoCompradorVendedor>\n'
        xml += '            <codigoVinculoCompradorVendedor>1</codigoVinculoCompradorVendedor>\n'
        
        # --- COFINS ---
        xml += '            <cofinsAliquotaAdValorem>00000</cofinsAliquotaAdValorem>\n'
        xml += '            <cofinsAliquotaEspecificaQuantidadeUnidade>000000000</cofinsAliquotaEspecificaQuantidadeUnidade>\n'
        xml += '            <cofinsAliquotaEspecificaValor>0000000000</cofinsAliquotaEspecificaValor>\n'
        xml += '            <cofinsAliquotaReduzida>00000</cofinsAliquotaReduzida>\n'
        xml += '            <cofinsAliquotaValorDevido>000000000000000</cofinsAliquotaValorDevido>\n'
        xml += '            <cofinsAliquotaValorRecolher>000000000000000</cofinsAliquotaValorRecolher>\n'
        
        # --- Condição de Venda ---
        xml += '            <condicaoVendaIncoterm>FCA</condicaoVendaIncoterm>\n'
        xml += '            <condicaoVendaLocal>EXTERIOR</condicaoVendaLocal>\n'
        xml += '            <condicaoVendaMetodoValoracaoCodigo>01</condicaoVendaMetodoValoracaoCodigo>\n'
        xml += '            <condicaoVendaMetodoValoracaoNome>METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)</condicaoVendaMetodoValoracaoNome>\n'
        xml += '            <condicaoVendaMoedaCodigo>220</condicaoVendaMoedaCodigo>\n'
        xml += '            <condicaoVendaMoedaNome>DOLAR DOS EUA</condicaoVendaMoedaNome>\n'
        xml += f'            <condicaoVendaValorMoeda>{val_total_fmt}</condicaoVendaValorMoeda>\n'
        xml += '            <condicaoVendaValorReais>000000000000000</condicaoVendaValorReais>\n'
        
        # --- Dados Cambiais ---
        xml += '            <dadosCambiaisCoberturaCambialCodigo>1</dadosCambiaisCoberturaCambialCodigo>\n'
        xml += '            <dadosCambiaisCoberturaCambialNome>COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE 180</dadosCambiaisCoberturaCambialNome>\n'
        xml += '            <dadosCambiaisInstituicaoFinanciadoraCodigo>00</dadosCambiaisInstituicaoFinanciadoraCodigo>\n'
        xml += '            <dadosCambiaisInstituicaoFinanciadoraNome>N/I</dadosCambiaisInstituicaoFinanciadoraNome>\n'
        xml += '            <dadosCambiaisMotivoSemCoberturaCodigo>00</dadosCambiaisMotivoSemCoberturaCodigo>\n'
        xml += '            <dadosCambiaisMotivoSemCoberturaNome>N/I</dadosCambiaisMotivoSemCoberturaNome>\n'
        xml += '            <dadosCambiaisValorRealCambio>000000000000000</dadosCambiaisValorRealCambio>\n'
        
        # --- Dados Carga ---
        xml += '            <dadosCargaPaisProcedenciaCodigo>000</dadosCargaPaisProcedenciaCodigo>\n'
        xml += '            <dadosCargaUrfEntradaCodigo>0000000</dadosCargaUrfEntradaCodigo>\n'
        xml += '            <dadosCargaViaTransporteCodigo>01</dadosCargaViaTransporteCodigo>\n'
        xml += '            <dadosCargaViaTransporteNome>MARÍTIMA</dadosCargaViaTransporteNome>\n'
        
        # --- Dados Mercadoria (CRUCIAL) ---
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
        
        # --- Dados Fornecedor (Pode ser melhorado com regex específico) ---
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
        
        # --- Frete ---
        xml += '            <freteMoedaNegociadaCodigo>220</freteMoedaNegociadaCodigo>\n'
        xml += '            <freteMoedaNegociadaNome>DOLAR DOS EUA</freteMoedaNegociadaNome>\n'
        xml += '            <freteValorMoedaNegociada>000000000000000</freteValorMoedaNegociada>\n'
        xml += '            <freteValorReais>000000000000000</freteValorReais>\n'
        
        # --- II (Imposto Importação) ---
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
        
        # --- IPI ---
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
        
        # --- MERCADORIA (Detalhe) ---
        xml += '            <mercadoria>\n'
        xml += f'                <descricaoMercadoria>{item.get("descricao", "ITEM IMPORTADO")}</descricaoMercadoria>\n'
        xml += f'                <numeroSequencialItem>{item.get("numero").zfill(2)}</numeroSequencialItem>\n'
        xml += f'                <quantidade>{qtd_fmt}</quantidade>\n'
        xml += '                <unidadeMedida>PECA                </unidadeMedida>\n'
        xml += f'                <valorUnitario>{val_unit_fmt}</valorUnitario>\n'
        xml += '            </mercadoria>\n'
        
        # --- Identificadores de Linkagem ---
        xml += f'            <numeroAdicao>{item.get("numero").zfill(3)}</numeroAdicao>\n'
        xml += f'            <numeroDUIMP>{data["header"].get("numero_duimp", "0000000000").replace(".", "").replace("-", "").replace("/", "")[:10]}</numeroDUIMP>\n'
        xml += '            <numeroLI>0000000000</numeroLI>\n'
        xml += '            <paisAquisicaoMercadoriaCodigo>076</paisAquisicaoMercadoriaCodigo>\n' # Exemplo
        xml += '            <paisAquisicaoMercadoriaNome>CHINA</paisAquisicaoMercadoriaNome>\n'
        xml += '            <paisOrigemMercadoriaCodigo>076</paisOrigemMercadoriaCodigo>\n'
        xml += '            <paisOrigemMercadoriaNome>CHINA</paisOrigemMercadoriaNome>\n'
        
        # --- PIS/PASEP ---
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
        
        # --- ICMS e CBS (Estrutura Nova DUIMP) ---
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
        
        # --- Finalização Item ---
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
        
    # --- Fechamento do XML e Tags Globais (Simplificado para o exemplo) ---
    # Nota: O XML de exemplo M-DUIMP fecha as adições e depois coloca tags de armazem, carga, etc.
    # Como estas são "globais", elas ficam fora do loop das adições.
    
    # Extraindo dados globais do header do PDF para fechar o XML
    frete_fmt = format_number_xml(data["header"].get("frete_total", "0"), 15, 5)
    
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
    # Tags adicionais seriam inseridas aqui seguindo a mesma lógica...
    xml += f'        <numeroDUIMP>{data["header"].get("numero_duimp", "0000000000").replace(".", "").replace("-", "").replace("/", "")[:10]}</numeroDUIMP>\n'
    xml += '    </duimp>\n'
    xml += '</ListaDeclaracoes>'
    
    return xml

# --- INTERFACE DO STREAMLIT ---

uploaded_file = st.file_uploader("Arraste seu PDF da DUIMP aqui", type="pdf")

if uploaded_file is not None:
    st.info("Iniciando processamento. Arquivos de 500 páginas podem levar alguns minutos.")
    
    if st.button("Processar e Gerar XML"):
        try:
            # 1. Extração
            with st.spinner('Lendo PDF e extraindo dados...'):
                extracted_data = process_pdf(uploaded_file)
            
            st.success(f"PDF lido com sucesso! Encontrados {len(extracted_data['itens'])} itens.")
            
            # Mostra preview dos dados lidos
            if extracted_data['itens']:
                df_preview = pd.DataFrame(extracted_data['itens'])
                st.dataframe(df_preview[['numero', 'ncm', 'quantidade', 'valor_unitario', 'descricao']].head())
            
            # 2. Geração do XML
            with st.spinner('Gerando XML no layout M-DUIMP...'):
                xml_string = generate_xml_content(extracted_data)
            
            # 3. Download
            st.download_button(
                label="📥 Baixar XML Processado",
                data=xml_string,
                file_name=f"DUIMP_CONVERTIDA_{datetime.now().strftime('%Y%m%d_%H%M')}.xml",
                mime="application/xml"
            )
            
        except Exception as e:
            st.error(f"Ocorreu um erro durante o processamento: {e}")
            st.write("Detalhes do erro:", e)
