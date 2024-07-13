# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os

from MediaReplayEnginePluginHelper import OutputHelper
from MediaReplayEnginePluginHelper import PluginHelper
from MediaReplayEnginePluginHelper import Status
from MediaReplayEnginePluginHelper import DataPlane


def lambda_handler(event, context):
    # 'event' is the input event payload passed to Lambda
    print(event)

    mre_dataplane = DataPlane(event)
    mre_outputhelper = OutputHelper(event)
    mre_pluginhelper = PluginHelper(event)

    chunk_start_time = event['Input']['Metadata']['HLSSegment']['StartTime']
    min_segment_length = 15

    results = []

    try:

        # get all detector data since last start or end plus this current chunk
        state, segment, labels = mre_dataplane.get_segment_state()
        print("state: ", str(state))
        print("segment: ", segment)
        print("labels: ", labels)

        # themes will overlap earlier clips/segments identified
        for theme in labels['DetectKeyContent']:
            print(theme)
            # if theme['Start'] >= chunk_start_time - 30:
            if theme['End'] - theme['Start'] > min_segment_length:
                # assemble the payload to submit to MRE with the single segment for this chunk
                result = {}
                result["Label"] = theme['Label']
                result["Desc"] = theme['Label']
                result["Start"] = theme['Start']
                result["End"] = theme['End']
                result["Summary"] = theme['Summary']
                result["Celebrities"] = theme['Celebrities']
                results.append(result)

        print(results)

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
