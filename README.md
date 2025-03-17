# openEHR2FHIRquestionnaire

This script converts an openEHR web template (JSON) to one or more FHIR Questionnaire resources (JSON).  
You can generate multiple language variants as needed and select the FHIR version (R4 or R5).

## Requirements

- Python 3.7+
- No special external libraries are required.

## Usage

```bash
python webtemplate_to_fhir_questionnaire_json.py \
    --input <path_to_webtemplate_json> \
    --output <base_output_file_name> \
    --output_folder <relative_output_folder_path> \
    --languages <comma_separated_langs> \
<<<<<<< HEAD
    --fhir_version <R4|R5> \
    --name <Optional name attribute for the FHIR Questionnaire> \
    --publisher <Optional publisher attribute for the FHIR Questionnaire>
=======
    --fhir_version <R4|R5>
```
>>>>>>> f3c2ab53ab1c747b76b5c0daec1c20e3bc2abadf

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contribution

Contributions are welcome! Please feel free to submit a Pull Request. See the CONTRIBUTING.md file for details.

## Citation
Cistec AG. (2025). openEHR to FHIR Questionnaire Mapper [Computer software]. 
https://github.com/cistec-com/openEHR2FHIRquestionnaire
