class HafelePDFParser:
    """
    Parser atualizado para o layout Extrato DUIMP (APP2.pdf).
    CORREÇÃO: Usa heurística de alíquotas para identificar PIS/COFINS/II/IPI,
    pois os cabeçalhos no PDF estão misturados ou deslocados.
    """
    
    def __init__(self):
        self.documento = {
            'cabecalho': {},
            'itens': [],
            'totais': {}
        }
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            logger.info(f"Iniciando parsing do layout DUIMP/APP2: {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    # layout=False garante a ordem de leitura do fluxo de dados
                    text = page.extract_text(layout=False) 
                    if text:
                        full_text += text + "\n"
            
            self._process_full_text(full_text)
            return self.documento
            
        except Exception as e:
            logger.error(f"Erro no parsing: {str(e)}")
            st.error(f"Erro ao ler o PDF APP2: {str(e)}")
            return self.documento

    def _process_full_text(self, text: str):
        # Separa o texto por "ITENS DA DUIMP-"
        chunks = re.split(r'(ITENS DA DUIMP-\d+)', text)
        items_found = []
        
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                header = chunks[i]
                content = chunks[i+1]
                item_num_match = re.search(r'(\d+)', header)
                item_num = int(item_num_match.group(1)) if item_num_match else i
                
                # Processa o bloco individual
                item_data = self._parse_item_block(item_num, content)
                if item_data:
                    items_found.append(item_data)
        
        self.documento['itens'] = items_found
        self._calculate_totals()

    def _parse_item_block(self, item_num: int, text: str) -> Dict:
        try:
            item = {
                'numero_item': item_num,
                'ncm': '',
                'codigo_produto': '',
                'codigo_interno': '',
                'nome_produto': '',
                'quantidade': 0.0,
                'peso_liquido': 0.0,
                'valor_total': 0.0,
                
                # Inicia zerado
                'ii_valor_devido': 0.0, 'ii_base_calculo': 0.0, 'ii_aliquota': 0.0,
                'ipi_valor_devido': 0.0, 'ipi_base_calculo': 0.0, 'ipi_aliquota': 0.0,
                'pis_valor_devido': 0.0, 'pis_base_calculo': 0.0, 'pis_aliquota': 0.0,
                'cofins_valor_devido': 0.0, 'cofins_base_calculo': 0.0, 'cofins_aliquota': 0.0,
                
                'frete_internacional': 0.0,
                'seguro_internacional': 0.0,
                'local_aduaneiro': 0.0
            }

            # --- Identificadores ---
            code_match = re.search(r'Código interno\s*([\d\.]+)', text)
            if code_match: item['codigo_interno'] = code_match.group(1).replace('.', '')

            ncm_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', text)
            if ncm_match: item['ncm'] = ncm_match.group(1).replace('.', '')

            # --- Valores Gerais ---
            qtd_match = re.search(r'Qtde Unid\. Comercial\s*([\d\.,]+)', text)
            if qtd_match: item['quantidade'] = self._parse_valor(qtd_match.group(1))
            
            val_match = re.search(r'Valor Tot\. Cond Venda\s*([\d\.,]+)', text)
            if val_match: item['valor_total'] = self._parse_valor(val_match.group(1))

            peso_match = re.search(r'Peso Líquido \(KG\)\s*([\d\.,]+)', text, re.IGNORECASE)
            if peso_match: item['peso_liquido'] = self._parse_valor(peso_match.group(1))

            frete_match = re.search(r'Frete Internac\. \(R\$\)\s*([\d\.,]+)', text)
            if frete_match: item['frete_internacional'] = self._parse_valor(frete_match.group(1))

            seg_match = re.search(r'Seguro Internac\. \(R\$\)\s*([\d\.,]+)', text)
            if seg_match: item['seguro_internacional'] = self._parse_valor(seg_match.group(1))

            aduana_match = re.search(r'Local Aduaneiro \(R\$\)\s*([\d\.,]+)', text)
            if aduana_match: item['local_aduaneiro'] = self._parse_valor(aduana_match.group(1))

            # --- CORREÇÃO DA EXTRAÇÃO DE IMPOSTOS ---
            # Em vez de procurar por blocos de texto (que falham), procuramos a ESTRUTURA dos dados:
            # Padrão: Base -> Alíquota -> Valor
            
            # Regex que captura trio: Base ... Alíquota ... Valor
            # Captura independente de quebras de linha (re.DOTALL)
            tax_matches = re.findall(
                r'Base de Cálculo \(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor (?:Devido|A Recolher|Calculado) \(R\$\)\s*([\d\.,]+)', 
                text, 
                re.DOTALL | re.IGNORECASE
            )

            # Itera sobre todas as tabelas de imposto encontradas no item
            for base_str, aliq_str, val_str in tax_matches:
                base = self._parse_valor(base_str)
                aliq = self._parse_valor(aliq_str)
                val = self._parse_valor(val_str)

                # Heurística para definir quem é quem baseada na Alíquota
                
                # PIS (Geralmente 1.65% ou 2.10%)
                if 1.60 <= aliq <= 3.00:
                    item['pis_aliquota'] = aliq
                    item['pis_base_calculo'] = base
                    item['pis_valor_devido'] = val
                
                # COFINS (Geralmente 7.60% ou 9.65%)
                elif 7.00 <= aliq <= 12.00:
                    item['cofins_aliquota'] = aliq
                    item['cofins_base_calculo'] = base
                    item['cofins_valor_devido'] = val
                
                # II - Importação (Geralmente > 12%, ex: 16%, 18%)
                elif aliq > 12.00:
                    item['ii_aliquota'] = aliq
                    item['ii_base_calculo'] = base
                    item['ii_valor_devido'] = val
                    
                # Se sobrar e não for zero, assume IPI (ou se alíquota específica de IPI)
                elif aliq > 0:
                    # Cuidado para não sobrescrever se já achou outros.
                    # IPI geralmente tem alíquotas variadas (0, 5, 10, 15...).
                    # Se não caiu nos ranges acima, é forte candidato a IPI.
                    if item['ipi_aliquota'] == 0: 
                        item['ipi_aliquota'] = aliq
                        item['ipi_base_calculo'] = base
                        item['ipi_valor_devido'] = val

            # Totais
            item['total_impostos'] = (item['ii_valor_devido'] + item['ipi_valor_devido'] + 
                                    item['pis_valor_devido'] + item['cofins_valor_devido'])
            item['valor_total_com_impostos'] = item['valor_total'] + item['total_impostos']

            return item
            
        except Exception as e:
            logger.error(f"Erro item {item_num}: {e}")
            return None

    def _parse_valor(self, valor_str: str) -> float:
        try:
            if not valor_str: return 0.0
            limpo = valor_str.replace('.', '').replace(',', '.')
            return float(limpo)
        except: return 0.0

    def _calculate_totals(self):
        totais = {
            'valor_total_mercadoria': sum(i['valor_total'] for i in self.documento['itens']),
            'total_impostos': sum(i['total_impostos'] for i in self.documento['itens'])
        }
        self.documento['totais'] = totais
