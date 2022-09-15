# syntax=docker/dockerfile:1
 
FROM python:3.10.7-bullseye
 
COPY requirements.txt .
 
RUN pip install -r requirements.txt
 
WORKDIR /contrans
 
EXPOSE 8888
 
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--allow-root"]
