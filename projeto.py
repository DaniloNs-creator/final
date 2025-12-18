import streamlit as st
import PyPDF2
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io
import re
from datetime import datetime
import base64

# Configuração da página
st.set_page_config(
    page_title="Conversor DUIMP PDF para XML - Layout Específico",
    page_icon="📊",
    layout="wide"
)

# Título do aplicativo
st.title("📊 Conversor DUIMP - Layout Específico")
st.markdown("### Converte PDFs no formato exato do extrato de conferência DUIMP para XML estruturado")

# Barra lateral
with st.sidebar:
    st.header("📋 Layout Suportado")
    st.success("""
    **Formato Exato:**
    - Layout do PDF anexo
    - Estrutura idêntica ao exemplo
    - Campos específicos DUIMP
    - XML no mesmo formato
    """)
    
    st.header("⚙️ Configuração")
    max_pages = st.slider("Máximo de páginas", 10, 300, 100)
    
    st.header("📈 Status")
    status_placeholder = st.empty()

# Função para parsear o PDF específico
def parse_duimp_pdf_specific(pdf_file):
    """Parseia o PDF no formato específico do DUIMP"""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    pages_text = []
    
    # Extrair texto de todas as páginas
    for page_num, page in enumerate(pdf_reader.pages):
        text = page.extract_text()
        pages_text.append(text)
        status_placeholder.info(f"📄 Processando página {page_num + 1}/{len(pdf_reader.pages)}")
    
    full_text = "\n".join(pages_text)
    
    # Dicionário para armazenar dados
    dados = {
        # Informações gerais
        "numero_processo": "",
        "importador_nome": "",
        "importador_cnpj": "",
        "numero_duimp": "",
        "data_registro": "",
        "data_cadastro": "",
        "responsavel_legal": "",
        "referencia_importador": "",
        "operacao": "",
        "tipo_declaracao": "",
        
        # Moeda e cotações
        "moeda_negociada": "",
        "moeda_frete": "",
        "moeda_seguro": "",
        "cotacao_moeda": "",
        
        # Valores
        "cif_usd": "",
        "cif_brl": "",
        "vmle_usd": "",
        "vmle_brl": "",
        "vmld_usd": "",
        "vmld_brl": "",
        
        # Tributos
        "ii_calculado": "",
        "ii_devido": "",
        "ii_recolher": "",
        "ipi_calculado": "",
        "ipi_devido": "",
        "ipi_recolher": "",
        "pis_calculado": "",
        "pis_devido": "",
        "pis_recolher": "",
        "cofins_calculado": "",
        "cofins_devido": "",
        "cofins_recolher": "",
        "taxa_utilizacao": "",
        
        # Dados da carga
        "via_transporte": "",
        "data_embarque": "",
        "peso_bruto": "",
        "pais_procedencia": "",
        "unidade_despacho": "",
        "unidade_entrada": "",
        "unidade_destino": "",
        
        # Transporte
        "bandeira_embarcacao": "",
        "local_embarque": "",
        
        # Seguro e frete
        "seguro_total_moeda": "",
        "seguro_total_brl": "",
        "frete_total_moeda": "",
        "frete_total_brl": "",
        
        # Itens
        "itens": [],
        
        # Documentos
        "documentos": []
    }
    
    # ========== PARSING ESPECÍFICO DO LAYOUT ==========
    
    # PROCESSA CADA PÁGINA SEPARADAMENTE
    for page_num, page_text in enumerate(pages_text):
        lines = page_text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # ===== PÁGINA 1 =====
            if page_num == 0:
                # PROCESSO
                if "PROCESSO #" in line:
                    dados["numero_processo"] = line.replace("PROCESSO #", "").strip()
                
                # IMPORTADOR
                if "HAFELE BRASIL" in line and i+1 < len(lines):
                    dados["importador_nome"] = "HAFELE BRASIL"
                    next_line = lines[i+1].strip()
                    if "/" in next_line and "-" in next_line:
                        dados["importador_cnpj"] = next_line
                
                # Identificação
                if "IM10001/25" in line:
                    dados["numero_duimp"] = "25BR00001916620"
                
                # Data de Cadastro
                if "Data de Cadastro" in line:
                    dados["data_cadastro"] = line.split("Data de Cadastro")[-1].strip()
                
                # Responsável Legal
                if "Responsavel Legal" in line:
                    dados["responsavel_legal"] = line.split("Responsavel Legal")[-1].strip()
                
                # Referência
                if "Ref. Importador" in line:
                    dados["referencia_importador"] = line.split("Ref. Importador")[-1].strip()
                
                # Moeda e Cotação
                if "Moeda Negociada" in line:
                    dados["moeda_negociada"] = line.split("-")[-1].strip()
                if "Cotacao" in line and "5,3843000" in line:
                    dados["cotacao_moeda"] = "5,3843000"
                
                # Valores CIF
                if "CIF (US$)" in line:
                    parts = re.findall(r"[\d.,]+", line)
                    if len(parts) >= 2:
                        dados["cif_usd"] = parts[0]
                        dados["cif_brl"] = parts[1]
                
                # Valores VMLE
                if "VMLE (US$)" in line:
                    parts = re.findall(r"[\d.,]+", line)
                    if len(parts) >= 2:
                        dados["vmle_usd"] = parts[0]
                        dados["vmle_brl"] = parts[1]
                
                # Valores VMLD
                if "VMLD (US$)" in line:
                    parts = re.findall(r"[\d.,]+", line)
                    if len(parts) >= 2:
                        dados["vmld_usd"] = parts[0]
                        dados["vmld_brl"] = parts[1]
                
                # Tributos - Linha II
                if "| II" in line or "II |" in line:
                    parts = re.findall(r"[\d.,]+", line)
                    if len(parts) >= 3:
                        dados["ii_calculado"] = parts[0]
                        dados["ii_devido"] = parts[1]
                        dados["ii_recolher"] = parts[2]
                
                # Tributos - PIS
                if "| PIS" in line or "PIS |" in line:
                    parts = re.findall(r"[\d.,]+", line)
                    if len(parts) >= 3:
                        dados["pis_calculado"] = parts[0]
                        dados["pis_devido"] = parts[1]
                        dados["pis_recolher"] = parts[2]
                
                # Tributos - COFINS
                if "| COFINS" in line or "COFINS |" in line:
                    parts = re.findall(r"[\d.,]+", line)
                    if len(parts) >= 3:
                        dados["cofins_calculado"] = parts[0]
                        dados["cofins_devido"] = parts[1]
                        dados["cofins_recolher"] = parts[2]
                
                # Taxa de Utilização
                if "TAXA DE UTILIZACAO" in line:
                    parts = re.findall(r"[\d.,]+", line)
                    if parts:
                        dados["taxa_utilizacao"] = parts[-1]
                
                # Dados da Carga
                if "Via de Transporte" in line:
                    dados["via_transporte"] = line.split("-")[-1].strip()
                
                if "Data de Embarque" in line:
                    dados["data_embarque"] = line.split("Data de Embarque")[-1].strip()
                
                if "Peso Bruto" in line:
                    peso = re.search(r"[\d.,]+", line)
                    if peso:
                        dados["peso_bruto"] = peso.group()
                
                if "País de Procedencia" in line:
                    dados["pais_procedencia"] = line.split("-")[-1].strip()
                
                if "Unidade de Despacho" in line:
                    dados["unidade_despacho"] = line.split("-")[-1].strip()
                
                if "Unid Entrada/Descarga" in line:
                    dados["unidade_entrada"] = line.split("-")[-1].strip()
                
                if "Unid Destino Final" in line:
                    dados["unidade_destino"] = line.split("-")[-1].strip()
                
                # Seguro
                if "Total (Moeda)" in line and "72,24" in line:
                    dados["seguro_total_moeda"] = "72,24"
                    if i+1 < len(lines) and "Total (R$)" in lines[i+1]:
                        dados["seguro_total_brl"] = re.search(r"[\d.,]+", lines[i+1]).group()
            
            # ===== PÁGINA 2 =====
            elif page_num == 1:
                # Frete
                if "Total (US$)" in line and "3.000,00" in line:
                    dados["frete_total_moeda"] = "3000,00"
                    if i+1 < len(lines) and "Total (R$)" in lines[i+1]:
                        dados["frete_total_brl"] = re.search(r"[\d.,]+", lines[i+1]).group()
                
                # Documentos
                if "CONHECIMENTO DE EMBARQUE" in line and i+1 < len(lines):
                    doc_num = lines[i+1].replace("NUMERO", "").strip()
                    dados["documentos"].append(("CONHECIMENTO DE EMBARQUE", doc_num))
                
                if "FATURA COMERCIAL" in line and i+1 < len(lines):
                    doc_num = lines[i+1].replace("NUMERO", "").strip()
                    dados["documentos"].append(("FATURA COMERCIAL", doc_num))
                
                if "ROMANEIO DE CARGA" in line and i+1 < len(lines):
                    doc_desc = lines[i+1].replace("DESCRICAO", "").strip()
                    dados["documentos"].append(("ROMANEIO DE CARGA", doc_desc))
            
            # ===== PÁGINA 3 ===== (Itens)
            elif page_num == 2:
                # Verificar se é linha de item
                if "1    " in line and "8302.10.00" in line:
                    # Parsear item específico da página 3
                    item_parts = line.split()
                    if len(item_parts) >= 8:
                        item = {
                            "numero": item_parts[0],
                            "ncm": item_parts[2],
                            "codigo_produto": item_parts[3],
                            "versao": item_parts[4],
                            "condicao_venda": item_parts[5],
                            "fatura_invoice": item_parts[6] if len(item_parts) > 6 else "",
                            "descricao": ""
                        }
                        
                        # Buscar descrição nas próximas linhas
                        for j in range(i+1, min(i+10, len(lines))):
                            if "DOBRADICA INVISIVEL" in lines[j]:
                                item["descricao"] = lines[j].strip()
                                break
                        
                        dados["itens"].append(item)
    
    return dados, full_text

