import socket
import threading
import os
import hashlib
import time
import json
import signal
import sys
import logging as l
from datetime import datetime
from colorama import Fore, Style

# Configurações do servidor
TAM_BUFFER = 1024
PASTA_ARQUIVOS = "../Files"
SERVER_NAME = '127.0.0.1'
SERVER_PORT = 5000


def configurar_logger():
    logger = l.getLogger(__name__)
    l.basicConfig(
        filename="server.log",
        encoding="utf-8",
        level=l.INFO,
        format="%(levelname)s - %(asctime)s: %(message)s"
    )
    return logger

logger = configurar_logger()

clientes_conectados = []
lock = threading.Lock()
servidor_ativo = threading.Event()
servidor_ativo.set()  

def signal_handler(sig, frame):
    logger.warning(f"Iniciando encerramento do servidor...")
    print(f"\nEncerrando servidor...")
    servidor_ativo.clear()

def titulo():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.MAGENTA)
    print("┌────────────────────┐")
    print("│      SERVIDOR      │")
    print("└────────────────────┘")
    print(Style.RESET_ALL)

def solicitar_porta():
    while True:
        try:
            porta_escolhida = int(input(f"Digite a porta do servidor (padrão: {SERVER_PORT}): ") or SERVER_PORT)
            if 1024 <= porta_escolhida <= 65535:
                return porta_escolhida
            else:
                print("A porta deve estar entre 1024 e 65535.")
        except ValueError:
            print("Por favor, insira um número válido.")

