import streamlit as st
import chardet
from io import BytesIO
import pandas as pd
from datetime import datetime
import base64

# Configuração da página
st.set_page_config(
    page_title="Sistema Fiscal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para mostrar a tela inicial
def mostrar_tela_inicial():
    st.markdown("""
    <div style="text-align:center; padding:50px">
        <h1 style="font-size:48px">Bem vindo ao sistema fiscal</h1>
    </div>
    """, unsafe_allow_html=True)

# Processador de Arquivos TXT
def processador_txt():
    st.title("📄 Processador de Arquivos TXT")
    st.markdown("""
    Remova linhas indesejadas de arquivos TXT. Carregue seu arquivo e defina os padrões a serem removidos.
    """)

    def detectar_encoding(conteudo):
        """Detecta o encoding do conteúdo do arquivo"""
        resultado = chardet.detect(conteudo)
        return resultado['encoding']

    def processar_arquivo(conteudo, padroes):
        """
        Processa o conteúdo do arquivo removendo linhas indesejadas e realizando substituições
        """
        try:
            # Dicionário de substituições
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN"
            }
            
            # Detecta o encoding
            encoding = detectar_encoding(conteudo)
            
            # Decodifica o conteúdo
            try:
                texto = conteudo.decode(encoding)
            except UnicodeDecodeError:
                texto = conteudo.decode('latin-1')
            
            # Processa as linhas
            linhas = texto.splitlines()
            linhas_processadas = []
            
            for linha in linhas:
                linha = linha.strip()
                # Verifica se a linha contém algum padrão a ser removido
                if not any(padrao in linha for padrao in padroes):
                    # Aplica as substituições
                    for original, substituto in substituicoes.items():
                        linha = linha.replace(original, substituto)
                    linhas_processadas.append(linha)
            
            return "\n".join(linhas_processadas), len(linhas)
        
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            return None, 0

    # Padrões padrão para remoção
    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
    
    # Upload do arquivo
    arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'])
    
    # Opções avançadas
    with st.expander("⚙️ Configurações avançadas"):
        padroes_adicionais = st.text_input(
            "Padrões adicionais para remoção (separados por vírgula)",
            help="Exemplo: padrão1, padrão2, padrão3"
        )
        
        padroes = padroes_default + [
            p.strip() for p in padroes_adicionais.split(",") 
            if p.strip()
        ] if padroes_adicionais else padroes_default

    if arquivo is not None:
        try:
            # Lê o conteúdo do arquivo
            conteudo = arquivo.read()
            
            # Processa o arquivo
            resultado, total_linhas = processar_arquivo(conteudo, padroes)
            
            if resultado is not None:
                # Mostra estatísticas
                linhas_processadas = len(resultado.splitlines())
                st.success(f"""
                **Processamento concluído!**  
                ✔️ Linhas originais: {total_linhas}  
                ✔️ Linhas processadas: {linhas_processadas}  
                ✔️ Linhas removidas: {total_linhas - linhas_processadas}
                """)

                # Prévia do resultado
                st.subheader("Prévia do resultado")
                st.text_area("Conteúdo processado", resultado, height=300)

                # Botão de download
                buffer = BytesIO()
                buffer.write(resultado.encode('utf-8'))
                buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Baixar arquivo processado",
                    data=buffer,
                    file_name=f"processado_{arquivo.name}",
                    mime="text/plain"
                )
        
        except Exception as e:
            st.error(f"Erro inesperado: {str(e)}")
            st.info("Tente novamente ou verifique o arquivo.")

