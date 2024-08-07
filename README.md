# MRE - WizeLine instruction

## Prerequisites

* python == 3.11
* aws-cli
* aws-cdk >= 2.24.1
* docker
* node = 18.20+
* npm >= 10.2.3
* git

## How to install MRE

## Step 1: Install MRE Core

```bash
export REGION=[specify the AWS region. For example, us-east-1 or us-west-2]
export VERSION=2.9.0
git clone https://git-codecommit.us-east-1.amazonaws.com/v1/repos/aws-media-replay-engine-gen-ai
cd aws-media-replay-engine-gen-ai
git checkout wl-main
cd deployment
./build-and-deploy.sh --enable-ssm-high-throughput --enable-generative-ai --version $VERSION --region $REGION --verbose [--profile <aws-profile>]
```

to re-deploy skipping the layer generation

```bash
./build-and-deploy.sh --enable-ssm-high-throughput --enable-generative-ai --no-layer --version $VERSION --region $REGION --verbose [--profile <aws-profile>]
```

## Step 2: Install MRE's plugins

1. Install necessasry lambda layers at `lambda-layers`:
   
```bash
cd lambda-layers
./deploy.sh [aws-profile] [aws-region]
```

2. Deploy the sample plugins:

```bash
cd aws-media-replay-engine-gen-ai/samples/deployment
./build-and-deploy.sh --app plugin-samples --region $REGION [--profile <aws-profile>]
```

## Step 3: Plugin configuration:

**Many (or all) steps in this section can be automated in script file, but at the point when this document is written, we don't have time and resource to update the script**

<!-- 1. [Add plugin roles](Plugin-Roles.md) -->
<!-- 2. Create the following S3 buckets:
  
  - `mre-transcribe-files-wizeline`
  - `mre-voice-samples-training-wizeline`
  - `mre-wizeline-video-samples`: Enable Bucket Versioning -->

1. Add `DetectSpeech` new version with bucket name `mre-transcribe-files-wizeline` and `mre-voice-samples-training-wizeline`:

    ![DetectSpeechConfig](assets/DetectSpeechConfig.png)

<!-- 4. Create `temp-chunk-vars` table in dynamodb -->
2. Request model access in Bedrock:
  - Titan Embeddings G1 - Text
  - Titan Text G1 - Express
  - Titan Text Embeddings V2
  - Claude 3 Sonnet
  - Claude 3 Haiku
  - Claude
  - Claude Instant
  - Embed English
3. Create OpenSearch Serverless cluster `aws-mre-collection`
  - Collection name: aws-mre-collection
  - Collection type: Vector search
  - Deployment type (Optional): Enable redundancy (active replicas)
  - Security: Standard create
  - Encryption: Use AWS owned key
  - Network access settings:
    + Access Type: Public
    + Enable access to OpenSearch endpoint
    + Enable access to OpenSearch Dashboards
  - Configure data access:
    + Rule 1: Add all needed principals and permissions
![Rule 1 Config](assets/OpenSearchAccessControlRule1.png)
    + Rule 2: Add all needed principals and permissions
![Rule 1 Config](assets/OpenSearchAccessControlRule2.png)

4. Update lambda functions below for missing configurations:
  <!-- - DetectSceneLabels:
    + Add Layers: MediaReplayEnginePluginHelper, Pillow, boto3, pyAV
    + Find dynamoDB table which the prefix `wl-mre-custom-api-GenAiTemplates` and update lambda parameter with corespoding value  `genai_templates_table = dynamodb.Table('wl-mre-custom-api-GenAiTemplates...')`

  - DetectCelebrities:
    + Add Layers: MediaReplayEnginePluginHelper, Pillow, pyAV, json-repair
    + Find dynamoDB table which the prefix `wl-mre-custom-api-GenAiTemplates` and update lambda parameter with corespoding value `genai_templates_table = dynamodb.Table('wl-mre-custom-api-GenAiTemplate...')`

  - DetectSpeech:
    + Add Layers: MediaReplayEnginePluginHelper, ffmpeg -->

  - SegmentNews: Also change Dynamo table names
    <!-- + Add Layers: MediaReplayEnginePluginHelper, opensearch-py, boto3, json-repair -->
    + Find dynamoDB table which the prefix `wl-mre-custom-api-GenAiTemplates` and create the environment variable `GEN_AI_TEMPLATES_TABLE_NAME` and assign the found value. The value should looks like `wl-mre-custom-api-GenAiTemplate...`
    + Find dynamoDB table which the prefix `aws-mre-dataplane-PluginResult` and create the environment variable `MRE_PLUGIN_RESULTS_TABLE_NAME` and assign the found value. The value should looks like `aws-mre-dataplane-PluginResult...`
    + More env vars:
      ```
      OPEN_SEARCH_SERVERLESS_CLUSTER_EP: {{Open search endpoint of aws-mre-collection}} (e.g., el38g1x1i9agzdwkws10.us-east-1.aoss.amazonaws.com)
      OPEN_SEARCH_SERVERLESS_CLUSTER_REGION: us-east-1 or us-west-2 depending on the case
      ```

