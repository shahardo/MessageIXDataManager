# MessageIX/GAMS Integration Implementation Plan

## Work Purpose

This document outlines the implementation plan to enable the MessageIX Data Manager to run actual MessageIX models using GAMS solver, replacing the current mock solver implementation. The goal is to transform the application from a demonstration tool into a fully functional integrated assessment modeling platform.

## Background

The MessageIX Data Manager currently provides a comprehensive GUI for loading, editing, and visualizing MessageIX Excel files, but uses a mock solver that only simulates optimization output. To enable real MessageIX/GAMS execution, the application needs integration with:

- **MessageIX Python API**: For scenario creation and management
- **GAMS Solver**: For mathematical optimization
- **IXMP**: MessageIX database interface

## Architecture Overview

### Current Architecture
```
Excel Files → InputManager → Data Models → UI Display
                                       ↓
Mock Solver → Simulated Output → Results Display
```

### Target Architecture
```
Excel Files → InputManager → Data Models → MessageIX Scenario
                                               ↓
GAMS Solver ← MessageIX API ← Real Results → Results Analyzer
```

## Detailed Task Breakdown

### Phase 1: Dependencies and Environment Setup

#### Task 1.1: Update Requirements and Dependencies
**Files to modify:**
- `requirements.txt`: Add MessageIX packages
- `README.md`: Update installation instructions

**Implementation:**
```txt
# Add to requirements.txt
ixmp>=3.5.0
message_ix>=3.5.0
gamsapi>=1.0.0
python-decouple>=3.6
```

**Tests:**
- Verify package installation in test environment
- Test import statements for new dependencies

#### Task 1.2: Environment Configuration System
**New files to create:**
- `src/config/__init__.py`
- `src/config/settings.py`
- `.env.example`

**Implementation:**
- Use python-decouple for configuration management
- Add GAMS executable path detection
- Implement environment validation

**Tests:**
- Test configuration loading from environment variables
- Test GAMS path detection on different platforms
- Test graceful handling of missing GAMS installation

### Phase 2: MessageIX Integration Core

#### Task 2.1: MessageIX Scenario Manager
**New file to create:**
- `src/managers/messageix_scenario_manager.py`

**Implementation:**
```python
class MessageIXScenarioManager:
    def __init__(self):
        self.ixmp_platform = None

    def create_scenario_from_excel(self, scenario_data: ScenarioData) -> 'ixmp.Scenario':
        """Convert application ScenarioData to MessageIX Scenario"""
        pass

    def solve_scenario(self, scenario: 'ixmp.Scenario', solver_config: dict) -> dict:
        """Execute MessageIX solve with GAMS"""
        pass

    def export_results(self, scenario: 'ixmp.Scenario') -> dict:
        """Extract results for application use"""
        pass
```

**Tests:**
- Test scenario creation from Excel data
- Test conversion of different parameter types
- Test error handling for invalid data

#### Task 2.2: Update Solver Manager
**Files to modify:**
- `src/managers/solver_manager.py`

**Implementation:**
- Replace mock solver calls with MessageIX API
- Add GAMS solver detection
- Implement real-time output capture from MessageIX
- Update `_build_solver_command()` method

**Key changes:**
```python
def get_available_solvers(self) -> List[str]:
    solvers = []

    # Check for GAMS through MessageIX
    try:
        import gamsapi
        solvers.append("gams")
    except ImportError:
        pass

    # Existing solver checks...
    return solvers or ["gams"]  # Default to GAMS if available
```

**Tests:**
- Test GAMS solver detection
- Test solver execution with MessageIX API
- Test error handling for solver failures

### Phase 3: GAMS Execution Integration

#### Task 3.1: GAMS Solver Implementation
**New file to create:**
- `src/managers/gams_solver.py`

**Implementation:**
```python
class GAMSSolver:
    def __init__(self, gams_path: str = None):
        self.gams_path = gams_path or self._detect_gams_path()

    def solve(self, scenario: 'ixmp.Scenario', config: dict) -> dict:
        """Execute GAMS solve on MessageIX scenario"""
        pass

    def _detect_gams_path(self) -> str:
        """Auto-detect GAMS installation path"""
        pass
```

**Tests:**
- Test GAMS path detection
- Test solver execution with various configurations
- Test output parsing and status reporting

#### Task 3.2: Solver Configuration UI
**Files to modify:**
- `src/ui/main_window.py`
- New: `src/ui/solver_config_dialog.py`

**Implementation:**
- Add solver selection dropdown with GAMS option
- Create configuration dialog for GAMS parameters
- Add real-time solver status display

**Tests:**
- Test UI updates with solver availability
- Test configuration dialog functionality
- Test status display during solving

### Phase 4: Results Handling and Testing

#### Task 4.1: MessageIX Results Integration
**Files to modify:**
- `src/managers/results_analyzer.py`

