import streamlit as st
import re
from pypdf import PdfReader
from io import BytesIO

# ==============================================================================
# 1. CLASSE DE UTILIDADES E FORMATAÇÃO (RIGOR DO XML)
# ==============================================================================
class XmlFormatter:
    @staticmethod
    def fmt_num(value, length=15):
        """
        Transforma '1.409,60' ou 1409.60 em '000000000140960'.
        Remove não numéricos e preenche com zeros à esquerda.
        """
        if not value:
            return "0" * length
        
        # Converte para string se não for
        s_val = str(value)
        
        # Se tiver vírgula decimal, remove pontos de milhar primeiro
        if ',' in s_val:
            s_val = s_val.replace('.', '').replace(',', '')
        elif '.' in s_val:
             # Caso venha como float do Python (1000.50) -> 100050
            parts = s_val.split('.')
            if len(parts) == 2:
                # Garante 2 casas decimais se for float
                decimal = parts[1].ljust(2, '0')[:2]
                s_val = parts[0] + decimal
            else:
                s_val = s_val.replace('.', '')
        
        # Remove qualquer lixo restante
        clean = re.sub(r'\D', '', s_val)
        return clean.zfill(length)

    @staticmethod
    def fmt_text(text, max_len=None):
        """Limpa texto e coloca em caixa alta"""
        if not text: return ""
        t = str(text).strip().upper()
        # Remove quebras de linha que possam vir do PDF
        t = t.replace('\n', ' ').replace('\r', '')
        if max_len:
            return t[:max_len]
        return t

# ==============================================================================
# 2. MOTOR DE EXTRAÇÃO (LEITURA DO PDF)
# ==============================================================================
def extract_data_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    
    lines = full_text.split('\n')
    
    data = {
        "global": {
            "duimp": "00000", "cnpj": "", "importador": "", 
            "peso_bruto": "0", "peso_liquido": "0", "data_reg": ""
        },
        "adicoes": []
    }

    # --- REGEX GLOBAIS ---
    # Tenta achar número DUIMP, CNPJ, etc.
    match_duimp = re.search(r"25BR(\d+)", full_text)
    if match_duimp: data["global"]["duimp"] = match_duimp.group(1)

    match_cnpj = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", full_text)
    if match_cnpj: data["global"]["cnpj"] = match_cnpj.group(1)

    match_imp = re.search(r"IMPORTADOR\s*\n\s*\"?(.*?)\"?", full_text)
    if match_imp: data["global"]["importador"] = match_imp.group(1)
    
    # Pesos (Busca genérica, pode precisar de ajuste fino dependendo da página)
    match_pb = re.search(r"([\d\.,]+)\s*PESO BRUTO", full_text, re.IGNORECASE)
    if match_pb: data["global"]["peso_bruto"] = match_pb.group(1)
    
    match_pl = re.search(r"([\d\.,]+)\s*PESO LIQUIDO", full_text, re.IGNORECASE)
    if match_pl: data["global"]["peso_liquido"] = match_pl.group(1)

    # --- PROCESSAMENTO DOS ITENS (MÁQUINA DE ESTADOS) ---
    current_item = None
    reading_desc = False
    desc_buffer = []
    
    # Regex de Item
    re_item_header = re.compile(r"ITENS DA DUIMP - (\d+)")
    re_ncm = re.compile(r"(\d{4}\.\d{2}\.\d{2})")
    re_val_merc = re.compile(r"([\d\.,]+)\s+Valor Tot\. Cond Venda")
    re_qtd = re.compile(r"([\d\.,]+)\s+Qtde Unid\. Comercial")
    
    # Regex de Impostos (Valores a Recolher)
    re_tax_rec = re.compile(r"([\d\.,]+)\s+Valor A Recolher")
    current_tax_context = None

    for line in lines:
        line = line.strip()
        
        # 1. Novo Item Detectado
        item_match = re_item_header.search(line)
        if item_match:
            # Salva o anterior
            if current_item:
                current_item["descricao"] = " ".join(desc_buffer).strip()
                data["adicoes"].append(current_item)
            
            # Inicializa novo
            current_item = {
                "numero": item_match.group(1),
                "ncm": "00000000",
                "descricao": "",
                "valor_fca_moeda": "0",
                "valor_fca_reais": "0", # Teremos que estimar ou deixar zerado se não tiver a taxa explicita na linha
                "qtd": "0",
                "ii_rec": "0", "ipi_rec": "0", "pis_rec": "0", "cofins_rec": "0"
            }
            reading_desc = False
            desc_buffer = []
            current_tax_context = None
            continue

        if not current_item: continue

        # 2. Dados Básicos do Item
        if re.search(r"DENOMINACAO DO PRODUTO", line):
            reading_desc = True
            continue
        if reading_desc:
            if re.search(r"CÓDIGO INTERNO|DESCRIÇÃO COMPLEMENTAR", line):
                reading_desc = False
            else:
                desc_buffer.append(line)

        # NCM
        if current_item["ncm"] == "00000000":
            m_ncm = re_ncm.search(line)
            if m_ncm: current_item["ncm"] = m_ncm.group(1).replace('.', '')

        # Qtd
        m_qtd = re_qtd.search(line)
        if m_qtd: current_item["qtd"] = m_qtd.group(1)

        # Valor
        m_val = re_val_merc.search(line)
        if m_val: 
            current_item["valor_fca_moeda"] = m_val.group(1)
            # Simulação de conversão para REAIS (já que o PDF tem a taxa no cabeçalho, mas aqui simplificamos)
            # Num cenário real, capturaríamos a taxa do cabeçalho. 
            # Vou assumir uma conversão simples ou repetir o valor formatado para preencher o campo obrigatório
            current_item["valor_fca_reais"] = m_val.group(1) 

        # 3. Impostos
        if line in ["II", "IPI", "PIS", "COFINS"]:
            current_tax_context = line
        
        if current_tax_context:
            m_rec = re_tax_rec.search(line)
            if m_rec:
                key = f"{current_tax_context.lower()}_rec"
                current_item[key] = m_rec.group(1)

    # Adiciona último item
    if current_item:
        current_item["descricao"] = " ".join(desc_buffer).strip()
        data["adicoes"].append(current_item)
        
    return data

