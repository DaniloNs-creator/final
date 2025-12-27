import streamlit as st
import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io

# Configuração da Página
st.set_page_config(
    page_title="Conversor DUIMP PDF > XML",
    page_icon="📄",
    layout="wide"
)

class DuimpConverter:
    def __init__(self, pdf_file):
        """
        Recebe um objeto de arquivo (BytesIO) do Streamlit, não um caminho de string.
        """
        self.pdf_file = pdf_file
        self.data = {
            "capa": {},
            "adicoes": []
        }

    def format_number_xml(self, value, length, precision=2):
        """Converte valores numéricos para o padrão string do XML (sem pontos/vírgulas)."""
        if not value:
            return "0" * length
        
        # Limpa caracteres não numéricos exceto vírgula e ponto
        clean_val = re.sub(r'[^\d,.]', '', str(value))
        
        if ',' in clean_val:
            clean_val = clean_val.replace('.', '').replace(',', '.')
        
        try:
            float_val = float(clean_val)
            int_val = int(round(float_val * (10 ** precision)))
            return str(int_val).zfill(length)
        except ValueError:
            return "0" * length

    def format_text(self, text):
        if not text: return ""
        return " ".join(text.split()).strip()

    def extract_data(self):
        """Extrai dados do PDF carregado em memória."""
        full_text = ""
        
        # Barra de progresso do Streamlit
        progress_text = "Lendo páginas do PDF..."
        my_bar = st.progress(0, text=progress_text)

        with pdfplumber.open(self.pdf_file) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                
                # Atualiza barra de progresso
                percent_complete = int(((i + 1) / total_pages) * 100)
                my_bar.progress(percent_complete, text=f"Lendo página {i+1} de {total_pages}")

        my_bar.empty() # Limpa a barra

        # --- 1. Extração da CAPA ---
        duimp_match = re.search(r'Numero\s*"?([\w\d]+)"?', full_text)
        self.data["capa"]["numeroDUIMP"] = duimp_match.group(1) if duimp_match else "0000000000"

        imp_match = re.search(r'IMPORTADOR\s*"\s*,\s*"\s*(.*?)\s*"', full_text, re.IGNORECASE)
        self.data["capa"]["importadorNome"] = imp_match.group(1) if imp_match else "DESCONHECIDO"

        peso_bruto_match = re.search(r'Peso Bruto\s*"?([\d.,]+)"?', full_text)
        self.data["capa"]["cargaPesoBruto"] = peso_bruto_match.group(1) if peso_bruto_match else "0"
        
        # --- 2. Extração das ADIÇÕES ---
        lines = full_text.split('\n')
        current_item = {}
        capturing_item = False
        
        for i, line in enumerate(lines):
            # Regex ajustado para capturar início de item (ex: "1","X","8302.10.00")
            item_start = re.search(r'^\s*"?(\d+)"?\s*,\s*"?X"?\s*,\s*"?([\d.]+)"?', line)
            
            if item_start:
                if current_item:
                    self.data["adicoes"].append(current_item)
                
                current_item = {
                    "numeroAdicao": item_start.group(1).zfill(3),
                    "ncm": item_start.group(2).replace('.', ''),
                    "descricao": "DESCRIÇÃO NÃO CAPTURADA",
                    "quantidade": "0",
                    "valor": "0"
                }
                capturing_item = True
                continue

            if capturing_item:
                if "DESCRIÇÃO DO PRODUTO" in line:
                    try:
                        desc = lines[i+1] + " " + lines[i+2]
                        current_item["descricao"] = self.format_text(desc)[:200]
                    except: pass
                
                qtd_match = re.search(r'Qtde Unid\. Estatística\s+([\d.,]+)', line)
                if qtd_match:
                    current_item["quantidade"] = qtd_match.group(1)

                val_match = re.search(r'VIr Cond Venda \(Moeda\s+([\d.,]+)', line)
                if not val_match:
                     val_match = re.search(r'Valor Tot\. Cond Venda\s+([\d.,]+)', line)
                if val_match:
                    current_item["valor"] = val_match.group(1)

        if current_item:
            self.data["adicoes"].append(current_item)

        return len(self.data["adicoes"])

    def get_xml_string(self):
        """Gera o XML e retorna como string formatada."""
        root = ET.Element("ListaDeclaracoes")
        duimp = ET.SubElement(root, "duimp")

        # Dados da Capa
        ET.SubElement(duimp, "numeroDUIMP").text = self.data["capa"].get("numeroDUIMP")
        ET.SubElement(duimp, "importadorNome").text = self.data["capa"].get("importadorNome")
        
        peso_b_fmt = self.format_number_xml(self.data["capa"].get("cargaPesoBruto"), 15, precision=5)
        ET.SubElement(duimp, "cargaPesoBruto").text = peso_b_fmt

        # Loop das Adições
        for item in self.data["adicoes"]:
            adicao = ET.SubElement(duimp, "adicao")
            
            ET.SubElement(adicao, "numeroAdicao").text = item["numeroAdicao"]
            
            mercadoria = ET.SubElement(adicao, "mercadoria")
            ET.SubElement(mercadoria, "descricaoMercadoria").text = item.get("descricao", "N/D")
            ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item.get("ncm", "00000000")
            
            qtd_fmt = self.format_number_xml(item.get("quantidade"), 14, precision=5)
            ET.SubElement(mercadoria, "quantidade").text = qtd_fmt
            
            val_fmt = self.format_number_xml(item.get("valor"), 15, precision=2)
            ET.SubElement(adicao, "condicaoVendaValorReais").text = val_fmt

        # Gera string
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
        return xml_str

