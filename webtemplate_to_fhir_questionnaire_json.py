#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Cistec AG
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

import json
import os
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import time

def convert_webtemplate_to_fhir_questionnaire_json(
    input_file_path: str,
    output_file_path: str,
    preferred_lang: str = "en",
    fhir_version: str = "R4",
    name: Optional[str] = None,
    publisher: Optional[str] = None,
    text_types: Optional[str] = None
):
    """
    Loads an openEHR web template (JSON), converts it to a minimal FHIR Questionnaire (JSON)
    in the specified language (preferred_lang) and for the specified fhir_version,
    then writes the result to disk.
    """
    # 1) Read the web template JSON
    with open(input_file_path, "r", encoding="utf-8") as f:
        web_template = json.load(f)

    template_id = web_template.get("templateId", "unknown-web-template")
    root_node = web_template["tree"]

    # Gather the top-level name and description in the chosen language
    top_level_name = get_localized_name(root_node, preferred_lang)
    top_level_description = get_localized_description(root_node, preferred_lang)
    id = root_node.get("id")

    # Get local timezone offset in seconds
    offset_seconds = time.localtime().tm_gmtoff  
    offset_hours = offset_seconds // 3600
    offset_minutes = (offset_seconds % 3600) // 60

    # Format the offset as ±HH:MM
    offset_str = f"{offset_hours:+03d}:{offset_minutes:02d}"

        # If you wish to record which FHIR version is being used, you can set a meta.profile or similar:
    if fhir_version == "R4":
        profile = "http://hl7.org/fhir/R4/StructureDefinition/Questionnaire"
        
    elif fhir_version == "R5":
        profile = "http://hl7.org/fhir/R5/StructureDefinition/Questionnaire"
    else:
        # This is just for safety; the argparse choices=["R4","R5"] should prevent this
        raise ValueError("Unsupported FHIR version. Must be R4 or R5.")

    # 2) Build the FHIR Questionnaire
    questionnaire = {
        "resourceType": "Questionnaire",
        "id": template_id.replace("_", "-"),
        #"language": preferred_lang,
        "url": f"http://example.org/fhir/Questionnaire/{preferred_lang}-{id}",
        #"meta": {
        #    "profile": [profile]
        #},
        #"identifier": [
        #    {
        #        "system": "http://example.org/fhir/identifiers",
        #        "value": f"{preferred_lang}-{id}"
        #    }
        #],
        "name": name if name else top_level_name.replace(' ', ''),
        "title": top_level_name or root_node.get("name", "Unnamed Template"),
        "status": "draft",
        "publisher": publisher if publisher else "converter",
        "date": datetime.now().strftime(f"%Y-%m-%dT%H:%M:%S{offset_str}"),
        "description": top_level_description or "Auto-generated from openEHR web template to FHIR Questionnaire",
        "item": []
    }

    # Create a top-level 'group' item
    composition_item = {
        # TODO: replace linkId: aqlPath instead of nodeId
        # Note: root doesn't have aqlPath
        "linkId": root_node.get("nodeId", "composition"),
        #"linkId": root_node.get("aqlPath"),
        "text": top_level_name or root_node.get("name", "Composition"),
        "type": "group",
        "item": []
    }
    questionnaire["item"].append(composition_item)

    # 3) Recursively process children
    children = root_node.get("children", [])
    for child in children:
        child_item = process_webtemplate_node(child, preferred_lang, fhir_version, text_types)
        if child_item:
            composition_item["item"].append(child_item)

    # 4) Write output
    with open(output_file_path, "w", encoding="utf-8") as out:
        json.dump(questionnaire, out, indent=2, ensure_ascii=False)
    print(f"FHIR Questionnaire for lang='{preferred_lang}', FHIR={fhir_version} written to {output_file_path}")