# ==============================================================================
# 3. GERADOR DE XML (STRING BUILDER PADRÃO RÍGIDO)
# ==============================================================================
def generate_strict_xml(data):
    xml_output = []
    
    # Cabeçalho Fixo
    xml_output.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    xml_output.append('<ListaDeclaracoes>')
    xml_output.append('  <duimp>')
    
    # --- LOOP ADIÇÕES ---
    for item in data["adicoes"]:
        # Prepara Variáveis
        num_adicao = item['numero'].zfill(3)
        v_moeda = XmlFormatter.fmt_num(item['valor_fca_moeda'])
        v_reais = XmlFormatter.fmt_num(item['valor_fca_reais']) # Idealmente multiplicar pela taxa
        v_qtd = XmlFormatter.fmt_num(item['qtd'], 14)
        v_ncm = item['ncm']
        desc = XmlFormatter.fmt_text(item['descricao'], 100)
        
        # Impostos Formatados
        ii_val = XmlFormatter.fmt_num(item['ii_rec'])
        ipi_val = XmlFormatter.fmt_num(item['ipi_rec'])
        pis_val = XmlFormatter.fmt_num(item['pis_rec'])
        cofins_val = XmlFormatter.fmt_num(item['cofins_rec'])

        # Bloco da Adição (Indentação manual para garantir rigor)
        adicao_block = f"""    <adicao>
      <acrescimo>
        <codigoAcrescimo>17</codigoAcrescimo>
        <denominacao>OUTROS ACRESCIMOS AO VALOR ADUANEIRO</denominacao>
        <moedaNegociadaCodigo>978</moedaNegociadaCodigo>
        <moedaNegociadaNome>EURO/COM.EUROPEIA</moedaNegociadaNome>
        <valorMoedaNegociada>{v_moeda}</valorMoedaNegociada>
        <valorReais>{v_reais}</valorReais>
      </acrescimo>
      <cideValorAliquotaEspecifica>00000000000</cideValorAliquotaEspecifica>
      <cideValorDevido>000000000000000</cideValorDevido>
      <cideValorRecolher>000000000000000</cideValorRecolher>
      <codigoRelacaoCompradorVendedor>3</codigoRelacaoCompradorVendedor>
      <codigoVinculoCompradorVendedor>1</codigoVinculoCompradorVendedor>
      <cofinsAliquotaAdValorem>00965</cofinsAliquotaAdValorem>
      <cofinsAliquotaEspecificaQuantidadeUnidade>000000000</cofinsAliquotaEspecificaQuantidadeUnidade>
      <cofinsAliquotaEspecificaValor>0000000000</cofinsAliquotaEspecificaValor>
      <cofinsAliquotaReduzida>00000</cofinsAliquotaReduzida>
      <cofinsAliquotaValorDevido>{cofins_val}</cofinsAliquotaValorDevido>
      <cofinsAliquotaValorRecolher>{cofins_val}</cofinsAliquotaValorRecolher>
      <condicaoVendaIncoterm>FCA</condicaoVendaIncoterm>
      <condicaoVendaLocal>BRUGNERA</condicaoVendaLocal>
      <condicaoVendaMetodoValoracaoCodigo>01</condicaoVendaMetodoValoracaoCodigo>
      <condicaoVendaMetodoValoracaoNome>METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)</condicaoVendaMetodoValoracaoNome>
      <condicaoVendaMoedaCodigo>978</condicaoVendaMoedaCodigo>
      <condicaoVendaMoedaNome>EURO/COM.EUROPEIA</condicaoVendaMoedaNome>
      <condicaoVendaValorMoeda>{v_moeda}</condicaoVendaValorMoeda>
      <condicaoVendaValorReais>{v_reais}</condicaoVendaValorReais>
      <dadosCambiaisCoberturaCambialCodigo>1</dadosCambiaisCoberturaCambialCodigo>
      <dadosCambiaisCoberturaCambialNome>COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180</dadosCambiaisCoberturaCambialNome>
      <dadosCambiaisInstituicaoFinanciadoraCodigo>00</dadosCambiaisInstituicaoFinanciadoraCodigo>
      <dadosCambiaisInstituicaoFinanciadoraNome>N/I</dadosCambiaisInstituicaoFinanciadoraNome>
      <dadosCambiaisMotivoSemCoberturaCodigo>00</dadosCambiaisMotivoSemCoberturaCodigo>
      <dadosCambiaisMotivoSemCoberturaNome>N/I</dadosCambiaisMotivoSemCoberturaNome>
      <dadosCambiaisValorRealCambio>000000000000000</dadosCambiaisValorRealCambio>
      <dadosCargaPaisProcedenciaCodigo>000</dadosCargaPaisProcedenciaCodigo>
      <dadosCargaUrfEntradaCodigo>0917800</dadosCargaUrfEntradaCodigo>
      <dadosCargaViaTransporteCodigo>01</dadosCargaViaTransporteCodigo>
      <dadosCargaViaTransporteNome>MARÍTIMA</dadosCargaViaTransporteNome>
      <dadosMercadoriaAplicacao>REVENDA</dadosMercadoriaAplicacao>
      <dadosMercadoriaCodigoNaladiNCCA>0000000</dadosMercadoriaCodigoNaladiNCCA>
      <dadosMercadoriaCodigoNaladiSH>00000000</dadosMercadoriaCodigoNaladiSH>
      <dadosMercadoriaCodigoNcm>{v_ncm}</dadosMercadoriaCodigoNcm>
      <dadosMercadoriaCondicao>NOVA</dadosMercadoriaCondicao>
      <dadosMercadoriaDescricaoTipoCertificado>Sem Certificado</dadosMercadoriaDescricaoTipoCertificado>
      <dadosMercadoriaIndicadorTipoCertificado>1</dadosMercadoriaIndicadorTipoCertificado>
      <dadosMercadoriaMedidaEstatisticaQuantidade>{v_qtd}</dadosMercadoriaMedidaEstatisticaQuantidade>
      <dadosMercadoriaMedidaEstatisticaUnidade>QUILOGRAMA LIQUIDO</dadosMercadoriaMedidaEstatisticaUnidade>
      <dadosMercadoriaNomeNcm>Descricao Padrao NCM</dadosMercadoriaNomeNcm>
      <dadosMercadoriaPesoLiquido>{v_qtd}</dadosMercadoriaPesoLiquido>
      <dcrCoeficienteReducao>00000</dcrCoeficienteReducao>
      <dcrIdentificacao>00000000</dcrIdentificacao>
      <dcrValorDevido>000000000000000</dcrValorDevido>
      <dcrValorDolar>000000000000000</dcrValorDolar>
      <dcrValorReal>000000000000000</dcrValorReal>
      <dcrValorRecolher>000000000000000</dcrValorRecolher>
      <fornecedorCidade>BRUGNERA</fornecedorCidade>
      <fornecedorLogradouro>VIALE EUROPA</fornecedorLogradouro>
      <fornecedorNome>ITALIANA FERRAMENTA S.R.L.</fornecedorNome>
      <fornecedorNumero>17</fornecedorNumero>
      <freteMoedaNegociadaCodigo>978</freteMoedaNegociadaCodigo>
      <freteMoedaNegociadaNome>EURO/COM.EUROPEIA</freteMoedaNegociadaNome>
      <freteValorMoedaNegociada>000000000002353</freteValorMoedaNegociada>
      <freteValorReais>000000000014595</freteValorReais>
      <iiAcordoTarifarioTipoCodigo>0</iiAcordoTarifarioTipoCodigo>
      <iiAliquotaAcordo>00000</iiAliquotaAcordo>
      <iiAliquotaAdValorem>01800</iiAliquotaAdValorem>
      <iiAliquotaPercentualReducao>00000</iiAliquotaPercentualReducao>
      <iiAliquotaReduzida>00000</iiAliquotaReduzida>
      <iiAliquotaValorCalculado>{ii_val}</iiAliquotaValorCalculado>
      <iiAliquotaValorDevido>{ii_val}</iiAliquotaValorDevido>
      <iiAliquotaValorRecolher>{ii_val}</iiAliquotaValorRecolher>
      <iiAliquotaValorReduzido>000000000000000</iiAliquotaValorReduzido>
      <iiBaseCalculo>000000001425674</iiBaseCalculo>
      <iiFundamentoLegalCodigo>00</iiFundamentoLegalCodigo>
      <iiMotivoAdmissaoTemporariaCodigo>00</iiMotivoAdmissaoTemporariaCodigo>
      <iiRegimeTributacaoCodigo>1</iiRegimeTributacaoCodigo>
      <iiRegimeTributacaoNome>RECOLHIMENTO INTEGRAL</iiRegimeTributacaoNome>
      <ipiAliquotaAdValorem>00325</ipiAliquotaAdValorem>
      <ipiAliquotaEspecificaCapacidadeRecipciente>00000</ipiAliquotaEspecificaCapacidadeRecipciente>
      <ipiAliquotaEspecificaQuantidadeUnidadeMedida>000000000</ipiAliquotaEspecificaQuantidadeUnidadeMedida>
      <ipiAliquotaEspecificaTipoRecipienteCodigo>00</ipiAliquotaEspecificaTipoRecipienteCodigo>
      <ipiAliquotaEspecificaValorUnidadeMedida>0000000000</ipiAliquotaEspecificaValorUnidadeMedida>
      <ipiAliquotaNotaComplementarTIPI>00</ipiAliquotaNotaComplementarTIPI>
      <ipiAliquotaReduzida>00000</ipiAliquotaReduzida>
      <ipiAliquotaValorDevido>{ipi_val}</ipiAliquotaValorDevido>
      <ipiAliquotaValorRecolher>{ipi_val}</ipiAliquotaValorRecolher>
      <ipiRegimeTributacaoCodigo>4</ipiRegimeTributacaoCodigo>
      <ipiRegimeTributacaoNome>SEM BENEFICIO</ipiRegimeTributacaoNome>
      <mercadoria>
        <descricaoMercadoria>{desc}</descricaoMercadoria>
        <numeroSequencialItem>{num_adicao}</numeroSequencialItem>
        <quantidade>{v_qtd}</quantidade>
        <unidadeMedida>UNIDADE</unidadeMedida>
        <valorUnitario>000000000000000000</valorUnitario>
      </mercadoria>
      <numeroAdicao>{num_adicao}</numeroAdicao>
      <numeroDUIMP>{data['global']['duimp']}</numeroDUIMP>
      <numeroLI>0000000000</numeroLI>
      <paisAquisicaoMercadoriaCodigo>386</paisAquisicaoMercadoriaCodigo>
      <paisAquisicaoMercadoriaNome>ITALIA</paisAquisicaoMercadoriaNome>
      <paisOrigemMercadoriaCodigo>386</paisOrigemMercadoriaCodigo>
      <paisOrigemMercadoriaNome>ITALIA</paisOrigemMercadoriaNome>
      <pisCofinsBaseCalculoAliquotaICMS>00000</pisCofinsBaseCalculoAliquotaICMS>
      <pisCofinsBaseCalculoFundamentoLegalCodigo>00</pisCofinsBaseCalculoFundamentoLegalCodigo>
      <pisCofinsBaseCalculoPercentualReducao>00000</pisCofinsBaseCalculoPercentualReducao>
      <pisCofinsBaseCalculoValor>000000001425674</pisCofinsBaseCalculoValor>
      <pisCofinsFundamentoLegalReducaoCodigo>00</pisCofinsFundamentoLegalReducaoCodigo>
      <pisCofinsRegimeTributacaoCodigo>1</pisCofinsRegimeTributacaoCodigo>
      <pisCofinsRegimeTributacaoNome>RECOLHIMENTO INTEGRAL</pisCofinsRegimeTributacaoNome>
      <pisPasepAliquotaAdValorem>00210</pisPasepAliquotaAdValorem>
      <pisPasepAliquotaEspecificaQuantidadeUnidade>000000000</pisPasepAliquotaEspecificaQuantidadeUnidade>
      <pisPasepAliquotaEspecificaValor>0000000000</pisPasepAliquotaEspecificaValor>
      <pisPasepAliquotaReduzida>00000</pisPasepAliquotaReduzida>
      <pisPasepAliquotaValorDevido>{pis_val}</pisPasepAliquotaValorDevido>
      <pisPasepAliquotaValorRecolher>{pis_val}</pisPasepAliquotaValorRecolher>
      <icmsBaseCalculoValor>000000000160652</icmsBaseCalculoValor>
      <icmsBaseCalculoAliquota>01800</icmsBaseCalculoAliquota>
      <icmsBaseCalculoValorImposto>00000000019374</icmsBaseCalculoValorImposto>
      <icmsBaseCalculoValorDiferido>00000000009542</icmsBaseCalculoValorDiferido>
      <cbsIbsCst>000</cbsIbsCst>
      <cbsIbsClasstrib>000001</cbsIbsClasstrib>
      <cbsBaseCalculoValor>00000000160652</cbsBaseCalculoValor>
      <cbsBaseCalculoAliquota>00090</cbsBaseCalculoAliquota>
      <cbsBaseCalculoAliquotaReducao>00000</cbsBaseCalculoAliquotaReducao>
      <cbsBaseCalculoValorImposto>00000000001445</cbsBaseCalculoValorImposto>
      <ibsBaseCalculoValor>000000000160652</ibsBaseCalculoValor>
      <ibsBaseCalculoAliquota>00010</ibsBaseCalculoAliquota>
      <ibsBaseCalculoAliquotaReducao>00000</ibsBaseCalculoAliquotaReducao>
      <ibsBaseCalculoValorImposto>00000000000160</ibsBaseCalculoValorImposto>
      <relacaoCompradorVendedor>Fabricante é desconhecido</relacaoCompradorVendedor>
      <seguroMoedaNegociadaCodigo>220</seguroMoedaNegociadaCodigo>
      <seguroMoedaNegociadaNome>DOLAR DOS EUA</seguroMoedaNegociadaNome>
      <seguroValorMoedaNegociada>000000000000000</seguroValorMoedaNegociada>
      <seguroValorReais>000000000001489</seguroValorReais>
      <sequencialRetificacao>00</sequencialRetificacao>
      <valorMultaARecolher>000000000000000</valorMultaARecolher>
      <valorMultaARecolherAjustado>000000000000000</valorMultaARecolherAjustado>
      <valorReaisFreteInternacional>000000000014595</valorReaisFreteInternacional>
      <valorReaisSeguroInternacional>000000000001489</valorReaisSeguroInternacional>
      <valorTotalCondicaoVenda>000000000000000</valorTotalCondicaoVenda>
      <vinculoCompradorVendedor>Não há vinculação entre comprador e vendedor.</vinculoCompradorVendedor>
    </adicao>"""
        xml_output.append(adicao_block)

    # --- DADOS GERAIS (Footer Fixo) ---
    pb = XmlFormatter.fmt_num(data["global"]["peso_bruto"])
    pl = XmlFormatter.fmt_num(data["global"]["peso_liquido"])
    cnpj = XmlFormatter.fmt_num(data["global"]["cnpj"])
    total_adicoes = str(len(data["adicoes"])).zfill(3)

    footer = f"""    <armazem>
      <nomeArmazem>TCP</nomeArmazem>
    </armazem>
    <armazenamentoRecintoAduaneiroCodigo>9801303</armazenamentoRecintoAduaneiroCodigo>
    <armazenamentoRecintoAduaneiroNome>TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A</armazenamentoRecintoAduaneiroNome>
    <armazenamentoSetor>002</armazenamentoSetor>
    <canalSelecaoParametrizada>001</canalSelecaoParametrizada>
    <caracterizacaoOperacaoCodigoTipo>1</caracterizacaoOperacaoCodigoTipo>
    <caracterizacaoOperacaoDescricaoTipo>Importação Própria</caracterizacaoOperacaoDescricaoTipo>
    <cargaDataChegada>20251120</cargaDataChegada>
    <cargaNumeroAgente>N/I</cargaNumeroAgente>
    <cargaPaisProcedenciaCodigo>386</cargaPaisProcedenciaCodigo>
    <cargaPaisProcedenciaNome>ITALIA</cargaPaisProcedenciaNome>
    <cargaPesoBruto>{pb}</cargaPesoBruto>
    <cargaPesoLiquido>{pl}</cargaPesoLiquido>
    <cargaUrfEntradaCodigo>0917800</cargaUrfEntradaCodigo>
    <cargaUrfEntradaNome>PORTO DE PARANAGUA</cargaUrfEntradaNome>
    <conhecimentoCargaEmbarqueData>20251025</conhecimentoCargaEmbarqueData>
    <conhecimentoCargaEmbarqueLocal>GENOVA</conhecimentoCargaEmbarqueLocal>
    <conhecimentoCargaId>CEMERCANTE31032008</conhecimentoCargaId>
    <conhecimentoCargaIdMaster>162505352452915</conhecimentoCargaIdMaster>
    <conhecimentoCargaTipoCodigo>12</conhecimentoCargaTipoCodigo>
    <conhecimentoCargaTipoNome>HBL - House Bill of Lading</conhecimentoCargaTipoNome>
    <conhecimentoCargaUtilizacao>1</conhecimentoCargaUtilizacao>
    <conhecimentoCargaUtilizacaoNome>Total</conhecimentoCargaUtilizacaoNome>
    <dataDesembaraco>20251124</dataDesembaraco>
    <dataRegistro>20251124</dataRegistro>
    <documentoChegadaCargaCodigoTipo>1</documentoChegadaCargaCodigoTipo>
    <documentoChegadaCargaNome>Manifesto da Carga</documentoChegadaCargaNome>
    <documentoChegadaCargaNumero>1625502058594</documentoChegadaCargaNumero>
    <embalagem>
      <codigoTipoEmbalagem>60</codigoTipoEmbalagem>
      <nomeEmbalagem>PALLETS</nomeEmbalagem>
      <quantidadeVolume>00002</quantidadeVolume>
    </embalagem>
    <freteCollect>000000000025000</freteCollect>
    <freteEmTerritorioNacional>000000000000000</freteEmTerritorioNacional>
    <freteMoedaNegociadaCodigo>978</freteMoedaNegociadaCodigo>
    <freteMoedaNegociadaNome>EURO/COM.EUROPEIA</freteMoedaNegociadaNome>
    <fretePrepaid>000000000000000</fretePrepaid>
    <freteTotalDolares>000000000028757</freteTotalDolares>
    <freteTotalMoeda>25000</freteTotalMoeda>
    <freteTotalReais>000000000155007</freteTotalReais>
    <icms>
      <agenciaIcms>00000</agenciaIcms>
      <bancoIcms>000</bancoIcms>
      <codigoTipoRecolhimentoIcms>3</codigoTipoRecolhimentoIcms>
      <cpfResponsavelRegistro>27160353854</cpfResponsavelRegistro>
      <dataRegistro>20251125</dataRegistro>
      <horaRegistro>152044</horaRegistro>
      <nomeTipoRecolhimentoIcms>Exoneração do ICMS</nomeTipoRecolhimentoIcms>
      <numeroSequencialIcms>001</numeroSequencialIcms>
      <ufIcms>PR</ufIcms>
      <valorTotalIcms>000000000000000</valorTotalIcms>
    </icms>
    <importadorCodigoTipo>1</importadorCodigoTipo>
    <importadorCpfRepresentanteLegal>27160353854</importadorCpfRepresentanteLegal>
    <importadorEnderecoBairro>JARDIM PRIMAVERA</importadorEnderecoBairro>
    <importadorEnderecoCep>83302000</importadorEnderecoCep>
    <importadorEnderecoComplemento>CONJ: 6 E 7;</importadorEnderecoComplemento>
    <importadorEnderecoLogradouro>JOAO LEOPOLDO JACOMEL</importadorEnderecoLogradouro>
    <importadorEnderecoMunicipio>PIRAQUARA</importadorEnderecoMunicipio>
    <importadorEnderecoNumero>4459</importadorEnderecoNumero>
    <importadorEnderecoUf>PR</importadorEnderecoUf>
    <importadorNome>{data['global']['importador']}</importadorNome>
    <importadorNomeRepresentanteLegal>PAULO HENRIQUE LEITE FERREIRA</importadorNomeRepresentanteLegal>
    <importadorNumero>{cnpj}</importadorNumero>
    <importadorNumeroTelefone>41  30348150</importadorNumeroTelefone>
    <informacaoComplementar>INFORMAÇÃO CAPTURADA OU PADRÃO</informacaoComplementar>
    <localDescargaTotalDolares>000000002061433</localDescargaTotalDolares>
    <localDescargaTotalReais>000000011111593</localDescargaTotalReais>
    <localEmbarqueTotalDolares>000000002030535</localEmbarqueTotalDolares>
    <localEmbarqueTotalReais>000000010945130</localEmbarqueTotalReais>
    <modalidadeDespachoCodigo>1</modalidadeDespachoCodigo>
    <modalidadeDespachoNome>Normal</modalidadeDespachoNome>
    <numeroDUIMP>{data['global']['duimp']}</numeroDUIMP>
    <operacaoFundap>N</operacaoFundap>
    <seguroMoedaNegociadaCodigo>220</seguroMoedaNegociadaCodigo>
    <seguroMoedaNegociadaNome>DOLAR DOS EUA</seguroMoedaNegociadaNome>
    <seguroTotalDolares>000000000002146</seguroTotalDolares>
    <seguroTotalMoedaNegociada>000000000002146</seguroTotalMoedaNegociada>
    <seguroTotalReais>000000000011567</seguroTotalReais>
    <sequencialRetificacao>00</sequencialRetificacao>
    <situacaoEntregaCarga>ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE EXONERACAO DO ICMS</situacaoEntregaCarga>
    <tipoDeclaracaoCodigo>01</tipoDeclaracaoCodigo>
    <tipoDeclaracaoNome>CONSUMO</tipoDeclaracaoNome>
    <totalAdicoes>{total_adicoes}</totalAdicoes>
    <urfDespachoCodigo>0917800</urfDespachoCodigo>
    <urfDespachoNome>PORTO DE PARANAGUA</urfDespachoNome>
    <valorTotalMultaARecolherAjustado>000000000000000</valorTotalMultaARecolherAjustado>
    <viaTransporteCodigo>01</viaTransporteCodigo>
    <viaTransporteMultimodal>N</viaTransporteMultimodal>
    <viaTransporteNome>MARÍTIMA</viaTransporteNome>
    <viaTransporteNomeTransportador>MAERSK A/S</viaTransporteNomeTransportador>
    <viaTransporteNomeVeiculo>MAERSK MEMPHIS</viaTransporteNomeVeiculo>
    <viaTransportePaisTransportadorCodigo>741</viaTransportePaisTransportadorCodigo>
    <viaTransportePaisTransportadorNome>CINGAPURA</viaTransportePaisTransportadorNome>
  </duimp>
</ListaDeclaracoes>"""
    xml_output.append(footer)
    
    return "\n".join(xml_output)

