#!/bin/bash
# Quick migration wrapper script

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         CrystalBudget Database Migration Tool             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if database exists
if [ ! -f "instance/budget.db" ]; then
    echo "⚠️  Database not found at instance/budget.db"
    echo ""
    echo "Please copy your production database first:"
    echo "  cp /path/to/prod/budget.db instance/budget.db"
    echo ""
    exit 1
fi

# Check database size
DB_SIZE=$(du -h instance/budget.db | cut -f1)
echo "📊 Database size: $DB_SIZE"
echo ""

# Run migration
python3 migrate_prod_db.py "$@"

# Check if migration succeeded
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Migration successful!"
    echo ""
    echo "Next steps:"
    echo "  1. Test the application: python app.py"
    echo "  2. Check that everything works correctly"
    echo "  3. Deploy to production"
    echo ""
else
    echo ""
    echo "❌ Migration failed!"
    echo "Your original database is safe in the backup file."
    echo ""
    exit 1
fi
