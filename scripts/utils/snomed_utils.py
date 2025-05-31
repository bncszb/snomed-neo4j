"""
Utility functions for working with SNOMED CT data.
"""

import os
import zipfile
from pathlib import Path

# SNOMED CT constants
SNOMED_ROOT_CONCEPT = "138875005"  # SNOMED CT Concept (root)
IS_A_RELATIONSHIP = "116680003"    # Is a (attribute)
FSN_TYPE = "900000000000003001"    # Fully specified name
PREFERRED_TERM_TYPE = "900000000000013009"  # Synonym
ACCEPTABLE_TERM_TYPE = "900000000000549004"  # Acceptable synonym

# Common SNOMED CT top-level concepts
CLINICAL_FINDING = "404684003"     # Clinical finding
PROCEDURE = "71388002"             # Procedure
BODY_STRUCTURE = "123037004"       # Body structure
ORGANISM = "410607006"             # Organism
SUBSTANCE = "105590001"            # Substance
PHARMACEUTICAL_PRODUCT = "373873005"  # Pharmaceutical / biologic product
SITUATION = "243796009"            # Situation with explicit context
EVENT = "272379006"                # Event
PHYSICAL_OBJECT = "260787004"      # Physical object
QUALIFIER_VALUE = "362981000"      # Qualifier value


def get_concept_hierarchy():
    """Return a dictionary of top-level SNOMED CT hierarchies."""
    return {
        "root": SNOMED_ROOT_CONCEPT,
        "clinical_finding": CLINICAL_FINDING,
        "procedure": PROCEDURE,
        "body_structure": BODY_STRUCTURE,
        "organism": ORGANISM,
        "substance": SUBSTANCE,
        "pharmaceutical_product": PHARMACEUTICAL_PRODUCT,
        "situation": SITUATION,
        "event": EVENT,
        "physical_object": PHYSICAL_OBJECT,
        "qualifier_value": QUALIFIER_VALUE
    }


def get_relationship_types():
    """Return a dictionary of common SNOMED CT relationship types."""
    return {
        "is_a": IS_A_RELATIONSHIP,
        "finding_site": "363698007",        # Finding site
        "associated_morphology": "116676008",  # Associated morphology
        "causative_agent": "246075003",     # Causative agent
        "has_active_ingredient": "127489000",  # Has active ingredient
        "method": "260686004",              # Method
        "pathological_process": "370135005",  # Pathological process
        "procedure_site": "363704007",      # Procedure site
        "severity": "246112005"             # Severity
    }


def format_concept_id(concept_id):
    """Format a SNOMED CT concept ID with proper spacing."""
    if not concept_id:
        return ""
    
    # Ensure the ID is a string
    concept_id = str(concept_id)
    
    # SNOMED CT IDs are typically formatted with a space every 3 digits
    # e.g., 123 456 789
    if len(concept_id) <= 3:
        return concept_id
    
    formatted = ""
    for i in range(0, len(concept_id), 3):
        chunk = concept_id[i:i+3]
        if formatted:
            formatted += " " + chunk
        else:
            formatted = chunk
    
    return formatted


def parse_concept_id(formatted_id):
    """Parse a formatted SNOMED CT concept ID to remove spaces."""
    if not formatted_id:
        return ""
    
    # Remove all spaces
    return formatted_id.replace(" ", "")


def extract_snomed_zip(zip_path, output_dir):
    """Extract a SNOMED CT zip file to the specified directory."""
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Zip file not found: {zip_path}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    
    # Return the path to the extracted directory
    extracted_dirs = [d for d in Path(output_dir).iterdir() if d.is_dir()]
    return str(extracted_dirs[0]) if extracted_dirs else output_dir


def find_rf2_files(data_dir):
    """Find RF2 files in the data directory and return their paths."""
    data_path = Path(data_dir)
    
    # Look for Snapshot directory
    snapshot_dirs = list(data_path.glob("**/Snapshot"))
    if not snapshot_dirs:
        # Try looking for Full directory if Snapshot not found
        full_dirs = list(data_path.glob("**/Full"))
        if not full_dirs:
            raise FileNotFoundError("Could not find Snapshot or Full directory in the provided data path")
        snapshot_dir = full_dirs[0]
    else:
        snapshot_dir = snapshot_dirs[0]
    
    # Find required RF2 files
    concept_file = list(snapshot_dir.glob("**/sct2_Concept_*"))
    description_file = list(snapshot_dir.glob("**/sct2_Description_*"))
    relationship_file = list(snapshot_dir.glob("**/sct2_Relationship_*"))
    
    if not concept_file or not description_file or not relationship_file:
        raise FileNotFoundError("Could not find all required RF2 files")
    
    return {
        "concept": str(concept_file[0]),
        "description": str(description_file[0]),
        "relationship": str(relationship_file[0])
    }
