# Troubleshooting Display Manager Issues

## Issue #978: Sugar Session Freezes at Loading Screen

### Symptoms
When attempting to log into Sugar via your system's display manager (GDM, LightDM, SDDM):
- The screen shows a loading indicator
- System becomes unresponsive
- Sugar desktop never appears
- Must force power off/restart

### Root Causes
This issue typically occurs due to:
1. Missing or incompatible dependencies (metacity, python modules)
2. Display manager compatibility problems
3. Incorrect session file configuration
4. Missing error logging/diagnostics

### Recommended Solution: Use Development Mode

Instead of logging in through the display manager, run Sugar within your existing desktop session:
```bash
# After building Sugar from source
sugar-dev
```

**Benefits:**
- Avoids display manager integration entirely
- Provides detailed error logging
- Safer for development and testing
- Works on all distributions
- Easy to debug and recover from issues

### Requirements
```bash
# Install dependencies
sudo apt install metacity python3-gi gir1.2-gtk-3.0 dbus-x11

# Build Sugar from source (if not already done)
# See docs/development-environment.md
```

### Running Sugar in Development Mode
```bash
# Simple invocation
sugar-dev

# Check logs if issues occur
cat ~/.sugar/default/logs/sugar-dev.log

# Debug mode
SUGAR_LOGGER_LEVEL=debug sugar-dev
```

### Alternative: Full Session Mode (Advanced)

If you specifically need Sugar as a complete desktop session:

#### 1. Verify Session File

Check `/usr/share/xsessions/sugar.desktop` contains:
```ini
[Desktop Entry]
Name=Sugar
Comment=Sugar Learning Platform
Exec=sugar-session
TryExec=sugar-session
Icon=sugar-xo
Type=Application
DesktopNames=SUGAR
```

#### 2. Ensure Dependencies Are Installed
```bash
sudo apt install metacity python3-gi gir1.2-gtk-3.0 dbus-x11
```

#### 3. Check Logs
```bash
# System journal
journalctl -b | grep sugar

# X server logs
cat /var/log/Xorg.0.log | grep -i error

# Sugar logs
ls -la ~/.sugar/default/logs/
```

#### 4. Recovery from Frozen Session

If stuck at loading screen:

1. Press `Ctrl + Alt + F3` to switch to text console (TTY3)
2. Login with your username and password
3. Restart display manager:
```bash
   sudo systemctl restart gdm  # or lightdm, or sddm
```
4. Switch back: `Ctrl + Alt + F1` or `Ctrl + Alt + F7`

### Platform-Specific Notes

#### Ubuntu 24.04+
- Sugar packages not available in repositories
- Must build from source
- Use `sugar-dev` recommended over full session mode

#### Fedora
- Install via: `sudo dnf install sugar`
- Generally better display manager compatibility

### Getting Help

If issues persist:

1. **Check logs first:**
   - `~/.sugar/default/logs/sugar-dev.log`
   - `~/.sugar/default/logs/shell.log`

2. **Run with debug logging:**
```bash
   SUGAR_LOGGER_LEVEL=debug sugar-dev
```

3. **Report issue:**
   - GitHub: https://github.com/sugarlabs/sugar/issues
   - Include log files and system information

### Why sugar-dev Instead of Full Session?

For developers and testers, `sugar-dev` is preferred because:
- ✅ Faster iteration cycle
- ✅ Easier debugging
- ✅ No risk of system lockout
- ✅ Better error visibility
- ✅ Works across different display managers
- ✅ Can run alongside other desktop environments

Full session mode is primarily intended for dedicated Sugar systems (like OLPC laptops) rather than development machines.
