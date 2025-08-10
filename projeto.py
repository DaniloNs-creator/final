import streamlit as st
import chardet
from io import BytesIO
import pandas as pd
from datetime import datetime
import base64

# Configuração da página
st.set_page_config(
    page_title="FISCAL HÄFALE",
    page_icon="📊",
    layout="wide"
)

# Estilo CSS personalizado
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Função para criar a capa
def mostrar_capa():
    st.markdown("""
    <div style="background-color:#1e3a8a;padding:20px;border-radius:10px;margin-bottom:30px">
        <h1 style="color:white;text-align:center;font-size:48px">FISCAL HÄFALE</h1>
        <p style="color:white;text-align:center;font-size:18px">Sistema de Processamento de Arquivos e Lançamentos Fiscais</p>
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

# Módulo de Lançamentos EFD REINF
def lancamentos_efd_reinf():
    st.title("📊 Lançamentos EFD REINF")
    st.markdown("""
    Sistema para lançamento de notas fiscais de serviço tomados e geração de arquivos R4020 e R2010.
    """)
    
    # Inicializa o DataFrame na sessão se não existir
    if 'notas_fiscais' not in st.session_state:
        st.session_state.notas_fiscais = pd.DataFrame(columns=[
            'Data', 'CNPJ Tomador', 'CNPJ Prestador', 'Valor Serviço', 
            'Descrição Serviço', 'Código Serviço', 'Alíquota', 'Valor INSS'
        ])
    
    # Formulário para adicionar nova nota fiscal
    with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data = st.date_input("Data da Nota Fiscal")
            cnpj_tomador = st.text_input("CNPJ Tomador")
        with col2:
            cnpj_prestador = st.text_input("CNPJ Prestador")
            valor_servico = st.number_input("Valor do Serviço (R$)", min_value=0.0, format="%.2f")
        with col3:
            descricao_servico = st.text_input("Descrição do Serviço")
            codigo_servico = st.text_input("Código do Serviço (LC 116)")
        
        aliquota = st.slider("Alíquota INSS (%)", min_value=0.0, max_value=100.0, step=0.01, value=4.5)
        
        if st.button("Adicionar Nota Fiscal"):
            valor_inss = valor_servico * (aliquota / 100)
            
            nova_nota = {
                'Data': data.strftime('%d/%m/%Y'),
                'CNPJ Tomador': cnpj_tomador,
                'CNPJ Prestador': cnpj_prestador,
                'Valor Serviço': valor_servico,
                'Descrição Serviço': descricao_servico,
                'Código Serviço': codigo_servico,
                'Alíquota': aliquota,
                'Valor INSS': valor_inss
            }
            
            st.session_state.notas_fiscais = st.session_state.notas_fiscais.append(nova_nota, ignore_index=True)
            st.success("Nota fiscal adicionada com sucesso!")
    
    # Visualização das notas fiscais cadastradas
    st.subheader("Notas Fiscais Cadastradas")
    if not st.session_state.notas_fiscais.empty:
        st.dataframe(st.session_state.notas_fiscais)
        
        # Opções para editar/excluir notas
        col1, col2 = st.columns(2)
        with col1:
            linha_editar = st.number_input("Número da linha para editar", min_value=0, max_value=len(st.session_state.notas_fiscais)-1)
            if st.button("Editar Linha"):
                st.session_state.editando = linha_editar
                
        with col2:
            linha_excluir = st.number_input("Número da linha para excluir", min_value=0, max_value=len(st.session_state.notas_fiscais)-1)
            if st.button("Excluir Linha"):
                st.session_state.notas_fiscais = st.session_state.notas_fiscais.drop(index=linha_excluir).reset_index(drop=True)
                st.success("Linha excluída com sucesso!")
        
        # Formulário de edição
        if 'editando' in st.session_state:
            with st.expander("✏️ Editar Nota Fiscal", expanded=True):
                nota_editar = st.session_state.notas_fiscais.iloc[st.session_state.editando]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    data_edit = st.text_input("Data", value=nota_editar['Data'], key='data_edit')
                    cnpj_tomador_edit = st.text_input("CNPJ Tomador", value=nota_editar['CNPJ Tomador'], key='cnpj_tomador_edit')
                with col2:
                    cnpj_prestador_edit = st.text_input("CNPJ Prestador", value=nota_editar['CNPJ Prestador'], key='cnpj_prestador_edit')
                    valor_servico_edit = st.number_input("Valor do Serviço (R$)", value=float(nota_editar['Valor Serviço']), key='valor_servico_edit')
                with col3:
                    descricao_servico_edit = st.text_input("Descrição do Serviço", value=nota_editar['Descrição Serviço'], key='descricao_servico_edit')
                    codigo_servico_edit = st.text_input("Código do Serviço", value=nota_editar['Código Serviço'], key='codigo_servico_edit')
                
                aliquota_edit = st.slider("Alíquota INSS (%)", min_value=0.0, max_value=100.0, step=0.01, 
                                        value=float(nota_editar['Alíquota']), key='aliquota_edit')
                
                if st.button("Salvar Alterações"):
                    valor_inss_edit = valor_servico_edit * (aliquota_edit / 100)
                    
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Data'] = data_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'CNPJ Tomador'] = cnpj_tomador_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'CNPJ Prestador'] = cnpj_prestador_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Valor Serviço'] = valor_servico_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Descrição Serviço'] = descricao_servico_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Código Serviço'] = codigo_servico_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Alíquota'] = aliquota_edit
                    st.session_state.notas_fiscais.at[st.session_state.editando, 'Valor INSS'] = valor_inss_edit
                    
                    del st.session_state.editando
                    st.success("Alterações salvas com sucesso!")
    else:
        st.warning("Nenhuma nota fiscal cadastrada ainda.")
    
    # Geração do arquivo EFD REINF
    st.subheader("Gerar Arquivo EFD REINF")
    
    if st.button("🔄 Gerar Arquivo para Entrega (R4020 e R2010)"):
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
            
            # Adiciona registros R2010
            for idx, nota in st.session_state.notas_fiscais.iterrows():
                conteudo.append(f"|2010|{idx+1}|{nota['CNPJ Tomador']}|{nota['CNPJ Prestador']}|{nota['Data'].replace('/', '')}|{nota['Código Serviço']}|{nota['Valor Serviço']:.2f}|{nota['Alíquota']:.2f}|{nota['Valor INSS']:.2f}|")
            
            # Adiciona registros R4020
            total_inss = st.session_state.notas_fiscais['Valor INSS'].sum()
            conteudo.append(f"|4020|1|{datetime.now().strftime('%Y%m')}|{total_inss:.2f}|1|")
            
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
            st.text_area("Prévia do Arquivo", arquivo_final, height=300)

# Navegação principal
def main():
    mostrar_capa()
    
    st.sidebar.title("Menu de Navegação")
    app_mode = st.sidebar.radio("Selecione o módulo:",
        ["Processador de arquivos TXT", "Lançamentos EFD REINF"])
    
    if app_mode == "Processador de arquivos TXT":
        processador_txt()
    elif app_mode == "Lançamentos EFD REINF":
        lancamentos_efd_reinf()

if __name__ == "__main__":
    main()
