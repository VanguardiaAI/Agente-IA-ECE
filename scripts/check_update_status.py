#!/usr/bin/env python
"""
Check the status of automatic updates
Shows last update time, results, and next scheduled update
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json
import subprocess

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_last_update_status():
    """Get the last update status from the status file"""
    status_file = Path("/opt/eva/logs/update_status.txt")
    
    if not status_file.exists():
        return None
    
    try:
        with open(status_file, 'r') as f:
            line = f.readline().strip()
            if line:
                parts = line.split('|', 2)
                if len(parts) >= 3:
                    return {
                        'timestamp': parts[0],
                        'status': parts[1],
                        'details': eval(parts[2])  # Safe since we control the file
                    }
    except Exception as e:
        print(f"Error reading status file: {e}")
    
    return None

def get_next_update_time():
    """Calculate when the next update will run"""
    now = datetime.now()
    
    # Update times: 6:00 AM and 6:00 PM
    morning = now.replace(hour=6, minute=0, second=0, microsecond=0)
    evening = now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    if now < morning:
        return morning
    elif now < evening:
        return evening
    else:
        # Next morning
        return (morning + timedelta(days=1))

def get_cron_jobs():
    """Get Eva-related cron jobs"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            eva_jobs = [line for line in lines if 'eva' in line.lower() and 'auto_update' in line]
            return eva_jobs
    except Exception:
        pass
    return []

def check_log_files():
    """Check recent log files"""
    log_dir = Path("/opt/eva/logs")
    if not log_dir.exists():
        return []
    
    log_files = list(log_dir.glob("auto_update_*.log"))
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    return log_files[:5]  # Last 5 log files

def format_time_ago(timestamp_str):
    """Format how long ago an update occurred"""
    try:
        update_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - update_time
        
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    except:
        return "unknown time ago"

def main():
    """Main status check function"""
    print("🔍 Eva Auto Update Status Check")
    print("=" * 50)
    
    # Check last update
    last_update = get_last_update_status()
    if last_update:
        print(f"\n📊 Last Update:")
        print(f"   Time: {last_update['timestamp']} ({format_time_ago(last_update['timestamp'])})")
        print(f"   Status: {'✅ SUCCESS' if last_update['status'] == 'SUCCESS' else '❌ FAILED'}")
        
        details = last_update['details']
        if 'products' in details and details['products']:
            print(f"\n   Products:")
            print(f"     - Added: {details['products'].get('added', 0)}")
            print(f"     - Updated: {details['products'].get('updated', 0)}")
            print(f"     - Deleted: {details['products'].get('deleted', 0)}")
            print(f"     - Errors: {details['products'].get('errors', 0)}")
        
        print(f"\n   Knowledge Base: {'✅ Updated' if details.get('knowledge_success') else '❌ Failed'}")
    else:
        print("\n⚠️  No update status found. Updates may not have run yet.")
    
    # Next update time
    next_update = get_next_update_time()
    time_until = next_update - datetime.now()
    hours, remainder = divmod(time_until.seconds, 3600)
    minutes = remainder // 60
    
    print(f"\n⏰ Next Update:")
    print(f"   Scheduled for: {next_update.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Time until: {hours}h {minutes}m")
    
    # Check cron jobs
    cron_jobs = get_cron_jobs()
    print(f"\n📅 Configured Cron Jobs:")
    if cron_jobs:
        for job in cron_jobs:
            print(f"   {job}")
    else:
        print("   ⚠️  No Eva update cron jobs found!")
    
    # Check log files
    log_files = check_log_files()
    print(f"\n📁 Recent Log Files:")
    if log_files:
        for log_file in log_files:
            size = log_file.stat().st_size / 1024  # KB
            print(f"   {log_file.name} ({size:.1f} KB)")
    else:
        print("   No log files found")
    
    print("\n" + "=" * 50)
    print("💡 Tips:")
    print("   - View logs: tail -f /opt/eva/logs/auto_update_*.log")
    print("   - Run update manually: python scripts/auto_update.py")
    print("   - Setup cron jobs: ./scripts/setup_auto_updates.sh")

if __name__ == "__main__":
    main()