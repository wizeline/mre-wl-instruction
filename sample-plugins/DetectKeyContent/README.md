# DetectKeyContent #

**MRE Plugin Class**
- Featurer

**Description**:

A plugin to determine themes in transcriptions and summarize them.

**Applies to Media Type**:
- Video

**Use Cases**:
- News, Sports or other presenter detection.

**Dependencies**:
- MRE Helper libraries
- Amazon Bedrock
- Amazon DynamoDB

**ML Model dependencies**:
- None

**Other plugin dependencies**:
- DetectSpeech
- DetectCelebrities

**Parameter inputs**:
- desired_presenters >> a string list of names ["Joe Biden"]
- duration_seconds >> how long to observe the data before a state transition
- summary_word_length >> how long should the summary be

**Output attributes**:
- Label >> Comment about the state of presenting active/inactive
- Transcript >> Transcription of the theme (from start to end) with timecode added 
- Summary >> LLM summary of the theme at the specified length
- Celebrities >> String list of detected celebrities

**IAM permissions (least privilege)**:
- None