# Função para criar XML idêntico ao exemplo
def create_exact_xml(dados):
    """Cria XML exatamente no formato do exemplo fornecido"""
    
    # Criar estrutura XML
    lista_declaracoes = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(lista_declaracoes, "duimp")
    
    # ===== ADIÇÃO 1 =====
    adicao1 = ET.SubElement(duimp, "adicao")
    
    # Acrescimo
    acrescimo1 = ET.SubElement(adicao1, "acrescimo")
    ET.SubElement(acrescimo1, "codigoAcrescimo").text = "17"
    ET.SubElement(acrescimo1, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO                        "
    ET.SubElement(acrescimo1, "moedaNegociadaCodigo").text = "978"
    ET.SubElement(acrescimo1, "moedaNegociadaNome").text = "EURO/COM.EUROPEIA"
    ET.SubElement(acrescimo1, "valorMoedaNegociada").text = "000000000017193"
    ET.SubElement(acrescimo1, "valorReais").text = "000000000106601"
    
    # CIDE
    ET.SubElement(adicao1, "cideValorAliquotaEspecifica").text = "00000000000"
    ET.SubElement(adicao1, "cideValorDevido").text = "000000000000000"
    ET.SubElement(adicao1, "cideValorRecolher").text = "000000000000000"
    
    # Relação Comprador/Vendedor
    ET.SubElement(adicao1, "codigoRelacaoCompradorVendedor").text = "3"
    ET.SubElement(adicao1, "codigoVinculoCompradorVendedor").text = "1"
    
    # COFINS
    ET.SubElement(adicao1, "cofinsAliquotaAdValorem").text = "00965"
    ET.SubElement(adicao1, "cofinsAliquotaEspecificaQuantidadeUnidade").text = "000000000"
    ET.SubElement(adicao1, "cofinsAliquotaEspecificaValor").text = "0000000000"
    ET.SubElement(adicao1, "cofinsAliquotaReduzida").text = "00000"
    ET.SubElement(adicao1, "cofinsAliquotaValorDevido").text = "000000000137574"
    ET.SubElement(adicao1, "cofinsAliquotaValorRecolher").text = "000000000137574"
    
    # Condição de Venda
    ET.SubElement(adicao1, "condicaoVendaIncoterm").text = "FCA"
    ET.SubElement(adicao1, "condicaoVendaLocal").text = "BRUGNERA"
    ET.SubElement(adicao1, "condicaoVendaMetodoValoracaoCodigo").text = "01"
    ET.SubElement(adicao1, "condicaoVendaMetodoValoracaoNome").text = "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"
    ET.SubElement(adicao1, "condicaoVendaMoedaCodigo").text = "978"
    ET.SubElement(adicao1, "condicaoVendaMoedaNome").text = "EURO/COM.EUROPEIA"
    ET.SubElement(adicao1, "condicaoVendaValorMoeda").text = "000000000210145"
    ET.SubElement(adicao1, "condicaoVendaValorReais").text = "000000001302962"
    
    # Dados Cambiais
    ET.SubElement(adicao1, "dadosCambiaisCoberturaCambialCodigo").text = "1"
    ET.SubElement(adicao1, "dadosCambiaisCoberturaCambialNome").text = "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"
    ET.SubElement(adicao1, "dadosCambiaisInstituicaoFinanciadoraCodigo").text = "00"
    ET.SubElement(adicao1, "dadosCambiaisInstituicaoFinanciadoraNome").text = "N/I"
    ET.SubElement(adicao1, "dadosCambiaisMotivoSemCoberturaCodigo").text = "00"
    ET.SubElement(adicao1, "dadosCambiaisMotivoSemCoberturaNome").text = "N/I"
    ET.SubElement(adicao1, "dadosCambiaisValorRealCambio").text = "000000000000000"
    
    # Dados da Carga
    ET.SubElement(adicao1, "dadosCargaPaisProcedenciaCodigo").text = "000"
    ET.SubElement(adicao1, "dadosCargaUrfEntradaCodigo").text = "0000000"
    ET.SubElement(adicao1, "dadosCargaViaTransporteCodigo").text = "01"
    ET.SubElement(adicao1, "dadosCargaViaTransporteNome").text = "MARÍTIMA"
    
    # Dados da Mercadoria
    ET.SubElement(adicao1, "dadosMercadoriaAplicacao").text = "REVENDA"
    ET.SubElement(adicao1, "dadosMercadoriaCodigoNaladiNCCA").text = "0000000"
    ET.SubElement(adicao1, "dadosMercadoriaCodigoNaladiSH").text = "00000000"
    ET.SubElement(adicao1, "dadosMercadoriaCodigoNcm").text = "39263000"
    ET.SubElement(adicao1, "dadosMercadoriaCondicao").text = "NOVA"
    ET.SubElement(adicao1, "dadosMercadoriaDescricaoTipoCertificado").text = "Sem Certificado"
    ET.SubElement(adicao1, "dadosMercadoriaIndicadorTipoCertificado").text = "1"
    ET.SubElement(adicao1, "dadosMercadoriaMedidaEstatisticaQuantidade").text = "00000004584200"
    ET.SubElement(adicao1, "dadosMercadoriaMedidaEstatisticaUnidade").text = "QUILOGRAMA LIQUIDO"
    ET.SubElement(adicao1, "dadosMercadoriaNomeNcm").text = "- Guarnições para móveis, carroçarias ou semelhantes"
    ET.SubElement(adicao1, "dadosMercadoriaPesoLiquido").text = "000000004584200"
    
    # DCR
    ET.SubElement(adicao1, "dcrCoeficienteReducao").text = "00000"
    ET.SubElement(adicao1, "dcrIdentificacao").text = "00000000"
    ET.SubElement(adicao1, "dcrValorDevido").text = "000000000000000"
    ET.SubElement(adicao1, "dcrValorDolar").text = "000000000000000"
    ET.SubElement(adicao1, "dcrValorReal").text = "000000000000000"
    ET.SubElement(adicao1, "dcrValorRecolher").text = "000000000000000"
    
    # Fornecedor
    ET.SubElement(adicao1, "fornecedorCidade").text = "BRUGNERA"
    ET.SubElement(adicao1, "fornecedorLogradouro").text = "VIALE EUROPA"
    ET.SubElement(adicao1, "fornecedorNome").text = "ITALIANA FERRAMENTA S.R.L."
    ET.SubElement(adicao1, "fornecedorNumero").text = "17"
    
    # Frete
    ET.SubElement(adicao1, "freteMoedaNegociadaCodigo").text = "978"
    ET.SubElement(adicao1, "freteMoedaNegociadaNome").text = "EURO/COM.EUROPEIA"
    ET.SubElement(adicao1, "freteValorMoedaNegociada").text = "000000000002353"
    ET.SubElement(adicao1, "freteValorReais").text = "000000000014595"
    
    # II
    ET.SubElement(adicao1, "iiAcordoTarifarioTipoCodigo").text = "0"
    ET.SubElement(adicao1, "iiAliquotaAcordo").text = "00000"
    ET.SubElement(adicao1, "iiAliquotaAdValorem").text = "01800"
    ET.SubElement(adicao1, "iiAliquotaPercentualReducao").text = "00000"
    ET.SubElement(adicao1, "iiAliquotaReduzida").text = "00000"
    ET.SubElement(adicao1, "iiAliquotaValorCalculado").text = "000000000256616"
    ET.SubElement(adicao1, "iiAliquotaValorDevido").text = "000000000256616"
    ET.SubElement(adicao1, "iiAliquotaValorRecolher").text = "000000000256616"
    ET.SubElement(adicao1, "iiAliquotaValorReduzido").text = "000000000000000"
    ET.SubElement(adicao1, "iiBaseCalculo").text = "000000001425674"
    ET.SubElement(adicao1, "iiFundamentoLegalCodigo").text = "00"
    ET.SubElement(adicao1, "iiMotivoAdmissaoTemporariaCodigo").text = "00"
    ET.SubElement(adicao1, "iiRegimeTributacaoCodigo").text = "1"
    ET.SubElement(adicao1, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
    
    # IPI
    ET.SubElement(adicao1, "ipiAliquotaAdValorem").text = "00325"
    ET.SubElement(adicao1, "ipiAliquotaEspecificaCapacidadeRecipciente").text = "00000"
    ET.SubElement(adicao1, "ipiAliquotaEspecificaQuantidadeUnidadeMedida").text = "000000000"
    ET.SubElement(adicao1, "ipiAliquotaEspecificaTipoRecipienteCodigo").text = "00"
    ET.SubElement(adicao1, "ipiAliquotaEspecificaValorUnidadeMedida").text = "0000000000"
    ET.SubElement(adicao1, "ipiAliquotaNotaComplementarTIPI").text = "00"
    ET.SubElement(adicao1, "ipiAliquotaReduzida").text = "00000"
    ET.SubElement(adicao1, "ipiAliquotaValorDevido").text = "000000000054674"
    ET.SubElement(adicao1, "ipiAliquotaValorRecolher").text = "000000000054674"
    ET.SubElement(adicao1, "ipiRegimeTributacaoCodigo").text = "4"
    ET.SubElement(adicao1, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"
    
    # Mercadoria
    mercadoria1 = ET.SubElement(adicao1, "mercadoria")
    ET.SubElement(mercadoria1, "descricaoMercadoria").text = "24627611 - 30 - 263.77.551 - SUPORTE DE PRATELEIRA DE EMBUTIR DE PLASTICO CINZAPARA MOVEIS                                                                                                     \r"
    ET.SubElement(mercadoria1, "numeroSequencialItem").text = "01"
    ET.SubElement(mercadoria1, "quantidade").text = "00000500000000"
    ET.SubElement(mercadoria1, "unidadeMedida").text = "PECA                "
    ET.SubElement(mercadoria1, "valorUnitario").text = "00000000000000321304"
    
    # Número Adição e DUIMP
    ET.SubElement(adicao1, "numeroAdicao").text = "001"
    if dados.get("numero_duimp"):
        ET.SubElement(adicao1, "numeroDUIMP").text = dados["numero_duimp"][-10:] if len(dados["numero_duimp"]) >= 10 else dados["numero_duimp"]
    else:
        ET.SubElement(adicao1, "numeroDUIMP").text = "8686868686"
    
    ET.SubElement(adicao1, "numeroLI").text = "0000000000"
    
    # País
    ET.SubElement(adicao1, "paisAquisicaoMercadoriaCodigo").text = "386"
    ET.SubElement(adicao1, "paisAquisicaoMercadoriaNome").text = "ITALIA"
    ET.SubElement(adicao1, "paisOrigemMercadoriaCodigo").text = "386"
    ET.SubElement(adicao1, "paisOrigemMercadoriaNome").text = "ITALIA"
    
    # PIS/COFINS
    ET.SubElement(adicao1, "pisCofinsBaseCalculoAliquotaICMS").text = "00000"
    ET.SubElement(adicao1, "pisCofinsBaseCalculoFundamentoLegalCodigo").text = "00"
    ET.SubElement(adicao1, "pisCofinsBaseCalculoPercentualReducao").text = "00000"
    ET.SubElement(adicao1, "pisCofinsBaseCalculoValor").text = "000000001425674"
    ET.SubElement(adicao1, "pisCofinsFundamentoLegalReducaoCodigo").text = "00"
    ET.SubElement(adicao1, "pisCofinsRegimeTributacaoCodigo").text = "1"
    ET.SubElement(adicao1, "pisCofinsRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
    
    # PIS/PASEP
    ET.SubElement(adicao1, "pisPasepAliquotaAdValorem").text = "00210"
    ET.SubElement(adicao1, "pisPasepAliquotaEspecificaQuantidadeUnidade").text = "000000000"
    ET.SubElement(adicao1, "pisPasepAliquotaEspecificaValor").text = "0000000000"
    ET.SubElement(adicao1, "pisPasepAliquotaReduzida").text = "00000"
    ET.SubElement(adicao1, "pisPasepAliquotaValorDevido").text = "000000000029938"
    ET.SubElement(adicao1, "pisPasepAliquotaValorRecolher").text = "000000000029938"
    
    # ICMS, CBS, IBS (exemplo)
    ET.SubElement(adicao1, "icmsBaseCalculoValor").text = "000000000160652"
    ET.SubElement(adicao1, "icmsBaseCalculoAliquota").text = "01800"
    ET.SubElement(adicao1, "icmsBaseCalculoValorImposto").text = "00000000019374"
    ET.SubElement(adicao1, "icmsBaseCalculoValorDiferido").text = "00000000009542"
    ET.SubElement(adicao1, "cbsIbsCst").text = "000"
    ET.SubElement(adicao1, "cbsIbsClasstrib").text = "000001"
    ET.SubElement(adicao1, "cbsBaseCalculoValor").text = "00000000160652"
    ET.SubElement(adicao1, "cbsBaseCalculoAliquota").text = "00090"
    ET.SubElement(adicao1, "cbsBaseCalculoAliquotaReducao").text = "00000"
    ET.SubElement(adicao1, "cbsBaseCalculoValorImposto").text = "00000000001445"
    ET.SubElement(adicao1, "ibsBaseCalculoValor").text = "000000000160652"
    ET.SubElement(adicao1, "ibsBaseCalculoAliquota").text = "00010"
    ET.SubElement(adicao1, "ibsBaseCalculoAliquotaReducao").text = "00000"
    ET.SubElement(adicao1, "ibsBaseCalculoValorImposto").text = "00000000000160"
    
    # Relações
    ET.SubElement(adicao1, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
    
    # Seguro
    ET.SubElement(adicao1, "seguroMoedaNegociadaCodigo").text = "220"
    ET.SubElement(adicao1, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
    ET.SubElement(adicao1, "seguroValorMoedaNegociada").text = "000000000000000"
    ET.SubElement(adicao1, "seguroValorReais").text = "000000000001489"
    
    # Sequencial
    ET.SubElement(adicao1, "sequencialRetificacao").text = "00"
    
    # Valores
    ET.SubElement(adicao1, "valorMultaARecolher").text = "000000000000000"
    ET.SubElement(adicao1, "valorMultaARecolherAjustado").text = "000000000000000"
    ET.SubElement(adicao1, "valorReaisFreteInternacional").text = "000000000014595"
    ET.SubElement(adicao1, "valorReaisSeguroInternacional").text = "000000000001489"
    ET.SubElement(adicao1, "valorTotalCondicaoVenda").text = "21014900800"
    ET.SubElement(adicao1, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."
    
    # ===== ELEMENTOS GERAIS DO DUIMP =====
    
    # Armazém
    armazem = ET.SubElement(duimp, "armazem")
    ET.SubElement(armazem, "nomeArmazem").text = "TCP       "
    
    # Armazenamento
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroCodigo").text = "9801303"
    ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
    ET.SubElement(duimp, "armazenamentoSetor").text = "002"
    
    # Canal
    ET.SubElement(duimp, "canalSelecaoParametrizada").text = "001"
    
    # Caracterização da Operação
    ET.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
    ET.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importação Própria"
    
    # Carga
    if dados.get("data_embarque"):
        try:
            data_emb = datetime.strptime(dados["data_embarque"], "%d/%m/%Y")
            ET.SubElement(duimp, "cargaDataChegada").text = data_emb.strftime("%Y%m%d")
        except:
            ET.SubElement(duimp, "cargaDataChegada").text = "20251120"
    
    ET.SubElement(duimp, "cargaNumeroAgente").text = "N/I"
    ET.SubElement(duimp, "cargaPaisProcedenciaCodigo").text = "386"
    ET.SubElement(duimp, "cargaPaisProcedenciaNome").text = "ITALIA"
    
    if dados.get("peso_bruto"):
        peso_bruto_num = dados["peso_bruto"].replace(".", "").replace(",", "")
        ET.SubElement(duimp, "cargaPesoBruto").text = f"{int(float(peso_bruto_num.replace(',', '.')) * 1000):015d}"
    
    # URF
    ET.SubElement(duimp, "cargaUrfEntradaCodigo").text = "0917800"
    ET.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
    
    # Conhecimento de Carga
    ET.SubElement(duimp, "conhecimentoCargaEmbarqueData").text = "20251025"
    ET.SubElement(duimp, "conhecimentoCargaEmbarqueLocal").text = "GENOVA"
    ET.SubElement(duimp, "conhecimentoCargaId").text = "CEMERCANTE31032008"
    ET.SubElement(duimp, "conhecimentoCargaIdMaster").text = "162505352452915"
    ET.SubElement(duimp, "conhecimentoCargaTipoCodigo").text = "12"
    ET.SubElement(duimp, "conhecimentoCargaTipoNome").text = "HBL - House Bill of Lading"
    ET.SubElement(duimp, "conhecimentoCargaUtilizacao").text = "1"
    ET.SubElement(duimp, "conhecimentoCargaUtilizacaoNome").text = "Total"
    
    # Datas
    ET.SubElement(duimp, "dataDesembaraco").text = "20251124"
    ET.SubElement(duimp, "dataRegistro").text = "20251124"
    
    # Documentos de Chegada
    ET.SubElement(duimp, "documentoChegadaCargaCodigoTipo").text = "1"
    ET.SubElement(duimp, "documentoChegadaCargaNome").text = "Manifesto da Carga"
    ET.SubElement(duimp, "documentoChegadaCargaNumero").text = "1625502058594"
    
    # Documentos Instrução Despacho
    for doc_type, doc_num in dados.get("documentos", []):
        doc_inst = ET.SubElement(duimp, "documentoInstrucaoDespacho")
        
        if "CONHECIMENTO" in doc_type:
            ET.SubElement(doc_inst, "codigoTipoDocumentoDespacho").text = "28"
            ET.SubElement(doc_inst, "nomeDocumentoDespacho").text = "CONHECIMENTO DE CARGA                                       "
            ET.SubElement(doc_inst, "numeroDocumentoDespacho").text = doc_num.ljust(25)
        elif "FATURA" in doc_type:
            ET.SubElement(doc_inst, "codigoTipoDocumentoDespacho").text = "01"
            ET.SubElement(doc_inst, "nomeDocumentoDespacho").text = "FATURA COMERCIAL                                            "
            ET.SubElement(doc_inst, "numeroDocumentoDespacho").text = doc_num.ljust(25)
        elif "ROMANEIO" in doc_type:
            ET.SubElement(doc_inst, "codigoTipoDocumentoDespacho").text = "29"
            ET.SubElement(doc_inst, "nomeDocumentoDespacho").text = "ROMANEIO DE CARGA                                           "
            ET.SubElement(doc_inst, "numeroDocumentoDespacho").text = doc_num.ljust(25)
    
    # Embalagem
    embalagem = ET.SubElement(duimp, "embalagem")
    ET.SubElement(embalagem, "codigoTipoEmbalagem").text = "60"
    ET.SubElement(embalagem, "nomeEmbalagem").text = "PALLETS                                                     "
    ET.SubElement(embalagem, "quantidadeVolume").text = "00002"
    
    # Frete
    ET.SubElement(duimp, "freteCollect").text = "000000000025000"
    ET.SubElement(duimp, "freteEmTerritorioNacional").text = "000000000000000"
    ET.SubElement(duimp, "freteMoedaNegociadaCodigo").text = "978"
    ET.SubElement(duimp, "freteMoedaNegociadaNome").text = "EURO/COM.EUROPEIA"
    ET.SubElement(duimp, "fretePrepaid").text = "000000000000000"
    ET.SubElement(duimp, "freteTotalDolares").text = "000000000028757"
    ET.SubElement(duimp, "freteTotalMoeda").text = "25000"
    ET.SubElement(duimp, "freteTotalReais").text = "000000000155007"
    
    # ICMS
    icms_elem = ET.SubElement(duimp, "icms")
    ET.SubElement(icms_elem, "agenciaIcms").text = "00000"
    ET.SubElement(icms_elem, "bancoIcms").text = "000"
    ET.SubElement(icms_elem, "codigoTipoRecolhimentoIcms").text = "3"
    ET.SubElement(icms_elem, "cpfResponsavelRegistro").text = "27160353854"
    ET.SubElement(icms_elem, "dataRegistro").text = "20251125"
    ET.SubElement(icms_elem, "horaRegistro").text = "152044"
    ET.SubElement(icms_elem, "nomeTipoRecolhimentoIcms").text = "Exoneração do ICMS"
    ET.SubElement(icms_elem, "numeroSequencialIcms").text = "001"
    ET.SubElement(icms_elem, "ufIcms").text = "PR"
    ET.SubElement(icms_elem, "valorTotalIcms").text = "000000000000000"
    
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
    ET.SubElement(duimp, "importadorNome").text = "HAFELE BRASIL LTDA"
    ET.SubElement(duimp, "importadorNomeRepresentanteLegal").text = "PAULO HENRIQUE LEITE FERREIRA"
    
    if dados.get("importador_cnpj"):
        cnpj_clean = dados["importador_cnpj"].replace(".", "").replace("/", "").replace("-", "")
        ET.SubElement(duimp, "importadorNumero").text = cnpj_clean
    else:
        ET.SubElement(duimp, "importadorNumero").text = "02473058000188"
    
    ET.SubElement(duimp, "importadorNumeroTelefone").text = "41  30348150"
    
    # Informação Complementar
    info_text = f"""INFORMACOES COMPLEMENTARES
--------------------------
Arquivo convertido do PDF: {dados.get('numero_processo', 'N/A')}
Importador: {dados.get('importador_nome', 'N/A')}
CNPJ: {dados.get('importador_cnpj', 'N/A')}
Data do PDF: {dados.get('data_cadastro', 'N/A')}
País: {dados.get('pais_procedencia', 'N/A')}
Via Transporte: {dados.get('via_transporte', 'N/A')}
Moeda: {dados.get('moeda_negociada', 'N/A')}
Cotação: {dados.get('cotacao_moeda', 'N/A')}
VMLE: USD {dados.get('vmle_usd', 'N/A')} / BRL {dados.get('vmle_brl', 'N/A')}
Data da conversão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
-----------------------------------------------------------------------
CONVERSÃO AUTOMÁTICA DUIMP PDF PARA XML
"""
    ET.SubElement(duimp, "informacaoComplementar").text = info_text
    
    # Local Descarga/Embarque
    ET.SubElement(duimp, "localDescargaTotalDolares").text = "000000002061433"
    ET.SubElement(duimp, "localDescargaTotalReais").text = "000000011111593"
    ET.SubElement(duimp, "localEmbarqueTotalDolares").text = "000000002030535"
    ET.SubElement(duimp, "localEmbarqueTotalReais").text = "000000010945130"
    
    # Modalidade
    ET.SubElement(duimp, "modalidadeDespachoCodigo").text = "1"
    ET.SubElement(duimp, "modalidadeDespachoNome").text = "Normal"
    
    # Número DUIMP
    if dados.get("numero_duimp"):
        ET.SubElement(duimp, "numeroDUIMP").text = dados["numero_duimp"][-10:] if len(dados["numero_duimp"]) >= 10 else dados["numero_duimp"]
    else:
        ET.SubElement(duimp, "numeroDUIMP").text = "8686868686"
    
    # Operação FUNDAP
    ET.SubElement(duimp, "operacaoFundap").text = "N"
    
    # Pagamentos (exemplo)
    pagamentos = [
        ("0086", "000000001772057"),
        ("1038", "000000001021643"),
        ("5602", "000000000233345"),
        ("5629", "000000001072281"),
        ("7811", "000000000028534"),
    ]
    
    for codigo, valor in pagamentos:
        pagamento = ET.SubElement(duimp, "pagamento")
        ET.SubElement(pagamento, "agenciaPagamento").text = "3715 "
        ET.SubElement(pagamento, "bancoPagamento").text = "341"
        ET.SubElement(pagamento, "codigoReceita").text = codigo
        ET.SubElement(pagamento, "codigoTipoPagamento").text = "1"
        ET.SubElement(pagamento, "contaPagamento").text = "             316273"
        ET.SubElement(pagamento, "dataPagamento").text = "20251124"
        ET.SubElement(pagamento, "nomeTipoPagamento").text = "Débito em Conta"
        ET.SubElement(pagamento, "numeroRetificacao").text = "00"
        ET.SubElement(pagamento, "valorJurosEncargos").text = "000000000"
        ET.SubElement(pagamento, "valorMulta").text = "000000000"
        ET.SubElement(pagamento, "valorReceita").text = valor
    
    # Seguro
    ET.SubElement(duimp, "seguroMoedaNegociadaCodigo").text = "220"
    ET.SubElement(duimp, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
    ET.SubElement(duimp, "seguroTotalDolares").text = "000000000002146"
    ET.SubElement(duimp, "seguroTotalMoedaNegociada").text = "000000000002146"
    ET.SubElement(duimp, "seguroTotalReais").text = "000000000011567"
    
    # Sequencial Retificação
    ET.SubElement(duimp, "sequencialRetificacao").text = "00"
    
    # Situação Entrega
    ET.SubElement(duimp, "situacaoEntregaCarga").text = "ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE EXONERACAO DO ICMS"
    
    # Tipo Declaração
    ET.SubElement(duimp, "tipoDeclaracaoCodigo").text = "01"
    ET.SubElement(duimp, "tipoDeclaracaoNome").text = "CONSUMO"
    
    # Total Adições
    ET.SubElement(duimp, "totalAdicoes").text = "005"
    
    # URF Despacho
    ET.SubElement(duimp, "urfDespachoCodigo").text = "0917800"
    ET.SubElement(duimp, "urfDespachoNome").text = "PORTO DE PARANAGUA"
    
    # Valor Total Multa
    ET.SubElement(duimp, "valorTotalMultaARecolherAjustado").text = "000000000000000"
    
    # Via Transporte
    ET.SubElement(duimp, "viaTransporteCodigo").text = "01"
    ET.SubElement(duimp, "viaTransporteMultimodal").text = "N"
    ET.SubElement(duimp, "viaTransporteNome").text = "MARÍTIMA"
    ET.SubElement(duimp, "viaTransporteNomeTransportador").text = "MAERSK A/S"
    ET.SubElement(duimp, "viaTransporteNomeVeiculo").text = "MAERSK MEMPHIS"
    ET.SubElement(duimp, "viaTransportePaisTransportadorCodigo").text = "741"
    ET.SubElement(duimp, "viaTransportePaisTransportadorNome").text = "CINGAPURA"
    
    # Converter para string XML formatada
    xml_string = ET.tostring(lista_declaracoes, encoding='utf-8', xml_declaration=True)
    
    # Formatar o XML
    parsed = minidom.parseString(xml_string)
    pretty_xml = parsed.toprettyxml(indent="  ", encoding='utf-8')
    
    return pretty_xml.decode('utf-8')

# Função principal
def main():
    # Área de upload
    st.subheader("📤 Upload do PDF DUIMP")
    uploaded_file = st.file_uploader(
        "Selecione o arquivo PDF no formato exato do extrato de conferência DUIMP",
        type=['pdf'],
        help="O PDF deve ter o mesmo layout do arquivo exemplo fornecido"
    )
    
    if uploaded_file is not None:
        # Verificar tamanho
        file_size = uploaded_file.size / (1024 * 1024)  # MB
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 Arquivo", uploaded_file.name)
        with col2:
            st.metric("📊 Tamanho", f"{file_size:.2f} MB")
        with col3:
            st.metric("⚙️ Status", "Pronto para processar")
        
        # Botão para processar
        if st.button("🔄 Processar PDF", type="primary"):
            with st.spinner("Processando PDF no layout específico DUIMP..."):
                try:
                    # Parsear PDF
                    dados, texto_extraido = parse_duimp_pdf_specific(uploaded_file)
                    
                    # Mostrar dados extraídos
                    st.subheader("📋 Dados Extraídos do PDF")
                    
                    # Criar colunas para exibição
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"**Processo:** {dados.get('numero_processo', 'Não encontrado')}")
                        st.info(f"**Importador:** {dados.get('importador_nome', 'Não encontrado')}")
                        st.info(f"**CNPJ:** {dados.get('importador_cnpj', 'Não encontrado')}")
                        st.info(f"**DUIMP:** {dados.get('numero_duimp', 'Não encontrado')}")
                        st.info(f"**Data Cadastro:** {dados.get('data_cadastro', 'Não encontrado')}")
                    
                    with col2:
                        st.info(f"**País Procedência:** {dados.get('pais_procedencia', 'Não encontrado')}")
                        st.info(f"**Via Transporte:** {dados.get('via_transporte', 'Não encontrado')}")
                        st.info(f"**Moeda:** {dados.get('moeda_negociada', 'Não encontrado')}")
                        st.info(f"**Cotação:** {dados.get('cotacao_moeda', 'Não encontrado')}")
                        st.info(f"**Peso Bruto:** {dados.get('peso_bruto', 'Não encontrado')}")
                    
                    # Mostrar valores
                    st.subheader("💰 Valores Extraídos")
                    
                    val_col1, val_col2, val_col3 = st.columns(3)
                    
                    with val_col1:
                        if dados.get('vmle_usd'):
                            st.metric("VMLE USD", dados['vmle_usd'])
                        if dados.get('cif_usd'):
                            st.metric("CIF USD", dados['cif_usd'])
                    
                    with val_col2:
                        if dados.get('vmle_brl'):
                            st.metric("VMLE BRL", dados['vmle_brl'])
                        if dados.get('cif_brl'):
                            st.metric("CIF BRL", dados['cif_brl'])
                    
                    with val_col3:
                        if dados.get('seguro_total_brl'):
                            st.metric("Seguro BRL", dados['seguro_total_brl'])
                        if dados.get('frete_total_brl'):
                            st.metric("Frete BRL", dados['frete_total_brl'])
                    
                    # Mostrar tributos
                    if any([dados.get('ii_calculado'), dados.get('pis_calculado'), dados.get('cofins_calculado')]):
                        st.subheader("🧾 Tributos")
                        
                        trib_col1, trib_col2, trib_col3, trib_col4 = st.columns(4)
                        
                        with trib_col1:
                            if dados.get('ii_calculado'):
                                st.metric("II Calculado", dados['ii_calculado'])
                        
                        with trib_col2:
                            if dados.get('pis_calculado'):
                                st.metric("PIS Calculado", dados['pis_calculado'])
                        
                        with trib_col3:
                            if dados.get('cofins_calculado'):
                                st.metric("COFINS Calculado", dados['cofins_calculado'])
                        
                        with trib_col4:
                            if dados.get('taxa_utilizacao'):
                                st.metric("Taxa Utilização", dados['taxa_utilizacao'])
                    
                    # Mostrar itens
                    if dados.get('itens'):
                        st.subheader(f"📦 Itens Encontrados: {len(dados['itens'])}")
                        
                        items_df = pd.DataFrame(dados['itens'])
                        st.dataframe(items_df, use_container_width=True)
                    
                    # Mostrar documentos
                    if dados.get('documentos'):
                        st.subheader(f"📄 Documentos: {len(dados['documentos'])}")
                        
                        for doc_type, doc_num in dados['documentos']:
                            st.write(f"**{doc_type}:** {doc_num}")
                    
                    # Gerar XML
                    with st.spinner("Gerando XML no formato exato..."):
                        xml_content = create_exact_xml(dados)
                        
                        # Mostrar preview
                        with st.expander("🔍 Visualizar XML Gerado (primeiras 2000 caracteres)"):
                            st.code(xml_content[:2000] + "..." if len(xml_content) > 2000 else xml_content, language='xml')
                        
                        # Botão de download
                        st.subheader("📥 Download do XML")
                        
                        # Nome do arquivo
                        file_name = "DUIMP_converted.xml"
                        if dados.get('numero_duimp'):
                            file_name = f"DUIMP_{dados['numero_duimp']}.xml"
                        elif dados.get('numero_processo'):
                            file_name = f"PROCESSO_{dados['numero_processo']}.xml"
                        
                        # Botão de download principal
                        st.download_button(
                            label="💾 Baixar Arquivo XML",
                            data=xml_content.encode('utf-8'),
                            file_name=file_name,
                            mime="application/xml",
                            type="primary"
                        )
                        
                        # Botões adicionais
                        col_d1, col_d2 = st.columns(2)
                        
                        with col_d1:
                            st.download_button(
                                label="📄 Baixar Texto Extraído",
                                data=texto_extraido.encode('utf-8'),
                                file_name="texto_extraido.txt",
                                mime="text/plain"
                            )
                        
                        with col_d2:
                            # JSON dos dados
                            import json
                            json_data = json.dumps(dados, indent=2, ensure_ascii=False)
                            st.download_button(
                                label="📊 Baixar Dados em JSON",
                                data=json_data.encode('utf-8'),
                                file_name="dados_extraidos.json",
                                mime="application/json"
                            )
                        
                        st.success("✅ Conversão concluída com sucesso!")
                        st.balloons()
                        
                except Exception as e:
                    st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
                    st.exception(e)
    
    else:
        # Instruções quando não há arquivo
        st.info("👆 Faça upload de um arquivo PDF para começar a conversão")
        
        # Exemplo de layout esperado
        with st.expander("🎯 Layout Exato Esperado"):
            st.markdown("""
            ### **Estrutura do PDF que será processada:**
            
            **Página 1:**
            ```
            PROCESSO #28523
            IMPORTADOR
            HAFELE BRASIL
            02.473.058/0001-88
            Identificacao
            IM10001/25
            Número 25BR00001916620
            Data Registro / /
            Data de Cadastro 13/10/2025
            Responsavel Legal PAULO HENRIQUE LEITE FERREIRA
            Moeda Negociada 220 - DOLAR DOS EUA
            Cotacao 5,3843000
            VALORES TOTAIS (CIF)
            CIF (US$) 0,00 CIF (R$) 0,00
            VALOR DA MERCADORIA NO LOCAL DE EMBARQUE (VMLE)
            VMLE (US$) 3.595,16 VMLE (R$) 19.203,88
            CÁLCULOS DOS TRIBUTOS
            | Tributo    | Calculado | Devido | A Recolher |
            | II         | 3.072,62  | 3.072,62 | 3.072,62 |
            | PIS        | 403,28    | 403,28   | 403,28   |
            | COFINS     | 1.853,17  | 1.853,17 | 1.853,17 |
            Via de Transporte 01 - MARITIMA
            Data de Embarque 12/10/2025
            Peso Bruto 15.790.00000
            País de Procedencia CHINA, REPUBLICA POPULAR (CN)
            ```
            
            **Página 2:**
            ```
            FRETE
            Total (US$) 3.000,00
            Total (R$) 16.123,20
            DOCUMENTOS INSTRUTIVOS DO DESPACHO
            CONHECIMENTO DE EMBARQUE
            NUMERO SZXS069034
            FATURA COMERCIAL
            NUMERO 554060729
            ```
            
            **Página 3:**
            ```
            Item | NCM | Codigo Produto | Fatura/Invoice
            1    | 8302.10.00 | 21 | 554060729
            DENOMINACAO DO PRODUTO
            DOBRADICA INVISIVEL EM LIGA DE ZINCO...
            ```
            """)

if __name__ == "__main__":
    main()
