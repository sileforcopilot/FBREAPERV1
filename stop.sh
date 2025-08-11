#!/bin/bash

# FBREAPERV1 Stop Script
# This script stops all services for the Facebook OSINT Dashboard

echo "🛑 Stopping FBREAPERV1 - Facebook OSINT Dashboard"
echo "=================================================="

# Stop tmux session if running
if tmux has-session -t fbreaper 2>/dev/null; then
    echo "🐧 Stopping tmux session 'fbreaper'..."
    tmux kill-session -t fbreaper
    echo "✅ Tmux session stopped"
else
    echo "ℹ️  No tmux session found"
fi

# Stop Docker services
echo "🐳 Stopping Docker services..."
docker-compose down

echo "✅ All services stopped"
echo ""
echo "🧹 To clean up completely, run:"
echo "   docker-compose down -v"
echo "   (This will remove all data volumes)"