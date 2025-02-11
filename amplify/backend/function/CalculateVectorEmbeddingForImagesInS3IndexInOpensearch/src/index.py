import json
import urllib.parse
import boto3
import numpy as np
import base64
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from datetime import datetime
import os
from botocore.exceptions import ClientError



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
CLOUDWATCH_CLIENT = boto3.client('cloudwatch')

AWS_REGION = os.environ['AWS_REGION']  # e.g. us-east-1

OPENSEARCH_CLIENT = initialize_opensearch_client()
OPENSEARCH_INDEX_NAME = os.environ['OpensearchIndexName']
print(f"OPENSEARCH_INDEX_NAME: {OPENSEARCH_INDEX_NAME}")

BEDROCK_EMBEDDING_MODEL_ID = os.environ['BedrockEmbeddingModelId']
print(f"BEDROCK_EMBEDDING_MODEL_ID: {BEDROCK_EMBEDDING_MODEL_ID}")

BEDROCK_INFERENCE_MODEL_ID = os.environ['BedrockInferenceModelId']
print(f"BEDROCK_INFERENCE_MODEL_ID: {BEDROCK_INFERENCE_MODEL_ID}")

MEDIA_CONVERT_JOB_TEMPLATE_NAME = os.environ["MediaConvertJobTemplateName"]
MEDIA_CONVERT_EXECUTION_ROLE_ARN = os.environ["MediaConvertExecutionRoleArn"]
MEDIA_CONVERT_CLIENT = boto3.client('mediaconvert')

# New environment variable for cosine similarity threshold
COSINE_SIMILARITY_THRESHOLD = float(os.environ.get('COSINE_SIMILARITY_THRESHOLD', 0.95))
print(f"COSINE_SIMILARITY_THRESHOLD: {COSINE_SIMILARITY_THRESHOLD}")

# Get the CloudWatch namespace from environment variable or use default
CLOUDWATCH_NAMESPACE = os.environ.get('CLOUDWATCH_NAMESPACE', 'clip-crunchers')
print(f"CloudWatch Namespace: {CLOUDWATCH_NAMESPACE}")

# Get the CloudWatch namespace from environment variable or use default
AMPLIFY_ENV = os.environ.get('ENV', 'Unknown Environment')
print(f"Amplify Environment: {AMPLIFY_ENV}")

def publish_metric(metric_name, value):
    try:
        CLOUDWATCH_CLIENT.put_metric_data(
            Namespace=CLOUDWATCH_NAMESPACE,
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': 'Count',
                    'Dimensions': [
                        {
                            'Name': 'Environment',
                            'Value': AMPLIFY_ENV
                        },
                        {
                            'Name': 'Function',
                            'Value': 'CalculateVectorEmbeddingForImagesInS3IndexInOpensearch'
                        },
                    ]
                },
            ]
        )
        print(f"Published metric: {metric_name} = {value} to namespace {CLOUDWATCH_NAMESPACE} with dimension Environment={AMPLIFY_ENV}")
    except ClientError as e:
        print(f"Error publishing metric {metric_name}: {e}")

def bedrock_invoke_model(body, modelId):
    response = BEDROCK_CLIENT.invoke_model(
        body=body, modelId=modelId
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

    embedding = np.array(bedrock_invoke_model(body, BEDROCK_EMBEDDING_MODEL_ID)['embedding'])
    if normalize:
        embedding /= np.linalg.norm(embedding)

    return embedding

def add_document_to_opensearch(key, embedding, timestamp, fragment_number, summary, source, custom_metadata):
    document = {
        's3-uri': key,
        'titan-embedding': embedding.tolist(),
        'timestamp': timestamp,
        'fragment-number': fragment_number,
        'summary': summary,  # Add the summary to the document
        'source': source,
        'custom-metadata': custom_metadata
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

def get_image_summary(bucket, key):
    """
    Use Amazon Bedrock API with Claude 3 Sonnet model to generate a summary of the image
    using the multi-modal messages API.
    """
    image_object = S3_RESOURCE.Object(bucket, key)
    image_data = image_object.get()['Body'].read()
    image_base64 = base64.b64encode(image_data).decode('utf-8')

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": "Analyze this image and provide a brief summary of its contents. Focus on the main subjects, actions, and any notable elements in the scene. Keep the summary concise, around 2-3 sentences."
                    }
                ]
            }
        ],
        "temperature": 0
    })

    response_body = bedrock_invoke_model(body, BEDROCK_INFERENCE_MODEL_ID)
    summary = response_body['content'][0]['text']
    return summary.strip()


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_last_image_embedding(prefix):
    """Retrieve the embedding of the last processed image with the given prefix."""
    query = {
        "size": 1,
        "sort": [{"timestamp": {"order": "desc"}}],
        "query": {
            "prefix": {"s3-uri": prefix}
        }
    }
    response = OPENSEARCH_CLIENT.search(index=OPENSEARCH_INDEX_NAME, body=query)

    if response['hits']['total']['value'] > 0:
        return np.array(response['hits']['hits'][0]['_source']['titan-embedding'])
    return None

