#####################################################
# Camada Física da Computação
#Carareto
#11/08/2022
#Aplicação
####################################################


#esta é a camada superior, de aplicação do seu software de comunicação serial UART.
#para acompanhar a execução e identificar erros, construa prints ao longo do código! 


import random
import struct
from enlace import *
import time
import numpy as np
import crcmod
import datetime


# voce deverá descomentar e configurar a porta com através da qual ira fazer comunicaçao
#   para saber a sua porta, execute no terminal :
#   python -m serial.tools.list_ports
# se estiver usando windows, o gerenciador de dispositivos informa a porta

#use uma das 3 opcoes para atribuir à variável a porta usada
#serialName = "/dev/ttyACM0"           # Ubuntu (variacao de)
#serialName = "/dev/tty.usbmodem1411" # Mac    (variacao de)
serialName = "com3"                  # Windows(variacao de)
crc16_func = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, xorOut=0x000)
#formulario head:
#0:4 byte - id do pacote
#4:6 byte - tamanho do pacote
#6:8 byte - CRC
#9 byte - handshake Caso seja o hs, ent = hs=b'\x01'
#10 byte - check - Envio correto: b'\x01'  - Envio incorreto: b'\xf0'
#11 byte - quantos pacotes serao enviados
#12 byte - byte de confirmacao final: final Transmissao sucesso =  b'/x01'

#bloco de envio: sendData + log_event()

def log_end_of_transmission(file):
    """
    Escreve uma linha de traços no log para marcar o fim da transmissão.
    """
    file.write('------------------------------------------Transmissao encerrada\n')

def log_event(file, event_type, msg_type, size, pacote_num=None, total_packs=None, crc=None):
    """
    file: Caminho do arquivo de log.
    event_type: "envio" ou "receb".
    msg_type: Tipo de mensagem: 3 (dados), 4 (OK), 5 (Erro).
    size: Tamanho do pacote.
    pacote_num: Número do pacote (se tipo for 3).
    total_packs: Total de pacotes (se tipo for 3).
    crc: CRC do payload (se tipo for 3).
    """
    # Pega o timestamp atual
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S.%f")[:-3]
    
    # Cria o log formatado
    if msg_type == 3:  # Se for um pacote de dados
        log_line = f"{timestamp} / {event_type} / {msg_type} / {size} / {pacote_num} / {total_packs} / {crc:04X}\n"
    else:
        log_line = f"{timestamp} / {event_type} / {msg_type} / {size}\n"
    
    # Escreve no arquivo de log
    #with open(file, 'a') as log_file:
    #    log_file.write(log_line)
    file.write(log_line)


def divide_em_payload(array):
    len_pack = 50
    pacotes = [array[i:i + len_pack] for i in range(0, len(array), len_pack)]#percorre array de bytes, dividindo de 50 em 50(len_pack) 
    return pacotes


def monta_head(id,len_indiv,len_total, CRC = b'\x02\x00', hs =b'\x00', check = b'\x01' ,final = b'\x00'): #numero do pacote #tamanho do pacote #verifica se a mensagem é um handshake
    id_bytes = id.to_bytes(4, byteorder='big')

    tamanho_bytes = len_indiv.to_bytes(2, byteorder='big')
    
    packs_total = len_total.to_bytes(1, byteorder='big')

    if CRC != b'\x02\x00':
        CRC = CRC.to_bytes(2, byteorder='big')
    
    array_nova = id_bytes + tamanho_bytes + CRC + hs + check + packs_total + final # 4,6,8,9,10,11,12
    return array_nova
    
def monta_pacote(head,array_dados,end = b'\xff' * 3):
    return head + array_dados + end



