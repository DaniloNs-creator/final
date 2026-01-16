import streamlit as st
import pdfplumber
import pypdf
import re
import io
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES E UTILITÁRIOS ---
st.set_page_config(page_title="Conversor DUIMP Pro", layout="wide")

def clean_text(text):
    """Remove quebras de linha e espaços múltiplos."""
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def format_siscomex(value, length=15, decimals=2):
    """
    Formata valores para o padrão Siscomex/Serpro:
    - Remove pontos de milhar.
    - Mantém decimais fixos.
    - Remove vírgula/ponto decimal.
    - Preenche com zeros à esquerda (Zfill).
    Ex: 1.200,50 -> 0000000120050 (para length=13, decimals=2)
    """
    if not value:
        return "0" * length
    
    # 1. Limpeza básica (deixa apenas digitos e virgula/ponto)
    # Trata formato brasileiro 1.000,00
    if ',' in str(value):
        clean = str(value).replace('.', '') # Remove milhar
        parts = clean.split(',')
        if len(parts) > 1:
            integer = parts[0]
            fraction = parts[1][:decimals].ljust(decimals, '0')
            raw = f"{integer}{fraction}"
        else:
            raw = f"{parts[0]}{'0'*decimals}"
    # Trata formato americano ou float puro
    elif '.' in str(value):
        parts = str(value).split('.')
        integer = parts[0]
        fraction = parts[1][:decimals].ljust(decimals, '0')
        raw = f"{integer}{fraction}"
    # Trata inteiros
    else:
        raw = f"{str(value)}{'0'*decimals}"

    # Remove qualquer caractere não numérico restante
    final_digits = re.sub(r'\D', '', raw)
    
    return final_digits.zfill(length)

def extract_field(text, pattern, default=""):
    """Extração segura via Regex."""
    if not text: return default
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else default

# --- MOTOR DE EXTRAÇÃO HÍBRIDO ---

def process_pdf_data(pdf_file):
    """
    Lê o PDF e extrai dados estruturados mapeando o arquivo Extrato-DUIMP.
    Usa pdfplumber (preciso) e pypdf (backup).
    """
    full_text = ""
    
    # Leitura do PDF
    try:
        pdf_bytes = pdf_file.read()
        
        # Tentativa 1: pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                try:
                    text = page.extract_text()
                    if text: full_text += text + "\n"
                except: pass
        
        # Tentativa 2: pypdf (se falhar ou vier vazio)
        if len(full_text) < 100:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
                
    except Exception as e:
        return None, f"Erro na leitura: {str(e)}"

    # --- MAPEAMENTO DE DADOS (Baseado nos [sources] do prompt) ---
    data = {
        "header": {},
        "itens": []
    }

    # 1. Dados Capa (Header)
    # Número DUIMP
    data["header"]["numero_duimp"] = extract_field(full_text, r"Extrato da DUIMP\s+([0-9BR-]+)")
    # CNPJ Importador
    data["header"]["cnpj"] = extract_field(full_text, r"CNPJ do importador:\s*([\d\.\/-]+)")
    # País Procedência
    data["header"]["pais_proc"] = extract_field(full_text, r"País de Procedência:\s*(.+?)(?=\n)", "CHINA")
    # URF Entrada
    data["header"]["urf_entrada"] = extract_field(full_text, r"UNIDADE DE ENTRADA.*?(\d{7})", "0000000")
    # Frete Total
    data["header"]["frete_total"] = extract_field(full_text, r"VALOR DO FRETE\s*:\s*([\d\.,]+)", "0,00")
    # Totais Impostos (II, IPI, PIS, COFINS globais se houver)
    # Nota: O layout pede por ITEM. Vamos tentar extrair por item, mas usar globais como fallback visual.

    # 2. Dados dos Itens (Adições)
    # Regex para quebrar o texto nos marcadores "Extrato da Duimp... Item X"
    # 
    raw_itens = re.split(r"(?i)Extrato da Duimp.*?Item\s+(\d+)", full_text)

    if len(raw_itens) > 1:
        # Pula o índice 0 (cabeçalho geral) e itera em pares (Numero, Conteudo)
        iterator = iter(raw_itens[1:])
        for item_num, content in zip(iterator, iterator):
            item = {}
            item["numero"] = item_num
            
            # NCM
            item["ncm"] = extract_field(content, r"NCM:\s*([\d\.]+)")
            
            # Descrição
            desc = re.search(r"Detalhamento do Produto:\s*(.*?)(?=\nCódigo de Class|Tributos|Versão)", content, re.DOTALL)
            item["descricao"] = clean_text(desc.group(1)) if desc else "DESCRIÇÃO NÃO ENCONTRADA"
            
            # Quantidade
            item["quantidade"] = extract_field(content, r"Quantidade na unidade comercializada:\s*([\d\.,]+)")
            
            # Valor Unitário
            item["valor_unit"] = extract_field(content, r"Valor unitário na condição de venda:\s*([\d\.,]+)")
            
            # Valor Total Local (VMLD ou VMLE dependendo do Incoterm, aqui pega Condição Venda)
            item["valor_total"] = extract_field(content, r"Valor total na condição de venda:\s*([\d\.,]+)")
            
            # Peso Líquido
            item["peso_liq"] = extract_field(content, r"Peso l[íi]quido \(kg\):\s*([\d\.,]+)")
            
            # Tributos (Se houver tabela no item)
            # Como o XML M-DUIMP exige campos específicos (II, IPI, PIS, COFINS, ICMS, CBS, IBS)
            # e o PDF muitas vezes diz "Nenhum resultado encontrado", preencheremos com 0 para manter o layout.
            
            data["itens"].append(item)
            
    return data, None

