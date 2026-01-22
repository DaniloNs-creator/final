import streamlit as st
import pdfplumber
import re
import pandas as pd
import tempfile
import os
import logging
from typing import Dict, List, Optional, Any

# ==============================================================================
# CONFIGURAÇÃO GERAL
# ==============================================================================
st.set_page_config(page_title="Sistema Integrado DUIMP 2026 (Final)", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; color: #003366; font-weight: bold; margin-bottom: 1rem; border-bottom: 2px solid #003366; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; background-color: #003366; color: white; height: 3em; }
    .metric-box { background-color: #f0f2f6; border-radius: 5px; padding: 15px; border-left: 5px solid #003366; }
</style>
""", unsafe_allow_html=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. PARSER APP 2 (HÄFELE) - ENGINE HÍBRIDA (PADRÃO + INVERTIDO)
# ==============================================================================

class HafelePDFParser:
    """
    Parser profissional capaz de ler layouts mistos (Standard e Left-Shifted).
    """
    def __init__(self):
        self.documento = {'itens': [], 'totais': {}}
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                # layout=True mantém a posição relativa visual (essencial para este PDF)
                text = page.extract_text(layout=True)
                if text: 
                    # Remove rodapés para limpar a leitura contínua
                    text = re.sub(r'--- PAGE \d+ ---', '', text)
                    all_text += text + "\n"
            
            self._process_full_text(all_text)
            return self.documento
            
    def _process_full_text(self, text: str):
        # Separa os itens pelo marcador mestre "ITENS DA DUIMP"
        chunks = re.split(r"ITENS DA DUIMP-(\d+)", text)
        
        items = []
        if len(chunks) > 1:
            # chunks[1]=Numero, chunks[2]=Conteudo...
            for i in range(1, len(chunks), 2):
                try:
                    item_num = int(chunks[i])
                    content = chunks[i+1]
                    item_data = self._parse_item_content(content, item_num)
                    items.append(item_data)
                except Exception as e:
                    logger.error(f"Erro item {i}: {e}")
        
        self.documento['itens'] = items
        self._calculate_totals()
    
    def _parse_item_content(self, text: str, item_num: int) -> Dict:
        item = {
            'numero_item': item_num,
            'codigo_interno': '',
            'descricao_complementar': '',
            'ncm': '',
            'produto': '',
            'valor_total': 0.0,
            'local_aduaneiro': 0.0, # BASE DE CÁLCULO PRINCIPAL
            'frete_internacional': 0.0,
            'seguro_internacional': 0.0,
            # Impostos (Valores e Alíquotas)
            'ii_valor': 0.0, 'ii_aliq': 0.0,
            'ipi_valor': 0.0, 'ipi_aliq': 0.0,
            'pis_valor': 0.0, 'pis_aliq': 0.0,
            'cofins_valor': 0.0, 'cofins_aliq': 0.0
        }

        # --- 1. IDENTIFICAÇÃO (CÓDIGO E DESCRIÇÃO) ---
        code_match = re.search(r'Código interno[^\d\n]*([\d\.]+)', text, re.IGNORECASE)
        if code_match: item['codigo_interno'] = code_match.group(1).strip()

        desc_match = re.search(r'DESCRIÇÃO COMPLEMENTAR DA MERCADORIA\s*\n?(.*?)(?=\n|CONDIÇÃO|NCM)', text, re.IGNORECASE | re.DOTALL)
        if desc_match: item['descricao_complementar'] = desc_match.group(1).strip().replace('\n', ' ')
        
        prod_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n?(.*?)(?=\n|DESCRICAO)', text, re.IGNORECASE | re.DOTALL)
        if prod_match: item['produto'] = prod_match.group(1).strip()

        ncm_match = re.search(r'NCM\s*\n?([\d\.]+)', text)
        if ncm_match: item['ncm'] = ncm_match.group(1).strip()

        # --- 2. VALORES (USANDO SUA LÓGICA PREFERIDA PARA ADUANEIRO) ---
        
        # Local Aduaneiro (Padrão: Label -> Valor)
        # Sua lógica: re.search(r'Local Aduaneiro \(R\$\)\s*([\d\.,]+)')
        loc_adu = re.search(r'Local Aduaneiro\s*\(R\$\)\s*([\d\.,]+)', text, re.IGNORECASE)
        if loc_adu: item['local_aduaneiro'] = self._parse_valor(loc_adu.group(1))

        # Frete e Seguro (Padrão: Label -> Valor)
        item['frete_internacional'] = self._extract_smart(r'Frete Internac\.', text, force_forward=True)
        item['seguro_internacional'] = self._extract_smart(r'Seguro Internac\.', text, force_forward=True)
        item['valor_total'] = self._extract_smart(r'Valor Tot\. Cond Venda', text, force_forward=True)

        # --- 3. IMPOSTOS (LÓGICA HÍBRIDA DE BLOCOS) ---
        # Isolamos cada imposto para evitar misturar dados
        self._extract_taxes_blocks(text, item)

        return item

    def _extract_taxes_blocks(self, text: str, item: Dict):
        """
        Recorta o texto em blocos (II, IPI...) e aplica extração bidirecional (Frente/Trás).
        """
        # Encontra índices
        idx_ii = -1
        match_ii = re.search(r'\b(II|11)\b[\s\n]', text) # Aceita II ou 11 (OCR)
        if match_ii: idx_ii = match_ii.start()
        
        idx_ipi = text.find("IPI", idx_ii if idx_ii != -1 else 0)
        
        match_pis = re.search(r'\bPIS\b[\s\n-]', text) # PIS isolado
        idx_pis = match_pis.start() if match_pis else -1
        
        match_cofins = re.search(r'\bCOFINS\b[\s\n]', text)
        idx_cofins = match_cofins.start() if match_cofins else -1

        def get_block(start, potential_ends):
            if start == -1: return ""
            valid = [x for x in potential_ends if x > start]
            end = min(valid) if valid else len(text)
            return text[start:end]

        # Blocos
        b_ii = get_block(idx_ii, [idx_ipi, idx_pis, idx_cofins])
        b_ipi = get_block(idx_ipi, [idx_pis, idx_cofins])
        b_pis = get_block(idx_pis, [idx_cofins])
        b_cofins = text[idx_cofins:] if idx_cofins != -1 else ""

        # Extração (Tenta Padrão Invertido Primeiro para Valores de Imposto)
        def process_tax(prefix, block):
            if not block: return
            
            # Valor (Geralmente invertido: "531,00 Valor Devido")
            val = self._extract_smart(r'Valor Devido', block)
            if val == 0: val = self._extract_smart(r'Valor A Recolher', block)
            if val == 0: val = self._extract_smart(r'Valor Calculado', block)
            
            # Alíquota
            aliq = self._extract_smart(r'% Alíquota', block)
            if aliq == 0: aliq = self._extract_smart(r'Ad Valorem', block)

            item[f'{prefix}_valor'] = val
            item[f'{prefix}_aliq'] = aliq

        process_tax('ii', b_ii)
        process_tax('ipi', b_ipi)
        process_tax('pis', b_pis)
        process_tax('cofins', b_cofins)

    def _extract_smart(self, label_pattern: str, text: str, force_forward: bool = False) -> float:
        """
        Tenta extrair o valor olhando para frente (Label -> Valor) E para trás (Valor -> Label).
        """
        try:
            # 1. Forward (Padrão): Label ... Valor
            regex_fwd = label_pattern + r'[^\d\n]*?([\d\.]*,\d+)'
            match_fwd = re.search(regex_fwd, text, re.IGNORECASE | re.DOTALL)
            val_fwd = self._parse_valor(match_fwd.group(1)) if match_fwd else 0.0
            
            if force_forward: return val_fwd

            # 2. Reverse (Invertido): Valor ... Label (comum em tabelas quebradas)
            # ([\d\.]*,\d+) ... Label
            regex_rev = r'([\d\.]*,\d+)[^\d\n]*?' + label_pattern
            match_rev = re.search(regex_rev, text, re.IGNORECASE)
            val_rev = self._parse_valor(match_rev.group(1)) if match_rev else 0.0

            # Prioridade: Maior valor ou Reverse se existir (já que forward pode pegar lixo distante)
            return val_rev if val_rev > 0 else val_fwd
        except:
            return 0.0

    def _calculate_totals(self):
        totais = {'total_impostos': 0.0, 'total_mercadoria': 0.0}
        for item in self.documento['itens']:
            imp = item['ii_valor'] + item['ipi_valor'] + item['pis_valor'] + item['cofins_valor']
            totais['total_impostos'] += imp
            totais['total_mercadoria'] += item['valor_total']
        self.documento['totais'] = totais

    def _parse_valor(self, valor_str: str) -> float:
        if not valor_str: return 0.0
        try:
            clean = valor_str.replace('.', '').replace(',', '.')
            return float(clean)
        except: return 0.0

class FinancialAnalyzer:
    def __init__(self, documento: Dict):
        self.documento = documento
    
    def prepare_dataframe(self):
        # Converte lista de dicts para DataFrame flat
        data = []
        for it in self.documento['itens']:
            # Concatenação solicitada
            cod = it.get('codigo_interno', '')
            desc = it.get('descricao_complementar', '')
            full_id = f"{cod} - {desc}" if desc else cod
            
            row = {
                'Item': it.get('numero_item'),
                'ID Composto': full_id,
                'Código Interno': cod,
                'Descrição': desc,
                'Produto': it.get('produto', ''),
                'NCM': it.get('ncm', ''),
                'Aduaneiro (Base)': it.get('local_aduaneiro', 0.0),
                'Frete': it.get('frete_internacional', 0.0),
                'Seguro': it.get('seguro_internacional', 0.0),
                'II Valor': it.get('ii_valor', 0.0), 'II %': it.get('ii_aliq', 0.0),
                'IPI Valor': it.get('ipi_valor', 0.0), 'IPI %': it.get('ipi_aliq', 0.0),
                'PIS Valor': it.get('pis_valor', 0.0), 'PIS %': it.get('pis_aliq', 0.0),
                'COFINS Valor': it.get('cofins_valor', 0.0), 'COFINS %': it.get('cofins_aliq', 0.0)
            }
            data.append(row)
        return pd.DataFrame(data)

# ==============================================================================
# MAIN APP
# ==============================================================================

def main():
    st.markdown('<div class="main-header">🏭 Sistema de Análise Häfele (Final)</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("Upload")
        uploaded_file = st.file_uploader("Arquivo Häfele (.pdf)", type=['pdf'])

    if uploaded_file:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            parser = HafelePDFParser()
            doc = parser.parse_pdf(tmp_path)
            os.unlink(tmp_path)
            
            analyser = FinancialAnalyzer(doc)
            df = analyser.prepare_dataframe()
            
            # --- DASHBOARD ---
            totais = doc['totais']
            c1, c2 = st.columns(2)
            c1.markdown(f'<div class="metric-box"><h3>Total Mercadoria</h3><h2>R$ {totais.get("total_mercadoria", 0):,.2f}</h2></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box"><h3>Total Impostos</h3><h2>R$ {totais.get("total_impostos", 0):,.2f}</h2></div>', unsafe_allow_html=True)
            
            st.divider()
            st.subheader(f"📦 Itens Extraídos ({len(df)})")
            
            # Formatação para exibição
            display_df = df.copy()
            cols_moeda = ['Aduaneiro (Base)', 'Frete', 'Seguro', 'II Valor', 'IPI Valor', 'PIS Valor', 'COFINS Valor']
            for c in cols_moeda:
                display_df[c] = display_df[c].apply(lambda x: f"R$ {x:,.2f}")
            
            st.dataframe(display_df, use_container_width=True, height=500)
            
            # Exportação
            csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Baixar CSV para Excel", csv, "relatorio_hafele.csv", "text/csv")
            
        except Exception as e:
            st.error(f"Erro: {e}")
    else:
        st.info("Por favor, carregue o PDF 'APP2' para iniciar.")

if __name__ == "__main__":
    main()
