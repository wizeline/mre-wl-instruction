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
from decimal import Decimal
from random import randint
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import json_repair

from MediaReplayEnginePluginHelper import OutputHelper
from MediaReplayEnginePluginHelper import PluginHelper
from MediaReplayEnginePluginHelper import Status
from MediaReplayEnginePluginHelper import DataPlane
from MediaReplayEnginePluginHelper import ControlPlane

brt = boto3.client(service_name='bedrock-runtime')

host = os.environ['OPEN_SEARCH_SERVERLESS_CLUSTER_EP'] # cluster endpoint, for example: my-test-domain.us-east-1.aoss.amazonaws.com
region = os.environ['OPEN_SEARCH_SERVERLESS_CLUSTER_REGION']
service = 'aoss'
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, region, service)

opensearch_client = OpenSearch(
    hosts = [{'host': host, 'port': 443}],
    http_auth = auth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection,
    pool_maxsize = 20
)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
chunk_vars_table = dynamodb.Table('temp-chunk-vars')
genai_templates_table = dynamodb.Table('temp-genai-templates')
mre_plugin_results_table = dynamodb.Table('aws-mre-dataplane-PluginResult28900DF5-1KCYLR8OU2JZ2')

model = "anthropic.claude-3-sonnet-20240229-v1:0"
#model = "anthropic.claude-3-haiku-20240307-v1:0"

# function to get record from dynamodb table
def get_transcript(a_program, a_event, a_start_chunk_number):
    # Specify the key condition expression for the query
    key_condition_expression = Key('program-event').eq(a_program + '::' + a_event) & Key('chunk_number').gt(a_start_chunk_number)

    # Perform the query
    response = chunk_vars_table.query(
        KeyConditionExpression=key_condition_expression
    )
    if len(response['Items']) == 0:
        return ""
    else:
        print("Found transcript history to assemble with")
        transcript = ""
        for chunk in response['Items']:
            if chunk['transcription'] != None:
                transcript += ' ' + chunk['transcription'] 
        return transcript


def set_chunk_vars(a_program, a_event, a_chunk, a_attribute, a_value):
    # Perform the update
    response = chunk_vars_table.update_item(
        Key={
            'program-event': a_program + '::' + a_event,
            'chunk_number': a_chunk
        },
        UpdateExpression='SET ' + a_attribute + ' = :val',
        ExpressionAttributeValues={
            ':val': a_value
        }
    )


def get_segments(a_program, a_event, a_segmenter, a_start):
    # Specify the key condition expression for the query
    key_condition_expression = Key('PK').eq(a_program + '#' + a_event + '#' + a_segmenter) & Key('Start').eq(Decimal(str(a_start)))
    
    # Perform the query
    response = mre_plugin_results_table.query(
        KeyConditionExpression=key_condition_expression
    )
    return response['Items']
    
     
def get_segments_by_label(a_program, a_event, a_segmenter, a_label):
    # Specify the key condition expression for the query
    key_condition_expression = Key('PK').eq(a_program + '#' + a_event + '#' + a_segmenter) 
    filter_expression = Attr("Label").eq(a_label) 
    
    # Perform the query
    response = mre_plugin_results_table.query(
        KeyConditionExpression=key_condition_expression,
        FilterExpression=filter_expression
    )
    return response['Items']
    
    
def delete_segment(a_program, a_event, a_segmenter, a_start):
    print(f"Deleting for start={str(a_start)}")

    segments = get_segments(a_program, a_event, a_segmenter, a_start)
    print(segments)
    
    #if len(segments) > 0:
        #a_doc_id = segments[0]['aoss_doc_id']
        
        #response = opensearch_client.delete(
        #    index = 'mre_news_index',
        #    id = str(a_doc_id)
        #)
        #print(f"delete from open search successful: {response}")
    
    response = mre_plugin_results_table.delete_item(
        Key={
            'PK': a_program + '#' + a_event + '#' + a_segmenter,
            'Start': Decimal(str(a_start))
        }
    )
    
    print("delete successful")
    

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
        
    
# function to get plugin output attribute data
def get_plugin_data(a_program, a_event, a_plugin, a_start):
    # Specify the key condition expression for the query
    key_condition_expression = Key('PK').eq(a_program + '#' + a_event + '#' + a_plugin) & Key('Start').gt(Decimal(str(a_start)))
 
    # Perform the query
    response = mre_plugin_results_table.query(
        KeyConditionExpression=key_condition_expression
    )
    if len(response['Items']) == 0:
        return []
    else:
        return response['Items']
        
        
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
            #if new_sentiment_list.count(sentiment_frame['primary_sentiment']) == 0:
            new_sentiment_list.append(sentiment_frame['primary_sentiment'])
                    
    if len(new_sentiment_list) > 0: 
        a_result = ','.join(new_sentiment_list)
    else:
        a_result = ''
    return a_result
    
        
