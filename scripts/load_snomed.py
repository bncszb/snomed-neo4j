#!/usr/bin/env python3
"""
Script to load SNOMED CT RF2 files into Neo4j.
"""

import os
import sys
import argparse
import csv
import time
from pathlib import Path
from tqdm import tqdm
from neo4j import GraphDatabase


def parse_args():
    parser = argparse.ArgumentParser(description='Load SNOMED CT data into Neo4j')
    parser.add_argument('--data-dir', required=True, help='Directory containing SNOMED CT RF2 files')
    parser.add_argument('--neo4j-uri', default='bolt://localhost:7687', help='Neo4j URI')
    parser.add_argument('--neo4j-user', default='neo4j', help='Neo4j username')
    parser.add_argument('--neo4j-password', default='neo4j', help='Neo4j password')
    parser.add_argument('--batch-size', type=int, default=10000, help='Batch size for loading')
    return parser.parse_args()


def find_rf2_files(data_dir):
    """Find RF2 files in the data directory."""
    data_path = Path(data_dir)
    
    # Look for Snapshot directory
    snapshot_dirs = list(data_path.glob("**/Snapshot"))
    if not snapshot_dirs:
        print("Error: Could not find Snapshot directory in the provided data path.")
        sys.exit(1)
    
    snapshot_dir = snapshot_dirs[0]
    
    # Find required files
    concept_file = list(snapshot_dir.glob("**/sct2_Concept_Snapshot_*.txt"))
    description_file = list(snapshot_dir.glob("**/sct2_Description_Snapshot_*.txt"))
    relationship_file = list(snapshot_dir.glob("**/sct2_Relationship_Snapshot_*.txt"))
    
    if not concept_file or not description_file or not relationship_file:
        print("Error: Could not find all required RF2 files.")
        sys.exit(1)
    
    return {
        "concept": str(concept_file[0]),
        "description": str(description_file[0]),
        "relationship": str(relationship_file[0])
    }


def setup_neo4j_schema(session):
    """Set up Neo4j schema with indexes and constraints."""
    print("Setting up Neo4j schema...")
    
    # Create constraints
    session.run("""
        CREATE CONSTRAINT concept_id IF NOT EXISTS
        FOR (c:Concept) REQUIRE c.id IS UNIQUE
    """)
    
    # Create indexes
    session.run("""
        CREATE INDEX concept_active IF NOT EXISTS
        FOR (c:Concept) ON (c.active)
    """)
    
    session.run("""
        CREATE INDEX description_term IF NOT EXISTS
        FOR (d:Description) ON (d.term)
    """)
    
    session.run("""
        CREATE INDEX relationship_type IF NOT EXISTS
        FOR ()-[r:RELATIONSHIP]->() ON (r.typeId)
    """)


