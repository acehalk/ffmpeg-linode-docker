import subprocess
import os

os.system("mkdir -p /home/output/")

#====================== Global Variables ====================== 

bucketName = "vod-videos" #Bucket (object Storage) Created on Akamai Cloud
bucket_intakeFolder = "Intake" #folder inside bucketName (set above) that will have folders with .mp4 files
bucket_outputFolder = "Output" # folder inside bucketName (set above) that will have folders with the converted files

#This is the Object Storage expected structure:

#bucketName
#|
#|->bucket_intakeFolder
#|  |->Folder A
#|  |  |->Video1.mp4
#|  |->Folder B
#|       |->Video2.mp4
#|
#|->bucket_outputFolder
#   |->Folder A
#   |  |->HLS files for Video1
#   |->Folder B
#      |->HLS files for Video2

#FFMPEG output folders - Change not required
container_intakeRootFolder = "/home/" #Were in the container the MP4 Videos will be downloaded to (need to end on "/")
container_intakeFolder = container_intakeRootFolder + bucket_intakeFolder #after dowloading the video will be stored on a folder with the name of the Object storage folder name
container_outputFolder = "/home/output" #Were in the container the converted Videos will be stored

#====================== Functions ====================== 

#Edit base FFMPEG script file
def FFMPEG_Config(intake_path,output_path = "/home/output/Stream-%v.m3u8",config_base_path = "/home/edit_bash.sh",master_playlist_name = "Master-pl.m3u8"): 
    with open(config_base_path, "r") as READ_FFMPEG_CONFIG:
        saida = READ_FFMPEG_CONFIG.read()
        #Search for keywords inside the "edit_bash.sh" file
        saida = saida.replace("INTAKE",intake_path)
        saida = saida.replace("MASTER_PL" ,master_playlist_name)
        saida = saida.replace("OUTPUT",output_path)
        READ_FFMPEG_CONFIG.close()

    with open(config_base_path, "w") as FFMPEG_CONFIG:
        FFMPEG_CONFIG.write(saida)
        FFMPEG_CONFIG.close()
        #Changes written down

#====================== Download from Object Storage ====================== 

os.system("s3cmd get --recursive s3://" + bucketName + "/" + bucket_intakeFolder + " " + container_intakeRootFolder) #Download the MP4 files from Akamai Cloud
print("\n")
print("Download Completed")
print("\n")

#====================== Transcoding ====================== 

listaDiretorios = os.listdir(os.path.join(container_intakeRootFolder,bucket_intakeFolder))

for pastas in listaDiretorios:
    diretorioTrabalho = os.path.join(container_intakeFolder,pastas)

    if os.path.isdir(diretorioTrabalho):
            
            for arquivos in os.listdir(diretorioTrabalho):
                os.system("cp /home/FFMPEG_bash.sh /home/edit_bash.sh") #copy the FFMPEG config backup file to a new place to be edited in every iteration
                os.system("chmod 777 /home/edit_bash.sh") #IMPORTANT!
                FFMPEG_Config(os.path.join(diretorioTrabalho,arquivos),"/home/output/" + pastas + "/Stream-%v.m3u8","/home/edit_bash.sh")#Intake Path, Output Path,FFMPEG script to be edited path, Master playlist name
                os.system("mkdir -p /home/output/" + pastas)
                subprocess.call("/home/edit_bash.sh", shell=True)  #Runs FFMPEG, need to be a subprocess not to stop the container after execution
                os.system("rm /home/edit_bash.sh") #remove the FFMPEG config file Python edited in this iteration

print("\n")
print("Transcode Completed")
print("\n")

#====================== Upload to Object Storage ====================== 

listaDiretorios = os.listdir(container_outputFolder)#FFMPEG output path
for pastas in listaDiretorios:
    diretorioTrabalho = os.path.join(container_outputFolder,pastas)

    if os.path.isdir(diretorioTrabalho):

        for arquivos in os.listdir(diretorioTrabalho):
            file = os.path.join(diretorioTrabalho, arquivos)
            if os.path.isfile(file):
                os.system("s3cmd put --acl-public " + file +" s3://vod-videos/Output/" + pastas + "/")#upload as public file

print("\n")
print("Upload Completed")
print("\n")

os.system("rm -r /home/Intake")#Remove the files downloaded from object storage
os.system("rm -r /home/output")#Remove the converted files after object storage upload
