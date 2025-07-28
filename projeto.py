import streamlit as st
import pandas as pd

def processar_arquivo(arquivo, padroes):
    """
    Processa o arquivo TXT removendo linhas que contêm os padrões especificados
    """
    linhas_processadas = []
    try:
        # Lê o arquivo linha por linha
        for linha in arquivo:
            linha_decodificada = linha.decode('utf-8').strip()
            
            # Verifica se a linha contém algum dos padrões indesejados
            if not any(padrao in linha_decodificada for padrao in padroes):
                linhas_processadas.append(linha_decodificada)
        
        return "\n".join(linhas_processadas)
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return None

def main():
    st.title("Processador de Arquivos TXT")
    st.markdown("""
    Este aplicativo permite importar um arquivo TXT e remover linhas indesejadas.
    """)
    
    # Padrões padrão para remoção
    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
    
    # Upload do arquivo
    arquivo = st.file_uploader("Carregue seu arquivo TXT", type=['txt'])
    
    # Opção para adicionar mais padrões
    with st.expander("Opções avançadas"):
        padroes_adicionais = st.text_input(
            "Adicionar mais padrões para remoção (separados por vírgula)",
            help="Exemplo: padrão1, padrão2, padrão3"
        )
        
        if padroes_adicionais:
            padroes = padroes_default + [p.strip() for p in padroes_adicionais.split(",")]
        else:
            padroes = padroes_default
    
    if arquivo is not None:
        st.success("Arquivo carregado com sucesso!")
        
        # Processa o arquivo
        resultado = processar_arquivo(arquivo, padroes)
        
        if resultado:
            # Mostra prévia do resultado
            st.subheader("Prévia do Resultado")
            st.text_area("Conteúdo processado", resultado, height=300)
            
            # Cria um botão para download
            st.download_button(
                label="Baixar arquivo processado",
                data=resultado,
                file_name="arquivo_processado.txt",
                mime="text/plain"
            )
            
            # Mostra estatísticas
            linhas_originais = len(arquivo.getvalue().decode('utf-8').split('\n'))
            linhas_processadas = len(resultado.split('\n'))
            linhas_removidas = linhas_originais - linhas_processadas
            
            st.info(f"""
            **Estatísticas:**
            - Linhas originais: {linhas_originais}
            - Linhas processadas: {linhas_processadas}
            - Linhas removidas: {linhas_removidas}
            """)

if __name__ == "__main__":
    main()
