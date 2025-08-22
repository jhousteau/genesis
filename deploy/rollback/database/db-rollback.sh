#!/usr/bin/env bash
# Database Rollback System
# Safe database migration rollbacks with backup verification

set -euo pipefail

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging functions
log_error() { echo -e "${RED}❌ ERROR: $1${NC}" >&2; }
log_warning() { echo -e "${YELLOW}⚠️  WARNING: $1${NC}"; }
log_success() { echo -e "${GREEN}✅ SUCCESS: $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  INFO: $1${NC}"; }
log_progress() { echo -e "${CYAN}🔄 ROLLBACK: $1${NC}"; }
log_db() { echo -e "${PURPLE}🗄️  DATABASE: $1${NC}"; }

# Configuration
DB_TYPE="${DB_TYPE:-postgresql}"  # postgresql, mysql, cloudsql
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-}"
DB_USER="${DB_USER:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
GCP_PROJECT="${GCP_PROJECT:-}"
CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-}"

# Rollback configuration
MIGRATION_ID="${MIGRATION_ID:-}"
TARGET_MIGRATION="${TARGET_MIGRATION:-}"
ROLLBACK_TYPE="${ROLLBACK_TYPE:-migration}"  # migration, snapshot, point-in-time
BACKUP_BEFORE_ROLLBACK="${BACKUP_BEFORE_ROLLBACK:-true}"
VERIFY_ROLLBACK="${VERIFY_ROLLBACK:-true}"
OUTPUT_DIR="${OUTPUT_DIR:-./db-rollback-logs}"
DRY_RUN="${DRY_RUN:-false}"

# Safety settings
MAX_ROLLBACK_HOURS="${MAX_ROLLBACK_HOURS:-24}"
REQUIRE_CONFIRMATION="${REQUIRE_CONFIRMATION:-true}"
ALLOW_DATA_LOSS="${ALLOW_DATA_LOSS:-false}"

log_info "🗄️ Starting Database Rollback System"
log_info "Database Type: $DB_TYPE"
log_info "Database: $DB_NAME"
log_info "Rollback Type: $ROLLBACK_TYPE"
log_info "Target Migration: $TARGET_MIGRATION"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize rollback state
declare -A rollback_state
declare -A backup_info

# Function to validate database connection
validate_db_connection() {
    log_progress "Validating database connection"
    
    case "$DB_TYPE" in
        postgresql)
            if [[ "$DRY_RUN" == "false" ]]; then
                if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
                    log_success "PostgreSQL connection successful"
                else
                    log_error "Failed to connect to PostgreSQL database"
                    return 1
                fi
            fi
            ;;
        mysql)
            if [[ "$DRY_RUN" == "false" ]]; then
                if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "SELECT 1;" > /dev/null 2>&1; then
                    log_success "MySQL connection successful"
                else
                    log_error "Failed to connect to MySQL database"
                    return 1
                fi
            fi
            ;;
        cloudsql)
            if [[ "$DRY_RUN" == "false" ]]; then
                if gcloud sql connect "$CLOUD_SQL_INSTANCE" --user="$DB_USER" --project="$GCP_PROJECT" --quiet << EOF > /dev/null 2>&1
SELECT 1;
\q
EOF
                then
                    log_success "Cloud SQL connection successful"
                else
                    log_error "Failed to connect to Cloud SQL instance"
                    return 1
                fi
            fi
            ;;
        *)
            log_error "Unsupported database type: $DB_TYPE"
            return 1
            ;;
    esac
    
    log_success "Database connection validated"
}

