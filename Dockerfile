FROM ubuntu:22.04
 
LABEL maintainer="Sindre Henriksen <sid.henriksen@gmail.com>"
 
ENV DEBIAN_FRONTEND=noninteractive
 
RUN adduser uwsgi
 
RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev uwsgi uwsgi-plugin-python3 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
 
RUN mkdir app && chown -R uwsgi app && chgrp -R uwsgi app
COPY /requirements.txt /app/requirements.txt
 
WORKDIR /app
 
RUN pip3 install --no-cache-dir -r requirements.txt
 
COPY . /app
 
RUN mkdir /data
 
RUN chown -R uwsgi /app /data && \
    chgrp -R uwsgi /app /data
 
EXPOSE 8183
 
WORKDIR /app/app
CMD [ "uwsgi_python3", "--ini", "uwsgi.ini" ]