**Implementation:**
- Update result loading for MessageIX output format
- Handle variable and equation result parsing
- Add result validation against MessageIX schema

**Key changes:**
```python
def load_results_file(self, file_path: str, progress_callback=None) -> ResultsData:
    """Load results from MessageIX scenario or Excel file"""
    # Support both Excel and MessageIX scenario results
    pass
```

**Tests:**
- Test loading MessageIX scenario results
- Test conversion to application data format
- Test result validation

#### Task 4.2: Integration Testing
**Files to modify/create:**
- `tests/test_messageix_integration.py`
- `tests/test_gams_solver.py`
- Update existing solver tests

**Implementation:**
- Add comprehensive integration tests
- Create test scenarios with known solutions
- Test end-to-end workflow

**Tests:**
- Full workflow tests: Excel → MessageIX → GAMS → Results
- Error condition testing
- Performance benchmarking

### Phase 5: Documentation and User Experience

#### Task 5.1: Documentation Updates
**Files to modify:**
- `README.md`: Add MessageIX/GAMS setup section
- `docs/`: Add troubleshooting guides
- New: `docs/MESSAGEIX_SETUP.md`

**Implementation:**
- Installation instructions for MessageIX and GAMS
- Configuration troubleshooting
- Usage examples

#### Task 5.2: UI Enhancements
**Files to modify:**
- Various UI components

**Implementation:**
- Add MessageIX status indicators
- Improve progress reporting
- Add solver availability status

**Tests:**
- UI testing for new components
- User experience validation

## Module Dependencies and Refactoring

### Files Requiring Modification

| File | Changes | Impact |
|------|---------|---------|
| `src/managers/solver_manager.py` | Replace mock with MessageIX API | High |
| `src/managers/results_analyzer.py` | Add MessageIX result format | Medium |
| `src/ui/main_window.py` | Add solver configuration UI | Medium |
| `requirements.txt` | Add MessageIX dependencies | Low |
| `README.md` | Update installation docs | Low |

### New Files to Create

| File | Purpose | Dependencies |
|------|---------|--------------|
| `src/managers/messageix_scenario_manager.py` | MessageIX scenario handling | ixmp, message_ix |
| `src/managers/gams_solver.py` | GAMS-specific operations | gamsapi |
| `src/config/settings.py` | Configuration management | python-decouple |
| `src/ui/solver_config_dialog.py` | Solver configuration UI | PyQt5 |
| `tests/test_messageix_integration.py` | Integration tests | pytest |

### Refactoring Considerations

1. **Solver Manager Abstraction**: Extract solver interface to allow multiple solver implementations
2. **Configuration Management**: Centralize all configuration in config module
3. **Error Handling**: Enhance error handling for MessageIX-specific errors
4. **Progress Reporting**: Improve progress callbacks for long-running operations

## Testing Strategy

### Unit Tests
- Individual component functionality
- Mock MessageIX API for testing
- Error condition handling

### Integration Tests
- End-to-end workflow testing
- MessageIX scenario creation and solving
- Result processing and display

### Performance Tests
- Large model loading and solving
- Memory usage monitoring
- Execution time benchmarking

## Risk Assessment and Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| MessageIX API changes | High | Version pinning, abstraction layer |
| GAMS licensing issues | High | Graceful fallback, clear error messages |
| Performance with large models | Medium | Progress indicators, background processing |
| Cross-platform GAMS compatibility | Medium | Comprehensive testing, user guidance |

### Implementation Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex integration | High | Phased implementation, thorough testing |
| Breaking existing functionality | Medium | Maintain backward compatibility |
| User adoption challenges | Medium | Clear documentation, migration guides |

## Success Criteria

- [ ] MessageIX scenarios can be created from Excel input files
- [ ] GAMS solver executes successfully on MessageIX models
- [ ] Results are properly loaded and displayed
- [ ] Application maintains backward compatibility
- [ ] Comprehensive test coverage (>80%)
- [ ] Clear documentation for users

## Timeline Estimate

- **Phase 1**: 1-2 weeks (Dependencies and setup)
- **Phase 2**: 2-3 weeks (Core MessageIX integration)
- **Phase 3**: 2-3 weeks (GAMS execution)
- **Phase 4**: 1-2 weeks (Results and testing)
- **Phase 5**: 1 week (Documentation and polish)

**Total Estimate**: 7-11 weeks for complete implementation

## Open Questions

1. Should we support MessageIX versions older than 3.5?
2. How to handle GAMS licensing for users?
3. What level of solver configuration options to expose?
4. Should we include sample MessageIX models for testing?
5. How to handle very large models (>1GB RAM)?

---

*This document serves as the implementation roadmap for MessageIX/GAMS integration. All tasks should be reviewed and approved before proceeding with Phase 1 implementation.*