def get_image_description(a_scene_list, a_start, a_end):
    new_scene_labels_list = []
    # many frames were described using a LLM
    for scene_label in a_scene_list:
        #print(scene_label)
        if scene_label['Start'] >= a_start and scene_label['End'] <= a_end:
            astr = scene_label['Image_Summary']
            labels_in_a_frame = json_repair.loads(astr)
            for label in labels_in_a_frame:
                # check for dups
                if new_scene_labels_list.count(label) == 0:
                    new_scene_labels_list.append(label)
                    
    if len(new_scene_labels_list) > 0: 
        a_result = ','.join(new_scene_labels_list)
    else:
        a_result = ''
    return a_result
    

# clip out the transcript from start to end for a theme
def get_excerpt(a_transcript, a_start, a_end):
    pos_start = a_transcript.find(str(a_start))
    pos_end = a_transcript.find(str(a_end))
    if pos_end > 500:
        print("Truncated the transcription")
        pos_end = 500
    return a_transcript[pos_start - 1:pos_end - 1]


def generate_bedrock_message(bedrock_runtime, model_id, messages, max_tokens, top_p, temp):
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temp,
            "top_p": top_p
        }
    )

    response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
    response_body = json_repair.loads(response.get('body').read())

    return response_body
    
    
def get_themes_from_transcript(a_transcription, a_last_theme, a_prompt_template):
    ''' Sample response
    ' Here are the key themes in the speech with start and end timings:\n\n[{"Theme": "Greeting and thanking the audience", "Start": "1.69", "End": "43.789"}, {"Theme": "Congratulating new Congressional leadership", "Start": "51.21", "End": "160.009"}, {"Theme": "America\'s resilience and progress", "Start": "219.12", "End": "240.009"}, {"Theme": "Bipartisan accomplishments", "Start": "260.86", "End": "380.009"}, {"Theme": "Appealing for continued bipartisanship", "Start": "400.31", "End": "410.979"}]'
    '''
    #The Start and End times are mandatory as floating point numbers.

    if a_last_theme != "<none>":
        a_theme_list = a_last_theme
    else:
        a_theme_list = ""
        
    prompt = f"""{get_prompt_template(a_prompt_template)}"""
    data = {
        "a_transcription": a_transcription,
        "a_theme_list": a_theme_list
    }
    prompt = prompt.format(**data)

    #messages=[{ "role":'user', "content":[{'type':'text','text': prompt}]}, {"role":"assistant", "content":"response: {"}]
    messages=[{ "role":'user', "content":[{'type':'text','text': prompt}]}]
    response_body = generate_bedrock_message(brt, model_id = model, messages=messages, max_tokens=2000, temp=0.1, top_p=0.9)
    
    response = response_body['content'][0]['text']
    response = response.strip().replace("\n", "").strip()
    response = response.strip().replace("<answer>", "").replace("</answer>", "").strip()
    response = response.strip().replace("Decimal(", "").replace("\"),", "\",").strip()
    
    #response = response.replace("\'", "\"")
    print(f"LLM response: {response}")
    
    return json_repair.loads(response)["Themes"]


