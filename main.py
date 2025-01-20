from flask import Flask, request, jsonify
from LoggerTemplate import get_logger
from jinja2 import Template
import os
import subprocess
import json
import sys
import ansible_runner
import sqlite3

app = Flask(__name__)

max_connections=100
shared_buffers='128MB'
TERRAFORM_DIR = "/app/terrafrom"
ANSIBLE_DIR="/app/terrafrom/ansible"
replica_count=1

# Initialize the database (run this once to set up the DB)
def init_db():
    with sqlite3.connect("/app/logs.db") as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS logs (timestamp TEXT, log_message TEXT)")
        conn.commit()

def is_terraform_initialized():
    return os.path.isdir(os.path.join(TERRAFORM_DIR, ".terraform"))

def run_terraform_command(command,logger,cmd=None):
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cmd)
        logger.info(result.stdout.decode())
        return result.stdout.decode()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running command: {' '.join(command)}")
        logger.error(e.stderr.decode())
        return None

    except FileNotFoundError as e:
        # Handle case where Terraform is not found (e.g., Terraform is not installed)
        logger.error(f"FileNotFoundError: {e}")
        logger.error("Ensure Terraform is installed and available in your system PATH.")
        return None

    except Exception as e:
        # Catch any other exceptions
        logger.error(f"An unexpected error occurred: {e}")
        return None

@app.route('/logs', methods=['POST'])
def receive_logs():
    log_data = request.json
    if log_data:
        log_message = log_data.get("log")
        timestamp = log_data.get("timestamp")

        # Store log in the database
        with sqlite3.connect("/app/logs.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO logs (timestamp, log_message) VALUES (?, ?)", (timestamp, log_message))
            conn.commit()

        return jsonify({"status": "success"}), 200
    return jsonify({"error": "No log data provided"}), 400

