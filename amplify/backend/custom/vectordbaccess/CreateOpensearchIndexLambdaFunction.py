import cfnresponse
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import os
import boto3
import time



def initialize_opensearch_client():
    opensearch_endpoint = os.environ['OpensearchEndpoint'].replace('https://','',1)  # serverless collection endpoint, without https://
    print(f'Opensearch Endpoint: {opensearch_endpoint}')
    region = os.environ['AWS_REGION']  # e.g. us-east-1
    print(f'region: {region}')
    credentials = boto3.Session().get_credentials()
    identity = boto3.client('sts').get_caller_identity()
    print(f'Caller Identity: {identity}')

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

function_initialization_success = False
try:
    print('initializing function')
    OPENSEARCH_CLIENT = initialize_opensearch_client()
    OPENSEARCH_INDEX_NAME = os.environ['OpensearchIndexName']
    print(f'OPENSEARCH_INDEX_NAME: {OPENSEARCH_INDEX_NAME}')
    S3_BUCKET_NAME = os.environ['S3StorageBucketName']
    print(f'S3_BUCKET_NAME: {S3_BUCKET_NAME}')
    MEDIA_CONVERT_JOB_TEMPLATE_NAME = os.environ['MediaConvertJobTemplateName']
    print(f'MEDIA_CONVERT_JOB_TEMPLATE_NAME: {MEDIA_CONVERT_JOB_TEMPLATE_NAME}')
    MEDIA_CONVERT_FRAME_RATE_NUMERATOR = os.environ['MediaConvertFrameRateNumerator']
    print(f'MEDIA_CONVERT_FRAME_RATE_NUMERATOR: {MEDIA_CONVERT_FRAME_RATE_NUMERATOR}')
    MEDIA_CONVERT_FRAME_RATE_DENOMINATOR = os.environ['MediaConvertFrameRateDenominator']
    print(f'MEDIA_CONVERT_FRAME_RATE_DENOMINATOR: {MEDIA_CONVERT_FRAME_RATE_DENOMINATOR}')
    function_initialization_success = True
except Exception as e:
    print('Exception occurred in function initialization')
    print(e)