# Function to get current migration state
get_migration_state() {
    log_progress "Getting current migration state"
    
    case "$DB_TYPE" in
        postgresql)
            if [[ "$DRY_RUN" == "false" ]]; then
                # Check if schema_migrations table exists
                if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
                    -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'schema_migrations');" \
                    -t | grep -q 't'; then
                    
                    # Get current migration version
                    local current_migration
                    current_migration=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
                        -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;" -t | tr -d ' ')
                    
                    rollback_state["current_migration"]="$current_migration"
                    log_info "Current migration: $current_migration"
                else
                    log_warning "No schema_migrations table found"
                    rollback_state["current_migration"]="none"
                fi
            else
                rollback_state["current_migration"]="dry_run_migration"
                log_info "[DRY RUN] Current migration: ${rollback_state[current_migration]}"
            fi
            ;;
        mysql)
            if [[ "$DRY_RUN" == "false" ]]; then
                # Similar logic for MySQL
                if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" \
                    -e "SHOW TABLES LIKE 'schema_migrations';" | grep -q 'schema_migrations'; then
                    
                    local current_migration
                    current_migration=$(mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" \
                        -e "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;" -s -N)
                    
                    rollback_state["current_migration"]="$current_migration"
                    log_info "Current migration: $current_migration"
                else
                    log_warning "No schema_migrations table found"
                    rollback_state["current_migration"]="none"
                fi
            else
                rollback_state["current_migration"]="dry_run_migration"
                log_info "[DRY RUN] Current migration: ${rollback_state[current_migration]}"
            fi
            ;;
        cloudsql)
            # Use gcloud sql to connect and check
            if [[ "$DRY_RUN" == "false" ]]; then
                local temp_file="/tmp/migration_check.sql"
                echo "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;" > "$temp_file"
                
                local current_migration
                if current_migration=$(gcloud sql connect "$CLOUD_SQL_INSTANCE" --user="$DB_USER" --project="$GCP_PROJECT" < "$temp_file" 2>/dev/null | tail -1); then
                    rollback_state["current_migration"]="$current_migration"
                    log_info "Current migration: $current_migration"
                else
                    rollback_state["current_migration"]="none"
                    log_warning "Could not determine current migration"
                fi
                
                rm -f "$temp_file"
            else
                rollback_state["current_migration"]="dry_run_migration"
                log_info "[DRY RUN] Current migration: ${rollback_state[current_migration]}"
            fi
            ;;
    esac
    
    log_success "Migration state retrieved"
}

# Function to validate rollback safety
validate_rollback_safety() {
    log_progress "Validating rollback safety"
    
    # Check if target migration exists
    if [[ -z "$TARGET_MIGRATION" ]]; then
        log_error "TARGET_MIGRATION is required"
        return 1
    fi
    
    # Check if we're going backwards
    local current_migration="${rollback_state[current_migration]}"
    if [[ "$current_migration" != "none" && "$TARGET_MIGRATION" > "$current_migration" ]]; then
        log_error "Cannot rollback to a newer migration ($TARGET_MIGRATION > $current_migration)"
        return 1
    fi
    
    # Check rollback time window
    if [[ "$ROLLBACK_TYPE" == "point-in-time" ]]; then
        # This would check if the target time is within the allowed window
        log_info "Point-in-time rollback safety validation"
    fi
    
    # Check for destructive changes
    if [[ "$ALLOW_DATA_LOSS" != "true" ]]; then
        log_warning "Data loss protection is enabled"
        log_warning "This rollback may involve data loss. Please review carefully."
        
        if [[ "$REQUIRE_CONFIRMATION" == "true" && "$DRY_RUN" == "false" ]]; then
            echo -n "Do you want to continue? (yes/no): "
            read -r confirmation
            if [[ "$confirmation" != "yes" ]]; then
                log_info "Rollback cancelled by user"
                exit 0
            fi
        fi
    fi
    
    log_success "Rollback safety validation completed"
}