# Módulo de Lançamentos EFD REINF com R4020 completo
def lancamentos_efd_reinf():
    st.title("📊 Lançamentos EFD REINF")
    st.markdown("""
    Sistema para lançamento de notas fiscais de serviço tomados e geração de arquivos R2010 e R4020 (com IRRF, PIS, COFINS e CSLL).
    """)
    
    # Inicializa o DataFrame na sessão se não existir
    if 'notas_fiscais' not in st.session_state:
        st.session_state.notas_fiscais = pd.DataFrame(columns=[
            'Data', 'CNPJ Tomador', 'CNPJ Prestador', 'Valor Serviço', 
            'Descrição Serviço', 'Código Serviço', 
            'Alíquota INSS', 'Valor INSS',
            'Retém IRRF', 'Alíquota IRRF', 'Valor IRRF',
            'Retém PIS', 'Alíquota PIS', 'Valor PIS',
            'Retém COFINS', 'Alíquota COFINS', 'Valor COFINS',
            'Retém CSLL', 'Alíquota CSLL', 'Valor CSLL'
        ])
    
    # Formulário para adicionar nova nota fiscal
    with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data da Nota Fiscal")
            cnpj_tomador = st.text_input("CNPJ Tomador (14 dígitos)", max_chars=14)
            cnpj_prestador = st.text_input("CNPJ Prestador (14 dígitos)", max_chars=14)
            valor_servico = st.number_input("Valor do Serviço (R$)", min_value=0.0, format="%.2f")
            descricao_servico = st.text_input("Descrição do Serviço")
            codigo_servico = st.text_input("Código do Serviço (LC 116)")
        
        with col2:
            st.subheader("Tributos")
            
            # INSS
            st.markdown("**INSS**")
            aliquota_inss = st.slider("Alíquota INSS (%)", min_value=0.0, max_value=100.0, step=0.01, value=4.5, key='aliquota_inss')
            valor_inss = valor_servico * (aliquota_inss / 100)
            st.info(f"Valor INSS: R$ {valor_inss:.2f}")
            
            # IRRF
            st.markdown("**IRRF**")
            retem_irrf = st.checkbox("Retém IRRF?", value=False, key='retem_irrf')
            aliquota_irrf = st.slider("Alíquota IRRF (%)", min_value=0.0, max_value=100.0, step=0.01, value=1.5, key='aliquota_irrf', disabled=not retem_irrf)
            valor_irrf = valor_servico * (aliquota_irrf / 100) if retem_irrf else 0.0
            st.info(f"Valor IRRF: R$ {valor_irrf:.2f}")
            
            # PIS
            st.markdown("**PIS**")
            retem_pis = st.checkbox("Retém PIS?", value=False, key='retem_pis')
            aliquota_pis = st.slider("Alíquota PIS (%)", min_value=0.0, max_value=100.0, step=0.01, value=0.65, key='aliquota_pis', disabled=not retem_pis)
            valor_pis = valor_servico * (aliquota_pis / 100) if retem_pis else 0.0
            st.info(f"Valor PIS: R$ {valor_pis:.2f}")
            
            # COFINS
            st.markdown("**COFINS**")
            retem_cofins = st.checkbox("Retém COFINS?", value=False, key='retem_cofins')
            aliquota_cofins = st.slider("Alíquota COFINS (%)", min_value=0.0, max_value=100.0, step=0.01, value=3.0, key='aliquota_cofins', disabled=not retem_cofins)
            valor_cofins = valor_servico * (aliquota_cofins / 100) if retem_cofins else 0.0
            st.info(f"Valor COFINS: R$ {valor_cofins:.2f}")
            
            # CSLL
            st.markdown("**CSLL**")
            retem_csll = st.checkbox("Retém CSLL?", value=False, key='retem_csll')
            aliquota_csll = st.slider("Alíquota CSLL (%)", min_value=0.0, max_value=100.0, step=0.01, value=1.0, key='aliquota_csll', disabled=not retem_csll)
            valor_csll = valor_servico * (aliquota_csll / 100) if retem_csll else 0.0
            st.info(f"Valor CSLL: R$ {valor_csll:.2f}")
        
        if st.button("Adicionar Nota Fiscal"):
            nova_nota = {
                'Data': data.strftime('%d/%m/%Y'),
                'CNPJ Tomador': cnpj_tomador,
                'CNPJ Prestador': cnpj_prestador,
                'Valor Serviço': valor_servico,
                'Descrição Serviço': descricao_servico,
                'Código Serviço': codigo_servico,
                'Alíquota INSS': aliquota_inss,
                'Valor INSS': valor_inss,
                'Retém IRRF': retem_irrf,
                'Alíquota IRRF': aliquota_irrf,
                'Valor IRRF': valor_irrf,
                'Retém PIS': retem_pis,
                'Alíquota PIS': aliquota_pis,
                'Valor PIS': valor_pis,
                'Retém COFINS': retem_cofins,
                'Alíquota COFINS': aliquota_cofins,
                'Valor COFINS': valor_cofins,
                'Retém CSLL': retem_csll,
                'Alíquota CSLL': aliquota_csll,
                'Valor CSLL': valor_csll
            }
            
            # Convertendo o dicionário para DataFrame e concatenando
            df_nova_nota = pd.DataFrame([nova_nota])
            st.session_state.notas_fiscais = pd.concat([st.session_state.notas_fiscais, df_nova_nota], ignore_index=True)
            st.success("Nota fiscal adicionada com sucesso!")
    
    # Visualização das notas fiscais cadastradas
    st.subheader("Notas Fiscais Cadastradas")
    if not st.session_state.notas_fiscais.empty:
        # Mostra apenas as colunas principais na visualização
        cols_principais = ['Data', 'CNPJ Tomador', 'CNPJ Prestador', 'Valor Serviço', 'Descrição Serviço', 'Código Serviço']
        st.dataframe(st.session_state.notas_fiscais[cols_principais])
        
        # Opções para editar/excluir notas
        col1, col2 = st.columns(2)
        with col1:
            linha_editar = st.number_input("Número da linha para editar", min_value=0, max_value=len(st.session_state.notas_fiscais)-1, key='linha_editar')
            if st.button("Editar Linha"):
                st.session_state.editando = linha_editar
                
        with col2:
            linha_excluir = st.number_input("Número da linha para excluir", min_value=0, max_value=len(st.session_state.notas_fiscais)-1, key='linha_excluir')
            if st.button("Excluir Linha"):
                st.session_state.notas_fiscais = st.session_state.notas_fiscais.drop(index=linha_excluir).reset_index(drop=True)
                st.success("Linha excluída com sucesso!")
        
        # Formulário de edição
        if 'editando' in st.session_state:
            with st.expander("✏️ Editar Nota Fiscal", expanded=True):
                nota_editar = st.session_state.notas_fiscais.iloc[st.session_state.editando]
                
                col1, col2 = st.columns(2)
                with col1:
                    data_edit = st.date_input("Data", value=datetime.strptime(nota_editar['Data'], '%d/%m/%Y'), key='data_edit')
                    cnpj_tomador_edit = st.text_input("CNPJ Tomador", value=nota_editar['CNPJ Tomador'], key='cnpj_tomador_edit')
                    cnpj_prestador_edit = st.text_input("CNPJ Prestador", value=nota_editar['CNPJ Prestador'], key='cnpj_prestador_edit')
                    valor_servico_edit = st.number_input("Valor do Serviço (R$)", value=float(nota_editar['Valor Serviço']), key='valor_servico_edit')
                    descricao_servico_edit = st.text_input("Descrição do Serviço", value=nota_editar['Descrição Serviço'], key='descricao_servico_edit')
                    codigo_servico_edit = st.text_input("Código do Serviço", value=nota_editar['Código Serviço'], key='codigo_servico_edit')
                
                with col2:
                    st.subheader("Tributos")
                    
                    # INSS
                    st.markdown("**INSS**")
                    aliquota_inss_edit = st.slider("Alíquota INSS (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                value=float(nota_editar['Alíquota INSS']), key='aliquota_inss_edit')
                    valor_inss_edit = valor_servico_edit * (aliquota_inss_edit / 100)
                    st.info(f"Valor INSS: R$ {valor_inss_edit:.2f}")
                    
                    # IRRF
                    st.markdown("**IRRF**")
                    retem_irrf_edit = st.checkbox("Retém IRRF?", value=bool(nota_editar['Retém IRRF']), key='retem_irrf_edit')
                    aliquota_irrf_edit = st.slider("Alíquota IRRF (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                  value=float(nota_editar['Alíquota IRRF']), key='aliquota_irrf_edit', disabled=not retem_irrf_edit)
                    valor_irrf_edit = valor_servico_edit * (aliquota_irrf_edit / 100) if retem_irrf_edit else 0.0
                    st.info(f"Valor IRRF: R$ {valor_irrf_edit:.2f}")
                    
                    # PIS
                    st.markdown("**PIS**")
                    retem_pis_edit = st.checkbox("Retém PIS?", value=bool(nota_editar['Retém PIS']), key='retem_pis_edit')
                    aliquota_pis_edit = st.slider("Alíquota PIS (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                value=float(nota_editar['Alíquota PIS']), key='aliquota_pis_edit', disabled=not retem_pis_edit)
                    valor_pis_edit = valor_servico_edit * (aliquota_pis_edit / 100) if retem_pis_edit else 0.0
                    st.info(f"Valor PIS: R$ {valor_pis_edit:.2f}")
                    
                    # COFINS
                    st.markdown("**COFINS**")
                    retem_cofins_edit = st.checkbox("Retém COFINS?", value=bool(nota_editar['Retém COFINS']), key='retem_cofins_edit')
                    aliquota_cofins_edit = st.slider("Alíquota COFINS (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                    value=float(nota_editar['Alíquota COFINS']), key='aliquota_cofins_edit', disabled=not retem_cofins_edit)
                    valor_cofins_edit = valor_servico_edit * (aliquota_cofins_edit / 100) if retem_cofins_edit else 0.0
                    st.info(f"Valor COFINS: R$ {valor_cofins_edit:.2f}")
                    
                    # CSLL
                    st.markdown("**CSLL**")
                    retem_csll_edit = st.checkbox("Retém CSLL?", value=bool(nota_editar['Retém CSLL']), key='retem_csll_edit')
                    aliquota_csll_edit = st.slider("Alíquota CSLL (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                                  value=float(nota_editar['Alíquota CSLL']), key='aliquota_csll_edit', disabled=not retem_csll_edit)
                    valor_csll_edit = valor_servico_edit * (aliquota_csll_edit / 100) if retem_csll_edit else 0.0
                    st.info(f"Valor CSLL: R$ {valor_csll_edit:.2f}")
                
                if st.button("Salvar Alterações"):
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Data'] = data_edit.strftime('%d/%m/%Y')
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'CNPJ Tomador'] = cnpj_tomador_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'CNPJ Prestador'] = cnpj_prestador_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Valor Serviço'] = valor_servico_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Descrição Serviço'] = descricao_servico_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Código Serviço'] = codigo_servico_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Alíquota INSS'] = aliquota_inss_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Valor INSS'] = valor_inss_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Retém IRRF'] = retem_irrf_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Alíquota IRRF'] = aliquota_irrf_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Valor IRRF'] = valor_irrf_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Retém PIS'] = retem_pis_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Alíquota PIS'] = aliquota_pis_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Valor PIS'] = valor_pis_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Retém COFINS'] = retem_cofins_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Alíquota COFINS'] = aliquota_cofins_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Valor COFINS'] = valor_cofins_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Retém CSLL'] = retem_csll_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Alíquota CSLL'] = aliquota_csll_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Valor CSLL'] = valor_csll_edit
                    
                    del st.session_state.editando
                    st.success("Alterações salvas com sucesso!")
    else:
        st.warning("Nenhuma nota fiscal cadastrada ainda.")
    
    # Geração do arquivo EFD REINF
    st.subheader("Gerar Arquivo EFD REINF")
    
    if st.button("🔄 Gerar Arquivo para Entrega (R2010 e R4020)"):
        if st.session_state.notas_fiscais.empty:
            st.error("Nenhuma nota fiscal cadastrada para gerar o arquivo.")
        else:
            # Simulação da geração do arquivo (em uma aplicação real, seria implementado o layout oficial)
            data_geracao = datetime.now().strftime('%Y%m%d%H%M%S')
            nome_arquivo = f"EFD_REINF_{data_geracao}.txt"
            
            # Cabeçalho do arquivo
            conteudo = [
                "|EFDREINF|0100|1|",
                "|0001|1|12345678901234|Empresa Teste|12345678|||A|12345678901|email@empresa.com|",
                "|0100|Fulano de Tal|12345678901|Rua Teste, 123|3100000||99999999|email@contador.com|"
            ]
            
            # Adiciona registros R2010 para cada nota
            for idx, nota in st.session_state.notas_fiscais.iterrows():
                conteudo.append(f"|2010|{idx+1}|{nota['CNPJ Tomador']}|{nota['CNPJ Prestador']}|{nota['Data'].replace('/', '')}|{nota['Código Serviço']}|{nota['Valor Serviço']:.2f}|{nota['Alíquota INSS']:.2f}|{nota['Valor INSS']:.2f}|")
            
            # Adiciona registros R4020 com todos os tributos
            total_inss = st.session_state.notas_fiscais['Valor INSS'].sum()
            total_irrf = st.session_state.notas_fiscais['Valor IRRF'].sum()
            total_pis = st.session_state.notas_fiscais['Valor PIS'].sum()
            total_cofins = st.session_state.notas_fiscais['Valor COFINS'].sum()
            total_csll = st.session_state.notas_fiscais['Valor CSLL'].sum()
            
            conteudo.append(f"|4020|1|{datetime.now().strftime('%Y%m')}|{total_inss:.2f}|{total_irrf:.2f}|{total_pis:.2f}|{total_cofins:.2f}|{total_csll:.2f}|1|")
            
            # Rodapé do arquivo
            conteudo.append("|9001|1|")
            conteudo.append(f"|9900|EFDREINF|{len(conteudo) - 3}|")
            conteudo.append("|9999|7|")
            
            arquivo_final = "\n".join(conteudo)
            
            # Cria o botão de download
            b64 = base64.b64encode(arquivo_final.encode('utf-8')).decode()
            href = f'<a href="data:file/txt;base64,{b64}" download="{nome_arquivo}">⬇️ Baixar Arquivo EFD REINF</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            st.success("Arquivo gerado com sucesso!")
            
            # Resumo dos totais
            st.subheader("Resumo dos Tributos")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total INSS", f"R$ {total_inss:.2f}")
            col2.metric("Total IRRF", f"R$ {total_irrf:.2f}")
            col3.metric("Total PIS", f"R$ {total_pis:.2f}")
            col4.metric("Total COFINS", f"R$ {total_cofins:.2f}")
            col5.metric("Total CSLL", f"R$ {total_csll:.2f}")
            
            # Prévia do arquivo
            st.subheader("Prévia do Arquivo")
            st.text_area("Conteúdo do Arquivo", arquivo_final, height=300)

# Navegação principal
def main():
    # Mostra a tela inicial apenas se nenhum módulo foi selecionado
    if 'modulo_selecionado' not in st.session_state:
        st.session_state.modulo_selecionado = None
    
    if st.session_state.modulo_selecionado is None:
        mostrar_tela_inicial()
    
    st.sidebar.title("Menu de Navegação")
    opcao = st.sidebar.radio("Selecione o módulo:", 
                            ["Início", "Processador de arquivos TXT", "Lançamentos EFD REINF"])
    
    if opcao != "Início":
        st.session_state.modulo_selecionado = opcao
    
    if st.session_state.modulo_selecionado == "Processador de arquivos TXT":
        processador_txt()
    elif st.session_state.modulo_selecionado == "Lançamentos EFD REINF":
        lancamentos_efd_reinf()

if __name__ == "__main__":
    main()
