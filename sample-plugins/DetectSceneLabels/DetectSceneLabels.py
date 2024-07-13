# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import av
import io
import math
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
import requests
import ast
import json
import base64

from MediaReplayEnginePluginHelper import OutputHelper
from MediaReplayEnginePluginHelper import PluginHelper
from MediaReplayEnginePluginHelper import Status
from MediaReplayEnginePluginHelper import DataPlane

brt = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
genai_templates_table = dynamodb.Table('temp-genai-templates')

#model = "anthropic.claude-3-sonnet-20240229-v1:0"
model = "anthropic.claude-3-haiku-20240307-v1:0"

def get_prompt_template(a_template):
    # Specify the key condition expression for the query
    key_condition_expression = Key('template').eq(a_template) 

    # Perform the query
    response = genai_templates_table.query(
        KeyConditionExpression=key_condition_expression
    )
    if len(response['Items']) == 0:
        return ""
    else:
        return response['Items'][0]['prompt']
        
def process_image(a_image, a_prompt):
    base64_string=""
    encoded_string = base64.b64encode(a_image)
    base64_string = encoded_string.decode('utf-8')

    payload = {
        "modelId": model,
        "contentType": "application/json",
        "accept": "application/json",
        "body": {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_string
                            }
                        },
                        {
                            "type": "text",
                            "text": a_prompt
                        }
                    ]
                }
            ]
        }
    }    

    # Convert the payload to bytes
    body_bytes = json.dumps(payload['body']).encode('utf-8')

    # Invoke the model
    response = brt.invoke_model(
        body=body_bytes,
        contentType=payload['contentType'],
        accept=payload['accept'],
        modelId=payload['modelId']
    )

    # Process the response
    response = json.loads(response['body'].read().decode('utf-8'))
    response_content = response['content'][0]
  
    return response_content['text']


def lambda_handler(event, context):
    print(event)

    results = []

    # 'event' is the input event payload passed to Lambda
    mre_dataplane = DataPlane(event)
    mre_outputhelper = OutputHelper(event)

    try:
        # Download the HLS video segment from S3
        media_path = mre_dataplane.download_media()

        # plugin params
        _, chunk_filename = head, tail = os.path.split(event["Input"]["Media"]["S3Key"])

        #minimum_confidence = int(event["Plugin"]["Configuration"]["minimum_confidence"])  # 30
        sampling_seconds = 2
        
        #Labels may include  things like what the scene is, the types of objects and who is present.
        #Provide the answer only in JSON format and do not include any plain text or XML tags in the answer
        # Ensure any quotations, apostrophes and punctuation marks used in a Label are escaped with one backslash.
        #Each Label should be an item in the list.
        #Keep the list flat.
        #Use JSON Array Literal format for the Labels. 
        #and JSON encode the text
        #JSON Array Literal format
        
        example1 = """["Flag", "US Capitol", "Podium", "Joe Biden", "Kamala Haris", "Presentation to congress","Congress\'s Role","The state of the union"]""" 
        example2 = """["Live", "State of the Union", "Joe Biden", "Kamala Haris", "Congress", "Podium", "US Capitol"]""" 
        
        prompt = f"""Generate a distinct list of Labels that describe the image and whats happening.
        Provide the answer in JSON Array Literal format in an <answer></answer> XML tag. 
        Provide the answer only in JSON format and do not include any plain text or XML tags in the answer.
        Examples are provided that describe the expected JSON format in the <example1></example1> and <example2></example2> XML tags.
        <example1>{example1}</example1>  
        <example2>{example2}</example2>
        """
        
        a_prompt_template = "scene-labels"
        prompt = f"""{get_prompt_template(a_prompt_template)}"""
        data = {
            "example1": example1,
            "example2": example2
        }
        prompt = prompt.format(**data)
        print(prompt)
    
        # Frame rate for sampling
        p_fps = int(event["Profile"]["ProcessingFrameRate"])  # i.e. 5
        v_fps = int(event["Input"]["Metadata"]["HLSSegment"]["FrameRate"])  # i.e. 25
        frameRate = int(v_fps / p_fps)
        chunk_start = event['Input']['Metadata']['HLSSegment']['StartTime']

        with av.open(media_path) as container:
            # Signal that we only want to look at keyframes.
            stream = container.streams.video[0]
            #get only keyframes
            stream.codec_context.skip_frame = "NONKEY"
        
            for frameId, frame in enumerate(container.decode(stream)):
            
                frame_start = mre_dataplane.get_frame_timecode(frameId)
                frame_start_absolute = frame_start - chunk_start
                
                # skip frames to meet processing FPS requirement
                #if frameId % math.floor(frameRate) == 0:
                if frame_start_absolute % sampling_seconds == 0:  
                    buffIO = io.BytesIO()
                    frame.to_image().save(buffIO, format='JPEG')
                    imageBytes = buffIO.getvalue()    
                    
                    response = process_image(imageBytes, prompt)
                    scene_labels = response.replace("<answer>","").replace("</answer>","")
                    
                    result = {}

                    # Get timecode from frame
                    result["Start"] = frame_start
                    result["End"] = result["Start"]
                    result["frameId"] = frameId
                    result["Label"] = "The image has been described"
                    result["Image_Summary"] = scene_labels
                    results.append(result)
                    print(result)
                    
        print(f'results:{results}')

        # Add the results of the plugin to the payload (required if the plugin status is "complete"; Optional if the plugin has any errors)
        mre_outputhelper.add_results_to_output(results)

        # Persist plugin results for later use
        mre_dataplane.save_plugin_results(results)

        # Update the processing status of the plugin (required)
        mre_outputhelper.update_plugin_status(Status.PLUGIN_COMPLETE)

        # Returns expected payload built by MRE helper library
        return mre_outputhelper.get_output_object()

    except Exception as e:
        print(e)

        # Update the processing status of the plugin (required)
        mre_outputhelper.update_plugin_status(Status.PLUGIN_ERROR)

        # Re-raise the exception to MRE processing where it will be handled
        raise