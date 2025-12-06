import json
import boto3
import os
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
# checking
lex_client = boto3.client('lexv2-runtime', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

ES_HOST = 'search-photos-nl743nwo2u243qlphekwu4pu2y.us-east-1.es.amazonaws.com'
ES_PORT = 443
ES_INDEX = 'photos'

region = 'us-east-1'

OS_USERNAME = os.environ.get('OS_USERNAME', '')
OS_PASSWORD = os.environ.get('OS_PASSWORD', '')

LEX_BOT_ID = os.environ.get('LEX_BOT_ID', '')
LEX_BOT_ALIAS_ID = os.environ.get('LEX_BOT_ALIAS_ID', '')
LEX_LOCALE_ID = os.environ.get('LEX_LOCALE_ID', 'en_US')

def lambda_handler(event, context):
    print("=== Search Lambda Invoked ===")
    print("Event received:", json.dumps(event))

    # Extract query from API Gateway event
    # query = event.get('queryStringParameters', {}).get('q', '')
    query_params = event.get('queryStringParameters') or {}
    query = query_params.get('q', '').strip()

    print(f"Search query: {query}")

    # Validate query
    if not query:
        return create_response([], "No query provided")
    
    try:
        # Call Lex
        lex_response = lex_client.recognize_text(
            botId=LEX_BOT_ID,
            botAliasId=LEX_BOT_ALIAS_ID,
            localeId=LEX_LOCALE_ID,
            sessionId='test-session',
            text=query
        )
        print(f"Lex response: {lex_response}")

    except Exception as e:
        print(f"Error calling Lex: {e}")
        # return create_response([], f"Error calling Lex: {e}")

        # fallback to direct parsing for keywords
        lex_response = {}
    

    # Extract keywords
    keywords = []
    stopwords = ['show', 'me', 'photos', 'images', 'pictures', 'of', 'with', 'find', 'search', 'for', 'and']

    if 'sessionState' in lex_response:
        slots = lex_response.get('sessionState', {}).get('intent', {}).get('slots', {})

        if slots and 'labels' in slots and slots['labels']:
            label_value = slots['labels'].get('value', {}).get('originalValue', '')
            # check if labels2 value exists
            if 'labels2' in slots and slots['labels2']:
                label_value += ' ' + slots['labels2'].get('value', {}).get('originalValue', '')
            # extract keywords
            keywords = [k.strip().lower() for k in label_value.split() 
                                if k.strip() and k.strip() not in stopwords]
    
    print(f"Lex extracted keywords: {keywords}")

    # Fallback: parse query directly for keywords
    if not keywords:
        print("Lex failed to extract keywords. Falling back to parsing query for keywords....")
        keywords = [k.strip().lower() for k in query.split() 
                   if k.strip().lower() not in stopwords]
    
    print(f"Final keywords: {keywords}")
    
    if not keywords:
        return create_response([], f"No keywords found in query: {query}")

    # mock_results = []
    # if keywords:
    #     mock_results = [{
    #         'message': f'Lex bot successfully extracted keywords: {", ".join(keywords)}',
    #         'query': query,
    #         'keywords': keywords,
    #         'note': 'ElasticSearch not configured yet - these are the keywords that would be searched'
    #     }]
    
    # return create_response(mock_results, f"Found {len(keywords)} keywords from query")


    # ########################################################

    # Search ElasticSearch
    try:
        es = get_es_client()
    
        # Build query
        es_query = {
            'size': 100,
            'query': {
                'bool': {
                    'should': [
                        {'match': {'labels': keyword}} for keyword in keywords
                    ],
                    'minimum_should_match': 1
                }
            }
        }
        print(f"Opensearch query: {es_query}")
    
        # Execute query
        response = es.search(index=ES_INDEX, body=es_query)
        print(f"Opensearch response: {json.dumps(response, default = str)}")
    
    
        # Format results
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            bucket = source['bucket']
            key = source['objectKey']

            image_url = f"https://{bucket}.s3.amazonaws.com/{key}"
            
            results.append({
                'url': image_url,
                'labels': source['labels'],
                'objectKey': key,
                'bucket': bucket,
                'createdTimestamp': source['createdTimestamp']
            })

        print(f"Returning {len(results)} results")

        return create_response(results, f"Found {len(results)} photos matching keywords: {','.join(keywords)}")

    except Exception as e:
        print(f"Error searching OpenSearch: {e}")
        return create_response([], f"Error searching OpenSearch: {e}")
    

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

def create_response(results, message=""):
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'results': results,
            'message': message
        })
    }
