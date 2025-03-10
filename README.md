# openEHR2FHIRquestionnaire

This script converts an openEHR web template (.json) to one or more FHIR Questionnaire resources (JSON).  
You can generate multiple language variants as needed and select the FHIR version (R4 or R5).

## Requirements

- Python 3.7+
- No special external libraries are required.

## Usage

```bash
python webtemplate_to_fhir_questionnaire_json.py \
    --input <path_to_webtemplate_json> \
    --output <base_output_name> \
    --languages <comma_separated_langs> \
    --fhir_version <R4|R5>