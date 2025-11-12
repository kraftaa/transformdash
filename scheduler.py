"""
Scheduler Service - Background job scheduling for transformation models
Uses APScheduler for cron-based scheduling with database persistence
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError
import pytz

from connection_manager import connection_manager
from transformations.dbt_loader import DBTModelLoader
from orchestration import TransformationEngine
from pathlib import Path

# Initialize model loader
models_dir = Path(__file__).parent / "models"
model_loader = DBTModelLoader(models_dir=str(models_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled execution of transformation models"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            timezone=pytz.UTC,
            job_defaults={
                'coalesce': True,  # Combine missed executions
                'max_instances': 1  # One instance per job
            }
        )
        self.scheduler.start()
        logger.info("Scheduler service started")

    def shutdown(self):
        """Gracefully shutdown the scheduler"""
        self.scheduler.shutdown(wait=True)
        logger.info("Scheduler service stopped")

    def add_schedule(
        self,
        schedule_id: int,
        model_names: list,
        cron_expression: str,
        timezone: str = 'UTC',
        model_name: str = None  # Backward compatibility
    ) -> bool:
        """
        Add a scheduled job for one or more models

        Args:
            schedule_id: Database ID of the schedule
            model_names: List of model names to run
            cron_expression: Cron expression (e.g., "0 9 * * *" for 9am daily)
            timezone: Timezone for the schedule
            model_name: Single model name (for backward compatibility)

        Returns:
            True if successfully added
        """
        try:
            # Handle backward compatibility
            if model_name and not model_names:
                model_names = [model_name]

            if not model_names:
                raise ValueError("No models specified for schedule")

            # Parse cron expression
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expression}")

            minute, hour, day, month, day_of_week = parts

            # Create cron trigger
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=pytz.timezone(timezone)
            )

            # Add job to scheduler
            job_id = f"schedule_{schedule_id}"
            models_desc = ', '.join(model_names) if len(model_names) <= 3 else f"{len(model_names)} models"

            self.scheduler.add_job(
                func=self._execute_scheduled_models,
                trigger=trigger,
                id=job_id,
                args=[schedule_id, model_names],
                replace_existing=True,
                name=f"Models: {models_desc}"
            )

            # Update next_run_at in database
            next_run = self.scheduler.get_job(job_id).next_run_time
            self._update_next_run_time(schedule_id, next_run)

            logger.info(f"Added schedule {schedule_id} for {len(model_names)} model(s) with cron '{cron_expression}'")
            return True

        except Exception as e:
            logger.error(f"Failed to add schedule {schedule_id}: {e}")
            return False

    def remove_schedule(self, schedule_id: int) -> bool:
        """Remove a scheduled job"""
        try:
            job_id = f"schedule_{schedule_id}"
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed schedule {schedule_id}")
            return True
        except JobLookupError:
            logger.warning(f"Schedule {schedule_id} not found in scheduler")
            return False
        except Exception as e:
            logger.error(f"Failed to remove schedule {schedule_id}: {e}")
            return False

    def pause_schedule(self, schedule_id: int) -> bool:
        """Pause a scheduled job"""
        try:
            job_id = f"schedule_{schedule_id}"
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused schedule {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause schedule {schedule_id}: {e}")
            return False

    def resume_schedule(self, schedule_id: int) -> bool:
        """Resume a paused scheduled job"""
        try:
            job_id = f"schedule_{schedule_id}"
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed schedule {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume schedule {schedule_id}: {e}")
            return False

    def get_active_schedules(self) -> List[Dict[str, Any]]:
        """Get all currently scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs

    def _execute_scheduled_models(self, schedule_id: int, model_names: List[str]):
        """
        Execute a scheduled run for one or more models

        Args:
            schedule_id: Database ID of the schedule
            model_names: List of model names to execute
        """
        started_at = datetime.now()
        run_records = {}  # Track run_id for each model

        try:
            models_str = ', '.join(model_names)
            logger.info(f"Starting scheduled run for models '{models_str}' (schedule {schedule_id})")

            # Load all models (need dependencies)
            all_models = model_loader.load_all_models()

            # Find all target models
            target_models = []
            for model_name in model_names:
                target_model = next((m for m in all_models if m.name == model_name), None)
                if not target_model:
                    logger.error(f"Model '{model_name}' not found")
                    continue
                target_models.append(target_model)

            if not target_models:
                raise ValueError(f"No valid models found from: {model_names}")

            # Get all dependencies for all target models
            all_dependencies = []
            for target_model in target_models:
                dependency_models = self._get_dependencies(target_model.name, all_models)
                for dep in dependency_models:
                    if dep not in all_dependencies:
                        all_dependencies.append(dep)

            # Combine dependencies and target models
            models_to_run = all_dependencies + target_models

            # Create run records for each target model
            for target_model in target_models:
                run_id = self._create_run_record(schedule_id, target_model.name, started_at)
                run_records[target_model.name] = run_id

            # Run all models together
            engine = TransformationEngine(models_to_run)
            context = engine.run(verbose=False)

            # Get summary
            summary = context.get_summary()
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()

            # Update run records for each target model
            for target_model in target_models:
                run_id = run_records.get(target_model.name)
                if not run_id:
                    continue

                if target_model.status == "completed":
                    self._complete_run_record(
                        run_id=run_id,
                        status='completed',
                        completed_at=completed_at,
                        execution_time=execution_time,
                        dependencies_run=len(all_dependencies),
                        models_completed=summary['successes'],
                        models_failed=summary['failures'],
                        models_skipped=0
                    )
                    logger.info(f"Scheduled run completed successfully for '{target_model.name}'")
                else:
                    error_msg = target_model.error or 'Model execution failed'
                    self._complete_run_record(
                        run_id=run_id,
                        status='failed',
                        completed_at=completed_at,
                        execution_time=execution_time,
                        error_message=error_msg,
                        error_traceback=None
                    )
                    logger.error(f"Scheduled run failed for '{target_model.name}': {error_msg}")

        except Exception as e:
            logger.error(f"Scheduled run failed: {e}")
            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds()

            # Mark all run records as failed
            for model_name, run_id in run_records.items():
                self._complete_run_record(
                    run_id=run_id,
                    status='failed',
                    completed_at=completed_at,
                    execution_time=execution_time,
                    error_message=str(e),
                    error_traceback=None
                )

        finally:
            # Update last_run_at and next_run_at for the schedule
            self._update_last_run_time(schedule_id, started_at)
            job_id = f"schedule_{schedule_id}"
            try:
                next_run = self.scheduler.get_job(job_id).next_run_time
                self._update_next_run_time(schedule_id, next_run)
            except:
                pass

    def _get_dependencies(self, model_name: str, all_models: List) -> List:
        """Recursively get all dependencies for a model"""
        model = next((m for m in all_models if m.name == model_name), None)
        if not model:
            return []

        deps = []
        for dep_name in model.depends_on:
            deps.extend(self._get_dependencies(dep_name, all_models))
            dep_model = next((m for m in all_models if m.name == dep_name), None)
            if dep_model and dep_model not in deps:
                deps.append(dep_model)

        return deps

    def _create_run_record(self, schedule_id: int, model_name: str, started_at: datetime) -> int:
        """Create a run record in the database"""
        with connection_manager.get_connection() as pg:
            result = pg.execute("""
                INSERT INTO schedule_runs (
                    schedule_id, model_name, status, started_at
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, params=(schedule_id, model_name, 'running', started_at), fetch=True)
            return result[0]['id']

    def _complete_run_record(
        self,
        run_id: int,
        status: str,
        completed_at: datetime,
        execution_time: float,
        dependencies_run: int = 0,
        models_completed: int = 0,
        models_failed: int = 0,
        models_skipped: int = 0,
        error_message: Optional[str] = None,
        error_traceback: Optional[str] = None
    ):
        """Update a run record with completion details"""
        with connection_manager.get_connection() as pg:
            pg.execute("""
                UPDATE schedule_runs
                SET
                    status = %s,
                    completed_at = %s,
                    execution_time_seconds = %s,
                    dependencies_run = %s,
                    models_completed = %s,
                    models_failed = %s,
                    models_skipped = %s,
                    error_message = %s,
                    error_traceback = %s
                WHERE id = %s
            """, params=(
                status, completed_at, execution_time,
                dependencies_run, models_completed, models_failed, models_skipped,
                error_message, error_traceback,
                run_id
            ))

    def _update_last_run_time(self, schedule_id: int, last_run_at: datetime):
        """Update the last_run_at timestamp for a schedule"""
        with connection_manager.get_connection() as pg:
            pg.execute("""
                UPDATE model_schedules
                SET last_run_at = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, params=(last_run_at, schedule_id))

    def _update_next_run_time(self, schedule_id: int, next_run_at: datetime):
        """Update the next_run_at timestamp for a schedule"""
        with connection_manager.get_connection() as pg:
            pg.execute("""
                UPDATE model_schedules
                SET next_run_at = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, params=(next_run_at, schedule_id))

    def load_schedules_from_db(self):
        """Load all active schedules from database and add them to scheduler"""
        try:
            with connection_manager.get_connection() as pg:
                # Get all active schedules
                schedules = pg.execute("""
                    SELECT id, schedule_name, cron_expression, timezone, is_active
                    FROM model_schedules
                    WHERE is_active = TRUE
                    ORDER BY id
                """, fetch=True)

                # For each schedule, get its associated models
                for schedule in schedules:
                    models = pg.execute("""
                        SELECT model_name
                        FROM schedule_models
                        WHERE schedule_id = %s
                        ORDER BY model_name
                    """, params=(schedule['id'],), fetch=True)

                    model_names = [m['model_name'] for m in models]

                    if model_names:
                        self.add_schedule(
                            schedule_id=schedule['id'],
                            model_names=model_names,
                            cron_expression=schedule['cron_expression'],
                            timezone=schedule['timezone']
                        )
                    else:
                        logger.warning(f"Schedule {schedule['id']} has no models assigned, skipping")

            logger.info(f"Loaded {len(schedules)} active schedules from database")

        except Exception as e:
            logger.error(f"Failed to load schedules from database: {e}")


# Global scheduler instance
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """Get or create the global scheduler service instance"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


def start_scheduler():
    """Initialize and start the scheduler service"""
    scheduler = get_scheduler()
    scheduler.load_schedules_from_db()
    return scheduler


def stop_scheduler():
    """Stop the scheduler service"""
    global _scheduler_service
    if _scheduler_service:
        _scheduler_service.shutdown()
        _scheduler_service = None
