# Modal System Rollback Runbook

## Overview
This document provides step-by-step procedures for rolling back the unified modal system to the legacy modal system in case of issues during the deployment.

## Quick Rollback (Emergency)

### Option 1: Environment Variable
```bash
# Disable modal system completely
export MODAL_SYSTEM_ENABLED=false

# Restart application
sudo systemctl restart crystalbudget
```

### Option 2: Canary Percentage Reduction  
```bash
# Reduce rollout to 0% (legacy for all users)
export MODAL_SYSTEM_CANARY_PCT=0

# Restart application
sudo systemctl restart crystalbudget
```

### Option 3: Configuration File
```bash
# Edit configuration temporarily
echo "MODAL_SYSTEM_ENABLED=false" >> /opt/crystall-budget/.env

# Restart application
sudo systemctl restart crystalbudget
```

## Monitoring During Rollback

### Check Application Health
```bash
# Health check endpoint
curl -f http://localhost:5000/healthz

# Monitor logs
sudo journalctl -u crystalbudget -f --since "5 minutes ago"

# Check monitoring dashboard
# Visit: http://localhost:5000/monitoring/modal-system
```

### Key Metrics to Monitor
- **Error Rate**: Should decrease below 5%
- **Average Load Time**: Should improve to <250ms
- **Bundle Distribution**: Should shift to 100% legacy
- **User Complaints**: Monitor support channels

## Gradual Rollback Procedure

### Step 1: Reduce Canary Percentage
```bash
# Reduce to 50% first
export MODAL_SYSTEM_CANARY_PCT=50
sudo systemctl restart crystalbudget

# Wait 5 minutes, monitor metrics

# Reduce to 20%  
export MODAL_SYSTEM_CANARY_PCT=20
sudo systemctl restart crystalbudget

# Wait 5 minutes, monitor metrics

# Reduce to 0%
export MODAL_SYSTEM_CANARY_PCT=0
sudo systemctl restart crystalbudget
```

### Step 2: Full Disable
```bash
# Completely disable modal system
export MODAL_SYSTEM_ENABLED=false
sudo systemctl restart crystalbudget
```

## Validation After Rollback

### 1. Functional Testing
- [ ] Login page loads correctly
- [ ] Dashboard displays without modal system
- [ ] Expense creation works with legacy system
- [ ] Income management works with legacy system  
- [ ] Goal management works with legacy system
- [ ] Settings page functions properly

### 2. Performance Validation
```bash
# Test key endpoints response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5000/
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5000/expenses
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5000/goals
```

Create `curl-format.txt`:
```
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
```

### 3. Bundle Verification
```bash
# Verify only legacy bundles are served
curl -s http://localhost:5000/ | grep -c "modal.css" # Should be 0
curl -s http://localhost:5000/ | grep -c "modals.js" # Should be 0
```

## Troubleshooting Common Issues

### Issue: Application Won't Start
```bash
# Check logs
sudo journalctl -u crystalbudget --no-pager | tail -20

# Verify configuration
python -c "from app import create_app; app = create_app('production'); print('OK')"

# Reset to known good state
git checkout HEAD -- app/core/config.py
sudo systemctl restart crystalbudget
```

### Issue: Some Users Still See Modal System
```bash
# Clear application cache
redis-cli FLUSHALL  # If using Redis
# Or restart app to clear SimpleCache
sudo systemctl restart crystalbudget

# Verify feature flag settings
python -c "
from app import create_app
from app.core.features import is_modal_system_enabled
app = create_app('production')
with app.app_context():
    print(f'Modal enabled: {is_modal_system_enabled()}')
"
```

### Issue: Performance Still Poor
```bash
# Clear browser cache for affected users
# Check if modal CSS/JS files are still being served
curl -I http://localhost:5000/static/css/components/modal.css
curl -I http://localhost:5000/static/js/modals.js

# Should return 404 or not be requested
```

## Communication Plan

### Internal Team
1. **Immediate**: Notify dev team via Slack/Teams
2. **5 minutes**: Update incident status page
3. **15 minutes**: Send email to stakeholders

### User Communication  
1. **If user-facing issues**: Deploy maintenance banner
2. **Social media**: Post brief status if widespread impact
3. **Follow-up**: Explain resolution once complete

## Post-Rollback Actions

### 1. Root Cause Analysis
- [ ] Review monitoring data during incident
- [ ] Analyze error logs and patterns
- [ ] Identify what went wrong with rollout
- [ ] Document lessons learned

### 2. Environment Cleanup
```bash
# Remove temporary environment variables
unset MODAL_SYSTEM_ENABLED
unset MODAL_SYSTEM_CANARY_PCT

# Clean up any temporary files
rm -f /opt/crystall-budget/.env.rollback
```

### 3. Prepare for Next Attempt
- [ ] Fix identified issues
- [ ] Update feature flag logic if needed
- [ ] Plan improved rollout strategy
- [ ] Schedule new deployment window

## Environment Variables Reference

| Variable | Values | Description |
|----------|---------|-------------|
| `MODAL_SYSTEM_ENABLED` | `true`/`false` | Enable/disable modal system globally |
| `MODAL_SYSTEM_DEBUG` | `true`/`false` | Enable debug logging |  
| `MODAL_SYSTEM_CANARY_PCT` | `0-100` | Percentage of users getting new system |

## Contact Information

**Primary Escalation**: Developer Team Lead
**Secondary**: DevOps Engineer  
**Emergency**: Production Support Hotline

## Testing the Rollback Procedure

Before any production deployment, test this rollback procedure in staging:

```bash
# In staging environment
export MODAL_SYSTEM_ENABLED=true
export MODAL_SYSTEM_CANARY_PCT=100
sudo systemctl restart crystalbudget-staging

# Verify unified system is active
# Then test rollback
export MODAL_SYSTEM_ENABLED=false
sudo systemctl restart crystalbudget-staging

# Verify legacy system is active
```

---
**Document Version**: 1.0  
**Last Updated**: 2024-09-29  
**Next Review**: After successful modal system deployment