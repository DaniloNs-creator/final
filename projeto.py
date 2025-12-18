import streamlit as st
import pdfplumber
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
from datetime import datetime
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="Conversor DUIMP PDF para XML",
    page_icon="📄",
    layout="wide"
)

# Título do aplicativo
st.title("📄 Conversor DUIMP PDF para XML")
st.markdown("Converte extratos de DUIMP em PDF para formato XML estruturado")

# Sidebar com instruções
with st.sidebar:
    st.header("Instruções")
    st.markdown("""
    1. Faça upload do arquivo PDF do extrato DUIMP
    2. O sistema irá extrair as informações automaticamente
    3. Revise os dados extraídos
    4. Gere e baixe o arquivo XML
    5. Use o XML no seu sistema de importação
    
    **Campos Extraídos:**
    - Informações do Importador
    - Dados da DUIMP
    - Informações da Carga
    - Tributos
    - Mercadorias
    - Documentos
    """)
    
    st.divider()
    st.info("Baseado nos layouts fornecidos: M-DUIMP-8686868686.xml e extrato_de_conferencia_duimp_teste.pdf")

# Função para extrair texto do PDF
def extrair_texto_pdf(pdf_file):
    texto_completo = ""
    
    with pdfplumber.open(pdf_file) as pdf:
        for i, page in enumerate(pdf.pages):
            texto = page.extract_text()
            if texto:
                texto_completo += f"\n=== Página {i+1} ===\n{texto}\n"
    
    return texto_completo

