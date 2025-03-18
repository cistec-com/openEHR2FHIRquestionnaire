#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import gradio as gr
import tempfile
import argparse
from datetime import datetime
from webtemplate_to_fhir_questionnaire_json import convert_webtemplate_to_fhir_questionnaire_json

def convert_openehr_to_fhir(
    webtemplate_file,
    languages="en",
    fhir_version="R4",
    name=None,
    publisher=None,
    text_types=None
):
    """
    Process the uploaded openEHR web template and return the converted FHIR Questionnaire(s)
    """
    if webtemplate_file is None:
        return "Please upload a webtemplate JSON file.", []

    # Create a temporary directory for output files
    temp_dir = tempfile.mkdtemp()

    # Split languages
    langs = [lang.strip() for lang in languages.split(",")]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base_name = os.path.splitext(os.path.basename(webtemplate_file.name))[0]

    # Dictionary to store output files
    output_files = {}
    output_content = {}
    download_files = []

    # Process each language
    for lang in langs:
        out_file = os.path.join(temp_dir, f"{timestamp}-{base_name}-{lang}.json")

        try:
            convert_webtemplate_to_fhir_questionnaire_json(
                input_file_path=webtemplate_file.name,
                output_file_path=out_file,
                preferred_lang=lang,
                fhir_version=fhir_version,
                name=name,
                publisher=publisher,
                text_types=text_types
            )

            # Read the generated file
            with open(out_file, "r", encoding="utf-8") as f:
                fhir_json = json.load(f)
                output_content[lang] = json.dumps(fhir_json, indent=2)

            output_files[lang] = out_file
            download_files.append(out_file)
        except Exception as e:
            return f"Error processing {lang}: {str(e)}", []

    # Combine results into a formatted string
    results = []

    for lang, content in output_content.items():
        results.append(f"## FHIR Questionnaire ({lang}):\n```json\n{content}\n```")

    return "\n\n".join(results), download_files

def load_sample():
    """Load a sample openEHR web template for demonstration"""
    sample_path = os.path.join(os.path.dirname(__file__), "samples", "sample_webtemplate.json")
    if os.path.exists(sample_path):
        return sample_path
    else:
        return None

def create_gradio_interface():
    """Create and return the Gradio interface"""
    with gr.Blocks(title="openEHR to FHIR Questionnaire Converter") as demo:
        gr.Markdown("# openEHR to FHIR Questionnaire Converter")
        gr.Markdown("""
        This tool converts openEHR web templates (JSON) to FHIR Questionnaire resources.
        Upload your web template and configure the conversion parameters below.
        """)

        with gr.Row():
            with gr.Column():
                webtemplate_file = gr.File(label="Upload openEHR Web Template (JSON)")

                with gr.Row():
                    languages = gr.Textbox(label="Languages (comma-separated)", value="en", info="Example: en,de,fr")
                    fhir_version = gr.Radio(["R4", "R5"], label="FHIR Version", value="R4")

                with gr.Row():
                    name = gr.Textbox(label="Name (optional)", info="The 'name' attribute for the FHIR Questionnaire")
                    publisher = gr.Textbox(label="Publisher (optional)", info="The 'publisher' attribute for the FHIR Questionnaire")

                text_types = gr.Dropdown(["from_annotations", None], label="Text Type Handling", value=None)

                with gr.Row():
                    load_sample_btn = gr.Button("Load Sample")
                    convert_btn = gr.Button("Convert to FHIR", variant="primary")

            with gr.Column():
                output = gr.Markdown(label="Conversion Result")
                download_files = gr.File(label="Download FHIR Questionnaires", file_count="multiple", type="file")

        convert_btn.click(
            fn=convert_openehr_to_fhir,
            inputs=[webtemplate_file, languages, fhir_version, name, publisher, text_types],
            outputs=[output, download_files]
        )

        if os.path.exists(os.path.join(os.path.dirname(__file__), "samples")):
            load_sample_btn.click(
                fn=load_sample,
                inputs=None,
                outputs=webtemplate_file
            )
        else:
            load_sample_btn.visible = False

    return demo

# Create directories for samples if they don't exist
def ensure_sample_dir():
    sample_dir = os.path.join(os.path.dirname(__file__), "samples")
    if not os.path.exists(sample_dir):
        os.makedirs(sample_dir)

        # Create a simple sample web template
        sample_template = {
            "templateId": "sample_template",
            "tree": {
                "id": "sample_root",
                "name": "Sample Web Template",
                "localizedNames": {
                    "en": "Sample Web Template",
                    "de": "Beispiel Web-Vorlage"
                },
                "localizedDescriptions": {
                    "en": "This is a sample web template for demonstration purposes",
                    "de": "Dies ist eine Beispiel-Web-Vorlage zu Demonstrationszwecken"
                },
                "nodeId": "sample_node_id",
                "children": [
                    {
                        "id": "sample_section",
                        "name": "Sample Section",
                        "localizedNames": {
                            "en": "Sample Section",
                            "de": "Beispielabschnitt"
                        },
                        "rmType": "SECTION",
                        "nodeId": "sample_section_id",
                        "aqlPath": "/content[openEHR-EHR-SECTION.sample_section.v1]",
                        "children": [
                            {
                                "id": "sample_element",
                                "name": "Sample Element",
                                "localizedNames": {
                                    "en": "Sample Element",
                                    "de": "Beispielelement"
                                },
                                "rmType": "DV_CODED_TEXT",
                                "nodeId": "sample_element_id",
                                "aqlPath": "/content[openEHR-EHR-SECTION.sample_section.v1]/items[openEHR-EHR-ELEMENT.sample_element.v1]/value",
                                "inputs": [
                                    {
                                        "type": "CODED_TEXT",
                                        "list": [
                                            {
                                                "value": "option1",
                                                "label": {
                                                    "en": "Option 1",
                                                    "de": "Option 1"
                                                }
                                            },
                                            {
                                                "value": "option2",
                                                "label": {
                                                    "en": "Option 2",
                                                    "de": "Option 2"
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        with open(os.path.join(sample_dir, "sample_webtemplate.json"), "w", encoding="utf-8") as f:
            json.dump(sample_template, f, indent=2)

# Launch the app if run directly
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the openEHR to FHIR Questionnaire Converter web interface')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--share', action='store_true', help='Create a public link for sharing')
    parser.add_argument('--port', type=int, default=7860, help='Port to run the app on')
    args = parser.parse_args()

    # Create sample directory and file when app starts
    ensure_sample_dir()

    # Create and launch the Gradio interface
    demo = create_gradio_interface()
    demo.launch(
        debug=args.debug,
        share=args.share,
        server_port=args.port
    )