def main():
    try:
        print("Iniciou o main")
        file_client = 'registro_client.txt'
        file_client = open(file_client, 'w')
        #declaramos um objeto do tipo enlace com o nome "com". Essa é a camada inferior à aplicação. Observe que um parametro
        #para declarar esse objeto é o nome da porta.
        com3 = enlace(serialName)

        # Ativa comunicacao. Inicia os threads e a comunicação seiral 
        com3.enable()

        time.sleep(2)
        com3.sendData(b'00')
        time.sleep(5)

        #Se chegamos até aqui, a comunicação foi aberta com sucesso. Faça um print para informar.
        print("Abriu a comunicação")
         
        #aqui você deverá gerar os dados a serem transmitidos. 
        #seus dados a serem transmitidos são um array bytes a serem transmitidos. Gere esta lista com o 
        #nome de txBuffer. Ela sempre irá armazenar os dados a serem enviados.
        imageR = './img/imagem.png'


        print('carregando números para transmissão :')
        print('- {}'.format(imageR))
        print("-------------------------")

        array_img = open(imageR, 'rb').read()
        pacotes = divide_em_payload(array_img)
        total_packs = len(pacotes)

        print('abriu') 
       
        print("meu array de bytes tem tamanho {}" .format(total_packs))
        #faça aqui uma conferência do tamanho do seu txBuffer, ou seja, quantos bytes serão enviados.
       
        #finalmente vamos transmitir os todos. Para isso usamos a funçao sendData que é um método da camada enlace.
        #faça um print para avisar que a transmissão vai começar

        #tente entender como o método send funciona!
        #Cuidado! Apenas trasmita arrays de bytes !        b'\x00'
               
        print('A transmissão vai começar')

        #handshake
        hs_head = monta_head(0, 1,hs=b'\x01', len_total=total_packs)  # head de HandShake
        handshake = hs_head + (b'\xff' * 3)
        com3.sendData(np.asarray(handshake))
        print(np.asarray(handshake))
        print("Handshake enviado. Aguardando resposta...")
        
        #timeout
        inicio = time.time()
        while com3.rx.getBufferLen() < 12:
            if time.time() - inicio >= 5:
                print("Timeout")
                resp = input('Servidor inativo. Tentar novamente? S/N ')
                if resp == 'S':
                    inicio = time.time()
                else:
                    com3.disable() 
                    return 0


        rxBuffer , _ = com3.getData(15)
        print (rxBuffer)

        debug = True

        if rxBuffer[-3:] == (b'\xff' * 3) and rxBuffer[9] == 1:
            print('envio dos pacotes iniciado')
            for i in range(len(pacotes)):
                #file_client = 'registro_client.txt'
                print('entrou no for principal')
                print(f'enviando pacote {i} de {len(pacotes)-1}')

                #calcula CRC
                crc_value = crc16_func(pacotes[i])
                print(f'calculou o CRC:{crc_value}')



                
                if debug:
                    #head = monta_head(3,len(pacotes[3]),len_total=total_packs, CRC=crc_value)#testando erro do id
                    head = monta_head(i,len(pacotes[i]),len_total=total_packs, CRC=24)#testando erro de CRC 
                    debug = False
                else:
                    head = monta_head(i,len(pacotes[i]),len_total=total_packs, CRC=crc_value)

                #txBuffer = monta_pacote(head,(b'\x02' * 60)) # teste erro len pacote
                txBuffer = monta_pacote(head,pacotes[i])

                com3.sendData(np.asarray(txBuffer))#bloco de envio
                log_event(file_client,'envio', 3, len(pacotes[i]), pacote_num= i, total_packs=total_packs,crc=crc_value)

                time_inicio = time.time()

                while com3.rx.getBufferLen()< 16:
                    print('esperando')
                    time.sleep(2)
                    
                    if time.time() - time_inicio >= 6:

                        com3.sendData(np.asarray(txBuffer))
                        log_event(file_client,'envio', 3, len(pacotes[i]), pacote_num= i, total_packs=total_packs,crc=crc_value)

                        print(f'mandou denovo o pacote {i}')
                        time_inicio = time.time()
                    #com3.rx.clearBuffer()
                    pass 
                print('passou do while')

                rxBuffer, nRx = com3.getData(16)#bloco de recebimento

                print('recebeu confirmacao do getdata')
                print(f'confirmacao {rxBuffer}')

                print(f'byte de check{rxBuffer[9]}')
                if rxBuffer[9] != 1:  # Se houver um erro (ex: CRC ou pacote fora de ordem)
                    while rxBuffer[9] != 1:
                        log_event(file_client, 'receb', 5, 16)

                        # O servidor está solicitando o pacote correto
                        package_num_solicitado = struct.unpack('>I', rxBuffer[:4])[0]  # Número do pacote solicitado
                        
                        print(f"O servidor solicitou o reenvio do pacote {package_num_solicitado}")
                        crc_corrigido = crc16_func(pacotes[package_num_solicitado])
                        
                        # Reenvia o pacote solicitado
                        head = monta_head(package_num_solicitado, len(pacotes[package_num_solicitado]), len_total=total_packs, CRC=crc_corrigido)
                        txBuffer = monta_pacote(head, pacotes[package_num_solicitado])

                        com3.sendData(np.asarray(txBuffer))
                        log_event(file_client,'envio', 3, len(pacotes[package_num_solicitado]), pacote_num=package_num_solicitado, total_packs=total_packs, crc=crc_corrigido)
                        
                        print(f'Pacote {package_num_solicitado} reenviado')

                        # Aguardar nova confirmação do servidor
                        rxBuffer, nRx = com3.getData(16)
                else:
                    log_event(file_client, 'receb', 4, 16)  # Se a resposta for OK
            

            #rxBuffer, nRx = com3.getData(12) nao tirar comentario
            if rxBuffer[11] == 1:
                print('transmissao bem sucedida')



        # Encerra comunicação
        log_end_of_transmission(file_client)
        file_client.close()

        print("-------------------------")
        print("Comunicação encerrada")
        print("-------------------------")
        com3.disable()
        
    except Exception as erro:
        print("ops! :-\\")
        print(erro)
        com3.disable()
        

    #so roda o main quando for executado do terminal ... se for chamado dentro de outro modulo nao roda
if __name__ == "__main__":
    main()
    
