import subprocess
import os

os.system("mkdir -p /home/output/")
#Baixar os arquivos do objstorage pra poder ter como controlar e deixar a exec aqui

#====================== Variaveis Globais

folder = "test" # intake folder will be the output folder /intake/video-folder -> /output/video-folder
bucketName = "vod-videos"
bucket_intakeFolder = "Intake"
bucket_outputFolder = "Output"
container_intakeFolder = "/home/Intake"# o final intake vai vir no dowload do bucket intake"
container_intakeRootFolder = "/home"# o final intake vai vir no dowload do bucket intake"
container_outputFolder = "/home/output"

#====================== Funções ===================================

#Editar o arquivo base do FFMPEG
def FFMPEG_Config(intake_path,output_path = "/home/output/Stream-%v.m3u8",config_base_path = "/home/edit_bash.sh",master_playlist_name = "Master-pl.m3u8"): 
    with open(config_base_path, "r") as READ_FFMPEG_CONFIG:
        saida = READ_FFMPEG_CONFIG.read()
        saida = saida.replace("INTAKE",intake_path)
        saida = saida.replace("MASTER_PL" ,master_playlist_name)
        saida = saida.replace("OUTPUT",output_path)
        READ_FFMPEG_CONFIG.close()

    with open(config_base_path, "w") as FFMPEG_CONFIG:
        FFMPEG_CONFIG.write(saida)
        FFMPEG_CONFIG.close()

#====================== Coleta do Object Storage ===================================

os.system("s3cmd get --recursive s3://" + bucketName + "/" + bucket_intakeFolder + " " + container_intakeRootFolder) #baixa videos do S3
#os.remove(container_intakeFolder)#ele cria um arquivo com o nome da pasta
print("\n")
print("Download Completed")
print("\n")

#====================== Transcoding e envio ao Object Storage ===================================
listaDiretorios = os.listdir(os.path.join(container_intakeRootFolder,bucket_intakeFolder))

for pastas in listaDiretorios:
    diretorioTrabalho = os.path.join(container_intakeFolder,pastas)

    if os.path.isdir(diretorioTrabalho):
            
            for arquivos in os.listdir(diretorioTrabalho):
                os.system("cp /home/FFMPEG_bash.sh /home/edit_bash.sh") #copia o arquivo com as tags que o python substitui
                os.system("chmod 777 /home/edit_bash.sh") #IMPORTANTE
                FFMPEG_Config(os.path.join(diretorioTrabalho,arquivos),"/home/output/" + pastas + "/Stream-%v.m3u8","/home/edit_bash.sh")
                os.system("mkdir -p /home/output/" + pastas)
                #print("FFMPEG " + os.path.join(diretorioTrabalho,arquivos) + " | saida = /home/output/" + pastas)
                subprocess.call("/home/edit_bash.sh", shell=True)  #Roda o FFMPEG, subprocess pra nao matar o container dps de rodar o FFMPEG
                os.system("rm /home/edit_bash.sh") #apaga o arquivo que o python substituiu

print("\n")
print("Transcode Completed")
print("\n")

listaDiretorios = os.listdir(container_outputFolder)#FFMPEG output path
for pastas in listaDiretorios:
    diretorioTrabalho = os.path.join(container_outputFolder,pastas)

    if os.path.isdir(diretorioTrabalho):

        for arquivos in os.listdir(diretorioTrabalho):
            file = os.path.join(diretorioTrabalho, arquivos)
            if os.path.isfile(file):
                os.system("s3cmd put --acl-public " + file +" s3://vod-videos/Output/" + pastas + "/")

print("\n")
print("Upload Completed")
print("\n")

os.system("rm -r /home/Intake") #Apaga os videos baixados do object storage
os.system("rm -r /home/output")#apagar output
