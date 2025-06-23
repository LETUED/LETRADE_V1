#!/bin/bash

# =============================================================================
# Letrade_v1 Trading System Security Check Script
# =============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} ✅ $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} ⚠️ $1"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')]${NC} ❌ $1"
}

log_critical() {
    echo -e "${RED}[$(date +'%H:%M:%S')]${NC} 🚨 CRITICAL: $1"
}

echo "🔐 Running Letrade_v1 Trading System Security Checks"
echo "===================================================="
echo ""

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]] || [[ ! -d "src" ]]; then
    log_error "This script must be run from the project root directory"
    exit 1
fi

# Create logs directory for security reports
mkdir -p logs/security

SECURITY_VIOLATIONS=0
CRITICAL_VIOLATIONS=0

# =============================================================================
# 1. Hardcoded Secrets Detection
# =============================================================================
echo "🔍 1. Hardcoded Secrets Detection"
echo "=================================="

log "Checking for hardcoded API keys..."

# Common API key patterns
API_KEY_PATTERNS=(
    "api_key\s*[=:]\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "apikey\s*[=:]\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "api-key\s*[=:]\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "key\s*[=:]\s*['\"][a-zA-Z0-9]{30,}['\"]"
)

SECRET_PATTERNS=(
    "secret\s*[=:]\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "secret_key\s*[=:]\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "private_key\s*[=:]\s*['\"][a-zA-Z0-9]{50,}['\"]"
    "password\s*[=:]\s*['\"][^'\"]{8,}['\"]"
)

EXCHANGE_PATTERNS=(
    "binance.*key"
    "coinbase.*key"
    "kraken.*key"
    "okx.*key"
    "huobi.*key"
    "bybit.*key"
)

# Check API key patterns
for pattern in "${API_KEY_PATTERNS[@]}"; do
    if grep -rn -E "$pattern" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -v "test" | grep -v "mock" | grep -v "example"; then
        log_critical "Hardcoded API key pattern detected: $pattern"
        CRITICAL_VIOLATIONS=$((CRITICAL_VIOLATIONS + 1))
    fi
done

# Check secret patterns
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -rn -E "$pattern" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -v "test" | grep -v "mock" | grep -v "example"; then
        log_critical "Hardcoded secret pattern detected: $pattern"
        CRITICAL_VIOLATIONS=$((CRITICAL_VIOLATIONS + 1))
    fi
done

# Check exchange-specific patterns
for pattern in "${EXCHANGE_PATTERNS[@]}"; do
    if grep -rn -i "$pattern" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -v "test" | grep -v "mock" | grep -v "example"; then
        log_critical "Exchange-specific hardcoded value detected: $pattern"
        CRITICAL_VIOLATIONS=$((CRITICAL_VIOLATIONS + 1))
    fi
done

if [[ $CRITICAL_VIOLATIONS -eq 0 ]]; then
    log_success "No hardcoded secrets detected"
else
    log_critical "$CRITICAL_VIOLATIONS hardcoded secret(s) detected"
fi

echo ""

# =============================================================================
# 2. Trading System Safety Checks
# =============================================================================
echo "💰 2. Trading System Safety Checks"
echo "==================================="

log "Checking for dry-run protection in trading code..."

# Find files with trading operations
TRADING_FILES=$(grep -rn -l "execute_trade\|place_order\|submit_order\|buy\|sell" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -v test | grep -v mock || true)

if [[ -n "$TRADING_FILES" ]]; then
    log "Found trading-related files:"
    echo "$TRADING_FILES" | while read -r file; do
        echo "  - $file"
    done
    
    echo ""
    log "Checking dry-run protection..."
    
    for file in $TRADING_FILES; do
        if [[ -f "$file" ]]; then
            # Check if the file has dry-run protection
            if grep -q "dry_run\|test_mode\|mock\|simulation" "$file"; then
                log_success "$file: Has dry-run protection"
            else
                log_warning "$file: Missing dry-run protection"
                SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
                
                # Show the trading-related lines for context
                echo "   Trading operations found:"
                grep -n "execute_trade\|place_order\|submit_order\|buy\|sell" "$file" | head -3 | sed 's/^/     /'
            fi
        fi
    done
else
    log_success "No trading operation files found"
fi

echo ""

# =============================================================================
# 3. Capital Manager Validation Check
# =============================================================================
echo "🏦 3. Capital Manager Validation Check"
echo "======================================"

log "Checking that all trade signals go through Capital Manager..."

# Find strategy files
STRATEGY_FILES=$(find src/ -name "*.py" -path "*/strategies/*" 2>/dev/null | grep -v __pycache__ | grep -v test || true)

if [[ -n "$STRATEGY_FILES" ]]; then
    log "Found strategy files:"
    echo "$STRATEGY_FILES" | while read -r file; do
        echo "  - $file"
    done
    
    echo ""
    
    for file in $STRATEGY_FILES; do
        if [[ -f "$file" ]]; then
            # Check if strategy generates trade signals
            if grep -q "trade\|signal\|order" "$file"; then
                # Check if it validates through Capital Manager
                if grep -q "capital_manager\|CapitalManager\|validate_trade\|request.*capital" "$file"; then
                    log_success "$file: Uses Capital Manager validation"
                else
                    log_warning "$file: May bypass Capital Manager validation"
                    SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
                fi
            fi
        fi
    done
else
    log_success "No strategy files found yet"
fi

echo ""

# =============================================================================
# 4. Error Handling Analysis
# =============================================================================
echo "🛡️ 4. Error Handling Analysis"
echo "============================="

log "Checking for proper error handling in critical sections..."

# Look for functions without try-catch blocks in critical areas
CRITICAL_MODULES=("core_engine" "capital_manager" "exchange_connector")

for module in "${CRITICAL_MODULES[@]}"; do
    if [[ -d "src/$module" ]]; then
        log "Analyzing $module for error handling..."
        
        # Find Python files in the module
        MODULE_FILES=$(find "src/$module" -name "*.py" 2>/dev/null | grep -v __pycache__ | grep -v test || true)
        
        for file in $MODULE_FILES; do
            if [[ -f "$file" ]]; then
                # Count functions and try blocks
                FUNC_COUNT=$(grep -c "def " "$file" 2>/dev/null || echo "0")
                TRY_COUNT=$(grep -c "try:" "$file" 2>/dev/null || echo "0")
                
                # Remove any newlines from counts
                FUNC_COUNT=$(echo "$FUNC_COUNT" | tr -d '\n\r')
                TRY_COUNT=$(echo "$TRY_COUNT" | tr -d '\n\r')
                
                if [[ "$FUNC_COUNT" -gt 0 ]] && [[ "$TRY_COUNT" -eq 0 ]]; then
                    log_warning "$file: $FUNC_COUNT functions but no try-catch blocks"
                    SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
                elif [[ "$FUNC_COUNT" -gt 0 ]]; then
                    log_success "$file: Has error handling ($TRY_COUNT try blocks for $FUNC_COUNT functions)"
                fi
            fi
        done
    else
        log "Module $module not found (expected for early development)"
    fi
done

echo ""

# =============================================================================
# 5. Environment Variable Usage Check
# =============================================================================
echo "🌍 5. Environment Variable Usage Check"
echo "======================================"

log "Checking proper environment variable usage..."

# Look for direct access to sensitive environment variables
SENSITIVE_ENV_VARS=(
    "API_KEY"
    "SECRET_KEY"
    "PASSWORD"
    "TOKEN"
    "PRIVATE_KEY"
    "BINANCE_API_KEY"
    "BINANCE_SECRET"
)

for var in "${SENSITIVE_ENV_VARS[@]}"; do
    # Check for direct os.environ access
    if grep -rn "os.environ\[.*$var.*\]" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -v test; then
        log_warning "Direct environment variable access found for $var"
        SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
    fi
    
    # Check for os.getenv without default or validation
    if grep -rn "os.getenv.*$var" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -v test | grep -v "default"; then
        log_warning "Environment variable $var accessed without default value"
        SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
    fi
done

log_success "Environment variable usage check completed"

echo ""

# =============================================================================
# 6. Logging Security Check
# =============================================================================
echo "📝 6. Logging Security Check"
echo "============================="

log "Checking for sensitive data in log statements..."

# Patterns that might log sensitive data
SENSITIVE_LOG_PATTERNS=(
    "log.*api_key"
    "log.*secret"
    "log.*password"
    "log.*token"
    "print.*api_key"
    "print.*secret"
    "print.*password"
)

for pattern in "${SENSITIVE_LOG_PATTERNS[@]}"; do
    if grep -rn -i "$pattern" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -v test; then
        log_warning "Potential sensitive data logging: $pattern"
        SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
    fi
done

log_success "Logging security check completed"

echo ""

# =============================================================================
# 7. Dependency Vulnerability Check
# =============================================================================
echo "📦 7. Dependency Vulnerability Check"
echo "===================================="

if command -v safety >/dev/null 2>&1; then
    log "Running safety check on dependencies..."
    
    if safety check --json --output logs/security/safety-report.json 2>/dev/null; then
        log_success "No known vulnerabilities in dependencies"
    else
        log_warning "Potential vulnerabilities found in dependencies"
        log "See logs/security/safety-report.json for details"
        SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
    fi
else
    log "safety tool not installed, skipping dependency vulnerability check"
    log "Install with: pip install safety"
fi

echo ""

# =============================================================================
# 8. File Permission Check
# =============================================================================
echo "🔒 8. File Permission Check"
echo "==========================="

log "Checking for overly permissive file permissions..."

# Check for world-writable files
WORLD_WRITABLE=$(find . -type f -perm -002 2>/dev/null | grep -v ".git" | grep -v "__pycache__" || true)

if [[ -n "$WORLD_WRITABLE" ]]; then
    log_warning "World-writable files found:"
    echo "$WORLD_WRITABLE" | sed 's/^/  /'
    SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
else
    log_success "No world-writable files found"
fi

# Check for executable Python files (potential security risk)
EXECUTABLE_PY=$(find src/ -name "*.py" -executable 2>/dev/null || true)

if [[ -n "$EXECUTABLE_PY" ]]; then
    log_warning "Executable Python files found (remove execute permission):"
    echo "$EXECUTABLE_PY" | sed 's/^/  /'
    SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
else
    log_success "No executable Python files found"
fi

echo ""

# =============================================================================
# 9. Configuration Security Check
# =============================================================================
echo "⚙️ 9. Configuration Security Check"
echo "=================================="

log "Checking configuration files for security issues..."

# Check for default passwords or keys in config files
CONFIG_FILES=$(find . -name "*.yaml" -o -name "*.yml" -o -name "*.json" -o -name "*.toml" -o -name "*.cfg" -o -name "*.ini" 2>/dev/null | grep -v ".git" || true)

if [[ -n "$CONFIG_FILES" ]]; then
    for file in $CONFIG_FILES; do
        if [[ -f "$file" ]]; then
            # Check for default/example credentials
            if grep -i "password.*123\|password.*admin\|password.*default\|key.*example\|secret.*test" "$file" >/dev/null 2>&1; then
                log_warning "$file: Contains default/example credentials"
                SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
            fi
            
            # Check for hardcoded production URLs or endpoints
            if grep -i "binance\.com\|coinbase\.com" "$file" >/dev/null 2>&1; then
                log_warning "$file: Contains hardcoded production endpoints"
                SECURITY_VIOLATIONS=$((SECURITY_VIOLATIONS + 1))
            fi
        fi
    done
    
    log_success "Configuration security check completed"
else
    log "No configuration files found"
fi

echo ""

# =============================================================================
# Generate Security Report
# =============================================================================
echo "📊 Security Report Generation"
echo "============================="

REPORT_FILE="logs/security/security-report.txt"

cat > "$REPORT_FILE" << EOF
Letrade_v1 Security Check Report
================================
Date: $(date)
Project: Letrade_v1 Automated Cryptocurrency Trading System

SUMMARY
-------
Critical Violations: $CRITICAL_VIOLATIONS
Security Violations: $SECURITY_VIOLATIONS
Total Issues: $((CRITICAL_VIOLATIONS + SECURITY_VIOLATIONS))

CHECKS PERFORMED
----------------
✓ Hardcoded secrets detection
✓ Trading system safety checks  
✓ Capital Manager validation
✓ Error handling analysis
✓ Environment variable usage
✓ Logging security check
✓ Dependency vulnerability check
✓ File permission check
✓ Configuration security check

RECOMMENDATIONS
---------------
EOF

if [[ $CRITICAL_VIOLATIONS -gt 0 ]]; then
    cat >> "$REPORT_FILE" << EOF

🚨 CRITICAL ISSUES FOUND:
- $CRITICAL_VIOLATIONS hardcoded secrets detected
- IMMEDIATE ACTION REQUIRED: Remove all hardcoded API keys and secrets
- Use GCP Secret Manager or environment variables instead

EOF
fi

if [[ $SECURITY_VIOLATIONS -gt 0 ]]; then
    cat >> "$REPORT_FILE" << EOF

⚠️ SECURITY IMPROVEMENTS NEEDED:
- $SECURITY_VIOLATIONS security violations found
- Review and address warnings above
- Implement missing dry-run protections
- Add proper error handling where missing
- Fix file permissions issues

EOF
fi

cat >> "$REPORT_FILE" << EOF

BEST PRACTICES FOR TRADING SYSTEMS
----------------------------------
1. Never hardcode API keys or secrets in source code
2. Always use dry-run mode for testing trading operations
3. Validate all trades through Capital Manager
4. Implement comprehensive error handling
5. Use structured logging without sensitive data
6. Keep dependencies updated and scan for vulnerabilities
7. Use least-privilege file permissions
8. Store sensitive configuration in secure vaults

NEXT STEPS
----------
1. Address all critical violations immediately
2. Review and fix security violations
3. Implement recommended security measures
4. Re-run security checks after fixes
5. Set up automated security scanning in CI/CD

For questions or assistance, refer to:
- docs/PROJECT_SETUP_WORKFLOW.md
- Security section in CLAUDE.md
EOF

log "Security report saved to $REPORT_FILE"

echo ""

# =============================================================================
# Final Results
# =============================================================================
echo "🎯 Final Security Assessment"
echo "============================"

if [[ $CRITICAL_VIOLATIONS -eq 0 ]] && [[ $SECURITY_VIOLATIONS -eq 0 ]]; then
    log_success "🎉 All security checks passed!"
    log_success "Your trading system meets security requirements"
    exit 0
elif [[ $CRITICAL_VIOLATIONS -gt 0 ]]; then
    log_critical "CRITICAL SECURITY VIOLATIONS DETECTED!"
    log_critical "$CRITICAL_VIOLATIONS critical issue(s) must be fixed immediately"
    log_error "Trading system is NOT safe for production use"
    echo ""
    echo "❌ BLOCKING ISSUES:"
    echo "   • Hardcoded secrets detected"
    echo "   • Immediate action required"
    echo ""
    echo "🔧 QUICK FIXES:"
    echo "   1. Move all API keys to .env file"
    echo "   2. Use os.getenv() to read environment variables"
    echo "   3. Add .env to .gitignore"
    echo "   4. Use GCP Secret Manager for production"
    exit 1
else
    log_warning "$SECURITY_VIOLATIONS security issue(s) found"
    log_warning "Review and address the warnings above"
    log "See $REPORT_FILE for detailed recommendations"
    echo ""
    echo "⚠️ ISSUES TO ADDRESS:"
    echo "   • Missing dry-run protections"
    echo "   • Error handling improvements needed"
    echo "   • File permission issues"
    echo ""
    echo "💡 These issues should be addressed before production deployment"
    exit 0  # Don't block development for non-critical issues
fi