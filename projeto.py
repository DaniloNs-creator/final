import streamlit as st
import pandas as pd
import numpy as np
import pdfplumber
import re
from typing import Dict, List, Optional
import tempfile
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da página
st.set_page_config(
    page_title="Sistema de Análise Häfele (DUIMP/DI)",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1E3A8A; font-weight: bold; margin-bottom: 1rem; }
    .sub-header { font-size: 1.5rem; color: #2563EB; margin-top: 2rem; border-bottom: 2px solid #E5E7EB; }
    .metric-card { background: #F3F4F6; border-radius: 8px; padding: 1rem; border-left: 5px solid #1E3A8A; }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #111827; }
    .metric-label { font-size: 0.9rem; color: #6B7280; }
</style>
""", unsafe_allow_html=True)

class HafelePDFParser:
    """Parser adaptado para layout DUIMP (Novo Padrão)"""
    
    def __init__(self):
        self.documento = {
            'itens': [],
            'totais': {}
        }
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            full_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Extract text mantendo layout aproximado
                    text = page.extract_text(x_tolerance=2, y_tolerance=2)
                    if text:
                        full_text += text + "\n"
            
            # Debug: Salvar texto extraído para análise se necessário
            # with open("debug_text.txt", "w", encoding="utf-8") as f:
            #     f.write(full_text)

            self._process_duimp_structure(full_text)
            return self.documento
            
        except Exception as e:
            logger.error(f"Erro fatal no parsing: {str(e)}")
            st.error(f"Erro ao ler o arquivo: {str(e)}")
            return self.documento

    def _process_duimp_structure(self, text: str):
        """Processa a estrutura baseada em 'ITENS DA DUIMP'"""
        
        # 1. Dividir o texto em blocos de itens
        # O novo PDF separa itens com 'ITENS DA DUIMP-XXXXX' ou similar
        # Vamos usar um split mais genérico que pega o início de cada item
        item_chunks = re.split(r'(?:ITENS DA DUIMP-\d+|Item\s+Integracao)', text)
        
        # O primeiro chunk geralmente é cabeçalho geral, ignoramos ou processamos separadamente
        if len(item_chunks) > 1:
            # Pula o índice 0 (cabeçalho do documento)
            for i, chunk in enumerate(item_chunks[1:], 1):
                item_data = self._parse_single_item(chunk, i)
                if item_data and item_data.get('codigo_produto'): # Só adiciona se tiver produto válido
                    self.documento['itens'].append(item_data)
        
        self._calculate_totals()

    def _parse_single_item(self, text: str, index: int) -> Dict:
        """Extrai dados de um único bloco de texto de item"""
        item = {
            'numero_item': index,
            'ncm': '',
            'codigo_produto': '',
            'codigo_interno': '',
            'nome_produto': '',
            'quantidade': 0.0,
            'valor_total': 0.0,
            'peso_liquido': 0.0,
            # Tributos
            'ii_base': 0.0, 'ii_valor': 0.0, 'ii_aliquota': 0.0,
            'ipi_base': 0.0, 'ipi_valor': 0.0, 'ipi_aliquota': 0.0,
            'pis_base': 0.0, 'pis_valor': 0.0, 'pis_aliquota': 0.0,
            'cofins_base': 0.0, 'cofins_valor': 0.0, 'cofins_aliquota': 0.0
        }

        # --- Identificação ---
        
        # NCM (formato XXXX.XX.XX)
        ncm_match = re.search(r'NCM\s*\n?\s*(\d{4}\.\d{2}\.\d{2})', text)
        if ncm_match: item['ncm'] = ncm_match.group(1)
        
        # Código Produto (Campo sequencial simples)
        cod_prod_match = re.search(r'Codigo Produto\s*\n?\s*(\d+)', text)
        if cod_prod_match: item['codigo_produto'] = cod_prod_match.group(1)

        # Código Interno (Partnumber - ex: 342.79.301)
        # O PDF novo mostra "Código interno" e o valor na linha de baixo ou lado
        cod_int_match = re.search(r'(?:Código interno|Partnumber).*?(\d{3}\.\d{2}\.\d{3})', text, re.IGNORECASE | re.DOTALL)
        if cod_int_match: item['codigo_interno'] = cod_int_match.group(1)

        # Denominação / Descrição
        denom_match = re.search(r'DENOMINACAO DO PRODUTO\s*\n?(.*?)(?:\nDESCRICAO|\nConhecido)', text, re.DOTALL)
        if denom_match:
            item['nome_produto'] = denom_match.group(1).replace('\n', ' ').strip()

        # --- Valores e Quantidades ---
        
        # Quantidade (Qtde Unid. Comercial)
        qtd_match = re.search(r'Qtde Unid\. Comercial\s*\n?\s*([\d\.,]+)', text)
        if qtd_match: item['quantidade'] = self._parse_float(qtd_match.group(1))

        # Peso Líquido
        peso_match = re.search(r'Peso Líquido \(KG\)\s*\n?\s*([\d\.,]+)', text)
        if peso_match: item['peso_liquido'] = self._parse_float(peso_match.group(1))

        # Valor Total (Valor Tot. Cond Venda)
        # No novo PDF parece ser "Valor Tot. Cond Venda" seguido do numero
        valor_match = re.search(r'Valor Tot\. Cond Venda\s*\n?\s*([\d\.,]+)', text)
        if valor_match: item['valor_total'] = self._parse_float(valor_match.group(1))

        # --- Tributos (Lógica Complexa para o novo layout) ---
        # A estratégia aqui é buscar o bloco específico de cada imposto para evitar pegar valores vizinhos
        
        item = self._extract_tax_section(text, item, 'II', ['II', 'Imposto de Importacao'])
        item = self._extract_tax_section(text, item, 'IPI', ['IPI'])
        item = self._extract_tax_section(text, item, 'PIS', ['PIS', 'PIS-IMPORTAÇÃO'])
        item = self._extract_tax_section(text, item, 'COFINS', ['COFINS', 'COFINS-IMPORTAÇÃO'])

        # Total Impostos
        item['total_impostos'] = (item['ii_valor'] + item['ipi_valor'] + item['pis_valor'] + item['cofins_valor'])
        item['valor_final'] = item['valor_total'] + item['total_impostos']

        return item

    def _extract_tax_section(self, text: str, item: Dict, tax_key: str, header_keywords: List[str]) -> Dict:
        """
        Extrai Base, Alíquota e Valor para um imposto específico.
        Usa regex para isolar a seção do imposto dentro do texto do item.
        """
        # Encontra onde começa o bloco do imposto
        start_idx = -1
        for kw in header_keywords:
            match = re.search(rf'\b{kw}\b', text) # \b para palavra exata
            if match:
                start_idx = match.start()
                break
        
        if start_idx == -1: return item

        # O bloco do imposto vai até o próximo grande cabeçalho ou fim do texto
        # Limitamos a busca aos próximos ~800 caracteres para evitar pegar o próximo imposto
        subtext = text[start_idx:start_idx+1500] 

        # Regexes específicas para o formato de tabela do novo PDF
        # Padrão: "Base de Cálculo (R$)" seguido de quebra de linha opcional e número
        
        # Base de Cálculo
        base_match = re.search(r'Base de Cálculo \(R\$\)\s*\n?\s*([\d\.,]+)', subtext)
        if base_match: item[f'{tax_key.lower()}_base'] = self._parse_float(base_match.group(1))

        # Alíquota (Pode ser % Alíquota ou % Alíquota Ad Valorem)
        aliq_match = re.search(r'% Alíquota\s*(?:Ad Valorem)?\s*\n?\s*([\d\.,]+)', subtext)
        if aliq_match: item[f'{tax_key.lower()}_aliquota'] = self._parse_float(aliq_match.group(1))

        # Valor (Pode ser Valor Devido, Valor A Recolher ou Valor Calculado)
        # Prioridade: A Recolher -> Devido -> Calculado
        val_recolher = re.search(r'Valor A Recolher \(R\$\)\s*\n?\s*([\d\.,]+)', subtext)
        val_devido = re.search(r'Valor Devido \(R\$\)\s*\n?\s*([\d\.,]+)', subtext)
        
        if val_recolher:
            item[f'{tax_key.lower()}_valor'] = self._parse_float(val_recolher.group(1))
        elif val_devido:
            item[f'{tax_key.lower()}_valor'] = self._parse_float(val_devido.group(1))

        return item

    def _parse_float(self, value_str: str) -> float:
        if not value_str: return 0.0
        try:
            # Remove pontos de milhar e troca vírgula decimal por ponto
            clean_str = value_str.replace('.', '').replace(',', '.')
            return float(clean_str)
        except ValueError:
            return 0.0

    def _calculate_totals(self):
        totais = {
            'mercadoria': sum(i['valor_total'] for i in self.documento['itens']),
            'impostos': sum(i['total_impostos'] for i in self.documento['itens']),
            'peso': sum(i['peso_liquido'] for i in self.documento['itens']),
            'quantidade': sum(i['quantidade'] for i in self.documento['itens'])
        }
        self.documento['totais'] = totais

def main():
    st.markdown('<h1 class="main-header">🏭 Extrator de Dados Häfele (DUIMP)</h1>', unsafe_allow_html=True)
    
    st.info("ℹ️ Sistema atualizado para suportar o novo layout DUIMP/Siscomex com quebras de itens dinâmicas.")

    uploaded_file = st.file_uploader("Arraste seu PDF aqui", type=['pdf'])

    if uploaded_file:
        # Salvar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            # Processamento
            parser = HafelePDFParser()
            with st.spinner('Lendo e estruturando dados do PDF...'):
                dados = parser.parse_pdf(tmp_path)

            itens = dados.get('itens', [])
            
            if not itens:
                st.warning("⚠️ Nenhum item foi encontrado. Verifique se o PDF é legível ou se o layout mudou novamente.")
                return

            # Criação do DataFrame
            df = pd.DataFrame(itens)
            
            # --- Dashboard ---
            totais = dados['totais']
            
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="metric-card"><div class="metric-value">R$ {totais["mercadoria"]:,.2f}</div><div class="metric-label">Total Mercadoria</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><div class="metric-value">R$ {totais["impostos"]:,.2f}</div><div class="metric-label">Total Impostos</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><div class="metric-value">{totais["peso"]:,.2f} kg</div><div class="metric-label">Peso Líquido</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-card"><div class="metric-value">{len(itens)}</div><div class="metric-label">Itens Extraídos</div></div>', unsafe_allow_html=True)

            st.markdown('<h2 class="sub-header">📊 Tabela Detalhada</h2>', unsafe_allow_html=True)

            # Seleção e renomeação de colunas para exibição
            cols_map = {
                'numero_item': 'Item',
                'codigo_interno': 'Código Interno',
                'nome_produto': 'Produto',
                'ncm': 'NCM',
                'valor_total': 'Valor Merc. (R$)',
                'ii_valor': 'II (R$)',
                'ipi_valor': 'IPI (R$)',
                'pis_valor': 'PIS (R$)',
                'cofins_valor': 'COFINS (R$)',
                'total_impostos': 'Total Imp. (R$)',
                'valor_final': 'Custo Total (R$)'
            }
            
            df_display = df[cols_map.keys()].rename(columns=cols_map)
            
            st.dataframe(
                df_display.style.format(precision=2, thousands=".", decimal=","),
                use_container_width=True,
                height=500
            )

            # Downloads
            csv = df_display.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button(
                "📥 Baixar Relatório em CSV",
                csv,
                "relatorio_hafele_duimp.csv",
                "text/csv"
            )

        except Exception as e:
            st.error(f"Erro no processamento: {e}")
        finally:
            os.unlink(tmp_path)

if __name__ == "__main__":
    main()
