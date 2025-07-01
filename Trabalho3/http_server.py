import socket
import threading
import os
import mimetypes
import signal
import sys
import logging as l
from datetime import datetime
from urllib.parse import unquote
from colorama import Fore, Style

# Configurações do servidor HTTP
TAM_BUFFER = 4096
PASTA_ARQUIVOS = "../Files"
PASTA_WEB = "./www"
SERVER_NAME = '127.0.0.1'
SERVER_PORT = 8080

# Configuração do logger
def configurar_logger():
    logger = l.getLogger(__name__)
    l.basicConfig(
        handlers=[
            l.StreamHandler(sys.stdout), 
            l.FileHandler("server.log", encoding="utf-8") 
        ],
        level=l.INFO,
        format="%(levelname)s - %(asctime)s: %(message)s"
    )
    return logger

# Inicializa o logger
logger = configurar_logger()

# Lista para armazenar clientes conectados
clientes_conectados = []
lock = threading.Lock()
servidor_ativo = threading.Event()
servidor_ativo.set()

def signal_handler(sig, frame):
    print(f"\nEncerrando servidor HTTP...")
    servidor_ativo.clear()

def titulo():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.MAGENTA)
    print("┌──────────────────────────┐")
    print("│      SERVIDOR HTTP       │")
    print("└──────────────────────────┘")
    print(Style.RESET_ALL)

def solicitar_porta():
    while True:
        try:
            porta_escolhida = int(input(f"Digite a porta do servidor HTTP (padrão: {SERVER_PORT}): ") or SERVER_PORT)
            if 1024 <= porta_escolhida <= 65535:
                return porta_escolhida
            else:
                print("A porta deve estar entre 1024 e 65535.")
        except ValueError:
            print("Por favor, insira um número válido.")

#--------------------------------

def obter_mime_type(arquivo):
    # extensao = arquivo.lower().split('.')[-1]
    # tipos_mime = {
    #     'txt': 'text/plain',
    #     'html': 'text/html',
    #     'css': 'text/css',
    #     'csv': 'text/csv',
    #     'pdf': 'application/pdf',
    #     'mp4': 'video/mp4',
    #     'jpg': 'image/jpeg',
    #     'jpeg': 'image/jpeg',
    #     'png': 'image/png',
    #     'gif': 'image/gif',
    # }
    # return tipos_mime.get(extensao, 'application/octet-stream')
    
    mime_type, _ = mimetypes.guess_type(arquivo)
    return mime_type or 'application/octet-stream'

def criar_resposta_http(status_code, status_text, content_type, body):
    current_time = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    headers = [
        f"HTTP/1.1 {status_code} {status_text}",
        f"Date: {current_time}",
        f"Server: UTFPR-HTTP-Server/1.0",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body)}",
        "Connection: close"
    ]
    
    response = "\r\n".join(headers) + "\r\n\r\n"
    
    if isinstance(body, str):
        return response.encode('utf-8') + body.encode('utf-8')
    else:
        return response.encode('utf-8') + body

def processar_requisicao_http(caminho, endereco_cliente):
    logger.info(f"Processando requisição para '{caminho}' de {endereco_cliente}")
    
    if '?' in caminho:
        caminho = caminho.split('?')[0]
    caminho = unquote(caminho)
    
    # Página inicial
    if caminho == "/" or caminho == "":
        return servir_pagina_inicial()
    
    # Arquivos estáticos (imagens, etc.)
    if caminho.startswith("/"):
        nome_arquivo = caminho[1:]  # Remove '/' inicial
        
        caminho_web = os.path.join(PASTA_WEB, nome_arquivo)
        if os.path.exists(caminho_web) and os.path.isfile(caminho_web):
            return servir_arquivo(caminho_web, endereco_cliente)
        
        caminho_arquivo = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
        if os.path.exists(caminho_arquivo) and os.path.isfile(caminho_arquivo):
            return servir_arquivo(caminho_arquivo, endereco_cliente)
        
        erro404_path = os.path.join(PASTA_WEB, "404.html")
        with open(erro404_path, "r", encoding="utf-8") as f:
            erro_404_content = f.read()
        
        logger.warning(f"Arquivo '{nome_arquivo}' não encontrado para {endereco_cliente}")
        return criar_resposta_http(404, "Not Found", "text/html", erro_404_content)

def servir_arquivo(caminho_arquivo, endereco_cliente):
    try:
        with open(caminho_arquivo, "rb") as f:
            content = f.read()
        
        mime_type = obter_mime_type(caminho_arquivo)
        nome_arquivo = os.path.basename(caminho_arquivo)
        
        logger.info(f"Servindo arquivo '{nome_arquivo}' para {endereco_cliente} - {len(content)} bytes")
        return criar_resposta_http(200, "OK", mime_type, content)
        
    except Exception as e:
        logger.error(f"Erro ao ler arquivo '{caminho_arquivo}': {e}")
        erro500_path = os.path.join(PASTA_WEB, "500.html")

        with open(erro500_path, "r", encoding="utf-8") as f:
            erro_500_content = f.read()

        return criar_resposta_http(500, "Internal Server Error", "text/html", erro_500_content)

