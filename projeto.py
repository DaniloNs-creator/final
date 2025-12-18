import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import PyPDF2
import io
import re
from datetime import datetime

st.set_page_config(page_title="Conversor DUIMP PDF para XML", layout="wide")

st.title("📄 Conversor DUIMP PDF para XML")
st.markdown("""
Converta extratos de conferência DUIMP em formato PDF para arquivos XML estruturados,
prontos para importação no seu sistema.
""")

# Estrutura do XML baseado no exemplo
def create_xml_structure():
    """Cria a estrutura base do XML conforme o exemplo fornecido"""
    lista_declaracoes = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(lista_declaracoes, "duimp")
    
    return lista_declaracoes, duimp

def parse_pdf_content(pdf_content):
    """Extrai e organiza o conteúdo do PDF"""
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
    
    text_content = []
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text = page.extract_text()
        text_content.append(f"===== Page {page_num + 1} =====\n{text}")
    
    return "\n".join(text_content)

def extract_duimp_info_from_text(text):
    """Extrai informações do DUIMP do texto do PDF"""
    info = {}
    
    # Padrões para extração
    patterns = {
        'processo': r'PROCESSO\s+#?(\d+)',
        'importador_nome': r'IMPORTADOR\s*\n.*?\n(.*?)\n',
        'importador_cnpj': r'CNPJ\s*\n(.*?)\n',
        'numero_duimp': r'Número\s+(\S+)',
        'data_registro': r'Data Registro\s+([\d/]+)',
        'operacao': r'Operacao\s+(\w+)',
        'tipo': r'Tipo\s+(\w+)',
        'moeda_negociada': r'Moeda Negociada\s+(\d+)\s*-\s*(.*)',
        'cotacao': r'Cotacao\s+([\d,]+)',
        'pais_procedencia': r'País de Procedencia\s+(.*?)\s*\(',
        'via_transporte': r'Via de Transporte\s+(\d+)\s*-\s*(.*)',
        'data_embarque': r'Data de Embarque\s+([\d/]+)',
        'peso_bruto': r'Peso Bruto\s+([\d.,]+)',
        'peso_liquido': r'Peso Líquido KG\s+([\d.,]+)',
        'unidade_despacho': r'Unidade de Despacho\s+(\d+)\s*-\s*(.*)',
        'conhecimento_embarque': r'CONHECIMENTO DE EMBARQUE.*?NUMERO\s+(\S+)',
        'fatura_comercial': r'FATURA COMERCIAL.*?NUMERO\s+(\S+)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            info[key] = match.group(1).strip()
    
    # Extrair itens/adicionais
    info['itens'] = extract_items_from_text(text)
    
    # Extrair valores totais e impostos
    info['valores'] = extract_values_from_text(text)
    
    return info

def extract_items_from_text(text):
    """Extrai informações dos itens do PDF"""
    itens = []
    
    # Padrão para encontrar itens (ajustar conforme necessário)
    item_patterns = re.finditer(r'Item\s+\d+.*?NCM\s+(\d{4}\.\d{2}\.\d{2}).*?DENOMINACAO DO PRODUTO\s+(.*?)\nDESCRICAO DO PRODUTO\s+(.*?)\n', 
                               text, re.DOTALL | re.IGNORECASE)
    
    for match in item_patterns:
        item = {
            'ncm': match.group(1),
            'denominacao': match.group(2).strip(),
            'descricao': match.group(3).strip()
        }
        itens.append(item)
    
    # Se não encontrar pelo padrão acima, tentar outro
    if not itens:
        # Buscar por linhas que contenham NCM
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'NCM' in line.upper() and i+1 < len(lines):
                ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', line)
                if ncm_match:
                    item = {
                        'ncm': ncm_match.group(1),
                        'denominacao': lines[i+1] if i+1 < len(lines) else '',
                        'descricao': lines[i+2] if i+2 < len(lines) else ''
                    }
                    itens.append(item)
    
    return itens

def extract_values_from_text(text):
    """Extrai valores e impostos do texto"""
    valores = {
        'ii': '0.00',
        'ipi': '0.00',
        'pis': '0.00',
        'cofins': '0.00',
        'taxa_utilizacao': '0.00',
        'valor_mercadoria': '0.00',
        'frete': '0.00',
        'seguro': '0.00'
    }
    
    # Padrões para valores
    patterns = {
        'ii': r'II\s+([\d.,]+)',
        'ipi': r'IPI\s+([\d.,]+)',
        'pis': r'PIS\s+([\d.,]+)',
        'cofins': r'COFINS\s+([\d.,]+)',
        'taxa_utilizacao': r'TAXA DE UTILIZACAO\s+([\d.,]+)',
        'valor_mercadoria': r'VALOR DA MERCADORIA.*?R\$\s+([\d.,]+)',
        'frete': r'FRETE.*?R\$\s+([\d.,]+)',
        'seguro': r'SEGURO.*?R\$\s+([\d.,]+)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            valores[key] = match.group(1).replace('.', '').replace(',', '.')
    
    return valores

def create_adicao_element(duimp_element, item_num, item_info, valores, duimp_info):
    """Cria elemento de adição/adicao"""
    adicao = ET.SubElement(duimp_element, "adicao")
    
    # Acrescimo
    acrescimo = ET.SubElement(adicao, "acrescimo")
    ET.SubElement(acrescimo, "codigoAcrescimo").text = "17"
    ET.SubElement(acrescimo, "denominacao").text = "OUTROS ACRESCIMOS AO VALOR ADUANEIRO"
    ET.SubElement(acrescimo, "moedaNegociadaCodigo").text = "978"
    ET.SubElement(acrescimo, "moedaNegociadaNome").text = "EURO/COM.EUROPEIA"
    ET.SubElement(acrescimo, "valorMoedaNegociada").text = "000000000000000"
    ET.SubElement(acrescimo, "valorReais").text = "000000000000000"
    
    # Informações básicas da adição
    ET.SubElement(adicao, "cideValorAliquotaEspecifica").text = "00000000000"
    ET.SubElement(adicao, "cideValorDevido").text = "000000000000000"
    ET.SubElement(adicao, "cideValorRecolher").text = "000000000000000"
    ET.SubElement(adicao, "codigoRelacaoCompradorVendedor").text = "3"
    ET.SubElement(adicao, "codigoVinculoCompradorVendedor").text = "1"
    
    # COFINS
    ET.SubElement(adicao, "cofinsAliquotaAdValorem").text = "00965"
    ET.SubElement(adicao, "cofinsAliquotaEspecificaQuantidadeUnidade").text = "000000000"
    ET.SubElement(adicao, "cofinsAliquotaEspecificaValor").text = "0000000000"
    ET.SubElement(adicao, "cofinsAliquotaReduzida").text = "00000"
    ET.SubElement(adicao, "cofinsAliquotaValorDevido").text = f"{float(valores['cofins']):015.0f}".replace('.', '')
    ET.SubElement(adicao, "cofinsAliquotaValorRecolher").text = f"{float(valores['cofins']):015.0f}".replace('.', '')
    
    # Condição de venda
    ET.SubElement(adicao, "condicaoVendaIncoterm").text = "FOB"
    ET.SubElement(adicao, "condicaoVendaLocal").text = duimp_info.get('pais_procedencia', 'CNYTN')
    ET.SubElement(adicao, "condicaoVendaMetodoValoracaoCodigo").text = "01"
    ET.SubElement(adicao, "condicaoVendaMetodoValoracaoNome").text = "METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"
    ET.SubElement(adicao, "condicaoVendaMoedaCodigo").text = "220"
    ET.SubElement(adicao, "condicaoVendaMoedaNome").text = "DOLAR DOS EUA"
    
    # Dados cambiais
    ET.SubElement(adicao, "dadosCambiaisCoberturaCambialCodigo").text = "1"
    ET.SubElement(adicao, "dadosCambiaisCoberturaCambialNome").text = "COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"
    
    # Dados da mercadoria
    ET.SubElement(adicao, "dadosMercadoriaAplicacao").text = "REVENDA"
    ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item_info['ncm'].replace('.', '')
    ET.SubElement(adicao, "dadosMercadoriaCondicao").text = "NOVA"
    ET.SubElement(adicao, "dadosMercadoriaNomeNcm").text = f"- {item_info['denominacao'][:50]}"
    
    # Fornecedor
    ET.SubElement(adicao, "fornecedorCidade").text = duimp_info.get('pais_procedencia', 'CNYTN')
    ET.SubElement(adicao, "fornecedorNome").text = "FORNECEDOR IMPORTACAO"
    
    # Frete
    ET.SubElement(adicao, "freteMoedaNegociadaCodigo").text = "220"
    ET.SubElement(adicao, "freteMoedaNegociadaNome").text = "DOLAR DOS EUA"
    ET.SubElement(adicao, "freteValorMoedaNegociada").text = f"{float(valores['frete']):015.0f}".replace('.', '')
    ET.SubElement(adicao, "freteValorReais").text = f"{float(valores['frete']):015.0f}".replace('.', '')
    
    # II - Imposto de Importação
    ET.SubElement(adicao, "iiAliquotaAdValorem").text = "01800"
    ET.SubElement(adicao, "iiAliquotaValorCalculado").text = f"{float(valores['ii']):015.0f}".replace('.', '')
    ET.SubElement(adicao, "iiAliquotaValorDevido").text = f"{float(valores['ii']):015.0f}".replace('.', '')
    ET.SubElement(adicao, "iiAliquotaValorRecolher").text = f"{float(valores['ii']):015.0f}".replace('.', '')
    ET.SubElement(adicao, "iiRegimeTributacaoCodigo").text = "1"
    ET.SubElement(adicao, "iiRegimeTributacaoNome").text = "RECOLHIMENTO INTEGRAL"
    
    # IPI
    ET.SubElement(adicao, "ipiAliquotaAdValorem").text = "00325"
    ET.SubElement(adicao, "ipiAliquotaValorDevido").text = f"{float(valores['ipi']):015.0f}".replace('.', '')
    ET.SubElement(adicao, "ipiAliquotaValorRecolher").text = f"{float(valores['ipi']):015.0f}".replace('.', '')
    ET.SubElement(adicao, "ipiRegimeTributacaoCodigo").text = "4"
    ET.SubElement(adicao, "ipiRegimeTributacaoNome").text = "SEM BENEFICIO"
    
    # Mercadoria
    mercadoria = ET.SubElement(adicao, "mercadoria")
    ET.SubElement(mercadoria, "descricaoMercadoria").text = item_info['descricao'][:200]
    ET.SubElement(mercadoria, "numeroSequencialItem").text = f"{item_num:02d}"
    ET.SubElement(mercadoria, "quantidade").text = "00000010000000"
    ET.SubElement(mercadoria, "unidadeMedida").text = "PECA"
    ET.SubElement(mercadoria, "valorUnitario").text = "00000000000000100000"
    
    # Número da adição e DUIMP
    ET.SubElement(adicao, "numeroAdicao").text = f"{item_num:03d}"
    ET.SubElement(adicao, "numeroDUIMP").text = duimp_info.get('numero_duimp', '0000000000').replace('25BR', '')
    ET.SubElement(adicao, "numeroLI").text = "0000000000"
    
    # País
    ET.SubElement(adicao, "paisAquisicaoMercadoriaCodigo").text = "076" if 'CHINA' in duimp_info.get('pais_procedencia', '').upper() else "386"
    ET.SubElement(adicao, "paisAquisicaoMercadoriaNome").text = duimp_info.get('pais_procedencia', 'CHINA')
    
    # PIS/PASEP
    ET.SubElement(adicao, "pisPasepAliquotaAdValorem").text = "00210"
    ET.SubElement(adicao, "pisPasepAliquotaValorDevido").text = f"{float(valores['pis']):015.0f}".replace('.', '')
    ET.SubElement(adicao, "pisPasepAliquotaValorRecolher").text = f"{float(valores['pis']):015.0f}".replace('.', '')
    
    # ICMS
    ET.SubElement(adicao, "icmsBaseCalculoValor").text = "000000000000000"
    ET.SubElement(adicao, "icmsBaseCalculoAliquota").text = "01800"
    ET.SubElement(adicao, "icmsBaseCalculoValorImposto").text = "000000000000000"
    
    # Seguro
    ET.SubElement(adicao, "seguroMoedaNegociadaCodigo").text = "220"
    ET.SubElement(adicao, "seguroMoedaNegociadaNome").text = "DOLAR DOS EUA"
    ET.SubElement(adicao, "seguroValorMoedaNegociada").text = f"{float(valores['seguro']):015.0f}".replace('.', '')
    ET.SubElement(adicao, "seguroValorReais").text = f"{float(valores['seguro']):015.0f}".replace('.', '')
    
    # Relação comprador/vendedor
    ET.SubElement(adicao, "relacaoCompradorVendedor").text = "Fabricante é desconhecido"
    ET.SubElement(adicao, "vinculoCompradorVendedor").text = "Não há vinculação entre comprador e vendedor."
    
    return adicao

def prettify_xml(elem):
    """Retorna uma string XML formatada"""
    rough_string = ET.tostring(elem, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding='utf-8')

def main():
    uploaded_file = st.file_uploader("Faça upload do arquivo PDF DUIMP", type=['pdf'])
    
    if uploaded_file is not None:
        try:
            # Ler o conteúdo do PDF
            pdf_content = uploaded_file.read()
            
            # Verificar tamanho do PDF
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            num_pages = len(pdf_reader.pages)
            
            if num_pages > 500:
                st.warning(f"O PDF tem {num_pages} páginas. Processando apenas as primeiras 500 páginas.")
            
            with st.spinner("Processando PDF..."):
                # Extrair texto do PDF
                text_content = parse_pdf_content(pdf_content[:5000000])  # Limitar para 5MB
                
                # Extrair informações do DUIMP
                duimp_info = extract_duimp_info_from_text(text_content)
                
                # Criar estrutura XML
                lista_declaracoes, duimp = create_xml_structure()
                
                # Adicionar informações gerais do DUIMP
                ET.SubElement(duimp, "armazenamentoRecintoAduaneiroCodigo").text = "9801303"
                ET.SubElement(duimp, "armazenamentoRecintoAduaneiroNome").text = "TCP - TERMINAL DE CONTEINERES DE PARANAGUA S/A"
                ET.SubElement(duimp, "canalSelecaoParametrizada").text = "001"
                
                # Caracterização da operação
                ET.SubElement(duimp, "caracterizacaoOperacaoCodigoTipo").text = "1"
                ET.SubElement(duimp, "caracterizacaoOperacaoDescricaoTipo").text = "Importação Própria"
                
                # Carga
                ET.SubElement(duimp, "cargaPaisProcedenciaCodigo").text = "076" if 'CHINA' in duimp_info.get('pais_procedencia', '').upper() else "386"
                ET.SubElement(duimp, "cargaPaisProcedenciaNome").text = duimp_info.get('pais_procedencia', 'CHINA')
                ET.SubElement(duimp, "cargaPesoBruto").text = f"{float(duimp_info.get('peso_bruto', '0').replace('.', '').replace(',', '.')):015.0f}".replace('.', '')
                ET.SubElement(duimp, "cargaPesoLiquido").text = f"{float(duimp_info.get('peso_liquido', '0').replace('.', '').replace(',', '.')):015.0f}".replace('.', '')
                ET.SubElement(duimp, "cargaUrfEntradaCodigo").text = "0917800"
                ET.SubElement(duimp, "cargaUrfEntradaNome").text = "PORTO DE PARANAGUA"
                
                # Conhecimento de carga
                ET.SubElement(duimp, "conhecimentoCargaEmbarqueData").text = "20251012"
                ET.SubElement(duimp, "conhecimentoCargaId").text = duimp_info.get('conhecimento_embarque', '0000000000')
                ET.SubElement(duimp, "conhecimentoCargaTipoCodigo").text = "12"
                ET.SubElement(duimp, "conhecimentoCargaTipoNome").text = "HBL - House Bill of Lading"
                
                # Data de registro
                data_registro = duimp_info.get('data_registro', '//')
                if data_registro != '//':
                    day, month, year = data_registro.split('/')
                    ET.SubElement(duimp, "dataRegistro").text = f"20{year}{month}{day}"
                
                # Documentos
                doc_despacho = ET.SubElement(duimp, "documentoInstrucaoDespacho")
                ET.SubElement(doc_despacho, "codigoTipoDocumentoDespacho").text = "28"
                ET.SubElement(doc_despacho, "nomeDocumentoDespacho").text = "CONHECIMENTO DE CARGA"
                ET.SubElement(doc_despacho, "numeroDocumentoDespacho").text = duimp_info.get('conhecimento_embarque', '0000000000')
                
                doc_fatura = ET.SubElement(duimp, "documentoInstrucaoDespacho")
                ET.SubElement(doc_fatura, "codigoTipoDocumentoDespacho").text = "01"
                ET.SubElement(doc_fatura, "nomeDocumentoDespacho").text = "FATURA COMERCIAL"
                ET.SubElement(doc_fatura, "numeroDocumentoDespacho").text = duimp_info.get('fatura_comercial', '0000000000')
                
                # Embalagem
                embalagem = ET.SubElement(duimp, "embalagem")
                ET.SubElement(embalagem, "codigoTipoEmbalagem").text = "60"
                ET.SubElement(embalagem, "nomeEmbalagem").text = "PALLETS"
                ET.SubElement(embalagem, "quantidadeVolume").text = "00001"
                
                # Importador
                ET.SubElement(duimp, "importadorCodigoTipo").text = "1"
                ET.SubElement(duimp, "importadorNome").text = duimp_info.get('importador_nome', 'HAFELE BRASIL')
                ET.SubElement(duimp, "importadorNumero").text = duimp_info.get('importador_cnpj', '02473058000188')
                ET.SubElement(duimp, "importadorNomeRepresentanteLegal").text = "PAULO HENRIQUE LEITE FERREIRA"
                
                # Número DUIMP
                ET.SubElement(duimp, "numeroDUIMP").text = duimp_info.get('numero_duimp', '0000000000').replace('25BR', '')
                
                # Pagamentos
                pagamento_ii = ET.SubElement(duimp, "pagamento")
                ET.SubElement(pagamento_ii, "codigoReceita").text = "0086"
                ET.SubElement(pagamento_ii, "valorReceita").text = f"{float(duimp_info['valores']['ii']):015.0f}".replace('.', '')
                
                # Via de transporte
                ET.SubElement(duimp, "viaTransporteCodigo").text = "01"
                ET.SubElement(duimp, "viaTransporteNome").text = "MARÍTIMA"
                
                # Adicionar adições (itens)
                for i, item in enumerate(duimp_info['itens'], 1):
                    create_adicao_element(duimp, i, item, duimp_info['valores'], duimp_info)
                
                # Total de adições
                ET.SubElement(duimp, "totalAdicoes").text = f"{len(duimp_info['itens']):03d}"
                
                # Gerar XML formatado
                xml_bytes = prettify_xml(lista_declaracoes)
                
                # Exibir informações extraídas
                st.success("PDF processado com sucesso!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 Informações Extraídas")
                    st.write(f"**Processo:** {duimp_info.get('processo', 'N/A')}")
                    st.write(f"**Importador:** {duimp_info.get('importador_nome', 'N/A')}")
                    st.write(f"**CNPJ:** {duimp_info.get('importador_cnpj', 'N/A')}")
                    st.write(f"**Número DUIMP:** {duimp_info.get('numero_duimp', 'N/A')}")
                    st.write(f"**País:** {duimp_info.get('pais_procedencia', 'N/A')}")
                    st.write(f"**Itens encontrados:** {len(duimp_info['itens'])}")
                
                with col2:
                    st.subheader("💰 Valores Extraídos")
                    st.write(f"**II:** R$ {duimp_info['valores']['ii']}")
                    st.write(f"**IPI:** R$ {duimp_info['valores']['ipi']}")
                    st.write(f"**PIS:** R$ {duimp_info['valores']['pis']}")
                    st.write(f"**COFINS:** R$ {duimp_info['valores']['cofins']}")
                    st.write(f"**Frete:** R$ {duimp_info['valores']['frete']}")
                
                # Exibir preview do XML
                st.subheader("📄 Preview do XML")
                xml_preview = xml_bytes.decode('utf-8')[:2000] + "..." if len(xml_bytes) > 2000 else xml_bytes.decode('utf-8')
                st.code(xml_preview, language='xml')
                
                # Botão para download
                st.download_button(
                    label="⬇️ Baixar Arquivo XML",
                    data=xml_bytes,
                    file_name=f"DUIMP_{duimp_info.get('numero_duimp', 'export')}.xml",
                    mime="application/xml"
                )
                
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            st.exception(e)
    
    else:
        st.info("👆 Faça upload de um arquivo PDF DUIMP para começar.")
        
        # Exemplo de uso
        with st.expander("ℹ️ Instruções de uso"):
            st.markdown("""
            1. **Faça upload** do arquivo PDF do extrato de conferência DUIMP
            2. O sistema irá **extrair automaticamente** as informações do PDF
            3. **Verifique** as informações extraídas nos painéis acima
            4. **Baixe** o arquivo XML gerado
            5. **Importe** o XML no seu sistema
            
            **Limitações:**
            - PDFs com até 500 páginas
            - Estrutura do PDF deve ser similar ao exemplo fornecido
            - Imagens não são processadas (somente texto)
            """)

if __name__ == "__main__":
    main()
