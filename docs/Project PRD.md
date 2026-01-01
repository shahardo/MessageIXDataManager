# Product Requirements Document: message_ix Data Manager

## 1. Executive Summary

### 1.1 Product Overview
The message_ix Data Manager is a desktop application designed to streamline the workflow of energy systems modelers working with the message_ix framework. It provides an intuitive graphical interface for viewing and editing input parameters, executing model runs, and analyzing and comparing results through interactive visualizations.

### 1.2 Problem Statement
Currently, working with message_ix requires:
- Manual editing of Excel files with complex parameter structures
- Command-line execution of solvers
- Separate tools for result analysis and visualization
- Difficulty in comparing multiple scenario runs

This fragmented workflow leads to inefficiencies, errors, and barriers to adoption for non-technical users.

### 1.3 Objectives
- Reduce time to configure and execute message_ix models by 60%
- Enable non-programmers to work effectively with message_ix
- Provide immediate visual feedback on model results
- Facilitate scenario comparison and sensitivity analysis

---

## 2. User Personas

### 2.1 Primary Persona: Energy Systems Analyst
- **Background**: PhD or Master's in energy/environmental engineering
- **Technical Skills**: Moderate programming (Python basics), strong Excel
- **Goals**: Run multiple scenarios, compare policy impacts, create visualizations for reports
- **Pain Points**: Command-line intimidation, time-consuming data preparation, difficulty tracking parameter changes

### 2.2 Secondary Persona: Research Manager
- **Background**: Senior researcher overseeing modeling projects
- **Technical Skills**: Limited programming, strategic thinker
- **Goals**: Review model configurations, validate results, make quick adjustments
- **Pain Points**: Dependency on technical staff, lack of visibility into model parameters

---

## 3. User Stories

### 3.1 Input Management
- As an analyst, I want to load an Excel input file and see all parameters in a structured view, so I can quickly understand the model configuration
- As an analyst, I want to edit parameter values in a validated form, so I can avoid syntax errors and invalid data
- As an analyst, I want to search and filter parameters, so I can quickly find relevant data in large models
- As an analyst, I want to save my changes back to Excel format, so I can maintain compatibility with existing workflows
- As an analyst, I want to handle several configurations and quickly move from one configuration to another

### 3.2 Model Execution
- As an analyst, I want to trigger the solver with one click, so I don't need to use the command line
- As an analyst, I want to see real-time progress and logs during solving, so I know the status of long-running models
- As an analyst, I want to be notified when the solver completes, so I can work on other tasks during execution

### 3.3 Results Analysis
- As an analyst, I want to load result Excel files and see key metrics immediately, so I can quickly assess model outcomes
- As an analyst, I want to create interactive charts of energy flows, capacity, costs, and emissions, so I can explore the results dynamically
- As an analyst, I want to export visualizations to high-quality images, so I can include them in reports and presentations
- As an analyst, I want to handle several configurations save the results into the proper configuration

### 3.4 Scenario Comparison
- As an analyst, I want to load results from multiple configurations simultaneously, so I can compare different scenarios
- As an analyst, I want to see side-by-side or overlaid visualizations of scenarios, so I can identify differences quickly
- As an analyst, I want to export comparison data to CSV, so I can perform additional analysis in other tools

---

## 4. Functional Requirements

### 4.1 Input File Management (Priority: MUST HAVE)

#### FR-1.1: Load Input File
- System shall support loading message_ix Excel input files (.xlsx, .xls)
- System shall validate file structure and display errors if format is incorrect
- System shall parse all parameter sheets (sets, parameters, mappings)
- Load time shall not be long

#### FR-1.2: Parameter Viewing
- System shall display parameters in a hierarchical tree view organized by category
- System shall provide a tabular view for each parameter with all dimensions visible
- System shall provide a graphical view for each parameter for easy understanting, allowing to browse all dimensions
- System shall support search functionality across parameter names and descriptions
- System shall show parameter metadata (units, dimensions, descriptions)

#### FR-1.3: Parameter Editing
- System shall provide inline editing for parameter values with validation
- System shall support bulk operations (fill, copy, paste)
- System shall validate data types (numeric, string, categorical)
- System shall validate against defined sets and dimensions
- System shall highlight modified cells and track change history

