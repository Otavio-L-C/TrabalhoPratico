# TrabalhoPratico GrauA
Nome: Otavio Librelotto Colombo

Como rodar: 
Configure o .txt com o nome(do peer), ipv4(do seu pc), port(para a aplicação) e nome(da pasta que quer monitorar/criar). 

Depois anuncie os outros peers, ex.: peer=B, 192.168.X.XX, 5000. 

Abra um terminal em uma pasta que contenha o .py e o .txt. E rode "python peer.py peerA*/config.txt

peerA* = peer + nome do peer

Documentação:

---Funcionamento---

O sistema utiliza UDP através de sockets Python.
O socket é criado com:
socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)
AF_INET indica que será utilizado IPv4.
SOCK_DGRAM indica que o protocolo utilizado é UDP.
Depois, o socket é associado à porta através de:
sock.bind((host, porta))
As mensagens são enviadas utilizando:
sock.sendto(...)
e recebidas utilizando:
sock.recvfrom(...)

---Arquivos---

Quando um novo arquivo é colocado na pasta tmp, o peer identifica o arquivo e envia uma mensagem ANUNCIO para os demais peers.
Os outros peers pedem o arquivo e esse ele é enviado e em seguida vai o ACK para confirmar a integridade dos dados. Caso o arquivo seja maior de 1500 bytes ele é partido em multiplas partes e enviado, cada um com um ACK.
Depois que todas as partes são recebidas, o arquivo é reconstruído no diretório tmp do peer.

Além disso cada parte recebida é armazenada utilizando seu número:

recebimentos[chave][numero] = dados

Dessa forma, as partes não precisam chegar na ordem correta e evita problemas causados pelo UDP como mensagens duplicadas.

---Protocolos---

O sistema utiliza os seguintes tipos de protocolos:

Protocolo -	Função

ANUNCIO -	Informa que um novo arquivo está disponível

PEDIR -	Solicita um arquivo a outro peer

DADOS -	Transporta uma parte do arquivo

ACK -	Confirma o recebimento de uma parte

REMOVIDO-	Informa que um arquivo foi removido

LIST -	Solicita a lista de arquivos de um peer

LISTA -	Responde com a lista e informações dos arquivos

---Comandos---

O programa possui o comando:
"list"

Esse comando solicita a um peer a lista dos arquivos existentes em seu diretório.

---Threads---

O programa utiliza múltiplas threads para que diferentes atividades possam ocorrer simultaneamente.
São utilizadas threads para:

- Recebimento de mensagens

thread_recebimento

Fica aguardando novas mensagens UDP.

- Monitoramento do diretório

thread_monitoramento

Verifica periodicamente se arquivos foram adicionados ou removidos.

- Envio de arquivos

Quando um peer recebe uma mensagem PEDIR, o envio do arquivo ocorre em uma nova thread.
Isso é importante porque o envio possui espera por ACKs. Sem uma thread separada, o recebimento de novas mensagens poderia ficar bloqueado durante a transferência.

- Comandos do usuário

A thread de comandos permite utilizar o terminal, como "list"
sem interromper o recebimento e processamento das mensagens de rede.

---Monitoramento do diretorio---

O programa verifica periodicamente os arquivos presentes na pasta tmp.

O intervalo utilizado é:
time.sleep(2)

Quando um arquivo novo é encontrado:
ANUNCIO
é enviado aos outros peers.

Quando um arquivo é removido:
REMOVIDO
é enviado aos outros peers.

O sistema não realiza comparação do conteúdo dos arquivos. A sincronização considera principalmente a inclusão e a remoção de arquivos.
