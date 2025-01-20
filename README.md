## api that generates terrafrom code and applies ansible playbook to setup postgres in primary secondary mode

### How to setup in local machine 
1. ensure that Terraform v1.5.6 is installed in your machine
2. ensure Python 3.13.1 is installed in your machine
3. ensure ansible-playbook [core 2.18.1] is installed in your machine
4. create a virtual env in python by using `python3 -m venv env` and `source env/bin/activate`
5. install the requirements.txt file by using command `pip3 install -r requirements.txt`

### why Dockerized the entire application
To solve it runs on my machine problem , all you need to do is build the docker file , add env variables with
```bash
    docker run -e AWS_ACCESS_KEY_ID="<replace value>" \
               -e AWS_SECRET_ACCESS_KEY="<replace value>" \
               -p 127.0.0.1:8080:5000 asutoshgha/postgresps:v15
```

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
* just update the docker compose files of primary and secondary populate its values in inventory.ini , take input in `/apply_ansible_configuration` api and generate inventory.ini dynamically

## Validating if replication is happening or not.
```bash 
   postgres=> SELECT * FROM pg_stat_replication
postgres-> ;
 pid | usesysid |  usename   | application_name |  client_addr  | client_hostname | client_port |         backend_start         | backend_xmin | state | sent_lsn | write_lsn | flush_lsn | replay_lsn | write_lag | flush_lag | replay_lag | sync_priority | sync_state | reply_time
-----+----------+------------+------------------+---------------+-----------------+-------------+-------------------------------+--------------+-------+----------+-----------+-----------+------------+-----------+-----------+------------+---------------+------------+------------
 107 |    16384 | replicator | walreceiver      | 172.31.42.250 |                 |       41308 | 2025-01-20 17:35:38.560571+00 |          |       |          |           |           |            |           |           |            |               |            |
 110 |    16384 | replicator | walreceiver      | 172.31.43.203 |                 |       38168 | 2025-01-20 17:35:39.908+00    |          |       |          |           |           |            |           |           |            |               |            |
(2 rows)

postgres=> SELECT * FROM pg_replication_slots;
     slot_name      | plugin | slot_type | datoid | database | temporary | active | active_pid | xmin | catalog_xmin | restart_lsn |confirmed_flush_lsn | wal_status | safe_wal_size | two_phase
--------------------+--------+-----------+--------+----------+-----------+--------+------------+------+--------------+-------------+---------------------+------------+---------------+-----------
 replication_slot_0 |        | physical  |        |          | f         | t      |        110 |      |              | 0/8000148   |                    | reserved   |               | f
 replication_slot_1 |        | physical  |        |          | f         | t      |        107 |      |              | 0/8000148   |                    | reserved   |               | f
(2 rows)
```
By running these two commands it validates that there are replication slots and 2 replicas being connected with primary

one other way would be to just create a table and see if it is getting replicated with replicas 

```sql
   CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    age INTEGER NOT NULL,
    department VARCHAR(50)
);

INSERT INTO employees (name, age, department)
VALUES 
    ('Bob', 25, 'Engineering'),
    ('Charlie', 35, 'Marketing'),
    ('Diana', 40, 'Finance');
```

run these two commands and check if it is getting replicated. After these commads are executed in primary it got replicated in secondary.
```bash
ip-172-31-42-250:/$ ls
bin                         lib                         root                        tmp
dev                         media                       run                         usr
docker-entrypoint-initdb.d  mnt                         sbin                        var
etc                         opt                         srv
home                        proc                        sys
ip-172-31-42-250:/$ psql -U replicator -d postgres
psql (14.15)
Type "help" for help.

postgres=> select * from employees
postgres-> ;
 id |  name   | age | department
----+---------+-----+-------------
  1 | Bob     |  25 | Engineering
  2 | Charlie |  35 | Marketing
  3 | Diana   |  40 | Finance
(3 rows)

postgres=>
```


> **Note:** please use python version greater than 3.8 on client machines as ansible core gives error for python version lower than this. For this purpose I used amazon linux 2023 ami which has latest version of python preinstalled.





