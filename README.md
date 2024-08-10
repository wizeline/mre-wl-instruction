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

1. Install lambda layers:

```bash
cd lambda-layers
./deploy.sh [aws-profile] [aws-region]
```

2. Deploy the sample plugins:

```bash
cd aws-media-replay-engine-gen-ai/samples/deployment
./build-and-deploy.sh --app plugin-samples --region $REGION [--profile <aws-profile>]
```

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
3. In the AWS console open OpenSearch Service an open the `aws-mre-collection` collection and setup the right principals:
  - Go to Data access and open de associated policy `aws-mre-collection-access-policy`
    + In Rule 1 add these principals
      - `aws-mre-dataplane-ChaliceRole` -> Sample of principal role: `arn:aws:iam::851725259499:role/aws-mre-dataplane-ChaliceRoleF025B2F9-f0yHL9FPdvKy`
      - `aws-mre-plugin-samples-SegmentNewsRole` -> Sample of principal role: `arn:aws:iam::851725259499:role/aws-mre-plugin-samples-SegmentNewsRoleC24731FD-louGX5HaYDDn`
    + In Rule 2 add this principal
      - `aws-mre-search-streaming--streamSummaryJsServiceRol` -> Sample of principal role: `arn:aws:iam::851725259499:role/aws-mre-search-streaming--streamSummaryJsServiceRol-9A1QHkp2k0GY`

4. In the AWS console open the `mre-vectorsearch-collection` collection and setup the right principals:
  - Go to Data access and open de associated policy `mre-aoss-data-access-policy`
    + In Rule 1 add this principal:
      - `aws-mre-search-streaming--streamSummaryJsServiceRol` -> Sample of principal role: `arn:aws:iam::851725259499:role/aws-mre-search-streaming--streamSummaryJsServiceRol-9A1QHkp2k0GY`

<!-- 8. Add `SegmentNews` environment variables -->

## Step 3: Install `live-news-segmenter` app API
1. ### GitHub setup
  - Create the branch of the project, for example:
    + `demo-nfl`
    + `dev-nfl`
2. ### Create the front end Amplify app
  - Create a new Amplify app based on the branch created above
    + Git provider: GitHub (After this AWS console will request your GitHub login)
    + Repository
    + Branch: the on created in the previous step (Next)
    + App Name: live-news-segmenter-frontend-{env} i.e `live-news-segmenter-frontend-dev`
    + Create a New Service Role: (New Browser tab)
      - AWS Service option 
      - Use Case: Amplify (Defaul) (Next)
      - Add permissions (Next)
      - Role Name: amplifyconsole-backend-role-{env} i.e `amplifyconsole-backend-role-dev` (Create Role)
    - Go back to the Amplify app and select the created role (next)
    - Save and Deploy

  Wait until the app is fully created to continue with the next steps

2. ### Run installation
```bash
cd aws-media-replay-engine-gen-ai/samples/deployment
./build-and-deploy.sh --app [live-news-segmenter || live-news-segmenter-ui || live-news-segmenter-api] --region $REGION [--profile <aws-profile>]
```

3. ### Amplify frontend app final setup (Env vars and custom headers)
  - Copy the file `aws-media-replay-engine-gen-ai/samples/source/live-news-segmenter/ui/cdk/template.frontend-setup.json` and rename it to `frontend-setup.json`
  - Update the values of the new created file
    + "webAppURL": You can find the app domain, excluding the protocol, in the app overview. For example: `demo-nfl.d9kh5a0nalcse.amplifyapp.com`.
    + "webAppId": You can find the app ID in the app overview
    + "region": current deployment region
    + "identityPoolId": You can find this in Cognito / Identity Pools under the created Identity pool which name will resemble `nabuie8b66a0e_identitypool_e8b66a0e__staging`. Use the Identity Pool ID, which will look similar to `us-west-2:03effd58-6db4-4ad5-a155-ccfec63b5311`.
    + "userPoolId": You can find this under the User pool overview  which will look similar to `us-west-2_2xuwGhEq9`,
    + "appClientId": You can find this under the User pool / App Integration/ App clients and App clients and analytics, get the Client ID the clientWeb one, it will look similar to `17kvktebes0dp4dbhb76qo1dm2`
  - Run the Amplify update script
    ```bash
    cd aws-media-replay-engine-gen-ai/samples/source/live-news-segmenter/ui/cdk
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python3 init-amplify.py $region [ $profile ] 2>&1
    deactivate
    rm -rf venv
    ```
  - Check the env vars in Amplify app

## Step 4: Plugins configuration:

<!-- 1. [Add plugin roles](Plugin-Roles.md) -->
<!-- 2. Create the following S3 buckets:
  
  - `mre-transcribe-files-wizeline`
  - `mre-voice-samples-training-wizeline`
  - `mre-wizeline-video-samples`: Enable Bucket Versioning -->

1. Add a new version of the `DetectSpeech` plugin:
  - Log in to the Media Replay Engine Admin tool.
  - Navigate to the "Plugins" option in the left-hand menu.
  - Search for the desired plugin.
  - Click on "Actions" and select "Add New Version" to update the plugin to the latest version.
  - Login into the Media Replay Engine Admin tool and go to plugins option in the left rail, search for the plugin and add the new verion clicking in the Actions
  - Update the values of the following configuration parameters: `training_bucket_name`, `output_bucket_name`, and `input_bucket_name`.

    + Search for the actual bucket names in your S3 buckets.
    + Replace the current values with the correct bucket names.
    + The bucket names should resemble these formats: `mre-transcribe-files-wizeline` and `mre-voice-samples-training-wizeline`.

  ![DetectSpeechConfig](assets/DetectSpeechConfig.png)

2. Update lambda functions below for extra configurations:
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
    + Locate the DynamoDB table with the prefix `wl-mre-custom-api-GenAiTemplates`, create an environment variable `GEN_AI_TEMPLATES_TABLE_NAME` and assign it the name of the found table. The value should resemble `wl-mre-custom-api-GenAiTemplate....`
    + Locate the DynamoDB table with the prefix `aws-mre-dataplane-PluginResult`, create an environment variable `MRE_PLUGIN_RESULTS_TABLE_NAME` and assign it the name of the found table. The value should resemble `aws-mre-dataplane-PluginResult....`
    + More env vars:

      ```
      OPEN_SEARCH_SERVERLESS_CLUSTER_EP: {{Open search endpoint of aws-mre-collection}} (e.g., el38g1x1i9agzdwkws10.us-east-1.aoss.amazonaws.com)
      OPEN_SEARCH_SERVERLESS_CLUSTER_REGION: us-east-1 or us-west-2 depending on the case
      ```

## Step 5: Re-deploy `Gateway API stack`

Due to a cyclic dependency with the live-news-segmenter API stack, it is necessary to re-deploy this stack to import the newly created `mre-custom-api-url`.

1. Open the file `aws-media-replay-engine-gen-ai/source/gateway/infrastructure/stacks/chaliceapp.py` and search for the `CUSTOM_API_URL` key. Comment out the line with the value TBD and uncomment the line below it with the final value.

From this:

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
python3 -m venv venv
source venv/bin/activate
pip3 install -U -q -r requirements.txt
cd infrastructure
cdk bootstrap
cdk deploy
```

3. Revert the code to its original status