# Função para processar o texto do PDF e extrair informações
def processar_extrato_duimp(texto_pdf):
    dados = {
        "importador": {},
        "duimp": {},
        "carga": {},
        "tributos": {},
        "mercadorias": [],
        "documentos": [],
        "pagamentos": [],
        "informacoes_complementares": ""
    }
    
    # Dividir por páginas
    paginas = texto_pdf.split("=== Página")
    
    for pagina in paginas[1:]:  # Pular o primeiro elemento vazio
        num_pagina, conteudo = pagina.split("===", 1)
        conteudo = conteudo.strip()
        
        # Extrair informações do importador (geralmente na primeira página)
        if "IMPORTADOR" in conteudo and "CNPJ" in conteudo:
            # Extrair CNPJ
            cnpj_match = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", conteudo)
            if cnpj_match:
                dados["importador"]["cnpj"] = cnpj_match.group(1)
                dados["importador"]["numero"] = cnpj_match.group(1).replace(".", "").replace("/", "").replace("-", "")
            
            # Extrair nome do importador
            nome_match = re.search(r"([A-Z\s]+)\s*\n*\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", conteudo)
            if nome_match:
                dados["importador"]["nome"] = nome_match.group(1).strip()
        
        # Extrair número da DUIMP
        duimp_match = re.search(r"N[úu]mero\s*(\d+[A-Z]?\d*)", conteudo)
        if duimp_match and not dados["duimp"].get("numero"):
            dados["duimp"]["numero"] = duimp_match.group(1)
        
        # Extrair data de registro
        data_match = re.search(r"Data Registro\s*(\d{2}/\d{2}/\d{4})", conteudo)
        if data_match:
            dados["duimp"]["data_registro"] = data_match.group(1)
        
        # Extrair tipo de operação
        if "Operacao" in conteudo:
            op_match = re.search(r"Operacao\s*([A-Z]+)", conteudo)
            if op_match:
                dados["duimp"]["tipo_operacao"] = op_match.group(1)
        
        # Extrair cotações de moeda
        if "MODAS/COTAÇÕES" in conteudo or "COTACAO" in conteudo:
            cotacao_match = re.search(r"Cotacao\s*([\d,.]+)", conteudo)
            if cotacao_match:
                dados["duimp"]["cotacao_dolar"] = cotacao_match.group(1).replace(".", "").replace(",", ".")
        
        # Extrair valores totais
        if "VALORES TOTAIS" in conteudo or "CIF" in conteudo:
            cif_match = re.search(r"CIF.*?\(R\$\)\s*([\d,.]+)", conteudo, re.IGNORECASE)
            if cif_match:
                dados["duimp"]["valor_total_cif"] = cif_match.group(1).replace(".", "").replace(",", ".")
        
        # Extrair tributos
        if "CÁLCULOS DOS TRIBUTOS" in conteudo or "TRIBUTOS" in conteudo:
            # Extrair II
            ii_match = re.search(r"II\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)", conteudo)
            if ii_match:
                dados["tributos"]["ii_devido"] = ii_match.group(3).replace(".", "").replace(",", ".")
            
            # Extrair PIS
            pis_match = re.search(r"PIS\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)", conteudo)
            if pis_match:
                dados["tributos"]["pis_devido"] = pis_match.group(3).replace(".", "").replace(",", ".")
            
            # Extrair COFINS
            cofins_match = re.search(r"COFINS\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)", conteudo)
            if cofins_match:
                dados["tributos"]["cofins_devido"] = cofins_match.group(3).replace(".", "").replace(",", ".")
        
        # Extrair dados da carga
        if "DADOS DA CARGA" in conteudo:
            # Via de transporte
            via_match = re.search(r"Via de Transporte\s*([^-]+-.*?)\n", conteudo)
            if via_match:
                dados["carga"]["via_transporte"] = via_match.group(1).strip()
            
            # Data de embarque
            embarque_match = re.search(r"Data de Embarque\s*(\d{2}/\d{2}/\d{4})", conteudo)
            if embarque_match:
                dados["carga"]["data_embarque"] = embarque_match.group(1)
            
            # Peso bruto
            peso_match = re.search(r"Peso Bruto\s*([\d,.]+)", conteudo)
            if peso_match:
                dados["carga"]["peso_bruto"] = peso_match.group(1).replace(".", "").replace(",", ".")
        
        # Extrair informações de mercadorias
        if "Item" in conteudo and "NCM" in conteudo and "Fatura/Invoice" in conteudo:
            # Procurar padrão de item
            item_pattern = r"(\d+)\s+[\w\s]*?\s+(\d{4}\.\d{2}\.\d{2})\s+([\w\d\.\s]+)\s+(\d+)\s+([A-Z]+)\s+([\w\d/-]+)"
            item_matches = re.findall(item_pattern, conteudo)
            
            for match in item_matches:
                mercadoria = {
                    "item": match[0],
                    "ncm": match[1],
                    "codigo_produto": match[2].strip(),
                    "versao": match[3],
                    "condicao_venda": match[4],
                    "fatura": match[5]
                }
                dados["mercadorias"].append(mercadoria)
        
        # Extrair documentos
        if "DOCUMENTOS INSTRUTIVOS" in conteudo:
            # Conhecimento de embarque
            conhecimento_match = re.search(r"CONHECIMENTO DE EMBARQUE.*?NUMERO\s*[:]?\s*([A-Z0-9]+)", conteudo, re.IGNORECASE)
            if conhecimento_match:
                dados["documentos"].append({
                    "tipo": "CONHECIMENTO DE EMBARQUE",
                    "numero": conhecimento_match.group(1).strip()
                })
            
            # Fatura comercial
            fatura_match = re.search(r"FATURA COMERCIAL.*?NUMERO\s*[:]?\s*([\w\d/-]+)", conteudo, re.IGNORECASE)
            if fatura_match:
                dados["documentos"].append({
                    "tipo": "FATURA COMERCIAL",
                    "numero": fatura_match.group(1).strip()
                })
        
        # Extrair frete
        if "FRETE" in conteudo:
            frete_match = re.search(r"Total.*?\(R\$\)\s*([\d,.]+)", conteudo)
            if frete_match:
                dados["carga"]["frete_total_reais"] = frete_match.group(1).replace(".", "").replace(",", ".")
        
        # Extrair seguro
        if "SEGURO" in conteudo:
            seguro_match = re.search(r"Total.*?\(R\$\)\s*([\d,.]+)", conteudo)
            if seguro_match:
                dados["carga"]["seguro_total_reais"] = seguro_match.group(1).replace(".", "").replace(",", ".")
    
    return dados

