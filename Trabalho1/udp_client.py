import socket as s
import time as t
import hashlib as h
import os
import random  
from colorama import Fore, Style 

# Configurações do cliente
TAM_BUFFER = 2048  

# Valores padrões
SERVER_NAME = "127.0.0.1"
SERVER_PORT = 6000
REQUISICAO = "GET TeamMaker.png"
PROBABILIDADE = 50

# Função para exibir o título do cliente
def titulo():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.MAGENTA)
    print("┌────────────────────┐")
    print("│       CLIENTE      │")
    print("└────────────────────┘")
    print(Style.RESET_ALL)

# Função para configurar o socket do cliente
def configurar_socket():
    cliente_socket = s.socket(s.AF_INET, s.SOCK_DGRAM)
    cliente_socket.settimeout(60)  # Define o timeout para evitar bloqueios.
    return cliente_socket

# Função para limpar o buffer do socket
def limpa_buffer(cliente_socket, tam_buffer_server):

    original_timeout = cliente_socket.gettimeout()
    
    cliente_socket.settimeout(0.1)
    try:
        while True:
            cliente_socket.recvfrom(tam_buffer_server)
    except s.timeout:
        pass 
    finally:
        cliente_socket.settimeout(original_timeout)

# Função para solicitar o nome e a porta do servidor ao usuário
def solicitar_configuracao_servidor():
    titulo()
    nome_servidor = input("Digite o endereço do servidor (padrão: 127.0.0.1): ") or SERVER_NAME
    while True:
        try:
            porta_servidor = int(input("Digite a porta do servidor (padrão: 6000): ") or SERVER_PORT)
            if 1024 <= porta_servidor <= 65535:
                break
            else:
                print("A porta deve estar entre 1024 e 65535.")
        except ValueError:
            print("Por favor, insira um número válido.")
    return nome_servidor, porta_servidor

# Função para solicitar uma requisição ao usuário
def solicitar_requisicao():
    while True:
        try:
            requisicao = input("Faça uma requisição (Ex: GET arquivo.ext): ") or REQUISICAO
            if requisicao.split(" ")[1]:
                nome_arquivo = requisicao.split(" ")[1]
                if nome_arquivo.split(".")[-1] in ["png", "jpg", "jpeg", "gif", "txt", "pdf"]:
                    break
                else:
                    print("Formato de arquivo inválido. Tente novamente.")
            else:
                print("Requisição inválida. Informe um arquivo.")
        except Exception as e:
            print("Requisição inválida. Tente novamente.")
 
    return requisicao, nome_arquivo

# Função para configurar a opção de descartar pacotes
def probabilidade_descartar_pacotes():
    while True:
        try:
            valor = int(input("Qual a probabilidade de perder um pacote? (0-100): ") or PROBABILIDADE)
            if 0 <= valor <= 100:
                break
            else:
                print("Valor inválido. Insira um valor entre 0 e 100.")
        except ValueError:
            print("Por favor, insira um número válido.")
            
    
    return valor

# Função para processar a resposta do servidor
def processar_resposta(cliente_socket, nome_arquivo, probabilidade_perda, nome_servidor, porta_servidor):
    
    titulo()
    print("Solicitando o arquivo " + Fore.CYAN + nome_arquivo + Style.RESET_ALL + " no servidor " + Fore.LIGHTGREEN_EX + f"{nome_servidor}:{porta_servidor}"+ Style.RESET_ALL)
    print('\nEsperando resposta do servidor...')
    mensagem, endereco_server = cliente_socket.recvfrom(TAM_BUFFER)

    if mensagem[0:6] == b"[ERRO]":
        # Exibe mensagem de erro recebida do servidor
        response = mensagem.decode().split(" ")
        titulo()
        print(Fore.RED)
        print("Aconteceu um erro: ", " ".join(response[1:]))
        print(Style.RESET_ALL)
    elif mensagem[0:2] == b"OK":
        print('Recebeu!\n')
        response = mensagem.decode().split(" ")
        num_pacotes = int(response[1])
        tam_buffer_server = int(response[2])
        receber_arquivo(cliente_socket, nome_arquivo, num_pacotes, tam_buffer_server, probabilidade_perda, nome_servidor, porta_servidor)

