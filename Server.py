#####################################################
# Camada Física da Computação
#Carareto
#11/08/2022
#Aplicação
####################################################


#esta é a camada superior, de aplicação do seu software de comunicação serial UART.
#para acompanhar a execução e identificar erros, construa prints ao longo do código! 


from enlace import *
import time
import numpy as np
import struct
from Client import monta_head,monta_pacote,log_event,log_end_of_transmission
import crcmod
import datetime

# voce deverá descomentar e configurar a porta com através da qual ira fazer comunicaçao
#   para saber a sua porta, execute no terminal :
#   python -m serial.tools.list_ports
# se estiver usando windows, o gerenciador de dispositivos informa a porta

#use uma das 3 opcoes para atribuir à variável a porta usada
#serialName = "/dev/ttyACM0"           # Ubuntu (variacao de)
#serialName = "/dev/tty.usbmodem1411" # Mac    (variacao de)
serialName = "COM5"                  # Windows(variacao de)
crc16_func = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, xorOut=0x000)


def main():
    try:
        print("Iniciou o main")
        file_server = 'registro_server.txt'
        file_server = open(file_server, 'w')
        #declaramos um objeto do tipo enlace com o nome "com". Essa é a camada inferior à aplicação. Observe que um parametro
        #para declarar esse objeto é o nome da porta.
        com5 = enlace(serialName)
    
        # Ativa comunicacao. Inicia os threads e a comunicação seiral 
        com5.enable()
        print("esperando 1 byte de sacrifício")
        rxBuffer, nRx = com5.getData(1)
        com5.rx.clearBuffer()
        time.sleep(.1)

        print("Servidor pronto para receber conexões...")

        # time.sleep(20) # ----> Para testar conceito B 
        
        imageW = './img/imagemcopiado.png' #a ser salva
        rx_all_buffer = bytearray()
        last_package_num = -1

        print("Aguardando handshake...")
        rxBuffer, nRx = com5.getData(15)
        print('Recebeu handshake') 
        print(rxBuffer)       
        if rxBuffer[-3:] == b'\xff' * 3:
            if rxBuffer[8] == 1:  # Verifica se o byte 9 é o handshake
                print("Handshake recebido")
                hs_confirm_head = monta_head(0, 15, 1)
                hs_confirm = hs_confirm_head + (b'\xff' * 3)
                total_packs = rxBuffer[10]
                print(hs_confirm)
                com5.sendData(np.asarray(hs_confirm))
                print(f"Confirmação do handshake enviada {total_packs}")
    
            while True:
                #file_server = 'registro_server.txt'
                print('entrou no loop principal')

                head, _ = com5.getData(12)
                package_num =  struct.unpack('>I', head[:4])[0]  # Número do pacote
                print(f'pacote :{package_num}')
                total_packs =  head[10]  # Total de pacotes
                print(f'total:{total_packs}')
                pacote_size = int.from_bytes(head[4:6], byteorder='big')
                print(f'tamanho:{pacote_size}')
                CRC_esperado = int.from_bytes(head[6:8], byteorder='big')
                print(f'CRC esperado{CRC_esperado}')


                pacote, _ = com5.getData(pacote_size + 3)
                print(f'recebeu {pacote}')
                print(f' numero do pacote: {package_num} numero do ultimo pacote: {last_package_num}' )
                print(f'final do pacote: {pacote[-3:]}')
                print(f'condicao 1 numero do pacote {package_num == last_package_num + 1}')
                print(f'condicao 2 end of package {pacote[-3:] == (b'\xff' * 3)}')

                #calulando CRC
                CRC_calculado = crc16_func(pacote[:-3])
                #CRC_calculado = 3 ----------- teste de erro
                print(f'condicao 3 CRC iguais {CRC_calculado == CRC_esperado}')                

                # Verifica se o número do pacote está correto e se o EOP está no local correto
                if (package_num == last_package_num + 1) and (pacote[-3:] == (b'\xff' * 3)) and CRC_calculado == CRC_esperado:
                    print('verificação correta')
                    log_event(file_server,'receb', 3, 16, pacote_num=package_num, total_packs=total_packs, crc=CRC_esperado)
                    
                    rx_all_buffer.extend(pacote[:-3])  # Adiciona o payload ao buffer (exclui o EOP)
                    
                    if package_num == total_packs - 1:  # Último pacote
                        print(f"Pacote {package_num} de {total_packs-1} recebido. Reagrupando e salvando o arquivo...")
                        with open(imageW, 'wb') as f:
                            f.write(rx_all_buffer)
                        print("Arquivo salvo com sucesso.")
                        
                        end_confirm_head = monta_head(0, 12, 1, check=b'\x01', final=b'\x01')
                        end_confirm = monta_pacote(end_confirm_head, b'\x00')

                        com5.sendData(np.asarray(end_confirm))  # Bloco de envio OK
                        log_event(file_server, 'envio', 4, 16)

                        print("Confirmação de transmissão finalizada enviada.")
                        break
                    else:
                        resp_head = monta_head(package_num, 1, total_packs)  # Confirmação correta
                        resp = monta_pacote(resp_head, b'\x00')

                        com5.sendData(np.asarray(resp))  # Bloco de envio OK
                        log_event(file_server, 'envio', 4, 16)

                        print(f'Mandou uma resposta: {resp}')
                        print(f"Pacote {package_num} de {total_packs-1} recebido. Solicitação do próximo pacote.")
                        last_package_num = package_num
                else:
                    # Pacote fora de ordem ou erro de CRC
                    log_event(file_server, 'receb', 5, 16)
                    
                    if (package_num != last_package_num + 1):  # Pacote fora de ordem
                        correct_num = last_package_num + 1
                        print(f"Pacote fora de ordem! Esperado: {correct_num}, Recebido: {package_num}")
                        
                        ack = monta_head(correct_num, 1, total_packs, check=b'\xf0')  # Solicitação de reenvio do pacote correto
                        w = monta_pacote(ack, b'\x00')
                        com5.sendData(np.asarray(w))
                        
                        log_event(file_server, 'envio', 5, 16)
                        print(f"Solicitação de reenvio do pacote {correct_num} enviada.")
                    else:
                        # Erro de CRC
                        print("Erro de CRC ou problema no EOP!")
                        ack = monta_head(package_num, 1, total_packs, check=b'\xf0')  # Solicitação de reenvio por erro de CRC
                        w = monta_pacote(ack, b'\x00')
                        com5.sendData(np.asarray(w))
                        
                        log_event(file_server, 'envio', 5, 16)
                        print(f"Solicitação de reenvio por erro de CRC ou EOP do pacote {package_num}.")


        # Encerra comunicação
        log_end_of_transmission(file_server)
        file_server.close()

        print("-------------------------")
        print("Comunicação encerrada")
        print("-------------------------")
        com5.disable()
        
    except Exception as erro:
        print("ops! :-\\")
        print(erro)
        com5.disable()
        

    #so roda o main quando for executado do terminal ... se for chamado dentro de outro modulo nao roda
if __name__ == "__main__":
    main()
