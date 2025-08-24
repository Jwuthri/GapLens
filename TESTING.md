# Testing Guide

This document provides comprehensive information about the testing strategy and implementation for the Review Gap Analyzer project.

## Overview

The project implements a multi-layered testing approach with:

- **Unit Tests**: Test individual components and functions in isolation
- **Integration Tests**: Test interactions between components and external services
- **End-to-End Tests**: Test complete user workflows from frontend to backend
- **Performance Tests**: Test system performance under load
- **Security Tests**: Test for common security vulnerabilities

## Test Coverage Goals

- **Backend**: Minimum 80% code coverage
- **Frontend**: Minimum 75% code coverage
- **Critical Paths**: 100% coverage for core analysis workflow

## Backend Testing

### Structure

```
backend/tests/
├── __init__.py
├── conftest.py                 # Shared test fixtures
├── api/                        # API endpoint tests
├── database/                   # Database operation tests
├── integration/                # Integration tests
├── e2e/                       # End-to-end tests
├── models/                    # Data model tests
├── services/                  # Service layer tests
└── tasks/                     # Background task tests
```

### Running Backend Tests

#### Using the test runner script

```bash
# Run all tests
python backend/run_tests.py all

# Run specific test types
python backend/run_tests.py unit
python backend/run_tests.py integration
python backend/run_tests.py e2e

# Run with coverage
python backend/run_tests.py coverage

# Run specific tests
python backend/run_tests.py specific -k "test_clustering"

# Run quality checks
python backend/run_tests.py quality
```

#### Using pytest directly

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test files
pytest tests/services/test_clustering_engine.py

# Run tests with specific markers
pytest -m "unit"
pytest -m "integration"
pytest -m "e2e"

# Run tests matching pattern
pytest -k "clustering"
```

### Test Categories

#### Unit Tests

- **Location**: `tests/services/`, `tests/models/`, `tests/api/`
- **Purpose**: Test individual functions and classes
- **Mocking**: Heavy use of mocks for external dependencies
- **Speed**: Fast execution (< 1 second per test)

#### Integration Tests

- **Location**: `tests/integration/`
- **Purpose**: Test component interactions
- **Database**: Uses test database with real connections
- **External Services**: Uses mocked external APIs

#### End-to-End Tests

- **Location**: `tests/e2e/`
- **Purpose**: Test complete user scenarios
- **Scope**: Full request-response cycles
- **Data**: Uses realistic test datasets

### Test Fixtures

Common fixtures are defined in `conftest.py`:

```python
@pytest.fixture
def test_session():
    """Provides a test database session."""
    
@pytest.fixture
def sample_review_data():
    """Provides sample review data for testing."""
    
@pytest.fixture
def sample_analysis_data():
    """Provides sample analysis data for testing."""
```

### Mocking Strategy

- **External APIs**: Mock all external service calls
- **Database**: Use test database for integration tests, mock for unit tests
- **File System**: Mock file operations
- **Time**: Use `freezegun` for time-dependent tests

## Frontend Testing

### Structure

```
frontend/src/
├── components/__tests__/       # Component tests
├── hooks/__tests__/           # Custom hook tests
├── services/__tests__/        # Service layer tests
└── utils/__tests__/           # Utility function tests
```

### Running Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run specific test suites
npm run test:components
npm run test:hooks
npm run test:services

# Run E2E tests
npm run test:e2e
```

### Test Categories

#### Component Tests

- **Framework**: React Testing Library
- **Focus**: User interactions and rendering
- **Mocking**: Mock external dependencies and APIs

#### Hook Tests

- **Framework**: React Testing Library hooks
- **Focus**: Custom hook behavior and state management
- **Mocking**: Mock API calls and browser APIs

#### Service Tests

- **Framework**: Jest
- **Focus**: API communication and data transformation
- **Mocking**: Mock fetch and external services

### Testing Utilities

#### Custom Render Function

```typescript
// test-utils.tsx
export function renderWithProviders(ui: React.ReactElement) {
  // Wrap with necessary providers
}
```

#### Mock Data Factories

```typescript
// test-factories.ts
export const createMockAnalysisResult = (overrides = {}) => ({
  // Default mock data
  ...overrides
});
```

## End-to-End Testing

### Tools

- **Backend E2E**: Custom test scenarios using FastAPI TestClient
- **Frontend E2E**: Playwright (configured but not implemented in this task)

### Scenarios Covered

1. **Complete Analysis Workflow**
   - Submit app for analysis
   - Monitor progress
   - Retrieve results
   - Export data

2. **Error Handling**
   - Invalid inputs
   - Network failures
   - Server errors

3. **Concurrent Users**
   - Multiple simultaneous analyses
   - Resource contention

4. **Large Datasets**
   - Performance with many reviews
   - Memory usage optimization

## Performance Testing

### Metrics Tracked

- **Response Time**: API endpoint response times
- **Memory Usage**: Memory consumption during processing
- **Database Performance**: Query execution times
- **Clustering Performance**: NLP processing speed

