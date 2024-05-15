import json
import urllib.parse
import boto3
import numpy as np
import base64
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from datetime import datetime
import os

def initialize_opensearch_client():
    opensearch_endpoint = os.environ['OpensearchEndpoint'].replace('https://','',1)  # serverless collection endpoint, without https://
    print(f"Opensearch Endpoint: {opensearch_endpoint}")
    print(f"region: {AWS_REGION}")
    credentials = boto3.Session().get_credentials()
    print(f"Caller Identity: {boto3.client('sts').get_caller_identity()}")

    auth = AWSV4SignerAuth(credentials, AWS_REGION, 'aoss')

    client = OpenSearch(
        hosts=[{'host': opensearch_endpoint, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
    )

    return client

print('Intializing function')
S3_RESOURCE = boto3.resource('s3')
S3_CLIENT = boto3.client('s3')
BEDROCK_CLIENT = boto3.client('bedrock-runtime')

AWS_REGION = os.environ['AWS_REGION']  # e.g. us-east-1

OPENSEARCH_CLIENT = initialize_opensearch_client()
OPENSEARCH_INDEX_NAME = os.environ['OpensearchIndexName']
print(f"OPENSEARCH_INDEX_NAME: {OPENSEARCH_INDEX_NAME}")

BEDROCK_MODEL_ID = os.environ['BedrockModelId']
print(f"BEDROCK_MODEL_ID: {BEDROCK_MODEL_ID}")

MEDIA_CONVERT_JOB_TEMPLATE_NAME = os.environ["MediaConvertJobTemplateName"]
MEDIA_CONVERT_EXECUTION_ROLE_ARN = os.environ["MediaConvertExecutionRoleArn"]
MEDIA_CONVERT_CLIENT = boto3.client('mediaconvert')

def bedrock_invoke_model(body):
    response = BEDROCK_CLIENT.invoke_model(
        body=body, modelId=BEDROCK_MODEL_ID
    )
    return json.loads(response.get("body").read())

def embedding_from_s3(bucket, key, normalize=True):
    print(f'Getting embedding for bucket:"{bucket}" key: "{key}"')

    bucket = S3_RESOURCE.Bucket(bucket)
    image = bucket.Object(key)
    img_data = image.get().get('Body').read()

    img_bytes = base64.b64encode(img_data).decode('utf8')

    body = json.dumps(
        {
            "inputText": None,
            "inputImage": img_bytes
        }
    )

    embedding = np.array(bedrock_invoke_model(body)['embedding'])
    if normalize:
        embedding /= np.linalg.norm(embedding)

    return embedding

def add_document_to_opensearch(key, embedding, timestamp, fragment_number):
    # Future enhancement: Check if exact same uri already exists in opensearch
    document = {
        's3-uri': key,
        'titan-embedding': embedding.tolist(),
        'timestamp': timestamp,
        'fragment-number': fragment_number
    }

    print(f"Opensearch document request: {document}")

    response = OPENSEARCH_CLIENT.index(
        index = OPENSEARCH_INDEX_NAME,
        body = document
    )

    print(f"Opensearch response: {response}")

def get_video_timestamp(data):

    timestamp = datetime.now().isoformat() + 'Z'

    try:
        if "Metadata" in data and "aws_kinesisvideo_producer_timestamp" in data["Metadata"]:
            dt = datetime.utcfromtimestamp(int(data["Metadata"]["aws_kinesisvideo_producer_timestamp"])/1000)
            timestamp = dt.isoformat() + 'Z'
            print(f"using aws_kinesisvideo_producer_timestamp as timestamp: {timestamp}")
    except Exception as e:
        print(e)
        print("Cannot determine timestamp from image metadata, using current system time")

    return timestamp

def get_video_fragment_number(data):

    framgment = ""

    if "Metadata" in data and "aws_kinesisvideo_fragment_number" in data["Metadata"]:
        framgment = data["Metadata"]["aws_kinesisvideo_fragment_number"]
        print(f"using aws_kinesisvideo_fragment_number: {framgment}")
    else:
        print("aws_kinesisvideo_fragment_number NOT FOUND in metadata")

    return framgment


def process_new_image_upload(bucket, key):
    response = S3_CLIENT.get_object(Bucket=bucket, Key=key)
    print(f"S3 get object response for bucket:{bucket} key:{key}")
    timestamp = get_video_timestamp(response)
    fragment_number = get_video_fragment_number(response)
    embedding = embedding_from_s3(bucket, key)
    print(f"Embedding for bucket:{bucket} key:{key} embedding:{embedding}")

    add_document_to_opensearch(key, embedding, timestamp, fragment_number)

def process_new_video_upload(bucket, key):
    
    settings_input = {"Inputs": [
        {
            "FileInput": f"s3://{bucket}/{key}"
        }
    ]}
    print(f"settings_input: {settings_input}")
    
    response = MEDIA_CONVERT_CLIENT.create_job(
        JobTemplate = MEDIA_CONVERT_JOB_TEMPLATE_NAME,
        Role = MEDIA_CONVERT_EXECUTION_ROLE_ARN,
        Settings = settings_input
    )
    print(f"Media Convert Create Job Response: {response}")

# function for lambda that processes events from s3
def s3_notification_event_record_handler(record):
    print("Processing record: " + json.dumps(record, indent=2))

    bucket = record['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')

    if not (key.endswith(".jpg") or key.endswith(".mp4") or key.endswith(".webm")):
        print("Skipping unsupported file: " + key)
        return None
    if not key.startswith("public"):
        print("Skipping file that is not public: " + key)
        return None

    if key.endswith(".jpg") and record['eventName'].startswith("ObjectCreated"):
        process_new_image_upload(bucket, key)
    elif (key.endswith(".mp4") or key.endswith(".webm")) and record['eventName'].startswith("ObjectCreated"):
        process_new_video_upload(bucket, key)
    elif record['eventName'].startswith("ObjectRemoved"):
        print("Object removal handling code is not available in this demo")
    else:
        print("Unknown event type: " + record['eventName'])

def handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    for record in event['Records']:
        s3_notification_event_record_handler(record)


if __name__ == "__main__":
    handler(0,0)