# --- GERADOR DE XML (LAYOUT M-DUIMP OBRIGATÓRIO) ---

def generate_xml_m_duimp(data):
    """
    Gera o XML preenchendo o template M-DUIMP-8686868686.xml.
    Não usa bibliotecas de XML para garantir a ordem estrita das tags.
    """
    
    # Header Estático
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    xml += '<ListaDeclaracoes>\n'
    xml += '    <duimp>\n'
    
    # --- LOOP DE ADIÇÕES ---
    for item in data["itens"]:
        # Formatações Siscomex
        ncm_clean = item["ncm"].replace(".", "")
        qtd_fmt = format_siscomex(item["quantidade"], 14, 5) # Exemplo de precisão
        peso_fmt = format_siscomex(item["peso_liq"], 15, 5)
        val_unit_fmt = format_siscomex(item["valor_unit"], 20, 8) # Alta precisão
        val_total_fmt = format_siscomex(item["valor_total"], 15, 2)
        
        # Dados de IDs
        num_adicao = item["numero"].zfill(3)
        num_duimp_clean = data["header"]["numero_duimp"].replace(".", "").replace("-", "").replace("/", "")[:10]

        xml += '        <adicao>\n'
        
        # ACRESCIMO
        xml += '            <acrescimo>\n'
        xml += '                <codigoAcrescimo>17</codigoAcrescimo>\n'
        xml += '                <denominacao>OUTROS ACRESCIMOS AO VALOR ADUANEIRO                        </denominacao>\n'
        xml += '                <moedaNegociadaCodigo>220</moedaNegociadaCodigo>\n' # Default USD
        xml += '                <moedaNegociadaNome>DOLAR DOS EUA</moedaNegociadaNome>\n'
        xml += '                <valorMoedaNegociada>000000000000000</valorMoedaNegociada>\n'
        xml += '                <valorReais>000000000000000</valorReais>\n'
        xml += '            </acrescimo>\n'
        
        # CIDE
        xml += '            <cideValorAliquotaEspecifica>00000000000</cideValorAliquotaEspecifica>\n'
        xml += '            <cideValorDevido>000000000000000</cideValorDevido>\n'
        xml += '            <cideValorRecolher>000000000000000</cideValorRecolher>\n'
        
        # RELAÇÃO
        xml += '            <codigoRelacaoCompradorVendedor>3</codigoRelacaoCompradorVendedor>\n'
        xml += '            <codigoVinculoCompradorVendedor>1</codigoVinculoCompradorVendedor>\n'
        
        # COFINS
        xml += '            <cofinsAliquotaAdValorem>00000</cofinsAliquotaAdValorem>\n'
        xml += '            <cofinsAliquotaEspecificaQuantidadeUnidade>000000000</cofinsAliquotaEspecificaQuantidadeUnidade>\n'
        xml += '            <cofinsAliquotaEspecificaValor>0000000000</cofinsAliquotaEspecificaValor>\n'
        xml += '            <cofinsAliquotaReduzida>00000</cofinsAliquotaReduzida>\n'
        xml += '            <cofinsAliquotaValorDevido>000000000000000</cofinsAliquotaValorDevido>\n'
        xml += '            <cofinsAliquotaValorRecolher>000000000000000</cofinsAliquotaValorRecolher>\n'
        
        # CONDIÇÃO VENDA
        xml += '            <condicaoVendaIncoterm>FCA</condicaoVendaIncoterm>\n'
        xml += '            <condicaoVendaLocal>EXTERIOR</condicaoVendaLocal>\n'
        xml += '            <condicaoVendaMetodoValoracaoCodigo>01</condicaoVendaMetodoValoracaoCodigo>\n'
        xml += '            <condicaoVendaMetodoValoracaoNome>METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)</condicaoVendaMetodoValoracaoNome>\n'
        xml += '            <condicaoVendaMoedaCodigo>220</condicaoVendaMoedaCodigo>\n'
        xml += '            <condicaoVendaMoedaNome>DOLAR DOS EUA</condicaoVendaMoedaNome>\n'
        xml += f'            <condicaoVendaValorMoeda>{val_total_fmt}</condicaoVendaValorMoeda>\n'
        xml += '            <condicaoVendaValorReais>000000000000000</condicaoVendaValorReais>\n'
        
        # DADOS CAMBIAIS
        xml += '            <dadosCambiaisCoberturaCambialCodigo>1</dadosCambiaisCoberturaCambialCodigo>\n'
        xml += '            <dadosCambiaisCoberturaCambialNome>COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE\' 180</dadosCambiaisCoberturaCambialNome>\n'
        xml += '            <dadosCambiaisInstituicaoFinanciadoraCodigo>00</dadosCambiaisInstituicaoFinanciadoraCodigo>\n'
        xml += '            <dadosCambiaisInstituicaoFinanciadoraNome>N/I</dadosCambiaisInstituicaoFinanciadoraNome>\n'
        xml += '            <dadosCambiaisMotivoSemCoberturaCodigo>00</dadosCambiaisMotivoSemCoberturaCodigo>\n'
        xml += '            <dadosCambiaisMotivoSemCoberturaNome>N/I</dadosCambiaisMotivoSemCoberturaNome>\n'
        xml += '            <dadosCambiaisValorRealCambio>000000000000000</dadosCambiaisValorRealCambio>\n'
        
        # DADOS CARGA
        xml += '            <dadosCargaPaisProcedenciaCodigo>000</dadosCargaPaisProcedenciaCodigo>\n'
        xml += '            <dadosCargaUrfEntradaCodigo>0000000</dadosCargaUrfEntradaCodigo>\n'
        xml += '            <dadosCargaViaTransporteCodigo>01</dadosCargaViaTransporteCodigo>\n'
        xml += '            <dadosCargaViaTransporteNome>MARÍTIMA</dadosCargaViaTransporteNome>\n'
        
        # DADOS MERCADORIA (CRUCIAL)
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
        
        # DCR / FORNECEDOR
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
        
        # FRETE
        xml += '            <freteMoedaNegociadaCodigo>220</freteMoedaNegociadaCodigo>\n'
        xml += '            <freteMoedaNegociadaNome>DOLAR DOS EUA</freteMoedaNegociadaNome>\n'
        xml += '            <freteValorMoedaNegociada>000000000000000</freteValorMoedaNegociada>\n'
        xml += '            <freteValorReais>000000000000000</freteValorReais>\n'
        
        # IMPOSTO IMPORTAÇÃO (II)
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
        
        # DETALHAMENTO ITEM (MERCADORIA)
        xml += '            <mercadoria>\n'
        # Limite de caracteres para descrição para evitar erro de buffer no ERP
        xml += f'                <descricaoMercadoria>{item["descricao"][:250]}</descricaoMercadoria>\n'
        xml += f'                <numeroSequencialItem>{item["numero"].zfill(2)}</numeroSequencialItem>\n'
        xml += f'                <quantidade>{qtd_fmt}</quantidade>\n'
        xml += '                <unidadeMedida>PECA                </unidadeMedida>\n'
        xml += f'                <valorUnitario>{val_unit_fmt}</valorUnitario>\n'
        xml += '            </mercadoria>\n'
        
        # TAGS DE IDENTIFICAÇÃO E LINKAGEM
        xml += f'            <numeroAdicao>{num_adicao}</numeroAdicao>\n'
        xml += f'            <numeroDUIMP>{num_duimp_clean}</numeroDUIMP>\n'	
        xml += '            <numeroLI>0000000000</numeroLI>\n'
        xml += '            <paisAquisicaoMercadoriaCodigo>076</paisAquisicaoMercadoriaCodigo>\n'
        xml += '            <paisAquisicaoMercadoriaNome>CHINA</paisAquisicaoMercadoriaNome>\n'
        xml += '            <paisOrigemMercadoriaCodigo>076</paisOrigemMercadoriaCodigo>\n'
        xml += '            <paisOrigemMercadoriaNome>CHINA</paisOrigemMercadoriaNome>\n'
        
        # PIS/PASEP
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
        
        # ICMS (Obrigatório conforme arquivo de exemplo)
        xml += '            <icmsBaseCalculoValor>000000000000000</icmsBaseCalculoValor>\n'
        xml += '            <icmsBaseCalculoAliquota>00000</icmsBaseCalculoAliquota>\n'
        xml += '            <icmsBaseCalculoValorImposto>00000000000000</icmsBaseCalculoValorImposto>\n'
        xml += '            <icmsBaseCalculoValorDiferido>00000000000000</icmsBaseCalculoValorDiferido>\n'
        
        # CBS / IBS (Reforma Tributária - Presente no Layout)
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
        
        # RODAPÉ DO ITEM
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

    # --- TAGS FINAIS (ARMAZÉM, CARGA, PAGAMENTO) ---
    # URF Entrada
    urf_entrada = data["header"]["urf_entrada"]
    
    xml += '        <armazem>\n'
    xml += '            <nomeArmazem>PORTO PADRAO</nomeArmazem>\n'
    xml += '        </armazem>\n'
    xml += f'        <armazenamentoRecintoAduaneiroCodigo>{urf_entrada}</armazenamentoRecintoAduaneiroCodigo>\n'
    xml += '        <armazenamentoRecintoAduaneiroNome>RECINTO ALFANDEGADO</armazenamentoRecintoAduaneiroNome>\n'
    xml += '        <armazenamentoSetor>002</armazenamentoSetor>\n'
    xml += '        <canalSelecaoParametrizada>001</canalSelecaoParametrizada>\n'
    xml += '        <caracterizacaoOperacaoCodigoTipo>1</caracterizacaoOperacaoCodigoTipo>\n'
    xml += '        <caracterizacaoOperacaoDescricaoTipo>Importação Própria</caracterizacaoOperacaoDescricaoTipo>\n'
    xml += '        <cargaDataChegada>20250101</cargaDataChegada>\n'
    xml += '        <cargaNumeroAgente>N/I</cargaNumeroAgente>\n'
    xml += '        <cargaPaisProcedenciaCodigo>076</cargaPaisProcedenciaCodigo>\n'
    xml += f'        <cargaPaisProcedenciaNome>{data["header"]["pais_proc"]}</cargaPaisProcedenciaNome>\n'
    xml += '        <cargaPesoBruto>000000000000000</cargaPesoBruto>\n'
    xml += '        <cargaPesoLiquido>000000000000000</cargaPesoLiquido>\n'
    xml += f'        <cargaUrfEntradaCodigo>{urf_entrada}</cargaUrfEntradaCodigo>\n'
    xml += '        <cargaUrfEntradaNome>PORTO DE ENTRADA</cargaUrfEntradaNome>\n'
    # Tags de Documento/Pagamento inseridas como dummy para validação de estrutura
    xml += '        <modalidadeDespachoCodigo>1</modalidadeDespachoCodigo>\n'
    xml += '        <modalidadeDespachoNome>Normal</modalidadeDespachoNome>\n'
    xml += f'        <numeroDUIMP>{data["header"]["numero_duimp"].replace(".","").replace("-","").replace("/","")[:10]}</numeroDUIMP>\n'
    xml += '    </duimp>\n'
    xml += '</ListaDeclaracoes>'
    
    return xml

# --- UI APP STREAMLIT ---

st.title("🏭 Conversor DUIMP para Layout XML (Integrador)")
st.info("Layout: M-DUIMP-8686868686 | Formatação: Padrão Siscomex (Zeros à esquerda)")

uploaded = st.file_uploader("Upload PDF DUIMP", type="pdf")

if uploaded:
    if st.button("Converter"):
        with st.spinner("Processando (Plumber + Regex)..."):
            extracted_data, error = process_pdf_data(uploaded)
            
            if error:
                st.error(error)
            elif not extracted_data["itens"]:
                st.warning("Nenhum item encontrado. Verifique se o PDF é um extrato válido.")
            else:
                st.success(f"Extração concluída: {len(extracted_data['itens'])} itens.")
                
                # Preview
                df = pd.DataFrame(extracted_data["itens"])
                st.dataframe(df[["numero", "ncm", "valor_total", "descricao"]].head())
                
                # Geração XML
                xml_out = generate_xml_m_duimp(extracted_data)
                
                st.download_button(
                    "📥 Download XML Mapeado",
                    data=xml_out,
                    file_name=f"DUIMP_FINAL_{datetime.now().strftime('%H%M%S')}.xml",
                    mime="text/xml"
                )
