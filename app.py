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
    template = None
    try:
        if file_obj is not None:
            with open(file_obj.name, "r", encoding="utf-8") as f:
                template = json.load(f)
        
        if template:
            langs = template.get("languages", [])
            default = template.get("defaultLanguage", None)
            default_value = [default] if default in langs else []
            return gr.CheckboxGroup(choices=langs, value=default_value)
    except Exception:
        pass
    return gr.CheckboxGroup(choices=[], value=[])

def convert_openehr_to_fhir(
    webtemplate_file,
    languages=["en"],
    fhir_version="R4",
    name=None,
    publisher=None,
    description=None,
    create_help_buttons=False
):
    if webtemplate_file is None:
        return "Please upload an openEHR Web Template file.", [], gr.update(visible=False), None

    input_path = webtemplate_file.name
    temp_dir = tempfile.mkdtemp()
    langs = languages
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    download_files = []
    output_content_map = {} 

    for lang in langs:
        out_file = os.path.join(temp_dir, f"{timestamp}-{base_name}-{lang}.json")
        try:
            convert_webtemplate_to_fhir_questionnaire_json(
                input_file_path=input_path,
                output_file_path=out_file,
                preferred_lang=lang,
                fhir_version=fhir_version,
                name=name,
                publisher=publisher,
                description=description,
                create_help_buttons=create_help_buttons
            )
            with open(out_file, "r", encoding="utf-8") as f:
                fhir_json = json.load(f)
                output_content_map[f"{lang} Questionnaire"] = fhir_json
            download_files.append(out_file)
        except Exception as e:
            return f"Error processing {lang}: {str(e)}", [], gr.update(visible=False)

    first_key = list(output_content_map.keys())[0] if output_content_map else None
    
    return (
        "Conversion successful!", 
        download_files, 
        gr.update(choices=download_files, value=download_files[0] if download_files else None, visible=True)
    )

def update_preview(selected_file_path):
    if not selected_file_path:
        return ""
    try:
        with open(selected_file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            return json.dumps(content, indent=2)
    except Exception:
        return {"error": "Could not read file"}

def load_sample():
    """Load a sample openEHR web template for demonstration"""
    sample_path = os.path.join(os.path.dirname(__file__), "samples", "sample_webtemplate.json")
    if os.path.exists(sample_path):
        return sample_path
    else:
        return None
    
def convert_questionnaire_to_openehr_composition(fhir_file, fhir_text, ctx_setting, ctx_territory):
    fhir_json = None
    try:
        # 1. Handle Input Source
        if fhir_file is not None:
            with open(fhir_file.name, "r", encoding="utf-8") as f:
                fhir_json = json.load(f)
            base_filename = os.path.splitext(os.path.basename(fhir_file.name))[0]
        elif fhir_text and fhir_text.strip():
            fhir_json = json.loads(fhir_text)
            base_filename = "pasted_response"
        else:
            return "Please upload or paste a FHIR QuestionnaireResponse.", []

        # 2. Process
        compositions = process_questionnaire_bundle(fhir_json, ctx_setting=ctx_setting, ctx_territory=ctx_territory)

        output_text = ""
        download_files = []
        temp_dir = tempfile.mkdtemp()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        for i, comp in enumerate(compositions):
            comp_json_str = json.dumps(comp["composition"], indent=2)
            filepath = os.path.join(temp_dir, f"{timestamp}-{base_filename}-{i+1}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(comp_json_str)
            download_files.append(filepath)
            
            output_text += f"<details><summary><strong>{comp['questionnaire']}</strong></summary>\n\n```json\n{comp_json_str}\n```\n</details>\n\n"

        return output_text, download_files
    except Exception as e:
        return f"Error: {str(e)}", []

def create_gradio_interface():
    iso_territories = sorted(
        [(f"{country.name} ({country.alpha_2})", country.alpha_2)
        for country in pycountry.countries],
        key=lambda x: x[0]
    )
    with gr.Blocks(title="FHIRquestionEHR") as demo:
        #results_store = gr.State(None)
        gr.Markdown("""🔗 This tool is open-source. View implementation details, contribute or open issues on the [GitHub Repository](https://github.com/cistec-com/openEHR2FHIRquestionnaire)""")
        
        with gr.Tabs():
            with gr.TabItem("openEHR to FHIR Questionnaire Converter"):
                gr.Markdown("# openEHR to FHIR Questionnaire Converter")
                
                with gr.Row():
                    with gr.Column():
                        # --- UPDATED: Reverted to single File component ---
                        webtemplate_file = gr.File(label="Upload openEHR Web Template (JSON)")
                        
                        with gr.Row():
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

                        with gr.Row():
                            help_box = gr.Checkbox(label="Create help buttons", info="Creates a help button extension for each question using the node descriptions", value=False)

                        with gr.Row():
                            description = gr.Textbox(label="Description (optional)", info="Natural language description of the questionnaire (markdown)")

                        with gr.Row():
                            load_sample_btn = gr.Button("Load Sample")
                            convert_btn = gr.Button("Convert to FHIR", variant="primary")

                    with gr.Column():
                        download_files = gr.File(label="Download FHIR Questionnaires", file_count="multiple", type="binary")
                        file_selector = gr.Dropdown(label="Preview Generated File", choices=[], visible=False)
                        json_preview = gr.Code(label="JSON Preview", language="json")
                        output_msg = gr.Markdown()

                # --- Event Listeners Updated ---
                webtemplate_file.upload(fn=extract_languages_from_template, inputs=[webtemplate_file], outputs=[language_selector])

                convert_btn.click(
                    fn=convert_openehr_to_fhir,
                    inputs=[webtemplate_file, language_selector, fhir_version, name, publisher, description, help_box],
                    outputs=[output_msg, download_files, file_selector]
                )

                file_selector.change(
                    fn=update_preview,
                     inputs=[file_selector],
                     outputs=json_preview
                )

                load_sample_btn.click(fn=load_sample, outputs=webtemplate_file)

            with gr.TabItem("FHIR QuestionnaireResponse to openEHR FLAT Composition Converter"):
                gr.Markdown("# FHIR QuestionnaireResponse to openEHR FLAT Composition Converter")
                gr.Markdown("""
                This tool converts FHIR QuestionnaireResponses to openEHR FLAT Compositions.
                Upload your FHIR QuestionnaireResponse and configure the conversion parameters below.
                The questionnaireResponse needs to be derived from a FHIR Questionnaire generated from an openEHR web template.            
                """)

                with gr.Row():
                    with gr.Column():
                        with gr.Tabs():
                            with gr.TabItem("Upload Response or Bundle"):
                                fhir_input_file = gr.File(label="Upload FHIR QuestionnaireResponse or Bundle (JSON)")
                            with gr.TabItem("Paste Response or Bundle"):
                                fhir_input_text = gr.Textbox(label="Paste FHIR QuestionnaireResponse or Bundle (JSON)", lines=10)

                        #template_id = gr.Textbox(label="Template ID", info="openEHR Template ID. Needs to be specified if questionnaire is not posted on a server and has the correct URL assigned.")

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
                    inputs=[fhir_input_file, fhir_input_text, care_setting, territory],
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
        server_port=args.port,
        show_api=False
    )