# Função para criar XML no formato desejado
def criar_xml_duimp(dados):
    # Criar elemento raiz
    lista_declaracoes = ET.Element("ListaDeclaracoes")
    duimp = ET.SubElement(lista_declaracoes, "duimp")
    
    # Adicionar informações básicas da DUIMP
    if dados["duimp"].get("numero"):
        ET.SubElement(duimp, "numeroDUIMP").text = dados["duimp"]["numero"]
    
    if dados["duimp"].get("data_registro"):
        # Converter data para formato yyyymmdd
        try:
            data_obj = datetime.strptime(dados["duimp"]["data_registro"], "%d/%m/%Y")
            ET.SubElement(duimp, "dataRegistro").text = data_obj.strftime("%Y%m%d")
        except:
            ET.SubElement(duimp, "dataRegistro").text = "00000000"
    
    # Adicionar informações do importador
    if dados["importador"]:
        if dados["importador"].get("nome"):
            ET.SubElement(duimp, "importadorNome").text = dados["importador"]["nome"]
        
        if dados["importador"].get("numero"):
            ET.SubElement(duimp, "importadorNumero").text = dados["importador"]["numero"]
    
    # Adicionar dados da carga
    if dados["carga"]:
        if dados["carga"].get("via_transporte"):
            # Extrair código e nome
            via_match = re.match(r"(\d+)\s*-\s*(.+)", dados["carga"]["via_transporte"])
            if via_match:
                ET.SubElement(duimp, "viaTransporteCodigo").text = via_match.group(1).zfill(2)
                ET.SubElement(duimp, "viaTransporteNome").text = via_match.group(2).strip()
        
        if dados["carga"].get("data_embarque"):
            try:
                data_obj = datetime.strptime(dados["carga"]["data_embarque"], "%d/%m/%Y")
                ET.SubElement(duimp, "conhecimentoCargaEmbarqueData").text = data_obj.strftime("%Y%m%d")
            except:
                pass
        
        if dados["carga"].get("peso_bruto"):
            # Formatar para 15 dígitos com zeros à esquerda
            peso_int = int(float(dados["carga"]["peso_bruto"]) * 10000)
            ET.SubElement(duimp, "cargaPesoBruto").text = str(peso_int).zfill(15)
        
        if dados["carga"].get("frete_total_reais"):
            frete_int = int(float(dados["carga"]["frete_total_reais"]) * 100)
            ET.SubElement(duimp, "freteTotalReais").text = str(frete_int).zfill(15)
        
        if dados["carga"].get("seguro_total_reais"):
            seguro_int = int(float(dados["carga"]["seguro_total_reais"]) * 100)
            ET.SubElement(duimp, "seguroTotalReais").text = str(seguro_int).zfill(15)
    
    # Adicionar tributos
    if dados["tributos"]:
        # Adicionar elemento de pagamentos
        if dados["tributos"].get("ii_devido"):
            pagamento = ET.SubElement(duimp, "pagamento")
            ET.SubElement(pagamento, "codigoReceita").text = "0086"  # Código para II
            valor_int = int(float(dados["tributos"]["ii_devido"]) * 100)
            ET.SubElement(pagamento, "valorReceita").text = str(valor_int).zfill(15)
            ET.SubElement(pagamento, "dataPagamento").text = datetime.now().strftime("%Y%m%d")
        
        if dados["tributos"].get("pis_devido"):
            pagamento = ET.SubElement(duimp, "pagamento")
            ET.SubElement(pagamento, "codigoReceita").text = "5602"  # Código para PIS
            valor_int = int(float(dados["tributos"]["pis_devido"]) * 100)
            ET.SubElement(pagamento, "valorReceita").text = str(valor_int).zfill(15)
            ET.SubElement(pagamento, "dataPagamento").text = datetime.now().strftime("%Y%m%d")
        
        if dados["tributos"].get("cofins_devido"):
            pagamento = ET.SubElement(duimp, "pagamento")
            ET.SubElement(pagamento, "codigoReceita").text = "5629"  # Código para COFINS
            valor_int = int(float(dados["tributos"]["cofins_devido"]) * 100)
            ET.SubElement(pagamento, "valorReceita").text = str(valor_int).zfill(15)
            ET.SubElement(pagamento, "dataPagamento").text = datetime.now().strftime("%Y%m%d")
    
    # Adicionar adições (mercadorias)
    total_adicoes = len(dados["mercadorias"])
    if total_adicoes > 0:
        ET.SubElement(duimp, "totalAdicoes").text = str(total_adicoes).zfill(3)
        
        for i, merc in enumerate(dados["mercadorias"], 1):
            adicao = ET.SubElement(duimp, "adicao")
            ET.SubElement(adicao, "numeroAdicao").text = str(i).zfill(3)
            
            # Informações da mercadoria
            if merc.get("ncm"):
                ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = merc["ncm"].replace(".", "")
            
            # Descrição da mercadoria (simplificada)
            mercadoria_elem = ET.SubElement(adicao, "mercadoria")
            ET.SubElement(mercadoria_elem, "numeroSequencialItem").text = merc.get("item", "01").zfill(2)
            
            if merc.get("codigo_produto"):
                ET.SubElement(mercadoria_elem, "descricaoMercadoria").text = f"Código: {merc['codigo_produto']}"
            
            # Condição de venda
            if merc.get("condicao_venda"):
                ET.SubElement(adicao, "condicaoVendaIncoterm").text = merc["condicao_venda"]
    
    # Adicionar documentos
    for doc in dados["documentos"]:
        doc_elem = ET.SubElement(duimp, "documentoInstrucaoDespacho")
        
        # Mapear tipos de documentos
        tipo_map = {
            "CONHECIMENTO DE EMBARQUE": ("12", "CONHECIMENTO DE CARGA"),
            "FATURA COMERCIAL": ("01", "FATURA COMERCIAL"),
            "ROMANEIO DE CARGA": ("29", "ROMANEIO DE CARGA")
        }
        
        tipo_codigo, tipo_nome = tipo_map.get(doc["tipo"], ("00", "OUTRO"))
        ET.SubElement(doc_elem, "codigoTipoDocumentoDespacho").text = tipo_codigo
        ET.SubElement(doc_elem, "nomeDocumentoDespacho").text = tipo_nome.ljust(60)
        
        if doc.get("numero"):
            ET.SubElement(doc_elem, "numeroDocumentoDespacho").text = doc["numero"].ljust(25)
    
    # Adicionar informações complementares
    if dados.get("informacoes_complementares"):
        ET.SubElement(duimp, "informacaoComplementar").text = dados["informacoes_complementares"]
    
    # Converter para string XML formatada
    xml_string = ET.tostring(lista_declaracoes, encoding='utf-8', method='xml')
    
    # Formatar o XML
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    return pretty_xml

