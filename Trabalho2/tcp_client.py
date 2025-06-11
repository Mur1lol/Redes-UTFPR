import socket
import os
import hashlib
import json
import threading
import time
from colorama import Fore, Style

TAM_BUFFER = 1024

SERVER_NAME = "127.0.0.1"
SERVER_PORT = 5000

recebendo_arquivo = threading.Event()
cliente_ativo = threading.Event()
cliente_ativo.set()

def titulo():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.MAGENTA)
    print("┌────────────────────────────────┐")
    print("│          CLIENTE TCP           │")
    print("└────────────────────────────────┘")
    print(Style.RESET_ALL)

def solicitar_configuracao_servidor():
    titulo()
    nome_servidor = input(f"Digite o endereço do servidor (padrão: {SERVER_NAME}): ") or SERVER_NAME
    while True:
        try:
            porta_servidor = int(input(f"Digite a porta do servidor (padrão: {SERVER_PORT}): ") or SERVER_PORT)
            if 1024 <= porta_servidor <= 65535:
                break
            else:
                print("A porta deve estar entre 1024 e 65535.")
        except ValueError:
            print("Por favor, insira um número válido.")
    return nome_servidor, porta_servidor

def calcular_sha256(arquivo_path):
    sha256_hash = hashlib.sha256()
    with open(arquivo_path, "rb") as f:
        for chunk in iter(lambda: f.read(TAM_BUFFER), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def receber_arquivo(cliente_socket, nome_arquivo, tamanho_arquivo, hash_esperado):
    try:
        recebendo_arquivo.set()
        
        pasta_destino = "Received_Files"
        if not os.path.exists(pasta_destino):
            os.makedirs(pasta_destino)
        
        caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)
            
        cliente_socket.send("READY".encode())
        
        print(f"Recebendo arquivo: {nome_arquivo}")
        print(f"Tamanho esperado: {tamanho_arquivo} bytes")
        
        with open(caminho_arquivo, "wb") as arquivo:
            bytes_recebidos = 0
            while bytes_recebidos < tamanho_arquivo:
                chunk = cliente_socket.recv(min(TAM_BUFFER, tamanho_arquivo - bytes_recebidos))
                if not chunk:
                    break
                arquivo.write(chunk)
                bytes_recebidos += len(chunk)
                
                progresso = (bytes_recebidos / tamanho_arquivo) * 100
                print(f"Progresso: {progresso:.1f}% ({bytes_recebidos}/{tamanho_arquivo} bytes)", end='\r')
        
        hash_calculado = calcular_sha256(caminho_arquivo)
        
        print(f"Hash esperado:  {hash_esperado}")
        print(f"Hash calculado: {hash_calculado}")
        
        if hash_calculado == hash_esperado:
            print(Fore.GREEN + "Arquivo recebido!" + Style.RESET_ALL)
        else:
            print(Fore.RED + "ERRO: Arquivo corrompido!" + Style.RESET_ALL)
            
    except Exception as e:
        print(f"Erro ao receber arquivo: {e}")
    finally:
        recebendo_arquivo.clear()
        print("Digite seu comando: ", end='', flush=True)

def receber_mensagens_thread(cliente_socket):
    buffer = ""
    while cliente_ativo.is_set():
        try:
            data = cliente_socket.recv(TAM_BUFFER).decode('utf-8', errors='ignore')
            if not data:
                break
                
            buffer += data
            
            while '\n' in buffer:
                linha, buffer = buffer.split('\n', 1)
                linha = linha.strip()
                
                if linha:
                    try:
                        json_start = linha.find('{')
                        if json_start >= 0:
                            json_part = linha[json_start:]
                            mensagem = json.loads(json_part)
                            
                            if mensagem.get("tipo") == "CHAT":
                                if not recebendo_arquivo.is_set():
                                    print(f"\n{Fore.CYAN}{mensagem['mensagem']}{Style.RESET_ALL}")
                                    print("Digite seu comando: ", end='', flush=True)
                                
                            elif mensagem.get("status") == "OK":
                                nome_arquivo = mensagem.get("nome_arquivo")
                                tamanho = mensagem.get("tamanho")
                                hash_sha256 = mensagem.get("hash_sha256")
                                
                                if nome_arquivo and tamanho and hash_sha256:
                                    receber_arquivo(cliente_socket, nome_arquivo, tamanho, hash_sha256)
                                    
                            elif mensagem.get("status") == "ERRO":
                                print(f"\n{Fore.RED}Erro: {mensagem.get('mensagem', 'Erro desconhecido')}{Style.RESET_ALL}")
                                print("Digite seu comando: ", end='', flush=True)
                                
                    except json.JSONDecodeError:
                        if not recebendo_arquivo.is_set():
                            print(f"\nJSON com problema: {linha}")
                            print("Digite seu comando: ", end='', flush=True)
                            
        except Exception as e:
            if cliente_ativo.is_set():
                print(f"Erro ao receber mensagem: {e}")
            break

def mostrar_menu():
    print(f"\n{Fore.YELLOW}=== MENU DE COMANDOS ==={Style.RESET_ALL}")
    print("1. SAIR - Encerrar conexão")
    print("2. ARQUIVO <nome> - Solicitar arquivo do servidor")
    print("3. CHAT <mensagem> - Enviar mensagem de chat")
    print(f"{Fore.YELLOW}========================{Style.RESET_ALL}")

def main():
    nome_servidor, porta_servidor = solicitar_configuracao_servidor()
    cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        titulo()
        cliente_socket.connect((nome_servidor, porta_servidor))
        
        print(Fore.GREEN + f"Conectado com sucesso ao servidor!" + Style.RESET_ALL)
        
        thread_recepcao = threading.Thread(target=receber_mensagens_thread, args=(cliente_socket,), daemon=True)
        thread_recepcao.start()
        
        mostrar_menu()
        
        while True:
            try:
                comando = input("Digite seu comando: ").strip()
                
                if not comando:
                    continue
                
                if comando == "SAIR":
                    cliente_socket.send(comando.encode())
                    print("Encerrando conexão...")
                    break
                    
                elif comando.startswith("ARQUIVO "):
                    if len(comando.split()) < 2:
                        print(f"{Fore.RED}Uso: ARQUIVO <nome_do_arquivo>{Style.RESET_ALL}")
                        continue
                    cliente_socket.send(comando.encode())
                    
                elif comando.startswith("CHAT "):
                    if len(comando.split()) < 2:
                        print(f"{Fore.RED}Uso: CHAT <sua_mensagem>{Style.RESET_ALL}")
                        continue
                    cliente_socket.send(comando.encode())
                    
                elif comando == "MENU":
                    mostrar_menu()
                    
                else:
                    print(f"{Fore.RED}Comando inválido. Digite 'MENU' para ver os comandos disponíveis.{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                print("\nEncerrando cliente...")
                break
                
    except ConnectionRefusedError:
        print(f"{Fore.RED}Erro: Não foi possível conectar ao servidor {nome_servidor}:{porta_servidor}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Erro: {e}{Style.RESET_ALL}")
        
    finally:
        cliente_ativo.clear()
        cliente_socket.close()
        print("Conexão encerrada.")

if __name__ == "__main__":
    main()