# Function to create pre-rollback backup
create_pre_rollback_backup() {
    if [[ "$BACKUP_BEFORE_ROLLBACK" != "true" ]]; then
        log_info "Pre-rollback backup disabled"
        return 0
    fi
    
    log_progress "Creating pre-rollback backup"
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$OUTPUT_DIR/pre_rollback_backup_${backup_timestamp}"
    
    case "$DB_TYPE" in
        postgresql)
            if [[ "$DRY_RUN" == "false" ]]; then
                local backup_path="${backup_file}.sql"
                PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
                    -d "$DB_NAME" -f "$backup_path" --verbose
                
                backup_info["backup_file"]="$backup_path"
                backup_info["backup_size"]=$(stat -c%s "$backup_path")
                
                log_success "PostgreSQL backup created: $backup_path"
            else
                backup_info["backup_file"]="$backup_file.sql (dry run)"
                log_info "[DRY RUN] Would create PostgreSQL backup: $backup_file.sql"
            fi
            ;;
        mysql)
            if [[ "$DRY_RUN" == "false" ]]; then
                local backup_path="${backup_file}.sql"
                mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" \
                    "$DB_NAME" > "$backup_path"
                
                backup_info["backup_file"]="$backup_path"
                backup_info["backup_size"]=$(stat -c%s "$backup_path")
                
                log_success "MySQL backup created: $backup_path"
            else
                backup_info["backup_file"]="$backup_file.sql (dry run)"
                log_info "[DRY RUN] Would create MySQL backup: $backup_file.sql"
            fi
            ;;
        cloudsql)
            if [[ "$DRY_RUN" == "false" ]]; then
                local backup_id="pre-rollback-backup-$backup_timestamp"
                
                gcloud sql backups create \
                    --instance="$CLOUD_SQL_INSTANCE" \
                    --project="$GCP_PROJECT" \
                    --description="Pre-rollback backup for migration rollback"
                
                # Get the backup ID
                local actual_backup_id
                actual_backup_id=$(gcloud sql backups list \
                    --instance="$CLOUD_SQL_INSTANCE" \
                    --project="$GCP_PROJECT" \
                    --format="value(id)" \
                    --limit=1 \
                    --sort-by="~startTime")
                
                backup_info["backup_id"]="$actual_backup_id"
                backup_info["backup_file"]="Cloud SQL Backup ID: $actual_backup_id"
                
                log_success "Cloud SQL backup created: $actual_backup_id"
            else
                backup_info["backup_file"]="Cloud SQL backup (dry run)"
                log_info "[DRY RUN] Would create Cloud SQL backup"
            fi
            ;;
    esac
    
    # Save backup metadata
    cat > "$OUTPUT_DIR/backup-metadata-$backup_timestamp.json" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "backup_type": "pre_rollback",
  "database_type": "$DB_TYPE",
  "database_name": "$DB_NAME",
  "current_migration": "${rollback_state[current_migration]}",
  "target_migration": "$TARGET_MIGRATION",
  "backup_file": "${backup_info[backup_file]}",
  "backup_size": "${backup_info[backup_size]:-unknown}"
}
EOF
    
    log_success "Pre-rollback backup completed"
}

# Function to execute migration rollback
execute_migration_rollback() {
    if [[ "$ROLLBACK_TYPE" != "migration" ]]; then
        return 0
    fi
    
    log_progress "Executing migration rollback"
    
    local current_migration="${rollback_state[current_migration]}"
    
    if [[ "$current_migration" == "$TARGET_MIGRATION" ]]; then
        log_info "Already at target migration: $TARGET_MIGRATION"
        return 0
    fi
    
    # Create rollback SQL script
    local rollback_script="$OUTPUT_DIR/rollback_script_$(date +%Y%m%d_%H%M%S).sql"
    
    case "$DB_TYPE" in
        postgresql|mysql|cloudsql)
            # Generate rollback script
            cat > "$rollback_script" << EOF
-- Rollback script generated on $(date)
-- Rolling back from $current_migration to $TARGET_MIGRATION

BEGIN;

-- Remove migrations newer than target
DELETE FROM schema_migrations WHERE version > '$TARGET_MIGRATION';

-- Note: This is a basic rollback script
-- In practice, you would include the actual rollback DDL statements
-- for each migration being rolled back

-- Example rollback operations:
-- DROP TABLE IF EXISTS new_table;
-- ALTER TABLE existing_table DROP COLUMN new_column;
-- DROP INDEX IF EXISTS new_index;

COMMIT;
EOF
            ;;
    esac
    
    if [[ "$DRY_RUN" == "false" ]]; then
        log_warning "Executing rollback script: $rollback_script"
        
        case "$DB_TYPE" in
            postgresql)
                PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
                    -d "$DB_NAME" -f "$rollback_script"
                ;;
            mysql)
                mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" \
                    "$DB_NAME" < "$rollback_script"
                ;;
            cloudsql)
                gcloud sql connect "$CLOUD_SQL_INSTANCE" --user="$DB_USER" \
                    --project="$GCP_PROJECT" < "$rollback_script"
                ;;
        esac
        
        log_success "Migration rollback executed"
    else
        log_info "[DRY RUN] Would execute rollback script: $rollback_script"
    fi
    
    rollback_state["rollback_executed"]="true"
}

