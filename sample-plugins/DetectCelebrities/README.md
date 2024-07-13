# DetectCelebrities #

**MRE Plugin Class**
- Featurer

**Description**:

A plugin to detect celebrities using the Amazon Rekognition API.

**Applies to Media Type**:
- Video

**Use Cases**:
- News, Sports or other presenter detection.

**Dependencies**:
- MRE Helper libraries
- opencv

**ML Model dependencies**:
- None

**Other plugin dependencies**:
- Amazon Rekognition

**Parameter inputs**:
- minimum_confidence >> 30 for example
- celebrity_list >> an ordered string list that matches the output attribute mapping you want. 5 in the default example ["Joe Biden","Donald Trump","Tom Cruise","Kamala Harris","Kevin McCarthy"]

**Output attributes**:
- Label >> List of any celebs found
- flag_celebrity1 >> boolean indicating whether celebrity1 was found
- flag_celebrity2 >> boolean indicating whether celebrity2 was found
- flag_celebrity3 >> boolean indicating whether celebrity3 was found
- flag_celebrity4 >> boolean indicating whether celebrity4 was found
- flag_celebrity5 >> boolean indicating whether celebrity5 was found

**IAM permissions (least privilege)**:
- Rekognition
