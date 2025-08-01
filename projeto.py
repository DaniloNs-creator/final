import streamlit as st
import chardet
from io import BytesIO

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

def main():
    st.set_page_config(page_title="Processador TXT", page_icon="📄")
    st.title("📄 Processador de Arquivos TXT")
    st.markdown("""
    Remova linhas indesejadas de arquivos TXT. Carregue seu arquivo e defina os padrões a serem removidos.
    """)

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

if __name__ == "__main__":
    main()