def process_webtemplate_node(node: Dict[str, Any], preferred_lang: str, fhir_version, text_types) -> Optional[Dict[str, Any]]:
    """
    Converts one node from the web template into a FHIR Questionnaire 'item' dict,
    picking the localized text in the chosen language if possible.
    """

    # Exclude items that are purely contextual, if appropriate:
    # TODO: add parameter to enable/disable this as a setting
    if node.get("inContext") is True:
        # Exclude most context items except certain date/time?
        if node.get("rmType") != "DV_DATE_TIME" or node.get("aqlPath") == "/context/start_time":
            return None

    fhir_item = {}
    # TODO: replace linkId: aqlPath instead of nodeId
    #link_id = node.get("nodeId") or node.get("id") or "unknown"
    link_id = node.get("aqlPath")
    fhir_item["linkId"] = link_id

    # Evaluate min/max -> required, repeats
    min_occurs = node.get("min", 0)
    max_occurs = node.get("max", 1)
    fhir_item["required"] = (min_occurs >= 1)
    fhir_item["repeats"] = (max_occurs >= 2 or max_occurs == -1)

    # Use localized names/descriptions for item text, if available
    item_text = get_localized_name(node, preferred_lang)
    if not item_text:
        item_text = node.get("name") or node.get("localizedName") or node.get("id")
    fhir_item["text"] = item_text

    # Child items
    children = node.get("children", [])
    if children:
        fhir_item["type"] = "group"
        subitems = []
        for child in children:
            sub_item = process_webtemplate_node(child, preferred_lang, fhir_version, text_types)
            if sub_item:
                subitems.append(sub_item)
        if subitems:
            fhir_item["item"] = subitems
        else:
            # remove group nodes without children
            return None 
    else:
        #rm_type = (node.get("rmType") or "").upper()
        fhir_item["type"] = map_rmtype_to_fhir_type(node, fhir_version, text_types)

        # TODO: check if this is the correct usage of R5 types
        if fhir_item["type"] in ["choice", "open-choice", "question", "coding"]:
            # TODO: default value for other types (?) is there actually defaults in other types?
            default_val = find_default_value(node.get("inputs", []))
            answer_options = build_answer_options(node, preferred_lang, default_val)
            if answer_options:
                fhir_item["answerOption"] = answer_options

        elif fhir_item["type"] == "quantity":
            build_quantity_with_unit_options(fhir_item, node)

        #if rm_type == "DV_CODED_TEXT":
        #    fhir_item["type"] = "open-choice" if find_list_open(node.get("inputs", [])) else "choice"
        #    default_val = find_default_value(node.get("inputs", []))
        #    answer_options = build_answer_options(node, preferred_lang, default_val)
        #    if answer_options:
        #        fhir_item["answerOption"] = answer_options
        #elif rm_type == "DV_TEXT":
        #    fhir_item["type"] = "string"
        #elif rm_type == "DV_QUANTITY":
        #    fhir_item["type"] = "quantity"
        #    build_quantity_with_unit_options(fhir_item, node)
        #else:
        #    # other types: dateTime, integer, etc.
        #    fhir_item["type"] = map_rmtype_to_fhir_type(rm_type)

    return fhir_item

# TODO: additional types and data structures.

#data_structures = ["CLUSTER", "DATA_STRUCTURE", "ELEMENT", "EVENT", "HISTORY", "INTERVAL_EVENT", "ITEM", "ITEM_LIST", "ITEM_SINGLE", "ITEM_STRUCTURE", "ITEM_TABLE", "ITEM_TREE", "POINT_EVENT"]
# data types:
# all: CODE_PHRASE DATA_VALUE DV_ABSOLUTE_QUANTITY DV_AMOUNT DV_BOOLEAN DV_CODED_TEXT DV_COUNT DV_DATE DV_DATE_TIME DV_DURATION DV_EHR_URI DV_ENCAPSULATED
# DV_GENERAL_TIME_SPECIFICATION DV_IDENTIFIER DV_INTERVAL DV_MULTIMEDIA DV_ORDERED DV_ORDINAL DV_PARAGRAPH DV_PARSABLE DV_PERIODIC_TIME_SPECIFICATION
# DV_PROPORTION DV_QUANTIFIED DV_QUANTITY DV_SCALE DV_STATE DV_TEMPORAL DV_TEXT DV_TIME DV_TIME_SPECIFICATION DV_URI PROPORTION_KIND REFERENCE_RANGE TERM_MAPPING

# see R4:
# see R5: https://build.fhir.org/codesystem-item-type.html#item-type-question
def map_rmtype_to_fhir_type(node, fhir_version, text_types) -> str:
    """Maps an openEHR RM Type to a corresponding FHIR Questionnaire item type."""
    rm_type = (node.get("rmType") or "").upper()
    # General mappings
    rmtype_to_fhir = {
        "COMPOSITION": "group",
        "CLUSTER": "group",
        "SECTION": "group",
        "EVENT_CONTEXT": "group",
        "DV_QUANTITY": "quantity",
        "DV_DATE_TIME": "dateTime",
        "DV_DATE": "date",
        "DV_TIME": "time",
        "DV_DURATION": "time",
        "DV_COUNT": "integer",
        "DV_BOOLEAN": "boolean",
        "DV_MULTIMEDIA": "attachment",
        "DV_URI": "reference",
        "DV_EHR_URI": "reference",
    }

    # Return if a direct match exists
    if rm_type in rmtype_to_fhir:
        return rmtype_to_fhir[rm_type]

    # Special cases
    if rm_type == "DV_CODED_TEXT":
        if fhir_version == "R4":
            return "open-choice" if find_list_open(node.get("inputs", [])) else "choice"
        elif fhir_version == "R5":
            return "question" if find_list_open(node.get("inputs", [])) else "coding"

    if rm_type == "DV_TEXT":
        return node.get("annotations", {}).get("text_type") if text_types == "from_annotations" else "text"

    # Default case
    return "text"


