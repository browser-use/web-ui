import os
import json
import logging
import gradio as gr
from datetime import datetime
from typing import Dict, Any, List

from src.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)

APPLICATIONS_FILE = "./data/applications/applications.json"

def load_applications():
    """Load applications from file"""
    try:
        if os.path.exists(APPLICATIONS_FILE):
            with open(APPLICATIONS_FILE, 'r', encoding='utf-8') as f:
                applications = json.load(f)
            # Sort by date (most recent first)
            applications.sort(key=lambda x: x.get('applied_date', ''), reverse=True)
            return applications
        else:
            return []
    except Exception as e:
        logger.error(f"Error loading applications: {e}")
        return []

def format_applications_table(applications: List[Dict], status_filter: str = "All") -> tuple:
    """Format applications for display in a table"""
    if not applications:
        return [], "No applications found."
    
    # Filter by status if specified
    if status_filter != "All":
        applications = [app for app in applications if app.get('status', '').lower() == status_filter.lower()]
    
    # Create table data
    table_data = []
    for app in applications:
        # Format date for display
        applied_date = app.get('applied_date', '')
        if applied_date:
            try:
                date_obj = datetime.fromisoformat(applied_date.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_date = applied_date[:16] if len(applied_date) > 16 else applied_date
        else:
            formatted_date = 'Unknown'
        
        # Format status with emoji
        status = app.get('status', 'unknown')
        status_emoji = {
            'submitted': '✅ Submitted',
            'failed': '❌ Failed',
            'skipped': '⏭️ Skipped'
        }.get(status.lower(), f'❓ {status}')
        
        table_data.append([
            app.get('id', ''),
            app.get('company', 'Unknown'),
            app.get('job_title', 'Unknown'),
            status_emoji,
            formatted_date,
            app.get('job_url', '')[:50] + '...' if len(app.get('job_url', '')) > 50 else app.get('job_url', ''),
            app.get('notes', '')[:100] + '...' if len(app.get('notes', '')) > 100 else app.get('notes', '')
        ])
    
    # Generate summary
    total = len(applications)
    summary = f"Showing {len(table_data)} of {total} applications"
    
    return table_data, summary

def get_application_stats(applications: List[Dict]) -> Dict[str, int]:
    """Get statistics about applications"""
    stats = {
        'total': len(applications),
        'submitted': 0,
        'failed': 0,
        'skipped': 0
    }
    
    for app in applications:
        status = app.get('status', '').lower()
        if status in stats:
            stats[status] += 1
    
    return stats

def refresh_applications_display(status_filter: str):
    """Refresh the applications display with current filter"""
    applications = load_applications()
    table_data, summary = format_applications_table(applications, status_filter)
    stats = get_application_stats(applications)
    
    # Create stats display
    stats_text = f"""
    📊 **Application Statistics:**
    - **Total Applications:** {stats['total']}
    - **✅ Submitted:** {stats['submitted']}
    - **❌ Failed:** {stats['failed']}
    - **⏭️ Skipped:** {stats['skipped']}
    """
    
    return table_data, summary, stats_text

def delete_application(application_id: int):
    """Delete an application by ID"""
    try:
        applications = load_applications()
        # Filter out the application with the given ID
        updated_applications = [app for app in applications if app.get('id') != application_id]
        
        if len(updated_applications) < len(applications):
            # Save updated list
            os.makedirs(os.path.dirname(APPLICATIONS_FILE), exist_ok=True)
            with open(APPLICATIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(updated_applications, f, indent=2, ensure_ascii=False)
            return True, f"Application #{application_id} deleted successfully"
        else:
            return False, f"Application #{application_id} not found"
    except Exception as e:
        logger.error(f"Error deleting application: {e}")
        return False, f"Error deleting application: {str(e)}"

def clear_all_applications():
    """Clear all applications"""
    try:
        if os.path.exists(APPLICATIONS_FILE):
            os.remove(APPLICATIONS_FILE)
        return True, "All applications cleared successfully"
    except Exception as e:
        logger.error(f"Error clearing applications: {e}")
        return False, f"Error clearing applications: {str(e)}"

def create_application_history_tab(webui_manager: WebuiManager):
    """
    Creates an application history tab for viewing job application results.
    """
    tab_components = {}
    
    with gr.Column():
        gr.Markdown("## 📋 Job Application History")
        
        # Control panel
        with gr.Row():
            status_filter = gr.Dropdown(
                label="Filter by Status",
                choices=["All", "Submitted", "Failed", "Skipped"],
                value="All",
                scale=2
            )
            refresh_button = gr.Button("🔄 Refresh", variant="secondary", scale=1)
            clear_all_button = gr.Button("🗑️ Clear All", variant="stop", scale=1)
        
        # Statistics display
        stats_display = gr.Markdown(
            value="📊 **Application Statistics:** No applications yet.",
            visible=True
        )
        
        # Applications table
        applications_table = gr.Dataframe(
            headers=["ID", "Company", "Job Title", "Status", "Applied Date", "URL", "Notes"],
            datatype=["number", "str", "str", "str", "str", "str", "str"],
            col_count=(7, "fixed"),
            row_count=(10, "dynamic"),
            interactive=False,
            wrap=True,
            label="Applications"
        )
        
        summary_text = gr.Textbox(
            label="Summary",
            value="No applications loaded yet.",
            interactive=False,
            max_lines=1
        )
        
        # Delete specific application
        with gr.Row():
            delete_id_input = gr.Number(
                label="Application ID to Delete",
                minimum=1,
                precision=0,
                scale=3
            )
            delete_button = gr.Button("🗑️ Delete Application", variant="secondary", scale=1)
        
        # Status message
        status_message = gr.Textbox(
            label="Status",
            interactive=False,
            visible=False
        )

    # Store components
    tab_components.update({
        "status_filter": status_filter,
        "refresh_button": refresh_button,
        "clear_all_button": clear_all_button,
        "stats_display": stats_display,
        "applications_table": applications_table,
        "summary_text": summary_text,
        "delete_id_input": delete_id_input,
        "delete_button": delete_button,
        "status_message": status_message
    })

    webui_manager.add_components("application_history", tab_components)

    # Event handlers
    def on_refresh(status_filter_value):
        """Handle refresh button click"""
        table_data, summary, stats_text = refresh_applications_display(status_filter_value)
        return (
            gr.update(value=table_data),  # applications_table
            gr.update(value=summary),     # summary_text
            gr.update(value=stats_text),  # stats_display
            gr.update(value="Data refreshed", visible=True)  # status_message
        )

    def on_status_filter_change(status_filter_value):
        """Handle status filter change"""
        table_data, summary, stats_text = refresh_applications_display(status_filter_value)
        return (
            gr.update(value=table_data),  # applications_table
            gr.update(value=summary),     # summary_text
            gr.update(value=stats_text)   # stats_display
        )

    def on_delete_application(app_id):
        """Handle delete application"""
        if not app_id:
            return (
                gr.update(),  # applications_table
                gr.update(),  # summary_text
                gr.update(),  # stats_display
                gr.update(value="Please enter a valid Application ID", visible=True)  # status_message
            )
        
        success, message = delete_application(int(app_id))
        if success:
            # Refresh the display after successful deletion
            table_data, summary, stats_text = refresh_applications_display("All")
            return (
                gr.update(value=table_data),  # applications_table
                gr.update(value=summary),     # summary_text
                gr.update(value=stats_text),  # stats_display
                gr.update(value=message, visible=True)  # status_message
            )
        else:
            return (
                gr.update(),  # applications_table
                gr.update(),  # summary_text
                gr.update(),  # stats_display
                gr.update(value=message, visible=True)  # status_message
            )

    def on_clear_all():
        """Handle clear all applications"""
        success, message = clear_all_applications()
        if success:
            return (
                gr.update(value=[]),  # applications_table
                gr.update(value="No applications found."),  # summary_text
                gr.update(value="📊 **Application Statistics:** No applications yet."),  # stats_display
                gr.update(value=message, visible=True)  # status_message
            )
        else:
            return (
                gr.update(),  # applications_table
                gr.update(),  # summary_text
                gr.update(),  # stats_display
                gr.update(value=message, visible=True)  # status_message
            )

    # Connect event handlers
    refresh_button.click(
        fn=on_refresh,
        inputs=[status_filter],
        outputs=[applications_table, summary_text, stats_display, status_message]
    )

    status_filter.change(
        fn=on_status_filter_change,
        inputs=[status_filter],
        outputs=[applications_table, summary_text, stats_display]
    )

    delete_button.click(
        fn=on_delete_application,
        inputs=[delete_id_input],
        outputs=[applications_table, summary_text, stats_display, status_message]
    )

    clear_all_button.click(
        fn=on_clear_all,
        inputs=[],
        outputs=[applications_table, summary_text, stats_display, status_message]
    )

    # Initialize with empty data - will be loaded when user refreshes
    # The initial refresh can be triggered by the user 