#### FR-1.4: Save Modified Input
- System shall save changes back to Excel format preserving original structure
- System shall compact the Excel file if redundant/empty parameters are found
- System shall create backup of original file before saving
- System shall support "Save As" to create new scenarios
- System shall log all changes with timestamp and user

#### FR-1.5: Configurationi Management
- System shall allow to manage multiple configuration
- System shall allow to create, edit, delete, duplicate, rename configuration
- System shall allow to add description and metadata for each configuration
- System shall allow to assign input and output files to different configurations

### 4.2 Model Execution (Priority: SECONDARY)

#### FR-2.1: Solver Configuration
- System shall detect installed message_ix Python environment
- System shall allow selection of solver (CPLEX, Gurobi, GLPK, etc.)
- System shall expose common solver parameters (time limit, optimality gap, threads)
- System shall validate configuration before execution

#### FR-2.2: Solver Execution
- System shall execute message_ix solver in separate process/thread
- System shall capture and display stdout/stderr in real-time console window
- System shall show progress indicators (elapsed time, iteration count if available)
- System shall allow cancellation of running solve
- System shall handle solver errors gracefully with user-friendly messages

#### FR-2.3: Execution History
- System shall maintain log of all solver runs with timestamp, parameters, and status
- System shall store references to input and output files for each run
- System shall allow re-running previous configurations

### 4.3 Results Analysis (Priority: MUST HAVE)

#### FR-3.1: Load Results
- System shall load message_ix Excel output files
- System shall assign message_ix results to a specific configuration
- System shall parse results into structured data (variables, equations, parameters)
- System shall calculate and display summary statistics automatically
- Load time shall be fast

#### FR-3.2: Key Metrics Dashboard
- System shall display overview dashboard with key indicators:
  - Total system cost
  - Energy mix by year and technology
  - Capacity mix by year and technology
  - Emissions trajectory
  - Resource utilization
- Dashboard shall be customizable (user can select which metrics to display)

#### FR-3.3: Interactive Visualizations
- System shall provide the following chart types:
  - Stacked area charts for energy generation
  - Bar charts for capacity by technology
  - Line charts for time series (emissions, costs)
  - Sankey diagrams for energy flows
  - Geographic maps (if spatial data available)
- All charts shall be interactive (zoom, pan, hover tooltips, legend filtering)
- System shall support exporting charts to PNG, SVG, PDF formats (min 300 DPI)

#### FR-3.4: Data Export
- System shall export filtered result data to CSV/Excel
- System shall export chart data to JSON/CSV/Excel for custom analysis
- System shall support batch export of all visualizations

### 4.4 Scenario Comparison (Priority: SHOULD HAVE)

#### FR-4.1: Multi-File Loading
- System shall support loading 2-10 result configurations simultaneously
- System shall display scenario list with metadata (name, date, key parameters)
- System shall allow renaming, saving and loading scenarios for clarity

#### FR-4.2: Comparative Visualizations
- System shall overlay time series charts from multiple scenarios
- System shall create side-by-side bar charts for cross-scenario comparison
- System shall generate difference/delta charts showing scenario variations
- System shall create comparison tables for key metrics

#### FR-4.3: Scenario Analysis
- System shall calculate and display percentage differences between scenarios
- System shall highlight key differences above user-defined thresholds
- System shall support scenario subtraction to isolate impacts of parameter changes

---

## 5. Non-Functional Requirements

### 5.1 Performance (Priority: MUST HAVE)
- **NFR-1.1**: Application startup time < 10 seconds
- **NFR-1.2**: UI response time < 200ms for all interactions (except file I/O)
- **NFR-1.3**: Support files up to 200MB without crashing
- **NFR-1.4**: Memory usage < 2GB for typical workflows
- **NFR-1.5**: Support concurrent solver execution (up to 3 runs)