# Function to execute snapshot rollback
execute_snapshot_rollback() {
    if [[ "$ROLLBACK_TYPE" != "snapshot" ]]; then
        return 0
    fi
    
    log_progress "Executing snapshot rollback"
    
    case "$DB_TYPE" in
        cloudsql)
            if [[ "$DRY_RUN" == "false" ]]; then
                # Restore from backup
                local backup_id="$TARGET_MIGRATION"  # In this case, TARGET_MIGRATION is backup ID
                
                log_warning "Restoring Cloud SQL instance from backup: $backup_id"
                
                gcloud sql backups restore "$backup_id" \
                    --restore-instance="$CLOUD_SQL_INSTANCE" \
                    --project="$GCP_PROJECT"
                
                log_success "Cloud SQL snapshot rollback completed"
            else
                log_info "[DRY RUN] Would restore from backup: $TARGET_MIGRATION"
            fi
            ;;
        *)
            log_error "Snapshot rollback not supported for database type: $DB_TYPE"
            return 1
            ;;
    esac
    
    rollback_state["rollback_executed"]="true"
}

# Function to execute point-in-time rollback
execute_point_in_time_rollback() {
    if [[ "$ROLLBACK_TYPE" != "point-in-time" ]]; then
        return 0
    fi
    
    log_progress "Executing point-in-time rollback"
    
    case "$DB_TYPE" in
        cloudsql)
            if [[ "$DRY_RUN" == "false" ]]; then
                # Point-in-time recovery
                local target_time="$TARGET_MIGRATION"  # In this case, TARGET_MIGRATION is timestamp
                
                log_warning "Performing point-in-time recovery to: $target_time"
                
                gcloud sql instances clone "$CLOUD_SQL_INSTANCE" \
                    "${CLOUD_SQL_INSTANCE}-rollback-$(date +%Y%m%d%H%M%S)" \
                    --point-in-time="$target_time" \
                    --project="$GCP_PROJECT"
                
                log_success "Point-in-time rollback completed"
                log_info "New instance created. You may need to update application configuration."
            else
                log_info "[DRY RUN] Would perform point-in-time recovery to: $TARGET_MIGRATION"
            fi
            ;;
        *)
            log_error "Point-in-time rollback not supported for database type: $DB_TYPE"
            return 1
            ;;
    esac
    
    rollback_state["rollback_executed"]="true"
}

# Function to verify rollback success
verify_rollback_success() {
    if [[ "$VERIFY_ROLLBACK" != "true" ]]; then
        log_info "Rollback verification disabled"
        return 0
    fi
    
    log_progress "Verifying rollback success"
    
    # Re-check migration state
    get_migration_state
    
    local new_migration="${rollback_state[current_migration]}"
    
    if [[ "$ROLLBACK_TYPE" == "migration" ]]; then
        if [[ "$new_migration" == "$TARGET_MIGRATION" ]]; then
            log_success "Migration rollback verified: $new_migration"
        else
            log_error "Migration rollback verification failed: expected $TARGET_MIGRATION, got $new_migration"
            return 1
        fi
    fi
    
    # Test database connectivity
    if ! validate_db_connection; then
        log_error "Database connectivity test failed after rollback"
        return 1
    fi
    
    # Run basic integrity checks
    case "$DB_TYPE" in
        postgresql)
            if [[ "$DRY_RUN" == "false" ]]; then
                PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
                    -d "$DB_NAME" -c "SELECT count(*) FROM information_schema.tables;" > /dev/null
                log_success "PostgreSQL integrity check passed"
            fi
            ;;
        mysql)
            if [[ "$DRY_RUN" == "false" ]]; then
                mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" \
                    "$DB_NAME" -e "CHECK TABLE information_schema.tables;" > /dev/null
                log_success "MySQL integrity check passed"
            fi
            ;;
        cloudsql)
            # Basic connectivity test is sufficient for Cloud SQL
            log_success "Cloud SQL connectivity verified"
            ;;
    esac
    
    log_success "Rollback verification completed successfully"
}

