"""
Model Registry - Manages trained ML models with versioning and metadata
"""
import json
import pickle
import joblib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Central registry for managing ML models
    Stores models, metadata, and provides versioning
    """

    def __init__(self, registry_dir: str = "ml/models"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.registry_dir / "registry.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        """Load registry metadata from JSON file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {"models": {}}

    def _save_metadata(self):
        """Save registry metadata to JSON file"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)

    def register_model(
        self,
        model: Any,
        model_name: str,
        model_type: str,
        version: Optional[str] = None,
        metrics: Optional[Dict] = None,
        feature_columns: Optional[List[str]] = None,
        target_column: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Register a trained model in the registry

        Args:
            model: Trained model object (sklearn, keras, etc.)
            model_name: Name of the model (e.g., 'churn_predictor')
            model_type: Type of model (e.g., 'classification', 'regression', 'clustering')
            version: Model version (auto-generated if not provided)
            metrics: Training/validation metrics
            feature_columns: List of feature column names
            target_column: Target column name
            description: Model description
            tags: Tags for categorization

        Returns:
            model_id: Unique identifier for the registered model
        """
        # Generate version if not provided
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")

        model_id = f"{model_name}_v{version}"

        # Save model artifact
        model_path = self.registry_dir / f"{model_id}.pkl"
        joblib.dump(model, model_path)

        # Create metadata entry
        metadata_entry = {
            "model_name": model_name,
            "model_id": model_id,
            "version": version,
            "model_type": model_type,
            "model_path": str(model_path),
            "registered_at": datetime.now().isoformat(),
            "metrics": metrics or {},
            "feature_columns": feature_columns or [],
            "target_column": target_column,
            "description": description or "",
            "tags": tags or [],
            "status": "active"
        }

        # Store in registry
        if model_name not in self.metadata["models"]:
            self.metadata["models"][model_name] = []

        self.metadata["models"][model_name].append(metadata_entry)
        self._save_metadata()

        logger.info(f"✓ Registered model: {model_id}")
        logger.info(f"  Type: {model_type}")
        logger.info(f"  Metrics: {metrics}")

        return model_id

    def load_model(self, model_name: str, version: Optional[str] = None) -> Any:
        """
        Load a model from the registry

        Args:
            model_name: Name of the model
            version: Specific version to load (loads latest if not specified)

        Returns:
            Loaded model object
        """
        if model_name not in self.metadata["models"]:
            raise ValueError(f"Model '{model_name}' not found in registry")

        versions = self.metadata["models"][model_name]

        if version:
            # Find specific version
            model_entry = next(
                (m for m in versions if m["version"] == version),
                None
            )
            if not model_entry:
                raise ValueError(f"Version '{version}' not found for model '{model_name}'")
        else:
            # Get latest version
            model_entry = max(versions, key=lambda x: x["registered_at"])

        model_path = Path(model_entry["model_path"])

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        model = joblib.load(model_path)
        logger.info(f"✓ Loaded model: {model_entry['model_id']}")

        return model

    def get_model_metadata(self, model_name: str, version: Optional[str] = None) -> Dict:
        """Get metadata for a specific model"""
        if model_name not in self.metadata["models"]:
            raise ValueError(f"Model '{model_name}' not found in registry")

        versions = self.metadata["models"][model_name]

        if version:
            model_entry = next(
                (m for m in versions if m["version"] == version),
                None
            )
            if not model_entry:
                raise ValueError(f"Version '{version}' not found for model '{model_name}'")
            return model_entry
        else:
            # Return latest version
            return max(versions, key=lambda x: x["registered_at"])

    def list_models(self) -> List[Dict]:
        """List all registered models with their latest versions"""
        models_list = []

        for model_name, versions in self.metadata["models"].items():
            latest = max(versions, key=lambda x: x["registered_at"])
            models_list.append({
                "model_name": model_name,
                "latest_version": latest["version"],
                "model_type": latest["model_type"],
                "description": latest.get("description", ""),
                "total_versions": len(versions),
                "last_updated": latest["registered_at"],
                "metrics": latest["metrics"],
                "tags": latest.get("tags", []),
                "feature_columns": latest.get("feature_columns", []),
                "target_column": latest.get("target_column", ""),
                "status": latest["status"]
            })

        return models_list

    def list_model_versions(self, model_name: str) -> List[Dict]:
        """List all versions of a specific model"""
        if model_name not in self.metadata["models"]:
            raise ValueError(f"Model '{model_name}' not found in registry")

        return sorted(
            self.metadata["models"][model_name],
            key=lambda x: x["registered_at"],
            reverse=True
        )

    def get_model_info(self, model_name: str, version: str = None) -> Dict:
        """
        Get detailed information about a model including description, metrics, features, etc.

        Args:
            model_name: Name of the model
            version: Specific version (optional, uses latest)

        Returns:
            Detailed model information dictionary
        """
        metadata = self.get_model_metadata(model_name, version)

        # Format the information nicely
        info = {
            "model_id": metadata["model_id"],
            "model_name": metadata["model_name"],
            "version": metadata["version"],
            "model_type": metadata["model_type"],
            "description": metadata.get("description", "No description provided"),
            "registered_at": metadata["registered_at"],
            "status": metadata["status"],
            "tags": metadata.get("tags", []),
            "metrics": metadata.get("metrics", {}),
            "features": {
                "feature_columns": metadata.get("feature_columns", []),
                "num_features": len(metadata.get("feature_columns", [])),
                "target_column": metadata.get("target_column", "")
            },
            "model_path": metadata["model_path"]
        }

        return info

    def delete_model(self, model_name: str, version: Optional[str] = None):
        """
        Delete a model or specific version
        If version is None, deletes all versions of the model
        """
        if model_name not in self.metadata["models"]:
            raise ValueError(f"Model '{model_name}' not found in registry")

        if version:
            # Delete specific version
            versions = self.metadata["models"][model_name]
            model_entry = next(
                (m for m in versions if m["version"] == version),
                None
            )

            if not model_entry:
                raise ValueError(f"Version '{version}' not found")

            # Delete model file
            model_path = Path(model_entry["model_path"])
            if model_path.exists():
                model_path.unlink()

            # Remove from metadata
            self.metadata["models"][model_name] = [
                m for m in versions if m["version"] != version
            ]

            # If no versions left, remove model entry
            if len(self.metadata["models"][model_name]) == 0:
                del self.metadata["models"][model_name]

            logger.info(f"✓ Deleted model version: {model_name}_v{version}")
        else:
            # Delete all versions
            versions = self.metadata["models"][model_name]

            for model_entry in versions:
                model_path = Path(model_entry["model_path"])
                if model_path.exists():
                    model_path.unlink()

            del self.metadata["models"][model_name]
            logger.info(f"✓ Deleted all versions of model: {model_name}")

        self._save_metadata()


