# Quick PR Guide for Fusion

## PR Title Format (MANDATORY)
```
<module_name> : <week_no> : <PR_Title>
```

### Examples:
- `ac-2 : 3 : fix branch change validation logic`
- `os-1 : 2 : add student profile update feature`
- `hr-3 : 4 : implement leave approval workflow`

## Quick Commands

### Initial Setup (One Time)
```bash
# Fork repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/Fusion.git
cd Fusion
git remote add upstream https://github.com/FusionIIIT/Fusion.git
```

### For Each PR
```bash
# 1. Update and create branch
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name

# 2. Make changes, then commit
git add .
git commit -m "descriptive message"

# 3. Push and create PR
git push origin feature/your-feature-name
# Go to GitHub and create PR with proper title format
```

## ⚠️ Important Rules

### DO NOT:
- ❌ Target main branch (use module branch only)
- ❌ Modify `requirements.txt` without approval
- ❌ Commit `settings/development.py` changes
- ❌ Include database dump files
- ❌ Use uppercase in module names

### DO:
- ✅ Use correct PR title format
- ✅ Target the specific module branch
- ✅ Test your changes thoroughly
- ✅ Keep fork updated with upstream
- ✅ Use feature branches

## Module Names (lowercase)
- `ac` - Academic Procedures
- `os` - Office of Students  
- `hr` - Human Resources
- `es` - Estate Module
- `iwd` - Infrastructure and Works Department

## Need Help?
1. Check CONTRIBUTING.md for detailed guidelines
2. Read README.md for full setup instructions
3. Contact project leads for dependency questions