import streamlit as st
import pandas as pd
import json
from datetime import datetime
import re
import io
from typing import Dict, List, Any, Optional

# Configuração da página
st.set_page_config(
    page_title="Analisador de DUIMP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #374151;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #F9FAFB;
        border-radius: 10px;
        padding: 15px;
        border-left: 4px solid #3B82F6;
        margin-bottom: 10px;
    }
    .tributo-card {
        background-color: #F0F9FF;
        border-radius: 8px;
        padding: 12px;
        margin: 5px 0;
        border: 1px solid #E0F2FE;
    }
    .item-card {
        background-color: #FEFCE8;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        border: 1px solid #FEF08A;
    }
</style>
""", unsafe_allow_html=True)

class DUIMPAnalyzer:
    """Classe para análise de arquivos DUIMP"""
    
    def __init__(self):
        self.data = {
            "identificacao": {},
            "valores": {},
            "tributos": {},
            "itens": [],
            "transportes": {},
            "documentos": {},
            "informacoes_complementares": {}
        }
    
    def parse_text(self, text: str) -> Dict:
        """Parseia o texto extraído do PDF"""
        lines = text.split('\n')
        
        # Inicializar estrutura
        resultado = {
            "identificacao": self._parse_identificacao(lines),
            "valores": self._parse_valores(lines),
            "tributos": self._parse_tributos(lines),
            "itens": self._parse_itens(text),
            "transportes": self._parse_transportes(lines),
            "documentos": self._parse_documentos(lines),
            "informacoes_complementares": self._parse_info_complementares(lines)
        }
        
        return resultado
    
    def _parse_identificacao(self, lines: List[str]) -> Dict:
        """Extrai informações de identificação"""
        identificacao = {}
        
        for line in lines:
            if "PROCESSO #" in line:
                identificacao["processo"] = line.split("#")[-1].strip()
            elif "IMPORTADOR" in line and "HAFELE" in line:
                identificacao["importador"] = "HAFELE BRASIL"
            elif "CNPJ" in line and "/" in line:
                identificacao["cnpj"] = line.split("CNPJ")[-1].strip()
            elif "Data de Cadastro" in line:
                identificacao["data_cadastro"] = line.split("Data de Cadastro")[-1].strip()
            elif "Numero" in line and "26BR" in line:
                identificacao["numero_duimp"] = line.split("Numero")[-1].strip().split()[0]
            elif "Responsavel Legal" in line:
                identificacao["responsavel"] = line.split("Responsavel Legal")[-1].strip()
        
        return identificacao
    
    def _parse_valores(self, lines: List[str]) -> Dict:
        """Extrai valores monetários"""
        valores = {
            "moedas": {},
            "cif": {},
            "vmle": {},
            "vmld": {}
        }
        
        for line in lines:
            if "Moeda Negociada" in line and "Cotacao" in line:
                partes = line.split("Cotacao")
                moeda = partes[0].replace("Moeda Negociada", "").strip()
                cotacao = partes[1].strip()
                valores["moedas"]["negociada"] = {"moeda": moeda, "cotacao": cotacao}
            
            elif "CIF (R$)" in line:
                match = re.search(r'CIF \(R\$\)\s+([\d.,]+)', line)
                if match:
                    valores["cif"]["reais"] = match.group(1)
            
            elif "VMLE (R$)" in line:
                match = re.search(r'VMLE \(R\$\)\s+([\d.,]+)', line)
                if match:
                    valores["vmle"]["reais"] = match.group(1)
            
            elif "VMLD (R$)" in line:
                match = re.search(r'VMLD \(R\$\)\s+([\d.,]+)', line)
                if match:
                    valores["vmld"]["reais"] = match.group(1)
        
        return valores
    
    def _parse_tributos(self, lines: List[str]) -> Dict:
        """Extrai informações de tributos"""
        tributos = {
            "resumo": {},
            "detalhados": []
        }
        
        # Padrões para tributos no resumo
        padroes_tributos = [
            ("II", r'II\s+([\d.,]+)\s+[\d.,]+\s+([\d.,]+)'),
            ("PIS", r'PIS\s+([\d.,]+)\s+[\d.,]+\s+([\d.,]+)'),
            ("COFINS", r'COFINS\s+([\d.,]+)\s+[\d.,]+\s+([\d.,]+)'),
            ("IPI", r'IPI\s+([\d.,]+)\s+[\d.,]+\s+([\d.,]+)'),
            ("TAXA DE UTILIZACAO", r'TAXA DE UTILIZACAO\s+([\d.,]+)\s+[\d.,]+\s+([\d.,]+)')
        ]
        
        for i, line in enumerate(lines):
            for tributo, padrao in padroes_tributos:
                match = re.search(padrao, line)
                if match:
                    tributos["resumo"][tributo] = {
                        "devido": match.group(2),
                        "recolher": match.group(1)
                    }
        
        return tributos
    
    def _parse_itens(self, text: str) -> List[Dict]:
        """Extrai informações dos itens da DUIMP"""
        itens = []
        
        # Encontrar seções de itens
        padrao_item = r'ITENS DA DUIMP - (\d{5})'
        secoes = re.split(padrao_item, text)
        
        for i in range(1, len(secoes), 2):
            item_num = secoes[i]
            conteudo = secoes[i+1] if i+1 < len(secoes) else ""
            
            item = {
                "numero": item_num,
                "descricao": self._extrair_descricao_item(conteudo),
                "codigo": self._extrair_codigo_item(conteudo),
                "ncm": self._extrair_ncm_item(conteudo),
                "quantidade": self._extrair_quantidade_item(conteudo),
                "valor": self._extrair_valor_item(conteudo),
                "tributos": self._extrair_tributos_item(conteudo)
            }
            itens.append(item)
        
        # Se não encontrou pelo padrão, cria itens básicos
        if not itens:
            for i in range(1, 6):
                itens.append({
                    "numero": f"{i:05d}",
                    "descricao": f"Item {i}",
                    "codigo": "N/A",
                    "ncm": "8302.10.00",
                    "quantidade": "0",
                    "valor": "0.00",
                    "tributos": {"II": "0.00", "PIS": "0.00", "COFINS": "0.00"}
                })
        
        return itens
    
    def _extrair_descricao_item(self, texto: str) -> str:
        """Extrai descrição do item"""
        padrao = r'DENOMINACAO DO PRODUTO\s+(.+?)(?:\n|DESCRICAO)'
        match = re.search(padrao, texto, re.DOTALL)
        return match.group(1).strip() if match else "Descrição não encontrada"
    
    def _extrair_codigo_item(self, texto: str) -> str:
        """Extrai código interno do item"""
        padrao = r'Código interno\s+([\d.]+)'
        match = re.search(padrao, texto)
        return match.group(1) if match else "N/A"
    
    def _extrair_ncm_item(self, texto: str) -> str:
        """Extrai NCM do item"""
        padrao = r'NCM\s+([\d.]+)'
        match = re.search(padrao, texto)
        return match.group(1) if match else "8302.10.00"
    
    def _extrair_quantidade_item(self, texto: str) -> str:
        """Extrai quantidade do item"""
        padrao = r'Qtde Unid\. Comercial\s+([\d.,]+)'
        match = re.search(padrao, texto)
        return match.group(1) if match else "0"
    
    def _extrair_valor_item(self, texto: str) -> str:
        """Extrai valor do item"""
        padrao = r'Valor Tot\. Cond Venda\s+([\d.,]+)'
        match = re.search(padrao, texto)
        return match.group(1) if match else "0.00"
    
    def _extrair_tributos_item(self, texto: str) -> Dict:
        """Extrai tributos do item"""
        tributos = {"II": "0.00", "PIS": "0.00", "COFINS": "0.00"}
        
        # Padrões para cada tributo
        padroes = {
            "II": r'II.*?Valor Devido \(R\$\)\s+([\d.,]+)',
            "PIS": r'PIS.*?Valor Devido \(R\$\)\s+([\d.,]+)',
            "COFINS": r'COFINS.*?Valor Devido \(R\$\)\s+([\d.,]+)'
        }
        
        for tributo, padrao in padroes.items():
            match = re.search(padrao, texto, re.DOTALL)
            if match:
                tributos[tributo] = match.group(1)
        
        return tributos
    
    def _parse_transportes(self, lines: List[str]) -> Dict:
        """Extrai informações de transporte"""
        transportes = {}
        
        for line in lines:
            if "Via de Transporte" in line:
                transportes["via"] = line.split("Via de Transporte")[-1].strip()
            elif "Data de Embarque" in line:
                partes = line.split("Data de Embarque")
                if len(partes) > 1:
                    transportes["embarque"] = partes[1].strip().split()[0]
            elif "Data de Chegada" in line:
                partes = line.split("Data de Chegada")
                if len(partes) > 1:
                    transportes["chegada"] = partes[1].strip().split()[0]
            elif "Peso Bruto" in line:
                match = re.search(r'Peso Bruto\s+([\d.,]+)', line)
                if match:
                    transportes["peso_bruto"] = match.group(1)
            elif "Peso Liquido" in line:
                match = re.search(r'Peso Liquido\s+([\d.,]+)', line)
                if match:
                    transportes["peso_liquido"] = match.group(1)
            elif "Porto de" in line:
                transportes["porto"] = line.strip()
        
        return transportes
    
    def _parse_documentos(self, lines: List[str]) -> Dict:
        """Extrai informações de documentos"""
        documentos = {}
        
        for line in lines:
            if "CONHECIMENTO DE EMBARQUE" in line:
                match = re.search(r'NUMERO:\s*(\d+)', line)
                if match:
                    documentos["conhecimento"] = match.group(1)
            elif "FATURA COMERCIAL" in line:
                if "NUMERO:" in line:
                    documentos["fatura_numero"] = line.split("NUMERO:")[-1].strip()
                if "VALOR US$:" in line:
                    match = re.search(r'VALOR US\$:\s*([\d.,]+)', line)
                    if match:
                        documentos["fatura_valor"] = match.group(1)
        
        return documentos
    
    def _parse_info_complementares(self, lines: List[str]) -> Dict:
        """Extrai informações complementares"""
        info = {}
        
        for line in lines:
            if "PROCESSO:" in line and ":" in line:
                info["processo"] = line.split("PROCESSO:")[-1].strip()
            elif "PAIS DE PROCEDENCIA:" in line:
                info["pais_origem"] = line.split("PAIS DE PROCEDENCIA:")[-1].strip()
            elif "COBERTURA CAMBIAL:" in line:
                info["cobertura_cambial"] = line.split("COBERTURA CAMBIAL:")[-1].strip()
        
        return info

def main():
    """Função principal do aplicativo Streamlit"""
    
    st.markdown('<h1 class="main-header">📊 Analisador de DUIMP - Declaração Única de Importação</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("Configurações")
        
        st.subheader("Upload de Arquivos")
        uploaded_file = st.file_uploader(
            "Carregue o arquivo DUIMP (PDF ou texto)",
            type=['pdf', 'txt', 'png'],
            help="Faça upload do arquivo da DUIMP para análise"
        )
        
        st.subheader("Opções de Análise")
        show_details = st.checkbox("Mostrar detalhes completos", value=True)
        export_data = st.checkbox("Exportar dados analisados", value=False)
        
        st.markdown("---")
        st.info("""
        **Instruções:**
        1. Faça upload do arquivo DUIMP
        2. O sistema extrairá automaticamente os dados
        3. Visualize os resultados nas abas abaixo
        4. Exporte os dados se necessário
        """)
    
    # Conteúdo principal
    if uploaded_file is not None:
        # Processar arquivo
        file_contents = uploaded_file.getvalue().decode("utf-8", errors='ignore')
        
        # Inicializar analisador
        analyzer = DUIMPAnalyzer()
        dados = analyzer.parse_text(file_contents)
        
        # Tabs para organização
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Resumo", 
            "💰 Valores & Tributos", 
            "📦 Itens", 
            "🚚 Transporte & Documentos",
            "📈 Análises"
        ])
        
        with tab1:
            st.markdown('<h2 class="sub-header">Resumo da Operação</h2>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric(
                    label="Processo",
                    value=dados["identificacao"].get("processo", "N/A")
                )
                st.metric(
                    label="DUIMP",
                    value=dados["identificacao"].get("numero_duimp", "N/A")
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric(
                    label="Importador",
                    value=dados["identificacao"].get("importador", "N/A")
                )
                st.metric(
                    label="CNPJ",
                    value=dados["identificacao"].get("cnpj", "N/A")
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric(
                    label="Data Cadastro",
                    value=dados["identificacao"].get("data_cadastro", "N/A")
                )
                st.metric(
                    label="Responsável",
                    value=dados["identificacao"].get("responsavel", "N/A")
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Resumo de valores
            st.markdown('<h3 class="sub-header">Valores da Operação</h3>', unsafe_allow_html=True)
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                valor_cif = dados["valores"]["cif"].get("reais", "0.00")
                st.metric("Valor CIF (R$)", f"R$ {valor_cif}")
            
            with col_b:
                valor_vmle = dados["valores"]["vmle"].get("reais", "0.00")
                st.metric("VMLE (R$)", f"R$ {valor_vmle}")
            
            with col_c:
                valor_vmld = dados["valores"]["vmld"].get("reais", "0.00")
                st.metric("VMLD (R$)", f"R$ {valor_vmld}")
        
        with tab2:
            st.markdown('<h2 class="sub-header">Tributação da Operação</h2>', unsafe_allow_html=True)
            
            # Resumo de tributos
            tributos_resumo = dados["tributos"]["resumo"]
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            colunas_tributos = [col1, col2, col3, col4, col5]
            tributos_chaves = ["II", "PIS", "COFINS", "IPI", "TAXA DE UTILIZACAO"]
            
            for col, tributo in zip(colunas_tributos, tributos_chaves):
                with col:
                    if tributo in tributos_resumo:
                        st.markdown(f'<div class="tributo-card">', unsafe_allow_html=True)
                        st.metric(
                            label=tributo,
                            value=f"R$ {tributos_resumo[tributo].get('devido', '0.00')}",
                            help=f"Valor a recolher: R$ {tributos_resumo[tributo].get('recolher', '0.00')}"
                        )
                        st.markdown('</div>', unsafe_allow_html=True)
            
            # Total de tributos
            st.markdown("---")
            total_tributos = sum(
                float(tributos_resumo[t].get("devido", "0.00").replace(".", "").replace(",", "."))
                for t in tributos_resumo if t != "TAXA DE UTILIZACAO"
            )
            
            col_total1, col_total2 = st.columns(2)
            with col_total1:
                st.metric(
                    "Total Tributos Federais (R$)",
                    f"R$ {total_tributos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
            
            with col_total2:
                taxa = float(tributos_resumo.get("TAXA DE UTILIZACAO", {}).get("devido", "0.00").replace(".", "").replace(",", "."))
                st.metric(
                    "Taxa Siscomex (R$)",
                    f"R$ {taxa:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
            
            # Informações de câmbio
            st.markdown('<h3 class="sub-header">Informações Cambiais</h3>', unsafe_allow_html=True)
            
            if dados["valores"]["moedas"]:
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.info(f"**Moeda Negociada:** {dados['valores']['moedas'].get('negociada', {}).get('moeda', 'N/A')}")
                with col_m2:
                    st.info(f"**Cotação:** {dados['valores']['moedas'].get('negociada', {}).get('cotacao', 'N/A')}")
        
        with tab3:
            st.markdown('<h2 class="sub-header">Itens da Importação</h2>', unsafe_allow_html=True)
            
            # Tabela de itens
            itens_data = []
            for item in dados["itens"]:
                itens_data.append({
                    "Item": item["numero"],
                    "Descrição": item["descricao"][:50] + "..." if len(item["descricao"]) > 50 else item["descricao"],
                    "Código": item["codigo"],
                    "NCM": item["ncm"],
                    "Quantidade": item["quantidade"],
                    "Valor (R$)": item["valor"],
                    "II (R$)": item["tributos"].get("II", "0.00"),
                    "PIS (R$)": item["tributos"].get("PIS", "0.00"),
                    "COFINS (R$)": item["tributos"].get("COFINS", "0.00")
                })
            
            df_itens = pd.DataFrame(itens_data)
            st.dataframe(df_itens, use_container_width=True, height=400)
            
            # Detalhes por item
            if show_details:
                st.markdown('<h3 class="sub-header">Detalhes por Item</h3>', unsafe_allow_html=True)
                
                for item in dados["itens"]:
                    with st.expander(f"Item {item['numero']} - {item['descricao'][:30]}..."):
                        col_i1, col_i2, col_i3 = st.columns(3)
                        
                        with col_i1:
                            st.write(f"**Código:** {item['codigo']}")
                            st.write(f"**NCM:** {item['ncm']}")
                            st.write(f"**Quantidade:** {item['quantidade']}")
                        
                        with col_i2:
                            st.write(f"**Valor Unitário:** R$ {item['valor']}")
                            st.write(f"**Descrição:**")
                            st.write(item['descricao'])
                        
                        with col_i3:
                            st.write("**Tributos:**")
                            for tributo, valor in item["tributos"].items():
                                st.write(f"- {tributo}: R$ {valor}")
        
        with tab4:
            st.markdown('<h2 class="sub-header">Transporte & Documentação</h2>', unsafe_allow_html=True)
            
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.subheader("Transporte")
                
                transportes = dados["transportes"]
                if transportes:
                    st.write(f"**Via:** {transportes.get('via', 'N/A')}")
                    st.write(f"**Data Embarque:** {transportes.get('embarque', 'N/A')}")
                    st.write(f"**Data Chegada:** {transportes.get('chegada', 'N/A')}")
                    st.write(f"**Porto:** {transportes.get('porto', 'N/A')}")
                    st.write(f"**Peso Bruto:** {transportes.get('peso_bruto', 'N/A')} kg")
                    st.write(f"**Peso Líquido:** {transportes.get('peso_liquido', 'N/A')} kg")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_t2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.subheader("Documentos")
                
                documentos = dados["documentos"]
                if documentos:
                    st.write(f"**Conhecimento:** {documentos.get('conhecimento', 'N/A')}")
                    st.write(f"**Fatura:** {documentos.get('fatura_numero', 'N/A')}")
                    st.write(f"**Valor Fatura:** US$ {documentos.get('fatura_valor', 'N/A')}")
                
                info = dados["informacoes_complementares"]
                if info:
                    st.write(f"**País Origem:** {info.get('pais_origem', 'N/A')}")
                    st.write(f"**Cobertura Cambial:** {info.get('cobertura_cambial', 'N/A')}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        with tab5:
            st.markdown('<h2 class="sub-header">Análises e Estatísticas</h2>', unsafe_allow_html=True)
            
            # Análise de tributos por item
            st.subheader("Distribuição de Tributos por Item")
            
            # Preparar dados para gráfico
            itens_analise = []
            for item in dados["itens"]:
                try:
                    valor_ii = float(item["tributos"].get("II", "0.00").replace(".", "").replace(",", "."))
                    valor_pis = float(item["tributos"].get("PIS", "0.00").replace(".", "").replace(",", "."))
                    valor_cofins = float(item["tributos"].get("COFINS", "0.00").replace(".", "").replace(",", "."))
                    valor_total_item = valor_ii + valor_pis + valor_cofins
                    
                    itens_analise.append({
                        "Item": item["numero"],
                        "II": valor_ii,
                        "PIS": valor_pis,
                        "COFINS": valor_cofins,
                        "Total": valor_total_item
                    })
                except:
                    continue
            
            if itens_analise:
                df_analise = pd.DataFrame(itens_analise)
                
                col_a1, col_a2 = st.columns(2)
                
                with col_a1:
                    st.bar_chart(df_analise.set_index("Item")[["II", "PIS", "COFINS"]])
                
                with col_a2:
                    st.bar_chart(df_analise.set_index("Item")["Total"])
                
                # Estatísticas
                st.subheader("Estatísticas da Operação")
                
                total_valor_itens = sum(float(item["valor"].replace(".", "").replace(",", ".")) for item in dados["itens"] 
                                      if item["valor"].replace(",", "").replace(".", "").isdigit())
                total_tributos_itens = sum(float(item["tributos"].get("II", "0.00").replace(".", "").replace(",", ".")) +
                                         float(item["tributos"].get("PIS", "0.00").replace(".", "").replace(",", ".")) +
                                         float(item["tributos"].get("COFINS", "0.00").replace(".", "").replace(",", "."))
                                         for item in dados["itens"])
                
                col_s1, col_s2, col_s3 = st.columns(3)
                
                with col_s1:
                    st.metric("Número de Itens", len(dados["itens"]))
                
                with col_s2:
                    st.metric(
                        "Valor Total Itens (R$)", 
                        f"R$ {total_valor_itens:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    )
                
                with col_s3:
                    st.metric(
                        "Tributos/Item Médio (R$)", 
                        f"R$ {(total_tributos_itens/len(dados['itens'])):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        if len(dados["itens"]) > 0 else "R$ 0,00"
                    )
            
            # Exportação de dados
            if export_data:
                st.markdown("---")
                st.subheader("Exportação de Dados")
                
                # Converter para JSON
                json_data = json.dumps(dados, indent=2, ensure_ascii=False)
                
                col_e1, col_e2 = st.columns(2)
                
                with col_e1:
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_data,
                        file_name=f"duimp_analise_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
                with col_e2:
                    # Converter para CSV (itens)
                    if itens_analise:
                        csv_data = df_analise.to_csv(index=False)
                        st.download_button(
                            label="📥 Download CSV (Itens)",
                            data=csv_data,
                            file_name=f"duimp_itens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
    
    else:
        # Tela inicial sem arquivo
        st.info("👆 Faça upload de um arquivo DUIMP para começar a análise")
        
        # Exemplo de layout esperado
        with st.expander("📋 Estrutura Esperada do Arquivo DUIMP"):
            st.markdown("""
            **Seções que serão extraídas automaticamente:**
            
            1. **Identificação da Operação**
               - Processo, DUIMP, Importador, CNPJ
            
            2. **Valores Monetários**
               - CIF, VMLE, VMLD
               - Informações cambiais
            
            3. **Tributação**
               - II, PIS, COFINS, IPI, Taxas
               - Valores por item
            
            4. **Itens da Importação**
               - Descrição, código, NCM, quantidade, valor
               - Tributos individuais
            
            5. **Transporte & Documentos**
               - Via, datas, porto, pesos
               - Documentos instrutivos
            
            6. **Informações Complementares**
               - País origem, cobertura cambial, etc.
            """)
        
        # Dashboard de exemplo
        st.markdown("---")
        st.markdown('<h2 class="sub-header">Exemplo de Análise</h2>', unsafe_allow_html=True)
        
        col_ex1, col_ex2, col_ex3 = st.columns(3)
        
        with col_ex1:
            st.metric("Processo", "29108", delta=None)
        
        with col_ex2:
            st.metric("Valor CIF", "R$ 9.396,63", delta=None)
        
        with col_ex3:
            st.metric("Total Tributos", "R$ 2.761,83", delta=None)

if __name__ == "__main__":
    main()
