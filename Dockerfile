FROM frolvlad/alpine-python3:latest

RUN apk update && apk upgrade && \
    apk add --no-cache bash git openssh && \
    pip3 install troposphere && \
    pip3 install git+https://github.com/jpotecki/TroposphereWrapper.git

COPY createCF.py /pythonfile

RUN ENV cf /pythonfile/createCF.py
