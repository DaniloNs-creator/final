import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# Configuração inicial do Streamlit
st.set_page_config(page_title="Análise de ECD", layout="wide")
st.title("Análise de Demonstrações Contábeis - ECD")

# Funções para processar o arquivo ECD
def parse_ecd(file_content):
    """Processa o conteúdo do arquivo ECD e extrai os dados relevantes"""
    lines = file_content.split('\n')
    
    # Extrair informações da empresa
    empresa_info = {}
    for line in lines:
        if line.startswith('|0000|'):
            parts = line.split('|')
            empresa_info['nome'] = parts[4]
            empresa_info['cnpj'] = parts[5]
            empresa_info['uf'] = parts[6]
            empresa_info['data_inicio'] = parts[3]
            empresa_info['data_fim'] = parts[4]
            break
    
    # Extrair contas e saldos (bloco I155)
    contas = []
    for line in lines:
        if line.startswith('|I155|'):
            parts = line.split('|')
            conta = parts[2].strip()
            saldo_anterior = float(parts[3].replace(',', '.')) if parts[3].strip() else 0.0
            natureza_anterior = parts[4].strip()
            debitos = float(parts[5].replace(',', '.')) if parts[5].strip() else 0.0
            creditos = float(parts[6].replace(',', '.')) if parts[6].strip() else 0.0
            saldo_final = float(parts[7].replace(',', '.')) if parts[7].strip() else 0.0
            natureza_final = parts[8].strip()
            
            contas.append({
                'conta': conta,
                'saldo_anterior': saldo_anterior,
                'natureza_anterior': natureza_anterior,
                'debitos': debitos,
                'creditos': creditos,
                'saldo_final': saldo_final,
                'natureza_final': natureza_final
            })
    
    # Extrair lançamentos (bloco I200 e I250)
    lancamentos = []
    current_lancamento = None
    for line in lines:
        if line.startswith('|I200|'):
            parts = line.split('|')
            current_lancamento = {
                'numero': parts[2].strip(),
                'data': parts[3].strip(),
                'valor': float(parts[4].replace(',', '.')) if parts[4].strip() else 0.0,
                'tipo': parts[5].strip(),
                'partidas': []
            }
        elif line.startswith('|I250|') and current_lancamento:
            parts = line.split('|')
            current_lancamento['partidas'].append({
                'conta': parts[2].strip(),
                'valor': float(parts[3].replace(',', '.')) if parts[3].strip() else 0.0,
                'natureza': parts[4].strip(),
                'historico': parts[7].strip() if len(parts) > 7 else ''
            })
        elif line.startswith('|I200|') and current_lancamento and current_lancamento['partidas']:
            lancamentos.append(current_lancamento)
            current_lancamento = None
    
    if current_lancamento and current_lancamento['partidas']:
        lancamentos.append(current_lancamento)
    
    return empresa_info, contas, lancamentos

def classificar_conta(conta):
    """Classifica a conta com base no seu código"""
    if not conta:
        return 'Outros'
    
    # Balanço Patrimonial - Ativo
    if conta.startswith('1.') or conta.startswith('1'):
        if conta.startswith(('1.1', '1.1.')):  # Ativo Circulante
            return 'Ativo Circulante'
        elif conta.startswith(('1.2', '1.2.')):  # Ativo Não Circulante
            return 'Ativo Não Circulante'
        else:
            return 'Ativo'
    
    # Balanço Patrimonial - Passivo
    elif conta.startswith('2.') or conta.startswith('2'):
        if conta.startswith(('2.1', '2.1.')):  # Passivo Circulante
            return 'Passivo Circulante'
        elif conta.startswith(('2.2', '2.2.')):  # Passivo Não Circulante
            return 'Passivo Não Circulante'
        elif conta.startswith(('2.3', '2.3.')):  # Patrimônio Líquido
            return 'Patrimônio Líquido'
        else:
            return 'Passivo'
    
    # Demonstração do Resultado
    elif conta.startswith('3.') or conta.startswith('3'):
        return 'Receitas'
    elif conta.startswith('4.') or conta.startswith('4'):
        return 'Despesas'
    elif conta.startswith('5.') or conta.startswith('5'):
        return 'Custos'
    else:
        return 'Outros'