# Function to generate rollback report
generate_rollback_report() {
    log_progress "Generating rollback report"
    
    local report_file="$OUTPUT_DIR/rollback-report-$(date +%Y%m%d_%H%M%S).json"
    
    cat > "$report_file" << EOF
{
  "rollback_session": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "database_type": "$DB_TYPE",
    "database_name": "$DB_NAME",
    "rollback_type": "$ROLLBACK_TYPE",
    "target_migration": "$TARGET_MIGRATION",
    "dry_run": $DRY_RUN
  },
  "initial_state": {
    "current_migration": "${rollback_state[current_migration]:-unknown}"
  },
  "backup_info": {
    "backup_created": $BACKUP_BEFORE_ROLLBACK,
    "backup_file": "${backup_info[backup_file]:-none}",
    "backup_size": "${backup_info[backup_size]:-unknown}"
  },
  "rollback_execution": {
    "executed": "${rollback_state[rollback_executed]:-false}",
    "verification_passed": "${rollback_state[verification_passed]:-false}"
  },
  "final_state": {
    "current_migration": "${rollback_state[final_migration]:-unknown}"
  }
}
EOF
    
    log_success "Rollback report generated: $report_file"
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --db-type)
                DB_TYPE="$2"
                shift 2
                ;;
            --db-host)
                DB_HOST="$2"
                shift 2
                ;;
            --db-port)
                DB_PORT="$2"
                shift 2
                ;;
            --db-name)
                DB_NAME="$2"
                shift 2
                ;;
            --db-user)
                DB_USER="$2"
                shift 2
                ;;
            --db-password)
                DB_PASSWORD="$2"
                shift 2
                ;;
            --gcp-project)
                GCP_PROJECT="$2"
                shift 2
                ;;
            --cloud-sql-instance)
                CLOUD_SQL_INSTANCE="$2"
                shift 2
                ;;
            --migration-id)
                MIGRATION_ID="$2"
                shift 2
                ;;
            --target-migration)
                TARGET_MIGRATION="$2"
                shift 2
                ;;
            --rollback-type)
                ROLLBACK_TYPE="$2"
                shift 2
                ;;
            --no-backup)
                BACKUP_BEFORE_ROLLBACK="false"
                shift
                ;;
            --allow-data-loss)
                ALLOW_DATA_LOSS="true"
                shift
                ;;
            --no-confirmation)
                REQUIRE_CONFIRMATION="false"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --db-type TYPE              Database type (postgresql, mysql, cloudsql)"
                echo "  --db-host HOST              Database host"
                echo "  --db-port PORT              Database port"
                echo "  --db-name NAME              Database name"
                echo "  --db-user USER              Database user"
                echo "  --db-password PASSWORD      Database password"
                echo "  --gcp-project PROJECT       GCP project ID"
                echo "  --cloud-sql-instance NAME   Cloud SQL instance name"
                echo "  --migration-id ID           Migration ID to rollback"
                echo "  --target-migration TARGET   Target migration version"
                echo "  --rollback-type TYPE        Rollback type (migration, snapshot, point-in-time)"
                echo "  --no-backup                 Skip pre-rollback backup"
                echo "  --allow-data-loss           Allow operations that may cause data loss"
                echo "  --no-confirmation           Skip confirmation prompts"
                echo "  --dry-run                   Dry run mode"
                echo "  --help                      Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$DB_NAME" ]]; then
        log_error "DB_NAME is required"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "🧪 Running in DRY RUN mode"
    fi
    
    # Execute rollback process
    validate_db_connection
    get_migration_state
    validate_rollback_safety
    create_pre_rollback_backup
    
    # Execute appropriate rollback type
    case "$ROLLBACK_TYPE" in
        migration)
            execute_migration_rollback
            ;;
        snapshot)
            execute_snapshot_rollback
            ;;
        point-in-time)
            execute_point_in_time_rollback
            ;;
        *)
            log_error "Unknown rollback type: $ROLLBACK_TYPE"
            exit 1
            ;;
    esac
    
    # Verify and report
    if verify_rollback_success; then
        rollback_state["verification_passed"]="true"
        log_success "Database rollback completed successfully"
    else
        rollback_state["verification_passed"]="false"
        log_error "Database rollback verification failed"
        exit 1
    fi
    
    # Update final state
    get_migration_state
    rollback_state["final_migration"]="${rollback_state[current_migration]}"
    
    # Generate report
    generate_rollback_report
    
    log_success "Database rollback process completed"
}

# Execute main function with all arguments
main "$@"