def get_s3_uri_input_from_mediaconvert_job_id(job_id):
    """Retrieve the S3 URI input from a MediaConvert job ID."""
    response = MEDIA_CONVERT_CLIENT.get_job(Id=job_id)
    return response['Job']['Settings']['Inputs'][0]['FileInput']

def get_image_source(key, response):
    """Determine the source of the image based on the bucket and key."""

    media_convert_job_id = ""
    if "Metadata" in response:
        if "mediaconvert-jobid" in response["Metadata"]:
            media_convert_job_id = response["Metadata"]["mediaconvert-jobid"]

    video_s3_uri = ""
    if media_convert_job_id != "":
        video_s3_uri = get_s3_uri_input_from_mediaconvert_job_id(media_convert_job_id)

    if "mediaconvert-videos-to-image-frames" in key and "/fileUploads/" in video_s3_uri:
        return "fileupload:video"
    elif "mediaconvert-videos-to-image-frames" in key and "/webcamUploads/" in video_s3_uri:
        return "webcam:video"
    elif "/fileUploads/" in key:
        return "fileupload:image"
    elif "/webcamUploads/" in key:
        return "webcam:image"
    else:
        return "unknown"

def get_image_custom_metadata(response):
    custom_metadata = ""
    if "Metadata" in response:
        if "custom-metadata" in response["Metadata"]:
            custom_metadata = response["Metadata"]["custom-metadata"]
    return custom_metadata

def process_new_image_upload(bucket, key):
    response = S3_CLIENT.get_object(Bucket=bucket, Key=key)
    print(f"S3 get object response for bucket:{bucket} key:{key} response:{response}")
    timestamp = get_video_timestamp(response)
    fragment_number = get_video_fragment_number(response)
    source = get_image_source(key, response)
    custom_metadata = get_image_custom_metadata(response)
    embedding = embedding_from_s3(bucket, key)
    print(f"Embedding for bucket:{bucket} key:{key} embedding:{embedding}")

    # Check if the image is from a video conversion
    if "mediaconvert-videos-to-image-frames" in key:
        prefix = '/'.join(key.split('/')[:-1]) + '/'
        last_embedding = get_last_image_embedding(prefix)

        if last_embedding is not None:
            similarity = cosine_similarity(embedding, last_embedding)
            print(f"Cosine similarity with last image: {similarity}")

            if similarity > COSINE_SIMILARITY_THRESHOLD:
                print(f"Skipping summary generation for {key} due to high similarity with previous image.")
                # Emit metric for discarded image
                publish_metric('ImagesDiscarded', 1)
                return

    # Generate summary for the image
    summary = get_image_summary(bucket, key)
    print(f"Generated summary for {key}: {summary}")

    # Add document to OpenSearch with the summary
    add_document_to_opensearch(key, embedding, timestamp, fragment_number, summary, source, custom_metadata)

    # Emit metric for processed image
    publish_metric('ImagesProcessed', 1)

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

    supported_extensions = (".jpg", ".jpeg", ".mp4", ".webm")

    if not (key.endswith(supported_extensions)):
        publish_metric('ReceivedUnsupportedFile', 1)
        print("Skipping unsupported file: " + key)
        return None
    if not key.startswith("public"):
        publish_metric('ReceivedNonPublicFile', 1)
        print("Skipping file that is not public: " + key)
        return None

    if key.endswith((".jpg", ".jpeg")) and record['eventName'].startswith("ObjectCreated"):
        publish_metric('ReceivedImageFile', 1)
        process_new_image_upload(bucket, key)
    elif key.endswith((".mp4",".webm")) and record['eventName'].startswith("ObjectCreated"):
        publish_metric('ReceivedVideoFile', 1)
        process_new_video_upload(bucket, key)
    elif record['eventName'].startswith("ObjectRemoved"):
        publish_metric('ReceivedObjectRemovalEvent', 1)
        print("Object removal handling code is not available in this demo")
    else:
        publish_metric('ReceivedUnknownEvent', 1)
        print("Unknown event type: " + record['eventName'])

def handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    for record in event['Records']:
        s3_notification_event_record_handler(record)


if __name__ == "__main__":
    handler(0,0)