def calcular_saldo_final(contas):
    """Calcula os totais por grupo de contas"""
    grupos = {}
    
    for conta in contas:
        grupo = classificar_conta(conta['conta'])
        saldo = conta['saldo_final'] if conta['natureza_final'] == 'D' else -conta['saldo_final']
        
        if grupo not in grupos:
            grupos[grupo] = 0.0
        grupos[grupo] += saldo
    
    return grupos

def calcular_kpis(grupos):
    """Calcula os KPIs financeiros com base nos grupos de contas"""
    kpis = {}
    
    # Lucro Líquido
    receitas = grupos.get('Receitas', 0)
    despesas = grupos.get('Despesas', 0)
    custos = grupos.get('Custos', 0)
    kpis['Lucro Líquido'] = receitas - despesas - custos
    
    # Margem de Contribuição
    kpis['Margem de Contribuição'] = (receitas - custos) / receitas * 100 if receitas != 0 else 0
    
    # ROE (Return on Equity)
    pl = grupos.get('Patrimônio Líquido', 1)  # Evitar divisão por zero
    kpis['ROE'] = kpis['Lucro Líquido'] / abs(pl) * 100 if pl != 0 else 0
    
    # Liquidez Corrente
    ativo_circulante = grupos.get('Ativo Circulante', 0)
    passivo_circulante = grupos.get('Passivo Circulante', 1)  # Evitar divisão por zero
    kpis['Liquidez Corrente'] = ativo_circulante / passivo_circulante
    
    # Endividamento
    passivo_total = (grupos.get('Passivo Circulante', 0) + 
                     grupos.get('Passivo Não Circulante', 0))
    ativo_total = (grupos.get('Ativo Circulante', 0) + 
                   grupos.get('Ativo Não Circulante', 0))
    kpis['Endividamento'] = passivo_total / ativo_total * 100 if ativo_total != 0 else 0
    
    return kpis

# Interface do Streamlit
uploaded_file = st.file_uploader("Carregar arquivo ECD", type=['txt'])

