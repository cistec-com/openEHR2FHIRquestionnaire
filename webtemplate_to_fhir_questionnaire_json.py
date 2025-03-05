#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from typing import Dict, Any, List, Optional

def convert_webtemplate_to_fhir_questionnaire_json(
    input_file_path: str,
    output_file_path: str,
    preferred_lang: str = "en"
):
    """
    Loads an openEHR web template (JSON), converts it to a minimal FHIR Questionnaire (JSON)
    in the specified language (preferred_lang), and writes the result to disk.
    """
    # 1) Read the web template JSON
    with open(input_file_path, "r", encoding="utf-8") as f:
        web_template = json.load(f)

    template_id = web_template.get("templateId", "unknown-web-template")
    root_node = web_template["tree"]

    # Gather the "name" or localized name for the top-level
    # e.g. web_template["tree"]["localizedNames"] = {"en": "Body weight", "de": "Körpergewicht"}
    top_level_name = get_localized_name(root_node, preferred_lang)
    top_level_description = get_localized_description(root_node, preferred_lang)

    # 2) Build the FHIR Questionnaire in the selected language
    questionnaire = {
        "resourceType": "Questionnaire",
        "language": preferred_lang,  # Indicate resource language
        # TODO: fix url, as language gets put after version number, example: 
        # "questionnaire": "http://example.org/fhir/Questionnaire/cistec.openehr.body_weight.v1-en|1.0",

        "url": f"http://example.org/fhir/Questionnaire/{template_id}-{preferred_lang}",
        "identifier": [
            {
                "system": "http://example.org/fhir/identifiers",
                "value": template_id
            }
        ],
        "version": "1.0",
        "name": f"{template_id}-{preferred_lang}",
        "title": top_level_name or root_node.get("name", "Unnamed Template"),
        "status": "draft",
        "publisher": "JB",
        "date": "2025-02-28",
        "description": top_level_description or "Auto-generated from openEHR web template to FHIR Questionnaire",
        "item": []
    }

    # Create a top-level 'group' item
    composition_item = {
        "linkId": root_node.get("nodeId", "composition"),
        "text": top_level_name or root_node.get("name", "Composition"),
        "type": "group",
        "item": []
    }
    questionnaire["item"].append(composition_item)

    # 3) Recursively process children
    children = root_node.get("children", [])
    for child in children:
        child_item = process_webtemplate_node(child, preferred_lang)
        if child_item:
            composition_item["item"].append(child_item)

    # 4) Write output
    with open(output_file_path, "w", encoding="utf-8") as out:
        json.dump(questionnaire, out, indent=2, ensure_ascii=False)  # ensure_ascii=False helps keep UTF-8
    print(f"FHIR Questionnaire (JSON) for lang='{preferred_lang}' written to {output_file_path}")


