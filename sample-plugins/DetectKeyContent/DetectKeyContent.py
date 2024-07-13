# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import math
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
import requests
import ast
import json

from MediaReplayEnginePluginHelper import OutputHelper
from MediaReplayEnginePluginHelper import PluginHelper
from MediaReplayEnginePluginHelper import Status
from MediaReplayEnginePluginHelper import DataPlane
from MediaReplayEnginePluginHelper import ControlPlane

brt = boto3.client(service_name='bedrock-runtime')

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = 'temp-chunk-vars'
table = dynamodb.Table(table_name)


# function to get record from dynamodb table
def get_transcript(a_program, a_event, a_start_chunk_number):
    # Specify the key condition expression for the query
    key_condition_expression = Key('program-event').eq(a_program + '::' + a_event) & Key('chunk_number').gt(a_start_chunk_number)

    # Perform the query
    response = table.query(
        KeyConditionExpression=key_condition_expression
    )
    if len(response['Items']) == 0:
        return ""
    else:
        transcript = ""
        for chunk in response['Items']:
            transcript += ' ' + chunk['transcription'] 
        return transcript


def set_chunk_vars(a_program, a_event, a_chunk, a_attribute, a_value):
    # Perform the update
    response = table.update_item(
        Key={
            'program-event': a_program + '::' + a_event,
            'chunk_number': a_chunk
        },
        UpdateExpression='SET ' + a_attribute + ' = :val',
        ExpressionAttributeValues={
            ':val': a_value
        }
    )


# find celebs during the specified time span and dedup the list
def get_celebs_for_theme(a_celebs_list, a_start, a_end):
    new_celeb_list = []
    # many frames were checked for celebrities, lets process them one at a time
    for celeb_frame in a_celebs_list:
        if celeb_frame['Start'] >= a_start and celeb_frame['End'] <= a_end:
            # each item is a list of celebs in the frame at the single point in time
            celebs_in_a_frame = json.loads(celeb_frame['Celebrities_List'])
            for celeb in celebs_in_a_frame:
                # check for dups
                if new_celeb_list.count(celeb) == 0:
                    new_celeb_list.append(celeb)
                    
    if len(new_celeb_list) > 0: 
        a_result = ','.join(new_celeb_list)
    else:
        a_result = ''
    return a_result
    

# find sentiment during the specified time span and dedup the list
def get_sentiment_for_theme(a_sentiment_list, a_start, a_end):
    new_sentiment_list = []
    # many frames were checked for celebrities, lets process them one at a time
    for sentiment_frame in a_sentiment_list:
        if sentiment_frame['Start'] >= a_start and sentiment_frame['End'] <= a_end:
            # check for dups
            if new_sentiment_list.count(sentiment_frame['primary_sentiment']) == 0:
                new_sentiment_list.append(sentiment_frame['primary_sentiment'])
                    
    if len(new_sentiment_list) > 0: 
        a_result = ','.join(new_sentiment_list)
    else:
        a_result = ''
    return a_result
        

# clip out the transcript from start to end for a theme
def get_excerpt(a_transcript, a_start, a_end):
    pos_start = a_transcript.find(str(a_start))
    pos_end = a_transcript.find(str(a_end))
    return a_transcript[pos_start - 1:pos_end - 1]


def get_themes_from_transcript(a_transcription, a_last_theme):
    ''' Sample response
    ' Here are the key themes in the speech with start and end timings:\n\n[{"Theme": "Greeting and thanking the audience", "Start": "1.69", "End": "43.789"}, {"Theme": "Congratulating new Congressional leadership", "Start": "51.21", "End": "160.009"}, {"Theme": "America\'s resilience and progress", "Start": "219.12", "End": "240.009"}, {"Theme": "Bipartisan accomplishments", "Start": "260.86", "End": "380.009"}, {"Theme": "Appealing for continued bipartisanship", "Start": "400.31", "End": "410.979"}]'
    '''
    
    if a_last_theme != "<none>":
        a_theme_list = a_last_theme
    else:
        a_theme_list = ""
        
    prompt = f"""
Human: Provided the following part of a political speech within the <transcription></transcription> XML tag,
    answer the question within the <question></question> XML tag. 
    Use the list of previously known themes within the <themes></themes> XML tag to determine if the theme has changed.
    <transcription>{a_transcription}</transcription>
    <themes>{a_theme_list}</themes>
    <question> What are the key themes in this speech? 
    Theme titles can be up to 10 words long.
    Include the start and end timings for each theme using the time data in brackets. 
    Each theme should be an item in the list.
    Use a compact JSON format with only the keys as 'Theme', 'Start', and 'End'. 
    Here is an example. {{'Start':2.341, 'End':6.231, 'Theme':'Economic Recovery of the United States'}}. 
    The Start and End times are mandatory as floating point numbers.
    Provide the answer only in JSON format and do not include any plain text or XML tags in the answer. 
    </question>
    """

    body = json.dumps({
        "prompt": prompt + " \n\nAssistant:",
        "max_tokens_to_sample": 2000,
        "temperature": 0.1,
        "top_p": 0.9,
    })
    modelId = 'anthropic.claude-v2' 
    accept = 'application/json'
    contentType = 'application/json'

    response = brt.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
    response_body = json.loads(response.get('body').read())
    print(response_body)
    response = response_body.get('completion')
    response = response.strip().replace("\n", "").strip()
    response = response.strip().replace("<answer>", "").replace("</answer>", "").strip()
    print(response)
    
    # the LLM response has a sentence we need to trim off before the JSON formatted data appears
    pos = response.find('[')
    if pos == -1:
        return json.loads(response)
    else:
        return json.loads(response[pos:])