# Função para receber o arquivo do servidor
def receber_arquivo(cliente_socket, nome_arquivo, num_pacotes, tam_buffer_server, probabilidade_perda, nome_servidor, porta_servidor):
    
    buffer = [None for _ in range(num_pacotes)] 

    # Recebe os pacotes do arquivo
    for i in range(num_pacotes):
        message, addr = cliente_socket.recvfrom(tam_buffer_server)

        if message[0:3] == b"END":
            break

        # Simula a perda de pacotes com base na probabilidade
        if random.randint(1, 100) <= probabilidade_perda:
            continue  

        # Processa o pacote recebido
        try:
            header = int(message[:len(str(num_pacotes))].decode())
            buffer[header] = message
        except (ValueError, IndexError):
            # Se ocorrer um erro ao processar o pacote, registra o erro e continua
            print(f"Erro ao processar o pacote {i}.")

    reconstruir_arquivo(buffer, nome_arquivo, num_pacotes, cliente_socket, tam_buffer_server, nome_servidor, porta_servidor)

# Função para reconstruir o arquivo a partir dos pacotes recebidos
def reconstruir_arquivo(buffer, nome_arquivo, num_pacotes, cliente_socket, tam_buffer_server, nome_servidor, porta_servidor):
    
    vet_arquivo = [None for _ in range(num_pacotes)]
    num_digitos = len(str(num_pacotes))
    hash_inicial = num_digitos + 1
    hash_final = hash_inicial + 16

    for pacote in buffer:
        if pacote is not None:
            header = pacote[:num_digitos].decode()
            hash_ = pacote[hash_inicial:hash_final]
            data = pacote[hash_final + 1:]

            if h.md5(data).digest() == hash_:
                vet_arquivo[int(header)] = data

    # Identificar pacotes perdidos
    pacotes_perdidos = [index for index, segment in enumerate(vet_arquivo) if segment is None]

    if pacotes_perdidos:
        print(Fore.RED + f"Pacotes perdidos: {pacotes_perdidos}" + Style.RESET_ALL)
        recuperar = input("Deseja recuperar os pacotes perdidos? [S/N]: ").strip().lower()
        
        titulo()
        if recuperar == 's':
            limpa_buffer(cliente_socket, tam_buffer_server)
            
            for index in pacotes_perdidos:
                data = b""
                hash_ = b""
                contador = 0
                while h.md5(data).digest() != hash_:
                    print(f"Recuperando pacote perdido ({index})...")
                    cliente_socket.sendto(f"GET {nome_arquivo}/{index}".encode(), (nome_servidor, porta_servidor))
                    message, addr = cliente_socket.recvfrom(tam_buffer_server)

                    # Corrigir a extração do hash e dos dados do pacote recebido
                    hash_ = message[hash_inicial:hash_final]
                    data = message[hash_final + 1:]

                    if h.md5(data).digest() == hash_:
                        print(f"Pacote {index} recuperado com sucesso!\n")
                        vet_arquivo[index] = data
                        break
                    else:
                        contador += 1
                        if contador > 3:
                            print(f"Falha ao recuperar o pacote {index} após várias tentativas.\n")
                            break
                        print(f"Pacote {index} inválido, tentando novamente...\n")
                
    # Criar pasta Received_Files
    if not os.path.exists("Received_Files"):
        os.makedirs("Received_Files")
        
    caminho_arquivo = os.path.join("Received_Files", nome_arquivo)

    # Salva o arquivo no disco
    with open(caminho_arquivo, "wb") as arquivo:
        for index in range(num_pacotes):
            if vet_arquivo[index] is None:
                print(f"Pacote {index} não recebido.")
                continue
            arquivo.write(vet_arquivo[index])
            
    print(Fore.GREEN + f"Arquivo {nome_arquivo} reconstruído com sucesso!\n" + Style.RESET_ALL)

def main():
    cliente_socket = configurar_socket()
    nome_servidor, porta_servidor = solicitar_configuracao_servidor()
    requisicao, nome_arquivo = solicitar_requisicao()
    probabilidade_perda = probabilidade_descartar_pacotes() 

    try:
        titulo()
        print(f"Enviando {nome_arquivo}!")
        cliente_socket.sendto(requisicao.encode(), (nome_servidor, porta_servidor))

        processar_resposta(cliente_socket, nome_arquivo, probabilidade_perda, nome_servidor, porta_servidor)
    except TimeoutError:
        print("Tempo limite de comunicação entre o servidor e o cliente!")
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("Encerrado manualmente.")
    finally:
        cliente_socket.close()
        
# Executa o cliente
if __name__ == "__main__":
    main()