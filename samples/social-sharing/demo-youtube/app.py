from chalice import Chalice
import boto3
import os
import sys
import json
import requests

app = Chalice(app_name='demo-youtube')
app.debug = True
s3_bucket = 'social-share-demo'
s3_client = boto3.client("s3")
youtube_get_upload_url = 'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status,contentDetails'




@app.route('/')
def index():
    return {'hello': 'world'}

@app.route('/upload-file', methods=['POST'], cors=True)
def upload_file():
    request = app.current_request
    token = request.json_body['token']
    file_name = request.json_body['file']
    
    #download s3 data
    tmp_dir = "/tmp"
    download_path = os.path.join(tmp_dir, file_name)
    
    _download_from_s3(s3_bucket, f"{file_name}", download_path)
    
    
    _upload_to_youtube(download_path, token)
    
    return {'status':str(os.path.getsize(download_path))}


def _download_from_s3(bucket, key, download_path):
    try:
        s3_client.download_file(bucket, key, download_path)
        # print(f"Successfully downloaded {key} from {bucket}")
    except Exception as e:
        print(f"Error downloading {key} from {bucket}: {str(e)}")
        raise
    
def _upload_to_youtube(download_path, token):
    size = os.path.getsize(download_path)
    # get upload url
    upload_url = _get_upload_url(size, token)
    # upload video 
    upload_header = {
        'Authorization': 'Bearer ' + token,
        'Content-Length' : str(size),
        'Content-Type': 'video/*',
    }
    
    with open(download_path, 'rb') as file:
        upload_response = requests.put(upload_url, headers=upload_header, data=file)
    
    if( upload_response.status_code == 200):
        return {"data": upload_response}
    else:
        print(f"Error when upload video {upload_response}")
        raise


def _get_upload_url(size, token):
    data = {
            "snippet": {
              "title": "My video title",
              "description": "This is a description of my video",
              "tags": ["cool", "video", "more keywords"],
              "categoryId": 22
            },
            "status": {
              "privacyStatus": "public",
              "embeddable": True,
              "license": "youtube"
            }
          }
  
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Length' : str(sys.getsizeof(json.dumps(data))),
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Upload-Content-Length' : str(size),
        'X-Upload-Content-Type': 'video/*'
    }
  
    response = requests.post(youtube_get_upload_url, headers=headers, json=data)
    print(str(response.content))
    print(str(response.json))
    print(str(response.raw))
    
    print(str(response.status_code))
    if( response.status_code == 200):
        return response.headers['location']
    else:
        print(f"Error when getting upload url {str(response)}")
        raise
        