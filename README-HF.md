# openEHR to FHIR Questionnaire Converter

This tool allows you to convert openEHR web templates (JSON) to FHIR Questionnaire resources.

## Features

- Convert openEHR web templates to FHIR Questionnaires
- Support for multiple languages (en, de, fr, etc.)
- Support for both FHIR R4 and R5 versions
- Download converted FHIR Questionnaires as JSON files
- Sample template available for testing

## How to use

1. Upload your openEHR web template (JSON file)
2. Configure the conversion parameters:
   - Languages (comma-separated)
   - FHIR version (R4 or R5)
   - Optional name and publisher attributes
   - Text type handling
3. Click "Convert to FHIR"
4. View the resulting FHIR Questionnaire(s) and download them

If you don't have a template to test with, click "Load Sample" to use a demonstration template.

## Background

The openEHR framework is a comprehensive approach to electronic health records that emphasizes interoperability and semantic precision. FHIR (Fast Healthcare Interoperability Resources) is a modern standard for healthcare data exchange.

This tool bridges the gap between these standards by converting openEHR templates to FHIR Questionnaires, enabling organizations using openEHR to integrate with FHIR-based systems.

## Source code

The source code for this tool is available on GitHub: [cistec/openEHR2FHIRquestionnaire](https://github.com/cistec/openEHR2FHIRquestionnaire)

## License

This project is licensed under the MIT License.
