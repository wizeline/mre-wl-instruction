# SegmentNews #

**MRE Plugin Class**
- Segmenter

**Description**:

This plugin is used to clip news topics from summarized transcriptions using an LLM.

**Applies to Media Type**:
- Video

**Use Cases**:
- Clip live or VOD news content

**Dependencies**:
- None

**ML Model dependencies**:
- None

**Other plugin dependencies**:
- DetectActivePresenter

**Parameter inputs**:
- min_segment_length >> 15 seconds for example

**Output attributes**:
- Label
- Desc >> used for the labeler plugin
- Summary
- Celebrities

**IAM permissions (least privilege)**:
- None
