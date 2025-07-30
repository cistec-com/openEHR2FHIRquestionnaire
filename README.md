---
title: openEHR to FHIR Questionnaire Converter
emoji: 📋
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.1
app_file: app_hf.py
pinned: false
license: mit
---

# openEHR2FHIRquestionnaire

This project provides two tools for working with openEHR and FHIR resources:

1. **openEHR Web Template → FHIR Questionnaire converter**
2. **FHIR QuestionnaireResponse → openEHR FLAT Composition converter**

You can use both tools via the CLI or an interactive web interface.

[Try the converter in the Web Interface](https://huggingface.co/spaces/cistec/openEHR2FHIRquestionnaire)

## Table of Contents

* [Overview](#overview)
* [Requirements](#requirements)
* [Usage](#usage)
  + [Command Line Interface](#command-line-interface)
  + [Web Interface (Gradio)](#web-interface-gradio)
  + [Examples](#examples)
  + [Parameters](#parameters)
* [Data Type Mapping](#data-type-mapping)
* [License](#license)
* [Contribution](#contribution)
* [Citation](#citation)

## Overview

### 1. openEHR → FHIR Questionnaire

Converts an **openEHR web template (JSON)** to one or more **FHIR Questionnaire** resources.  
Features:
- Multi-language output (based on available template translations)
- Support for FHIR R4 and R5
- Customizable name, publisher, and description fields

---

### 2. FHIR QuestionnaireResponse → openEHR Composition

Converts a **FHIR QuestionnaireResponse** (or a Bundle of them) into one or more **openEHR FLAT Compositions**.  
Features:
- Creates valid openEHR FLAT compositions from QuestionnaireResponse
- QuestionnaireResponse needs to be derived from a FHIR Questionnaire generated through openEHR → FHIR Questionnaire script

---

### Requirements CLI

* Python 3.7+ (the core conversion script has no external dependencies)

### Web Interface (Gradio)

* Python 3.10+ (required by Gradio)
* Dependencies are managed through pyproject.toml

We've added a web interface using Gradio. To run it locally:

1. Install uv if you don't have it:

[UV Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)

2. Create a virtual environment and run the app:

```bash
uv venv --python 3.10
source .venv/bin/activate
uv run app.py
```

3. Open your browser at http://localhost:7860

You can also try the hosted version of this tool on Hugging Face Spaces: [openEHR2FHIR Questionnaire Converter](https://huggingface.co/spaces/cistec/openEHR2FHIRquestionnaire)

## Web Template to FHIR questionnaire

### Command Line Interface

```bash
python webtemplate_to_fhir_questionnaire_json.py \
    --input <path_to_webtemplate_json> \
    --output <base_output_file_name> \
    --output_folder <relative_output_folder_path> \
    --languages <comma_separated_langs> \
    --fhir_version <R4|R5> \
    --name <Optional name attribute for the FHIR Questionnaire> \
    --publisher <Optional publisher attribute for the FHIR Questionnaire>
    --description <Natural language description of the questionnaire>
    --create_help_buttons <True/False>
```

Note: Since the CLI script has no external dependencies, it can be run directly with Python without requiring uv.


### Examples

```bash
# Full example with all parameters
python webtemplate_to_fhir_questionnaire_json.py \
    --input path_to_folder/web_template.json \
    --output questionnaire \
    --output_folder output_folder_path \
    --languages en,de \
    --fhir_version R4 \
    --name QuestionnaireName \
    --publisher QuestionnairePublisher \
    --description Questionnaire description \
    --create_help_buttons False
```

```bash
# Simple example with just input file
python webtemplate_to_fhir_questionnaire_json.py --input web_template.json
```

```bash
# Test with sample web template included in the repository
python webtemplate_to_fhir_questionnaire_json.py --input samples/sample_webtemplate.json
```

### Parameters

| Parameters      | Description                                                                   | Required? | Default                            | Comments                                                                                                                                                  |
| --------------- | ----------------------------------------------------------------------------- | --------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| --input         | Path to the Web Template JSON file to be converted into a FHIR Questionnaire. | Yes       | None                               |                                                                                                                                                           |
| --output        | Base output file name for the generated FHIR Questionnaire.                   | No        | Input file base name.              | A timestamp (%Y%m%d\_%H%M) is prepended and the language code appended to the base name.                                                                  |
| --output_folder | Path to the Web Template JSON file to be converted into a FHIR Questionnaire. | No        | `.` (current folder)               |                                                                                                                                                           |
| --languages     | Comma-separated list of language codes (e.g., `en,de` )..                      | No        | `en` | A separate questionnaire is generated for each language.                                                                                                  |
| --fhir_version  | FHIR version to use (either `R4` or `R5` ).                                    | No        | `R4` |                                                                                                                                                           |
| --name          | The `name` attribute for the FHIR Questionnaire.                              | No        | Web Template name (without spaces) |                                                                                                                                                           |
| --publisher     | The `publisher` attribute for the FHIR Questionnaire.                         | No        | `converter` |                                                                                                                                                           |
| --description    | Natural language description of the questionnaire (markdown)                 | No        | Root Archetype description                               |                                      |
| --create_help_buttons    | Create help text for each questionnaire item.                        | No        | True                              | Disable with ``False`                                     |


## FHIR questionnaireResponse to FLAT Composition

The input can be either a single questionnaireResponse or a collection of responses in a bundle. They have to originate from a questionnaire created through the converter, as the linkIds assigned to the elements in the questionnaire correspond to the path structure used in FLAT compositions.
The generated FLAT Composition can be posted to both EHRbase and Better.

### Command Line Interface

```bash
python fill_composition_from_response.py \
    --input <path_to_questionnaireResponse/bundle> \
    --output <base_output_file_name> \
    --output_folder <relative_output_folder_path> \
    --care_setting <openehr_care_setting> \
    --territory <territory_code>
```

| Parameters      | Description                                                                   | Required? | Default                            | Comments                                                                                                                                                  |
| --------------- | ----------------------------------------------------------------------------- | --------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| --input         | Path to the Web Template JSON file to be converted into a FHIR Questionnaire. | Yes       | None                               |                                                                                                                                                           |
| --output        | Base output file name for the generated FHIR Questionnaire.                   | No        | Input file base name.              | A timestamp (%Y%m%d\_%H%M) is prepended and the language code appended to the base name.                                                                  |
| --output_folder | Path to the Web Template JSON file to be converted into a FHIR Questionnaire. | No        | `.` (current folder)               |                                                                                                                                                           |
| --care_setting  | Care setting for the openEHR composition, 3-digit code or description         | No        | 228 / other care  | [openEHR Support Terminology - Setting](https://specifications.openehr.org/releases/TERM/latest/SupportTerminology.html#_setting)                                                                                                                                                          |
| --territory     | 2-character code according to ISO 3166-1                                      | No        | Inferred using `locale.getdefaultlocale()` |                                                                                                                                                           |


## Data Type Mapping

| openEHR RM Type                            | FHIR Questionnaire Type   | Notes |
|--------------------------------------------|---------------------------|-------|
| `COMPOSITION`, `CLUSTER`, `SECTION`, `EVENT_CONTEXT` | `group`                   | Used for hierarchical structuring. |
| `DV_CODED_TEXT`                            | `choice` / `open-choice` (R4) or `coding` / `question` (R5) | Depends on `fhir_version` and whether the list is open. |
| `DV_TEXT`                                  | `text` / `string`          | If `text_types="from_annotations"`, annotations are used for distinction. Defaults to using `text`. |
| `DV_QUANTITY`                              | `quantity`                 |  |
| `DV_DATE_TIME`                             | `dateTime`                 |  |
| `DV_DATE`                                  | `date`                     |  |
| `DV_TIME`, `DV_DURATION`                   | `time`                     |  |
| `DV_COUNT`                                 | `integer`                  |  |
| `DV_BOOLEAN`                               | `boolean`                  |  |
| `DV_MULTIMEDIA`                            | `attachment`               |  |
| `DV_URI`, `DV_EHR_URI`                     | `reference`                |  |
| *Other types*                              | `text`                     | Default fallback for unmapped types. |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contribution

Contributions are welcome! Please feel free to submit a Pull Request. See the [CONTRIBUTING.md](CONTRIBUTING.md) file for details.

## Citation

```bibtex
@software{OpenEHR2FHIRQuestionnaire,
  author = {Cistec AG},
  title = {openEHR to FHIR Questionnaire Mapper},
  year = {2025},
  url = {https://github.com/cistec-com/openEHR2FHIRquestionnaire}
}
```