def get_summary_from_excerpt(a_transcript, a_word_length):
    body = json.dumps({
        "prompt": "Human: Write a " + str(
            a_word_length) + " word newspaper story about this part of a speech. Ignore the time information in brackets. " +
                  a_transcript + " \n\nAssistant:",
        "max_tokens_to_sample": 1000,
        "temperature": 0.1,
        "top_p": 0.9,
    })
    modelId = 'anthropic.claude-v2' 
    accept = 'application/json'
    contentType = 'application/json'

    response = brt.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
    response_body = json.loads(response.get('body').read())

    response = response_body.get('completion')
    pos = response.find('\n\n')
    return response[pos + 2:]


def lambda_handler(event, context):
    print(event)

    results = []

    # 'event' is the input event payload passed to Lambda
    mre_dataplane = DataPlane(event)
    mre_outputhelper = OutputHelper(event)
    mre_pluginhelper = PluginHelper(event)
    mre_controlplane = ControlPlane(event)
    
    # get all dependent detector data
    depResults = mre_dataplane.get_dependent_plugins_output()
    print(depResults)

    try:
        summary_word_length = int(event["Plugin"]["Configuration"]["summary_word_length"])  # 150
        search_window_seconds = int(event["Plugin"]["Configuration"]["search_window_seconds"]) #180
        chunk_start = float(event['Input']['Metadata']['HLSSegment']['StartTime'])
        chunk_duration = int(event['Input']['Metadata']['HLSSegment']['Duration'])
        chunk_number = int((chunk_start + chunk_duration) / chunk_duration)
        chunk_window = int(search_window_seconds / chunk_duration)
        
        # get event level context variables
        context_vars = mre_controlplane.get_event_context_variables()
        print(context_vars)
        last_theme = context_vars['Last_Theme']
        
        #get all chunk vars within the search window to assemble the subset of the transcript looking back <search_window_seconds> ago. No negative values at the start.
        transcript = get_transcript(event['Event']['Program'], event['Event']['Name'], max(chunk_number - chunk_window, 0))
        print (transcript)
        
        # append context variable with timecode and ensure they are sorted based on start time
        chunk_transcript = ''
        sorted_transcriptions = sorted(depResults['DetectSentiment'], key=lambda d: d["Start"])
        for result in sorted_transcriptions:
            chunk_transcript += ' [' + str(result['Start']) + '] ' + result['Transcription']
        new_transcript = transcript + chunk_transcript
        set_chunk_vars(event['Event']['Program'], event['Event']['Name'], chunk_number, 'transcription', chunk_transcript)

        last_theme = ""
        themes = get_themes_from_transcript(new_transcript, last_theme) 
        for theme in themes:
            result = {}
            result["Start"] = theme["Start"]
            result["End"] = theme["End"]
            result["Label"] = theme['Theme']
            if theme["End"] is not None:
                result["Transcript"] = get_excerpt(new_transcript, theme["Start"], theme["End"])
                result["Summary"] = ""  #get_summary_from_excerpt(result["Transcript"], summary_word_length)
                result["Celebrities"] = get_celebs_for_theme(depResults["DetectCelebrities"], theme["Start"], theme["End"])
                result["Sentiment"] = get_sentiment_for_theme(depResults["DetectSentiment"], theme["Start"], theme["End"])
                #result["Image_Summary"] = get_image_description(depResults["DetectCelebrities"], theme["Start"], theme["End"])
                results.append(result)
                last_theme = theme['Theme']

        print(f'results:{results}')
        
        temp_vars = {}
        temp_vars["Last_Theme"] = last_theme
        mre_controlplane.update_event_context_variables(temp_vars)

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