# Interface principal
uploaded_file = st.file_uploader("Faça upload do arquivo PDF do extrato DUIMP", type="pdf")

if uploaded_file is not None:
    # Extrair texto do PDF
    with st.spinner("Extraindo informações do PDF..."):
        texto_pdf = extrair_texto_pdf(uploaded_file)
    
    # Processar informações
    dados_extraidos = processar_extrato_duimp(texto_pdf)
    
    # Mostrar preview do texto extraído
    with st.expander("Visualizar Texto Extraído do PDF"):
        st.text_area("Conteúdo Extraído", texto_pdf, height=300)
    
    # Mostrar dados extraídos em colunas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📋 Informações do Importador")
        if dados_extraidos["importador"]:
            st.write(f"**Nome:** {dados_extraidos['importador'].get('nome', 'Não encontrado')}")
            st.write(f"**CNPJ:** {dados_extraidos['importador'].get('cnpj', 'Não encontrado')}")
        else:
            st.write("Não encontrado")
    
    with col2:
        st.subheader("📄 Dados da DUIMP")
        if dados_extraidos["duimp"]:
            st.write(f"**Número:** {dados_extraidos['duimp'].get('numero', 'Não encontrado')}")
            st.write(f"**Data Registro:** {dados_extraidos['duimp'].get('data_registro', 'Não encontrado')}")
            st.write(f"**Tipo Operação:** {dados_extraidos['duimp'].get('tipo_operacao', 'Não encontrado')}")
        else:
            st.write("Não encontrado")
    
    with col3:
        st.subheader("📦 Dados da Carga")
        if dados_extraidos["carga"]:
            st.write(f"**Via Transporte:** {dados_extraidos['carga'].get('via_transporte', 'Não encontrado')}")
            st.write(f"**Data Embarque:** {dados_extraidos['carga'].get('data_embarque', 'Não encontrado')}")
            st.write(f"**Peso Bruto:** {dados_extraidos['carga'].get('peso_bruto', 'Não encontrado')}")
        else:
            st.write("Não encontrado")
    
    # Mostrar tributos
    st.subheader("💰 Tributos")
    if dados_extraidos["tributos"]:
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        with col_t1:
            st.metric("II Devido", f"R$ {dados_extraidos['tributos'].get('ii_devido', '0,00')}")
        with col_t2:
            st.metric("PIS Devido", f"R$ {dados_extraidos['tributos'].get('pis_devido', '0,00')}")
        with col_t3:
            st.metric("COFINS Devido", f"R$ {dados_extraidos['tributos'].get('cofins_devido', '0,00')}")
    else:
        st.write("Nenhum tributo extraído")
    
    # Mostrar mercadorias
    st.subheader("📦 Mercadorias")
    if dados_extraidos["mercadorias"]:
        df_mercadorias = pd.DataFrame(dados_extraidos["mercadorias"])
        st.dataframe(df_mercadorias, use_container_width=True)
    else:
        st.write("Nenhuma mercadoria extraída")
    
    # Mostrar documentos
    st.subheader("📎 Documentos")
    if dados_extraidos["documentos"]:
        for doc in dados_extraidos["documentos"]:
            st.write(f"**{doc['tipo']}:** {doc.get('numero', 'N/A')}")
    else:
        st.write("Nenhum documento extraído")
    
    # Gerar XML
    st.divider()
    st.subheader("⚙️ Gerar XML")
    
    if st.button("Gerar Arquivo XML", type="primary"):
        with st.spinner("Gerando XML..."):
            xml_content = criar_xml_duimp(dados_extraidos)
            
            # Mostrar preview do XML
            with st.expander("Visualizar XML Gerado"):
                st.code(xml_content, language="xml")
            
            # Criar nome do arquivo
            nome_arquivo = f"M-DUIMP-{dados_extraidos['duimp'].get('numero', '0000000000')}.xml"
            
            # Botão para download
            st.download_button(
                label="📥 Baixar Arquivo XML",
                data=xml_content,
                file_name=nome_arquivo,
                mime="application/xml"
            )
            
            st.success("XML gerado com sucesso!")
