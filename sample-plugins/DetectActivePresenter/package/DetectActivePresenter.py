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

    # 'event' is the input event payload passed to Lambda
    mre_dataplane = DataPlane(event)
    mre_outputhelper = OutputHelper(event)
    mre_pluginhelper = PluginHelper(event)
    mre_controlplane = ControlPlane(event)

    # get all dependent detector data
    depResults = mre_dataplane.get_dependent_plugins_output()
    # print(depResults)

    try:
        duration_seconds = int(event["Plugin"]["Configuration"]["duration_seconds"])  # 3
        desired_presenters = ast.literal_eval(event['Plugin']['Configuration'][
                                                  'desired_presenters'])  # ['Joe', 'Bob', 'Mary'] in order for output attributes

        # check for global context var to see if already Active_Presenter == True, if so exit
        context_vars = mre_controlplane.get_event_context_variables()
        print(context_vars)

        # TODO integrate the duration_seconds to make sure its real

        # check the celeb data for the desired speaker
        for celeb in depResults['DetectCelebrities']:
            a_celebs_list = json.loads(celeb['Celebrities_List'])
            if all(person in a_celebs_list for person in desired_presenters):
                # we found it
                result = {}
                result["Start"] = celeb["Start"]
                result["End"] = celeb["End"]
                result["Label"] = "Found the celeb"
                result["Active_Presenter"] = True
                results.append(result)
                context_vars["data"]["Active_Presenter"] = True
                # mre_controlplane.update_event_context_variables(context_vars["data"])
                break

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