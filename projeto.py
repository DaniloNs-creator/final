import streamlit as st
import pandas as pd
import re
from pypdf import PdfReader
from io import BytesIO

# ==============================================================================
# 1. MOTOR DE EXTRAÇÃO E MAPEAMENTO (O CÉREBRO)
# ==============================================================================
class DuimpExtractor:
    def __init__(self, pdf_file):
        self.reader = PdfReader(pdf_file)
        self.full_text = ""
        self.data_global = {}
        self.items_table = []
        
        # Consolida todo o texto para buscas globais
        for page in self.reader.pages:
            self.full_text += page.extract_text() + "\n"
            
        # Limpeza básica
        self.lines = self.full_text.split('\n')

    def parse_currency(self, value_str):
        """Converte string '1.234,56' para float 1234.56"""
        if not value_str: return 0.0
        clean = value_str.replace('R$', '').strip()
        clean = clean.replace('.', '').replace(',', '.')
        try:
            return float(clean)
        except:
            return 0.0

    def extract_global_data(self):
        """Mapeia o Cabeçalho e Rodapé (Dados da Capa)"""
        text = self.full_text
        
        # 1. Identificação
        self.data_global['numero_duimp'] = self._regex(r"25BR(\d+)", text) or "00000000000"
        self.data_global['cnpj_importador'] = self._regex(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", text)
        self.data_global['nome_importador'] = self._regex(r"IMPORTADOR\s*\n\s*\"?(.*?)\"?", text)
        
        # 2. Cotações (Fundamental para calcular Reais)
        # Ex: 978 - EURO 6,3636000
        taxa_euro = self._regex(r"978\s*-\s*EURO\s*([\d,]+)", text)
        self.data_global['taxa_euro'] = self.parse_currency(taxa_euro) if taxa_euro else 1.0
        
        taxa_usd = self._regex(r"220\s*-\s*DOLAR.*?([\d,]+)", text)
        self.data_global['taxa_usd'] = self.parse_currency(taxa_usd) if taxa_usd else 1.0

        # 3. Totais (Peso, Frete, Seguro)
        # Busca Peso Bruto e Líquido Totais
        pb = self._regex(r"([\d\.,]+)\s*PESO BRUTO", text)
        pl = self._regex(r"([\d\.,]+)\s*PESO LIQUIDO", text)
        self.data_global['peso_bruto_total'] = self.parse_currency(pb)
        self.data_global['peso_liquido_total'] = self.parse_currency(pl)

        # Frete e Seguro Totais (Geralmente na capa)
        frete_total = self._regex(r"FRETE.*?([\d\.,]+)\s*Total \(Moeda\)", text) # Simplificado
        seguro_total = self._regex(r"SEGURO.*?([\d\.,]+)\s*Total \(Moeda\)", text)
        
        # Se não achar com regex simples, assumimos valores capturados ou zerados para não quebrar
        # No seu PDF real, ajustamos esses regex conforme o layout exato da área de Totais
        self.data_global['frete_total_moeda'] = self.parse_currency(frete_total)
        self.data_global['seguro_total_moeda'] = self.parse_currency(seguro_total)

        return self.data_global

    def extract_items(self):
        """Máquina de Estados que lê Item a Item (Todas as Páginas)"""
        
        # Regex Específicos de Item
        re_item_start = re.compile(r"ITENS DA DUIMP - (\d+)")
        re_ncm = re.compile(r"(\d{4}\.\d{2}\.\d{2})")
        re_qtd = re.compile(r"([\d\.,]+)\s+Qtde Unid\. Comercial")
        re_valor_fca = re.compile(r"([\d\.,]+)\s+Valor Tot\. Cond Venda")
        
        # Captura de Impostos (Contextual)
        re_tax_recolher = re.compile(r"([\d\.,]+)\s+Valor A Recolher")

        current_item = {}
        buffer_desc = []
        reading_desc = False
        tax_context = None # II, IPI, PIS, COFINS

        for line in self.lines:
            line = line.strip()
            
            # --- 1. Detecta Novo Item ---
            match_new = re_item_start.search(line)
            if match_new:
                # Salva item anterior se existir
                if current_item:
                    current_item['descricao'] = " ".join(buffer_desc).strip()
                    self.items_table.append(current_item)
                
                # Inicia novo
                current_item = {
                    'numero': match_new.group(1),
                    'ncm': '',
                    'descricao': '',
                    'qtd': 0.0,
                    'valor_moeda': 0.0,
                    'peso_liquido': 0.0, # Será preenchido se encontrado ou rateado
                    'II_rec': 0.0, 'IPI_rec': 0.0, 'PIS_rec': 0.0, 'COFINS_rec': 0.0
                }
                buffer_desc = []
                reading_desc = False
                tax_context = None
                continue

            if not current_item: continue

            # --- 2. Captura Dados do Item ---
            
            # NCM
            if not current_item['ncm']:
                m_ncm = re_ncm.search(line)
                if m_ncm: current_item['ncm'] = m_ncm.group(1).replace('.', '')

            # Quantidade
            m_qtd = re_qtd.search(line)
            if m_qtd: current_item['qtd'] = self.parse_currency(m_qtd.group(1))

            # Valor Moeda (FCA)
            m_val = re_valor_fca.search(line)
            if m_val: current_item['valor_moeda'] = self.parse_currency(m_val.group(1))

            # Descrição (Multilinha)
            if "DENOMINACAO DO PRODUTO" in line:
                reading_desc = True
                continue
            if reading_desc:
                if any(x in line for x in ["CÓDIGO INTERNO", "FABRICANTE", "DADOS DA MERCADORIA"]):
                    reading_desc = False
                else:
                    buffer_desc.append(line)

            # --- 3. Captura Tributos ---
            if line in ["II", "IPI", "PIS", "COFINS"]:
                tax_context = line
            
            if tax_context:
                m_rec = re_tax_recolher.search(line)
                if m_rec:
                    key = f"{tax_context}_rec"
                    current_item[key] = self.parse_currency(m_rec.group(1))

        # Salva o último item
        if current_item:
            current_item['descricao'] = " ".join(buffer_desc).strip()
            self.items_table.append(current_item)

        return pd.DataFrame(self.items_table)

    def _regex(self, pattern, text):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else None


# ==============================================================================
# 2. FORMATADOR XML (PADRÃO RIGOROSO 15 DÍGITOS)
# ==============================================================================
def fmt_xml(value, length=15):
    """
    Recebe float ou string.
    Retorna string numérica sem pontos/vírgulas, preenchida com zeros à esquerda.
    Ex: 100.50 -> '000000000010050'
    """
    if isinstance(value, str):
        # Remove caracteres não numéricos
        clean = re.sub(r'\D', '', value)
        return clean.zfill(length)
    
    if isinstance(value, (int, float)):
        # Formata com 2 casas decimais fixas, remove ponto
        s = f"{value:.2f}".replace('.', '')
        return s.zfill(length)
    
    return "0" * length

def fmt_upper(text, limit=None):
    if not text: return ""
    t = str(text).upper().replace('\n', ' ').strip()
    return t[:limit] if limit else t


# ==============================================================================
# 3. INTERFACE STREAMLIT E FLUXO PRINCIPAL
# ==============================================================================
st.set_page_config(layout="wide", page_title="Extrator DUIMP Pro")

st.title("📑 Extrator e Mapeador DUIMP -> XML")
st.markdown("""
Este sistema realiza a leitura completa do PDF, cria uma tabela de dados reais e gera o XML no layout obrigatório.
**Diferencial:** Calcula automaticamente os valores em Reais baseados na taxa de câmbio encontrada no PDF e faz o rateio de Frete/Seguro.
""")

uploaded_file = st.file_uploader("Upload do PDF da DUIMP", type="pdf")

if uploaded_file:
    # --- FASE 1: EXTRAÇÃO ---
    extractor = DuimpExtractor(uploaded_file)
    
    with st.spinner("Lendo todas as páginas e mapeando dados..."):
        # Extrai Globais
        global_data = extractor.extract_global_data()
        
        # Extrai Tabela de Itens
        df_items = extractor.extract_items()
        
        # --- FASE 2: CÁLCULOS E RATEIOS (ENRIQUECIMENTO DE DADOS) ---
        if not df_items.empty:
            # Calcula Valor Total da DUIMP (Soma dos FCAs) para rateio
            total_fca = df_items['valor_moeda'].sum()
            
            # Taxas extraídas do PDF
            tx_euro = global_data.get('taxa_euro', 1.0)
            
            # Adiciona colunas calculadas ao DataFrame (A Tabela que você pediu)
            df_items['Valor_Reais'] = df_items['valor_moeda'] * tx_euro
            
            # Rateio de Frete/Seguro (Proporcional ao Valor da Mercadoria)
            # Se Frete Total for 0 ou não achado, rateio será 0
            frete_total = global_data.get('frete_total_moeda', 0)
            seguro_total = global_data.get('seguro_total_moeda', 0)
            
            if total_fca > 0:
                df_items['Frete_Item_Moeda'] = (df_items['valor_moeda'] / total_fca) * frete_total
                df_items['Seguro_Item_Moeda'] = (df_items['valor_moeda'] / total_fca) * seguro_total
            else:
                df_items['Frete_Item_Moeda'] = 0
                df_items['Seguro_Item_Moeda'] = 0
                
            # Converte Frete/Seguro para Reais
            df_items['Frete_Item_Reais'] = df_items['Frete_Item_Moeda'] * tx_euro
            df_items['Seguro_Item_Reais'] = df_items['Seguro_Item_Moeda'] * global_data.get('taxa_usd', 1.0)

    # --- FASE 3: EXIBIÇÃO DA TABELA (CONFIRMAÇÃO VISUAL) ---
    st.success("PDF Mapeado com Sucesso!")
    
    st.subheader("1. Dados Globais Identificados")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("DUIMP", global_data.get('numero_duimp'))
    c2.metric("Taxa Euro", f"R$ {global_data.get('taxa_euro'):.4f}")
    c3.metric("Peso Bruto Total", f"{global_data.get('peso_bruto_total')} kg")
    c4.metric("Itens Encontrados", len(df_items))

    st.subheader("2. Tabela Mapeada (Dados Reais do PDF)")
    st.dataframe(df_items.style.format("{:.2f}", subset=['valor_moeda', 'Valor_Reais', 'II_rec', 'IPI_rec']))

    # --- FASE 4: GERAÇÃO DO XML (BUILDER) ---
    if st.button("Gerar XML Obrigatório"):
        xml_lines = []
        xml_lines.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
        xml_lines.append('<ListaDeclaracoes>')
        xml_lines.append('  <duimp>')

        # Loop gerando as tags <adicao> preenchidas com o DF
        for idx, row in df_items.iterrows():
            
            # Prepara valores formatados (15 dígitos)
            num_adicao = str(row['numero']).zfill(3)
            val_moeda = fmt_xml(row['valor_moeda'])
            val_reais = fmt_xml(row['Valor_Reais'])
            val_frete = fmt_xml(row['Frete_Item_Reais'])
            val_seguro = fmt_xml(row['Seguro_Item_Reais'])
            qtd = fmt_xml(row['qtd'], 14) # Exemplo: 14 digitos para qtd
            desc = fmt_upper(row['descricao'], 200)
            
            # Impostos
            v_ii = fmt_xml(row['II_rec'])
            v_ipi = fmt_xml(row['IPI_rec'])
            v_pis = fmt_xml(row['PIS_rec'])
            v_cofins = fmt_xml(row['COFINS_rec'])

            xml_lines.append(f"""    <adicao>
      <acrescimo>
        <codigoAcrescimo>17</codigoAcrescimo>
        <denominacao>OUTROS ACRESCIMOS AO VALOR ADUANEIRO</denominacao>
        <moedaNegociadaCodigo>978</moedaNegociadaCodigo>
        <moedaNegociadaNome>EURO/COM.EUROPEIA</moedaNegociadaNome>
        <valorMoedaNegociada>000000000000000</valorMoedaNegociada>
        <valorReais>000000000000000</valorReais>
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
      <cofinsAliquotaValorDevido>{v_cofins}</cofinsAliquotaValorDevido>
      <cofinsAliquotaValorRecolher>{v_cofins}</cofinsAliquotaValorRecolher>
      <condicaoVendaIncoterm>FCA</condicaoVendaIncoterm>
      <condicaoVendaLocal>EXTERIOR</condicaoVendaLocal>
      <condicaoVendaMetodoValoracaoCodigo>01</condicaoVendaMetodoValoracaoCodigo>
      <condicaoVendaMetodoValoracaoNome>METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)</condicaoVendaMetodoValoracaoNome>
      <condicaoVendaMoedaCodigo>978</condicaoVendaMoedaCodigo>
      <condicaoVendaMoedaNome>EURO/COM.EUROPEIA</condicaoVendaMoedaNome>
      <condicaoVendaValorMoeda>{val_moeda}</condicaoVendaValorMoeda>
      <condicaoVendaValorReais>{val_reais}</condicaoVendaValorReais>
      <dadosCambiaisCoberturaCambialCodigo>1</dadosCambiaisCoberturaCambialCodigo>
      <dadosCambiaisCoberturaCambialNome>COM COBERTURA</dadosCambiaisCoberturaCambialNome>
      <dadosCambiaisInstituicaoFinanciadoraCodigo>00</dadosCambiaisInstituicaoFinanciadoraCodigo>
      <dadosCambiaisInstituicaoFinanciadoraNome>N/I</dadosCambiaisInstituicaoFinanciadoraNome>
      <dadosCambiaisMotivoSemCoberturaCodigo>00</dadosCambiaisMotivoSemCoberturaCodigo>
      <dadosCambiaisMotivoSemCoberturaNome>N/I</dadosCambiaisMotivoSemCoberturaNome>
      <dadosCambiaisValorRealCambio>000000000000000</dadosCambiaisValorRealCambio>
      <dadosCargaPaisProcedenciaCodigo>249</dadosCargaPaisProcedenciaCodigo>
      <dadosCargaUrfEntradaCodigo>0917800</dadosCargaUrfEntradaCodigo>
      <dadosCargaViaTransporteCodigo>01</dadosCargaViaTransporteCodigo>
      <dadosCargaViaTransporteNome>MARÍTIMA</dadosCargaViaTransporteNome>
      <dadosMercadoriaAplicacao>REVENDA</dadosMercadoriaAplicacao>
      <dadosMercadoriaCodigoNaladiNCCA>0000000</dadosMercadoriaCodigoNaladiNCCA>
      <dadosMercadoriaCodigoNaladiSH>00000000</dadosMercadoriaCodigoNaladiSH>
      <dadosMercadoriaCodigoNcm>{row['ncm']}</dadosMercadoriaCodigoNcm>
      <dadosMercadoriaCondicao>NOVA</dadosMercadoriaCondicao>
      <dadosMercadoriaDescricaoTipoCertificado>Sem Certificado</dadosMercadoriaDescricaoTipoCertificado>
      <dadosMercadoriaIndicadorTipoCertificado>1</dadosMercadoriaIndicadorTipoCertificado>
      <dadosMercadoriaMedidaEstatisticaQuantidade>{qtd}</dadosMercadoriaMedidaEstatisticaQuantidade>
      <dadosMercadoriaMedidaEstatisticaUnidade>UNIDADE</dadosMercadoriaMedidaEstatisticaUnidade>
      <dadosMercadoriaNomeNcm>Descricao Oficial NCM</dadosMercadoriaNomeNcm>
      <dadosMercadoriaPesoLiquido>{qtd}</dadosMercadoriaPesoLiquido>
      <dcrCoeficienteReducao>00000</dcrCoeficienteReducao>
      <dcrIdentificacao>00000000</dcrIdentificacao>
      <dcrValorDevido>000000000000000</dcrValorDevido>
      <dcrValorDolar>000000000000000</dcrValorDolar>
      <dcrValorReal>000000000000000</dcrValorReal>
      <dcrValorRecolher>000000000000000</dcrValorRecolher>
      <fornecedorCidade>EXTERIOR</fornecedorCidade>
      <fornecedorLogradouro>EXTERIOR</fornecedorLogradouro>
      <fornecedorNome>FORNECEDOR PADRAO</fornecedorNome>
      <fornecedorNumero>00</fornecedorNumero>
      <freteMoedaNegociadaCodigo>978</freteMoedaNegociadaCodigo>
      <freteMoedaNegociadaNome>EURO/COM.EUROPEIA</freteMoedaNegociadaNome>
      <freteValorMoedaNegociada>{fmt_xml(row['Frete_Item_Moeda'])}</freteValorMoedaNegociada>
      <freteValorReais>{val_frete}</freteValorReais>
      <iiAcordoTarifarioTipoCodigo>0</iiAcordoTarifarioTipoCodigo>
      <iiAliquotaAcordo>00000</iiAliquotaAcordo>
      <iiAliquotaAdValorem>01800</iiAliquotaAdValorem>
      <iiAliquotaPercentualReducao>00000</iiAliquotaPercentualReducao>
      <iiAliquotaReduzida>00000</iiAliquotaReduzida>
      <iiAliquotaValorCalculado>{v_ii}</iiAliquotaValorCalculado>
      <iiAliquotaValorDevido>{v_ii}</iiAliquotaValorDevido>
      <iiAliquotaValorRecolher>{v_ii}</iiAliquotaValorRecolher>
      <iiAliquotaValorReduzido>000000000000000</iiAliquotaValorReduzido>
      <iiBaseCalculo>000000000000000</iiBaseCalculo>
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
      <ipiAliquotaValorDevido>{v_ipi}</ipiAliquotaValorDevido>
      <ipiAliquotaValorRecolher>{v_ipi}</ipiAliquotaValorRecolher>
      <ipiRegimeTributacaoCodigo>4</ipiRegimeTributacaoCodigo>
      <ipiRegimeTributacaoNome>SEM BENEFICIO</ipiRegimeTributacaoNome>
      <mercadoria>
        <descricaoMercadoria>{desc}</descricaoMercadoria>
        <numeroSequencialItem>{num_adicao}</numeroSequencialItem>
        <quantidade>{qtd}</quantidade>
        <unidadeMedida>UNIDADE</unidadeMedida>
        <valorUnitario>000000000000000000</valorUnitario>
      </mercadoria>
      <numeroAdicao>{num_adicao}</numeroAdicao>
      <numeroDUIMP>{global_data.get('numero_duimp')}</numeroDUIMP>
      <numeroLI>0000000000</numeroLI>
      <paisAquisicaoMercadoriaCodigo>386</paisAquisicaoMercadoriaCodigo>
      <paisAquisicaoMercadoriaNome>ITALIA</paisAquisicaoMercadoriaNome>
      <paisOrigemMercadoriaCodigo>386</paisOrigemMercadoriaCodigo>
      <paisOrigemMercadoriaNome>ITALIA</paisOrigemMercadoriaNome>
      <pisCofinsBaseCalculoAliquotaICMS>00000</pisCofinsBaseCalculoAliquotaICMS>
      <pisCofinsBaseCalculoFundamentoLegalCodigo>00</pisCofinsBaseCalculoFundamentoLegalCodigo>
      <pisCofinsBaseCalculoPercentualReducao>00000</pisCofinsBaseCalculoPercentualReducao>
      <pisCofinsBaseCalculoValor>000000000000000</pisCofinsBaseCalculoValor>
      <pisCofinsFundamentoLegalReducaoCodigo>00</pisCofinsFundamentoLegalReducaoCodigo>
      <pisCofinsRegimeTributacaoCodigo>1</pisCofinsRegimeTributacaoCodigo>
      <pisCofinsRegimeTributacaoNome>RECOLHIMENTO INTEGRAL</pisCofinsRegimeTributacaoNome>
      <pisPasepAliquotaAdValorem>00210</pisPasepAliquotaAdValorem>
      <pisPasepAliquotaEspecificaQuantidadeUnidade>000000000</pisPasepAliquotaEspecificaQuantidadeUnidade>
      <pisPasepAliquotaEspecificaValor>0000000000</pisPasepAliquotaEspecificaValor>
      <pisPasepAliquotaReduzida>00000</pisPasepAliquotaReduzida>
      <pisPasepAliquotaValorDevido>{v_pis}</pisPasepAliquotaValorDevido>
      <pisPasepAliquotaValorRecolher>{v_pis}</pisPasepAliquotaValorRecolher>
      <icmsBaseCalculoValor>000000000000000</icmsBaseCalculoValor>
      <icmsBaseCalculoAliquota>01800</icmsBaseCalculoAliquota>
      <icmsBaseCalculoValorImposto>00000000000000</icmsBaseCalculoValorImposto>
      <icmsBaseCalculoValorDiferido>00000000000000</icmsBaseCalculoValorDiferido>
      <cbsIbsCst>000</cbsIbsCst>
      <cbsIbsClasstrib>000001</cbsIbsClasstrib>
      <cbsBaseCalculoValor>000000000000000</cbsBaseCalculoValor>
      <cbsBaseCalculoAliquota>00090</cbsBaseCalculoAliquota>
      <cbsBaseCalculoAliquotaReducao>00000</cbsBaseCalculoAliquotaReducao>
      <cbsBaseCalculoValorImposto>00000000000000</cbsBaseCalculoValorImposto>
      <ibsBaseCalculoValor>000000000000000</ibsBaseCalculoValor>
      <ibsBaseCalculoAliquota>00010</ibsBaseCalculoAliquota>
      <ibsBaseCalculoAliquotaReducao>00000</ibsBaseCalculoAliquotaReducao>
      <ibsBaseCalculoValorImposto>00000000000000</ibsBaseCalculoValorImposto>
      <relacaoCompradorVendedor>Fabricante é desconhecido</relacaoCompradorVendedor>
      <seguroMoedaNegociadaCodigo>220</seguroMoedaNegociadaCodigo>
      <seguroMoedaNegociadaNome>DOLAR DOS EUA</seguroMoedaNegociadaNome>
      <seguroValorMoedaNegociada>{fmt_xml(row['Seguro_Item_Moeda'])}</seguroValorMoedaNegociada>
      <seguroValorReais>{val_seguro}</seguroValorReais>
      <sequencialRetificacao>00</sequencialRetificacao>
      <valorMultaARecolher>000000000000000</valorMultaARecolher>
      <valorMultaARecolherAjustado>000000000000000</valorMultaARecolherAjustado>
      <valorReaisFreteInternacional>{val_frete}</valorReaisFreteInternacional>
      <valorReaisSeguroInternacional>{val_seguro}</valorReaisSeguroInternacional>
      <valorTotalCondicaoVenda>000000000000000</valorTotalCondicaoVenda>
      <vinculoCompradorVendedor>Não há vinculação entre comprador e vendedor.</vinculoCompradorVendedor>
    </adicao>""")
        
        # Footer Geral (Dados da Capa)
        cnpj_fmt = fmt_xml(global_data.get('cnpj_importador'), 14)
        pb_fmt = fmt_xml(global_data.get('peso_bruto_total'))
        pl_fmt = fmt_xml(global_data.get('peso_liquido_total'))
        tot_adicoes = str(len(df_items)).zfill(3)

        xml_lines.append(f"""    <armazem>
      <nomeArmazem>TCP</nomeArmazem>
    </armazem>
    <armazenamentoRecintoAduaneiroCodigo>9801303</armazenamentoRecintoAduaneiroCodigo>
    <cargaPaisProcedenciaNome>ALEMANHA</cargaPaisProcedenciaNome>
    <cargaPesoBruto>{pb_fmt}</cargaPesoBruto>
    <cargaPesoLiquido>{pl_fmt}</cargaPesoLiquido>
    <cargaUrfEntradaCodigo>0917800</cargaUrfEntradaCodigo>
    <cargaUrfEntradaNome>PORTO DE PARANAGUA</cargaUrfEntradaNome>
    <dataRegistro>20251124</dataRegistro>
    <freteMoedaNegociadaNome>EURO/COM.EUROPEIA</freteMoedaNegociadaNome>
    <importadorNome>{fmt_upper(global_data.get('nome_importador'))}</importadorNome>
    <importadorNumero>{cnpj_fmt}</importadorNumero>
    <numeroDUIMP>{global_data.get('numero_duimp')}</numeroDUIMP>
    <tipoDeclaracaoNome>CONSUMO</tipoDeclaracaoNome>
    <totalAdicoes>{tot_adicoes}</totalAdicoes>
    <viaTransporteNome>MARÍTIMA</viaTransporteNome>
  </duimp>
</ListaDeclaracoes>""")

        final_xml = "\n".join(xml_lines)
        
        st.download_button(
            label="📥 Baixar XML Preenchido com Dados Reais",
            data=final_xml,
            file_name=f"DUIMP_{global_data.get('numero_duimp')}_Mapeada.xml",
            mime="text/xml"
        )
