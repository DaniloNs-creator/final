import streamlit as st
import pandas as pd
import pdfplumber
import re
import io
import logging

# Configuração da página
st.set_page_config(
    page_title="Extrator DUIMP - Padrão APP2",
    page_icon="📦",
    layout="wide"
)

# Estilos CSS
st.markdown("""
<style>
    .main-header { font-size: 2rem; color: #1E3A8A; font-weight: bold; margin-bottom: 1rem; }
    .card { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 1rem; }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #0F5132; }
    .metric-label { font-size: 0.9rem; color: #6c757d; }
</style>
""", unsafe_allow_html=True)

class DuimpParser:
    """Parser especializado para o layout DUIMP (APP2)"""
    
    def __init__(self):
        self.itens = []
        self.totais = {
            'total_mercadoria_brl': 0.0,
            'total_impostos': 0.0,
            'peso_liquido_total': 0.0
        }

    def parse_pdf(self, file_bytes):
        """Processa o PDF carregado"""
        full_text = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        # 1. Separar por Itens usando o marcador explícito da DUIMP
        # Padrão: "ITENS DA DUIMP-00001", "ITENS DA DUIMP-00002", etc.
        chunks = re.split(r'(ITENS DA DUIMP-\d+)', full_text)
        
        # O split cria uma lista onde [marcador, conteudo, marcador, conteudo...]
        # Vamos iterar pulando de 2 em 2
        for i in range(1, len(chunks), 2):
            header = chunks[i] # Ex: ITENS DA DUIMP-00001
            content = chunks[i+1] if i+1 < len(chunks) else ""
            
            # Extrair número do item do cabeçalho
            num_item = re.search(r'(\d+)', header).group(1)
            
            # Processar o conteúdo do item
            item_data = self._process_item(content, int(num_item))
            if item_data:
                self.itens.append(item_data)
        
        self._calcular_totais_gerais()
        return pd.DataFrame(self.itens)

    def _process_item(self, text, item_num):
        """Extrai dados de um único item"""
        try:
            dados = {
                'Item': item_num,
                'Código Produto': '',
                'NCM': '',
                'Descrição': '',
                'Part Number': '',
                'Qtd. Comercial': 0.0,
                'Peso Líquido (KG)': 0.0,
                'Valor Unit. (EUR)': 0.0,
                'Valor Total (EUR)': 0.0,
                'Valor Total (BRL)': 0.0,
                'Frete (BRL)': 0.0,
                'Seguro (BRL)': 0.0,
                'Valor Aduaneiro (BRL)': 0.0,
                
                # Impostos
                'II Base (BRL)': 0.0, 'II Alíq. (%)': 0.0, 'II Valor (BRL)': 0.0,
                'IPI Base (BRL)': 0.0, 'IPI Alíq. (%)': 0.0, 'IPI Valor (BRL)': 0.0,
                'PIS Base (BRL)': 0.0, 'PIS Alíq. (%)': 0.0, 'PIS Valor (BRL)': 0.0,
                'COFINS Base (BRL)': 0.0, 'COFINS Alíq. (%)': 0.0, 'COFINS Valor (BRL)': 0.0,
            }

            # --- Extração de Cabeçalho e Descrição ---
            
            # NCM e Código Produto (geralmente nas primeiras linhas do bloco)
            # Procura por: NCM [quebra] 8302.10.00
            ncm_match = re.search(r'NCM\s*\n?\s*(\d{4}\.\d{2}\.\d{2})', text)
            if ncm_match: dados['NCM'] = ncm_match.group(1)
            
            # Descrição e Part Number
            desc_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n(.*?)\n(?:DESCRICAO|MARCA)', text, re.DOTALL)
            if desc_match: dados['Descrição'] = desc_match.group(1).replace('\n', ' ').strip()
            
            part_match = re.search(r'Código interno\s*\n?([0-9\.]+)', text)
            if part_match: dados['Part Number'] = part_match.group(1)

            # --- Valores e Quantidades ---
            
            dados['Qtd. Comercial'] = self._get_value(r'Qtde Unid\. Comercial\s*\n?\s*([\d\.,]+)', text)
            dados['Peso Líquido (KG)'] = self._get_value(r'Peso Líquido \(KG\)\s*\n?\s*([\d\.,]+)', text)
            
            # Valores Monetários (Nota: O PDF tem quebras de linha estranhas nos valores)
            dados['Valor Unit. (EUR)'] = self._get_value(r'Valor Unit Cond Venda\s*([\d\.,]+)', text)
            dados['Valor Total (EUR)'] = self._get_value(r'Valor Tot\. Cond Venda\s*\n?\s*([\d\.,]+)', text)
            dados['Valor Total (BRL)'] = self._get_value(r'Vlr Cond Venda \(R\$\)\s*\n?\s*([\d\.,]+)', text)
            
            # Se não achou BRL direto, tenta procurar "Local Embarque (R$)" que é similar ao FOB
            if dados['Valor Total (BRL)'] == 0:
                dados['Valor Total (BRL)'] = self._get_value(r'Local Embarque \(R\$\)\s*([\d\.,]+)', text)

            dados['Frete (BRL)'] = self._get_value(r'Frete Internac\. \(R\$\)\s*\n?\s*([\d\.,]+)', text)
            dados['Seguro (BRL)'] = self._get_value(r'Seguro Internac\. \(R\$\)\s*\n?\s*([\d\.,]+)', text)
            
            # Valor Aduaneiro costuma ser: Local Aduaneiro (R$)
            dados['Valor Aduaneiro (BRL)'] = self._get_value(r'Local Aduaneiro \(R\$\)\s*([\d\.,]+)', text)

            # --- Extração de Impostos por Blocos ---
            # Recortamos o texto para garantir que pegamos a base/alíquota do imposto CERTO
            
            # II
            bloco_ii = self._extract_block(text, "CALCULOS DOS TRIBUTOS - MERCADORIA", "IPI")
            if not bloco_ii: bloco_ii = self._extract_block(text, "II", "IPI") # Fallback
            dados['II Base (BRL)'] = self._get_value(r'Base de Cálculo \(R\$\)\s*\n?\s*([\d\.,]+)', bloco_ii)
            dados['II Alíq. (%)'] = self._get_value(r'% Alíquota\s*\n?\s*([\d\.,]+)', bloco_ii)
            dados['II Valor (BRL)'] = self._get_value(r'Valor A Recolher \(R\$\)\s*\n?\s*([\d\.,]+)', bloco_ii)

            # IPI
            bloco_ipi = self._extract_block(text, "IPI", "PIS")
            dados['IPI Base (BRL)'] = self._get_value(r'Base de Cálculo \(R\$\)\s*\n?\s*([\d\.,]+)', bloco_ipi)
            dados['IPI Alíq. (%)'] = self._get_value(r'% Alíquota\s*\n?\s*([\d\.,]+)', bloco_ipi)
            dados['IPI Valor (BRL)'] = self._get_value(r'Valor A Recolher \(R\$\)\s*\n?\s*([\d\.,]+)', bloco_ipi)

            # PIS
            bloco_pis = self._extract_block(text, "PIS", "COFINS")
            dados['PIS Base (BRL)'] = self._get_value(r'Base de Cálculo \(R\$\)\s*\n?\s*([\d\.,]+)', bloco_pis)
            dados['PIS Alíq. (%)'] = self._get_value(r'% Alíquota\s*\n?\s*([\d\.,]+)', bloco_pis)
            dados['PIS Valor (BRL)'] = self._get_value(r'Valor A Recolher \(R\$\)\s*\n?\s*([\d\.,]+)', bloco_pis)

            # COFINS
            bloco_cofins = self._extract_block(text, "COFINS", "INFORMAÇÕES DO ICMS")
            dados['COFINS Base (BRL)'] = self._get_value(r'Base de Cálculo \(R\$\)\s*\n?\s*([\d\.,]+)', bloco_cofins)
            dados['COFINS Alíq. (%)'] = self._get_value(r'% Alíquota\s*\n?\s*([\d\.,]+)', bloco_cofins)
            dados['COFINS Valor (BRL)'] = self._get_value(r'Valor A Recolher \(R\$\)\s*\n?\s*([\d\.,]+)', bloco_cofins)

            return dados

        except Exception as e:
            st.error(f"Erro ao processar item {item_num}: {e}")
            return None

    def _extract_block(self, text, start_marker, end_marker):
        """Extrai texto entre dois marcadores"""
        pattern = re.escape(start_marker) + r'(.*?)' + re.escape(end_marker)
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        return ""

    def _get_value(self, regex, text):
        """Busca valor numérico em texto e converte para float"""
        if not text: return 0.0
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            val_str = match.group(1)
            # Padrão brasileiro: remove ponto (milhar), troca vírgula por ponto (decimal)
            val_clean = val_str.replace('.', '').replace(',', '.')
            try:
                return float(val_clean)
            except:
                return 0.0
        return 0.0

    def _calcular_totais_gerais(self):
        for item in self.itens:
            self.totais['total_mercadoria_brl'] += item['Valor Total (BRL)']
            self.totais['peso_liquido_total'] += item['Peso Líquido (KG)']
            self.totais['total_impostos'] += (
                item['II Valor (BRL)'] + item['IPI Valor (BRL)'] + 
                item['PIS Valor (BRL)'] + item['COFINS Valor (BRL)']
            )