# Global registry instance
model_registry = ModelRegistry()


if __name__ == "__main__":
    # Test the registry
    print("Testing Model Registry\n")
    print("=" * 60)

    # List all models
    print("\n📋 Registered Models:")
    models = model_registry.list_models()

    if not models:
        print("  No models registered yet")
        print("\n  To train a model, run:")
        print("    python ml/examples/train_example_model.py")
    else:
        for model in models:
            print(f"\n  • {model['model_name']}")
            print(f"    Version: {model['latest_version']}")
            print(f"    Type: {model['model_type']}")
            if model.get('description'):
                print(f"    Description: {model['description']}")
            if model.get('tags'):
                print(f"    Tags: {', '.join(model['tags'])}")
            print(f"    Features: {len(model.get('feature_columns', []))} columns")
            if model.get('target_column'):
                print(f"    Target: {model['target_column']}")
            print(f"    Total Versions: {model['total_versions']}")
            print(f"    Last Updated: {model['last_updated']}")
            print(f"    Metrics: {model['metrics']}")

        # Show detailed info for first model
        if models:
            print("\n" + "=" * 60)
            print("📊 Detailed Model Info (First Model):")
            print("=" * 60)
            first_model = models[0]
            info = model_registry.get_model_info(first_model['model_name'])

            print(f"\nModel ID: {info['model_id']}")
            print(f"Description: {info['description']}")
            print(f"Type: {info['model_type']}")
            print(f"Status: {info['status']}")

            if info['tags']:
                print(f"Tags: {', '.join(info['tags'])}")

            print(f"\nFeatures ({info['features']['num_features']}):")
            for i, feat in enumerate(info['features']['feature_columns'][:10], 1):
                print(f"  {i}. {feat}")
            if len(info['features']['feature_columns']) > 10:
                print(f"  ... and {len(info['features']['feature_columns']) - 10} more")

            print(f"\nTarget Column: {info['features']['target_column']}")

            print("\nMetrics:")
            for metric, value in info['metrics'].items():
                print(f"  {metric}: {value:.4f}")

            print(f"\nModel Path: {info['model_path']}")
