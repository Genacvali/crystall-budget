/**
 * Kanban Board JavaScript
 * Drag & Drop functionality for issue management
 */

class KanbanBoard {
    constructor() {
        this.draggedElement = null;
        this.init();
    }
    
    init() {
        this.setupDragAndDrop();
        this.setupQuickActions();
        this.setupAutoRefresh();
    }
    
    setupDragAndDrop() {
        // Handle drag start
        document.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('issue-card')) {
                this.draggedElement = e.target;
                e.target.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/html', e.target.outerHTML);
            }
        });
        
        // Handle drag end
        document.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('issue-card')) {
                e.target.classList.remove('dragging');
                this.draggedElement = null;
            }
        });
        
        // Handle drag over columns
        document.querySelectorAll('.kanban-body').forEach(column => {
            column.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                column.classList.add('drag-over');
            });
            
            column.addEventListener('dragleave', (e) => {
                if (!column.contains(e.relatedTarget)) {
                    column.classList.remove('drag-over');
                }
            });
            
            column.addEventListener('drop', (e) => {
                e.preventDefault();
                column.classList.remove('drag-over');
                this.handleDrop(e, column);
            });
        });
    }
    
    async handleDrop(event, targetColumn) {
        if (!this.draggedElement) return;
        
        const issueId = this.draggedElement.dataset.issueId;
        const newStatus = targetColumn.id.replace('column-', '');
        const currentStatus = this.draggedElement.dataset.status;
        
        if (newStatus === currentStatus) return;
        
        // Optimistic update
        targetColumn.appendChild(this.draggedElement);
        this.draggedElement.dataset.status = newStatus;
        
        try {
            const response = await fetch(`/issues/${issueId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ status: newStatus })
            });
            
            if (!response.ok) {
                throw new Error('Failed to update issue status');
            }
            
            const result = await response.json();
            
            // Update badge counts
            this.updateColumnCounts();
            
            // Show success notification
            this.showNotification(`Issue #${issueId} moved to ${newStatus.replace('_', ' ')}`, 'success');
            
        } catch (error) {
            console.error('Error updating issue:', error);
            
            // Revert on error
            const originalColumn = document.getElementById(`column-${currentStatus}`);
            if (originalColumn) {
                originalColumn.appendChild(this.draggedElement);
                this.draggedElement.dataset.status = currentStatus;
            }
            
            this.showNotification('Failed to update issue status', 'error');
        }
    }
    
    updateColumnCounts() {
        document.querySelectorAll('.kanban-column').forEach(column => {
            const status = column.dataset.status;
            const count = column.querySelectorAll('.issue-card').length;
            const badge = column.querySelector('.badge');
            if (badge) {
                badge.textContent = count;
            }
        });
    }
    
    setupQuickActions() {
        // Double click to edit
        document.addEventListener('dblclick', (e) => {
            if (e.target.closest('.issue-card')) {
                const card = e.target.closest('.issue-card');
                const issueId = card.dataset.issueId;
                this.openQuickEdit(issueId);
            }
        });
        
        // Context menu for more actions
        document.addEventListener('contextmenu', (e) => {
            if (e.target.closest('.issue-card')) {
                e.preventDefault();
                const card = e.target.closest('.issue-card');
                const issueId = card.dataset.issueId;
                this.showContextMenu(e, issueId);
            }
        });
    }
    
    openQuickEdit(issueId) {
        // For now, redirect to detail page
        window.location.href = `/issues/${issueId}`;
    }
    
    showContextMenu(event, issueId) {
        // Create context menu
        const menu = document.createElement('div');
        menu.className = 'context-menu';
        menu.style.position = 'fixed';
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
        menu.style.background = 'white';
        menu.style.border = '1px solid #ccc';
        menu.style.borderRadius = '4px';
        menu.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        menu.style.zIndex = '1000';
        
        menu.innerHTML = `
            <div class="context-menu-item" onclick="window.location.href='/issues/${issueId}'">
                <i class="bi bi-eye me-2"></i>View Details
            </div>
            <div class="context-menu-item" onclick="kanban.editIssue(${issueId})">
                <i class="bi bi-pencil me-2"></i>Edit
            </div>
            <div class="context-menu-item text-danger" onclick="kanban.deleteIssue(${issueId})">
                <i class="bi bi-trash me-2"></i>Delete
            </div>
        `;
        
        document.body.appendChild(menu);
        
        // Remove menu on click outside
        setTimeout(() => {
            document.addEventListener('click', () => {
                if (menu.parentNode) {
                    menu.parentNode.removeChild(menu);
                }
            }, { once: true });
        }, 100);
    }
    
    async deleteIssue(issueId) {
        if (!confirm('Are you sure you want to delete this issue?')) {
            return;
        }
        
        try {
            const response = await fetch(`/issues/${issueId}/delete`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const card = document.querySelector(`[data-issue-id="${issueId}"]`);
                if (card) {
                    card.remove();
                    this.updateColumnCounts();
                }
                this.showNotification(`Issue #${issueId} deleted`, 'success');
            }
        } catch (error) {
            console.error('Error deleting issue:', error);
            this.showNotification('Failed to delete issue', 'error');
        }
    }
    
    setupAutoRefresh() {
        // Refresh every 5 minutes
        setInterval(() => {
            this.refreshBoard();
        }, 5 * 60 * 1000);
    }
    
    async refreshBoard() {
        try {
            const response = await fetch('/issues/api/issues');
            if (!response.ok) return;
            
            const data = await response.json();
            
            // Update issue cards with new data
            data.issues.forEach(issue => {
                const card = document.querySelector(`[data-issue-id="${issue.id}"]`);
                if (card) {
                    // Update card content if needed
                    this.updateCardContent(card, issue);
                }
            });
            
        } catch (error) {
            console.error('Error refreshing board:', error);
        }
    }
    
    updateCardContent(card, issueData) {
        // Update title, description, assignee, etc.
        const title = card.querySelector('.issue-title');
        if (title && title.textContent !== issueData.title) {
            title.textContent = issueData.title;
            card.classList.add('updated');
            setTimeout(() => card.classList.remove('updated'), 2000);
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '1050';
        notification.style.minWidth = '300px';
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.remove('show');
                setTimeout(() => notification.remove(), 150);
            }
        }, 3000);
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name=csrf-token]');
        return token ? token.getAttribute('content') : '';
    }
}

// CSS for context menu and notifications
const style = document.createElement('style');
style.textContent = `
    .context-menu-item {
        padding: 8px 16px;
        cursor: pointer;
        font-size: 14px;
        display: flex;
        align-items: center;
    }
    
    .context-menu-item:hover {
        background-color: #f8f9fa;
    }
    
    .issue-card.updated {
        outline: 2px solid var(--bs-info);
        outline-offset: 2px;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    
    .kanban-loading .spinner-border {
        animation: pulse 1s infinite;
    }
`;
document.head.appendChild(style);

// Initialize kanban board
let kanban;
document.addEventListener('DOMContentLoaded', () => {
    kanban = new KanbanBoard();
});

// Export for global access
window.kanban = kanban;