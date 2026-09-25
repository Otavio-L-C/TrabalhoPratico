import socket
import threading
import os
import sys
import time

TAMANHO_PARTE = 1500
TIMEOUT = 1
TENTATIVAS = 5
peers = []

#CONFIGURAÇÃO

with open("config.txt", "r") as arquivo:
    linhas = arquivo.readlines()

for linha in linhas:
    linha = linha.strip()

    if linha.startswith("name="):
        nome = linha.split("=")[1]

    elif linha.startswith("host="):
        host = linha.split("=")[1]

    elif linha.startswith("port="):
        porta = int(linha.split("=")[1])

    elif linha.startswith("tmp="):
        diretorio = linha.split("=")[1]

    elif linha.startswith("peer="):
        partes = linha.split("=")[1].split(",")
        peers.append({
            "name": partes[0],
            "host": partes[1],
            "port": int(partes[2])
        })

#SOCKET UDP

sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

sock.bind(
    (host, porta)
)

#CRIAR DIRETÓRIO TMP

if not os.path.exists(diretorio):
    os.makedirs(diretorio)


print("--------------------------------")
print("Peer:", nome)
print("IP:", host)
print("Porta:", porta)
print("Diretório:", diretorio)
print("--------------------------------")

#VARIÁVEIS DE CONTROLE

#partes de arquivos que ainda estão sendo recebidos
recebimentos = {}

#ACKs recebidos
acks = {}

#lock para proteger as estruturas compartilhadas
lock = threading.Lock()

#arquivos que já foram recebidos pela rede
arquivos_recebidos = set()


#ENVIAR MENSAGEM

def enviar(mensagem, endereco):

    sock.sendto(
        mensagem.encode("latin1"),
        endereco
    )


#ENVIAR PARA TODOS OS PEERS

def enviar_para_todos(mensagem):

    for peer in peers:

        endereco = (
            peer["host"],
            peer["port"]
        )

        print(
            "Enviando mensagem para:",
            peer["name"],
            endereco
        )

        try:

            enviar(
                mensagem,
                endereco
            )

        except OSError as erro:

            print(
                "ERRO enviando para",
                peer["name"],
                endereco
            )

            print(erro)


#ANUNCIAR ARQUIVO

def anunciar_arquivo(nome_arquivo):

    caminho = os.path.join(
        diretorio,
        nome_arquivo
    )

    if not os.path.isfile(caminho):
        return

    tamanho = os.path.getsize(caminho)

    mensagem = (
        "ANUNCIO|"
        + nome_arquivo
        + "|"
        + str(tamanho)
    )

    enviar_para_todos(
        mensagem
    )

    print(
        "Arquivo anunciado:",
        nome_arquivo
    )
    
#ENVIAR ARQUIVO

def enviar_arquivo(
    nome_arquivo,
    endereco
):

    caminho = os.path.join(
        diretorio,
        nome_arquivo
    )

    if not os.path.isfile(caminho):
        return

    with open(caminho, "rb") as arquivo:

        dados = arquivo.read()


    #divide o arquivo em partes
    partes = []

    for i in range(
        0,
        len(dados),
        TAMANHO_PARTE
    ):

        partes.append(
            dados[
                i:i + TAMANHO_PARTE
            ]
        )


    total = len(partes)


    print(
        "Enviando",
        nome_arquivo,
        "para",
        endereco
    )

    for numero in range(total):

        parte = partes[numero]

        #converte os bytes para texto
        texto = parte.decode("latin1")

        mensagem = (
            "DADOS|"
            + nome_arquivo
            + "|"
            + str(numero)
            + "|"
            + str(total)
            + "|"
            + texto
        )


        recebido = False


        #tenta enviar até receber ACK
        for tentativa in range(
            TENTATIVAS
        ):

            enviar(
                mensagem,
                endereco
            )

            inicio = time.time()


            while (
                time.time() - inicio
                < TIMEOUT
            ):

                with lock:

                    chave = (
                        endereco,
                        nome_arquivo,
                        numero
                    )

                    if chave in acks:

                        del acks[chave]

                        recebido = True

                        break


                time.sleep(0.01)


            if recebido:
                break


            print(
                "Sem ACK. Reenviando parte",
                numero
            )


        if not recebido:

            print(
                "Erro ao enviar",
                nome_arquivo
            )

            return


    print(
        "Arquivo enviado:",
        nome_arquivo
    )