def main():
    st.markdown('<div class="main-header">📦 Extrator de DUIMP (Padrão APP2)</div>', unsafe_allow_html=True)
    
    st.info("Este aplicativo foi ajustado especificamente para o layout 'ITENS DA DUIMP' conforme o arquivo APP2.pdf")

    uploaded_file = st.file_uploader("Arraste seu PDF aqui", type="pdf")

    if uploaded_file:
        with st.spinner('Lendo e extraindo dados...'):
            parser = DuimpParser()
            df = parser.parse_pdf(uploaded_file.getvalue())

            if not df.empty:
                # --- Seção de Totais (KPIs) ---
                kpi1, kpi2, kpi3 = st.columns(3)
                totais = parser.totais
                
                kpi1.markdown(f"""
                <div class="card">
                    <div class="metric-label">Total Mercadoria (BRL)</div>
                    <div class="metric-value">R$ {totais['total_mercadoria_brl']:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
                kpi2.markdown(f"""
                <div class="card">
                    <div class="metric-label">Total Impostos (II+IPI+PIS+COFINS)</div>
                    <div class="metric-value">R$ {totais['total_impostos']:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)

                kpi3.markdown(f"""
                <div class="card">
                    <div class="metric-label">Peso Líquido Total</div>
                    <div class="metric-value">{totais['peso_liquido_total']:,.2f} kg</div>
                </div>
                """, unsafe_allow_html=True)

                # --- Tabela Detalhada ---
                st.subheader("📋 Detalhamento por Item")
                
                # Formatar colunas para exibição (R$ e %)
                df_display = df.copy()
                cols_monetarias = [c for c in df.columns if '(BRL)' in c or '(EUR)' in c]
                cols_percentuais = [c for c in df.columns if '(%)' in c]
                
                for c in cols_monetarias:
                    df_display[c] = df_display[c].apply(lambda x: f"{x:,.2f}")
                for c in cols_percentuais:
                    df_display[c] = df_display[c].apply(lambda x: f"{x:,.2f}%")

                st.dataframe(
                    df_display,
                    column_config={
                        "Item": st.column_config.NumberColumn("Item", format="%d"),
                    },
                    use_container_width=True,
                    height=500
                )

                # --- Exportação ---
                st.subheader("💾 Download")
                col_csv, col_excel = st.columns(2)
                
                # CSV
                csv = df.to_csv(sep=';', decimal=',', index=False).encode('utf-8-sig')
                col_csv.download_button(
                    label="📥 Baixar CSV (Excel Brasileiro)",
                    data=csv,
                    file_name="extrato_duimp_app2.csv",
                    mime="text/csv"
                )
                
                # Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='DUIMP')
                
                col_excel.download_button(
                    label="📊 Baixar Excel (.xlsx)",
                    data=buffer.getvalue(),
                    file_name="extrato_duimp_app2.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                st.warning("Nenhum item encontrado. Verifique se o PDF está no formato DUIMP correto.")

if __name__ == "__main__":
    main()
