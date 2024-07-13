# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import cv2
import math
from botocore.exceptions import ClientError
import requests
import ast

from MediaReplayEnginePluginHelper import OutputHelper
from MediaReplayEnginePluginHelper import PluginHelper
from MediaReplayEnginePluginHelper import Status
from MediaReplayEnginePluginHelper import DataPlane

rek_client = boto3.client('rekognition')

#check if a specific celebrity is in a search list that is desired to be flagged
def check_celeb(aName, aSearchList):
    
    list_position = [idx for idx, s in enumerate(aSearchList) if aName in s]
    if len(list_position) > 0:
        return "flag_celebrity" + list_position[0]
    else
        return ""
    
def lambda_handler(event, context):

    print(event)

    results = []
    mre_dataplane = DataPlane(event)

    # 'event' is the input event payload passed to Lambda
    mre_outputhelper = OutputHelper(event)

    try:

        # Download the HLS video segment from S3
        media_path = mre_dataplane.download_media()

        # plugin params
        _, chunk_filename = head, tail = os.path.split(event["Input"]["Media"]["S3Key"])

        minimum_confidence = int(event["Plugin"]["Configuration"]["minimum_confidence"]) #30     
        celebrity_list = ast.literal_eval(event['Plugin']['Configuration']['celebrity_list']) #['Joe', 'Bob', 'Mary'] in order for output attributes 

        # Frame rate for sampling
        p_fps = int(event["Profile"]["ProcessingFrameRate"]) #i.e. 5
        v_fps = int(event["Input"]["Metadata"]["HLSSegment"]["FrameRate"]) #i.e. 25
        frameRate = int(v_fps/p_fps)

        cap = cv2.VideoCapture(media_path)
        
        # loop through frames in video chunk file
        while(cap.isOpened()):
            frameId = cap.get(1) #current frame number
            ret, frame = cap.read()

            if (ret != True):
                break

            # skip frames to meet processing FPS requirement
            if (frameId % math.floor(frameRate) == 0):
                hasFrame, imageBytes = cv2.imencode(".jpg", frame)
                if(hasFrame):               
                    #print(f'working on frame {frameId}')
                    response = rek_client.recognize_celebrities(
                        Image={'Bytes': imageBytes.tobytes()}
                    )

                    elabel = {}
                    if len(response["CelebrityFaces"]) > 0:
                        aLabel = ""
                        for celeb in response["CelebrityFaces"]:
                            if celeb["MatchConfidence"] > minimum_confidence:
                                aLabel += celeb["Name"]                            
                                out_attribute = check_celeb(celeb["Name"], celebrity_list)
                                if (out_attribute != ""):
                                    elabel[out_attribute] = True

                        # Get timecode from frame
                        elabel["Start"] = mre_dataplane.get_frame_timecode(frameId)
                        elabel["End"] = elabel["Start"]
                        elabel["frameId"] = frameId
                        elabel["Label"] = aLabel
                        results.append(elabel)


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