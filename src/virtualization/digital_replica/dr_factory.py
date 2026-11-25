from datetime import datetime
from typing import Dict, Any, Type, List
from pydantic import BaseModel, create_model, Field, field_validator
import yaml
import uuid
import copy

class DRFactory:
    def __init__(self, schema_path: str):
        self.schema = self._load_schema(schema_path)
        if not self.schema or "schemas" not in self.schema:
            raise ValueError(f"Invalid schema structure in {schema_path}")

    def _load_schema(self, path: str) -> Dict:
        try:
            with open(path, "r") as file:
                return yaml.safe_load(file)
        except Exception as e:
            raise ValueError(f"Failed to load schema: {str(e)}")

    def _create_profile_model(self) -> Type[BaseModel]:
        """Create Pydantic model for profile section"""
        
        mandatory_fields = (
            self.schema["schemas"]
            .get("validations", {})
            .get("mandatory_fields", {})
            .get("profile", [])
        )
        type_constraints = (
            self.schema["schemas"].get("validations", {}).get("type_constraints", {})
        )

        field_definitions = {}
        profile_fields = self.schema["schemas"]["common_fields"].get("profile", {})

        for field_name, field_type in profile_fields.items():
            is_required = field_name in mandatory_fields
            constraints = {}

            if field_name in type_constraints:
                rules = type_constraints[field_name]
                if "min" in rules:
                    constraints["ge"] = rules["min"]
                if "max" in rules:
                    constraints["le"] = rules["max"]

            field_definitions[field_name] = (
                (
                    str
                    if field_type == "str"
                    else (
                        int
                        if field_type == "int"
                        else (
                            float
                            if field_type == "float"
                            else datetime if field_type == "datetime" else Any
                        )
                    )
                ),
                Field(None if not is_required else ..., **constraints),
            )

        model = create_model("Profile", **field_definitions)

        # Add enum validators where needed
        for field_name in field_definitions:
            if (
                field_name in type_constraints
                and "enum" in type_constraints[field_name]
            ):
                enum_values = type_constraints[field_name]["enum"]

                @field_validator(field_name)
                def validate_enum(value, field):
                    if value not in enum_values:
                        raise ValueError(f"{field.name} must be one of {enum_values}")
                    return value

                setattr(model, f"validate_{field_name}", validate_enum)

        return model

    def _create_data_model(self) -> Type[BaseModel]:
        """Create Pydantic model for data section"""
        type_constraints = (
            self.schema["schemas"].get("validations", {}).get("type_constraints", {})
        )
        data_fields = self.schema["schemas"].get("entity", {}).get("data", {})

        field_definitions = {}
        for field_name, field_type in data_fields.items():
            if field_type == "List[Dict]":
                field_definitions[field_name] = (
                    List[Dict[str, Any]],
                    Field(default_factory=list),
                )
            elif field_type == "List[str]":
                field_definitions[field_name] = (List[str], Field(default_factory=list))
            else:
                field_definitions[field_name] = (
                    (
                        str
                        if field_type == "str"
                        else (
                            int
                            if field_type == "int"
                            else float if field_type == "float" else Any
                        )
                    ),
                    Field(None),
                )

        model = create_model("Data", **field_definitions)

        # Add validators for fields that need them
        for field_name, field_type in data_fields.items():
            # Add enum validator if needed
            if (
                field_name in type_constraints
                and "enum" in type_constraints[field_name]
            ):
                enum_values = type_constraints[field_name]["enum"]

                @field_validator(field_name)
                def validate_enum(value, field):
                    if value not in enum_values:
                        raise ValueError(f"{field.name} must be one of {enum_values}")
                    return value

                setattr(model, f"validate_{field_name}", validate_enum)

            # Add List[Dict] validator if needed
            if field_type == "List[Dict]" and field_name in type_constraints:
                rules = type_constraints[field_name]
                if "item_constraints" in rules:
                    item_rules = rules["item_constraints"]
                    required_fields = item_rules.get("required_fields", [])
                    type_mappings = item_rules.get("type_mappings", {})

                    @field_validator(field_name)
                    def validate_list_items(value, field):
                        if not isinstance(value, list):
                            raise ValueError(f"{field.name} must be a list")

                        for idx, item in enumerate(value):
                            if not isinstance(item, dict):
                                raise ValueError(
                                    f"Item {idx} in {field.name} must be a dictionary"
                                )

                            missing = [f for f in required_fields if f not in item]
                            if missing:
                                raise ValueError(
                                    f"Missing required fields {missing} in item {idx}"
                                )

                            for key, expected_type in type_mappings.items():
                                if key in item:
                                    val = item[key]
                                    if expected_type == "datetime":
                                        if not isinstance(val, (datetime, str)):
                                            raise ValueError(
                                                f"Field {key} in item {idx} must be a datetime"
                                            )
                                    elif expected_type == "float":
                                        try:
                                            item[key] = float(val)
                                        except (TypeError, ValueError):
                                            raise ValueError(
                                                f"Field {key} in item {idx} must be a number"
                                            )
                        return value

                    setattr(model, f"validate_{field_name}", validate_list_items)

        return model

    def create_dr(self, dr_type: str, initial_data: Dict[str, Any]) -> Dict:
        """Create a new Digital Replica instance"""

        # Create Pydantic models for sections
        ProfileModel = self._create_profile_model()
        DataModel = self._create_data_model()

        # Initialize with required fields and defaults
        dr_dict = {
            "_id": str(uuid.uuid4()),  # We use _id for MongoDB
            "type": dr_type,
            "metadata": {
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            "data": {},  # Initialization of the 'data' container
        }

        # Apply initialization defaults dynamically based on the schema
        data_fields = self.schema["schemas"].get("entity", {}).get("data", {})
        init_values = (
            self.schema["schemas"].get("validations", {}).get("initialization", {})
        )

        for section, defaults in init_values.items():
            default_val = copy.deepcopy(defaults)
            if section == "metadata" and isinstance(default_val, dict):
                dr_dict["metadata"].update(default_val)
            elif section == "profile" and isinstance(default_val, dict):
                dr_dict.setdefault("profile", {}).update(default_val)
            elif section == "data" and isinstance(default_val, dict):
                dr_dict["data"].update(default_val)
            elif section in data_fields:
                dr_dict["data"][section] = default_val
            else:
                dr_dict[section] = default_val

        # Merge defaults with provided data and validate each section
        if "profile" in initial_data or "profile" in dr_dict:
            merged_profile = {
                **dr_dict.get("profile", {}),
                **initial_data.get("profile", {}),
            }
            profile = ProfileModel(**merged_profile)
            dr_dict["profile"] = profile.model_dump(exclude_unset=True)

        if "data" in initial_data or dr_dict["data"]:
            merged_data = {**dr_dict["data"], **initial_data.get("data", {})}
            data = DataModel(**merged_data)
            dr_dict["data"] = data.model_dump(exclude_unset=True)

        if "metadata" in initial_data:
            dr_dict["metadata"].update(initial_data["metadata"])

        return dr_dict

    def update_dr(self, dr: Dict[str, Any], updates: Dict[str, Any]) -> Dict:
        """Update an existing Digital Replica"""
        # Create Pydantic models
        ProfileModel = self._create_profile_model()
        DataModel = self._create_data_model()

        updated_dr = dr.copy()

        # Validate and apply updates section by section
        if "profile" in updates:
            current_profile = updated_dr.get("profile", {})
            profile = ProfileModel(**(current_profile | updates["profile"]))
            updated_dr["profile"] = profile.model_dump(exclude_unset=True)

        if "data" in updates:
            current_data = updated_dr.get("data", {})
            data = DataModel(**(current_data | updates["data"]))
            updated_dr["data"] = data.model_dump(exclude_unset=True)

        if "metadata" in updates:
            updated_dr["metadata"].update(updates["metadata"])

        # Update timestamp
        updated_dr["metadata"]["updated_at"] = datetime.utcnow()

        return updated_dr
