import json
import boto3
import numpy as np
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dateutil import parser
from datetime import timedelta
import os

def initialize_opensearch_client():
    opensearch_endpoint = os.environ['OpensearchEndpoint'].replace('https://','',1)  # serverless collection endpoint, without https://
    print(f"Opensearch Endpoint: {opensearch_endpoint}")
    region = os.environ['AWS_REGION']  # e.g. us-east-1
    print(f"region: {region}")
    credentials = boto3.Session().get_credentials()
    print(f"Caller Identity: {boto3.client('sts').get_caller_identity()}")

    auth = AWSV4SignerAuth(credentials, region, 'aoss')

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

OPENSEARCH_CLIENT = initialize_opensearch_client()
OPENSEARCH_INDEX_NAME = os.environ['OpensearchIndexName']
print(f"OPENSEARCH_INDEX_NAME: {OPENSEARCH_INDEX_NAME}")

BEDROCK_MODEL_ID = os.environ['BedrockModelId']
print(f"BEDROCK_MODEL_ID: {BEDROCK_MODEL_ID}")

KINESIS_VIDEO_STREAM_INTEGRATION = os.environ['KinesisVideoStreamIntegration'] == 'True'
print(f"KINESIS_VIDEO_STREAM_INTEGRATION: {KINESIS_VIDEO_STREAM_INTEGRATION}")

if KINESIS_VIDEO_STREAM_INTEGRATION:
    KINESIS_VIDEO_STREAM_NAME = os.environ['KinesisVideoStreamName']
    print(f"KINESIS_VIDEO_STREAM_NAME: {KINESIS_VIDEO_STREAM_NAME}")

    def get_kinesis_data_endpoint():
        client = boto3.client("kinesisvideo")

        response = client.get_data_endpoint(
            StreamName=KINESIS_VIDEO_STREAM_NAME,
            APIName='GET_HLS_STREAMING_SESSION_URL'
        )

        return response['DataEndpoint']

    KINESIS_DATA_ENDPOINT = get_kinesis_data_endpoint()
    KINESIS_VIDEO_ARCHIVED_MEDIA_CLIENT = boto3.client("kinesis-video-archived-media", endpoint_url=KINESIS_DATA_ENDPOINT)

def get_hls_streaming_session_live_url():
    response = KINESIS_VIDEO_ARCHIVED_MEDIA_CLIENT.get_hls_streaming_session_url(
        StreamName=KINESIS_VIDEO_STREAM_NAME,
        PlaybackMode='LIVE',
        HLSFragmentSelector={
            'FragmentSelectorType': 'PRODUCER_TIMESTAMP',
        },
        DiscontinuityMode='ON_DISCONTINUITY',
        DisplayFragmentTimestamp='ALWAYS',
        Expires=3600
    )

    return response['HLSStreamingSessionURL']

def deduplicate_by_timestamp(data, window=30):

    data.sort(key=lambda x: x['timestamp'])

    deduplicated_data = []
    last_timestamp = None

    for item in data:
        current_timestamp = parser.isoparse(item['timestamp'])
        if last_timestamp is None or (current_timestamp - last_timestamp) > timedelta(seconds=window):
            deduplicated_data.append(item)
            last_timestamp = current_timestamp

    return deduplicated_data

def get_hls_streaming_session_url(timestamp):
    image_date = parser.isoparse(timestamp)
    print(image_date)
    start_time = image_date - timedelta(seconds=20)
    print(start_time)
    end_time = image_date + timedelta(seconds=10)
    print(end_time)

    response = KINESIS_VIDEO_ARCHIVED_MEDIA_CLIENT.get_hls_streaming_session_url(
        StreamName=KINESIS_VIDEO_STREAM_NAME,
        PlaybackMode='ON_DEMAND',
        HLSFragmentSelector={
            'FragmentSelectorType': 'PRODUCER_TIMESTAMP',
            'TimestampRange': {
                'StartTimestamp': start_time,
                'EndTimestamp': end_time
            }
        },
        DiscontinuityMode='ON_DISCONTINUITY',
        DisplayFragmentTimestamp='ALWAYS',
        Expires=3600
    )

    print(response['HLSStreamingSessionURL'])

    return response['HLSStreamingSessionURL']

def bedrock_invoke_model(body):
    response = BEDROCK_CLIENT.invoke_model(
        body=body, modelId=BEDROCK_MODEL_ID
    )
    return json.loads(response.get("body").read())


