#!/usr/bin/env python3
"""
TransformDash CLI - Command-line interface for managing system, jobs, and agents
"""
import argparse
import requests
import json
from datetime import datetime
from tabulate import tabulate
import sys

BASE_URL = "http://localhost:8000"


def format_uptime(seconds):
    """Format uptime in human-readable format"""
    minutes = int(seconds / 60)
    hours = int(minutes / 60)
    days = int(hours / 24)

    if days > 0:
        return f"{days}d {hours % 24}h {minutes % 60}m"
    elif hours > 0:
        return f"{hours}h {minutes % 60}m"
    else:
        return f"{minutes}m"


def format_next_run(next_run_str):
    """Format next run time"""
    if not next_run_str:
        return "Not scheduled"

    try:
        next_run = datetime.fromisoformat(next_run_str.replace('Z', '+00:00'))
        now = datetime.now(next_run.tzinfo)
        diff = next_run - now

        diff_hours = int(diff.total_seconds() / 3600)
        diff_minutes = int((diff.total_seconds() % 3600) / 60)

        if diff_hours > 24:
            diff_days = int(diff_hours / 24)
            return f"in {diff_days}d {diff_hours % 24}h"
        elif diff_hours > 0:
            return f"in {diff_hours}h {diff_minutes}m"
        elif diff_minutes > 0:
            return f"in {diff_minutes}m"
        else:
            return "Soon"
    except Exception as e:
        return next_run_str


def get_status():
    """Get server status"""
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        data = response.json()

        if data['status'] == 'healthy':
            print("\n✅ TransformDash Server Status")
            print("=" * 60)
            print(f"Status: {data['status'].upper()}")
            print(f"Timestamp: {data['timestamp']}")
            print()

            # Process info
            process = data['process']
            print("📊 Process Information:")
            print(f"  PID: {process['pid']}")
            print(f"  Uptime: {format_uptime(process['uptime_seconds'])}")
            print(f"  Memory: {process['memory_mb']:.1f} MB")
            print(f"  CPU: {process['cpu_percent']:.1f}%")
            print(f"  Threads: {process['threads']}")
            print()

            # Scheduler info
            scheduler = data['scheduler']
            print("⏰ Scheduler:")
            print(f"  Status: {'✅ Active' if scheduler['active'] else '❌ Inactive'}")
            print(f"  Active Jobs: {scheduler['jobs_count']}")
            print()

            # Database info
            db = data['database']
            if db.get('error'):
                print("💾 Database: ⚠️  Check needed")
            else:
                print(f"💾 Database: ✅ Connected")

            return True
        else:
            print(f"❌ Server Error: {data.get('error', 'Unknown')}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to TransformDash server")
        print(f"   Make sure the server is running at {BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def list_jobs():
    """List all scheduled jobs"""
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        data = response.json()

        if data['status'] == 'healthy':
            jobs = data['scheduler']['jobs']

            if not jobs:
                print("\n📭 No scheduled jobs")
                print("   Create schedules in the Web UI at http://localhost:8000")
                return

            print(f"\n⏰ Scheduled Jobs ({len(jobs)} active)")
            print("=" * 80)

            table_data = []
            for job in jobs:
                table_data.append([
                    job['id'],
                    job['name'][:40] + '...' if len(job['name']) > 40 else job['name'],
                    format_next_run(job.get('next_run_time')),
                    job.get('trigger', 'N/A')
                ])

            headers = ['Job ID', 'Name', 'Next Run', 'Trigger']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            print()

        else:
            print(f"❌ Server Error: {data.get('error', 'Unknown')}")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to TransformDash server")
        print(f"   Make sure the server is running at {BASE_URL}")
    except Exception as e:
        print(f"❌ Error: {e}")


def pause_job(job_id):
    """Pause a job"""
    try:
        response = requests.post(f"{BASE_URL}/api/jobs/{job_id}/pause")
        data = response.json()

        if response.status_code == 200:
            print(f"✅ Job {job_id} paused successfully")
        else:
            print(f"❌ Failed to pause job: {data.get('detail', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Error: {e}")


def resume_job(job_id):
    """Resume a paused job"""
    try:
        response = requests.post(f"{BASE_URL}/api/jobs/{job_id}/resume")
        data = response.json()

        if response.status_code == 200:
            print(f"✅ Job {job_id} resumed successfully")
        else:
            print(f"❌ Failed to resume job: {data.get('detail', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Error: {e}")


def job_details(job_id):
    """Get detailed information about a specific job"""
    try:
        response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        data = response.json()

        if response.status_code == 200:
            print(f"\n📋 Job Details: {job_id}")
            print("=" * 60)
            print(f"Name: {data['name']}")
            print(f"Next Run: {format_next_run(data.get('next_run_time'))}")
            print(f"Trigger: {data.get('trigger', 'N/A')}")
            if data.get('args'):
                print(f"Arguments: {data['args']}")
            if data.get('kwargs'):
                print(f"Keyword Arguments: {data['kwargs']}")
            print()
        else:
            print(f"❌ Job not found: {job_id}")

    except Exception as e:
        print(f"❌ Error: {e}")


def watch_status(interval=5):
    """Watch server status (refreshes every N seconds)"""
    import time
    import os

    try:
        while True:
            # Clear screen
            os.system('clear' if os.name == 'posix' else 'cls')

            # Display status
            get_status()

            # Display jobs
            list_jobs()

            print(f"\n⟳ Refreshing every {interval}s (Press Ctrl+C to stop)...")

            # Wait
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n👋 Stopped watching")


def main():
    parser = argparse.ArgumentParser(
        description='TransformDash CLI - Manage server, jobs, and agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status              Show server status
  %(prog)s jobs                List all scheduled jobs
  %(prog)s job <job_id>        Show job details
  %(prog)s pause <job_id>      Pause a job
  %(prog)s resume <job_id>     Resume a paused job
  %(prog)s watch               Watch server status (auto-refresh)
  %(prog)s watch --interval 10 Watch with custom refresh interval

For more information, visit http://localhost:8000
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Status command
    subparsers.add_parser('status', help='Show server status')

    # Jobs command
    subparsers.add_parser('jobs', help='List all scheduled jobs')

    # Job details command
    job_parser = subparsers.add_parser('job', help='Show detailed job information')
    job_parser.add_argument('job_id', help='Job ID to inspect')

    # Pause command
    pause_parser = subparsers.add_parser('pause', help='Pause a scheduled job')
    pause_parser.add_argument('job_id', help='Job ID to pause')

    # Resume command
    resume_parser = subparsers.add_parser('resume', help='Resume a paused job')
    resume_parser.add_argument('job_id', help='Job ID to resume')

    # Watch command
    watch_parser = subparsers.add_parser('watch', help='Watch server status (auto-refresh)')
    watch_parser.add_argument('--interval', type=int, default=5, help='Refresh interval in seconds (default: 5)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == 'status':
        get_status()
    elif args.command == 'jobs':
        list_jobs()
    elif args.command == 'job':
        job_details(args.job_id)
    elif args.command == 'pause':
        pause_job(args.job_id)
    elif args.command == 'resume':
        resume_job(args.job_id)
    elif args.command == 'watch':
        watch_status(args.interval)


if __name__ == '__main__':
    main()