if uploaded_file is not None:
    # Ler o conteúdo do arquivo
    bytes_data = uploaded_file.getvalue()
    file_content = bytes_data.decode('utf-8')
    
    # Processar o ECD
    empresa_info, contas, lancamentos = parse_ecd(file_content)
    
    # Exibir informações da empresa
    st.subheader("Informações da Empresa")
    col1, col2, col3 = st.columns(3)
    col1.metric("Nome", empresa_info.get('nome', 'Não informado'))
    col2.metric("CNPJ", empresa_info.get('cnpj', 'Não informado'))
    col3.metric("Período", f"{empresa_info.get('data_inicio', '')} a {empresa_info.get('data_fim', '')}")
    
    # Calcular grupos e KPIs
    grupos = calcular_saldo_final(contas)
    kpis = calcular_kpis(grupos)
    
    # Exibir KPIs
    st.subheader("Indicadores Financeiros")
    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Lucro Líquido", f"R$ {kpis['Lucro Líquido']:,.2f}")
    kpi_cols[1].metric("Margem de Contribuição", f"{kpis['Margem de Contribuição']:.2f}%")
    kpi_cols[2].metric("ROE", f"{kpis['ROE']:.2f}%")
    kpi_cols[3].metric("Liquidez Corrente", f"{kpis['Liquidez Corrente']:.2f}")
    
    # Tabs para as demonstrações
    tab1, tab2, tab3, tab4 = st.tabs(["Balancete", "Balanço Patrimonial", "DRE", "Lançamentos"])
    
    with tab1:
        st.subheader("Balancete Contábil")
        df_balancete = pd.DataFrame(contas)
        
        # Ajustar a exibição dos saldos
        df_balancete['Saldo Anterior'] = df_balancete.apply(
            lambda x: x['saldo_anterior'] if x['natureza_anterior'] == 'D' else -x['saldo_anterior'], axis=1)
        df_balancete['Saldo Final'] = df_balancete.apply(
            lambda x: x['saldo_final'] if x['natureza_final'] == 'D' else -x['saldo_final'], axis=1)
        
        # Selecionar e renomear colunas
        df_balancete = df_balancete[['conta', 'Saldo Anterior', 'debitos', 'creditos', 'Saldo Final']]
        df_balancete.columns = ['Conta', 'Saldo Anterior', 'Débitos', 'Créditos', 'Saldo Final']
        
        st.dataframe(df_balancete, height=600, use_container_width=True)
        
        # Opção para exportar
        csv = df_balancete.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')
        st.download_button(
            label="Exportar Balancete (CSV)",
            data=csv,
            file_name=f"balancete_{empresa_info.get('nome', '')}.csv",
            mime='text/csv'
        )
    
    with tab2:
        st.subheader("Balanço Patrimonial")
        
        # Criar DataFrame para o Balanço
        ativo_circulante = grupos.get('Ativo Circulante', 0)
        ativo_nao_circulante = grupos.get('Ativo Não Circulante', 0)
        passivo_circulante = grupos.get('Passivo Circulante', 0)
        passivo_nao_circulante = grupos.get('Passivo Não Circulante', 0)
        patrimonio_liquido = grupos.get('Patrimônio Líquido', 0)
        
        ativo_total = ativo_circulante + ativo_nao_circulante
        passivo_total = passivo_circulante + passivo_nao_circulante + patrimonio_liquido
        
        balanco_data = {
            'Ativo': {
                'Ativo Circulante': ativo_circulante,
                'Ativo Não Circulante': ativo_nao_circulante,
                'Total do Ativo': ativo_total
            },
            'Passivo': {
                'Passivo Circulante': passivo_circulante,
                'Passivo Não Circulante': passivo_nao_circulante,
                'Patrimônio Líquido': patrimonio_liquido,
                'Total do Passivo': passivo_total
            }
        }
        
        df_balanco = pd.DataFrame(balanco_data).fillna(0)
        st.dataframe(df_balanco.style.format("{:,.2f}"), height=300, use_container_width=True)
        
        # Gráfico do Balanço
        st.bar_chart({
            'Ativo': ativo_total,
            'Passivo': passivo_circulante + passivo_nao_circulante,
            'Patrimônio Líquido': patrimonio_liquido
        })
    
    with tab3:
        st.subheader("Demonstração do Resultado do Exercício (DRE)")
        
        # Criar DataFrame para a DRE
        receitas = grupos.get('Receitas', 0)
        custos = grupos.get('Custos', 0)
        despesas = grupos.get('Despesas', 0)
        lucro_bruto = receitas - custos
        lucro_liquido = lucro_bruto - despesas
        
        dre_data = {
            'Descrição': ['Receitas', 'Custos', 'Lucro Bruto', 'Despesas', 'Lucro Líquido'],
            'Valor': [receitas, -custos, lucro_bruto, -despesas, lucro_liquido]
        }
        
        df_dre = pd.DataFrame(dre_data)
        st.dataframe(df_dre.style.format({"Valor": "{:,.2f}"}), height=300, use_container_width=True)
        
        # Gráfico da DRE
        st.bar_chart(df_dre.set_index('Descrição'))
    
    with tab4:
        st.subheader("Lançamentos Contábeis")
        
        # Criar DataFrame para os lançamentos
        lancamentos_data = []
        for lanc in lancamentos:
            for partida in lanc['partidas']:
                lancamentos_data.append({
                    'Data': lanc['data'],
                    'Número': lanc['numero'],
                    'Conta': partida['conta'],
                    'Valor': partida['valor'],
                    'Natureza': partida['natureza'],
                    'Histórico': partida['historico']
                })
        
        df_lancamentos = pd.DataFrame(lancamentos_data)
        
        if not df_lancamentos.empty:
            st.dataframe(df_lancamentos, height=600, use_container_width=True)
            
            # Opção para exportar
            csv = df_lancamentos.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')
            st.download_button(
                label="Exportar Lançamentos (CSV)",
                data=csv,
                file_name=f"lancamentos_{empresa_info.get('nome', '')}.csv",
                mime='text/csv'
            )
        else:
            st.warning("Nenhum lançamento encontrado no arquivo ECD.")

else:
    st.info("Por favor, carregue um arquivo ECD no formato TXT para análise.")