@app.route('/get_logs', methods=['GET'])
def get_logs():
    with sqlite3.connect("/app/logs.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
        logs = cursor.fetchall()

    # Format logs for display
    logs_data = [{"timestamp": log[0], "log_message": log[1]} for log in logs]
    return jsonify(logs_data), 200

@app.route('/generate-terraform', methods=['POST'])
def generate_terraform():
    logger = get_logger("http://0.0.0.0:5000/logs")
    try:
        # Extract input data from the POST request
        data = request.json
        instance_type = data.get('instance_type', 't2.medium')
        replica_count = data.get('replica_count', 1)
        region = data.get('region', 'us-east-1')

        template_file = "terraform_template.j2"

        with open(template_file, "r") as file:
            terraform_template_content = file.read()

        # Render the Terraform template
        template = Template(terraform_template_content)
        rendered_template = template.render(
            instanceType=instance_type,
            count=replica_count,
            region=region
        )
        logger.info(rendered_template)

        output_file = TERRAFORM_DIR+"/main.tf"
        with open(output_file, "w") as file:
            file.write(rendered_template)

        # Return the rendered Terraform template as JSON
        return jsonify({
            "status": "success",
            "message": f"Terraform template saved to {output_file}",
            "terraform": rendered_template
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/generate-terraform-plan', methods=['POST'])
def generate_terrafrom_plan():
    logger = get_logger("http://0.0.0.0:5000/logs")
    if not is_terraform_initialized():
        logger.error("Terraform is not initialized. Running terrafrom init")
        run_terraform_command(["terraform", "init"],logger,TERRAFORM_DIR)
    logger.info("Running 'terraform plan'...")
    result = run_terraform_command(["terraform", "plan"],logger,TERRAFORM_DIR)
    if result == None:
        return jsonify({
            "status": "error",
            "message": "check stdout logs"
        })
    else:
        return jsonify({
            "status": "success",
            "message": f"{ result }"
        })

@app.route('/generate-terraform-apply', methods=['POST'])
def generate_terrafrom_apply():
    logger = get_logger("http://0.0.0.0:5000/logs")
    if not is_terraform_initialized():
        result="Terraform is not initialized. run  /generate-terraform and /generate-terraform-plan first"
        logger.error(result)
        return jsonify({
            "status": "error",
            "message": f"{ result }"
        })
    logger.info("Running 'terraform apply'...")
    result = run_terraform_command(["terraform", "apply", "-auto-approve"],logger,TERRAFORM_DIR)
    if result == None:
        return jsonify({
            "status": "error",
            "message": "check stdout logs"
        })
    else:
        return jsonify({
            "status": "success",
            "message": f"{ result }"
        })

@app.route("/apply_ansible_configuration", methods=["POST"])
def apply_ansible_configuration():
    logger = get_logger("http://0.0.0.0:5000/logs")
    """
    Generate Ansible inventory file based on Terraform outputs.
    """
    if not is_terraform_initialized():
        result="Terraform is not initialized. please run '/generate-terraform'"
        logger.error(result)
        return jsonify({
            "status": "failure",
            "message": f"{ result }"
        })
    data = request.json
    max_connections = data.get('max_connections', 100)
    shared_buffers = data.get('shared_buffers', '128MB')
    replica_count = data.get('replica_count', 1)
    postgres_image_tag= data.get("image_tag","14-alpine")
    try:
        # Fetch Terraform output
        os.chdir(TERRAFORM_DIR)

        terraform_output = subprocess.check_output(["terraform", "output", "-json"],cwd=TERRAFORM_DIR)
        output_data = json.loads(terraform_output)

        # Extract IPs
        primary_ip = output_data["primary_public_ip"]["value"][0]
        replica_ips = output_data["replica_ips"]["value"]

        primary_instance_private_ip= output_data["primary_private_ip"]["value"][0]

        os.chdir(ANSIBLE_DIR)
        current_dir=os.getcwd()

        # Generate inventory file
        inventory_file_path = "inventory.ini"
        ansible_config_path= "ansible.cfg"
        with open(inventory_file_path, "w") as inventory_file:
            inventory_file.write("[primary]\n")
            inventory_file.write(f"{primary_ip}\n\n")
            inventory_file.write("[replicas]\n")
            for ip in replica_ips:
                inventory_file.write(f"{ip}\n")
            inventory_file.write(f"[all:vars] \nansible_user=ec2-user \nansible_ssh_private_key_file={current_dir}/my-key-pair.pem \nprimary_private_ip={primary_instance_private_ip} \npostgres_sql_version={postgres_image_tag} \nshared_buffers={shared_buffers} \nmax_conns={max_connections} \nnumber_of_replicas={replica_count} \nnumber_of_walsender={replica_count+1}")
        with open(ansible_config_path,"w") as ansible_config_file:
            ansible_config_file.write("[defaults]\ninventory = inventory.ini \nhost_key_checking = False \nremote_user = root \nansible_python_interpreter = /usr/local/bin/python3")

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Error fetching Terraform output: {e.output.decode()}"}), 500
    except KeyError as e:
        return jsonify({"error": f"Missing expected output key: {str(e)}"}), 500

    playbook_file="bootstrap_postgress.yml"
    inventory_file="inventory.ini"

    logger.info(f"Running playbook: {playbook_file}")
    # result = run_terraform_command(["ansible-playbook","-i inventory.ini bootstrap_postgress.yml"],current_dir)
    # if result == None:
    #     return jsonify({
    #         "status": "error",
    #         "message": "check stdout logs"
    #     })
    # else:
    #     return jsonify({
    #         "status": "success",
    #         "message": f"{ result }"
    #     })
    runner = ansible_runner.run(
        private_data_dir=current_dir,  # Directory containing your playbook, inventory, and other files
        playbook=playbook_file  # The playbook file to run
    )

    if runner.status == "successful":
        logger.info("Playbook executed successfully.")
    else:
        logger.error(f"Playbook execution failed. Status: {runner.status}")
        return jsonify({
            "status": "failure",
            "message": f"{ runner.status }"
        })
    for event in runner.events:
        if 'stdout' in event:
            logger.info(event['stdout'])

    return jsonify({
        "status": "success",
        "message": "postgres primary secondary is ready"
    })

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)