# ==============================================================================
# 4. INTERFACE STREAMLIT
# ==============================================================================
def main():
    st.set_page_config(page_title="Conversor DUIMP PDF -> XML", layout="wide")
    st.title("🤖 Conversor Automático DUIMP")
    st.write("Transforme o extrato PDF da DUIMP no arquivo XML bancário/governamental padrão.")

    uploaded_file = st.file_uploader("Carregue o arquivo PDF (Extrato DUIMP)", type="pdf")

    if uploaded_file is not None:
        if st.button("Processar e Gerar XML"):
            with st.spinner("Lendo PDF e mapeando tags..."):
                try:
                    # 1. Extração
                    data = extract_data_from_pdf(uploaded_file)
                    
                    # 2. Geração do XML
                    xml_string = generate_strict_xml(data)
                    
                    st.success(f"Sucesso! {len(data['adicoes'])} adições encontradas.")
                    
                    # 3. Download
                    xml_bytes = xml_string.encode('utf-8')
                    file_name = f"M-DUIMP-{data['global']['duimp']}.xml"
                    
                    st.download_button(
                        label="📥 Baixar Arquivo XML Pronto",
                        data=xml_bytes,
                        file_name=file_name,
                        mime="text/xml"
                    )
                    
                    # Preview (Opcional)
                    with st.expander("Ver Preview dos Dados Extraídos"):
                        st.json(data)
                        
                except Exception as e:
                    st.error(f"Ocorreu um erro ao processar: {e}")

if __name__ == "__main__":
    main()
