# Introduction

This is a demo project for education/training purposes of transcoding for videos on demand from MP4 to HLS

This project is based on a VM runing on Akamai cloud (A.K.A Linode) running docker, and Akamai Cloud's Object Storage (bucket).
The process is the Docker container downloading the MP4 files from the Akamai Cloud's Object Storage Intake folder, and then uploading the converted HLS files into an Output folder.

The code **expects** the organization below (the output content folders and files will be generated after execution):

![image](https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/9988daed-d5ee-414f-a866-aeb61c41d1ec)

## Requirements

1. A Akamai Cloud (Linode) [account](https://login.linode.com/signup)
1. An object storage ![image](https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/57ff2511-2b13-40bc-9e15-be6067990c8e)
1. Creation of 2 Folders inside the created object storage, this will be the "Input" folder, were the MP4 files to be converted will be storaged and the "Output" folder, were the HLS files will be storaged ready for delivery (Intake and Output for example), this 2 folder names needs to be changed in the Python code ![image](https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/1cf09f6e-7ce3-4a97-aaf1-7bddf85ff867)
1. The following Keys and Access tokens with READ and WRITE permissions:
   * **BUCKET ACCESS KEY:** Can be found in the "Access Keys" [tab](https://cloud.linode.com/object-storage/access-keys) (this tab is outside the bucket) ![image](https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/3bc05b97-5d84-4fc4-9dcd-c0e1e683d502)
   * **BUCKET SECRET KEY:** When generating a new Access Key the Secret Key is displayed
     <img src = "https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/86028ccf-2e72-4914-9d73-50ed2287ceb3" width =500 height = 350></br>
   * **CLUSTER ID:** Can be found in the URL of the bucket, in my case:  _cloud.linode.com/object-storage/buckets/**us-southeast-1**/vod-videos_
     > were "us-southeast-1" is the cluster ID
   
1. With the information from the step above edit the [.s3cfg config file](source/.s3cfg), replacing the text inside double brackets [[term]] with the correct information (without the double brackets):
   * [[BUCKET ACCESS KEY]] on line 2
   * [[CLUSTER ID]] on line 36 and 37
   * [[BUCKET SECRET KEY]] on line 66

## FFMPEG Code

The FFMPEG code that will do the transcoding create 4 separeted streams with different video bitrates:
* 360p (480,360)px at 0,6 Mb/s
* 480p (640,480)px at 0,8 Mb/s
* 720p (1280,720)px at 1,0 Mb/s
* 1080p (1920,1080)px at 2,0 Mb/s

The Master Playlist will have all the 4 playlists (one for each stream)

```
ffmpeg -i "INTAKE" -loglevel debug -map 0:v:0 -map 0:a:0 -map 0:v:0 -map 0:a:0 -map 0:v:0 -map 0:a:0 -map 0:v:0 -map 0:a:0 -c:v libx264 -crf 22 -c:a aac -ar 48000 -filter:v:0 scale=w=480:h=360  -maxrate:v:0 600k -b:a:0 64k -filter:v:1 scale=w=640:h=480  -maxrate:v:1 800k -b:a:1 128k -filter:v:2 scale=w=1280:h=720 -maxrate:v:2 1M -b:a:2 128k -filter:v:3 scale=w=1920:h=1080 -maxrate:v:3 2M -b:a:3 320k -var_stream_map "v:0,a:0,name:360p v:1,a:1,name:480p v:2,a:2,name:720p v:3,a:3,name:1080p" -force_key_frames:v "expr:gte(t,n_forced*2)" -preset slow -hls_list_size 0 -threads 0 -f hls -hls_playlist_type event -hls_time 6 -hls_flags independent_segments -master_pl_name "MASTER_PL" "OUTPUT"
```
This command is stored in the [FFMPEG_bash.sh](source/FFMPEG_bash.sh) file, and is changed for every video file during execution

# Code explanation

## Python Script

This is the [script.py](source/script.py) file

### Libraries
```python
import subprocess
import os
```
_subprocess_ is imported to allow the execution of the [FFMPEG_code](source/FFMPEG_bash.sh) without stopping the container after the execution
_os_ is imported to allow the manipulation of files/paths

### Global Variables

```python
bucketName = "vod-videos" #Bucket (object Storage) Created on Akamai Cloud
bucket_intakeFolder = "Intake" #folder inside bucketName (set above) that will have folders with .mp4 files
bucket_outputFolder = "Output" # folder inside bucketName (set above) that will have folders with the converted files
#FFMPEG output folders - Change not required
container_intakeRootFolder = "/home/" #Were in the container the MP4 Videos will be downloaded to (need to end on "/")
container_intakeFolder = container_intakeRootFolder + bucket_intakeFolder #after dowloading the video will be stored on a folder with the name of the Object storage folder name
container_outputFolder = "/home/output" #Were in the container the converted Videos will be stored

os.system("mkdir -p "+ container_outputFolder) #Create the folder to store the converted videos, need to be created here because this folder is deleted after the conversion of all videos
```
Keep in mind the folder's expected schema, displayed on the first picture [(the SmartArt)](README.md#introduction)
Here we set:
* The name of the Bucket (Orange box) with the variable: ```bucketName```
* The control folders (Yellow boxes) with the variables: ```bucket_intakeFolder``` and ```bucket_outputFolder```
* The FFMPEG root intake folder (not in diagram) with the variable ```container_intakeRootFolder```
* The FFMPEG input folder (not in diagram), when dowloading the files from the Object Storage, a new folder with the name of the object storage Input Folder (```bucket_intakeFolder``` variable) will be created on the ```container_intakeRootFolder``` path, that will be the path that FFMPEG needs to gather the MP4 files from. So the variable ```container_intakeFolder``` is set as the concatenation of ```container_intakeRootFolder``` and ```bucket_intakeFolder```
* The FFMPEG ouput folder (not in diagram), with the variable ```container_outputFolder```, after the conversion the files on that folder will be uploaded to the Object Storage Output folder (```bucket_outputFolder``` variable)

The MkDir command needs to be executed here because after the convertion of all files the output folder in ```container_outputFolder```, as well as the files, are deleted

### FFMPEG Function
Passing the FFMPEG Command via Python or Docker CMD/EXEC is hard, so i will be creating a shell file containing the command.
This command will be customized by the python code for every video.

```python
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
```
Here we create a funcion with 4 parameters:
* ```intake_path```: This is the MP4 video path that FFMPEG needs to convert
* ```output_path```: This is the output path were the HLS files (.ts and .m3u8 playlists) will be stored after conversion, the "%v" will be the name of the stream for example: Stream-1080p.m3u8, Stream-1080p21.ts, Stream-1080p22.ts
* ```config_base_path```: This is the master [FFMPEG script](source/FFMPEG_bash.sh) file path, it's changed in every iteration of the loop (for every video)
* ```master_playlist_name```: The name of the master playlist that will be delivered by the distribution plataform, in my example will be [Akamai Adaptative Media Delivery (AMD)](https://www.akamai.com/products/adaptive-media-delivery)

Then the [FFMPEG script](source/FFMPEG_bash.sh) is opened as "read-only" and some keywords are changed in the document, based on the parameters of the just defined function. It's always important to close the file aftwards.
The [FFMPEG script](source/FFMPEG_bash.sh) is opened once again, but this time as "Writable", and saved with the information changed on the last step.
I chose to open the file in 2 steps as a safety precaution against corruption

### Download from Object Storage

```python
os.system("s3cmd get --recursive s3://" + bucketName + "/" + bucket_intakeFolder + " " + container_intakeRootFolder) #Download the MP4 files from Akamai Cloud
print("\n")
print("Download Completed")
print("\n")
```

The folders containing the MP4 files are downloaded from the object storage, keep in mind the **required** folder schema described on the first picture [(the SmartArt)](README.md#introduction)

### Transcoding

```python
listaDiretorios = os.listdir(container_intakeFolder)

for pastas in listaDiretorios:
    diretorioTrabalho = os.path.join(container_intakeFolder,pastas)

    if os.path.isdir(diretorioTrabalho):
            
            for arquivos in os.listdir(diretorioTrabalho):
                os.system("cp /home/FFMPEG_bash.sh /home/edit_bash.sh") #copy the FFMPEG config backup file to a new place to be edited in every iteration
                os.system("chmod 777 /home/edit_bash.sh") #IMPORTANT!
                FFMPEG_Config(os.path.join(diretorioTrabalho,arquivos),container_outputFolder + pastas + "/Stream-%v.m3u8","/home/edit_bash.sh")#Intake Path, Output Path,FFMPEG script to be edited path, Master playlist name
                os.system("mkdir -p " + container_outputFolder + pastas)
                subprocess.call("/home/edit_bash.sh", shell=True)  #Runs FFMPEG, need to be a subprocess not to stop the container after execution
                os.system("rm /home/edit_bash.sh") #remove the FFMPEG config file Python edited in this iteration

print("\n")
print("Transcode Completed")
print("\n")
```
This part is responsible for the transcoding itself using FFMPEG. Again keep in mind the **required** folder schema described on the first picture [(the SmartArt)](README.md#introduction) 
First we list all the directories in the ```container_intakeFolder``` in my case /home/Intake. Then this list is iterated and then cheked if the appended path from ```container_intakeFolder``` and the iterated list string (```pastas```) form a directory or not, for example: _/home/Intake/Gameplay-LeagueOfLegends_, in the [(SmartArt)](README.md#introduction) diagram we're now checking the folders in blue , if it's not a directory the file is ignorated.

Once again we list all the files inside the now confirmed directory, in the [(SmartArt)](README.md#introduction) diagram we're now checking the files in green, for example: _/home/Intake/Gameplay-LeagueOfLegends/RekSai-Jungle-02-12-23.mp4_
It now copy the base [FFMPEG script](source/FFMPEG_bash.sh) and create a new version that will be edited in this iteration, as we're copying a Shell file the Linux CHMOD with execute (X) permission is required.
The FFMPEG script is edited with this iteration information.

A new folder is created inside the output folder to store the converted files, this will new folder will be named as the name of the content folder the MP4 was stored (folder in blue in the diagram). in my example:
* Input: /home/Intake/**Gameplay-LeagueOfLegends**/RekSai-Jungle-02-12-23.mp4
* Output: /home/Output/**Gameplay-LeagueOfLegends**/*
FFMPEG is finally executed as a subprocess to not stop the container after execution
After convertion the edited FFMPEG scipt is removed.

### Upload to Object Storage

```python
listaDiretorios = os.listdir(container_outputFolder)#FFMPEG output path
for pastas in listaDiretorios:
    diretorioTrabalho = os.path.join(container_outputFolder,pastas)

    if os.path.isdir(diretorioTrabalho):

        for arquivos in os.listdir(diretorioTrabalho):
            file = os.path.join(diretorioTrabalho, arquivos)
            if os.path.isfile(file):
                os.system("s3cmd put --acl-public " + file +" s3://vod-videos/" + bucket_outputFolder + "/" + pastas + "/")#upload as public file

print("\n")
print("Upload Completed")
print("\n")

os.system("rm -r " + container_intakeFolder)#Remove the files downloaded from object storage
os.system("rm -r " + container_outputFolder)#Remove the converted files after object storage upload 
```
After the conversion we need to upload the files to the object storage, this way we can deliver them to our endusers.
The FOR loop is similar to the Transcoding part

First we list all the directories in the ```container_outputFolder``` in my case /home/output. Then this list is iterated and then cheked if the appended path from ```container_outputFolder``` and the iterated list string (```pastas```) form a directory or not, for example: _/home/output/Gameplay-LeagueOfLegends_, in the [(SmartArt)](README.md#introduction) diagram we're now checking the folders in blue in the output side, if it's not a directory the file is ignorated.

Once again we list all the files inside the now confirmed directory, in the [(SmartArt)](README.md#introduction) diagram we're now checking the files in green in the output side, for example: _/home/output/Gameplay-LeagueOfLegends/Stream-720p321.ts_
The files (Master Playlist, the manifests for every exported Bitrate/Resolution, and the Chunks (.ts files)) are then uploaded to the Bucket as **PUBLIC** files
Finally the downloaded and uploaded files from/to the object storage are removed to save space in the container
