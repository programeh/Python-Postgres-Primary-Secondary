FROM python:3.9.21-alpine3.20
MAINTAINER Asutosh Ghanto <asutoshghanto23@gmail.com>

ENV TERRAFROM_VERSION="1.5.6"

RUN apk add wget unzip && \
        wget https://releases.hashicorp.com/terraform/${TERRAFROM_VERSION}/terraform_${TERRAFROM_VERSION}_linux_amd64.zip && \
        unzip terraform_${TERRAFROM_VERSION}_linux_amd64.zip  &&\
        mv terraform /usr/local/bin/ && \
        rm terraform_${TERRAFROM_VERSION}_linux_amd64.zip

WORKDIR /app

COPY main.py requirements.txt terraform_template.j2 LoggerTemplate.py /app/

RUN mkdir -p terrafrom/ansible && \
    mkdir -p terrafrom/ansible/primary && \
    mkdir -p terrafrom/ansible/secondary && \
    apk update  && \
    apk add py3-pip openssh build-base sqlite sqlite-dev gcc musl-dev libffi-dev && \
    pip3 install -r requirements.txt

# copy the docker compose files , ansible default config and ansible playbook
COPY terraform/ansible/primary/ terrafrom/ansible/primary
COPY terraform/ansible/secondary/ terrafrom/ansible/secondary
COPY terraform/ansible/ansible.cfg  terraform/ansible/bootstrap_postgress.yml terrafrom/ansible


EXPOSE 5000

ENTRYPOINT ["python3", "main.py"]





