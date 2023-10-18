FROM alpine:3.18.4

RUN apk update
RUN apk upgrade

#install FFMPEG
RUN apk add --no-cache ffmpeg

#Install PIP3 for python 3.11
RUN apk add py3-pip

#Install s3cmd to send encoded files to Object StorGihuage
RUN pip3 install s3cmd

#Backup for FFMPEG default configuration
RUN mkdir /home/backup

#Object Storage Configuration File - REMEMBER TO EDIT IT
COPY /source/.s3cfg /root/

COPY /source/FFMPEG_bash.sh /home/backup
COPY /source/FFMPEG_bash.sh /home
COPY /source/script.py /home

#Execute Python Script to fetch data from OBJ Storage folder to
CMD python3 home/script.py