def process_webtemplate_node(node: Dict[str, Any], preferred_lang: str) -> Optional[Dict[str, Any]]:
    """
    Converts one node from the web template into a FHIR Questionnaire 'item' dict,
    picking the localized text in the chosen language if possible.
    """
    # Exclude items if "inContext" == true
    if node.get("inContext") is True:
        # Possibly keep some exceptions if needed
        return None

    fhir_item = {}

    link_id = node.get("nodeId") or node.get("id") or "unknown"
    fhir_item["linkId"] = link_id

    # Evaluate min/max -> required, repeats
    min_occurs = node.get("min", 0)
    max_occurs = node.get("max", 1)
    fhir_item["required"] = (min_occurs >= 1)
    fhir_item["repeats"] = (max_occurs != 1)

    # Use localized names/descriptions for item text, if available
    item_text = get_localized_name(node, preferred_lang)
    if not item_text:
        item_text = node.get("name") or node.get("localizedName") or link_id
    fhir_item["text"] = item_text

    # Child items
    children = node.get("children", [])
    if children:
        fhir_item["type"] = "group"
        subitems = []
        for child in children:
            sub_item = process_webtemplate_node(child, preferred_lang)
            if sub_item:
                subitems.append(sub_item)
        if subitems:
            fhir_item["item"] = subitems
    else:
        rm_type = (node.get("rmType") or "").upper()
        if rm_type in ["DV_CODED_TEXT", "DV_TEXT"]:
            # read the "inputs" to see if there's a "listOpen" or "defaultValue"
            item_inputs = node.get("inputs", [])
            # We'll pick up "listOpen" from that
            list_open = find_list_open(item_inputs)  # see below
            # => set item.type to "open-choice" if true, else "choice"
            fhir_item["type"] = "open-choice" if list_open else "choice"

            # Check for defaultValue => set item.initial or add extension
            default_val = find_default_value(item_inputs)  # see below
            if default_val:
                answer_options = build_answer_options(node, preferred_lang, default_val)
            else:
                answer_options = build_answer_options(node, preferred_lang, None)

            if answer_options:
                fhir_item["answerOption"] = answer_options


        elif rm_type == "DV_QUANTITY":
            fhir_item["type"] = "quantity"
            build_quantity_with_unit_options(fhir_item, node)
        else:
            # other types: dateTime, string, etc.
            fhir_item["type"] = map_rmtype_to_fhir_type(rm_type)
        '''
        rm_type = (node.get("rmType") or "").upper()
        fhir_item["type"] = map_rmtype_to_fhir_type(rm_type)
        # TODO: "open-choice"
        #if fhir_item["type"] == "DV_CODED_TEXT" and node.get("inputs")

        # If coded text => try building answerOption, or referencing a ValueSet, etc.
        if fhir_item["type"] in ["choice", "open-choice"]:
            answer_options = build_answer_options(node, preferred_lang)
            if answer_options:
                fhir_item["answerOption"] = answer_options
        elif fhir_item["type"] == "quantity":
            build_quantity_with_unit_options(fhir_item, node)
        '''

    return fhir_item


def build_answer_options(node: Dict[str, Any], preferred_lang: str, default_value: None) -> List[Dict[str, Any]]:
    """
    Look for coded input lists in 'node["inputs"]' and produce FHIR answerOption entries,
    with text possibly in the chosen language.
    """
    options = []
    inputs = node.get("inputs", [])
    for input_def in inputs:
        if "list" in input_def:
            for option in input_def["list"]:
                code_val = option.get("value", "")
                # Try picking a label in the desired language if present, else fallback
                label = option.get("label", "")  # Might be something like "label": {"en": "...", "de": "..."}
                # If 'label' is itself localized, you can fetch label for 'preferred_lang'
                if isinstance(label, dict) and preferred_lang in label:
                    label = label[preferred_lang]
                elif isinstance(label, dict):
                    # fallback to any known language
                    label = next(iter(label.values()))

                # Decide system (Snomed vs. dummy code, etc.)
                system = "http://cistec-internal-dummy.ch/noCodes"
                # example logic
                terminology = input_def.get("terminology")
                if terminology:
                    system = terminology
                elif code_val.startswith("at"):
                    system = "http://cistec-internal-dummy.ch/atCodes"

                if default_value and default_value == label:
                    options.append({
                        "valueCoding": {
                            "system": system,
                            "code": code_val,
                            "display": label
                        },
                        "initialSelected": "true",

                    })
                else:
                    options.append({
                        "valueCoding": {
                            "system": system,
                            "code": code_val,
                            "display": label
                        }
                    })
    return options


