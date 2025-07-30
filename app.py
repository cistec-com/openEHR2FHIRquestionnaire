#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import gradio as gr
import tempfile
import argparse
from datetime import datetime
from webtemplate_to_fhir_questionnaire_json import convert_webtemplate_to_fhir_questionnaire_json
from fill_composition_from_response import process_questionnaire_bundle
import pycountry

def extract_languages_from_template(file_obj):
    if file_obj is None:
        return gr.CheckboxGroup(choices=[], value=[])
    try:
        with open(file_obj.name, "r", encoding="utf-8") as f:
            template = json.load(f)
        print("Extracting languages from:", file_obj.name)
        langs = template.get("languages", [])
        default = template.get("defaultLanguage", None)
        default_value = [default] if default in langs else []
        print("language 1:", langs[0])
        print("Default language:", default)

        #return langs, default_value
        return gr.CheckboxGroup(choices=langs, value=default_value)
    except Exception as e:
        return gr.CheckboxGroup(choices=[], value=[])

def convert_openehr_to_fhir(
    webtemplate_file,
    languages=["en"],
    fhir_version="R4",
    name=None,
    publisher=None,
    description=None
):
    """
    Process the uploaded openEHR web template and return the converted FHIR Questionnaire(s)
    """
    if webtemplate_file is None:
        return "Please upload a webtemplate JSON file.", []

    # Create a temporary directory for output files
    temp_dir = tempfile.mkdtemp()

    # Split languages
    #langs = [lang.strip() for lang in languages.split(",")]
    langs = languages

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
                description=description
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
        # Use HTML <details> tags to create collapsible sections
        # The <summary> becomes the section title
        details_block = (
            f"<details>"
            f"<summary><strong>FHIR Questionnaire ({lang})</strong></summary>\n\n"
            f"```json\n{content}\n```"
            f"\n</details>"
        )
        results.append(details_block)

    # Join all collapsible sections together
    combined_result = "\n\n".join(results)
    return combined_result, download_files

def load_sample():
    """Load a sample openEHR web template for demonstration"""
    sample_path = os.path.join(os.path.dirname(__file__), "samples", "sample_webtemplate.json")
    if os.path.exists(sample_path):
        return sample_path
    else:
        return None
    
