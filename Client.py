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


# voce deverá descomentar e configurar a porta com através da qual ira fazer comunicaçao
#   para saber a sua porta, execute no terminal :
#   python -m serial.tools.list_ports
# se estiver usando windows, o gerenciador de dispositivos informa a porta

#use uma das 3 opcoes para atribuir à variável a porta usada
#serialName = "/dev/ttyACM0"           # Ubuntu (variacao de)
#serialName = "/dev/tty.usbmodem1411" # Mac    (variacao de)
serialName = "com5"                  # Windows(variacao de)

#formulario head:
#0:4 byte - id do pacote
#4:6 byte - tamanho do pacote
#6:8 byte - CRC
#9 byte - handshake Caso seja o hs, ent = hs=b'\x01'
#10 byte - check - Envio correto: b'\x01'  - Envio incorreto: b'\xf0'
#11 byte - quantos pacotes serao enviados
#12 byte - byte de confirmacao final: final Transmissao sucesso =  b'/x01'

def divide_em_payload(array):
    len_pack = 50
    pacotes = [array[i:i + len_pack] for i in range(0, len(array), len_pack)]#percorre array de bytes, dividindo de 50 em 50(len_pack) 
    return pacotes


def monta_head(id,len_indiv,len_total,CRC = b'\x02', hs =b'\x00', check = b'\x01' ,final = b'\x00'): #numero do pacote #tamanho do pacote #verifica se a mensagem é um handshake
    id_bytes = id.to_bytes(4, byteorder='big')

    tamanho_bytes = len_indiv.to_bytes(2, byteorder='big')
    
    packs_total = len_total.to_bytes(1, byteorder='big')

    
    array_nova = id_bytes + tamanho_bytes + CRC + hs + check + packs_total + final # 4,6,8,9,10,11,12
    return array_nova
    
def monta_pacote(head,array_dados,end = b'\xff' * 3):
    return head + array_dados + end



def main():
    try:
        print("Iniciou o main")
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
        if rxBuffer[-3:] == (b'\xff' * 3) and rxBuffer[9] == 1:
            print('envio dos pacotes iniciado')
            for i in range(len(pacotes)):
                print('entrou no for principal')
                print(f'enviando pacote {i} de {len(pacotes)-1}')

                #calcula CRC
                



                #head = monta_head(2,len(pacotes[i]),len_total=total_packs)#testar erro id
                head = monta_head(i,len(pacotes[i]),len_total=total_packs)

                #txBuffer = monta_pacote(head,(b'\x02' * 60)) # teste erro len pacote
                txBuffer = monta_pacote(head,pacotes[i])

                com3.sendData(np.asarray(txBuffer))

                time_inicio = time.time()

                while com3.rx.getBufferLen()< 16:
                    print('esperando')
                    time.sleep(2)
                    
                    if time.time() - time_inicio >= 6:
                        com3.sendData(np.asarray(txBuffer))
                        print(f'mandou denovo o pacote {i}')
                        time_inicio = time.time()
                    #com3.rx.clearBuffer()
                    pass 
                print('passou do while')

                rxBuffer, nRx = com3.getData(16)
                print('recebeu confirmacao do getdata')
                print(f'confirmacao {rxBuffer}')

                print(f'byte de check{rxBuffer[9]}')
                while rxBuffer[9] != 1:
                    print('envio com problema, montando e enviando de novo')
                    head = monta_head(i,len(pacotes[i]),len_total=total_packs)
                    txBuffer = monta_pacote(head,pacotes[i])

                    com3.sendData(np.asarray(txBuffer))
                    print('pacote reenviado')

                    while com3.rx.getBufferLen()< 16:
                        print('esperando resposta do servidor')
                        time.sleep(2)
                        pass 

                    rxBuffer, nRx = com3.getData(16)
                    print('recebeu resposta')


            #rxBuffer, nRx = com3.getData(12)
            if rxBuffer[11] == 1:
                print('transmissao bem sucedida')



        # Encerra comunicação
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
    
