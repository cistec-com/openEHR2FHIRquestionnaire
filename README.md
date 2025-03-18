# openEHR2FHIRquestionnaire

This script converts an openEHR web template (JSON) to one or more FHIR Questionnaire resources (JSON).
You can generate multiple language variants, in case the respective translation is included in the web template. The FHIR version can be selected (currently supports R4 and R5).

## Table of Contents

- [Requirements](#requirements)
- [Usage](#usage)
  - [Command Line Interface](#command-line-interface)
  - [Web Interface (Gradio)](#web-interface-gradio)
  - [Docker Container](#docker-container)
- [Local Development and Testing](#local-development-and-testing)
- [Examples](#examples)
- [Parameters](#parameters)
- [License](#license)
- [Contribution](#contribution)
- [Citation](#citation)

## Requirements

- Python 3.7+
- No special external libraries are required for the CLI version.
- For the web interface: see `requirements.txt`

## Usage

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
    --text_types <from_annotations|...>
```

### Web Interface (Gradio)

We've added a web interface using Gradio. To run it locally:

1. Install the required dependencies using uv (recommended):

   ```bash
   # Install uv if you don't have it
   pip install uv

   # Install dependencies
   uv pip install -r requirements.txt
   ```

   Alternatively, you can use pip:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the Gradio app:

   ```bash
   python app.py
   ```

3. Open your browser at http://localhost:7860

You can also try the hosted version of this tool on Hugging Face Spaces: [openEHR2FHIR Questionnaire Converter](https://huggingface.co/spaces/cistec/openEHR2FHIRquestionnaire)

### Docker Container

You can also run the web interface using Docker:

```bash
# Build the Docker image
docker build -t openehr2fhir .

# Run the container
docker run -p 7860:7860 openehr2fhir
```

Then open your browser at http://localhost:7860

## Local Development and Testing

For local development and testing, follow these steps:

1. Clone the repository:

   ```bash
   git clone https://github.com/cistec/openEHR2FHIRquestionnaire.git
   cd openEHR2FHIRquestionnaire
   ```

2. Create and activate a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. Install dependencies using uv:

   ```bash
   pip install uv
   uv pip install -r requirements.txt
   ```

4. Run the Gradio app with debug mode enabled:

   ```bash
   python app.py
   ```

   The app will automatically reload when you make changes to the code.

5. Test the command-line interface:

   ```bash
   python webtemplate_to_fhir_questionnaire_json.py --input samples/sample_webtemplate.json
   ```

6. To test with your own web templates, place them in any directory and use the full path:
   ```bash
   python webtemplate_to_fhir_questionnaire_json.py --input /path/to/your/webtemplate.json
   ```

### Examples

```bash
python ./webtemplate_to_fhir_questionnaire_json.py \
    --input path_to_folder/web_template.json \
    --output questionnaire \
    --output_folder output_folder_path \
    --languages en,de \
    --fhir_version R4 \
    --name QuestionnaireName \
    --publisher QuestionnairePublisher \
    --text_types from_annotations
```

```bash
python ./webtemplate_to_fhir_questionnaire_json.py --input web_template.json
```

### Parameters

| Parameters      | Description                                                                   | Required? | Default                            | Comments                                                                                        |
| --------------- | ----------------------------------------------------------------------------- | --------- | ---------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| --input         | Path to the Web Template JSON file to be converted into a FHIR Questionnaire. | Yes       | None                               |                                                                                                 |
| --output        | Base output file name for the generated FHIR Questionnaire.                   | No        | Input file base name.              | A timestamp (%Y%m%d\_%H%M) is prepended and the language code appended to the base name.        |
| --output_folder | Path to the Web Template JSON file to be converted into a FHIR Questionnaire. | No        | `.` (current folder)               |                                                                                                 |
| --languages     | Comma-separated list of language codes (e.g., `en,de`)..                      | No        | `en`                               | A separate questionnaire is generated for each language.                                        |
| --fhir_version  | FHIR version to use (either `R4` or `R5`).                                    | No        | `R4`                               |                                                                                                 |
| --name          | The `name` attribute for the FHIR Questionnaire.                              | No        | Web Template name (without spaces) |                                                                                                 |
| --publisher     | The `publisher` attribute for the FHIR Questionnaire.                         | No        | `converter`                        |                                                                                                 |
| --text_types    | Distinction of `DV_TEXT` mapping to `text` and `string` FHIR types.           | No        | None                               | `from_annotations`: Annotated items in the Web Template with `key=text_type` and `value=<string | text>` are converted to the respective FHIR item type. |

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