### 5.2 Usability (Priority: MUST HAVE)
- **NFR-2.1**: First-time users should complete basic workflow (load, edit, solve, visualize) within 15 minutes without training
- **NFR-2.2**: All functionality accessible within 3 clicks from home screen
- **NFR-2.3**: Provide contextual help and tooltips for all features
- **NFR-2.4**: Support keyboard shortcuts for power users
- **NFR-2.5**: Follow platform UI conventions (Windows/Mac/Linux)

### 5.3 Reliability (Priority: MUST HAVE)
- **NFR-3.1**: Application crash rate < 0.1% of sessions
- **NFR-3.2**: Auto-save work every 5 minutes
- **NFR-3.3**: Recover gracefully from solver crashes
- **NFR-3.4**: Recover gracefully from application crashes, reverting to last save point
- **NFR-3.5**: Validate all user inputs before processing

### 5.4 Compatibility (Priority: SHOULD HAVE)
- **NFR-4.1**: Support Windows 10+, macOS 11+, Ubuntu 20.04+
- **NFR-4.2**: Compatible with message_ix versions 3.0+
- **NFR-4.3**: Support Python 3.8+
- **NFR-4.4**: Excel files compatible with Excel 2016+ and OpenOffice

### 5.5 Maintainability (Priority: SHOULD HAVE)
- **NFR-5.1**: Modular architecture allowing component updates
- **NFR-5.2**: Comprehensive logging for debugging
- **NFR-5.3**: Configuration files for customization without code changes
- **NFR-5.4**: Code coverage > 70%

---

## 6. Technical Requirements

### 6.1 Technology Stack

#### Frontend/GUI Framework
- **Recommended**: Electron + React (cross-platform, modern UI)
- **Alternative**: PyQt6/PySide6 (native Python integration)
- **Rationale**: Need rich interactive visualizations and cross-platform support

#### Data Processing
- **Core**: Python 3.8+ with pandas, openpyxl
- **message_ix Integration**: Direct Python API calls
- **Validation**: pydantic or similar for schema validation

#### Visualization
- **Primary**: Plotly.js (interactive, publication-quality)
- **Alternative**: D3.js for custom visualizations
- **Export**: plotly kaleido for static image export

#### Database (Optional)
- **SQLite** for execution history, configurations, and metadata storage
- **Not for large result datasets** (stay with pandas/files)

### 6.2 Architecture

```
┌─────────────────────────────────────────────┐
│           User Interface Layer              │
│  (Electron/Qt - Responsive Design)          │
├─────────────────────────────────────────────┤
│         Application Logic Layer             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Input   │  │ Solver   │  │ Results  │  │
│  │ Manager  │  │ Manager  │  │ Analyzer │  │
│  └──────────┘  └──────────┘  └──────────┘  │
├─────────────────────────────────────────────┤
│          Data Access Layer                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Excel   │  │ message_ │  │  SQLite  │  │
│  │  I/O     │  │ ix API   │  │ Metadata │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────┘
```

### 6.3 Key Components

#### Input Manager
- Parse Excel files using openpyxl
- Maintain in-memory data model (pandas DataFrames)
- Implement validation rules engine
- Allow for data compactification and removal of empty/redundant datasets
- Handle serialization back to Excel

#### Solver Manager
- Detect message_ix installation
- Configure solver parameters
- Execute as subprocess with IPC
- Monitor execution and capture logs
- Implement timeout and cancellation
- Parse output logs to identify errors
- Suggest help for errors

#### Results Analyzer
- Parse result Excel files
- Calculate derived metrics
- Generate visualization specifications
- Handle multi-file comparisons
- Export functionality

#### Visualization Engine
- Render interactive charts
- Handle user interactions (zoom, filter, select)
- Export to multiple formats
- Theme management for consistent styling

#### Configurations Manager
- Create, edit, save, load and delete configurations
- Assign input and output files to configurations
- Switch between configurations
- Compare configurations

---

## 7. User Interface Requirements

### 7.1 Overall Layout

