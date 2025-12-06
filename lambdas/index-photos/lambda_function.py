import json
import boto3
import os
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

rekognition = boto3.client('rekognition', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

# ElasticSearch configuration
ES_HOST = 'search-photos-nl743nwo2u243qlphekwu4pu2y.us-east-1.es.amazonaws.com'
ES_PORT = 443
ES_INDEX = 'photos'
region = 'us-east-1'

OS_USERNAME = os.environ.get('OS_USERNAME', '')
OS_PASSWORD = os.environ.get('OS_PASSWORD', '')

def lambda_handler(event, context):
    print("=== Index Photos Lambda Invoked ===")
    print("Event:", json.dumps(event))

    try:
        # Get S3 object details from event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
    
        # decode the key
        from urllib.parse import unquote_plus
        key = unquote_plus(key)

        print("Decoded key:", key)
        # print("Does object exist?")
        # try:
        #     s3.head_object(Bucket=bucket, Key=key)
        #     print("Object exists")
        # except:
        #     print("Object NOT found!")
        print("DEBUG: checking object existence")
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            print("DEBUG: object retrieved, size =", obj['ContentLength'])
        except Exception as e:
            print("DEBUG ERROR: cannot retrieve object:", e)

        print(f"Processing Image: s3://{bucket}/{key}")

        # Get S3 metadata
        print("Getting S3 metadata...")
        head_response = s3.head_object(Bucket=bucket, Key=key)
        print("DEBUG: Content-Type =", head_response['ContentType'])
        print("DEBUG: File size:", head_response['ContentLength'])
        metadata = head_response.get('Metadata', {})
        
        # Extract custom labels
        print("Extracting custom labels from S3 metadata...")
        custom_labels = metadata.get('customlabels', '')
        print("Custom labels:", custom_labels)

        # Detect labels using Rekognition
        print("Detecting labels using Rekognition...")
        rekognition_response = rekognition.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            MaxLabels=10,
            MinConfidence=75
        )
        print("Rekognition response:", json.dumps(rekognition_response))
    
        # Extract labels
        labels = [label['Name'].lower() for label in rekognition_response['Labels']]
        print("Detected labels:", labels)

        if custom_labels:
            custom_labels_list = [label.strip().lower() for label in custom_labels.split(',')]
            labels.extend(custom_labels_list)
            print("Combined labels:", labels)
    
        # Create JSON object
        photo_doc = {
            'objectKey': key,
            'bucket': bucket,
            'createdTimestamp': datetime.now().isoformat(),
            'labels': labels
        }

        print("Photo document:", json.dumps(photo_doc))
    
        
      # Index to OpenSearch
        print("=== Starting OpenSearch indexing ===")
        print("Creating OpenSearch client...")
        es = get_es_client()
        print("OpenSearch client created successfully")
        
        print(f"Indexing to index: {ES_INDEX}, doc ID: {key}")
        response = es.index(
            index=ES_INDEX, 
            body=photo_doc, 
            id=key,
            refresh=True
        )
        print("=== OpenSearch indexing completed ===")
        print("OpenSearch response:", json.dumps(response, default=str))
        
        # Verify document was indexed
        print("Verifying document was indexed...")
        verify_response = es.get(index=ES_INDEX, id=key)
        print("Verification response:", json.dumps(verify_response, default=str))

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Photo indexed successfully',
                'objectKey': key,
                'labels': labels
            })
        }
    
    # End
    except Exception as e:
        print("Error:", e)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Failed to index photo',
                'error': str(e)
            })
        }

def get_es_client():
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key, 
        credentials.secret_key,
        region, 
        'es',
        session_token=credentials.token
    )
    
    es = OpenSearch(
        hosts=[{'host': ES_HOST, 'port': ES_PORT}],
        http_auth=(OS_USERNAME, OS_PASSWORD),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30
    )

    return es
