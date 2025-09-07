# Fusion - Academic Management System

Fusion is a comprehensive academic management system designed for educational institutions.

## Quick Start Guide for Contributing

### Prerequisites
- Git installed on your local machine
- GitHub account
- Forked repository from the main Fusion project

### Step-by-Step Guide to Raise a Pull Request

#### 1. Fork and Clone the Repository
```bash
# Fork the repository on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/Fusion.git
cd Fusion
```

#### 2. Set Up Remote Upstream
```bash
# Add the original repository as upstream
git remote add upstream https://github.com/FusionIIIT/Fusion.git
git remote -v  # Verify remotes
```

#### 3. Create a Feature Branch
```bash
# Update your main branch
git checkout main
git pull upstream main

# Create and switch to a new feature branch
git checkout -b feature/your-feature-name
```

#### 4. Make Your Changes
- Implement your changes following the project's coding standards
- Test your changes thoroughly
- Ensure your changes don't break existing functionality

#### 5. Commit Your Changes
```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "module_name: brief description of changes"
```

#### 6. Push to Your Fork
```bash
# Push your feature branch to your fork
git push origin feature/your-feature-name
```

#### 7. Create Pull Request
1. Go to your fork on GitHub
2. Click "Compare & pull request"
3. **Important**: Make sure you're targeting the correct module branch, NOT the main branch
4. Follow the PR title format: `<module_name> : <week_no> : <PR_Title>`

#### Example PR Title
```
ac-2 : 3 : fix branch change validation logic
```

### PR Guidelines Checklist

Before submitting your PR, ensure:

- [ ] PR title follows the format: `<module_name> : <week_no> : <PR_Title>`
- [ ] Module name is in lowercase (e.g., ac-2, os-2)
- [ ] Week number is specified
- [ ] PR title starts with lowercase letter
- [ ] Targeting the correct module branch (not main)
- [ ] No changes to `requirements.txt` without approval
- [ ] No changes to `settings/development.py` for local database setup
- [ ] No database dump files included
- [ ] Fork is up to date with upstream
- [ ] Changes are tested and working
- [ ] Code follows project conventions

### Common Modules
- **ac** - Academic Procedures
- **os** - Office of Students
- **hr** - Human Resources
- **es** - Estate Module
- **iwd** - Infrastructure and Works Department

### After Submitting PR

1. **Wait for Review**: Project maintainers will review your PR
2. **Address Feedback**: Make changes if requested by reviewers
3. **Update PR**: Push additional commits to the same branch to update the PR
4. **Merge**: Once approved, your PR will be merged

### Troubleshooting

#### Merge Conflicts
If you encounter merge conflicts:
```bash
# Update your branch with latest upstream changes
git checkout your-feature-branch
git fetch upstream
git rebase upstream/target-module-branch

# Resolve conflicts manually, then:
git add .
git rebase --continue
git push -f origin your-feature-branch
```

#### Updating an Existing PR
```bash
# Make additional changes
git add .
git commit -m "address review feedback"
git push origin your-feature-branch
```

### Need Help?

- Check existing issues and PRs for similar problems
- Contact project leads for dependency-related questions
- Follow the Code of Conduct
- Ask questions in project discussions

## Project Structure

```
Fusion/
├── FusionIIIT/
│   ├── applications/
│   │   ├── academic_procedures/
│   │   ├── estate_module/
│   │   ├── globals/
│   │   └── ...
│   └── templates/
└── CONTRIBUTING.md
```

## Development Setup

1. Clone the repository
2. Set up your development environment
3. Install dependencies (check with project leads before modifying requirements.txt)
4. Configure your local database (don't commit these changes)
5. Run tests to ensure everything works

Remember: Always work on feature branches and never commit directly to main or module branches!