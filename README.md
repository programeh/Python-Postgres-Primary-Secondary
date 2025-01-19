## api that generates terrafrom code and applies ansible playbook to setup postgres in primary secondary mode

### How to setup in local machine 
1. ensure that Terraform v1.5.6 is installed in your machine
2. ensure Python 3.13.1 is installed in your machine
3. ensure ansible-playbook [core 2.18.1] is installed in your machine
4. create a virtual env in python by using `python3 -m venv env` and `source env/bin/activate`
5. install the requirements.txt file by using command `pip3 install -r requirements.txt`



### Api details 
* `/generate-terraform` is used to generate the terraform file.It take json input as

```json
{
  "instance_type": "t2.small",
  "replica_count": 2,
  "region": "us-east-1"
}
```
* `/generate-terraform-plan` is used to get the plan result in json format, it doesn't take any inputs. It gives out the plan output in json format
* `/generate-terraform-apply` is used to get the apply result in json format. It gives out the apply output in json format
* `/apply_ansible_configuration` is used to setup the provisioned infrastructure to run postgres in primary secondary asynchronous replication.It takes json input
```json
{
  "replica_count": 2,
  "max_connections": 200,
  "shared_buffers": "256MB",
  "region": "us-east-1",
  "image_tag": "14-alpine"
}
```
This endpoint generates the inventory.ini file by using terraform outputs which is used to patch the instances to run postgres

### Architecture Overview 
Postgres runs in two modes when it comes to replication.
1. asynchronous - in this case there is a replication lag between the writes in primary and secondary
2. synchronous - in this there will be no replication lag between writes of primary and secondary

in postgres asyncronous replication is prefered as in synchronous mode it leads to entire cluster going down even if replica goes down.The next write is not proceesed untill the write is replicated to replica instances in syncronous mode.

currently I am using docker to run postgres , it is using host networking mode which means host and docker share same eni.
I am doing a physical replication between primary and secondary which means there is one to one mapping in the bytes getting copied between them.

> **Note:** by adding a lot of replicas we introduce overhead on network and cpu of primary , so it is a best practice to keep replicas below 5 for optimal performance

### why I choose docker?
* As I was facing issues with getting older versions of postgres , by using this approach I ensured that we can upgrade or down grade postgres to any version I want.

### source of information used to do this project
* [postgres tutorial](https://www.youtube.com/watch?v=Jm7deC0mOyY)
* [postgres tutorial 2 ](https://www.youtube.com/watch?v=UjrvaGvSCOI)

## future improvements 
* we can create a front end to this app so that it looks beautiful

## if you want to add more options in postgres primary
* just update the docker compose files of primary and secondary populate its values in inventory.ini


> **Note:** please use python version greater than 3.8 on client machines as ansible core gives error for python version lower than this. For this purpose I used amazon linux 2023 ami which has latest version of python preinstalled.





