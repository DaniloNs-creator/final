import streamlit as st
import chardet
from io import BytesIO
import pandas as pd
from datetime import datetime

# --- Funções do Processador de TXT (Original) ---

def detectar_encoding(conteudo):
    """Detecta o encoding do conteúdo do arquivo"""
    resultado = chardet.detect(conteudo)
    return resultado['encoding']

def processar_arquivo(conteudo, padroes):
    """
    Processa o conteúdo do arquivo removendo linhas indesejadas e realizando substituições
    """
    try:
        substituicoes = {
            "IMPOSTO IMPORTACAO": "IMP IMPORT",
            "TAXA SICOMEX": "TX SISCOMEX",
            "FRETE INTERNACIONAL": "FRET INTER",
            "SEGURO INTERNACIONAL": "SEG INTERN"
        }
        encoding = detectar_encoding(conteudo)
        try:
            texto = conteudo.decode(encoding)
        except UnicodeDecodeError:
            texto = conteudo.decode('latin-1')
        
        linhas = texto.splitlines()
        linhas_processadas = []
        
        for linha in linhas:
            linha = linha.strip()
            if not any(padrao in linha for padrao in padroes):
                for original, substituto in substituicoes.items():
                    linha = linha.replace(original, substituto)
                linhas_processadas.append(linha)
        
        return "\n".join(linhas_processadas), len(linhas)
    
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        return None, 0

# --- Funções do Gerador EFD-Reinf (Novo) ---

def gerar_arquivo_reinf(notas_fiscais, competencia):
    """
    Gera o conteúdo do arquivo EFD-Reinf com base nas notas fiscais lançadas.
    Formato simplificado para R-2010 e R-4020.
    """
    if not notas_fiscais:
        return ""

    # Formata a competência para AAAA-MM
    competencia_fmt = competencia.strftime('%Y-%m')
    
    # Linhas do arquivo Reinf
    linhas_reinf = []

    # Exemplo de Bloco de Abertura (simplificado)
    linhas_reinf.append(f"|R-1000|1|{competencia_fmt}|||||||||||||||")
    
    for nota in notas_fiscais:
        # Formatação de valores para o padrão brasileiro (vírgula decimal)
        valor_bruto_fmt = f"{nota['valor_bruto']:.2f}".replace('.', ',')
        base_ret_fmt = f"{nota['base_retencao']:.2f}".replace('.', ',')
        valor_ret_fmt = f"{nota['valor_retido_inss']:.2f}".replace('.', ',')
        valor_irrf_fmt = f"{nota['valor_irrf']:.2f}".replace('.', ',')
        
        # Data da emissão no formato DDMMAAAA
        data_emissao_fmt = nota['data_emissao'].strftime('%d%m%Y')
        
        # === Registro R-2010 (Serviços Tomados) ===
        # Leiaute simplificado: |ID|CNPJ Prestador|Valor Bruto|Base INSS|Valor Retido INSS|Tipo de Serviço|
        # O '1' no final indica o tipo de serviço (ex: 1 - Limpeza) - simplificação
        linhas_reinf.append(
            f"|R-2010|{nota['cnpj_prestador']}|{nota['num_nota']}|{data_emissao_fmt}|{valor_bruto_fmt}|"
            f"{base_ret_fmt}|{valor_ret_fmt}|1|||"
        )
        
        # === Registro R-4020 (Pagamentos a Pessoa Jurídica) ===
        # Leiaute simplificado: |ID|CNPJ Beneficiário|Valor Bruto|Valor Retido IRRF|Natureza Rendimento|
        # 15051 é um código comum de natureza de rendimento - simplificação
        linhas_reinf.append(
            f"|R-4020|{nota['cnpj_prestador']}|{valor_bruto_fmt}|0,00|{valor_irrf_fmt}|0,00|0,00|15051||"
        )
        
    # Exemplo de Bloco de Fechamento (simplificado)
    linhas_reinf.append("|R-9999|1|") # 1 = Existem informações no bloco
    
    return "\n".join(linhas_reinf)