<!-- 8. Add `SegmentNews` environment variables -->
  
5. Add principle `aws-mre-search-streaming--streamSummaryJsServiceRol` to Data access policies for AOSS's `mre-vectorsearch-collection`

## Step 4: Install `live-news-segmenter` app

```bash
cd aws-media-replay-engine-gen-ai/samples/deployment
./build-and-deploy.sh --app [live-news-segmenter || live-news-segmenter-ui || live-news-segmenter-api] --region $REGION [--profile <aws-profile>]
```

## Step 5: Re-deploy `Gateway PI stack`

Due to a cyclic dependency with the live-news-segmenter API stack, it is necessary to re-deploy this stack to import the newly created `mre-custom-api-url`.

1. Open the file `aws-media-replay-engine-gen-ai/source/gateway/infrastructure/stacks/chaliceapp.py` and search for the `CUSTOM_API_URL` key. Comment out the line with the value TBD and uncomment the line below it with the final value.

From this:

```python
self.chalice = Chalice(
            self,
            self,
            self,
            "MreApiChaliceApp",
            source_dir=RUNTIME_SOURCE_DIR,
            stage_config={
                "environment_variables": {
                    "PLUGIN_URL": Fn.import_value("mre-plugin-api-url"),
                    "MODEL_URL": Fn.import_value("mre-model-api-url"),
                    "PROMPT_CATALOG_URL": Fn.import_value("mre-prompt-catalog-api-url"),
                    "CONTENT_GROUP_URL": Fn.import_value("mre-contentgroup-api-url"),
                    "EVENT_URL": Fn.import_value("mre-event-api-url"),
                    "PROFILE_URL" : Fn.import_value("mre-profile-api-url"),
                    "PROGRAM_URL" : Fn.import_value("mre-program-api-url"),
                    "REPLAY_URL" : Fn.import_value("mre-replay-api-url"),
                    "SYSTEM_URL" : Fn.import_value("mre-system-api-url"),
                    "WORKFLOW_URL" : Fn.import_value("mre-workflow-api-url"),
                    "CUSTOM_PRIORITIES_URL": Fn.import_value("mre-custompriorities-api-url"),
                    "CUSTOM_API_URL": "TBD",
                    # "CUSTOM_API_URL": Fn.import_value("mre-custom-api-url"),
                    "API_AUTH_SECRET_KEY_NAME": "mre_hsa_api_auth_secret",
                },
                "tags": {
                    "Project": "MRE"
                },
                "tags": {"Project": "MRE"},
                "manage_iam_role": False,
                "iam_role_arn": self.chalice_role.role_arn,
            },
        )
```

To this:

```python
self.chalice = Chalice(
            self,
            "MreApiChaliceApp",
            source_dir=RUNTIME_SOURCE_DIR,
            stage_config={
                "environment_variables": {
                    "PLUGIN_URL": Fn.import_value("mre-plugin-api-url"),
                    "MODEL_URL": Fn.import_value("mre-model-api-url"),
                    "PROMPT_CATALOG_URL": Fn.import_value("mre-prompt-catalog-api-url"),
                    "CONTENT_GROUP_URL": Fn.import_value("mre-contentgroup-api-url"),
                    "EVENT_URL": Fn.import_value("mre-event-api-url"),
                    "PROFILE_URL" : Fn.import_value("mre-profile-api-url"),
                    "PROGRAM_URL" : Fn.import_value("mre-program-api-url"),
                    "REPLAY_URL" : Fn.import_value("mre-replay-api-url"),
                    "SYSTEM_URL" : Fn.import_value("mre-system-api-url"),
                    "WORKFLOW_URL" : Fn.import_value("mre-workflow-api-url"),
                    "CUSTOM_PRIORITIES_URL": Fn.import_value("mre-custompriorities-api-url"),
                    # "CUSTOM_API_URL": "TBD",
                    "CUSTOM_API_URL": Fn.import_value("mre-custom-api-url"),
                    "API_AUTH_SECRET_KEY_NAME": "mre_hsa_api_auth_secret",
                },
                "tags": {
                    "Project": "MRE"
                },
                "tags": {"Project": "MRE"},
                "manage_iam_role": False,
                "iam_role_arn": self.chalice_role.role_arn,
            },
        )
```

2. Re-deploy the Stack, make sure you have activated the right AWS profile and you're pointing to the right region

```bash
cd aws-media-replay-engine-gen-ai/source/gateway
python -m venv venv
source venv/bin/activate
pip3 install -U -q -r requirements.txt
cd infrastructure
cdk bootstrap
cdk deploy
```

3. Revert the code to its original status