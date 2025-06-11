# Trabalho 2 - TCP Client/Server

Este trabalho implementa uma aplicação cliente-servidor utilizando o protocolo TCP com suporte a múltiplos clientes simultâneos, transferência de arquivos com verificação de integridade e chat.

## Como Usar

### 1. Iniciando o Servidor
```bash
py tcp_server.py
```
- Digite a porta desejada (padrão: 5000)
- O servidor estará pronto para receber conexões
- Digite mensagens no console para enviar chat para todos os clientes

### 2. Iniciando o Cliente
```bash
py tcp_client.py
```
- Digite o endereço do servidor (padrão: 127.0.0.1)
- Digite a porta do servidor (padrão: 5000)
- Use os comandos disponíveis

## Protocolo de Aplicação

### Comandos do Cliente

#### 1. SAIR
- **Descrição**: Encerra a conexão com o servidor
- **Formato**: `SAIR`
- **Exemplo**: `SAIR`

#### 2. ARQUIVO
- **Descrição**: Solicita um arquivo do servidor
- **Formato**: `ARQUIVO <nome_do_arquivo>`
- **Exemplo**: `ARQUIVO teste.txt`

#### 3. CHAT
- **Descrição**: Envia mensagem de chat para todos os clientes conectados
- **Formato**: `CHAT <mensagem>`
- **Exemplo**: `CHAT Olá!`

### Respostas do Servidor

#### Mensagens de Erro
```json
{
  "status": "ERRO",
  "mensagem": "Arquivo não encontrado"
}
```

#### Mensagens de Chat
```json
{
  "tipo": "CHAT",
  "mensagem": "[127.0.0.1:5001]: Mensagem do cliente"
}
```

#### Arquivo
```json
{
    "status": "OK",
    "nome_arquivo": "teste.txt",
    "tamanho": 31094,
    "hash_sha256": "591aa51bf0422e8bbca17a8d0c896c5037161ea029f77cf6a05973162b2a9812"
}
```