def calcular_sha256(arquivo_path):
    sha256_hash = hashlib.sha256()
    with open(arquivo_path, "rb") as f:
        for chunk in iter(lambda: f.read(TAM_BUFFER), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def enviar_arquivo(cliente_socket, nome_arquivo, endereco_cliente):
    """Envia um arquivo para o cliente com verificação de integridade"""
    logger.info(f"Solicitação de arquivo '{nome_arquivo}' de {endereco_cliente}")
    
    try:
        caminho_arquivo = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
        
        if not os.path.exists(caminho_arquivo):
            logger.warning(f"Arquivo '{nome_arquivo}' não encontrado para {endereco_cliente}")
            resposta = {
                "status": "ERRO",
                "mensagem": "Arquivo não encontrado"
            }
            cliente_socket.send(json.dumps(resposta).encode() + b'\n')
            return

        tamanho_arquivo = os.path.getsize(caminho_arquivo)
        hash_arquivo = calcular_sha256(caminho_arquivo)
        
        logger.info(f"Enviando arquivo '{nome_arquivo}' para {endereco_cliente} - Tamanho: {tamanho_arquivo} bytes")
        print(f"Enviando arquivo {nome_arquivo} para {endereco_cliente}")
        print(f"Tamanho: {tamanho_arquivo} bytes, SHA-256: {hash_arquivo}")

        metadados = {
            "status": "OK",
            "nome_arquivo": nome_arquivo,
            "tamanho": tamanho_arquivo,
            "hash_sha256": hash_arquivo
        }
        cliente_socket.send(json.dumps(metadados).encode() + b'\n')
        
        confirmacao = cliente_socket.recv(TAM_BUFFER).decode().strip()
        if confirmacao != "READY":
            logger.warning(f"Cliente {endereco_cliente} não confirmou recebimento: {confirmacao}")
            print(f"Cliente {endereco_cliente} não está pronto para receber o arquivo")
            return

        logger.info(f"Cliente {endereco_cliente} confirmou - iniciando transferência")
        with open(caminho_arquivo, "rb") as arquivo:
            bytes_enviados = 0
            while True:
                chunk = arquivo.read(TAM_BUFFER)
                if not chunk:
                    break
                cliente_socket.send(chunk)
                bytes_enviados += len(chunk)
                
                progresso = (bytes_enviados / tamanho_arquivo) * 100
                print(f"Progresso: {progresso:.1f}% ({bytes_enviados}/{tamanho_arquivo} bytes)", end='\r')

        logger.info(f"Arquivo '{nome_arquivo}' enviado com sucesso para {endereco_cliente}")
        print(f"\nArquivo {nome_arquivo} enviado com sucesso para {endereco_cliente}")

    except Exception as e:
        logger.error(f"Erro ao enviar arquivo '{nome_arquivo}' para {endereco_cliente}: {e}")
        print(f"Erro ao enviar arquivo {nome_arquivo}: {e}")
        resposta = {
            "status": "ERRO",
            "mensagem": f"Erro interno do servidor: {str(e)}"
        }
        try:
            cliente_socket.send(json.dumps(resposta).encode() + b'\n')
        except:
            logger.error(f"Falha ao enviar mensagem de erro para {endereco_cliente}")

def broadcast_chat(mensagem, remetente_socket=None):
    """Envia mensagem de chat para todos os clientes conectados"""
    logger.info(f"Broadcasting mensagem de chat: {mensagem[:50]}...")
    
    with lock:
        clientes_para_remover = []
        clientes_ativos = len(clientes_conectados)
        
        for cliente_info in clientes_conectados:
            cliente_socket = cliente_info['socket']
            if cliente_socket != remetente_socket:
                try:
                    chat_msg = {
                        "tipo": "CHAT",
                        "mensagem": mensagem
                    }
                    cliente_socket.send(json.dumps(chat_msg).encode() + b'\n')
                except Exception as e:
                    logger.warning(f"Falha ao enviar chat para {cliente_info['endereco']}: {e}")
                    clientes_para_remover.append(cliente_info)
        
        for cliente_info in clientes_para_remover:
            logger.info(f"Removendo cliente desconectado: {cliente_info['endereco']}")
            clientes_conectados.remove(cliente_info)
            
        logger.debug(f"Mensagem enviada para {clientes_ativos - len(clientes_para_remover) - 1} clientes")

def processar_cliente(cliente_socket, endereco_cliente):
    """Processa as requisições de um cliente específico"""
    logger.info(f"Nova conexão estabelecida: {endereco_cliente}")
    print(f"Cliente conectado: {endereco_cliente}")
    
    with lock:
        clientes_conectados.append({
            'socket': cliente_socket,
            'endereco': endereco_cliente
        })
    
    logger.info(f"Total de clientes conectados: {len(clientes_conectados)}")

    try:
        while True:
            requisicao = cliente_socket.recv(TAM_BUFFER).decode().strip()
            
            if not requisicao:
                logger.info(f"Cliente {endereco_cliente} enviou requisição vazia - desconectando")
                break
                
            logger.info(f"Requisição de {endereco_cliente}: {requisicao}")
            print(f"Requisição de {endereco_cliente}: {requisicao}")
            
            if requisicao == "SAIR":
                logger.info(f"Cliente {endereco_cliente} solicitou desconexão")
                print(f"Cliente {endereco_cliente} solicitou desconexão")
                break
                
            elif requisicao.startswith("ARQUIVO "):
                nome_arquivo = requisicao[8:].strip()
                logger.info(f"Cliente {endereco_cliente} solicitou arquivo: {nome_arquivo}")
                enviar_arquivo(cliente_socket, nome_arquivo, endereco_cliente)
                
            elif requisicao.startswith("CHAT "):
                mensagem_chat = requisicao[5:].strip()
                logger.info(f"Mensagem de chat de {endereco_cliente}: {mensagem_chat}")
                print(Fore.CYAN + f"[{endereco_cliente}]: {mensagem_chat}" + Style.RESET_ALL)

                mensagem_completa = f"[{endereco_cliente}]: {mensagem_chat}"
                broadcast_chat(mensagem_completa, cliente_socket)
                
            else:
                logger.warning(f"Comando não reconhecido de {endereco_cliente}: {requisicao}")
                resposta = {
                    "status": "ERRO",
                    "mensagem": "Comando não reconhecido!"
                }
                cliente_socket.send(json.dumps(resposta).encode() + b'\n')

    except Exception as e:
        logger.error(f"Erro ao processar cliente {endereco_cliente}: {e}")
        print(f"Erro com cliente {endereco_cliente}: {e}")
    finally:
        with lock:
            clientes_conectados[:] = [c for c in clientes_conectados if c['socket'] != cliente_socket]
        
        cliente_socket.close()
        logger.info(f"Cliente {endereco_cliente} desconectado. Clientes restantes: {len(clientes_conectados)}")
        print(f"Cliente {endereco_cliente} desconectado")

def console_input_thread():    
    while servidor_ativo.is_set():
        try:
            mensagem = input()
            if not servidor_ativo.is_set():
                break
            if mensagem.strip():
                if mensagem.lower() == 'quit' or mensagem.lower() == 'sair':
                    logger.info("Comando de encerramento recebido via console")
                    servidor_ativo.clear()
                    print("Encerrando servidor...")
                    break
                logger.info(f"Mensagem do servidor sendo enviada: {mensagem}")
                mensagem_servidor = f"[SERVIDOR]: {mensagem}"
                broadcast_chat(mensagem_servidor)
                print(f"Mensagem enviada para todos os clientes: {mensagem}")
        except (EOFError, KeyboardInterrupt):
            logger.info("Interrupção detectada na thread de console")
            servidor_ativo.clear()
            break

def main():    
    titulo()
    porta_escolhida = solicitar_porta()
    
    if not os.path.exists(PASTA_ARQUIVOS):
        os.makedirs(PASTA_ARQUIVOS)
        print(f"Pasta {PASTA_ARQUIVOS} criada")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(1.0) 
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        server_socket.bind((SERVER_NAME, porta_escolhida))
        server_socket.listen(5)  
        logger.info(f"Servidor bind realizado em {SERVER_NAME}:{porta_escolhida}")
        
        titulo()
        print("Servidor iniciado em " + Fore.LIGHTGREEN_EX + f"{SERVER_NAME}:{porta_escolhida}" + Style.RESET_ALL)
        print("Aguardando conexões de clientes...")
        print(Fore.YELLOW + "Digite mensagens aqui para enviar chat para todos os clientes:" + Style.RESET_ALL)
        print(Fore.RED + "Digite 'quit' ou 'sair' para encerrar o servidor" + Style.RESET_ALL)
        print(Fore.RED + "Ou use Ctrl+C para forçar o encerramento" + Style.RESET_ALL)
        
        console_thread = threading.Thread(target=console_input_thread)
        console_thread.start()
        
        while servidor_ativo.is_set():
            try:
                cliente_socket, endereco_cliente = server_socket.accept()
                
                if not servidor_ativo.is_set():
                    cliente_socket.close()
                    break
                
                logger.info(f"Nova conexão aceita de {endereco_cliente}")
                cliente_thread = threading.Thread(
                    target=processar_cliente,
                    args=(cliente_socket, endereco_cliente)
                )
                cliente_thread.start()
                
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                logger.warning("Interrupção por teclado detectada")
                print("\nEncerrando servidor...")
                servidor_ativo.clear()
                break
            except Exception as e:
                if servidor_ativo.is_set():
                    logger.error(f"Erro ao aceitar conexão: {e}")
                    print(f"Erro ao aceitar conexão: {e}")
                
    except Exception as e:
        logger.error(f"Erro no servidor: {e}")
        print(f"Erro no servidor: {e}")
    finally:
        # Fecha todas as conexões
        servidor_ativo.clear()
        logger.info("Fechando conexões...")
        print("Fechando conexões...")
        
        with lock:
            for cliente_info in clientes_conectados[:]:
                try:
                    logger.debug(f"Fechando conexão com {cliente_info['endereco']}")
                    cliente_info['socket'].close()
                except Exception as e:
                    logger.error(f"Erro ao fechar conexão: {e}")
        
        server_socket.close()
        logger.info("Servidor encerrado com sucesso!")
        print(Fore.GREEN + "Servidor encerrado com sucesso!" + Style.RESET_ALL)

if __name__ == "__main__":
    main()