### Benchmarks

```bash
# Run performance tests
pytest tests/ --benchmark-only
```

## Test Data Management

### Realistic Test Data

- **Reviews**: Diverse complaint types and languages
- **Apps**: Various app categories and sizes
- **Websites**: Different business types and review sources

### Data Factories

- **Factory Boy**: For creating test database records
- **Faker**: For generating realistic fake data
- **Custom Factories**: Domain-specific test data

## Continuous Integration

### GitHub Actions Workflow

The CI pipeline runs:

1. **Code Quality Checks**
   - Linting (flake8, ESLint)
   - Type checking (mypy, TypeScript)
   - Code formatting (black, prettier)

2. **Unit Tests**
   - Backend unit tests with coverage
   - Frontend component tests with coverage

3. **Integration Tests**
   - API integration tests
   - Database integration tests

4. **End-to-End Tests**
   - Complete workflow tests
   - Error scenario tests

5. **Security Scans**
   - Dependency vulnerability checks
   - Code security analysis

6. **Performance Tests**
   - Benchmark regression tests
   - Memory usage monitoring

### Coverage Reporting

- **Backend**: Coverage reports uploaded to Codecov
- **Frontend**: Coverage reports uploaded to Codecov
- **Combined**: Overall project coverage tracking

## Test Environment Setup

### Backend Test Environment

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Set environment variables
export DATABASE_URL="sqlite:///test.db"
export REDIS_URL="redis://localhost:6379/1"
export TESTING=true
```

### Frontend Test Environment

```bash
# Install dependencies
npm install

# Jest configuration in jest.config.js
# Test setup in jest.setup.js
```

### Docker Test Environment

```bash
# Run tests in Docker
docker-compose -f docker-compose.test.yml up --build
```

## Writing New Tests

### Backend Test Guidelines

1. **Use descriptive test names**

   ```python
   def test_clustering_engine_groups_similar_complaints():
   ```

2. **Follow AAA pattern** (Arrange, Act, Assert)

   ```python
   def test_example():
       # Arrange
       data = create_test_data()
       
       # Act
       result = process_data(data)
       
       # Assert
       assert result.is_valid
   ```

3. **Use appropriate fixtures**

   ```python
   def test_with_database(test_session):
       # Test uses database session
   ```

4. **Mock external dependencies**

   ```python
   @patch('app.services.external_api.call')
   def test_with_mocked_api(mock_call):
       # Test with mocked external call
   ```

### Frontend Test Guidelines

1. **Test user behavior, not implementation**

   ```typescript
   test('displays error when form is submitted empty', () => {
     // Test user interaction, not internal state
   });
   ```

2. **Use semantic queries**

   ```typescript
   screen.getByRole('button', { name: /submit/i })
   screen.getByLabelText(/email address/i)
   ```

3. **Test accessibility**

   ```typescript
   expect(screen.getByRole('button')).toBeInTheDocument();
   ```

4. **Mock API calls**

   ```typescript
   jest.mock('@/services/api', () => ({
     submitAnalysis: jest.fn()
   }));
   ```

## Test Maintenance

### Regular Tasks

1. **Update test data** when schemas change
2. **Review test coverage** monthly
3. **Update mocks** when external APIs change
4. **Performance baseline** updates quarterly

### Test Debt Management

1. **Identify flaky tests** and fix root causes
2. **Remove obsolete tests** when features are removed
3. **Refactor test utilities** to reduce duplication
4. **Update test documentation** with code changes

## Debugging Tests

### Backend Debugging

```bash
# Run single test with verbose output
pytest tests/test_specific.py::test_function -v -s

# Run with debugger
pytest tests/test_specific.py::test_function --pdb

# Run with coverage and open HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Frontend Debugging

```bash
# Run tests in debug mode
npm test -- --verbose

# Run specific test file
npm test -- ComponentName.test.tsx

# Debug with browser
npm test -- --debug
```

## Best Practices

### General

- **Test behavior, not implementation**
- **Keep tests independent and isolated**
- **Use meaningful test data**
- **Write tests before fixing bugs**
- **Maintain test readability**

### Performance

- **Use appropriate test isolation levels**
- **Mock expensive operations in unit tests**
- **Use test databases for integration tests**
- **Parallelize test execution when possible**

### Maintenance

- **Regular test review and cleanup**
- **Update tests with feature changes**
- **Monitor test execution times**
- **Keep test dependencies up to date**

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Check test database configuration
   - Ensure test isolation

2. **Flaky tests**
   - Identify timing issues
   - Add proper waits and assertions

3. **Mock issues**
   - Verify mock setup and cleanup
   - Check mock call expectations

4. **Coverage gaps**
   - Identify untested code paths
   - Add targeted tests for edge cases

### Getting Help

- Check test logs for detailed error messages
- Review CI/CD pipeline outputs
- Consult team documentation and standards
- Use debugging tools and techniques outlined above
