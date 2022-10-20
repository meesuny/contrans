# syntax=docker/dockerfile:1
 
FROM python:3.10.7-bullseye
 
COPY requirements.txt .
 
RUN pip install -r requirements.txt

RUN curl -fsSL https://deb.nodesource.com/setup_19.x | bash - &&\
apt-get install -y nodejs

 RUN npm install -g dbdocs
 
WORKDIR /contrans
 
EXPOSE 8888
 
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--allow-root"]
