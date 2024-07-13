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

sns_client = boto3.client('sns')
    
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

    return ','.join(new_celeb_list)


def lambda_handler(event, context):
    print(event)

    results = []
    active_presenter_flag = None

    # 'event' is the input event payload passed to Lambda
    mre_dataplane = DataPlane(event)
    mre_outputhelper = OutputHelper(event)
    mre_pluginhelper = PluginHelper(event)
    mre_controlplane = ControlPlane(event)

    # get all dependent detector data
    depResults = mre_dataplane.get_dependent_plugins_output()
    # depResults = event["Deps"]
    print(depResults)

    try:
        duration_seconds = int(event["Plugin"]["Configuration"]["duration_seconds"])  # 3
        desired_presenters = ast.literal_eval(event['Plugin']['Configuration'][
                                                  'desired_presenters'])  # ['Joe', 'Bob', 'Mary'] in order for output attributes
        topic_arn = event['Plugin']['Configuration']['sns_topic_arn'] if "sns_topic_arn" in event['Plugin']['Configuration'] and event['Plugin']['Configuration']['sns_topic_arn'] != "" else None
        notification_message = event["Plugin"]["Configuration"]["notification_message"] if event["Plugin"]["Configuration"]["notification_message"] != "" else ''
        
        # check for global context var to see if already Active_Presenter == True, if so exit
        context_vars = mre_controlplane.get_event_context_variables()
        print(f"context_vars: {context_vars}")
        sent_notifications = json.loads(context_vars["sent_notifications"]) if "sent_notifications" in context_vars else {}
        
        # # context_vars = event["ContextVars"]
        # if context_vars["Active_Presenter"] == True:
        #     mre_outputhelper.update_plugin_status(Status.PLUGIN_COMPLETE)
        #     return mre_outputhelper.get_output_object()
            
        # Process the Speech detection
        sorted_detected_speech = sorted(depResults["DetectSpeech"], key=lambda d: d["Start"])
        for speech in sorted_detected_speech:
            if "speech-detection" in sent_notifications:
                break
            
            event_id = f'{event["Event"]["Program"]}#{event["Event"]["Name"]}'
            message = {
                "event": event_id, 
                "start": str(speech["Start"]), 
                "type": "speech-detection", 
                "celebrity": speech["Speaker"] if "Speaker" in speech else "unknown"
            }
                
            active_presenter_flag = True
            result = {}
            result["Start"] = speech["Start"]
            result["End"] = speech["End"]
            result["Label"] = "Speech Detected"
            result["Message"] = message
            # result["Active_Presenter"] = True
            
            results.append(result)
            if topic_arn != None and topic_arn != "TBD":
                sent_notifications["speech-detection"] = message
                response = sns_client.publish(TopicArn=topic_arn, Message=json.dumps(message))
                print(f"SNS Message: {message}")
            break
        
        
        sorted_detected_celebs = sorted(depResults["DetectCelebrities"], key=lambda d: d["Start"])
        active_presenters_occurrences = 0
        pos = 0
        # check the celeb data for the desired speaker
        for celeb in sorted_detected_celebs:
            a_celebs_list = json.loads(celeb['Celebrities_List'])
            
            if all(person in a_celebs_list for person in desired_presenters):
                # we found it and accumulated the occurrence
                active_presenters_occurrences += 1
            else:
                active_presenters_occurrences = 0
                
            if active_presenters_occurrences >= duration_seconds:
                result = {}
                result["Start"] = celeb["Start"]
                result["End"] = celeb["End"]
                result["Label"] = "Active Presenter(s) Found: " + ', '.join(ast.literal_eval(celeb["Celebrities_List"]))
                result["Message"] = notification_message
                result["Active_Presenter"] = True
                results.append(result)
                
                # Publish SNS message to the Topic
                if topic_arn != None and topic_arn != "TBD":
                    for celeb_name in a_celebs_list:
                        if celeb_name in sent_notifications:
                            continue
                        
                        event_id = f'{event["Event"]["Program"]}#{event["Event"]["Name"]}'
                        message = {
                            "event": event_id, 
                            "start": str(celeb["Start"]), 
                            "type": "celebrity-detection", 
                            "celebrity": celeb_name
                        }
                        sent_notifications[celeb_name] = message
                        response = sns_client.publish(TopicArn=topic_arn, Message=json.dumps(message))
                        
                        print(f"SNS Message: {message}")
                # break
        
        temp_vars = {}
        temp_vars["Active_Presenter"] = active_presenter_flag
        temp_vars["sent_notifications"] = json.dumps(sent_notifications)
        # temp_vars["sent_notifications"] = "{}"
        mre_controlplane.update_event_context_variables(temp_vars)
                
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