def convert_questionnaire_to_openehr_composition(fhir_file, ctx_setting, ctx_territory):
    if fhir_file is None:
        return "Please upload a FHIR QuestionnaireResponse or Bundle JSON file.", []

    try:
        with open(fhir_file.name, "r", encoding="utf-8") as f:
            fhir_json = json.load(f)

        compositions = process_questionnaire_bundle(fhir_json, ctx_setting=ctx_setting, ctx_territory=ctx_territory)

        output_text = ""
        download_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        base_name = os.path.splitext(os.path.basename(fhir_file.name))[0]
        temp_dir = tempfile.mkdtemp()

        for i, comp in enumerate(compositions):
            comp_json = json.dumps(comp["composition"], indent=2)
            filename = f"{timestamp}-{base_name}-{i+1}.json"
            filepath = os.path.join(temp_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(comp_json)

            download_files.append(filepath)

            output_text += (
                f"<details><summary><strong>{comp['questionnaire']}</strong></summary>\n\n"
                f"```json\n{comp_json}\n```"
                f"\n</details>\n\n"
            )

        return output_text, download_files
    except Exception as e:
        return f"Error: {str(e)}", []

def create_gradio_interface():
    """Create and return the Gradio interface"""
    iso_territories = sorted(
        [(f"{country.name} ({country.alpha_2})", country.alpha_2)
        for country in pycountry.countries],
        key=lambda x: x[0]
    )
    with gr.Blocks(title="FHIRquestionEHR") as demo:
        gr.Markdown("""
    🔗 This tool is open-source. View implementation details, contribute or open issues on the [GitHub Repository](https://github.com/cistec-com/openEHR2FHIRquestionnaire)
        """)
        with gr.Tabs():
            with gr.TabItem("openEHR to FHIR Questionnaire Converter"):
                gr.Markdown("# openEHR to FHIR Questionnaire Converter")
                gr.Markdown("""
                This tool converts openEHR web templates (JSON) to FHIR Questionnaires.
                Upload your web template and configure the conversion parameters below.
                """)

                with gr.Row():
                    with gr.Column():
                        webtemplate_file = gr.File(label="Upload openEHR Web Template (JSON)")

                        with gr.Row():
                            #languages = gr.Textbox(label="Languages (comma-separated)", value="en", info="Example: en,de,fr")
                            language_selector = gr.CheckboxGroup(
                                label="Select languages",
                                choices=["en"],
                                value=["en"],
                                interactive=True,
                                info="One questionnaire will be generated for each language."
                            )

                            fhir_version = gr.Radio(choices=["R4", "R5"], label="FHIR Version", value="R4")

                        with gr.Row():
                            name = gr.Textbox(label="Name (optional)", info="Name for this questionnaire (computer friendly)")
                            publisher = gr.Textbox(label="Publisher (optional)", info="The 'publisher' attribute for the FHIR Questionnaire")

                        # TODO: add more fields, implement in app & script
                        with gr.Row():
                            #status = gr.Radio(choices=["draft", "active", "retired", "unknown"], label="Status of the Questionnaire", value="draft", info="The 'status' attribute for the FHIR Questionnaire")
                            #title = gr.Textbox(label="Title (optional)", info="Name for this questionnaire (human friendly)")
                            description = gr.Textbox(label="Description (optional)", info="Natural language description of the questionnaire (markdown)")

                        with gr.Row():
                            load_sample_btn = gr.Button("Load Sample")
                            convert_btn = gr.Button("Convert to FHIR", variant="primary")

                    with gr.Column():
                        download_files = gr.File(label="Download FHIR Questionnaires", file_count="multiple", type="binary")
                        
                        with gr.Accordion("Conversion Result", open=True):
                            output = gr.Markdown()

                convert_btn.click(
                    fn=convert_openehr_to_fhir,
                    inputs=[webtemplate_file, language_selector, fhir_version, name, publisher, description],
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

                webtemplate_file.upload(
                    fn=extract_languages_from_template,
                    inputs=webtemplate_file,
                    outputs=[language_selector]
                )

            with gr.TabItem("FHIR QuestionnaireResponse to openEHR FLAT Composition Converter"):
                gr.Markdown("# FHIR QuestionnaireResponse to openEHR FLAT Composition Converter")
                gr.Markdown("""
                This tool converts FHIR QuestionnaireResponses to openEHR FLAT Compositions.
                Upload your FHIR QuestionnaireResponse and configure the conversion parameters below.
                The questionnaireResponse needs to be derived from a FHIR Questionnaire generated from an openEHR web template.            
                """)

                with gr.Row():
                    with gr.Column():
                        fhir_input_file = gr.File(label="Upload FHIR QuestionnaireResponse or Bundle (JSON)")

                        care_setting = gr.Dropdown(
                            label="Care Setting",
                            choices=[
                                ("225 - home", "225"),
                                ("227 - emergency care", "227"),
                                ("228 - primary medical care", "228"),
                                ("229 - primary nursing care", "229"),
                                ("230 - primary allied health care", "230"),
                                ("231 - midwifery care", "231"),
                                ("232 - secondary medical care", "232"),
                                ("233 - secondary nursing care", "233"),
                                ("234 - secondary allied health care", "234"),
                                ("235 - complementary health care", "235"),
                                ("236 - dental care", "236"),
                                ("237 - nursing home care", "237"),
                                ("802 - mental healthcare", "802"),
                                ("238 - other care", "238"),
                            ],
                            value="238",
                            interactive=True,
                            info="Context setting for the composition (ctx/setting)"
                        )

                        territory = gr.Dropdown(
                            label="Territory (ISO 3166-1)",
                            choices=iso_territories,
                            value="US",
                            interactive=True,
                            info="Mandatory for a valid composition (ctx/territory)"
                        )

                        convert_qr_btn = gr.Button("Convert to openEHR", variant="primary")

                    with gr.Column():
                        download_comps = gr.File(
                            label="Download openEHR Compositions",
                            file_count="multiple",
                            type="binary"
                        )

                        with gr.Accordion("Generated Compositions", open=True):
                            comp_output = gr.Markdown()

                convert_qr_btn.click(
                    fn=convert_questionnaire_to_openehr_composition,
                    inputs=[fhir_input_file, care_setting, territory],
                    outputs=[comp_output, download_comps]
                )

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