def embedding_from_text(text, normalize=True):
    body = json.dumps({"inputText": text, "inputImage": None})

    embedding = np.array(bedrock_invoke_model(body)["embedding"])
    if normalize:
        embedding /= np.linalg.norm(embedding)

    return embedding

def get_nearest_neighbors_from_opensearch(k_neighbors, embedding, days):
    query = {
        "size": k_neighbors,
        "query": {
            "knn": {
                "titan-embedding": {
                    "vector": embedding.tolist(),
                    "k": k_neighbors,
                    "filter": {
                        "range": {
                            "timestamp": {"gte": f"now-{days}d", "lte": "now"}
                        }
                    },
                }
            }
        },
    }

    print(f"Sending query to opensearch: {query}")
    response = OPENSEARCH_CLIENT.search(body=query, index=OPENSEARCH_INDEX_NAME)
    print(f"Recevied response from opensearch: {response}")

    return response

def process_nearest_neighbor_raw_response_for_image_search(response, baseline_embedding, confidenceThreshold, includeSimilarTimestamp=True):
    output_dict = {}

    for hit in response["hits"]["hits"]:
        s3_filename = hit["_source"]["s3-uri"]
        timestamp = hit["_source"]["timestamp"]

        if not str(timestamp).endswith("Z"):
            timestamp = f"{timestamp}Z"

        if s3_filename.startswith("public/"):
            s3_filename = s3_filename.replace("public/", "")

            target_embedding = np.array(hit["_source"]["titan-embedding"]).astype(float)
            dist = np.linalg.norm(target_embedding - baseline_embedding)
            confidence = (1 - dist / 2) * 100

            print(f"s3 uri: {s3_filename} - confidence: {confidence}")
            if round(confidence, 2) >= confidenceThreshold:
                output_dict[s3_filename] = {"confidence": round(confidence, 2), "timestamp": timestamp}

    print(f"output dictionary:{output_dict}")
    images = [(lambda d: d.update(file=key) or d)(val) for (key, val) in output_dict.items()]

    if not includeSimilarTimestamp:
        images = deduplicate_by_timestamp(images)
        
    images = sorted(images, key=lambda x: x['confidence'], reverse=True)

    print(f"Images after all processing: {images}")

    return {"images": images}
def handler(event, context):
    print("received event:")
    print(event)

    statusCode = 200
    output = {}

    if event["path"] == "/images/search" and event["httpMethod"] == "POST":
        eventJson = json.loads(event["body"])

        searchString = eventJson["searchString"]
        days = "1"
        k_neighbors = 20
        confidenceThreshold = 42.00

        if "days" in eventJson:
            days = eventJson["days"]

        if "confidenceThreshold" in eventJson:
            confidenceThreshold = float(eventJson["confidenceThreshold"])

        includeSimilarTimestamp = True
        if "includeSimilarTimestamp" in eventJson:
            includeSimilarTimestamp = eventJson["includeSimilarTimestamp"]

        print(f"string: {searchString} - days:{days} - confidence: {confidenceThreshold} - includeSimilarTimestamp: {includeSimilarTimestamp}")

        user_query_embedding = embedding_from_text(searchString)

        print(f"embedding of user query: {user_query_embedding}")

        raw_nearest_neighbors_response = get_nearest_neighbors_from_opensearch(k_neighbors, user_query_embedding, days)

        output = process_nearest_neighbor_raw_response_for_image_search(raw_nearest_neighbors_response, user_query_embedding, confidenceThreshold, includeSimilarTimestamp)

    elif event["path"] == "/images/sessionURL" and event["httpMethod"] == "GET" and KINESIS_VIDEO_STREAM_INTEGRATION:
        timestamp = event["queryStringParameters"]["timestamp"]
        session_url = get_hls_streaming_session_url(timestamp)
        output = {"sessionURL": session_url}

    elif event["path"] == "/images/liveURL" and event["httpMethod"] == "GET" and KINESIS_VIDEO_STREAM_INTEGRATION:
        session_url = get_hls_streaming_session_live_url()
        output = {"sessionURL": session_url}

    else:
        statusCode = 404
        output = {"message": "Path not found"}
    
    return {
        "statusCode": statusCode,
        "headers": {
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        },
        "body": json.dumps(output),
    }