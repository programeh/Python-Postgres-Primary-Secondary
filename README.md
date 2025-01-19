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
* `/apply_ansible_configuration` is used to setup the provisioned infrastructure to run postgres in primary secondary asynchronous replication.It take json input
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