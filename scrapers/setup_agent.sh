#!/bin/bash
# NPT Stock Intelligence — Agent Setup Script
# Run this once to configure the agent + bi-weekly email schedule

echo "======================================"
echo "  NPT Stock Intelligence Agent Setup"
echo "======================================"

# 1. Install dependencies
echo ""
echo "Step 1: Installing dependencies..."
pip install anthropic python-dotenv --quiet
echo "✅ Done"

# 2. Create .env file if not exists
echo ""
echo "Step 2: Creating .env file..."
ENV_FILE="$(dirname "$0")/.env"

if [ ! -f "$ENV_FILE" ]; then
cat > "$ENV_FILE" << 'EOF'
# NPT Stock Intelligence — Environment Variables
# Fill in your actual values below

# Claude API key (get from console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE

# Gmail for sending reports (use a Gmail App Password, not your main password)
# Go to: Google Account → Security → 2-Step Verification → App Passwords
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Report recipients (comma separated)
REPORT_RECIPIENTS=lowwood@nipharm.co.uk,mcgregor@nipharm.co.uk
EOF
echo "✅ Created .env — edit it with your API key and Gmail details"
else
echo "⚠️  .env already exists — skipping"
fi

# 3. Schedule bi-weekly report (every Monday and Thursday at 8am)
echo ""
echo "Step 3: Setting up bi-weekly email schedule..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_CMD="0 8 * * 1,4 cd '$SCRIPT_DIR' && source .env && python agent.py --report >> /tmp/npt_report.log 2>&1"

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -q "agent.py --report") && {
    echo "⚠️  Cron job already exists — skipping"
} || {
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ Scheduled: bi-weekly report every Monday & Thursday at 8:00am"
}

echo ""
echo "======================================"
echo "  Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your ANTHROPIC_API_KEY"
echo "  2. Edit .env with your GMAIL credentials"
echo "  3. Test the agent:  python agent.py"
echo "  4. Test a report:   python agent.py --report --email you@example.com"
echo ""
echo "Deployment (staff-only access to Streamlit):"
echo "  See README_DEPLOY.md for Cloudflare Tunnel setup"
echo ""