#### Main Application Window
```
┌────────────────────────────────────────────────────┐
│  [File] [Edit] [Run] [View] [Help]        [?][□][X]│
├────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────────────────────┐ │
│  │             │  │                              │ │
│  │  Project    │  │                              │ │
│  │  Navigator  │  │      Main Content Area       │ │
│  │             │  │                              │ │
│  │  - Inputs   │  │                              │ │
│  │  - Config   │  │                              │ │
│  │  - Results  │  │                              │ │
│  │  - Compare  │  │                              │ │
│  │             │  │                              │ │
│  └─────────────┘  └──────────────────────────────┘ │
├────────────────────────────────────────────────────┤
│  Status: Ready  |  Last Saved: 10:32 AM           │
└────────────────────────────────────────────────────┘
```

### 7.2 Responsive Design
- Minimum window size: 1024x768
- Recommended: 1920x1080
- Support window resizing with adaptive layout
- Collapsible side panels for more workspace
- Full-screen mode for presentations

### 7.3 Key Screens

#### 7.3.1 Input Editor Screen
- Left panel: Parameter tree/list with search
- Center: Spreadsheet-like grid for editing
- Right panel: Parameter metadata and validation messages
- Top toolbar: Save, Undo/Redo, Filter, Bulk operations, Configuration
- Bottom: Status and validation summary

#### 7.3.2 Solver Configuration Screen
- Form-based interface for solver parameters
- Dropdown for solver selection with availability status
- Advanced options in expandable section
- Run button with progress modal during execution
- Console output in collapsible panel

#### 7.3.3 Results Dashboard
- Top: Scenario selector and date range filter, Configuration
- Grid of metric cards (system cost, emissions, etc.)
- Below: Tabbed interface for different visualization types
- Right sidebar: Chart configuration and export options

#### 7.3.4 Comparison Screen
- Top: Scenarios selector (multi-select)
- Left: Metric selector
- Center: Comparative visualization
- Bottom: Difference table with sortable columns

### 7.4 Visual Design
- **Color Scheme**: Professional blue/gray with accent colors for data
- **Typography**: Sans-serif (Roboto, Inter, or system default)
- **Icons**: Material Design or Feather icons for consistency
- **Data Visualization**: ColorBrewer palettes for accessibility
- **Dark Mode**: Optional dark theme for extended use

### 7.5 Accessibility
- WCAG 2.1 Level AA compliance
- Keyboard navigation for all functions
- Screen reader support for key workflows
- High contrast mode support
- Configurable font sizes

---

## 8. Data Formats and Standards

### 8.1 Input Excel Format
- Follow standard message_ix Excel structure
- Support multiple sheets for sets, parameters, mappings
- Required sheets: model, scenario, sets, parameters
- Cell formatting preserved during round-trip

### 8.2 Output Excel Format
- Parse standard message_ix results structure
- Support var_* and equ_* sheets
- Handle multi-dimensional variables

### 8.3 Configuration Files
- JSON format for application settings
- YAML for scenario comparison templates
- INI files for solver configurations

### 8.4 Export Formats
- Visualizations: PNG (300dpi), SVG, PDF
- Data: CSV, Excel, JSON
- Reports: HTML, Markdown

---

## 9. Security and Privacy

### 9.1 Data Security
- All data processing local (no cloud upload required)
- Optional encrypted storage for sensitive scenarios
- No telemetry without explicit user consent

### 9.2 Access Control
- File system permissions for data access
- Optional project-level password protection
- Audit log of all modifications

---

## 10. Success Metrics

### 10.1 Adoption Metrics
- Number of active users per month
- User retention rate (30-day, 90-day)
- Number of models processed per user

### 10.2 Efficiency Metrics
- Average time to complete full workflow (target: < 30 min)
- Reduction in data entry errors (target: 80% reduction)
- Number of scenarios compared per session

### 10.3 Quality Metrics
- User satisfaction score (target: > 4.0/5.0)
- Feature usage rates
- Bug report rate (target: < 5 per 1000 user sessions)

### 10.4 Technical Metrics
- Application crash rate
- Average load time for files
- Memory usage profile

---

## 11. Development Phases

### Phase 1: MVP (Months 1-3)
**Goal**: Core workflow functional

Features:
- Load/view input Excel files (read-only)
- Execute solver with basic configuration
- Load and display results with 3 basic chart types
- Single scenario workflow only

Deliverable: Working prototype for user testing