def build_quantity_with_unit_options(fhir_item: Dict[str, Any], node: Dict[str, Any]):
    """
    Use the SDC extension 'questionnaire-unitOption' for enumerated units.
    """
    inputs = node.get("inputs", [])
    global_min = None
    global_max = None
    extensions = []

    for input_def in inputs:
        if input_def.get("suffix") == "unit" and "list" in input_def:
            for unit_option in input_def["list"]:
                code_val = unit_option.get("value", "")
                label = unit_option.get("label", code_val)
                # If label might be localized, handle it similarly to above
                if isinstance(label, dict):
                    # pick your language or fallback
                    label = next(iter(label.values()))

                # SDC extension for enumerating unit choices
                extensions.append({
                    "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-unitOption",
                    "valueCoding": {
                        "system": "http://unitsofmeasure.org",
                        "code": code_val,
                        "display": label
                    }
                })
                rng = unit_option.get("validation", {}).get("range", {})
                local_min = rng.get("min")
                local_max = rng.get("max")
                if local_min is not None:
                    if global_min is None or local_min < global_min:
                        global_min = local_min
                if local_max is not None:
                    if global_max is None or local_max > global_max:
                        global_max = local_max

    if global_min is not None:
        extensions.append({
            "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-minValue",
            "valueQuantity": {
                "value": global_min,
                "system": "http://unitsofmeasure.org"
            }
        })
    if global_max is not None:
        extensions.append({
            "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-maxValue",
            "valueQuantity": {
                "value": global_max,
                "system": "http://unitsofmeasure.org"
            }
        })

    if extensions:
        fhir_item["extension"] = extensions


def get_localized_name(node: Dict[str, Any], preferred_lang: str) -> str:
    """
    Return the name for node in the desired language, if available in 'localizedNames'.
    Otherwise return None or an empty string.
    """
    loc_names = node.get("localizedNames", {})
    return loc_names.get(preferred_lang, "")

def get_localized_description(node: Dict[str, Any], preferred_lang: str) -> str:
    """
    Return the description for node in the desired language, if available in 'localizedDescriptions'.
    Otherwise return None or an empty string.
    """
    loc_descriptions = node.get("localizedDescriptions", {})
    return loc_descriptions.get(preferred_lang, "")


def map_rmtype_to_fhir_type(rm_type: str) -> str:
    rm_type = rm_type.upper()
    if rm_type in ["COMPOSITION", "CLUSTER", "SECTION", "EVENT_CONTEXT"]:
        return "group"
    elif rm_type == "DV_CODED_TEXT":
        return "choice"
    elif rm_type == "DV_QUANTITY":
        return "quantity"
    elif rm_type == "DV_DATE_TIME":
        return "dateTime"
    elif rm_type == "DV_DATE":
        return "date"
    elif rm_type in ["DV_TIME", "DV_DURATION"]:
        return "time"
    elif rm_type == "DV_COUNT":
        return "integer"
    else:
        return "string"
    
def find_list_open(inputs: List[Dict[str, Any]]) -> bool:
    """
    Return true if any input_def has 'listOpen': true
    """
    for inp in inputs:
        # If it's the one with "list", also check if "listOpen" is present
        if inp.get("type") in ["TEXT", "CODED_TEXT"] and "list" in inp:
            # If 'listOpen' is explicitly false or true, return that
            # Some tools might store 'listOpen' at the same level
            if inp.get("listOpen") is True:
                return True
    return False

def find_default_value(inputs: List[Dict[str, Any]]) -> Optional[str]:
    """
    If there's a 'defaultValue' in the 'inputs', return it
    """
    for inp in inputs:
        if "defaultValue" in inp:
            return inp["defaultValue"]
    return None


if __name__ == "__main__":
    """
    Example usage:
        python3 webtemplate_to_fhir_questionnaire_json.py input_webtemplate.json out_en.json out_de.json
    """
    if len(sys.argv) < 3:
        print("Usage: python3 webtemplate_to_fhir_questionnaire_json.py <input.json> <output> ")
        sys.exit(1)

    # TODO: put actual code back
    #input_path = sys.argv[1]
    #input_path = "../templates_testing/cistec.openehr.body_weight_new.v1.json"
    input_path = "../templates_testing/report_status_internal_medicine.v1.json"
    out_en = f"{sys.argv[2]}_en.json"
    out_de = f"{sys.argv[2]}_de.json"

    # Convert for English
    convert_webtemplate_to_fhir_questionnaire_json(input_path, out_en, preferred_lang="en")
    # Convert for German
    convert_webtemplate_to_fhir_questionnaire_json(input_path, out_de, preferred_lang="de")
