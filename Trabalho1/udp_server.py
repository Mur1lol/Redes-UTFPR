import socket as s
import time as t
import logging as l
import threading as th
import hashlib as h
import os
from colorama import Fore, Style 

# Configurações do servidor
TAM_BUFFER = 1024 
PASTA_ARQUIVOS = "./Files"

# Valores padrões
SERVER_NAME = '127.0.0.1'  
SERVER_PORT = 5000    

# Configuração do logger
def configurar_logger():
    logger = l.getLogger(__name__)
    l.basicConfig(
        filename="server.log",
        encoding="utf-8",
        level=l.INFO,
        format="%(levelname)s - %(asctime)s: %(message)s"
    )
    return logger

# Função para exibir o título do servidor
def titulo():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.MAGENTA)
    print("┌────────────────────┐")
    print("│      SERVIDOR      │")
    print("└────────────────────┘")
    print(Style.RESET_ALL)

# Função para solicitar a porta ao usuário
def solicitar_porta():
    while True:
        try:
            porta_escolhida = int(input(f"Digite a porta do servidor (padrão: {SERVER_PORT}): ") or SERVER_PORT)
            if 1024 <= porta_escolhida <= 65535:
                iniciar_server = True
                break
            else:
                print("A porta deve estar entre 1024 e 65535.")
        except ValueError:
            print("Por favor, insira um número válido.")
    return porta_escolhida, iniciar_server

# Função para enviar um arquivo ou uma parte específica dele
def envio_arquivo(retorno_socket: s.socket, nome_arquivo: str, endereco: tuple, parte: int = None) -> None:
    
    # Verifica se o arquivo solicitado existe.
    caminho_arquivo = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
    if not os.path.exists(caminho_arquivo):
        # Mensagem de erro caso o arquivo não exista
        retorno_socket.sendto("[ERRO] Arquivo não encontrado".encode(), endereco)
        return

    # Segmentação do arquivo em múltiplos pedaços
    num_pacotes = (os.path.getsize(caminho_arquivo) // TAM_BUFFER) + 1
    num_digitos = len(str(num_pacotes))

    if parte is not None and (parte < 0 or parte >= num_pacotes):
        # Mensagem de erro caso o segmento solicitado não exista
        retorno_socket.sendto("[ERRO] Pacote não existe".encode(), endereco)
        return

    if parte is None:
        retorno_socket.sendto(f"OK {num_pacotes} {num_digitos+18+TAM_BUFFER}".encode(), endereco)

    with open(caminho_arquivo, "rb") as arquivo:
        for i in range(num_pacotes):
            data = arquivo.read(TAM_BUFFER)
            if not data:
                break 

            try:
                if parte is None or i == parte:
                    # Cada segmento contém índice, hash MD5 e dados.
                    hash_ = h.md5(data).digest()
                    pacote = f"{i:{'0'}{num_digitos}}".encode() + b" " + hash_ + b" " + data
                    print(f"Enviando pacote {i}/{num_pacotes} para {endereco}")
                    t.sleep(0.01) 
                    retorno_socket.sendto(pacote, endereco)

                    # Aguarda ACK do cliente
                    try:
                        retorno_socket.settimeout(0.1)
                        ack, _ = retorno_socket.recvfrom(1024)
                        if ack != f"ACK {i}".encode():
                            print(f"ACK inválido para pacote {i}")
                    except s.timeout:
                        print(f"Timeout esperando ACK do pacote {i}")

                    if parte is not None:
                        break 
            except Exception as e:
                print(f"Erro ao enviar o pacote {i}: {e}")

    if parte is None:
        t.sleep(0.1)
        print(f"Enviando pacote {i+1}/{num_pacotes} para {endereco}")

        retorno_socket.sendto(b"END", endereco)


def requisicao_arquivo(message_: bytes, addr_: tuple, logger):
    request = message_.decode().split()
    
    #evitar concorrencia de threads
    th.Lock().acquire()

    # Cria um socket adicional com uma porta dinâmica
    retorno_socket = s.socket(s.AF_INET, s.SOCK_DGRAM)
    retorno_socket.bind((SERVER_NAME, 0))  
    porta_aleatoria = retorno_socket.getsockname()[1] 

    logger.info(f"Requisição: '{message_.decode()}', socket criado na porta: {porta_aleatoria}")
    print(f"Requisição: '{message_.decode()}', socket criado na porta: {addr_}")

    if len(request) <= 1:
        # Envia mensagem de erro para requisição inválida
        print(Fore.RED + "[ERRO] Requisição inválida" + Style.RESET_ALL)
        retorno_socket.sendto("[ERRO] Requisição inválida".encode(), addr_)
        return

    if request[0] != "GET":
        # Envia mensagem de erro para método não permitido
        print(Fore.RED + "[ERRO] Método não permitido" + Style.RESET_ALL)
        retorno_socket.sendto("[ERRO] Método não permitido".encode(), addr_)
        return
    
    nome_arquivo = request[1]
    arquivos_separados = nome_arquivo.split("/")
    if len(arquivos_separados) > 1:
        # Retransmissão de segmentos específicos
        envio_arquivo(retorno_socket, arquivos_separados[0], addr_, parte=int(arquivos_separados[1]))
    else:
        envio_arquivo(retorno_socket, nome_arquivo, addr_)

    retorno_socket.close()


# Função principal do servidor
def main():
    logger = configurar_logger()

    titulo()
    porta_escolhida, iniciar_server = solicitar_porta()

    # Configuração do socket do servidor
    server_socket = s.socket(s.AF_INET, s.SOCK_DGRAM)
    server_socket.bind((SERVER_NAME, porta_escolhida))  
    server_socket.settimeout(1)  
    
    titulo()
    print("Servidor iniciado em " + Fore.LIGHTGREEN_EX + f"{SERVER_NAME}:{porta_escolhida}" + Style.RESET_ALL)

    try:
        print("Aguardando requisições...")
        while iniciar_server:
            try:
                # Aguarda conexões/mensagens de clientes
                message, addr = server_socket.recvfrom(TAM_BUFFER)

                # Cria uma nova thread para processar a requisição
                thread = th.Thread(target=requisicao_arquivo, args=(message, addr, logger), daemon=True)
                thread.start()
                
            except s.timeout:
                continue
            
    except KeyboardInterrupt:
        print("Encerrado manualmente.")
    finally:
        server_socket.close()
        print("Socket do servidor fechado.")

# Executa o servidor
if __name__ == "__main__":
    main()