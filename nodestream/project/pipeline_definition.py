import os.path
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Set

from ..file_io import LoadsFromYaml, SavesToYaml
from ..pipeline import Pipeline, PipelineFile, PipelineInitializationArguments
from ..schema import ExpandsSchema, SchemaExpansionCoordinator


def get_default_name(file_path: Path) -> str:
    return file_path.stem


@dataclass
class PipelineDefinition(ExpandsSchema, SavesToYaml, LoadsFromYaml):
    """A `PipelineDefinition` represents a pipeline that can be loaded from a file.

    `PipelineDefinition` objects are used to load pipelines from files. They themselves
    are not pipelines, but rather represent the metadata needed to load a pipeline from
    a file.

    `PipelineDefinition` objects are also `IntrospectiveIngestionComponent` objects,
    meaning that they can be introspected to determine their known schema definitions.

    `PipelineDefinition` objects are also `SavesToYaml` and `LoadsFromYaml` objects,
    meaning that they can be serialized to and deserialized from YAML data.
    """

    name: str
    file_path: Path
    targets: Set[str] = frozenset()
    exclude_inherited_targets: bool = False
    annotations: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(cls, file_path: Path):
        """Create a `PipelineDefinition` from a file path.

        The name of the pipeline will be the stem of the file path, and the annotations
        will be empty. The pipeline will be loaded from the provided file path.

        Args:
            file_path (Path): The path to the file from which to load the pipeline.

        Returns:
            PipelineDefinition: The `PipelineDefinition` object.
        """
        return cls(get_default_name(file_path), file_path)

    @classmethod
    def describe_yaml_schema(cls):
        from schema import Optional, Or, Schema

        return Schema(
            Or(
                str,
                {
                    Optional("name"): str,
                    "path": os.path.exists,
                    Optional("annotations"): {str: Or(str, int, float, bool)},
                    Optional("targets"): [str],
                    Optional("exclude_inherited_targets"): bool,
                },
            )
        )

    @classmethod
    def from_file_data(cls, data, parent_annotations):
        if isinstance(data, str):
            data = {"path": data}

        file_path = Path(data.pop("path"))
        name = data.pop("name", get_default_name(file_path))
        exclude_targets = data.pop("exclude_inherited_targets", False)
        annotations = data.pop("annotations", {})
        targets = data.pop("targets", [])
        return cls(
            name,
            file_path,
            set(targets),
            exclude_targets,
            {**parent_annotations, **annotations},
        )

    def to_file_data(self, verbose: bool = False):
        using_default_name = self.name == self.file_path.stem
        if using_default_name and not self.annotations and not verbose:
            return str(self.file_path)

        result = {"path": str(self.file_path)}
        if not using_default_name or verbose:
            result["name"] = self.name
        if self.annotations or verbose:
            result["annotations"] = self.annotations
        if self.targets or verbose:
            result["targets"] = self.targets

        return result

    def initialize(self, init_args: PipelineInitializationArguments) -> Pipeline:
        return PipelineFile(self.file_path).load_pipeline(init_args)

    def remove_file(self, missing_ok: bool = True):
        """Remove the file associated with this `PipelineDefinition`.

        Args:
            missing_ok (bool, optional): Whether to ignore missing files. Defaults to True.

        Raises:
            FileNotFoundError: If the file does not exist and `missing_ok` is False.
        """
        self.file_path.unlink(missing_ok=missing_ok)

    def initialize_for_introspection(self) -> Pipeline:
        return self.initialize(PipelineInitializationArguments.for_introspection())

    def expand_schema(self, coordinator: SchemaExpansionCoordinator):
        self.initialize_for_introspection().expand_schema(coordinator)
