import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
import argparse
from datetime import datetime, timezone
import os
import requests
import locale

def process_questionnaire_bundle(bundle_json: dict, ctx_setting="238", ctx_territory=None) -> List[Dict[str, Any]]:
    """Processes a FHIR Bundle containing multiple QuestionnaireResponses."""
    compositions = []

    if bundle_json.get("resourceType") == "QuestionnaireResponse":
        composition = convert_fhir_to_openehr_flat(bundle_json, ctx_setting=ctx_setting, ctx_territory=ctx_territory)
        questionnaire_ref = bundle_json.get("questionnaire", "")
        compositions.append({
            "questionnaire": questionnaire_ref,
            "composition": composition
        })
        return compositions # early return if single QuestionnaireResponse (in [] anyway)

    for entry in bundle_json.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Practitioner":
            practitioner_id = resource.get("id", "")
        elif resource.get("resourceType") == "Encounter":
            encounter_id = resource.get("id", "") # visit number (?)
        elif resource.get("resourceType") == "QuestionnaireResponse":
            print(f"Processing QuestionnaireResponse: {resource.get('id', 'unknown')}")
            qr = resource
            questionnaire_ref = qr.get("questionnaire", "")
            composition = convert_fhir_to_openehr_flat(qr, ctx_setting=ctx_setting, ctx_territory=ctx_territory, ctx_author=practitioner_id)
            compositions.append({
                "questionnaire": questionnaire_ref,
                "composition": composition
            })
        else:
            continue

    return compositions

def convert_fhir_to_openehr_flat(questionnaire_response: Dict[str, Any], ctx_setting=None, ctx_territory=None, ctx_author=None) -> Dict[str, Any]:
    composition = {}

    questionnaire = fetch_questionnaire_from_server(questionnaire_response.get("questionnaire"))
    metadata_questionnaire = extract_metadata_from_questionnaire(questionnaire)

    if not ctx_author:
        ctx_author = questionnaire_response.get("author", {}).get("display", "Unknown Author")

    ### NOTE: doesn't work for gradio/huggingface
    if not ctx_territory:
        ctx_territory = locale.getdefaultlocale()  # e.g., ('en_US', 'UTF-8')
        if ctx_territory and '_' in ctx_territory[0]:
            ctx_territory = ctx_territory[0].split('_')[1]  # → "US"

    ctx_values = {
        "ctx/template_id": metadata_questionnaire["template_id"],
        "ctx/territory": ctx_territory,
        "ctx/language": metadata_questionnaire["language"],
        "ctx/composer_name": ctx_author,  # author
        #"ctx/setting":
    }

    if ctx_setting:
        ctx_values["ctx/setting"] = ctx_setting

    composition.update(ctx_values)

    #group_counters = defaultdict(int)  # Keeps count of group-level indices
    #group_stack = []  # Stack of current parent groups

    def process_items(items: List[Dict[str, Any]], parent_path: str = ""):
        grouped_by_link = defaultdict(list)
        for item in items:
            grouped_by_link[item["linkId"]].append(item)

        #print(f"Processing items with parent path: {parent_path}")
        #print("Grouped items by linkId:")
        #for k, v in grouped_by_link.items():
        #    print(k, v)

        for link_id, group_items in grouped_by_link.items():
            for index, item in enumerate(group_items):
                # Only append index if repeated group
                last_part = link_id.split("/")[-1]
                if len(group_items) > 1:
                    path = f"{parent_path}/{last_part}:{index}" if parent_path else f"{link_id}:{index}"
                else:
                    path = f"{parent_path}/{last_part}" if parent_path else link_id
                #if len(group_items) > 1:
                #    path = f"{link_id}:{index}"
                #else:
                #    path = link_id

                process_item(item, path)

    def process_item(item: Dict[str, Any], path: str):
        # Answers
        if "answer" in item:
            answers = item["answer"]
            for idx, answer in enumerate(answers):
                final_path = f"{path}:{idx}" if len(answers) > 1 else path
                process_answer(final_path, answer)

        # Nested items
        if "item" in item:
            process_items(item["item"], parent_path=path)

    def process_answer(path: str, answer: Dict[str, Any]):
        if 'valueQuantity' in answer:
            quantity = answer['valueQuantity']
            composition[f"{path}|magnitude"] = quantity.get('value')
            composition[f"{path}|unit"] = quantity.get('unit')
            composition[f"{path}|precision"] = quantity.get('precision', 0)
        elif 'valueCoding' in answer:
            coding = answer['valueCoding']
            composition[f"{path}|value"] = coding.get('display')
            composition[f"{path}|code"] = coding.get('code')
            composition[f"{path}|terminology"] = coding.get('system', 'local')
        elif 'valueString' in answer:
            composition[path] = answer['valueString']
        elif 'valueBoolean' in answer:
            composition[path] = answer['valueBoolean']
        elif 'valueInteger' in answer:
            composition[path] = answer['valueInteger']
        elif 'valueDecimal' in answer:
            composition[path] = answer['valueDecimal']
        elif 'valueDate' in answer:
            composition[path] = answer['valueDate']
        elif 'valueDateTime' in answer:
            composition[path] = answer['valueDateTime']
        elif 'valueTime' in answer:
            composition[path] = answer['valueTime']
        elif 'valueUri' in answer:
            composition[path] = answer['valueUri']
        elif 'valueReference' in answer:
            reference = answer['valueReference']
            composition[path] = reference.get('reference')

    # Kick off the process
    if "item" in questionnaire_response:
        process_items(questionnaire_response["item"])

    return composition

