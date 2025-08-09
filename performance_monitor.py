"""
Performance Monitoring Tool with Real-time Tracking and Persistent Storage
Monitors CPU, Memory, Disk, Network, and Process details with graceful interruption handling

Author: Performance Monitoring System
Date: August 2025
"""

import psutil
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
import threading
import signal
import sys
import os
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')


class PerformanceMonitor:
    def __init__(self, csv_file="performance_log.csv", interval=1.0, max_records=10000):
        """
        Initialize Performance Monitor
        
        Args:
            csv_file: CSV file to store performance data
            interval: Monitoring interval in seconds
            max_records: Maximum records to keep in memory before flushing
        """
        self.csv_file = csv_file
        self.interval = interval
        self.max_records = max_records
        self.monitoring = False
        self.data_buffer = []
        self.start_time = None
        self.lock = threading.Lock()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize CSV file with headers if it doesn't exist
        self._initialize_csv()
        
        print("🚀 Performance Monitor Initialized")
        print(f"📁 Log file: {self.csv_file}")
        print(f"⏱️ Monitoring interval: {self.interval}s")
        print(f"📊 Max buffer size: {self.max_records} records")
    
    def _initialize_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            headers = [
                'timestamp', 'elapsed_time_sec', 'cpu_percent', 'cpu_count_logical',
                'cpu_count_physical', 'cpu_freq_current', 'memory_total_gb', 
                'memory_available_gb', 'memory_used_gb', 'memory_percent',
                'disk_total_gb', 'disk_used_gb', 'disk_free_gb', 'disk_percent',
                'network_bytes_sent', 'network_bytes_recv', 'network_packets_sent',
                'network_packets_recv', 'process_count', 'boot_time'
            ]
            df = pd.DataFrame(columns=headers)
            df.to_csv(self.csv_file, index=False)
            print(f"✅ Created new CSV file: {self.csv_file}")
        else:
            print(f"📄 Using existing CSV file: {self.csv_file}")
    
    def _signal_handler(self, signum, frame):
        """Handle interruption signals gracefully"""
        print(f"\n⚠️ Received signal {signum}. Saving data and shutting down gracefully...")
        self.stop_monitoring()
        self._flush_buffer()
        print("💾 All data saved successfully!")
        sys.exit(0)
    
    def _get_system_metrics(self):
        """Collect comprehensive system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)
            cpu_freq = psutil.cpu_freq()
            cpu_freq_current = cpu_freq.current if cpu_freq else 0
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_total_gb = memory.total / (1024**3)
            memory_available_gb = memory.available / (1024**3)
            memory_used_gb = memory.used / (1024**3)
            memory_percent = memory.percent
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_total_gb = disk.total / (1024**3)
            disk_used_gb = disk.used / (1024**3)
            disk_free_gb = disk.free / (1024**3)
            disk_percent = (disk.used / disk.total) * 100
            
            # Network metrics
            net_io = psutil.net_io_counters()
            network_bytes_sent = net_io.bytes_sent
            network_bytes_recv = net_io.bytes_recv
            network_packets_sent = net_io.packets_sent
            network_packets_recv = net_io.packets_recv
            
            # Process metrics
            process_count = len(psutil.pids())
            boot_time = psutil.boot_time()
            
            # Calculate elapsed time
            current_time = datetime.now()
            elapsed_time_sec = (current_time - self.start_time).total_seconds() if self.start_time else 0
            
            return {
                'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'elapsed_time_sec': round(elapsed_time_sec, 3),
                'cpu_percent': round(cpu_percent, 2),
                'cpu_count_logical': cpu_count_logical,
                'cpu_count_physical': cpu_count_physical,
                'cpu_freq_current': round(cpu_freq_current, 2),
                'memory_total_gb': round(memory_total_gb, 3),
                'memory_available_gb': round(memory_available_gb, 3),
                'memory_used_gb': round(memory_used_gb, 3),
                'memory_percent': round(memory_percent, 2),
                'disk_total_gb': round(disk_total_gb, 3),
                'disk_used_gb': round(disk_used_gb, 3),
                'disk_free_gb': round(disk_free_gb, 3),
                'disk_percent': round(disk_percent, 2),
                'network_bytes_sent': network_bytes_sent,
                'network_bytes_recv': network_bytes_recv,
                'network_packets_sent': network_packets_sent,
                'network_packets_recv': network_packets_recv,
                'process_count': process_count,
                'boot_time': boot_time
            }
        except Exception as e:
            print(f"❌ Error collecting metrics: {e}")
            return None
    
    def _flush_buffer(self):
        """Flush data buffer to CSV file"""
        if not self.data_buffer:
            return
        
        with self.lock:
            try:
                df_new = pd.DataFrame(self.data_buffer)
                df_new.to_csv(self.csv_file, mode='a', header=False, index=False)
                print(f"💾 Flushed {len(self.data_buffer)} records to {self.csv_file}")
                self.data_buffer.clear()
            except Exception as e:
                print(f"❌ Error flushing buffer: {e}")
    
    def _monitoring_loop(self):
        """Main monitoring loop running in separate thread"""
        while self.monitoring:
            try:
                metrics = self._get_system_metrics()
                if metrics:
                    with self.lock:
                        self.data_buffer.append(metrics)
                    
                    # Flush buffer if it reaches max size
                    if len(self.data_buffer) >= self.max_records:
                        self._flush_buffer()
                
                time.sleep(self.interval)
                
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                break
    
    def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring:
            print("⚠️ Monitoring is already running!")
            return
        
        self.monitoring = True
        self.start_time = datetime.now()
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        print(f"🔄 Performance monitoring started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to stop monitoring and save data")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self.monitoring:
            print("⚠️ Monitoring is not running!")
            return
        
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=2)
        
        self._flush_buffer()
        print("🛑 Performance monitoring stopped")
    
    def get_current_stats(self):
        """Get current system statistics"""
        metrics = self._get_system_metrics()
        if metrics:
            print("\n" + "="*60)
            print("CURRENT SYSTEM STATISTICS")
            print("="*60)
            print(f"CPU Usage: {metrics['cpu_percent']}%")
            print(f"Memory Usage: {metrics['memory_percent']}% ({metrics['memory_used_gb']:.2f} GB / {metrics['memory_total_gb']:.2f} GB)")
            print(f"Disk Usage: {metrics['disk_percent']:.2f}% ({metrics['disk_used_gb']:.2f} GB / {metrics['disk_total_gb']:.2f} GB)")
            print(f"Process Count: {metrics['process_count']}")
            print(f"Network Sent: {metrics['network_bytes_sent'] / (1024**2):.2f} MB")
            print(f"Network Received: {metrics['network_bytes_recv'] / (1024**2):.2f} MB")
        return metrics
    
    def create_performance_report(self, output_file="performance_report.html"):
        """Create comprehensive performance report with graphs"""
        try:
            # Load data from CSV
            if not os.path.exists(self.csv_file):
                print("❌ No performance data found. Start monitoring first!")
                return None, None
            
            df = pd.read_csv(self.csv_file)
            if df.empty:
                print("❌ No data in performance log!")
                return None, None
            
            print(f"📊 Creating performance report from {len(df)} records...")
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create visualizations
            plt.style.use('seaborn-v0_8')
            fig, axes = plt.subplots(3, 2, figsize=(16, 12))
            fig.suptitle('System Performance Monitoring Report', fontsize=16, fontweight='bold')
            
            # CPU Usage over time
            axes[0,0].plot(df['elapsed_time_sec'], df['cpu_percent'], color='red', linewidth=1)
            axes[0,0].set_title('CPU Usage Over Time')
            axes[0,0].set_xlabel('Time (seconds)')
            axes[0,0].set_ylabel('CPU Usage (%)')
            axes[0,0].grid(True, alpha=0.3)
            
            # Memory Usage over time
            axes[0,1].plot(df['elapsed_time_sec'], df['memory_percent'], color='blue', linewidth=1)
            axes[0,1].set_title('Memory Usage Over Time')
            axes[0,1].set_xlabel('Time (seconds)')
            axes[0,1].set_ylabel('Memory Usage (%)')
            axes[0,1].grid(True, alpha=0.3)
            
            # Disk Usage over time
            axes[1,0].plot(df['elapsed_time_sec'], df['disk_percent'], color='green', linewidth=1)
            axes[1,0].set_title('Disk Usage Over Time')
            axes[1,0].set_xlabel('Time (seconds)')
            axes[1,0].set_ylabel('Disk Usage (%)')
            axes[1,0].grid(True, alpha=0.3)
            
            # Process Count over time
            axes[1,1].plot(df['elapsed_time_sec'], df['process_count'], color='orange', linewidth=1)
            axes[1,1].set_title('Process Count Over Time')
            axes[1,1].set_xlabel('Time (seconds)')
            axes[1,1].set_ylabel('Number of Processes')
            axes[1,1].grid(True, alpha=0.3)
            
            # Network Traffic over time
            axes[2,0].plot(df['elapsed_time_sec'], df['network_bytes_sent']/(1024**2), label='Sent (MB)', color='purple')
            axes[2,0].plot(df['elapsed_time_sec'], df['network_bytes_recv']/(1024**2), label='Received (MB)', color='cyan')
            axes[2,0].set_title('Network Traffic Over Time')
            axes[2,0].set_xlabel('Time (seconds)')
            axes[2,0].set_ylabel('Data (MB)')
            axes[2,0].legend()
            axes[2,0].grid(True, alpha=0.3)
            
            # Resource Usage Distribution
            resource_data = [df['cpu_percent'].mean(), df['memory_percent'].mean(), df['disk_percent'].mean()]
            resource_labels = ['CPU', 'Memory', 'Disk']
            colors = ['red', 'blue', 'green']
            
            axes[2,1].bar(resource_labels, resource_data, color=colors, alpha=0.7)
            axes[2,1].set_title('Average Resource Usage')
            axes[2,1].set_ylabel('Usage (%)')
            axes[2,1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save plot
            plot_filename = f"performance_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
            plt.show()
            
            # Generate summary statistics
            print("\n" + "="*60)
            print("PERFORMANCE SUMMARY STATISTICS")
            print("="*60)
            
            summary_stats = {
                'Monitoring Duration (minutes)': df['elapsed_time_sec'].max() / 60,
                'Total Records': len(df),
                'Average CPU Usage (%)': df['cpu_percent'].mean(),
                'Peak CPU Usage (%)': df['cpu_percent'].max(),
                'Average Memory Usage (%)': df['memory_percent'].mean(),
                'Peak Memory Usage (%)': df['memory_percent'].max(),
                'Average Disk Usage (%)': df['disk_percent'].mean(),
                'Average Process Count': df['process_count'].mean(),
                'Peak Process Count': df['process_count'].max(),
                'Total Network Sent (MB)': (df['network_bytes_sent'].max() - df['network_bytes_sent'].min()) / (1024**2),
                'Total Network Received (MB)': (df['network_bytes_recv'].max() - df['network_bytes_recv'].min()) / (1024**2)
            }
            
            for key, value in summary_stats.items():
                if isinstance(value, float):
                    print(f"{key}: {value:.2f}")
                else:
                    print(f"{key}: {value}")
            
            # Export detailed report to CSV
            summary_df = pd.DataFrame([summary_stats])
            summary_filename = f"performance_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            summary_df.to_csv(summary_filename, index=False)
            
            print(f"\n✅ Performance report created successfully!")
            print(f"📊 Plot saved as: {plot_filename}")
            print(f"📋 Summary saved as: {summary_filename}")
            print(f"📁 Raw data: {self.csv_file}")
            
            return plot_filename, summary_filename
            
        except Exception as e:
            print(f"❌ Error creating performance report: {e}")
            return None, None


class AdvancedPerformanceMonitor(PerformanceMonitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0
        }
        self.alerts_log = []
        self.process_tracking = {}
    
    def set_alert_thresholds(self, cpu=80, memory=85, disk=90):
        """Set alert thresholds for system resources"""
        self.alert_thresholds = {
            'cpu_percent': cpu,
            'memory_percent': memory,
            'disk_percent': disk
        }
        print(f"🔔 Alert thresholds set: CPU>{cpu}%, Memory>{memory}%, Disk>{disk}%")
    
    def track_specific_process(self, process_name):
        """Track a specific process by name"""
        try:
            for process in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                if process_name.lower() in process.info['name'].lower():
                    pid = process.info['pid']
                    self.process_tracking[process_name] = pid
                    print(f"🎯 Now tracking process: {process_name} (PID: {pid})")
                    return True
            print(f"❌ Process '{process_name}' not found")
            return False
        except Exception as e:
            print(f"❌ Error tracking process: {e}")
            return False
    
    def get_process_metrics(self):
        """Get metrics for tracked processes"""
        process_metrics = {}
        to_remove = []
        
        for name, pid in self.process_tracking.items():
            try:
                process = psutil.Process(pid)
                process_metrics[name] = {
                    'cpu_percent': process.cpu_percent(),
                    'memory_percent': process.memory_percent(),
                    'memory_mb': process.memory_info().rss / (1024**2),
                    'status': process.status(),
                    'threads': process.num_threads(),
                    'files_open': len(process.open_files())
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process no longer exists or access denied
                to_remove.append(name)
                print(f"⚠️ Process {name} (PID: {pid}) no longer accessible")
        
        # Remove inaccessible processes
        for name in to_remove:
            del self.process_tracking[name]
        
        return process_metrics
    
    def check_alerts(self, metrics):
        """Check for resource usage alerts"""
        alerts = []
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for resource, threshold in self.alert_thresholds.items():
            if resource in metrics and metrics[resource] > threshold:
                alert = {
                    'timestamp': timestamp,
                    'resource': resource,
                    'value': metrics[resource],
                    'threshold': threshold,
                    'severity': 'HIGH' if metrics[resource] > threshold * 1.1 else 'MEDIUM'
                }
                alerts.append(alert)
                self.alerts_log.append(alert)
                
                print(f"🚨 ALERT: {resource.replace('_', ' ').title()} at {metrics[resource]:.1f}% (threshold: {threshold}%)")
        
        return alerts
    
    def _get_system_metrics(self):
        """Extended system metrics collection with alerts and process tracking"""
        metrics = super()._get_system_metrics()
        if metrics:
            # Check for alerts
            self.check_alerts(metrics)
            
            # Add process-specific metrics
            process_metrics = self.get_process_metrics()
            for name, proc_data in process_metrics.items():
                for key, value in proc_data.items():
                    metrics[f'process_{name}_{key}'] = value
        
        return metrics
    
    def show_real_time_dashboard(self, duration_seconds=30):
        """Show real-time dashboard for specified duration"""
        from matplotlib.animation import FuncAnimation
        from collections import deque
        
        print(f"📊 Starting real-time dashboard for {duration_seconds} seconds...")
        print("Close the plot window to stop monitoring")
        
        # Data storage for plotting
        timestamps = deque(maxlen=100)
        cpu_data = deque(maxlen=100)
        memory_data = deque(maxlen=100)
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle('Real-Time System Performance Dashboard', fontsize=14)
        
        def update_plot(frame):
            metrics = self._get_system_metrics()
            if metrics:
                timestamps.append(frame)
                cpu_data.append(metrics['cpu_percent'])
                memory_data.append(metrics['memory_percent'])
                
                # Clear and update CPU plot
                ax1.clear()
                ax1.plot(list(timestamps), list(cpu_data), 'r-', linewidth=2)
                ax1.set_title('CPU Usage (%)')
                ax1.set_ylim(0, 100)
                ax1.grid(True, alpha=0.3)
                ax1.axhline(y=self.alert_thresholds['cpu_percent'], color='red', linestyle='--', alpha=0.5)
                
                # Clear and update Memory plot
                ax2.clear()
                ax2.plot(list(timestamps), list(memory_data), 'b-', linewidth=2)
                ax2.set_title('Memory Usage (%)')
                ax2.set_ylim(0, 100)
                ax2.grid(True, alpha=0.3)
                ax2.axhline(y=self.alert_thresholds['memory_percent'], color='red', linestyle='--', alpha=0.5)
                
                plt.tight_layout()
        
        # Create animation
        ani = FuncAnimation(fig, update_plot, frames=range(duration_seconds), 
                          interval=1000, repeat=False)
        plt.show()
    
    def export_alerts_log(self, filename="alerts_log.csv"):
        """Export alerts log to CSV"""
        if self.alerts_log:
            alerts_df = pd.DataFrame(self.alerts_log)
            alerts_df.to_csv(filename, index=False)
            print(f"🔔 Exported {len(self.alerts_log)} alerts to {filename}")
        else:
            print("📋 No alerts to export")
    
    def get_performance_summary(self):
        """Get comprehensive performance summary"""
        if not os.path.exists(self.csv_file):
            print("❌ No performance data available")
            return
        
        df = pd.read_csv(self.csv_file)
        if df.empty:
            print("❌ No data in performance log")
            return
        
        print("\n" + "="*60)
        print("COMPREHENSIVE PERFORMANCE SUMMARY")
        print("="*60)
        
        duration_minutes = df['elapsed_time_sec'].max() / 60
        
        summary = {
            'Monitoring Period': f"{duration_minutes:.2f} minutes",
            'Total Data Points': len(df),
            'Avg CPU Usage': f"{df['cpu_percent'].mean():.2f}%",
            'Peak CPU Usage': f"{df['cpu_percent'].max():.2f}%",
            'CPU Usage Std Dev': f"{df['cpu_percent'].std():.2f}%",
            'Avg Memory Usage': f"{df['memory_percent'].mean():.2f}%",
            'Peak Memory Usage': f"{df['memory_percent'].max():.2f}%",
            'Memory Usage Std Dev': f"{df['memory_percent'].std():.2f}%",
            'Avg Disk Usage': f"{df['disk_percent'].mean():.2f}%",
            'Process Count Range': f"{df['process_count'].min()} - {df['process_count'].max()}",
            'Total Alerts': len(self.alerts_log)
        }
        
        for key, value in summary.items():
            print(f"{key:.<25} {value}")
        
        if self.alerts_log:
            print(f"\n🚨 RECENT ALERTS:")
            for alert in self.alerts_log[-5:]:  # Show last 5 alerts
                print(f"   {alert['timestamp']}: {alert['resource']} at {alert['value']:.1f}% (threshold: {alert['threshold']:.1f}%)")
        
        return summary


def create_monitor(monitor_type="basic", csv_file=None, interval=1.0, max_records=1000):
    """
    Factory function to create performance monitor instances
    
    Args:
        monitor_type: "basic" or "advanced"
        csv_file: CSV file for logging (auto-generated if None)
        interval: Monitoring interval in seconds
        max_records: Max records before flushing to CSV
    
    Returns:
        PerformanceMonitor or AdvancedPerformanceMonitor instance
    """
    if csv_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"performance_log_{timestamp}.csv"
    
    if monitor_type.lower() == "advanced":
        return AdvancedPerformanceMonitor(csv_file=csv_file, interval=interval, max_records=max_records)
    else:
        return PerformanceMonitor(csv_file=csv_file, interval=interval, max_records=max_records)


if __name__ == "__main__":
    print("🚀 Performance Monitor Module")
    print("="*50)
    print("Available classes:")
    print("• PerformanceMonitor - Basic monitoring")
    print("• AdvancedPerformanceMonitor - Advanced monitoring with alerts")
    print("\nFactory function:")
    print("• create_monitor(monitor_type, csv_file, interval, max_records)")
    print("\nExample usage:")
    print("from performance_monitor import create_monitor")
    print("monitor = create_monitor('advanced')")
    print("monitor.start_monitoring()")