def build_answer_options(node: Dict[str, Any], preferred_lang: str, default_value: Optional[str]) -> List[Dict[str, Any]]:
    """
    Look for coded input lists in node["inputs"] and produce FHIR answerOption entries.
    """
    options = []
    inputs = node.get("inputs", [])
    for input_def in inputs:
        if "list" in input_def:
            for option in input_def["list"]:
                code_val = option.get("value", "")
                label = option.get("label", "")
                # If label is dict, try to fetch the preferred language or fallback
                if isinstance(label, dict) and preferred_lang in label:
                    label = label[preferred_lang]
                elif isinstance(label, dict):
                    label = next(iter(label.values()))

                # TODO: replace this with a proper solution that validates when posting
                system = "http://cistec-internal-dummy.ch/noCodes"
                terminology = input_def.get("terminology")
                if terminology:
                    system = terminology
                elif code_val.startswith("at"):
                    system = "http://cistec-internal-dummy.ch/atCodes"

                coding_dict = {
                    "system": system,
                    "code": code_val,
                    "display": label
                }
                # If this code is the default
                # TODO: (maybe) use initial instead of initialSelected (seems more stable)
                if default_value and default_value == label:
                    options.append({
                        "valueCoding": coding_dict,
                        "initialSelected": True
                    })
                else:
                    options.append({"valueCoding": coding_dict})
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
                if isinstance(label, dict):
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

                #if local_min is not None:
                #    extensions.append({
                #        "url": "http://hl7.org/fhir/StructureDefinition/minValue",
                #        "valueQuantity": local_min
                #    })
#
                #if local_max is not None:
                #    extensions.append({
                #        "url": "http://hl7.org/fhir/StructureDefinition/maxValue",
                #        "valueQuantity": local_max
                #    })

    if global_min is not None:
        extensions.append({
            "url": "http://hl7.org/fhir/StructureDefinition/minValue",
            "valueDecimal": global_min
        })

    if global_max is not None:
        extensions.append({
            "url": "http://hl7.org/fhir/StructureDefinition/maxValue",
            "valueDecimal": global_max
        })

    if extensions:
        fhir_item["extension"] = extensions


def get_localized_name(node: Dict[str, Any], preferred_lang: str) -> str:
    """
    Return the name for node in the desired language if available in 'localizedNames'.
    """
    loc_names = node.get("localizedNames", {})
    return loc_names.get(preferred_lang, "")


def get_localized_description(node: Dict[str, Any], preferred_lang: str) -> str:
    """
    Return the description for node in the desired language if available in 'localizedDescriptions'.
    """
    loc_descriptions = node.get("localizedDescriptions", {})
    return loc_descriptions.get(preferred_lang, "")


def find_list_open(inputs: List[Dict[str, Any]]) -> bool:
    """
    Return true if any input_def with 'list' indicates 'listOpen': true
    """
    for inp in inputs:
        if inp.get("type") in ["TEXT", "CODED_TEXT"] and "list" in inp:
            if inp.get("listOpen") is True:
                return True
    return False


def find_default_value(inputs: List[Dict[str, Any]]) -> Optional[str]:
    """
    If there's a 'defaultValue' in the 'inputs', return it.
    """
    for inp in inputs:
        if "defaultValue" in inp:
            return inp["defaultValue"]
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Converts an openEHR web template (JSON) into FHIR Questionnaire (JSON)."
    )
    parser.add_argument("--input", required=True, help="Path to the input openEHR web template JSON")
    parser.add_argument(
        "--output",
        required=False,
        help="Base name for the output FHIR Questionnaire JSON"
    )
    parser.add_argument(
        "--output_folder",
        required=False,
        default=".",
        help="Output folder path"
    )
    parser.add_argument(
        "--languages",
        required=False,
        default="en",
        help="Comma-separated list of languages to generate. Default is 'en'. Example: 'en,de,fr'"
    )
    parser.add_argument(
        "--fhir_version",
        required=False,
        default="R4",
        choices=["R4", "R5"],
        help="FHIR version to use in the output. Must be either R4 or R5. Default is R4."
    )
    parser.add_argument(
        "--name",
        required=False,
        help="Optional 'name' attribute for the FHIR Questionnaire. "
             "If not given, we default to the template name (without spaces)."
    )
    parser.add_argument(
        "--publisher",
        required=False,
        help="Optional 'publisher' attribute for the FHIR Questionnaire. "
             "If not given, we default to 'converter'."
    )
    parser.add_argument(
        "--text_types",
        required=False,
        help="Handling of Free text (string/text in questionnaires)."
    )

    args = parser.parse_args()

    # Split languages on commas
    langs = [lang.strip() for lang in args.languages.split(",")]

    # You can choose how to handle the output naming convention. For example:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    # set (default) output base name:
    if args.output:
        base_name = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.input))[0]

    for lang in langs:
        #out_file = f"{args.output}_{lang}.json"
        out_file = os.path.join(args.output_folder, f"{timestamp}-{base_name}-{lang}.json")
        convert_webtemplate_to_fhir_questionnaire_json(
            input_file_path=args.input,
            output_file_path=out_file,
            preferred_lang=lang,
            fhir_version=args.fhir_version,
            name=args.name,
            publisher=args.publisher,
            text_types=args.text_types
        )