#RECEBER DADOS DE UMA PARTE

def receber_dados(
    nome_arquivo,
    numero,
    total,
    dados,
    endereco
):

    chave = (
        endereco,
        nome_arquivo
    )


    #cria o espaço para o arquivo
    if chave not in recebimentos:

        recebimentos[chave] = {}


    #guarda a parte
    recebimentos[chave][numero] = dados


    #envia ACK
    mensagem = (
        "ACK|"
        + nome_arquivo
        + "|"
        + str(numero)
    )

    enviar(
        mensagem,
        endereco
    )


    print(
        "Recebida parte",
        numero + 1,
        "/",
        total,
        "de",
        nome_arquivo
    )


    #verifica se todas as partes chegaram
    if len(recebimentos[chave]) == total:

        montar_arquivo(
            nome_arquivo,
            total,
            chave
        )


#MONTAR ARQUIVO

def montar_arquivo(
    nome_arquivo,
    total,
    chave
):

    partes = recebimentos[chave]

    caminho = os.path.join(
        diretorio,
        nome_arquivo
    )


    with open(caminho,"wb") as arquivo:

        for numero in range(total):

            arquivo.write(
                partes[numero]
            )


    del recebimentos[chave]


    arquivos_recebidos.add(nome_arquivo)


    print("Arquivo recebido:",nome_arquivo)



#função auxiliar para listar os arquivos no diretório tmp
def listar_arquivos():

    arquivos = []

    tamanho_total = 0

    for arquivo in os.listdir(diretorio):

        caminho = os.path.join(
            diretorio,
            arquivo
        )

        if os.path.isfile(caminho):

            tamanho = os.path.getsize(caminho)

            arquivos.append(
                (arquivo, tamanho)
            )

            tamanho_total += tamanho

    return arquivos, tamanho_total

#PROCESSAR MENSAGEM

def processar_mensagem(
    mensagem,
    endereco
):

    partes = mensagem.split("|", 4)

    tipo = partes[0]

    #ANUNCIO

    if tipo == "ANUNCIO":

        nome_arquivo = partes[1]
        tamanho = int(partes[2])

        caminho = os.path.join(
            diretorio,
            nome_arquivo
        )

        if os.path.exists(caminho):

            tamanho_local = os.path.getsize(
                caminho
            )

            if tamanho_local == tamanho:

                return

        print(
            "Peer",
            endereco,
            "possui:",
            nome_arquivo
        )

        mensagem_pedir = (
            "PEDIR|"
            + nome_arquivo
        )

        enviar(
            mensagem_pedir,
            endereco
        )

    #PEDIR

    elif tipo == "PEDIR":

        nome_arquivo = partes[1]

        #enviar o arquivo em outra thread

        thread_envio = threading.Thread(
            target=enviar_arquivo,
            args=(
                nome_arquivo,
                endereco
            )
        )

        thread_envio.daemon = True

        thread_envio.start()

    #DADOS

    elif tipo == "DADOS":

        nome_arquivo = partes[1]

        numero = int(
            partes[2]
        )

        total = int(
            partes[3]
        )

        texto = partes[4]

        dados = texto.encode(
            "latin1"
        )


        receber_dados(
            nome_arquivo,
            numero,
            total,
            dados,
            endereco
        )

    
    #ACK

    elif tipo == "ACK":

        nome_arquivo = partes[1]

        numero = int(
            partes[2]
        )

        chave = (
            endereco,
            nome_arquivo,
            numero
        )

        with lock:

            acks[chave] = True


    #REMOVIDO

    elif tipo == "REMOVIDO":

        nome_arquivo = partes[1]

        caminho = os.path.join(
            diretorio,
            nome_arquivo
        )

        if os.path.isfile(caminho):

            os.remove(caminho)

            print(
                "Arquivo removido:",
                nome_arquivo
            )

    #LIST

    elif tipo == "LIST":

        arquivos, tamanho_total = listar_arquivos()

        mensagem = "LISTA|" + str(tamanho_total)

        for arquivo, tamanho in arquivos:

            mensagem += (
                "|"
                + arquivo
                + "|"
                + str(tamanho)
        )

        enviar(
            mensagem,
            endereco
        )

    #LISTA

    elif tipo == "LISTA":

        partes_lista = mensagem.split("|")

        tamanho_total = int(partes_lista[1])

        quantidade = (len(partes_lista) - 2) // 2

        print()
        print("==============================")
        print("LISTA DE ARQUIVOS")
        print("==============================")

        print(
            "Arquivos:",
            quantidade
        )

        print(
            "Tamanho total:",
            round(
                tamanho_total / 1024 / 1024,
                2
            ),
            "MB"
        )

        print()
        print("Arquivos:")

        posicao = 2

        while posicao < len(partes_lista):

            nome_arquivo = partes_lista[posicao]

            tamanho = int(
                partes_lista[posicao + 1]
            )

            print(
                "-",
                nome_arquivo,
                "(",
                round(
                    tamanho / 1024,
                    2
                ),
                "KB)"
            )

            posicao += 2

        print("==============================")