def fetch_questionnaire_from_server(canonical_url: str) -> dict:
    #base_url, sep, version = canonical_url.partition("|")

    try:
        response = requests.get(canonical_url)
        response.raise_for_status()
        questionnaire = response.json()

        # Optional: verify version
        #if version and questionnaire.get("version") != version:
        #    raise ValueError(f"Version mismatch: expected {version}, got {questionnaire.get('version')}")

        return questionnaire

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch Questionnaire: {e}")

def extract_metadata_from_questionnaire(questionnaire: dict):
    # Extract template ID from identifier
    template_id = None
    for idf in questionnaire.get("identifier", []):
        if idf.get("system") == "http://example.org/openEHR/templates":
            template_id = idf.get("value")
            break

    language = questionnaire.get("language", "en")

    return {
        "template_id": template_id,
        "language": language
    }

# Run the example
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Creates an openEHR composition from a questionnaireResponse."
    )
    parser.add_argument("--input", help="Path to the input questionnaireResponse JSON file")
    parser.add_argument(
        "--care_setting",
        required=False,
        help="Care setting for the openEHR composition, either 3-digit code or description (example: 228 / primary medical care)"
    )
    parser.add_argument(
        "--territory",
        required=False,
        help="Territory: 2-character code according to ISO 3166-1 (example: 'US')." \
        "If not provided, will default to 'US'" \
    )
    parser.add_argument(
        "--output",
        required=False,
        help="Base name for the output questionnaireResponse"
    )
    parser.add_argument(
        "--output_folder",
        required=False,
        default=".",
        help="Output folder path"
    )

    args = parser.parse_args()

    if not args.input:
        ### individual questionnaire responses:
        #args.input = "../outputs/questionnaires/testing/20251007_0907-heart_sounds_response.json"  # Default input file if not provided
        #args.input = "../outputs/questionnaires/testing/20251007_0924-medication_order_response.json"
        #args.input = "../outputs/questionnaires/testing/20250725-1032_BloodPressure_Response.json"
        ### bundles:
        #args.input = "../outputs/questionnaires/testing/Bundle-CollectionBundleK6_adapted.json"
        args.input = "../outputs/questionnaires/testing/Bundle-CollectionBundleK6_adapted2.json"


    # You can choose how to handle the output naming convention. For example:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    # set (default) output base name:
    if args.output:
        base_name = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.input))[0]

    # example command for local testing:
    # python fill_composition_from_response.py --input ../outputs/questionnaires/testing/cistec.openehr.blood_pressure.v1.json --languages en --fhir_version R4 --publisher "Command local" --output_folder ../outputs/questionnaires/testing
    
    # Convert to openEHR composition
    fhir_response = json.load(open(args.input, 'r', encoding='utf-8'))
    #compositions = convert_fhir_to_openehr_flat(fhir_response)
    compositions = process_questionnaire_bundle(fhir_response, ctx_setting=args.care_setting, ctx_territory=args.territory)

    # Print the result
    print("openEHR Composition(s) (FLAT format):")
    #print(json.dumps(compositions, indent=2))
    for comp in compositions:
        print(json.dumps(comp, indent=2))
    #print(json.dumps(fhir_response, indent=2))

    #out_file = os.path.join(args.output_folder, f"{timestamp}-{base_name}-{lang}.json")
