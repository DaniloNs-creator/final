import pdfplumber
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

class DuimpConverter:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.data = {
            "capa": {},
            "adicoes": []
        }
        # Buffer para guardar a adição sendo processada atualmente
        self.current_adicao = None

    def format_number_xml(self, value, length, precision=2):
        """
        Converte string '1.234,56' para formato XML '0000000123456'.
        Remove pontos de milhar e vírgula decimal.
        """
        if not value:
            return "0" * length
        
        # Limpa caracteres não numéricos exceto vírgula e ponto
        clean_val = re.sub(r'[^\d,.]', '', str(value))
        
        if ',' in clean_val:
            # Padrão brasileiro 1.000,00 -> 1000.00
            clean_val = clean_val.replace('.', '').replace(',', '.')
        
        try:
            # Converte para float para garantir precisão
            float_val = float(clean_val)
            # Multiplica pela precisão (ex: 100 para 2 casas decimais)
            int_val = int(round(float_val * (10 ** precision)))
            return str(int_val).zfill(length)
        except ValueError:
            return "0" * length

    def format_text(self, text):
        """Limpa espaços extras e quebras de linha."""
        if not text: return ""
        return " ".join(text.split()).strip()

    def extract_from_pdf(self):
        print(f"Iniciando extração de: {self.pdf_path}")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            full_text = ""
            # Estratégia para 500 páginas: Iterar e extrair texto corrido
            # mas mantendo o contexto de blocos
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        # --- 1. Extração da CAPA (Regex baseados no seu PDF) ---
        
        # Ex: "Numero","25BR00001916620"
        duimp_match = re.search(r'Numero\s*"?([\w\d]+)"?', full_text)
        self.data["capa"]["numeroDUIMP"] = duimp_match.group(1) if duimp_match else "0000000000"

        # Ex: Importador
        imp_match = re.search(r'IMPORTADOR\s*"\s*,\s*"\s*(.*?)\s*"', full_text, re.IGNORECASE)
        self.data["capa"]["importadorNome"] = imp_match.group(1) if imp_match else "DESCONHECIDO"

        # Ex: Peso Bruto (captura global da carga)
        peso_bruto_match = re.search(r'Peso Bruto\s*"?([\d.,]+)"?', full_text)
        self.data["capa"]["cargaPesoBruto"] = peso_bruto_match.group(1) if peso_bruto_match else "0"
        
        # Ex: Peso Liquido
        peso_liq_match = re.search(r'Peso Liquido\s*"?([\d.,]+)"?', full_text)
        self.data["capa"]["cargaPesoLiquido"] = peso_liq_match.group(1) if peso_liq_match else "0"

        # --- 2. Extração das ADIÇÕES (Loop complexo) ---
        
        # Vamos dividir o texto em blocos de "Item" ou "Nº Adição"
        # O padrão no PDF parece ser tabelas ou blocos iniciados por identificadores de item
        
        # Regex para encontrar blocos de itens. Ajustado para o padrão do PDF enviado
        # Procura por "Item [numero]" seguido de NCM
        item_pattern = re.compile(r'Item\s*"?(\d+)"?.*?NCM\s*"?([\d.]+)"?', re.DOTALL)
        
        # Encontrar todas as ocorrências de itens básicos primeiro para saber quantos são
        # Nota: Em PDFs complexos, o ideal é iterar linha a linha, mas regex funciona se o padrão for constante
        
        # Vamos iterar sobre linhas para capturar detalhes específicos de cada item
        lines = full_text.split('\n')
        current_item = {}
        capturing_item = False
        
        for i, line in enumerate(lines):
            # Identifica início de um item na tabela de itens
            # Ex: "1","X","8302.10.00","21"
            # Ajuste o regex conforme a linha exata que inicia um item no seu PDF real
            item_start = re.search(r'^\s*"?(\d+)"?\s*,\s*"?X"?\s*,\s*"?([\d.]+)"?', line)
            
            if item_start:
                # Se já tínhamos um item sendo capturado, salva ele
                if current_item:
                    self.data["adicoes"].append(current_item)
                
                # Inicia novo item
                current_item = {
                    "numeroAdicao": item_start.group(1).zfill(3),
                    "ncm": item_start.group(2).replace('.', ''),
                    "descricao": "DESCRIÇÃO PADRÃO - AJUSTAR NO REGEX", # Placeholder
                    "quantidade": "0",
                    "valor": "0",
                    "pesoLiq": "0"
                }
                capturing_item = True
                continue

            if capturing_item:
                # Tenta capturar dados complementares nas linhas seguintes
                
                # Ex: Captura Descrição (Geralmente linhas após "DESCRIÇÃO DO PRODUTO")
                if "DESCRIÇÃO DO PRODUTO" in line:
                    # Pega as próximas 2 linhas como descrição
                    try:
                        desc = lines[i+1] + " " + lines[i+2]
                        current_item["descricao"] = self.format_text(desc)[:200] # Limita tamanho
                    except: pass
                
                # Ex: Captura Quantidade e Unidade (Procura padrões numéricos grandes seguidos de texto)
                # "14.784,00000"
                qtd_match = re.search(r'Qtde Unid\. Estatística\s+([\d.,]+)', line)
                if qtd_match:
                    current_item["quantidade"] = qtd_match.group(1)

                # Ex: Valor Condição Venda
                val_match = re.search(r'VIr Cond Venda \(Moeda\s+([\d.,]+)', line)
                if not val_match:
                     val_match = re.search(r'Valor Tot\. Cond Venda\s+([\d.,]+)', line)

                if val_match:
                    current_item["valor"] = val_match.group(1)

        # Adiciona o último item encontrado
        if current_item:
            self.data["adicoes"].append(current_item)

        print(f"Total de adições encontradas: {len(self.data['adicoes'])}")

    def generate_xml(self, output_path):
        print("Gerando XML...")
        
        root = ET.Element("ListaDeclaracoes")
        duimp = ET.SubElement(root, "duimp")

        # --- Loop das Adições ---
        for item in self.data["adicoes"]:
            adicao = ET.SubElement(duimp, "adicao")
            
            # Campos Fixos/Calculados
            ET.SubElement(adicao, "numeroAdicao").text = item["numeroAdicao"]
            ET.SubElement(adicao, "numeroDUIMP").text = self.data["capa"].get("numeroDUIMP")
            
            # Dados da Mercadoria
            mercadoria = ET.SubElement(adicao, "mercadoria")
            ET.SubElement(mercadoria, "descricaoMercadoria").text = item.get("descricao", "N/D")
            # NCM
            ET.SubElement(adicao, "dadosMercadoriaCodigoNcm").text = item.get("ncm", "00000000")
            
            # Formatações Numéricas Rigorosas (Baseado no XML 8686868686)
            # Quantidade (5 casas decimais no XML de exemplo: 00000500000000) -> len 14, prec 5
            qtd_fmt = self.format_number_xml(item.get("quantidade"), 14, precision=5)
            ET.SubElement(mercadoria, "quantidade").text = qtd_fmt
            
            # Valor (2 casas decimais no XML: 000000001302962) -> len 15, prec 2
            val_fmt = self.format_number_xml(item.get("valor"), 15, precision=2)
            ET.SubElement(adicao, "condicaoVendaValorReais").text = val_fmt # Assumindo Reais para exemplo
            
            # Estrutura base de tributos (exemplo simplificado, pois varia por NCM)
            ET.SubElement(adicao, "iiRegimeTributacaoCode").text = "1"
            ET.SubElement(adicao, "pisCofinsRegimeTributacaoCodigo").text = "1"

        # --- Dados Gerais da DUIMP (Fim do XML) ---
        ET.SubElement(duimp, "importadorNome").text = self.data["capa"].get("importadorNome")
        
        # Formata Pesos Totais
        peso_b_fmt = self.format_number_xml(self.data["capa"].get("cargaPesoBruto"), 15, precision=5)
        ET.SubElement(duimp, "cargaPesoBruto").text = peso_b_fmt
        
        # Prettify e Salvar
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
        
        print(f"XML salvo com sucesso em: {output_path}")

# --- Execução ---
if __name__ == "__main__":
    # Substitua pelo caminho real do seu PDF
    arquivo_pdf = "extrato_de_conferencia_duimp_teste.pdf" 
    arquivo_xml_saida = "DUIMP_Final_Importacao.xml"
    
    converter = DuimpConverter(arquivo_pdf)
    
    # 1. Extrair
    try:
        converter.extract_from_pdf()
        # 2. Gerar XML
        converter.generate_xml(arquivo_xml_saida)
    except Exception as e:
        print(f"Erro durante o processamento: {e}")
        # Em produção, adicione logs detalhados aqui
