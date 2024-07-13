# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import cv2
import math
from botocore.exceptions import ClientError
import requests
import ast
import json
import base64

from MediaReplayEnginePluginHelper import OutputHelper
from MediaReplayEnginePluginHelper import PluginHelper
from MediaReplayEnginePluginHelper import Status
from MediaReplayEnginePluginHelper import DataPlane

s3_client = boto3.client('s3')
sagemaker_runtime = boto3.client('sagemaker-runtime')


def process_frame(a_ml_endpoint, a_image):
    # Convert image to base64
    image_base64 = base64.b64encode(a_image)
    image = image_base64.decode('utf-8')
    prompt = "Describe the image with as much detail as possible. State only facts you see in the image but do not infer things that are not visible or subjective to opinion"

    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=a_ml_endpoint,
        ContentType='application/json',
        Body=json.dumps({
            'image': image,
            'prompt': prompt,
            'repetition_penalty': 3.0,
        })
    )

    result = response['Body'].read().decode('utf-8').strip('"')
    print(result)
    return result


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

        minimum_confidence = int(event["Plugin"]["Configuration"]["minimum_confidence"])  # 30
        ml_model_endpoint = "huggingface-pytorch-inference-2024-01-24-22-42-20-303"  # arn:aws:sagemaker:us-west-2:842081126128:endpoint/

        # Frame rate for sampling
        p_fps = int(event["Profile"]["ProcessingFrameRate"])  # i.e. 5
        v_fps = int(event["Input"]["Metadata"]["HLSSegment"]["FrameRate"])  # i.e. 25
        frameRate = int(v_fps / p_fps)

        cap = cv2.VideoCapture(media_path)
        additional_skip = False
        skip_cnt = 0

        # loop through frames in video chunk file
        while cap.isOpened():
            frameId = cap.get(1)  # current frame number
            ret, frame = cap.read()

            if not ret:
                break

            # skip frames to meet processing FPS requirement
            if frameId % math.floor(frameRate) == 0 and not additional_skip:
                hasFrame, imageBytes = cv2.imencode(".jpg", frame)
                if hasFrame:
                    # print(f'working on frame {frameId}')
                    response = process_frame(ml_model_endpoint, imageBytes)
                    result = {}

                    # Get timecode from frame
                    result["Start"] = mre_dataplane.get_frame_timecode(frameId)
                    result["End"] = result["Start"]
                    result["frameId"] = frameId
                    result["Label"] = "The iamge has been summarized"
                    result["Image_Summary"] = response
                    results.append(result)

            # temp solution to process every other second to speed this plugin up
            skip_cnt += 1
            if skip_cnt > 15:
                additional_skip = not additional_skip
                skip_cnt = 0

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