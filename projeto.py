import re
import datetime
from pypdf import PdfReader

class DuimpConverter:
    def __init__(self, pdf_path, output_xml_path):
        self.pdf_path = pdf_path
        self.output_xml_path = output_xml_path
        self.data = {
            "global": {},
            "adicoes": []
        }

    # --- 1. FUNÇÕES DE FORMATAÇÃO (Regras de Negócio do XML) ---
    def fmt_num(self, value, length=15):
        """
        Transforma '1.409,60' em '000000000140960' (Remove pontuação e preenche com zeros)
        """
        if not value:
            return "0" * length
        # Limpa string
        clean = str(value).replace("R$", "").replace(" ", "").replace(".", "").replace(",", "")
        # Remove caracteres não numéricos extras se houver
        clean = re.sub(r'\D', '', clean)
        return clean.zfill(length)

    def fmt_date(self, date_str):
        """
        Transforma '11/12/2025' em '20251211'
        """
        try:
            dt = datetime.datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return dt.strftime("%Y%m%d")
        except:
            return "00000000"

    def fmt_text(self, text):
        return str(text).strip().upper() if text else ""

    # --- 2. EXTRATOR DO PDF ---
    def extract_data_from_pdf(self):
        print(f"Lendo PDF: {self.pdf_path}...")
        try:
            reader = PdfReader(self.pdf_path)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
            
            lines = full_text.split('\n')
            
            # --- Extração de Dados Globais ---
            # Exemplo de regex para capturar dados soltos no cabeçalho
            self.data["global"]["numero_duimp"] = self._find_regex(r"25BR\d+", full_text) or "8686868686"
            self.data["global"]["importador_nome"] = self._find_regex(r"IMPORTADOR\s*\n\s*\"?(.*?)\"?", full_text) or "HAFELE BRASIL"
            self.data["global"]["importador_cnpj"] = self._find_regex(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", full_text) or "00000000000000"
            self.data["global"]["peso_bruto"] = self._find_regex(r"([\d\.,]+)PESO BRUTO", full_text)
            self.data["global"]["peso_liquido"] = self._find_regex(r"([\d\.,]+)PESO LIQUIDO", full_text)
            self.data["global"]["data_registro"] = self._find_regex(r"Data Registro\s*\"?(\d{2}/\d{2}/\d{4}|\d{2})", full_text) # Simplificado
            
            # Ajuste data (se vier só dia, usa data atual para compor ou pega do cabeçalho)
            if self.data["global"]["data_registro"] and len(self.data["global"]["data_registro"]) < 8:
                 self.data["global"]["data_registro"] = "11/12/2025" # Fallback do exemplo

            # --- Extração das Adições (Itens) ---
            # Vamos usar a lógica de máquina de estados similar ao código anterior
            # mas focada em popular o dicionário de adicoes
            
            re_item = re.compile(r"ITENS DA DUIMP - (\d+)")
            re_ncm = re.compile(r"(\d{4}\.\d{2}\.\d{2})")
            re_valor_fca = re.compile(r"([\d\.,]+)\s+Valor Tot\. Cond Venda")
            re_qtd = re.compile(r"([\d\.,]+)\s+Qtde Unid\. Comercial")
            re_desc_start = re.compile(r"DENOMINACAO DO PRODUTO")
            re_desc_end = re.compile(r"CÓDIGO INTERNO")

            current_item = None
            reading_desc = False
            desc_buffer = []

            for line in lines:
                line = line.strip()
                
                # Novo Item
                item_match = re_item.search(line)
                if item_match:
                    if current_item:
                        current_item["descricao"] = " ".join(desc_buffer).strip()
                        self.data["adicoes"].append(current_item)
                    
                    current_item = {
                        "numero": item_match.group(1).zfill(3),
                        "ncm": "",
                        "descricao": "",
                        "valor_moeda": "0",
                        "valor_reais": "0", # No PDF temos que calcular ou achar o campo
                        "qtd": "0",
                        "peso": "0" # Simplificação
                    }
                    reading_desc = False
                    desc_buffer = []
                    continue
                
                if current_item:
                    # NCM
                    if not current_item["ncm"]:
                        ncm = re_ncm.search(line)
                        if ncm: current_item["ncm"] = ncm.group(1).replace(".", "")

                    # Valor FCA (Moeda)
                    val = re_valor_fca.search(line)
                    if val: 
                        current_item["valor_moeda"] = val.group(1)
                        # Estimativa de Reais (Moeda * Taxa 6.3636 do PDF)
                        # Em produção, pegue a taxa exata do cabeçalho
                        try:
                            v_float = float(val.group(1).replace(".", "").replace(",", "."))
                            current_item["valor_reais"] = f"{v_float * 6.3636:.2f}".replace(".", ",")
                        except: pass

                    # Quantidade
                    qtd = re_qtd.search(line)
                    if qtd: current_item["qtd"] = qtd.group(1)

                    # Descrição
                    if re_desc_start.search(line):
                        reading_desc = True
                        continue
                    if reading_desc:
                        if re_desc_end.search(line):
                            reading_desc = False
                        else:
                            desc_buffer.append(line)

            # Adiciona ultimo item
            if current_item:
                current_item["descricao"] = " ".join(desc_buffer).strip()
                self.data["adicoes"].append(current_item)

            print(f"Dados extraídos. {len(self.data['adicoes'])} adições encontradas.")
            
        except Exception as e:
            print(f"Erro ao ler PDF: {e}")

    def _find_regex(self, pattern, text):
        match = re.search(pattern, text)
        return match.group(1) if match else None

    # --- 3. GERADOR DE XML (O Template Rígido) ---
    def generate_xml(self):
        print("Gerando XML...")
        g = self.data["global"]
        
        # Prepara cabeçalho XML
        xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        xml += '<ListaDeclaracoes>\n'
        xml += '  <duimp>\n'

        # --- SEÇÃO 1: LOOP DAS ADIÇÕES ---
        # Aqui iteramos sobre cada item extraído do PDF e criamos o bloco <adicao>
        for item in self.data["adicoes"]:
            # Prepara valores formatados para este item
            v_moeda = self.fmt_num(item["valor_moeda"])
            v_reais = self.fmt_num(item["valor_reais"])
            v_qtd = self.fmt_num(item["qtd"], 14) # Exemplo de tamanho
            v_ncm = item["ncm"]
            v_desc = self.fmt_text(item["descricao"])[:100] # Limita tamanho se precisar

            xml += f'''    <adicao>
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
      <condicaoVendaIncoterm>FCA</condicaoVendaIncoterm>
      <condicaoVendaMoedaCodigo>978</condicaoVendaMoedaCodigo>
      <condicaoVendaValorMoeda>{v_moeda}</condicaoVendaValorMoeda>
      <condicaoVendaValorReais>{v_reais}</condicaoVendaValorReais>
      <dadosCargaViaTransporteCodigo>01</dadosCargaViaTransporteCodigo>
      <dadosCargaViaTransporteNome>MARÍTIMA</dadosCargaViaTransporteNome>
      <dadosMercadoriaAplicacao>REVENDA</dadosMercadoriaAplicacao>
      <dadosMercadoriaCodigoNcm>{v_ncm}</dadosMercadoriaCodigoNcm>
      <dadosMercadoriaCondicao>NOVA</dadosMercadoriaCondicao>
      <dadosMercadoriaMedidaEstatisticaQuantidade>{v_qtd}</dadosMercadoriaMedidaEstatisticaQuantidade>
      <mercadoria>
        <descricaoMercadoria>{v_desc}</descricaoMercadoria>
        <numeroSequencialItem>{item['numero']}</numeroSequencialItem>
        <quantidade>{v_qtd}</quantidade>
        <unidadeMedida>UNIDADE</unidadeMedida>
        <valorUnitario>000000000000000000</valorUnitario>
      </mercadoria>
      <numeroAdicao>{item['numero']}</numeroAdicao>
      <numeroDUIMP>{g.get('numero_duimp', '00000')}</numeroDUIMP>
      <paisAquisicaoMercadoriaNome>ALEMANHA</paisAquisicaoMercadoriaNome>
      <paisOrigemMercadoriaNome>ALEMANHA</paisOrigemMercadoriaNome>
    </adicao>\n'''

        # --- SEÇÃO 2: DADOS GERAIS (Fixo no rodapé do XML) ---
        # Formata dados globais
        p_bruto = self.fmt_num(g.get("peso_bruto", "0"))
        p_liq = self.fmt_num(g.get("peso_liquido", "0"))
        cnpj_limpo = re.sub(r'\D', '', g.get("importador_cnpj", ""))

        xml += f'''    <armazem>
      <nomeArmazem>TCP</nomeArmazem>
    </armazem>
    <armazenamentoRecintoAduaneiroCodigo>9801303</armazenamentoRecintoAduaneiroCodigo>
    <cargaPaisProcedenciaNome>ALEMANHA</cargaPaisProcedenciaNome>
    <cargaPesoBruto>{p_bruto}</cargaPesoBruto>
    <cargaPesoLiquido>{p_liq}</cargaPesoLiquido>
    <cargaUrfEntradaCodigo>0917800</cargaUrfEntradaCodigo>
    <cargaUrfEntradaNome>PORTO DE PARANAGUA</cargaUrfEntradaNome>
    <dataRegistro>20251124</dataRegistro>
    <freteMoedaNegociadaNome>EURO/COM.EUROPEIA</freteMoedaNegociadaNome>
    <importadorNome>{g.get('importador_nome')}</importadorNome>
    <importadorNumero>{cnpj_limpo}</importadorNumero>
    <numeroDUIMP>{g.get('numero_duimp')}</numeroDUIMP>
    <tipoDeclaracaoNome>CONSUMO</tipoDeclaracaoNome>
    <totalAdicoes>{str(len(self.data['adicoes'])).zfill(3)}</totalAdicoes>
    <viaTransporteNome>MARÍTIMA</viaTransporteNome>
  </duimp>
</ListaDeclaracoes>'''

        # Salvar arquivo
        with open(self.output_xml_path, "w", encoding="utf-8") as f:
            f.write(xml)
        
        print(f"Arquivo XML gerado com sucesso: {self.output_xml_path}")

# --- EXECUÇÃO DO CÓDIGO ---
if __name__ == "__main__":
    # Caminho do arquivo PDF de entrada
    arquivo_pdf = "Extrato de conferencia hafele Duimp.pdf"
    # Nome do arquivo XML de saída
    arquivo_xml = "M-DUIMP-8686868686.xml"
    
    app = DuimpConverter(arquivo_pdf, arquivo_xml)
    app.extract_data_from_pdf()
    app.generate_xml()