#RECEBIMENTO DE MENSAGENS

def receber_mensagens():

    while True:

        dados, endereco = sock.recvfrom(
            65535
        )

        mensagem = dados.decode(
            "latin1"
        )

        processar_mensagem(
            mensagem,
            endereco
        )


#MONITORAMENTO

def monitorar_diretorio():

    estado_anterior = set()


    while True:

        estado_atual = set()


        #lista os arquivos atuais
        for arquivo in os.listdir(
            diretorio
        ):

            caminho = os.path.join(
                diretorio,
                arquivo
            )

            if os.path.isfile(caminho):

                estado_atual.add(
                    arquivo
                )


        #ARQUIVOS NOVOS OU MODIFICADOS

        for arquivo in estado_atual:

            if arquivo not in estado_anterior:

                #se acabou de receber da rede,
                #não anuncia novamente
                if arquivo in arquivos_recebidos:

                    arquivos_recebidos.remove(
                        arquivo
                    )

                else:

                    anunciar_arquivo(
                        arquivo
                    )


        #ARQUIVOS REMOVIDOS

        for arquivo in estado_anterior:

            if arquivo not in estado_atual:

                mensagem = (
                    "REMOVIDO|"
                    + arquivo
                )

                enviar_para_todos(
                    mensagem
                )

                print(
                    "Arquivo removido:",
                    arquivo
                )


        estado_anterior = estado_atual

        time.sleep(2)


#função para receber comandos
def receber_comandos():

    while True:

        comando = input(
            "\nComando: "
        )

        if comando == "list":

            if len(peers) == 0:

                print(
                    "Nenhum peer configurado."
                )

                continue

            peer = peers[0]

            endereco = (
                peer["host"],
                peer["port"]
            )

            print(
                "Solicitando lista do peer:",
                peer["name"]
            )

            enviar(
                "LIST",
                endereco
            )

        else:

            print(
                "Comando desconhecido."
            )


#INICIAR THREADS

thread_recebimento = threading.Thread(
    target=receber_mensagens
)

thread_monitoramento = threading.Thread(
    target=monitorar_diretorio
)

thread_comandos = threading.Thread(
    target=receber_comandos
)

thread_recebimento.daemon = True
thread_monitoramento.daemon = True
thread_comandos.daemon = True

thread_recebimento.start()
thread_monitoramento.start()
thread_comandos.start()

# MANTER PROGRAMA RODANDO

while True:

    time.sleep(1)