def main():
    st.set_page_config(page_title="Ferramentas Fiscais", page_icon="📄", layout="wide")
    st.title("⚙️ Ferramentas Fiscais e de Texto")

    # Inicializa o estado da sessão para armazenar as notas
    if 'notas_fiscais' not in st.session_state:
        st.session_state.notas_fiscais = []

    tab1, tab2 = st.tabs(["📄 Processador de TXT", " fiscais de Serviço Tomado (EFD-Reinf)"])

    # --- ABA 1: PROCESSADOR DE TXT ---
    with tab1:
        st.header("Remova linhas e substitua texto em arquivos TXT")
        st.markdown("Carregue seu arquivo e defina os padrões a serem removidos ou substituídos.")

        padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
        arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'], key="uploader_txt")
        
        with st.expander("⚙️ Configurações avançadas de remoção"):
            padroes_adicionais = st.text_input(
                "Padrões adicionais para remoção (separados por vírgula)",
                help="Exemplo: padrão1, padrão2, padrão3"
            )
            padroes = padroes_default + [p.strip() for p in padroes_adicionais.split(",") if p.strip()] if padroes_adicionais else padroes_default

        if arquivo is not None:
            try:
                conteudo = arquivo.read()
                resultado, total_linhas = processar_arquivo(conteudo, padroes)
                
                if resultado is not None:
                    linhas_processadas = len(resultado.splitlines())
                    st.success(f"""
                    **Processamento concluído!** ✔️ Linhas originais: {total_linhas}  
                    ✔️ Linhas processadas: {linhas_processadas}  
                    ✔️ Linhas removidas: {total_linhas - linhas_processadas}
                    """)
                    st.text_area("Conteúdo processado", resultado, height=300, key="resultado_txt")
                    buffer = BytesIO()
                    buffer.write(resultado.encode('utf-8'))
                    buffer.seek(0)
                    st.download_button(
                        label="⬇️ Baixar arquivo TXT processado",
                        data=buffer,
                        file_name=f"processado_{arquivo.name}",
                        mime="text/plain"
                    )
            except Exception as e:
                st.error(f"Erro inesperado: {str(e)}")
                st.info("Tente novamente ou verifique o arquivo.")

    # --- ABA 2: GERADOR EFD-REINF ---
    with tab2:
        st.header("Lançamento de Notas Fiscais de Serviço Tomado (R-2010 / R-4020)")
        st.markdown("Preencha os dados da nota fiscal e adicione à lista para gerar o arquivo da EFD-Reinf.")

        st.warning("""
        **Atenção:** Este é um gerador **simplificado** para fins de demonstração. 
        O leiaute da EFD-Reinf possui muito mais campos e regras. 
        O arquivo gerado deve ser **validado por um profissional de contabilidade** e pelo PVA (Programa Validador e Assinador) da Receita Federal.
        """)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📝 Lançar Nova Nota Fiscal")
            with st.form("form_nota_fiscal", clear_on_submit=True):
                competencia = st.date_input(
                    "Competência (Mês/Ano)", 
                    value=datetime.now(),
                    format="MM/YYYY",
                    help="Mês e ano de referência para a apuração."
                )
                cnpj_prestador = st.text_input("CNPJ do Prestador de Serviço", "00.000.000/0000-00")
                num_nota = st.text_input("Número da Nota Fiscal")
                data_emissao = st.date_input("Data de Emissão da Nota")
                valor_bruto = st.number_input("Valor Bruto da Nota (R$)", min_value=0.0, format="%.2f")
                base_retencao = st.number_input("Base de Retenção do INSS (R$)", min_value=0.0, format="%.2f")
                valor_retido_inss = st.number_input("Valor Retido do INSS (11%) (R$)", min_value=0.0, format="%.2f")
                valor_irrf = st.number_input("Valor Retido de IRRF (R$)", min_value=0.0, format="%.2f")
                
                submitted = st.form_submit_button("➕ Adicionar Nota à Lista")
                if submitted:
                    nova_nota = {
                        "Competência": competencia.strftime('%m/%Y'),
                        "CNPJ Prestador": cnpj_prestador,
                        "Nº Nota": num_nota,
                        "Data Emissão": data_emissao.strftime('%d/%m/%Y'),
                        "Valor Bruto (R$)": valor_bruto,
                        # Dados internos para o cálculo
                        "data_emissao": data_emissao,
                        "valor_bruto": valor_bruto,
                        "base_retencao": base_retencao,
                        "valor_retido_inss": valor_retido_inss,
                        "valor_irrf": valor_irrf,
                        "cnpj_prestador": cnpj_prestador,
                        "num_nota": num_nota
                    }
                    st.session_state.notas_fiscais.append(nova_nota)
                    st.success(f"Nota fiscal nº {num_nota} adicionada!")

        with col2:
            st.subheader("📋 Notas Lançadas na Sessão Atual")
            if not st.session_state.notas_fiscais:
                st.info("Nenhuma nota fiscal foi lançada ainda.")
            else:
                # Prepara um DataFrame para exibição amigável
                df_display = pd.DataFrame(st.session_state.notas_fiscais)[
                    ["Competência", "CNPJ Prestador", "Nº Nota", "Data Emissão", "Valor Bruto (R$)"]
                ]
                st.dataframe(df_display, use_container_width=True)

                if st.button("🗑️ Limpar todas as notas"):
                    st.session_state.notas_fiscais = []
                    st.rerun()

                st.subheader("⬇️ Gerar Arquivo EFD-Reinf")
                # Usa a competência da primeira nota lançada como referência para o arquivo
                competencia_geracao = st.session_state.notas_fiscais[0]['data_emissao']
                
                conteudo_reinf = gerar_arquivo_reinf(st.session_state.notas_fiscais, competencia_geracao)
                
                st.download_button(
                    label="**Clique aqui para Baixar o Arquivo EFD-Reinf (.txt)**",
                    data=conteudo_reinf.encode('ascii', 'ignore'), # Reinf usa codificação ASCII
                    file_name=f"EFD_REINF_{competencia_geracao.strftime('%Y%m')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
                with st.expander("👁️ Ver prévia do arquivo gerado"):
                    st.text(conteudo_reinf)

if __name__ == "__main__":
    main()