def construct_segment(theme, new_transcript, depResults, leave_open_ended, celeb_plugin_data, sentiment_plugin_data, scene_plugin_data):
    
    result = {}
    #random_offset = randint(0, 29)/30
    #result["Start"] = round(theme["Start"] + random_offset, 3)
    result["Start"] = theme["Start"]
    if not leave_open_ended:
        result["End"] = theme["End"]
    result["Label"] = theme["Theme"]
    result["Desc"] = theme["Theme"]
    if theme["End"] is not None:
        celebs = get_celebs_for_theme(celeb_plugin_data, theme["Start"], theme["End"])
        print('final celebs list')
        print(celebs)
        
        sentiment = get_sentiment_for_theme(sentiment_plugin_data, theme["Start"], theme["End"])
        print(sentiment)
        
        image_summary = get_image_description(scene_plugin_data, theme["Start"], theme["End"])
        print(f"image_summary = {image_summary}")
        
        result["Transcript"] = get_excerpt(new_transcript, theme["Start"], theme["End"])
        result["Summary"] = theme["Summary"]
        result["Celebrities"] = celebs
        result["Sentiment"] = sentiment
        result["Image_Summary"] = image_summary
        print(result)
        
    return result
    

def lambda_handler(event, context):
    # 'event' is the input event payload passed to Lambda
    print(event)

    mre_dataplane = DataPlane(event)
    mre_outputhelper = OutputHelper(event)
    mre_pluginhelper = PluginHelper(event)
    mre_controlplane = ControlPlane(event)

    # get all dependent detector data
    depResults = mre_dataplane.get_dependent_plugins_output()
    print("depResults:", depResults)
    
    results = []

    try:
        # get all detector data since last start or end plus this current chunk
        state, segment, labels = mre_dataplane.get_segment_state()
        print("state: ", str(state))
        print("segment: ", segment)
        print("labels: ", labels)

        chunk_start_time = event['Input']['Metadata']['HLSSegment']['StartTime']
        min_segment_length = 30

        summary_word_length = int(event["Plugin"]["Configuration"]["summary_word_length"])  # 150
        search_window_seconds = 400 #int(event["Plugin"]["Configuration"]["search_window_seconds"]) #180
        chunk_start = float(event['Input']['Metadata']['HLSSegment']['StartTime'])
        chunk_duration = int(event['Input']['Metadata']['HLSSegment']['Duration'])
        chunk_number = int((chunk_start + chunk_duration) / chunk_duration)
        chunk_window = int(search_window_seconds / chunk_duration)
        
        # get event level context variables
        context_vars = mre_controlplane.get_event_context_variables()
        print(context_vars)
        if "Last_Theme" in context_vars:
            last_theme = context_vars['Last_Theme']
        else:
            last_theme = ""
            
        if 'Prompt_Name' in context_vars: 
            a_prompt_template = context_vars['Prompt_Name']
        else: 
            a_prompt_template = "news1"
        
        #get all chunk vars within the search window to assemble the subset of the transcript looking back <search_window_seconds> ago. No negative values at the start.
        transcript = get_transcript(event['Event']['Program'], event['Event']['Name'], max(chunk_number - chunk_window, 0))
        print (f"transcript: {transcript}")
        
        # append context variable with timecode and ensure they are sorted based on start time
        chunk_transcript = ''
        print(f"depResults for DetectSentiment: {depResults['DetectSentiment']}")
        sorted_transcriptions = sorted(depResults['DetectSentiment'], key=lambda d: d["Start"])
        for cnt, result in enumerate(sorted_transcriptions):
            chunk_transcript += ' [' + str(result['Start']) + '] ' + result['Transcription']
                
        new_transcript = transcript + chunk_transcript
        print(f"set_chunk_vars: chunk_transcript >> {chunk_transcript}")
        set_chunk_vars(event['Event']['Program'], event['Event']['Name'], chunk_number, 'transcription', chunk_transcript)
        print(f"new_transcript: {new_transcript}") 
        if len(new_transcript.strip()) > 0:
            themes = get_themes_from_transcript(new_transcript, last_theme, a_prompt_template) 
            print(themes)
            #themes = themes
            #good_json_string = repair_json(bad_json_string)
            theme_count = len(themes)
            print(f"theme_count: {theme_count} themes: {themes}")
            sorted_themes = sorted(themes, key=lambda d: d["Start"])
            
            found_theme_after_last = False
            print(f"sorted_themes: {sorted_themes}")
        else:
            print("No transcript generated, skipping theme detection")
            sorted_themes = []
        
        #list of themes to save. it will appended as processing logic dictates
        themes_to_save = []
        
        # themes will overlap earlier clips/segments identified
        for theme in sorted_themes:
            print(theme)
            add_theme = False
            # if theme['Start'] >= chunk_start_time - 30:
            if theme["End"] is not None:
                if theme['End'] - theme['Start'] > min_segment_length:
                    #check for prior segments at this same start time
                    prior_segments = get_segments(event['Event']['Program'], event['Event']['Name'], 'SegmentNews', theme['Start'])
                    if len(prior_segments) == 0:
                        print("no prior segments")
                        matching_theme_name_segments = get_segments_by_label(event['Event']['Program'], event['Event']['Name'], 'SegmentNews', theme['Theme'])
                        if len(matching_theme_name_segments) == 0:
                            print("no dup themes found using a label search")
                            #add the new one
                            add_theme = True
                        else:
                            print("prior matches with theme name")
                            #loop through matching themes with the same name
                            for prior_matching_theme in matching_theme_name_segments:
                                #if match started earlier, keep that one with the greater end time of the two 
                                if prior_matching_theme["Start"] < theme["Start"]:
                                    print("prior match with theme name and start earlier than new theme")
                                    
                                    #delete the shorter theme
                                    delete_segment(event['Event']['Program'], event['Event']['Name'], 'SegmentNews', theme['Start'])
                                    
                                    #add new theme with earlier start time 
                                    theme["Start"] = prior_matching_theme["Start"] - 1
                                    add_theme = True
                                    
                                    #add new theme with later end time
                                    if prior_matching_theme["End"] > theme["End"]: 
                                        theme["End"] = prior_matching_theme["End"] + 1
                                else:
                                    #delete the shorter theme that started after the new theme
                                    print("deleting a shorter segment that started after the new theme")
                                    delete_segment(event['Event']['Program'], event['Event']['Name'], 'SegmentNews', prior_matching_theme['Start'])
                                    
                    #there are prior segments at this start time                
                    else:
                        print("prior segment at the start time")
                        #get max duration of prior segment
                        max_prior_segment_duration = 0
                        for segment in prior_segments:
                            if "End" in segment:
                                prior_segment_duration = segment["End"] - segment["Start"]
                                if prior_segment_duration > max_prior_segment_duration:
                                    max_prior_segment_duration = prior_segment_duration 
                        
                        print("max prior seg duration: " + str(max_prior_segment_duration))            
                        #is the new theme/segment longer than the prior segments that start at the same time. If not, skip it            
                        if theme['End'] - theme['Start'] > max_prior_segment_duration:
                            #delete the old one
                            print("deleting shorter segment")
                            delete_segment(event['Event']['Program'], event['Event']['Name'], 'SegmentNews', theme['Start'])
                            
                            #add the new one
                            add_theme = True
                            
            if add_theme:
                themes_to_save.append(theme)
                
                
        #figure out what the earliest theme is 
        sorted_themes_to_save = sorted(themes_to_save, key=lambda d: d["Start"])
        earliest_start = -1
        theme_count = len(sorted_themes_to_save)
        if theme_count > 0:
            earliest_start = sorted_themes_to_save[0]['Start']
                
        celeb_plugin_data = []
        scene_plugin_data = []
        sentiment_plugin_data = []
        if earliest_start > -1:
            print("getting dependent data")
            celeb_plugin_data = get_plugin_data(event['Event']['Program'], event['Event']['Name'], 'DetectCelebrities', earliest_start)
            sentiment_plugin_data = get_plugin_data(event['Event']['Program'], event['Event']['Name'], 'DetectSentiment', earliest_start)
            scene_plugin_data = get_plugin_data(event['Event']['Program'], event['Event']['Name'], 'DetectSceneLabels', earliest_start)
            
        for theme in sorted_themes_to_save:    
            leave_open_ended = False
            #cleanup for eroneous Decimal() cast in the json output
            a_start = str(theme["Start"])
            a_start.strip().replace("Decimal(", "").replace("\"),", "\",").strip()
            theme["Start"] = float(a_start)
            
            a_end = str(theme["End"])
            a_end.strip().replace("Decimal(", "").replace("\"),", "\",").strip()
            theme["End"] = float(a_end)
            
            results.append(construct_segment(theme, new_transcript, depResults, leave_open_ended, celeb_plugin_data, sentiment_plugin_data, scene_plugin_data))
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

