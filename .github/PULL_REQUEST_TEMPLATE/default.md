# Pull Request

## 📋 Description

<!-- Provide a brief description of the changes in this PR -->

### What changed?
<!-- Describe what was changed, added, or removed -->

### Why was this change made?
<!-- Explain the motivation or reasoning behind this change -->

### How was it implemented?
<!-- Brief technical overview of the implementation -->

## 🔗 Related Issues

<!-- Link to related issues using keywords: fixes #123, closes #456, relates to #789 -->
- Fixes #
- Relates to #

## 📦 Type of Change

<!-- Check all that apply -->
- [ ] 🚀 **Feature**: New functionality
- [ ] 🐛 **Bug fix**: Fixes an existing issue
- [ ] 📚 **Documentation**: Documentation only changes
- [ ] 🎨 **Style**: Code style changes (formatting, etc.)
- [ ] ♻️ **Refactor**: Code refactoring without functional changes
- [ ] ⚡ **Performance**: Performance improvements
- [ ] 🧪 **Test**: Adding or updating tests
- [ ] 🔧 **Chore**: Maintenance tasks, dependency updates
- [ ] 💥 **Breaking Change**: Changes that break backward compatibility

## 🧪 Testing

### Test Coverage
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] E2E tests added/updated
- [ ] Manual testing completed

### Test Results
<!-- Paste test results or link to CI build -->
```
# Example:
pytest tests/ -v
================================ test session starts ================================
...
```

### Test Environment
- [ ] Local development environment
- [ ] Docker environment
- [ ] CI environment
- [ ] Staging environment

## 🔒 Security & Safety (Required for Trading System)

### Security Checklist
- [ ] No hardcoded API keys or secrets
- [ ] All sensitive data uses GCP Secret Manager
- [ ] Input validation implemented
- [ ] No SQL injection vulnerabilities
- [ ] Authentication/authorization checked

### Trading Safety Checklist
- [ ] Dry-run mode properly implemented
- [ ] All trades validated through CapitalManager
- [ ] Risk management rules applied
- [ ] Error handling prevents system crashes
- [ ] State reconciliation tested
- [ ] Rate limiting implemented for exchange APIs

### Data Protection
- [ ] No sensitive data in logs
- [ ] Personal data handling compliant
- [ ] Database migrations are reversible

## 📊 Performance Impact

### Performance Considerations
- [ ] No significant performance degradation
- [ ] Memory usage optimized
- [ ] Database queries optimized
- [ ] Caching strategy considered

### Benchmarks (if applicable)
<!-- Include before/after performance metrics -->
```
# Example:
Before: 200ms average response time
After:  150ms average response time
```

## 🚀 Deployment

### Deployment Checklist
- [ ] Configuration changes documented
- [ ] Environment variables updated
- [ ] Database migrations included
- [ ] Rollback plan prepared

### Environment Variables Added/Changed
```bash
# Example:
NEW_FEATURE_ENABLED=true
MAX_POSITION_SIZE=1000
```

### Database Changes
- [ ] Migration scripts included
- [ ] Backward compatibility maintained
- [ ] Data migration tested

## 📚 Documentation

### Documentation Updates
- [ ] README.md updated
- [ ] API documentation updated
- [ ] Architecture diagrams updated
- [ ] Code comments added/updated
- [ ] Changelog updated

### Breaking Changes
<!-- If this is a breaking change, describe the impact and migration path -->
- [ ] This PR contains breaking changes
- [ ] Migration guide provided
- [ ] Deprecation notices added

## 🔄 Review Checklist

### Code Quality
- [ ] Code follows project style guide
- [ ] Functions have proper docstrings
- [ ] Type hints added where appropriate
- [ ] No debugging code left in
- [ ] Error handling is comprehensive

### Architecture
- [ ] Follows established patterns
- [ ] SOLID principles applied
- [ ] No tight coupling introduced
- [ ] Scalability considered

### Git
- [ ] Commit messages follow conventional format
- [ ] No sensitive information in commit history
- [ ] Branch is up to date with target branch

## 🎯 Validation

### Functional Testing
<!-- Describe how the feature/fix was tested -->
- [ ] Feature works as expected
- [ ] Edge cases handled
- [ ] Error scenarios tested
- [ ] User experience validated

### Integration Testing
- [ ] Works with existing features
- [ ] No regression in other areas
- [ ] Message bus communication tested
- [ ] Database operations tested

## 📸 Screenshots/Demos

<!-- Include screenshots, videos, or GIFs demonstrating the changes (if applicable) -->

## 📝 Additional Notes

<!-- Any additional information that reviewers should know -->

### Technical Debt
<!-- List any technical debt introduced or resolved -->

### Future Improvements
<!-- List any known limitations or future enhancement opportunities -->

## 👥 Reviewer Guidelines

### For Reviewers
Please ensure:
1. 🔒 **Security**: All security and safety checklists are completed
2. 🧪 **Testing**: Adequate test coverage for changes
3. 📚 **Documentation**: Documentation is updated appropriately
4. 🏗️ **Architecture**: Changes align with system architecture
5. 🚀 **Performance**: No negative performance impact

### Review Focus Areas
<!-- Guide reviewers on what to focus on -->
- [ ] Business logic correctness
- [ ] Error handling and edge cases
- [ ] Security implications
- [ ] Performance impact
- [ ] Code maintainability

---

## 📋 Pre-submission Checklist

<!-- Complete before submitting the PR -->
- [ ] Self-review completed
- [ ] All tests passing locally
- [ ] Documentation updated
- [ ] Security checklist completed (if applicable)
- [ ] Performance impact assessed
- [ ] Breaking changes documented (if applicable)

---

**Note**: This PR will be automatically validated by our CI pipeline. Please ensure all checks pass before requesting review.