def load_concepts(session, concept_file, batch_size):
    """Load concepts from RF2 file into Neo4j."""
    print("Loading concepts...")
    
    # Count lines for progress bar
    with open(concept_file, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for _ in f) - 1  # Subtract header
    
    batch = []
    loaded = 0
    
    with open(concept_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        with tqdm(total=total_lines) as pbar:
            for row in reader:
                # Convert active to boolean
                active = row['active'] == '1'
                
                # Add to batch
                batch.append({
                    "id": row['id'],
                    "active": active,
                    "moduleId": row['moduleId'],
                    "definitionStatusId": row['definitionStatusId']
                })
                
                # Process batch if full
                if len(batch) >= batch_size:
                    session.run("""
                        UNWIND $batch AS row
                        CREATE (c:Concept {
                            id: row.id,
                            active: row.active,
                            moduleId: row.moduleId,
                            definitionStatusId: row.definitionStatusId
                        })
                    """, {"batch": batch})
                    
                    loaded += len(batch)
                    pbar.update(len(batch))
                    batch = []
            
            # Process remaining batch
            if batch:
                session.run("""
                    UNWIND $batch AS row
                    CREATE (c:Concept {
                        id: row.id,
                        active: row.active,
                        moduleId: row.moduleId,
                        definitionStatusId: row.definitionStatusId
                    })
                """, {"batch": batch})
                
                loaded += len(batch)
                pbar.update(len(batch))
    
    print(f"Loaded {loaded} concepts.")


def load_descriptions(session, description_file, batch_size):
    """Load descriptions from RF2 file into Neo4j."""
    print("Loading descriptions...")
    
    # Count lines for progress bar
    with open(description_file, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for _ in f) - 1  # Subtract header
    
    batch = []
    loaded = 0
    
    with open(description_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        with tqdm(total=total_lines) as pbar:
            for row in reader:
                # Convert active to boolean
                active = row['active'] == '1'
                
                # Add to batch
                batch.append({
                    "id": row['id'],
                    "conceptId": row['conceptId'],
                    "active": active,
                    "term": row['term'],
                    "typeId": row['typeId'],
                    "languageCode": row['languageCode']
                })
                
                # Process batch if full
                if len(batch) >= batch_size:
                    session.run("""
                        UNWIND $batch AS row
                        MATCH (c:Concept {id: row.conceptId})
                        CREATE (d:Description {
                            id: row.id,
                            active: row.active,
                            term: row.term,
                            typeId: row.typeId,
                            languageCode: row.languageCode
                        })
                        CREATE (c)-[:HAS_DESCRIPTION]->(d)
                    """, {"batch": batch})
                    
                    loaded += len(batch)
                    pbar.update(len(batch))
                    batch = []
            
            # Process remaining batch
            if batch:
                session.run("""
                    UNWIND $batch AS row
                    MATCH (c:Concept {id: row.conceptId})
                    CREATE (d:Description {
                        id: row.id,
                        active: row.active,
                        term: row.term,
                        typeId: row.typeId,
                        languageCode: row.languageCode
                    })
                    CREATE (c)-[:HAS_DESCRIPTION]->(d)
                """, {"batch": batch})
                
                loaded += len(batch)
                pbar.update(len(batch))
    
    print(f"Loaded {loaded} descriptions.")


def load_relationships(session, relationship_file, batch_size):
    """Load relationships from RF2 file into Neo4j."""
    print("Loading relationships...")
    
    # Count lines for progress bar
    with open(relationship_file, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for _ in f) - 1  # Subtract header
    
    batch = []
    loaded = 0
    
    with open(relationship_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        with tqdm(total=total_lines) as pbar:
            for row in reader:
                # Convert active to boolean
                active = row['active'] == '1'
                
                # Skip inactive relationships
                if not active:
                    pbar.update(1)
                    continue
                
                # Add to batch
                batch.append({
                    "id": row['id'],
                    "sourceId": row['sourceId'],
                    "destinationId": row['destinationId'],
                    "typeId": row['typeId'],
                    "characteristicTypeId": row['characteristicTypeId'],
                    "modifierId": row['modifierId']
                })
                
                # Process batch if full
                if len(batch) >= batch_size:
                    session.run("""
                        UNWIND $batch AS row
                        MATCH (source:Concept {id: row.sourceId})
                        MATCH (destination:Concept {id: row.destinationId})
                        CREATE (source)-[:RELATIONSHIP {
                            id: row.id,
                            typeId: row.typeId,
                            characteristicTypeId: row.characteristicTypeId,
                            modifierId: row.modifierId
                        }]->(destination)
                    """, {"batch": batch})
                    
                    loaded += len(batch)
                    pbar.update(len(batch))
                    batch = []
            
            # Process remaining batch
            if batch:
                session.run("""
                    UNWIND $batch AS row
                    MATCH (source:Concept {id: row.sourceId})
                    MATCH (destination:Concept {id: row.destinationId})
                    CREATE (source)-[:RELATIONSHIP {
                        id: row.id,
                        typeId: row.typeId,
                        characteristicTypeId: row.characteristicTypeId,
                        modifierId: row.modifierId
                    }]->(destination)
                """, {"batch": batch})
                
                loaded += len(batch)
                pbar.update(len(batch))
    
    print(f"Loaded {loaded} relationships.")


def create_is_a_relationships(session):
    """Create IS_A relationships for better querying."""
    print("Creating IS_A relationships...")
    
    # The IS_A relationship type ID in SNOMED CT is 116680003
    session.run("""
        MATCH (source)-[r:RELATIONSHIP {typeId: '116680003'}]->(destination)
        CREATE (source)-[:IS_A]->(destination)
    """)
    
    print("IS_A relationships created.")


def main():
    args = parse_args()
    
    # Find RF2 files
    rf2_files = find_rf2_files(args.data_dir)
    
    # Connect to Neo4j
    driver = GraphDatabase.driver(
        args.neo4j_uri,
        auth=(args.neo4j_user, args.neo4j_password)
    )
    
    start_time = time.time()
    
    with driver.session() as session:
        # Set up schema
        setup_neo4j_schema(session)
        
        # Load data
        load_concepts(session, rf2_files["concept"], args.batch_size)
        load_descriptions(session, rf2_files["description"], args.batch_size)
        load_relationships(session, rf2_files["relationship"], args.batch_size)
        
        # Create IS_A relationships
        create_is_a_relationships(session)
    
    end_time = time.time()
    print(f"Data loading completed in {end_time - start_time:.2f} seconds.")
    
    driver.close()


if __name__ == "__main__":
    main()
