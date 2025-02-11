import json
import boto3
import numpy as np
import base64
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dateutil import parser
from datetime import datetime, timedelta
import os
import base64

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

BEDROCK_EMBEDDING_MODEL_ID = os.environ['BedrockEmbeddingModelId']
print(f"BEDROCK_EMBEDDING_MODEL_ID: {BEDROCK_EMBEDDING_MODEL_ID}")

BEDROCK_INFERENCE_MODEL_ID = os.environ['BedrockInferenceModelId']
print(f"BEDROCK_INFERENCE_MODEL_ID: {BEDROCK_INFERENCE_MODEL_ID}")

KINESIS_VIDEO_STREAM_INTEGRATION = os.environ['KinesisVideoStreamIntegration'] == 'True'
print(f"KINESIS_VIDEO_STREAM_INTEGRATION: {KINESIS_VIDEO_STREAM_INTEGRATION}")

S3STORAGE_BUCKETNAME = os.environ.get('STORAGE_S3STORAGE_BUCKETNAME', '')
print(f"S3STORAGE_BUCKETNAME: {S3STORAGE_BUCKETNAME}")

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
        body=body, modelId=BEDROCK_EMBEDDING_MODEL_ID
    )
    return json.loads(response.get("body").read())


def embedding_from_text_and_s3(text, bucket, key, normalize=True):
    print(f'Getting embedding for text: "{text}" bucket: "{bucket}" key: "{key}"')

    img_bytes = None
    if key != "" and bucket != "":
        bucket = S3_RESOURCE.Bucket(bucket)
        image = bucket.Object(key)
        img_data = image.get().get('Body').read()

        img_bytes = base64.b64encode(img_data).decode('utf8')

    if text == "":
        text = None

    if text == None and img_bytes == None:
        raise ValueError("Either text or image must be provided")

    body = json.dumps(
        {
            "inputText": text,
            "inputImage": img_bytes
        }
    )

    embedding = np.array(bedrock_invoke_model(body)['embedding'])
    if normalize:
        embedding /= np.linalg.norm(embedding)

    return embedding

def get_date_range_filter(date_range):
    if date_range['type'] == 'relative':
        end_date = datetime.utcnow()
        if date_range['unit'] == 'year':
            start_date = end_date - timedelta(days=365 * date_range['amount'])
        elif date_range['unit'] == 'month':
            start_date = end_date - timedelta(days=30 * date_range['amount'])
        elif date_range['unit'] == 'week':
            start_date = end_date - timedelta(weeks=date_range['amount'])
        elif date_range['unit'] == 'day':
            start_date = end_date - timedelta(days=date_range['amount'])
        elif date_range['unit'] == 'hour':
            start_date = end_date - timedelta(hours=date_range['amount'])
        elif date_range['unit'] == 'minute':
            start_date = end_date - timedelta(minutes=date_range['amount'])
        elif date_range['unit'] == 'second':
            start_date = end_date - timedelta(seconds=date_range['amount'])
        else:
            raise ValueError(f"Unsupported unit: {date_range['unit']}")
    else:  # absolute
        start_date = parser.isoparse(date_range['startDate'])
        end_date = parser.isoparse(date_range['endDate'])

    return {
        "range": {
            "timestamp": {
                "gte": start_date.isoformat(),
                "lte": end_date.isoformat()
            }
        }
    }

def get_nearest_neighbors_from_opensearch(k_neighbors, embedding, date_range):
    date_filter = get_date_range_filter(date_range)

    query = {
        "size": k_neighbors,
        "query": {
            "knn": {
                "titan-embedding": {
                    "vector": embedding.tolist(),
                    "k": k_neighbors,
                    "filter": date_filter
                }
            }
        },
    }

    print(f"Sending query to opensearch: {query}")
    response = OPENSEARCH_CLIENT.search(body=query, index=OPENSEARCH_INDEX_NAME)
    print(f"Received response from opensearch: {response}")

    return response

def process_nearest_neighbor_raw_response_for_image_search(response, baseline_embedding, confidenceThreshold, includeSimilarTimestamp=True):
    output_dict = {}

    for hit in response["hits"]["hits"]:
        s3_filename = hit["_source"]["s3-uri"]
        timestamp = hit["_source"]["timestamp"]

        text_summary = "No text summary available"
        if "summary" in hit["_source"]:
            print(f'Text summary: {hit["_source"]["summary"]}')
            text_summary = hit["_source"]["summary"]

        source = "unknown"
        if "source" in hit["_source"]:
            print(f'source: {hit["_source"]["source"]}')
            source = hit["_source"]["source"]

        custom_metadata = ""
        if "custom-metadata" in hit["_source"]:
            print(f'custom-metadata: {hit["_source"]["custom-metadata"]}')
            custom_metadata = hit["_source"]["custom-metadata"]
        if custom_metadata == "":
            custom_metadata = "No custom metadata available"

        if not str(timestamp).endswith("Z"):
            timestamp = f"{timestamp}Z"

        if s3_filename.startswith("public/"):
            s3_filename = s3_filename.replace("public/", "")

            target_embedding = np.array(hit["_source"]["titan-embedding"]).astype(float)
            dist = np.linalg.norm(target_embedding - baseline_embedding)
            confidence = (1 - dist / 2) * 100

            print(f"s3 uri: {s3_filename} - confidence: {confidence}")
            if round(confidence, 2) >= confidenceThreshold:
                output_dict[s3_filename] = {"confidence": round(confidence, 2), "timestamp": timestamp,  "summary": text_summary, "source": source,  "custom_metadata": custom_metadata}

    print(f"output dictionary:{output_dict}")
    images = [(lambda d: d.update(file=key) or d)(val) for (key, val) in output_dict.items()]

    if not includeSimilarTimestamp:
        images = deduplicate_by_timestamp(images)
        
    images = sorted(images, key=lambda x: x['confidence'], reverse=True)

    print(f"Images after all processing: {images}")

    return {"images": images}

