import requests
import zipfile
import io
import time
from urllib.parse import urlparse
import socket

def baixar_arquivo_ceps(url, tentativas=3, timeout=10):
    """
    Função para baixar o arquivo de CEPs dos Correios com tratamento robusto de erros.
    
    Args:
        url (str): URL do arquivo a ser baixado
        tentativas (int): Número máximo de tentativas
        timeout (int): Tempo máximo de espera em segundos
        
    Returns:
        bytes: Conteúdo do arquivo baixado ou None em caso de falha
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for tentativa in range(tentativas):
        try:
            # Verifica resolução DNS primeiro
            dominio = urlparse(url).netloc
            try:
                socket.gethostbyname(dominio)
            except socket.gaierror as e:
                print(f"Falha na resolução DNS para {dominio} (tentativa {tentativa + 1}): {e}")
                time.sleep(2)
                continue
                
            print(f"Tentando baixar {url} (tentativa {tentativa + 1})")
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            return response.content
            
        except requests.exceptions.RequestException as e:
            print(f"Erro ao baixar o arquivo (tentativa {tentativa + 1}): {e}")
            if tentativa < tentativas - 1:
                time.sleep(2)  # Espera antes de tentar novamente
                
    return None

def extrair_arquivo_zip(conteudo_zip, nome_arquivo=None):
    """
    Extrai conteúdo de um arquivo ZIP baixado.
    
    Args:
        conteudo_zip (bytes): Conteúdo do arquivo ZIP
        nome_arquivo (str): Nome específico do arquivo a extrair (opcional)
        
    Returns:
        str: Conteúdo do arquivo extraído ou None em caso de falha
    """
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as zip_file:
            # Se nenhum nome específico for fornecido, pega o primeiro arquivo
            if nome_arquivo is None:
                nome_arquivo = zip_file.namelist()[0]
                
            with zip_file.open(nome_arquivo) as arquivo:
                return arquivo.read().decode('latin1')
                
    except Exception as e:
        print(f"Erro ao extrair arquivo ZIP: {e}")
        return None

def main():
    # URLs alternativas (caso a principal falhe)
    urls = [
        "https://dados.correios.com.br/public/localidades/faixa_cep_publico.zip",
        "http://dados.correios.com.br/public/localidades/faixa_cep_publico.zip",
        "https://ftp.correios.com.br/public/localidades/faixa_cep_publico.zip"
    ]
    
    conteudo_zip = None
    
    # Tenta cada URL até conseguir baixar
    for url in urls:
        conteudo_zip = baixar_arquivo_ceps(url)
        if conteudo_zip is not None:
            break
            
    if conteudo_zip is None:
        print("Falha ao baixar o arquivo após várias tentativas.")
        return
        
    print("Arquivo baixado com sucesso!")
    
    # Extrai o conteúdo do ZIP
    conteudo = extrair_arquivo_zip(conteudo_zip)
    
    if conteudo:
        print("Arquivo extraído com sucesso!")
        # Aqui você pode processar o conteúdo como necessário
        # Exemplo: salvar em um arquivo ou banco de dados
        with open("faixa_cep.txt", "w", encoding="latin1") as f:
            f.write(conteudo)
        print("Dados salvos em faixa_cep.txt")
    else:
        print("Falha ao extrair o arquivo ZIP.")

if __name__ == "__main__":
    main()
