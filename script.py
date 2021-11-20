import json
import os
import sys
import boto3
from botocore.exceptions import ClientError
from time import sleep
import time

with open('credentials.json') as fd:
    credentials = json.load(fd)

TYPE_DB = "DB"
TYPE_WB = "WEB"

AWSACCESSKEYID = credentials["aws_access_key_id"]
AWSSECRETACCESSKEY = credentials["aws_secret_access_key"]

#Trocar nome
OWNER_NAME = sys.argv[1] if len(sys.argv) >= 2 else "TESTE"
KEY_PAIR_NAME = sys.argv[2] if len(sys.argv) >= 3 else "TESTE"
SEC_GROUP_NAME = sys.argv[3] if len(sys.argv) >= 4 else "TESTE"
POSTGRES_PW = "cloud"
POSTGRES_IP = ""
POSTGRES_ID = ""

DJANGO_IP = "" #REMOVER
DJANGO_ID = ""

OWNER_NAME_NV = OWNER_NAME+"_NV"
KEY_PAIR_NAME_NV = KEY_PAIR_NAME+"_NV"
SEC_GROUP_NAME_NV = SEC_GROUP_NAME+"_NV"
SEC_GROUP_ID_NV = ""

OWNER_NAME_OH = OWNER_NAME+"_OH"
KEY_PAIR_NAME_OH = KEY_PAIR_NAME+"_OH"
SEC_GROUP_NAME_OH = SEC_GROUP_NAME+"_OH"
SEC_GROUP_ID_OH = ""