def get_s3_uris_from_opensearch(date_range, max_results=20):
    date_filter = get_date_range_filter(date_range)

    query = {
        "size": max_results,
        "query": date_filter,
        "_source": ["s3-uri"]
    }

    print(f"Sending query to opensearch: {query}")
    response = OPENSEARCH_CLIENT.search(body=query, index=OPENSEARCH_INDEX_NAME)
    print(f"Received response from opensearch: {response}")

    s3_uris = []
    for hit in response["hits"]["hits"]:
        s3_uris.append(hit["_source"]["s3-uri"])

    return s3_uris

def get_image_data(bucket, uris):
    bucket = S3_RESOURCE.Bucket(bucket)
    images_content = []
    for uri in uris:
        image = bucket.Object(uri)
        img_data = image.get().get('Body').read()
        image_content = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.b64encode(img_data).decode('utf8')
            }
        }
        images_content.append(image_content)

    return images_content

def bedrock_invoke_multimodal_model(images_content, custom_summary_prompt="Analyze these images and provide a brief summary of its contents. Focus on the main subjects, actions, and any notable elements in the scene. Keep the summary concise, around 2-3 sentences."):
    if len(images_content) == 0:
        return "No summary"

    text_content = {
        "type": "text",
        "text": custom_summary_prompt
    }
    multimodal_content = images_content
    multimodal_content.append(text_content)
    # print(f"multimodal content first: {multimodal_content[0]}")
    # print(f"multimodal content last: {multimodal_content[-1]}")

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": multimodal_content
            }
        ],
        "temperature": 0
    })

    response = BEDROCK_CLIENT.invoke_model(
        body=body,
        modelId=BEDROCK_INFERENCE_MODEL_ID,
        contentType="application/json",
        accept="application/json"
    )

    response_body = json.loads(response['body'].read())
    summary = response_body['content'][0]['text'].strip()
    return summary

def handler(event, context):
    print("received event:")
    print(event)

    statusCode = 200
    output = {}

    if event["path"] == "/images/search" and event["httpMethod"] == "POST":
        eventJson = json.loads(event["body"])

        searchText = eventJson["searchText"]
        searchImage = eventJson["searchImage"]
        date_range = eventJson["dateRange"]
        confidenceThreshold = 0.0
        maxResults = 50

        if "confidenceThreshold" in eventJson:
            confidenceThreshold = float(eventJson["confidenceThreshold"])

        includeSimilarTimestamp = True
        if "includeSimilarTimestamp" in eventJson:
            includeSimilarTimestamp = eventJson["includeSimilarTimestamp"]

        if "maxResults" in eventJson:
            maxResults = float(eventJson["maxResults"])

        print(f"searchText: {searchText} - searchImage: {searchImage} - date_range: {date_range} - confidence: {confidenceThreshold} - includeSimilarTimestamp: {includeSimilarTimestamp}")

        object_key = ""
        if searchImage != "":
            object_key = f'public/fileUploads/{searchImage}'

        user_query_embedding = embedding_from_text_and_s3(searchText, S3STORAGE_BUCKETNAME, object_key)

        print(f"embedding of user query: {user_query_embedding}")

        raw_nearest_neighbors_response = get_nearest_neighbors_from_opensearch(maxResults, user_query_embedding, date_range)

        output = process_nearest_neighbor_raw_response_for_image_search(raw_nearest_neighbors_response, user_query_embedding, confidenceThreshold, includeSimilarTimestamp)

    elif event["path"] == "/images/sessionURL" and event["httpMethod"] == "GET" and KINESIS_VIDEO_STREAM_INTEGRATION:
        timestamp = event["queryStringParameters"]["timestamp"]
        session_url = get_hls_streaming_session_url(timestamp)
        output = {"sessionURL": session_url}

    elif event["path"] == "/images/liveURL" and event["httpMethod"] == "GET" and KINESIS_VIDEO_STREAM_INTEGRATION:
        session_url = get_hls_streaming_session_live_url()
        output = {"sessionURL": session_url}

    elif event["path"] == "/images/summarize" and event["httpMethod"] == "POST":
        eventJson = json.loads(event["body"])
        date_range = eventJson["dateRange"]
        print(f"date_range: {date_range}")
        custom_summary_prompt = eventJson["customSummaryPrompt"]
        print(f"custom_summary_prompt: {custom_summary_prompt}")

        uris = get_s3_uris_from_opensearch(date_range)
        images = get_image_data(S3STORAGE_BUCKETNAME, uris)
        output = {}
        output['summary'] = bedrock_invoke_multimodal_model(images, custom_summary_prompt)
        output['images'] = uris

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