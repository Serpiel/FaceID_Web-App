import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

def connect_to_dynamodb():
    try:
        dynamodb = boto3.resource('dynamodb',
            region_name=os.getenv('AWS_REGION'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        return dynamodb
    except ClientError as e:
        print(f"Erreur de connexion AWS : {e}")
        return None

def get_users_table(db):
    table_name = "Users_sp"
    table = db.Table(table_name)
    try:
        table.load()
        return table
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"Création de la table {table_name}...")
            table = db.create_table(
                TableName=table_name,
                KeySchema=[{'AttributeName': 'email', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'email', 'AttributeType': 'S'}],
                ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
            )
            table.wait_until_exists()
            return table
        return None