### Phase 2: Input Editing (Months 4-5)
**Goal**: Enable parameter modification

Features:
- Full editing capability with validation
- Save modified inputs
- Undo/redo functionality
- Parameter search and filtering

Deliverable: Beta version for early adopters

### Phase 3: Advanced Visualization (Months 6-7)
**Goal**: Comprehensive analysis tools

Features:
- Complete chart library (8+ chart types)
- Interactive features (zoom, filter, drill-down)
- Dashboard customization
- Export functionality

Deliverable: Feature-complete for single scenarios

### Phase 4: Comparison & Polish (Months 8-9)
**Goal**: Multi-scenario analysis

Features:
- Load multiple result files
- Comparative visualizations
- Scenario analysis tools
- Performance optimization
- UI/UX refinement

Deliverable: Version 1.0 release candidate

### Phase 5: Production Release (Month 10)
**Goal**: Stable release

Activities:
- Bug fixes from beta testing
- Documentation completion
- Deployment packaging
- User training materials

Deliverable: Version 1.0 production release

---

## 12. Risks and Mitigation

### 12.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| message_ix API changes | High | Medium | Abstract API calls, maintain compatibility layer |
| Large file performance | High | High | Implement lazy loading, pagination, data sampling |
| Cross-platform compatibility | Medium | Medium | Early testing on all platforms, CI/CD for all targets |
| Solver integration complexity | High | Medium | Support multiple solvers, extensive error handling |

### 12.2 User Adoption Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Learning curve too steep | High | Medium | Extensive onboarding, video tutorials, in-app help |
| Resistance to new tools | Medium | Medium | Maintain Excel compatibility, gradual migration path |
| Missing key features | Medium | Medium | User research, beta testing program, feature requests |

### 12.3 Project Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope creep | High | High | Strict prioritization, phase-gated development |
| Resource constraints | Medium | Medium | Focus on MVP, modular architecture for parallel work |
| Dependency on external libraries | Medium | Low | Vendor library assessment, fallback options |

---

## 13. Dependencies and Assumptions

### 13.1 Dependencies
- message_ix framework installed and functioning
- Python environment with required packages
- Solver software (CPLEX, Gurobi, or GLPK)
- Excel-compatible file format

### 13.2 Assumptions
- Users have basic understanding of energy systems modeling
- Users have administrative rights to install software
- Input/output Excel files follow message_ix conventions
- Solver execution time is acceptable for typical models (<4 hours)

---

## 14. Open Questions

1. Should the application support cloud storage integration (Google Drive, OneDrive)?
2. Do we need collaboration features (shared projects, comments)?
3. Should we support custom scripting (Python/JavaScript) for advanced users?
4. What level of customization should be allowed for visualizations?
5. Should we include sensitivity analysis automation?
6. Do we need integration with version control systems (Git)?
7. Should we support real-time solver monitoring (if solver provides API)?

---

## 15. Future Enhancements (Post v1.0)

### Version 1.1
- Automated sensitivity analysis
- Custom report generation
- Template library for common scenarios
- Batch processing for multiple scenarios

### Version 1.2
- Collaborative features (comments, sharing)
- Integration with cloud storage
- Advanced statistics and uncertainty analysis
- Machine learning-assisted parameter tuning

### Version 2.0
- Web-based version for broader accessibility
- API for third-party integrations
- Plugin architecture for extensions
- Real-time collaborative editing

---

## 16. Appendices

### Appendix A: Glossary
- **message_ix**: Open-source framework for integrated assessment modeling
- **Solver**: Optimization engine (CPLEX, Gurobi, GLPK)
- **Parameter**: Input data defining the model (costs, demands, constraints)
- **Variable**: Result data calculated by the solver
- **Scenario**: Specific configuration of parameters representing a future pathway

### Appendix B: References
- message_ix Documentation: https://docs.messageix.org/
- IIASA Energy Program: https://iiasa.ac.at/energy
- Excel file format specifications

### Appendix C: Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-01 | Initial | Initial draft |

---

**Document Status**: Draft for Review  
**Last Updated**: January 1, 2026  
**Next Review**: Upon stakeholder feedback