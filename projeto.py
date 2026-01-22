class HafelePDFParser:
    """
    Parser especializado para o Layout Detalhado (APP2.pdf)
    Onde cada item possui seu próprio bloco de tributação e detalhes.
    """
    
    def __init__(self):
        self.documento = {
            'cabecalho': {},
            'itens': [],
            'totais': {}
        }
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            logging.info(f"Iniciando parsing do PDF: {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    # Extração de texto mantendo layout para facilitar regex
                    full_text += page.extract_text() + "\n\n"
            
            # Processamento baseado em blocos de itens
            self._process_text_blocks(full_text)
            
            return self.documento
            
        except Exception as e:
            logging.error(f"Erro no parsing: {str(e)}")
            raise

    def _process_text_blocks(self, text: str):
        """Divide o texto completo em blocos de itens"""
        
        # O padrão de quebra é "ITENS DA DUIMP-" ou "Item Integracao"
        # Usamos um lookahead para dividir sem consumir o número do próximo item
        # Exemplo no PDF: "ITENS DA DUIMP-00001" ou "Item X"
        
        # Estratégia: Encontrar onde começam os itens e dividir o texto
        # Regex captura o inicio de um item: Item <numero> ou ITENS DA DUIMP-<numero>
        item_split_pattern = r'(?:ITENS DA DUIMP-|Item\s+(?:Integracao\s+)?|Item\s*\n)(\d+)'
        
        # Split gera lista: [LixoHeader, NumItem1, TextoItem1, NumItem2, TextoItem2...]
        chunks = re.split(item_split_pattern, text)
        
        if len(chunks) < 2:
            logging.warning("Nenhum item encontrado com o padrão de blocos.")
            return

        # O primeiro chunk é o cabeçalho geral (antes do item 1)
        self._parse_header(chunks[0])
        
        # Iterar pares (Número do Item, Texto do Item)
        # chunks[0] é lixo/header, então começamos de 1
        for i in range(1, len(chunks), 2):
            item_num = chunks[i].strip()
            item_body = chunks[i+1]
            
            item_data = self._extract_item_data(item_num, item_body)
            if item_data:
                self.documento['itens'].append(item_data)
                
        self._calculate_totals()

    def _parse_header(self, text: str):
        """Extrai dados globais como Moeda e Frete se necessário"""
        # Exemplo: Capturar Processo
        proc_match = re.search(r'PROCESSO\s*#?(\d+)', text, re.IGNORECASE)
        if proc_match:
            self.documento['cabecalho']['processo'] = proc_match.group(1)

    def _extract_item_data(self, item_num: str, text: str) -> Dict:
        """Extrai dados de dentro do bloco de texto de UM item"""
        try:
            item = {
                'numero_item': item_num,
                # Valores padrão
                'codigo_interno': '',
                'nome_produto': '',
                'ncm': '',
                'valor_total': 0.0,
                'frete_internacional': 0.0,
                'seguro_internacional': 0.0,
                'local_aduaneiro': 0.0,
                'ii_valor_devido': 0.0,
                'ipi_valor_devido': 0.0,
                'pis_valor_devido': 0.0,
                'cofins_valor_devido': 0.0,
                # Adicione outros campos padrão se necessário
            }
            
            # --- 1. Identificação do Produto ---
            
            # Código Interno / Part Number
            # No PDF aparece como "Código interno 342.79.301" ou "CODIGO INTERNO (PARTNUMBER)..."
            code_match = re.search(r'(?:Código interno|PartNumber).*?([\d\.]+)', text, re.IGNORECASE)
            if code_match:
                item['codigo_interno'] = code_match.group(1).strip()
            
            # NCM
            ncm_match = re.search(r'NCM\s*(\d[\d\.]*)', text)
            if not ncm_match: # Tenta layout alternativo "8302.10.00" solto no inicio
                 ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', text)
            if ncm_match:
                item['ncm'] = ncm_match.group(1)

            # --- 2. Valores Financeiros ---
            
            # Valor Total (Condição de Venda)
            # PDF: "Valor Tot. Cond Venda 519,00"
            val_total_match = re.search(r'Valor Tot\. Cond Venda\s*([\d\.,]+)', text)
            if val_total_match:
                item['valor_total'] = self._parse_valor(val_total_match.group(1))
            
            # Frete
            frete_match = re.search(r'Frete Internac\.\s*\(R\$\)\s*([\d\.,]+)', text)
            if frete_match:
                item['frete_internacional'] = self._parse_valor(frete_match.group(1))

            # Seguro
            seguro_match = re.search(r'Seguro Internac\.\s*\(R\$\)\s*([\d\.,]+)', text)
            if seguro_match:
                item['seguro_internacional'] = self._parse_valor(seguro_match.group(1))
                
            # Valor Aduaneiro
            aduana_match = re.search(r'Local Aduaneiro\s*\(R\$\)\s*([\d\.,]+)', text)
            if aduana_match:
                item['local_aduaneiro'] = self._parse_valor(aduana_match.group(1))

            # --- 3. Impostos (Logica de Bloco) ---
            # O PDF agrupa impostos. Usamos Regex com DOTALL para pegar "II ... Valor Devido"
            
            # II
            ii_match = re.search(r'II.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.DOTALL)
            if ii_match: item['ii_valor_devido'] = self._parse_valor(ii_match.group(1))
            
            # IPI
            ipi_match = re.search(r'IPI.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.DOTALL)
            if ipi_match: item['ipi_valor_devido'] = self._parse_valor(ipi_match.group(1))
            
            # PIS
            # Cuidado: PIS e COFINS as vezes aparecem juntos no cabeçalho "1100-PIS... e COFINS"
            # Mas os valores calculados aparecem separados.
            
            # Busca PIS específico (Procura bloco PIS que tenha Valor Devido)
            pis_match = re.search(r'PIS(?!.*COFINS).*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.DOTALL)
            # Se falhar, tenta pegar o primeiro valor de um bloco "PIS-IMPORTAÇÃO"
            if not pis_match:
                pis_match = re.search(r'PIS-IMPORTAÇÃO.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.DOTALL)
            if pis_match: item['pis_valor_devido'] = self._parse_valor(pis_match.group(1))
            
            # COFINS
            cofins_match = re.search(r'COFINS.*?Valor Devido \(R\$\)\s*([\d\.,]+)', text, re.DOTALL)
            if cofins_match: item['cofins_valor_devido'] = self._parse_valor(cofins_match.group(1))
            
            # Extração de Bases e Alíquotas (Opcional para a vinculação, mas bom ter)
            base_match = re.search(r'II.*?Base de Cálculo \(R\$\)\s*([\d\.,]+)', text, re.DOTALL)
            if base_match: item['ii_base_calculo'] = self._parse_valor(base_match.group(1))

            item['total_impostos'] = (item['ii_valor_devido'] + item['ipi_valor_devido'] + 
                                      item['pis_valor_devido'] + item['cofins_valor_devido'])
            
            return item
            
        except Exception as e:
            logging.error(f"Erro processando item {item_num}: {e}")
            return None

    def _parse_valor(self, valor_str: str) -> float:
        if not valor_str: return 0.0
        # Formato Brasileiro: 1.000,00 -> remove ponto, troca virgula por ponto
        clean = valor_str.replace('.', '').replace(',', '.')
        try:
            return float(clean)
        except:
            return 0.0

    def _calculate_totals(self):
        # Recalcula totais gerais baseado nos itens extraídos
        pass