def create_mediaconvert_job_template():
    template = {
        'Description': 'Takes a video file from s3 and outputs the image frames to s3',
        'Name': MEDIA_CONVERT_JOB_TEMPLATE_NAME,
        'Settings': {
            'TimecodeConfig': {
                'Source': 'ZEROBASED'
            },
            'OutputGroups': [
                {
                    'CustomName': 'Archive Video',
                    'Name': 'File Group',
                    'Outputs': [
                        {
                            'ContainerSettings': {
                                'Container': 'MP4',
                                'Mp4Settings': {}
                            },
                            'VideoDescription': {
                                'CodecSettings': {
                                    'Codec': 'H_264',
                                    'H264Settings': {
                                        'MaxBitrate': 1000,
                                        'RateControlMode': 'QVBR',
                                        'SceneChangeDetect': 'TRANSITION_DETECTION'
                                    }
                                }
                            }
                        }
                    ],
                    'OutputGroupSettings': {
                        'Type': 'FILE_GROUP_SETTINGS',
                        'FileGroupSettings': {
                            'Destination': f's3://{S3_BUCKET_NAME}/mediaconvert-archive/',
                            'DestinationSettings': {
                                'S3Settings': {
                                    'Encryption': {
                                        'EncryptionType': 'SERVER_SIDE_ENCRYPTION_S3'
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    'CustomName': 'JPG Frames',
                    'Name': 'File Group',
                    'Outputs': [
                        {
                            'ContainerSettings': {
                                'Container': 'RAW'
                            },
                            'VideoDescription': {
                                'CodecSettings': {
                                    'Codec': 'FRAME_CAPTURE',
                                    'FrameCaptureSettings': {
                                        'FramerateNumerator': int(MEDIA_CONVERT_FRAME_RATE_NUMERATOR),
                                        'FramerateDenominator': int(MEDIA_CONVERT_FRAME_RATE_DENOMINATOR)
                                    }
                                }
                            },
                            'Extension': '.jpg'
                        }
                    ],
                    'OutputGroupSettings': {
                        'Type': 'FILE_GROUP_SETTINGS',
                        'FileGroupSettings': {
                            'Destination': f's3://{S3_BUCKET_NAME}/public/mediaconvert-videos-to-image-frames/',
                            'DestinationSettings': {
                                'S3Settings': {
                                    'Encryption': {
                                        'EncryptionType': 'SERVER_SIDE_ENCRYPTION_S3'
                                    }
                                }
                            }
                        }
                    }
                }
            ],
            'Inputs': [
                {
                    'TimecodeSource': 'ZEROBASED'
                }
            ]
        },
        'AccelerationSettings': {
            'Mode': 'DISABLED'
        },
        'StatusUpdateInterval': 'SECONDS_60',
        'Priority': 0,
        'HopDestinations': []
    }

    MEDIACONVERT_CLIENT = boto3.client('mediaconvert')

    for retry_count in range(3):
        try:
            print(f'Creating Job Template using {template}')
            response = MEDIACONVERT_CLIENT.create_job_template(**template)
            print(f'MediaConvert Create Job Template Response: {response}')
            return cfnresponse.SUCCESS
        except Exception as e:
            print(f'Exception occurred while creating media convert job template: {template}')
            print(e)
            time.sleep(30)

    return cfnresponse.FAILED

def delete_mediaconvert_job_template():
    MEDIACONVERT_CLIENT = boto3.client('mediaconvert')

    for retry_count in range(3):
        try:
            print(f'Deleting Job Template with name {MEDIA_CONVERT_JOB_TEMPLATE_NAME}')
            response = MEDIACONVERT_CLIENT.delete_job_template(Name=MEDIA_CONVERT_JOB_TEMPLATE_NAME)
            print(f'MediaConvert Delete Job Template Response: {response}')
            return cfnresponse.SUCCESS
        except Exception as e:
            print(f'Exception occurred while deleting media convert job template name: {MEDIA_CONVERT_JOB_TEMPLATE_NAME}')
            print(e)
            time.sleep(30)

    return cfnresponse.FAILED

def create_opensearch_index():
    index_body = {
        'settings': {
            'index.knn': True
        },
        'mappings': {
            'properties': {
                'titan-embedding': {
                    'type': 'knn_vector',
                    'dimension': 1024,
                    'method': {
                        'engine': 'faiss',
                        'space_type': 'l2',
                        'name': 'hnsw',
                        'parameters': {}
                    }
                },
                'fragment-number': {
                    'type': 'text'
                },
                's3-uri': {
                    'type': 'text'
                },
                'timestamp': {
                    'type': 'date'
                }
            }
        }
    }

    for retry_count in range(3):
        try:
            response = OPENSEARCH_CLIENT.indices.create(index=OPENSEARCH_INDEX_NAME, body=index_body)
            print(f'Opensearch Index Create Response: {response}')
            return cfnresponse.SUCCESS
        except Exception as e:
            print(f'Exception occurred while creating index {OPENSEARCH_INDEX_NAME} with retry_count {retry_count}')
            print(e)
            time.sleep(30)

    return cfnresponse.FAILED
def handler(event, context):
    print(f'event: {event}')
    response = cfnresponse.SUCCESS
    if not function_initialization_success:
        response = cfnresponse.FAILED
    elif event['RequestType'] == 'Delete':
        response = delete_mediaconvert_job_template()
    elif event['RequestType'] == 'Create':
        print('Create Request received')
        response = create_opensearch_index()

        if response != cfnresponse.FAILED:
            response = create_mediaconvert_job_template()

    cfnresponse.send(event, context, response, {})