PERMISSION_DJ =[
    {'IpProtocol': 'tcp',
    'FromPort': 22,
    'ToPort': 22,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
    {'IpProtocol': 'tcp',
    'FromPort': 8080,
    'ToPort': 8080,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
]

SEC_GROUP_NAME_DB = SEC_GROUP_NAME+"_DB"
SEC_GROUP_ID_DB = ""

PERMISSION_DB = [
    {'IpProtocol': 'tcp',
    'FromPort': 22,
    'ToPort': 22,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
    {'IpProtocol': 'tcp',
    'FromPort': 5432,
    'ToPort': 5432,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
]


SEC_GROUP_NAME_LB = SEC_GROUP_NAME+"_LB"
SEC_GROUP_ID_LB = ""
LB_ARN =""

PERMISSION_LB = [
    {'IpProtocol': 'tcp',
    'FromPort': 80,
    'ToPort': 80,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
]

TARGETGROUP_NAME = OWNER_NAME + "-TG"
TG_ARN =""

AUTOSCALE_NAME = OWNER_NAME + "_AS"

LAUNCH_NAME = OWNER_NAME + "_LAUNCH"

#UBUNTU para cada regiao
UBUNTU_OH = "ami-0b9064170e32bde34"
UBUNTU_NV = "ami-0747bdcabd34c712a"

client_nv = boto3.client("ec2", region_name="us-east-1", aws_access_key_id=AWSACCESSKEYID, aws_secret_access_key=AWSSECRETACCESSKEY)
client_oh = boto3.client("ec2", region_name="us-east-2", aws_access_key_id=AWSACCESSKEYID, aws_secret_access_key=AWSSECRETACCESSKEY)
clientLB  = boto3.client('elbv2', region_name="us-east-1", aws_access_key_id=AWSACCESSKEYID, aws_secret_access_key=AWSSECRETACCESSKEY)
clientAS  = boto3.client('autoscaling', region_name="us-east-1", aws_access_key_id=AWSACCESSKEYID, aws_secret_access_key=AWSSECRETACCESSKEY)

WAITER_TERMINATE_NV = client_nv.get_waiter('instance_terminated')
WAITER_RUNNING_NV = client_nv.get_waiter('instance_status_ok')
WAITER_IMAGE_NV = client_nv.get_waiter('image_available')

WAITER_TERMINATE_OH = client_oh.get_waiter('instance_terminated')
WAITER_RUNNING_OH = client_oh.get_waiter('instance_status_ok')

def delete_existing_instances(client, OWNER_NAME, WAITER_TERMINATE):
    #EXISTTING INSTANCES
    try:
        delete_instances_ids = []
        existing_instances = client.describe_instances()
        existing_instances = existing_instances["Reservations"]
        for instance in existing_instances:
            for i in instance["Instances"]:
                if (i["State"]["Code"] == (0 or 16 or 80)):
                    for t in i["Tags"]:
                        if(t["Key"] == "Name" and t["Value"] == OWNER_NAME):
                            delete_instances_ids.append(i["InstanceId"])
        if (len(delete_instances_ids) > 0):
            print("Deletando instancia(s) existente(s)...")
            deleted = client.terminate_instances(InstanceIds=delete_instances_ids)
            print("Response: ", deleted["ResponseMetadata"]["HTTPStatusCode"])
            print("Esperando...")
            WAITER_TERMINATE.wait(InstanceIds=delete_instances_ids)
            print("Instancia(s) deletada(s)")
        else:
            print("Nao ha instancias existentes")
    except ClientError as e:
            print("Algo errado aconteceu ao tentar apagar instancias =^(")
            print(e)

def create_credentials(client, KEY_PAIR_NAME, SEC_GROUP_NAME, PERMISSIONS):
    #KEY PAIR
    try:
        existing_kp = client.describe_key_pairs()
        for key in list(existing_kp.values())[0]:
            if (key["KeyName"] == KEY_PAIR_NAME):
                print("Deletando par de chaves existente...")
                deleted = client.delete_key_pair(KeyName=KEY_PAIR_NAME)
                os.remove("./" + KEY_PAIR_NAME + ".pem")
                print("Response: ", deleted["ResponseMetadata"]["HTTPStatusCode"])
        print("Criando Par de Chaves")
        created = client.create_key_pair(KeyName=KEY_PAIR_NAME)
        key_file = open(KEY_PAIR_NAME + ".pem", "w")
        key_file.write(created["KeyMaterial"])
        os.chmod("./" + KEY_PAIR_NAME + ".pem", 0o777)
        print("Arquivo .pem criado")
        print("Response: ", created["ResponseMetadata"]["HTTPStatusCode"])
    except ClientError as e:
            print("Algo errado aconteceu na criacao do par de chaves =^(")
            print(e)

    #SECURITY GROUP
    try:
        existing_sg = client.describe_security_groups()
        for sg in list(existing_sg.values())[0]:
            if (sg["GroupName"] == SEC_GROUP_NAME):
                print("Deletando Grupo de Seguranca existente...")
                deleted = client.delete_security_group(GroupName=sg["GroupName"], GroupId=sg["GroupId"])
                print("Response: ", deleted["ResponseMetadata"]["HTTPStatusCode"])

        print("Criando Grupo de Seguranca...")

        response = client.describe_vpcs()
        vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

        response = client.create_security_group(GroupName=SEC_GROUP_NAME,
                                            Description="TESTE",
                                            VpcId=vpc_id)
        print("Response: ", created["ResponseMetadata"]["HTTPStatusCode"])
        SEC_GROUP_ID = response['GroupId']
        print('Grupo de Seguranca criado %s na %s.' % (SEC_GROUP_ID, vpc_id))

        data = client.authorize_security_group_ingress(
            GroupId=SEC_GROUP_ID,
            IpPermissions=PERMISSIONS)
        print("Response: ", data["ResponseMetadata"]["HTTPStatusCode"])

        return SEC_GROUP_ID
    except ClientError as e:
        print("Algo errado aconteceu na criacao do grupo de seguranca =^(")
        print(e)

def delete_credentials(client, KEY_PAIR_NAME, SEC_GROUP_NAME):
    #KEY PAIR
    try:
        existing_kp = client.describe_key_pairs()
        for key in list(existing_kp.values())[0]:
            if (key["KeyName"] == KEY_PAIR_NAME):
                print("Deletando par de chaves existente...")
                deleted = client.delete_key_pair(KeyName=KEY_PAIR_NAME)
                os.remove("./" + KEY_PAIR_NAME + ".pem")
                print("Response: ", deleted["ResponseMetadata"]["HTTPStatusCode"])
    except:
            print("Algo errado aconteceu na remocao do par de chaves =^(")

    #SECURITY GROUP 
    try:
        existing_sg = client.describe_security_groups()
        for sg in list(existing_sg.values())[0]:
            if (sg["GroupName"] == SEC_GROUP_NAME):
                print("Deletando Grupo de Seguranca existente...")
                deleted = client.delete_security_group(GroupName=sg["GroupName"], GroupId=sg["GroupId"])
                print("Response: ", deleted["ResponseMetadata"]["HTTPStatusCode"])
    except:
        print("Algo errado aconteceu na remocao do grupo de seguranca =^(")

def create_db(client, OWNER_NAME, UBUNTU, SEC_GROUP_ID, SEC_GROUP_NAME, KEY_PAIR_NAME, WAITER_RUNNING):
    TYPE = "db"
    USERDATA_POSTGRES = """
    #cloud-config
        runcmd:
        - cd /
        - sudo apt update -y
        - sudo apt install postgresql postgresql-contrib -y
        - sudo -u postgres psql -c "CREATE DATABASE tasks;"
        - sudo -u postgres psql -c "CREATE USER cloud WITH PASSWORD '%s';"
        - sudo -u postgres psql -c "ALTER ROLE cloud SET client_encondig TO 'utf8';"
        - sudo -u postgres psql -c "ALTER ROLE cloud SET default_transaction_isolation TO 'read committed';"
        - sudo -u postgres psql -c "ALTER ROLE cloud SET timezone TO 'UTC';"
        - sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tasks TO cloud;"
        - sudo echo "listen_addresses = '*'" >> /etc/postgresql/10/main/postgresql.conf
        - sudo echo "host all all 0.0.0.0/0 trust" >> /etc/postgresql/10/main/pg_hba.conf
        - sudo ufw allow 5432/tcp -y
        - sudo systemctl restart postgresql
    """ % (POSTGRES_PW)


    POSTGRES_ID, POSTGRES_IP = instance_create(client, OWNER_NAME, UBUNTU, SEC_GROUP_ID, SEC_GROUP_NAME, KEY_PAIR_NAME, USERDATA_POSTGRES, WAITER_RUNNING, TYPE)
    print(f"IP do DB: {POSTGRES_IP}:5432")
    return POSTGRES_ID, POSTGRES_IP

def create_wb(client, OWNER_NAME, UBUNTU, SEC_GROUP_ID, SEC_GROUP_NAME, KEY_PAIR_NAME, WAITER_RUNNING, POSTGRES_IP):
    TYPE = "wb"
    USERDATA_WEB = """
    #cloud-config
        runcmd:
        - cd /home/ubuntu 
        - sudo apt update -y
        - git clone https://github.com/lucaskf1996/tasks
        - cd tasks
        - sed -i "s/node1/%s/g" ./portfolio/settings.py
        - ./install.sh
        - sudo ufw allow 8080/tcp -y
        - sudo reboot
    """% (POSTGRES_IP)

    DJANGO_ID, DJANGO_IP = instance_create(client, OWNER_NAME, UBUNTU, SEC_GROUP_ID, SEC_GROUP_NAME, KEY_PAIR_NAME, USERDATA_WEB, WAITER_RUNNING, TYPE)
    print(f"IP do WB: {DJANGO_IP}:8080")
    return DJANGO_ID, DJANGO_IP

def instance_create(client, OWNER_NAME, UBUNTU, SEC_GROUP_ID, SEC_GROUP_NAME, KEY_PAIR_NAME, USERDATA, WAITER_RUNNING, TYPE):
    # print('Criando instancias...')
    
    print(f"Criando {TYPE}")

    if USERDATA is None:
        response = client.run_instances(ImageId=UBUNTU, MinCount=1, MaxCount=1, InstanceType='t2.micro', SecurityGroupIds=[SEC_GROUP_ID], SecurityGroups=[SEC_GROUP_NAME], KeyName=KEY_PAIR_NAME,
                                        TagSpecifications=[{ 'ResourceType' : 'instance', 'Tags' : [{'Key' : 'Name', 'Value' : KEY_PAIR_NAME}, { 'Key' : 'Owner', 'Value' : OWNER_NAME}]}])
    else:
        response = client.run_instances(ImageId=UBUNTU, MinCount=1, MaxCount=1, InstanceType='t2.micro', SecurityGroupIds=[SEC_GROUP_ID], SecurityGroups=[SEC_GROUP_NAME], KeyName=KEY_PAIR_NAME,
                                        TagSpecifications=[{ 'ResourceType' : 'instance', 'Tags' : [{'Key' : 'Name', 'Value' : KEY_PAIR_NAME}, { 'Key' : 'Owner', 'Value' : OWNER_NAME}]}], UserData=USERDATA)
    

    print('Instancia criada com id %s' % response["Instances"][0]["InstanceId"])
    WAITER_RUNNING.wait(InstanceIds=[response["Instances"][0]["InstanceId"]])
    
    instancia_criada = None
    existing_instances = client.describe_instances()
    existing_instances = existing_instances["Reservations"]
    for instance in existing_instances:
            for i in instance["Instances"]:
                if (i["State"]["Code"] == (16)):
                    for t in i["Tags"]:
                        if(t["Key"] == "Name" and t["Value"] == OWNER_NAME):
                            if(i["InstanceId"] == response["Instances"][0]["InstanceId"]):
                                instancia_criada = i
    # print(instancia_criada["PublicIpAddress"])
    return  response["Instances"][0]["InstanceId"], instancia_criada["PublicIpAddress"]

def create_ami(client, OWNER_NAME, INSTANCE_ID, WAITER):
    print("Criando imagem do Web Server...")
    response = client.create_image(InstanceId=INSTANCE_ID,
                                    Name='WEBSERVER',
                                    NoReboot=False,
                                    TagSpecifications=[{'ResourceType': 'image','Tags': [{'Key': 'Owner','Value': OWNER_NAME}]}]
                )
    # print(response)
    WAITER.wait(ImageIds=[response["ImageId"]])
    print("Imagem criada. Encerrando Web Server...")
    delete_existing_instances(client_nv, OWNER_NAME_NV, WAITER_TERMINATE_NV)
    print("Instancia encerrada...")
    return response["ImageId"]

def delete_images(client):
    response = client.describe_images(Owners=["self"])
    # print(response)

    if(len(response["Images"])==0):
        print("Nao ha imagens existentes")
        return

    images = []
    for i in response["Images"]:
        if(i["Name"] == "WEBSERVER"):
            images.append(i["ImageId"])

    print("Deletando imagem(ns) existentes")
    for id in images:
        response = client.deregister_image(
            ImageId=id
        )
    print("Response:", response["ResponseMetadata"]["HTTPStatusCode"])
    print("Imagem(ns) deletada(s).")

def get_subnets(client):
    response = client.describe_subnets()
    subnets_id =[]
    for subnet in response["Subnets"]:
        subnets_id.append(subnet["SubnetId"])
    return subnets_id

def create_loadbalancer(client_ec2, client_lb, OWNER_NAME, SEC_GROUP_ID):
    waiter = client_lb.get_waiter('load_balancer_available')
    LB_ARN = ""
    try:
        subnets = get_subnets(client_ec2)
        response = client_lb.create_load_balancer(
            SecurityGroups=[SEC_GROUP_ID],
            Tags=[{ 'Key' : 'Owner', 'Value' : OWNER_NAME}],
            IpAddressType="ipv4",
            Name=OWNER_NAME,
            Subnets=subnets
        )
        for lb in response["LoadBalancers"]:
            if lb["LoadBalancerName"] == OWNER_NAME:
                LB_ARN = lb["LoadBalancerArn"]
                print(lb["DNSName"])
        waiter.wait(LoadBalancerArns=[LB_ARN])
        print(f"Response: {response['ResponseMetadata']['HTTPStatusCode']}")
        return  LB_ARN
    except ClientError as e:
        print("Algo errado aconteceu na criação do Load Balancer =^(")
        print(e)

def delete_loadbalancers(client_lb, OWNER_NAME):
    waiter = client_lb.get_waiter('load_balancers_deleted')
    try:
        response = client_lb.describe_load_balancers()
        if(len(response["LoadBalancers"])==0):
            print("Nao ha load balancers existentes")
            return
        loadbalancers = []
        for lb in response["LoadBalancers"]:
            if lb["LoadBalancerName"] == OWNER_NAME:
                loadbalancers = lb["LoadBalancerArn"]
                print("Deletando loab balancer(s) existente(s)")
                response = client_lb.delete_load_balancer(LoadBalancerArn=loadbalancers)
                waiter.wait(LoadBalancerArns=[loadbalancers])
                print("Response:", response["ResponseMetadata"]["HTTPStatusCode"])
                print("Load Balancer(s) deletado(s)")
                return loadbalancers

    except ClientError as e:
        print("Algo errado aconteceu na remocao do(s) Load Balancer(s) =^(")
        print(e)

def create_target_group(client_lb, client_ec2, targetGroupName):
    print('Criando Target Group...')

    response = client_ec2.describe_vpcs()
    VPC_id = response['Vpcs'][0]['VpcId']
    
    response = client_lb.create_target_group(
        Name = targetGroupName,
        Protocol = 'HTTP',
        Port = 8080,
        TargetType='instance',
        VpcId = VPC_id
    )
    
    print("Response:", response["ResponseMetadata"]["HTTPStatusCode"])

    response = client_lb.describe_target_groups(
        Names=[
            targetGroupName,
        ]
    )

    responseARN = response["TargetGroups"][0]["TargetGroupArn"]

    return responseARN

def delete_target_group(client, TARGETGROUP_NAME):
    print("Removendo target group...")
    response = client.describe_target_groups()
    if len(response["TargetGroups"]) == 0:
        print("Nao ha target groups existentes")
        return
    for tg in response["TargetGroups"]:
        if tg["TargetGroupName"] == TARGETGROUP_NAME:
            response = client.delete_target_group(
                TargetGroupArn=tg["TargetGroupArn"]
            )
            return
    print(f"Nao foi encontrado o target group com o nome {TARGETGROUP_NAME}")

def create_launch_configuration(client, LAUNCH_NAME, AMI_ID, SG_ID):
    print('Criando Launch Configuration...')

    response = client.create_launch_configuration(
        LaunchConfigurationName=LAUNCH_NAME,
        ImageId=AMI_ID,
        SecurityGroups=[
            SG_ID,
        ],
        InstanceType='t2.micro'
    )
    print("Response:", response["ResponseMetadata"]["HTTPStatusCode"])

def delete_launch_configuration(client, LAUNCH_NAME):
    print('Deletando Launch Configuration...')
    try:
        response = client.delete_launch_configuration(
            LaunchConfigurationName=LAUNCH_NAME
        )
        print("Esperando...")
        while len(client.describe_launch_configurations(LaunchConfigurationNames=[LAUNCH_NAME])['LaunchConfigurations']) != 0:
            time.sleep(2)
        print("Response:", response["ResponseMetadata"]["HTTPStatusCode"])
    except ClientError as e:
        print(e)

def create_auto_scaling_group(client_ec2, client_as, AUTOSCALE_NAME , LAUNCH_NAME, TG_ARN):
    print('Criando Auto Scaling Group..')
    response = client_ec2.describe_availability_zones()

    available_zones = []
    for avz in response["AvailabilityZones"]:
        available_zones.append(avz["ZoneName"])

    response = client_as.create_auto_scaling_group(
    AutoScalingGroupName=AUTOSCALE_NAME,
    LaunchConfigurationName=LAUNCH_NAME,
    MinSize=1,
    MaxSize=3,
    DesiredCapacity=1,
    DefaultCooldown=100,
    TargetGroupARNs=[
        TG_ARN,
    ],
    AvailabilityZones=available_zones)

    print("Response:", response["ResponseMetadata"]["HTTPStatusCode"])

def delete_auto_scaling_group(client, AUTOSCALE_NAME):
    print('Deletando Auto Scaling Group...')
    
    wait = True
    try:
        response = client.delete_auto_scaling_group(
            AutoScalingGroupName=AUTOSCALE_NAME,
            ForceDelete = True
        )
        print('Esperando...')
        while len(client.describe_auto_scaling_groups(AutoScalingGroupNames=[AUTOSCALE_NAME])["AutoScalingGroups"]) != 0:
            time.sleep(2)
        print("Response:", response["ResponseMetadata"]["HTTPStatusCode"])
    except ClientError as e:
        print(e)

def create_listener(client, ARN_LB, ARN_TG):
    print('Criando listener para LoadBalancer e TargetGroup')
    response = client.create_listener(
        LoadBalancerArn = ARN_LB,
        Protocol='HTTP',
        Port=80,
        DefaultActions=[
            {
                'Type': 'forward',
                'TargetGroupArn': ARN_TG
            }
        ]
    )
    
    print("Response:", response["ResponseMetadata"]["HTTPStatusCode"])

def delete_listener(client, ARN_LB):
    try:
        print("Removendo listeners...")
        response = client.describe_listeners(LoadBalancerArn = ARN_LB)
        if len(response["TargetGroups"]) == 0:
            print("Nao ha listeners existentes")
            return ""
        for lt in response["Listeners"]:
            if lt["LoadBalancerArn"] == ARN_LB:
                response = client.delete_listener(
                    ListenerArn=lt["ListenerArn"]
                )
                notDeleted = True
                lbarns =[]
                while notDeleted:
                    lbarns =[]
                    response = client.describe_listeners()
                    for lt in response["Listeners"]:
                        lbarns.append(lt["LoadBalancerArn"])
                    if ARN_LB not in lbarns:
                        notDeleted = False
                    time.sleep(2)
                return
        print(f"Nao foi encontrado o target group com o nome {TARGETGROUP_NAME}")
    except:
        print("Algo de errado aconteceu na remoção do listener ou não há load balancer =^(  ")
#------------------------------------------------------------------#


delete_auto_scaling_group(clientAS, AUTOSCALE_NAME)
LB_ARN = delete_loadbalancers(clientLB, OWNER_NAME)
delete_listener(clientLB, LB_ARN)
delete_images(client_nv)
# delete_target_group(clientLB, TARGETGROUP_NAME)
delete_launch_configuration(clientAS, LAUNCH_NAME)

delete_existing_instances(client_nv, OWNER_NAME_NV, WAITER_TERMINATE_NV)
delete_existing_instances(client_oh, OWNER_NAME_OH, WAITER_TERMINATE_OH)

delete_credentials(client_nv, KEY_PAIR_NAME_NV, SEC_GROUP_NAME_NV)
# delete_credentials(client_oh, KEY_PAIR_NAME_OH, SEC_GROUP_NAME_OH)
delete_credentials(client_oh, KEY_PAIR_NAME_OH, SEC_GROUP_NAME_DB)
delete_credentials(client_nv, KEY_PAIR_NAME_NV, SEC_GROUP_NAME_LB)

SEC_GROUP_ID_NV = create_credentials(client_nv, KEY_PAIR_NAME_NV, SEC_GROUP_NAME_NV, PERMISSION_DJ)
# SEC_GROUP_ID_OH = create_credentials(client_oh, KEY_PAIR_NAME_OH, SEC_GROUP_NAME_OH, PERMISSION_DJ)
SEC_GROUP_ID_DB = create_credentials(client_oh, KEY_PAIR_NAME_OH, SEC_GROUP_NAME_DB, PERMISSION_DB)
SEC_GROUP_ID_LB = create_credentials(client_nv, KEY_PAIR_NAME_NV, SEC_GROUP_NAME_LB, PERMISSION_LB)

POSTGRES_ID, POSTGRES_IP = create_db(client_oh, OWNER_NAME_OH, UBUNTU_OH, SEC_GROUP_ID_DB, SEC_GROUP_NAME_DB, KEY_PAIR_NAME_OH, WAITER_RUNNING_OH)
DJANGO_ID, DJANGO_IP = create_wb(client_nv, OWNER_NAME_NV, UBUNTU_NV, SEC_GROUP_ID_NV, SEC_GROUP_NAME_NV, KEY_PAIR_NAME_NV, WAITER_RUNNING_NV, POSTGRES_IP)
# AMI_ID = create_ami(client_nv, OWNER_NAME_NV, DJANGO_ID, WAITER_IMAGE_NV)
# TG_ARN = create_target_group(clientLB, client_nv, TARGETGROUP_NAME)
# LB_ARN = create_loadbalancer(client_nv, clientLB, OWNER_NAME, SEC_GROUP_ID_LB)
# create_launch_configuration(clientAS, LAUNCH_NAME, AMI_ID, SEC_GROUP_ID_NV)
# create_auto_scaling_group(client_nv, clientAS, AUTOSCALE_NAME, LAUNCH_NAME, TG_ARN)
# create_listener(clientLB, LB_ARN, TG_ARN)

#------------------------------------------------------------------#
