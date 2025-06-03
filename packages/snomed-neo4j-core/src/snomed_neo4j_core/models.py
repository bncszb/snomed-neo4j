from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer, field_validator


def validate_effective_time(v: str | datetime) -> datetime:
    """Convert string to datetime, pass datetime through"""
    if isinstance(v, datetime):
        return v

    if isinstance(v, str):
        # SNOMED CT format (YYYYMMDD)
        if len(v) == 8 and v.isdigit():
            return datetime.strptime(v, "%Y%m%d")

        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            pass

        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"]:
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                continue

        raise ValueError(f"Cannot parse datetime from: {v}")

    raise ValueError(f"Expected string or datetime, got {type(v)}")


EffectiveTimeField = Annotated[
    datetime | str | None,
    BeforeValidator(validate_effective_time),
    PlainSerializer(lambda v: v.strftime("%Y%m%d"), return_type=str),
]

ActiveField = Annotated[
    bool | str | None,
    BeforeValidator(lambda v: v if isinstance(v, bool) else v.lower() in ("true", "1")),
]


class StatusEnum(str, Enum):
    """Status values for SNOMED CT components"""

    ACTIVE = "900000000000073002"  # Active
    INACTIVE = "900000000000074008"  # Inactive


class ModuleEnum(str, Enum):
    """Common SNOMED CT module identifiers"""

    CORE = "900000000000207008"  # SNOMED CT core module
    US_EXTENSION = "731000124108"  # US National Library of Medicine maintained module
    UK_EXTENSION = "999000041000000102"  # UK extension module


class DefinitionStatusEnum(str, Enum):
    """Definition status for SNOMED CT concepts"""

    PRIMITIVE = "900000000000074008"  # Primitive
    FULLY_DEFINED = "900000000000073002"  # Fully defined


class DescriptionTypeEnum(str, Enum):
    """Description type identifiers"""

    FSN = "900000000000003001"  # Fully specified name
    SYNONYM = "900000000000013009"  # Synonym
    DEFINITION = "900000000000550004"  # Definition


class CaseSignificanceEnum(str, Enum):
    """Case significance values"""

    ENTIRE_TERM_CASE_SENSITIVE = "900000000000017005"
    CASE_INSENSITIVE = "900000000000020002"
    INITIAL_CHARACTER_CASE_INSENSITIVE = "900000000000448009"


class CharacteristicTypeEnum(str, Enum):
    """Relationship characteristic types"""

    STATED_RELATIONSHIP = "900000000000010007"
    INFERRED_RELATIONSHIP = "900000000000011006"
    ADDITIONAL_RELATIONSHIP = "900000000000227009"


class ModifierEnum(str, Enum):
    """Relationship modifiers"""

    EXISTENTIAL_RESTRICTION = "900000000000451002"
    UNIVERSAL_RESTRICTION = "900000000000450001"


class Concept(BaseModel):
    """SNOMED CT Concept model"""

    id: str = Field(..., description="Concept identifier (SCTID)")
    effective_time: EffectiveTimeField = Field(..., description="Effective time of the concept", alias="effectiveTime")
    active: ActiveField = Field(True, description="Whether the concept is active")
    module_id: str = Field(..., description="Module identifier", alias="moduleId")
    definition_status_id: str = Field(..., description="Definition status", alias="definitionStatusId")

    @field_validator("id")
    @staticmethod
    def validate_concept_id(v: str) -> str:
        """Validate SNOMED CT concept ID format"""
        if not v.isdigit() or len(v) < 6 or len(v) > 18:
            raise ValueError("Concept ID must be 6-18 digits")
        return v


class Description(BaseModel):
    """SNOMED CT Description model"""

    id: str = Field(..., description="Description identifier (SCTID)")
    effective_time: EffectiveTimeField = Field(None, description="Effective time of the description", alias="effectiveTime")
    active: ActiveField = Field(True, description="Whether the description is active")
    module_id: str = Field(..., description="Module identifier", alias="moduleId")
    concept_id: str = Field(..., description="Associated concept identifier", alias="conceptId")
    language_code: str = Field("en", description="Language code (ISO 639-1)", alias="languageCode")
    type_id: str = Field(..., description="Description type", alias="typeId")
    term: str = Field(..., description="The description text")
    case_significance_id: str | None = Field(None, description="Case significance", alias="caseSignificanceId")

    @field_validator("id")
    @staticmethod
    def validate_description_id(v: str) -> str:
        """Validate SNOMED CT description ID format"""
        if not v.isdigit() or len(v) < 6 or len(v) > 18:
            raise ValueError("Description ID must be 6-18 digits")
        return v

    @field_validator("concept_id")
    @staticmethod
    def validate_concept_id(v: str) -> str:
        """Validate associated concept ID format"""
        if not v.isdigit() or len(v) < 6 or len(v) > 18:
            raise ValueError("Concept ID must be 6-18 digits")
        return v

    @field_validator("language_code")
    @staticmethod
    def validate_language_code(v: str) -> str:
        """Validate language code format"""
        if len(v) != 2:
            raise ValueError("Language code must be 2 characters (ISO 639-1)")
        return v.lower()

    @field_validator("term")
    @staticmethod
    def validate_term(v: str) -> str:
        """Validate term is not empty"""
        if not v or not v.strip():
            raise ValueError("Term cannot be empty")
        return v.strip()


