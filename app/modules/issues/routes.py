"""Issue tracker routes."""
import os
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.core.extensions import db
from app.modules.issues import issues_bp
from app.modules.issues.models import Issue, IssueComment, IssuePriority, IssueStatus
from app.core.diagnostics import generate_diagnostic_report


@issues_bp.route('/')
@login_required
def kanban_board():
    """Main kanban board view."""
    # Get all issues grouped by status
    issues_by_status = {}
    for status in IssueStatus:
        issues_by_status[status.value] = Issue.query.filter_by(status=status).order_by(
            Issue.priority.desc(), Issue.created_at.desc()
        ).all()
    
    # Get summary statistics
    stats = {
        'total': Issue.query.count(),
        'blockers': Issue.query.filter_by(priority=IssuePriority.BLOCKER).count(),
        'in_progress': Issue.query.filter_by(status=IssueStatus.IN_PROGRESS).count(),
        'open': Issue.query.filter(Issue.status != IssueStatus.DONE).count()
    }
    
    return render_template('issues/kanban.html', 
                         issues_by_status=issues_by_status,
                         stats=stats,
                         priorities=IssuePriority,
                         statuses=IssueStatus)


@issues_bp.route('/api/issues')
def api_issues():
    """API endpoint for issues."""
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    
    query = Issue.query
    
    if status_filter:
        query = query.filter_by(status=IssueStatus(status_filter))
    
    if priority_filter:
        query = query.filter_by(priority=IssuePriority(priority_filter))
    
    issues = query.order_by(Issue.priority.desc(), Issue.created_at.desc()).all()
    
    return jsonify({
        'issues': [issue.to_dict() for issue in issues]
    })


@issues_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_issue():
    """Create new issue."""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            issue = Issue(
                title=data['title'],
                description=data.get('description'),
                priority=IssuePriority(data['priority']),
                status=IssueStatus(data.get('status', 'backlog')),
                assignee=data.get('assignee'),
                reporter=current_user.name if hasattr(current_user, 'name') else 'user',
                endpoint=data.get('endpoint'),
                reproduction_steps=data.get('reproduction_steps'),
                acceptance_criteria=data.get('acceptance_criteria'),
                estimated_hours=float(data['estimated_hours']) if data.get('estimated_hours') else None
            )
            
            db.session.add(issue)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'issue': issue.to_dict()})
            else:
                flash(f'Issue #{issue.id} created successfully', 'success')
                return redirect(url_for('issues.kanban_board'))
                
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': str(e)}), 400
            else:
                flash(f'Error creating issue: {e}', 'error')
    
    return render_template('issues/create.html', 
                         priorities=IssuePriority,
                         statuses=IssueStatus)


@issues_bp.route('/<int:issue_id>')
@login_required
def view_issue(issue_id):
    """View issue details."""
    issue = Issue.query.get_or_404(issue_id)
    return render_template('issues/detail.html', issue=issue)


@issues_bp.route('/<int:issue_id>/update', methods=['POST'])
@login_required  
def update_issue(issue_id):
    """Update issue."""
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json() if request.is_json else request.form
    
    try:
        # Update fields
        if 'status' in data:
            old_status = issue.status
            issue.status = IssueStatus(data['status'])
            
            # Set resolved timestamp when moving to done
            if issue.status == IssueStatus.DONE and old_status != IssueStatus.DONE:
                issue.resolved_at = datetime.utcnow()
            elif issue.status != IssueStatus.DONE:
                issue.resolved_at = None
        
        if 'priority' in data:
            issue.priority = IssuePriority(data['priority'])
        
        if 'assignee' in data:
            issue.assignee = data['assignee']
        
        if 'title' in data:
            issue.title = data['title']
        
        if 'description' in data:
            issue.description = data['description']
        
        if 'acceptance_criteria' in data:
            issue.acceptance_criteria = data['acceptance_criteria']
        
        if 'estimated_hours' in data:
            issue.estimated_hours = float(data['estimated_hours']) if data['estimated_hours'] else None
            
        if 'actual_hours' in data:
            issue.actual_hours = float(data['actual_hours']) if data['actual_hours'] else None
        
        issue.updated_at = datetime.utcnow()
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'issue': issue.to_dict()})
        else:
            flash('Issue updated successfully', 'success')
            return redirect(url_for('issues.view_issue', issue_id=issue.id))
            
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        else:
            flash(f'Error updating issue: {e}', 'error')
            return redirect(url_for('issues.view_issue', issue_id=issue.id))


@issues_bp.route('/<int:issue_id>/comment', methods=['POST'])
@login_required
def add_comment(issue_id):
    """Add comment to issue."""
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json() if request.is_json else request.form
    
    try:
        comment = IssueComment(
            issue_id=issue.id,
            author=current_user.name if hasattr(current_user, 'name') else 'user',
            content=data['content']
        )
        
        db.session.add(comment)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True})
        else:
            flash('Comment added successfully', 'success')
            return redirect(url_for('issues.view_issue', issue_id=issue.id))
            
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        else:
            flash(f'Error adding comment: {e}', 'error')
            return redirect(url_for('issues.view_issue', issue_id=issue.id))


@issues_bp.route('/diagnostics')
@login_required
def diagnostics_report():
    """Show diagnostics report and create issues from errors."""
    if not current_app.debug and not current_app.config.get('DIAGNOSTICS_ENABLED'):
        flash('Diagnostics not enabled', 'error')
        return redirect(url_for('issues.kanban_board'))
    
    report = generate_diagnostic_report()
    
    return render_template('issues/diagnostics.html', report=report)


@issues_bp.route('/auto-create-from-errors', methods=['POST'])
@login_required
def auto_create_from_errors():
    """Automatically create issues from recent errors."""
    if not current_app.debug and not current_app.config.get('DIAGNOSTICS_ENABLED'):
        return jsonify({'error': 'Diagnostics not enabled'}), 403
    
    try:
        from app.core.diagnostics import error_metrics
        
        # Get recent errors that might need issues
        recent_errors = error_metrics.get_recent_errors(20)
        created_count = 0
        
        for error in recent_errors:
            # Only create issues for 500 errors or frequent 404s
            if error['details']['status_code'] == 500:
                # Check if similar issue already exists
                existing = Issue.query.filter_by(
                    endpoint=error['endpoint']
                ).filter(Issue.status != IssueStatus.DONE).first()
                
                if not existing:
                    issue = Issue.create_from_error(
                        error['details'], 
                        reporter='auto-diagnostics'
                    )
                    db.session.add(issue)
                    created_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'created_count': created_count,
            'message': f'Created {created_count} issues from recent errors'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500