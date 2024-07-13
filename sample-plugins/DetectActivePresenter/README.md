# DetectActivePresenter #

**MRE Plugin Class**
- Featurer

**Description**:

A plugin to detect whether a specific presenter is active.

**Applies to Media Type**:
- Video

**Use Cases**:
- News, Sports or other presenter detection.

**Dependencies**:
- MRE Helper libraries

**ML Model dependencies**:
- None

**Other plugin dependencies**:
- DetectSpeech
- DetectCelebrities

**Parameter inputs**:
- desired_presenters >> a string list of names ["Joe Biden"]
- duration_seconds >> how long to observe the data before a state transition

**Output attributes**:
- Label >> Comment about the state of presenting active/inactive
- Celebrities >> a list of celebrities found in the clip
- Active_Presenter >> boolean indicating whether presenter is active

**IAM permissions (least privilege)**:
- None