class Relationship(BaseModel):
    """SNOMED CT Relationship model"""

    id: str = Field(..., description="Relationship identifier (SCTID)")
    effective_time: EffectiveTimeField = Field(None, description="Effective time of the relationship", alias="effectiveTime")
    active: ActiveField = Field(True, description="Whether the relationship is active")
    module_id: str = Field(..., description="Module identifier", alias="moduleId")
    source_id: str = Field(..., description="Source concept identifier", alias="sourceId")
    destination_id: str = Field(..., description="Destination concept identifier", alias="destinationId")
    relationship_group: int | str = Field(0, description="Relationship group number", alias="relationshipGroup")
    type_id: str = Field(..., description="Relationship type concept identifier", alias="typeId")
    characteristic_type_id: str = Field(..., description="Characteristic type", alias="characteristicTypeId")
    modifier_id: str = Field(..., description="Relationship modifier", alias="modifierId")

    @field_validator("id")
    @staticmethod
    def validate_relationship_id(v: str) -> str:
        """Validate SNOMED CT relationship ID format"""
        if not v.isdigit() or len(v) < 6 or len(v) > 18:
            raise ValueError("Relationship ID must be 6-18 digits")
        return v

    @field_validator("source_id", "destination_id", "type_id")
    @staticmethod
    def validate_concept_ids(v: str) -> str:
        """Validate concept ID format"""
        if not v.isdigit() or len(v) < 6 or len(v) > 18:
            raise ValueError("Concept ID must be 6-18 digits")
        return v

    @field_validator("relationship_group")
    @staticmethod
    def validate_relationship_group(v: str | int) -> int:
        """Validate relationship group is non-negative"""
        if isinstance(v, str):
            v = int(v)
        if v < 0:
            raise ValueError("Relationship group must be non-negative")
        return v

    model_config = ConfigDict(extra="ignore", json_encoders={datetime: lambda v: v.strftime("%Y%m%d")})


class ConceptWithDetails(Concept):
    """Extended SNOMED CT Concept with descriptions and relationships"""

    descriptions: list[Description] = Field(default_factory=list, description="Associated descriptions")
    relationships: list[Relationship] = Field(default_factory=list, description="Associated relationships")
    parent_relationships: list[Relationship] = Field(default_factory=list, description="Incoming relationships")

    @property
    def fsn(self) -> str | None:
        """Get the Fully Specified Name"""
        for desc in self.descriptions:
            if desc.active and desc.type_id == DescriptionTypeEnum.FSN:
                return desc.term
        return None

    @property
    def preferred_term(self) -> str | None:
        """Get the preferred synonym or FSN if no synonym exists"""
        # Look for active synonyms first
        for desc in self.descriptions:
            if desc.active and desc.type_id == DescriptionTypeEnum.SYNONYM:
                return desc.term
        # Fall back to FSN
        return self.fsn

    @property
    def is_a_relationships(self) -> list[Relationship]:
        """Get IS-A relationships (116680003)"""
        return [rel for rel in self.relationships if rel.active and rel.type_id == "116680003"]

    @classmethod
    def from_concept(cls, concept: Concept, **kwargs) -> "ConceptWithDetails":
        """Create ConceptWithDetails from a basic Concept"""
        return cls(**kwargs, **concept.model_dump(by_alias=True))


# Example usage and helper functions
class CodeSystem(BaseModel):
    """Container for SNOMED CT data"""

    concepts: list[Concept] = Field(default_factory=list)
    descriptions: list[Description] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    def get_concept_by_id(self, concept_id: str) -> Concept | None:
        """Get concept by ID"""
        return next((c for c in self.concepts if c.id == concept_id), None)

    def get_descriptions_for_concept(self, concept_id: str) -> list[Description]:
        """Get all descriptions for a concept"""
        return [d for d in self.descriptions if d.concept_id == concept_id]

    def get_relationships_for_concept(self, concept_id: str) -> list[Relationship]:
        """Get all outgoing relationships for a concept"""
        return [r for r in self.relationships if r.source_id == concept_id]


# Common SNOMED CT concept identifiers as constants
class CommonConcepts:
    """Common SNOMED CT concept identifiers"""

    SNOMED_CT_CONCEPT = "138875005"  # SNOMED CT Concept
    IS_A = "116680003"  # Is a
    PART_OF = "123005000"  # Part of
    CLINICAL_FINDING = "404684003"  # Clinical finding
    PROCEDURE = "71388002"  # Procedure
    OBSERVABLE_ENTITY = "363787002"  # Observable entity
    BODY_STRUCTURE = "123037004"  # Body structure
    ORGANISM = "410607006"  # Organism
    SUBSTANCE = "105590001"  # Substance
    PHARMACEUTICAL_PRODUCT = "373873005"  # Pharmaceutical / biologic product
    PHYSICAL_OBJECT = "260787004"  # Physical object
