# Introduction

This is a demo project for education/training purposes of transcoding for videos on demand from MP4 to HLS

This project is based on a VM runing on Akamai cloud (A.K.A Linode) running docker, and Akamai Cloud's Object Storage (bucket).
The process is the Docker container downloading the MP4 files from the Akamai Cloud's Object Storage Intake folder, and then uploading the converted HLS files into an Output folder.

The code **expects** the organization below (the output content folders and files will be generated after execution):

![image](https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/d04719e1-410a-4e8f-a2e7-2c0791b08309)

## Requirements

1. A Akamai Cloud (Linode) [account](https://login.linode.com/signup)
1. An object storage ![image](https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/1140fdbc-1c51-4ec6-9945-bc7a327915f2)
1. Creation of 2 Folders inside the created object storage, this will be the "Input" folder, were the MP4 files to be converted will be storaged and the "Output" folder, were the HLS files will be storaged ready for delivery (Intake and Output for example)![image](https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/1526dbbd-3e62-4dff-bd41-461d106ac095)
1. The following Keys and Access tokens with READ and WRITE permissions:
   * **BUCKET ACCESS KEY:** Can be found in the "Access Keys" [tab](https://cloud.linode.com/object-storage/access-keys) (this tab is outside the bucket) ![image](https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/73d8e36b-a20a-4039-a015-e4b1a362d954)
   * **BUCKET SECRET KEY:** When generating a new Access Key the Secret Key is displayed
     <img src = "https://github.com/acehalk/ffmpeg-linode-docker/assets/2445293/8b4452e8-28ff-406f-acb4-e20d659a1cd1" width =500 height = 350></br>
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

os.system("mkdir -p /home/output/")
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
```
Keep in mind the folder's expected schema, displayed on the first picture [(the SmartArt)](README.md#introduction)
Here we set:
* The name of the Bucket (Orange box) with the variable: ```bucketName```
* The control folders (Yellow boxes) with the variables: ```bucket_intakeFolder``` and ```bucket_outputFolder```
* The FFMPEG root intake folder (not in diagram) with the variable ```container_intakeRootFolder```
* The FFMPEG input folder (not in diagram), when dowloading the files from the Object Storage, a new folder with the name of the object storage Input Folder (```bucket_intakeFolder``` variable) will be created on the ```container_intakeRootFolder``` path, that will be the path that FFMPEG needs to gather the MP4 files from. So the variable ```container_intakeFolder``` is set as the concatenation of ```container_intakeRootFolder``` and ```bucket_intakeFolder```
* The FFMPEG ouput folder (not in diagram), with the variable ```container_outputFolder```, after the conversion the files on that folder will be uploaded to the Object Storage Output folder (```bucket_outputFolder``` variable)