# --- Interface Streamlit ---

st.title("📄 Conversor de Extrato DUIMP para XML")
st.markdown("""
Este aplicativo converte o PDF de Extrato de Conferência da DUIMP para o formato XML compatível com importação de sistemas.
**Suporta arquivos grandes (500+ itens).**
""")

st.divider()

col1, col2 = st.columns([1, 2])

with col1:
    st.info("📂 **Passo 1:** Faça upload do PDF")
    uploaded_file = st.file_uploader("Escolha o arquivo PDF", type="pdf")

if uploaded_file is not None:
    # Mostra detalhes do arquivo
    file_details = {"Nome": uploaded_file.name, "Tamanho": f"{uploaded_file.size / 1024:.2f} KB"}
    st.write(file_details)

    # Botão de processamento
    if st.button("🔄 Processar e Converter", type="primary"):
        try:
            with st.spinner('Processando dados... Isso pode levar alguns segundos para arquivos grandes.'):
                # Instancia o conversor passando o arquivo em memória
                converter = DuimpConverter(uploaded_file)
                
                # Executa extração
                total_itens = converter.extract_data()
                
                # Gera XML
                xml_output = converter.get_xml_string()

            # Sucesso
            st.success("Conversão concluída com sucesso!")
            
            # Métricas
            m1, m2 = st.columns(2)
            m1.metric("Número da DUIMP", converter.data["capa"].get("numeroDUIMP", "N/A"))
            m2.metric("Itens Encontrados", total_itens)

            # Preview do XML
            with st.expander("Ver Preview do XML (Primeiras 20 linhas)"):
                st.code("\n".join(xml_output.split("\n")[:20]), language="xml")

            # Botão de Download
            st.download_button(
                label="⬇️ Baixar XML da DUIMP",
                data=xml_output,
                file_name=f"DUIMP_{converter.data['capa'].get('numeroDUIMP', 'Export')}.xml",
                mime="application/xml",
            )

        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
            st.warning("Verifique se o PDF é um 'Extrato de Conferência' válido e se não está corrompido.")

else:
    with col2:
        st.write("👈 *Aguardando upload do arquivo para iniciar...*")
