"""
Models API Endpoints
Handles listing, viewing, and running transformation models
"""
import logging
import json
import sys
from pathlib import Path
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
import asyncio

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from transformations.dbt_loader import DBTModelLoader
from orchestration.engine import TransformationEngine


async def get_all_models():
    """Get all transformation models (SQL + Python)"""
    try:
        logging.info("Loading all transformation models")

        models_dir = Path(__file__).parent / "models"
        loader = DBTModelLoader(models_dir=str(models_dir))

        # Load all models
        models = loader.load_all_models()

        # Convert to JSON-serializable format
        models_list = []
        for model in models:
            model_dict = {
                'name': model.name,
                'type': model.model_type.value,
                'depends_on': model.depends_on,
                'status': model.status,
                'config': getattr(model, 'config', {}),
                'file_path': getattr(model, 'file_path', None)
            }
            models_list.append(model_dict)

        # Group by layer
        bronze = [m for m in models_list if m['name'].startswith('stg_')]
        silver = [m for m in models_list if m['name'].startswith('int_')]
        gold = [m for m in models_list if m['name'].startswith('fct_')]
        other = [m for m in models_list if m not in bronze + silver + gold]

        logging.info(f"Loaded {len(models_list)} models")

        return {
            "success": True,
            "total": len(models_list),
            "models": models_list,
            "by_layer": {
                "bronze": bronze,
                "silver": silver,
                "gold": gold,
                "other": other
            }
        }

    except Exception as e:
        import traceback
        logging.error(f"Error loading models: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_model_by_name(model_name: str):
    """Get a single model by name"""
    try:
        logging.info(f"Loading model: {model_name}")

        models_dir = Path(__file__).parent / "models"
        loader = DBTModelLoader(models_dir=str(models_dir))

        # Load all models and find the one we want
        models = loader.load_all_models()
        model = next((m for m in models if m.name == model_name), None)

        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        model_dict = {
            'name': model.name,
            'type': model.model_type.value,
            'depends_on': model.depends_on,
            'status': model.status,
            'config': getattr(model, 'config', {}),
            'file_path': getattr(model, 'file_path', None)
        }

        # Read file content if available
        if model_dict['file_path']:
            try:
                with open(model_dict['file_path'], 'r') as f:
                    model_dict['content'] = f.read()
            except:
                model_dict['content'] = None

        return {
            "success": True,
            "model": model_dict
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error loading model {model_name}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_models(request: Request):
    """Run transformation models (all or specific ones)"""
    try:
        body = await request.json() if request.method == "POST" else {}
        model_names = body.get("models", None)  # None = run all

        if model_names:
            logging.info(f"Running specific models: {model_names}")
        else:
            logging.info("Running all transformation models")

        models_dir = Path(__file__).parent / "models"
        loader = DBTModelLoader(models_dir=str(models_dir))

        # Load models
        all_models = loader.load_all_models()

        # Filter to specific models if requested
        if model_names:
            models_to_run = [m for m in all_models if m.name in model_names]
            if len(models_to_run) != len(model_names):
                found_names = [m.name for m in models_to_run]
                missing = [n for n in model_names if n not in found_names]
                raise HTTPException(status_code=404, detail=f"Models not found: {missing}")
        else:
            models_to_run = all_models

        # Run models
        engine = TransformationEngine(models_to_run)
        context = engine.run(verbose=True)

        # Get summary
        summary = context.get_summary()

        # Get model results
        results = []
        for model in models_to_run:
            results.append({
                'name': model.name,
                'type': model.model_type.value,
                'status': model.status,
                'error': model.error
            })

        return {
            "success": summary['failures'] == 0,
            "summary": summary,
            "results": results,
            "logs": context.logs
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error running models: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_single_model(model_name: str):
    """Run a single transformation model"""
    try:
        logging.info(f"Running single model: {model_name}")

        models_dir = Path(__file__).parent / "models"
        loader = DBTModelLoader(models_dir=str(models_dir))

        # Load all models (need dependencies)
        all_models = loader.load_all_models()

        # Find the target model
        target_model = next((m for m in all_models if m.name == model_name), None)
        if not target_model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

        # Get all dependencies (recursively)
        def get_dependencies(model_name, all_models):
            model = next((m for m in all_models if m.name == model_name), None)
            if not model:
                return []

            deps = []
            for dep_name in model.depends_on:
                deps.extend(get_dependencies(dep_name, all_models))
                dep_model = next((m for m in all_models if m.name == dep_name), None)
                if dep_model and dep_model not in deps:
                    deps.append(dep_model)

            return deps

        # Get all models needed (dependencies + target)
        dependency_models = get_dependencies(model_name, all_models)
        models_to_run = dependency_models + [target_model]

        # Run models
        engine = TransformationEngine(models_to_run)
        context = engine.run(verbose=True)

        # Get summary
        summary = context.get_summary()

        # Check if target model succeeded
        if target_model.status != "completed":
            return {
                "success": False,
                "model": {
                    'name': target_model.name,
                    'type': target_model.model_type.value,
                    'status': target_model.status,
                    'error': target_model.error
                },
                "message": f"Model '{model_name}' failed to execute",
                "dependencies_run": len(dependency_models)
            }

        return {
            "success": True,
            "model": {
                'name': target_model.name,
                'type': target_model.model_type.value,
                'status': target_model.status,
                'error': target_model.error
            },
            "message": f"Model '{model_name}' executed successfully",
            "dependencies_run": len(dependency_models)
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"Error running model {model_name}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