else:
    st.info("👈 Por favor, faça upload de um arquivo PDF para começar")
    
    # Mostrar exemplo de estrutura
    with st.expander("Exemplo de Estrutura XML Esperada"):
        st.code("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ListaDeclaracoes>
    <duimp>
        <numeroDUIMP>8686868686</numeroDUIMP>
        <dataRegistro>20251124</dataRegistro>
        <importadorNome>HAFELE BRASIL LTDA</importadorNome>
        <importadorNumero>02473058000188</importadorNumero>
        <viaTransporteCodigo>01</viaTransporteCodigo>
        <viaTransporteNome>MARÍTIMA</viaTransporteNome>
        <!-- ... mais campos ... -->
        <adicao>
            <numeroAdicao>001</numeroAdicao>
            <dadosMercadoriaCodigoNcm>39263000</dadosMercadoriaCodigoNcm>
            <mercadoria>
                <numeroSequencialItem>01</numeroSequencialItem>
                <descricaoMercadoria>24627611 - 30 - 263.77.551 - SUPORTE DE PRATELEIRA...</descricaoMercadoria>
            </mercadoria>
        </adicao>
    </duimp>
</ListaDeclaracoes>""", language="xml")

# Rodapé
st.divider()
st.caption("Conversor DUIMP PDF para XML - Desenvolvido para integração de sistemas de importação")