def servir_pagina_inicial():
    """Carrega o template HTML externo e insere dinamicamente a lista de arquivos"""
    try:
        # Carrega o template HTML externo
        template_path = os.path.join(PASTA_WEB, "index.html")
        erro404_path = os.path.join(PASTA_WEB, "404.html")
        
        with open(erro404_path, "r", encoding="utf-8") as f:
            erro_404_content = f.read()
        
        if not os.path.exists(template_path):
            logger.error(f"Template HTML não encontrado em {template_path}")
            return criar_resposta_http(404, "Not Found", "text/html", erro_404_content)

        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        return criar_resposta_http(200, "OK", "text/html", html_content)
        
    except Exception as e:
        logger.error(f"Erro ao carregar página inicial: {e}")
        erro500_path = os.path.join(PASTA_WEB, "500.html")
        with open(erro500_path, "r", encoding="utf-8") as f:
            erro_500_content = f.read()

        return criar_resposta_http(500, "Internal Server Error", "text/html", erro_500_content)

def processar_cliente_http(cliente_socket, endereco_cliente):
    logger.info(f"Nova conexão HTTP estabelecida: {endereco_cliente}")
    
    with lock:
        clientes_conectados.append({
            'socket': cliente_socket,
            'endereco': endereco_cliente
        })
    
    try:
        request_data = cliente_socket.recv(TAM_BUFFER).decode('utf-8', errors='replace')
        print(Fore.YELLOW + f"------------------------------" + Style.RESET_ALL)
        
        if not request_data:
            logger.info(f"Cliente {endereco_cliente} enviou requisição vazia")
            return
        
        lines = request_data.split('\r\n')
        request_line = lines[0]
        
        parts = request_line.split()
        method = parts[0]
        path = parts[1]
        
        logger.info(f"Requisição {method} {path} de {endereco_cliente}")
        if method == "GET":
            response = processar_requisicao_http(path, endereco_cliente)
        else:
            logger.warning(f"Método não suportado: {method} de {endereco_cliente}")
            erro405_path = os.path.join(PASTA_WEB, "405.html")
            with open(erro405_path, "r", encoding="utf-8") as f:
                erro_405_content = f.read()

            response = criar_resposta_http(405, "Method Not Allowed", "text/html", erro_405_content)

        cliente_socket.send(response)
        
    except Exception as e:
        logger.error(f"Erro ao processar cliente HTTP {endereco_cliente}: {e}")
        try:
            erro500_path = os.path.join(PASTA_WEB, "500.html")
            with open(erro500_path, "r", encoding="utf-8") as f:
                erro_500_content = f.read()
                
            cliente_socket.send(criar_resposta_http(500, "Internal Server Error", "text/html", erro_500_content))
        except:
            pass
    finally:
        with lock:
            clientes_conectados[:] = [c for c in clientes_conectados if c['socket'] != cliente_socket]
        
        cliente_socket.close()
        logger.info(f"Cliente HTTP {endereco_cliente} desconectado")

def main():
    logger.info("=== INICIANDO SERVIDOR HTTP ===")
    titulo()
    porta_escolhida = solicitar_porta()
    logger.info(f"Porta HTTP selecionada: {porta_escolhida}")
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(1.0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        server_socket.bind((SERVER_NAME, porta_escolhida))
        server_socket.listen(10)
        logger.info(f"Servidor HTTP bind realizado em {SERVER_NAME}:{porta_escolhida}")
        
        titulo()
        print("Servidor HTTP iniciado em " + Fore.LIGHTGREEN_EX + f"http://{SERVER_NAME}:{porta_escolhida}" + Style.RESET_ALL)
        print(Fore.YELLOW + "Use Ctrl+C para encerrar o servidor" + Style.RESET_ALL)
        
        logger.info("Servidor HTTP pronto para aceitar conexões")
        
        while servidor_ativo.is_set():
            try:
                cliente_socket, endereco_cliente = server_socket.accept()
                
                if not servidor_ativo.is_set():
                    logger.info("Servidor HTTP inativo - rejeitando nova conexão")
                    cliente_socket.close()
                    break
                
                logger.debug(f"Nova conexão HTTP aceita de {endereco_cliente}")
                cliente_thread = threading.Thread(
                    target=processar_cliente_http,
                    args=(cliente_socket, endereco_cliente)
                )
                cliente_thread.start()
                
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                logger.warning("Encerrando servidor HTTP...")
                servidor_ativo.clear()
                break
            except Exception as e:
                if servidor_ativo.is_set():
                    logger.error(f"Erro ao aceitar conexão HTTP: {e}")
                
    except Exception as e:
        logger.error(f"Erro no servidor HTTP: {e}")
    finally:
        servidor_ativo.clear()
        logger.info("Fechando conexões HTTP...")
        
        with lock:
            for cliente_info in clientes_conectados[:]:
                try:
                    logger.debug(f"Fechando conexão HTTP com {cliente_info['endereco']}")
                    cliente_info['socket'].close()
                except Exception as e:
                    logger.error(f"Erro ao fechar conexão HTTP: {e}")
        
        server_socket.close()
        logger.info("Socket do servidor HTTP fechado")

if __name__ == "__main__":
    main()
