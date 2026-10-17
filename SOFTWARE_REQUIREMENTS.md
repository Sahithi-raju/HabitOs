# Software Requirements Specification (SRS)
## HabitOS - AI Smart Habit Tracker

**Version:** 1.0.0  
**Date:** March 24, 2026  
**Author:** Development Team

---

## 1. Introduction

### 1.1 Purpose
HabitOS is an AI-powered habit tracking application designed to help users build and maintain healthy habits through intelligent monitoring, reminders, and analytics. The system provides a comprehensive platform for habit management with real-time tracking, automated reminders, and data-driven insights.

### 1.2 Scope
The application consists of:
- **Backend API**: FastAPI-based REST API with SQLite database
- **Frontend**: HTML/JavaScript single-page application
- **Background Services**: Automated reminder scheduler
- **Authentication System**: JWT-based user management

### 1.3 Definitions, Acronyms, and Abbreviations
- **API**: Application Programming Interface
- **JWT**: JSON Web Token
- **CRUD**: Create, Read, Update, Delete
- **SRS**: Software Requirements Specification
- **UI**: User Interface
- **DB**: Database

---

## 2. Overall Description

### 2.1 Product Perspective
HabitOS is a standalone web application that operates independently. It serves both the API backend and static frontend files, requiring no external dependencies beyond Python and its standard library.

### 2.2 Product Functions
The system shall provide the following high-level functions:
- User registration and authentication
- Habit/task creation and management
- Daily habit logging with progress tracking
- Automated reminder scheduling and notifications
- Statistical analysis and reporting
- AI-powered habit suggestions

### 2.3 User Characteristics
- **Primary Users**: Individuals seeking to build and maintain habits
- **Technical Expertise**: Basic computer literacy required
- **Usage Frequency**: Daily interaction expected
- **Age Range**: 13+ (minimum age for habit formation)

### 2.4 Constraints
- **Technology Stack**: Python 3.11+, FastAPI, SQLite
- **Deployment**: Single-server architecture
- **Database**: SQLite (no external database servers)
- **Authentication**: JWT tokens with 7-day expiration
- **Performance**: Support for up to 1000 concurrent users

---

## 3. Specific Requirements

### 3.1 External Interface Requirements

#### 3.1.1 User Interfaces
- **Web Interface**: Responsive HTML/CSS/JavaScript application
- **API Documentation**: Interactive Swagger UI at `/docs`
- **Authentication**: Login/register forms with validation feedback

#### 3.1.2 Hardware Interfaces
- **Storage**: Local file system for SQLite database
- **Memory**: Minimum 512MB RAM recommended
- **CPU**: Single-core processor minimum

#### 3.1.3 Software Interfaces
- **Operating System**: Windows, macOS, Linux
- **Web Browser**: Modern browsers with JavaScript enabled
- **Python Runtime**: Python 3.11 or higher

#### 3.1.4 Communication Interfaces
- **HTTP/HTTPS**: REST API communication
- **WebSocket**: Future real-time notifications (planned)
- **CORS**: Cross-origin resource sharing enabled

### 3.2 Functional Requirements

#### 3.2.1 Authentication System
**FR-AUTH-001**: User Registration
- The system shall allow new users to register with username, email, and password
- Username shall be 3-40 characters, unique
- Password shall be minimum 6 characters
- Email shall be optional but unique if provided
- System shall hash passwords using SHA-256 with salt
- System shall create default habits and reminders for new users

**FR-AUTH-002**: User Login
- The system shall authenticate users with username/password
- System shall generate JWT tokens valid for 7 days
- System shall return user profile information on successful login

**FR-AUTH-003**: Token Validation
- The system shall validate JWT tokens on protected endpoints
- System shall return 401 for invalid/expired tokens
- System shall extract user ID from valid tokens

#### 3.2.2 Task/Habit Management
**FR-TASK-001**: Task Creation
- The system shall allow users to create custom habits/tasks
- Required fields: name, unit, daily limit
- Optional fields: icon, priority, warning settings
- System shall validate input data

**FR-TASK-002**: Task Retrieval
- The system shall return all active tasks for authenticated users
- System shall order tasks with defaults first, then custom tasks
- System shall include task metadata (limits, priorities, etc.)

**FR-TASK-003**: Task Updates
- The system shall allow modification of task properties
- System shall validate updated data
- System shall preserve creation timestamps

**FR-TASK-004**: Task Deactivation
- The system shall support soft deletion (deactivation) of tasks
- Deactivated tasks shall not appear in active lists
- System shall preserve historical data

#### 3.2.3 Habit Logging
**FR-LOG-001**: Daily Log Creation
- The system shall allow logging habit completion values
- System shall accept date, value, and optional notes
- System shall enforce unique logs per task per date
- System shall validate date format (YYYY-MM-DD)

**FR-LOG-002**: Log Retrieval
- The system shall return logs for specific date ranges
- System shall include task metadata with each log
- System shall calculate completion status (ok/under/over)

**FR-LOG-003**: Bulk Logging
- The system shall support logging multiple habits simultaneously
- System shall validate all entries before saving
- System shall return success/failure status for each entry

#### 3.2.4 Reminder System
**FR-REM-001**: Reminder Creation
- The system shall allow creation of scheduled reminders
- Required fields: label, time (HH:MM), repeat days
- Optional fields: icon, category, sound, notes
- System shall validate time format and day selections

**FR-REM-002**: Reminder Scheduling
- The system shall support daily/weekly repeat patterns
- System shall calculate next occurrence times
- System shall display human-readable schedules

**FR-REM-003**: Reminder Execution
- Background scheduler shall check reminders every minute
- System shall fire reminders at scheduled times
- System shall prevent duplicate firings within 2-minute windows
- System shall log all fired reminders

**FR-REM-004**: Reminder Management
- System shall support enable/disable reminders
- System shall allow snooze and dismiss actions
- System shall track reminder interaction history

#### 3.2.5 Statistics and Analytics
**FR-STATS-001**: Streak Calculation
- The system shall calculate current habit logging streaks
- System shall count consecutive days with any logged activities
- System shall display streak information with motivational messages

**FR-STATS-002**: Weekly Reports
- The system shall generate 7-day productivity reports
- System shall calculate daily productivity scores (0-100)
- System shall provide averages, best/worst days
- System shall support historical week viewing

**FR-STATS-003**: Productivity Scoring
- System shall calculate scores based on habit completion
- For "low warning" habits: score = min(100, (actual/limit) × 100)
- For "high warning" habits: score decreases when exceeding limits
- System shall weight all active habits equally

**FR-STATS-004**: AI Suggestions (Future)
- System shall analyze habit patterns
- System shall provide personalized improvement suggestions
- System shall recommend optimal reminder times

### 3.3 Non-Functional Requirements

#### 3.3.1 Performance Requirements
**NFR-PERF-001**: Response Time
- API responses shall complete within 500ms for simple operations
- Complex queries (statistics) shall complete within 2 seconds
- Background scheduler shall not impact API performance

**NFR-PERF-002**: Concurrent Users
- System shall support 100 simultaneous users
- Database shall handle concurrent read/write operations
- SQLite WAL mode shall be enabled for better concurrency

#### 3.3.2 Security Requirements
**NFR-SEC-001**: Password Security
- Passwords shall be hashed with SHA-256 and random salt
- No plain-text password storage
- Secure comparison using HMAC

**NFR-SEC-002**: Authentication Security
- JWT tokens shall include expiration timestamps
- System shall validate token signatures
- Sensitive endpoints shall require authentication

**NFR-SEC-003**: Data Protection
- User data shall be isolated by user_id
- Foreign key constraints shall prevent data corruption
- Database transactions shall ensure data consistency

#### 3.3.3 Reliability Requirements
**NFR-REL-001**: Data Persistence
- SQLite database shall persist all user data
- System shall handle database connection failures gracefully
- Automatic database initialization on first run

**NFR-REL-002**: Error Handling
- System shall provide meaningful error messages
- API shall return appropriate HTTP status codes
- System shall log errors for debugging

#### 3.3.4 Usability Requirements
**NFR-USAB-001**: User Interface
- Interface shall be responsive and mobile-friendly
- System shall provide clear feedback for all actions
- Error messages shall be user-friendly and actionable

**NFR-USAB-002**: API Documentation
- Interactive API documentation shall be available at `/docs`
- All endpoints shall include example requests/responses
- Schema validation shall prevent invalid data submission

#### 3.3.5 Maintainability Requirements
**NFR-MAINT-001**: Code Structure
- Code shall be organized in modular routers
- Database schema shall support future enhancements
- Configuration shall be environment-variable driven

**NFR-MAINT-002**: Logging
- System shall log important events (reminder firings, errors)
- Background processes shall have configurable log levels
- Logs shall include timestamps and context information

### 3.4 Database Requirements

#### 3.4.1 Schema Requirements
**DB-SCHEMA-001**: Users Table
- Primary key: auto-incrementing integer ID
- Unique constraints on username and email
- Password hash storage with salt
- Timestamps for creation and updates

**DB-SCHEMA-002**: Tasks Table
- Foreign key reference to users
- Support for default and custom tasks
- Soft deletion via is_active flag
- Priority levels (high/medium/low)

**DB-SCHEMA-003**: Habit Logs Table
- Composite unique constraint (user_id, task_id, log_date)
- Value storage as floating-point numbers
- Optional notes field for additional context

**DB-SCHEMA-004**: Reminders Table
- Time storage in HH:MM format
- Repeat days as CSV string (0-6 for Sunday-Saturday)
- Enable/disable flag for active reminders

**DB-SCHEMA-005**: Reminder Logs Table
- Tracks fired reminders to prevent duplicates
- Supports snooze and dismiss actions
- Automatic timestamping

#### 3.4.2 Data Integrity
**DB-INTEGRITY-001**: Foreign Keys
- All foreign key constraints shall be enforced
- Cascade deletes shall preserve referential integrity
- Orphaned records shall be prevented

**DB-INTEGRITY-002**: Data Validation
- Database-level constraints where possible
- Application-level validation for complex rules
- Transaction rollback on validation failures

---

## 4. System Architecture

### 4.1 Architecture Diagram
```
┌─────────────────┐    HTTP/HTTPS    ┌─────────────────┐
│   Web Browser   │◄────────────────►│   FastAPI App   │
│   (Frontend)    │                  │   (Backend)     │
└─────────────────┘                  └─────────────────┘
                                           │
                                           │ SQLite
                                           ▼
                                   ┌─────────────────┐
                                   │   habitos.db    │
                                   │   (Database)    │
                                   └─────────────────┘
                                           ▲
                                           │
                                   ┌─────────────────┐
                                   │  Scheduler      │
                                   │  (Background)   │
                                   └─────────────────┘
```

### 4.2 Component Description

#### 4.2.1 FastAPI Backend
- **Purpose**: Main application server handling all business logic
- **Technology**: FastAPI framework with automatic API documentation
- **Responsibilities**: Request routing, authentication, data processing

#### 4.2.2 SQLite Database
- **Purpose**: Data persistence layer
- **Technology**: SQLite with WAL mode for concurrency
- **Responsibilities**: Data storage and retrieval with ACID compliance

#### 4.2.3 Background Scheduler
- **Purpose**: Automated reminder checking and firing
- **Technology**: Python threading with 60-second intervals
- **Responsibilities**: Time-based event triggering and logging

#### 4.2.4 Frontend Application
- **Purpose**: User interface and interaction
- **Technology**: HTML/CSS/JavaScript
- **Responsibilities**: Data visualization and user input collection

---

## 5. Assumptions and Dependencies

### 5.1 Assumptions
- Users have basic computer literacy
- Internet connectivity is available for web access
- Modern web browsers are used
- Single-user database access patterns (SQLite limitations)

### 5.2 Dependencies
- **Python 3.11+**: Core runtime environment
- **FastAPI**: Web framework and API generation
- **SQLite**: Database engine (built into Python)
- **Web Browser**: For frontend access
- **Operating System**: Windows/macOS/Linux support

---

## 6. Appendices

### 6.1 API Endpoints Summary
```
Authentication:
/api/auth/register (POST)
/api/auth/login (POST)
/api/auth/me (GET)

Tasks:
/api/habits/tasks (GET, POST)
/api/habits/tasks/{id} (PUT, DELETE)

Logging:
/api/habits/logs (GET, POST)
/api/habits/logs/{id} (PUT, DELETE)
/api/habits/bulk-log (POST)

Reminders:
/api/reminders (GET, POST)
/api/reminders/{id} (PUT, DELETE, PATCH)

Statistics:
/api/stats/streak (GET)
/api/stats/weekly (GET)
```

### 6.2 Default Data
**Default Tasks:**
- Eat Food (🍽️, meals, 3.0, high priority)
- Drink Water (💧, glasses, 8.0, high priority)
- Mobile Usage (📱, hours, 3.0, medium priority, inverted)
- Played (⚽, hours, 2.0, low priority, inverted)
- Homework (📚, hours, 2.0, high priority)
- Sleep (😴, hours, 8.0, high priority)

**Default Reminders:**
- Water reminders (08:00, 12:00, 15:00, 21:30)
- Lunch reminder (12:00)
- Homework reminder (17:00)
- Sleep reminder (22:00)

### 6.3 Data Flow Diagrams
See attached UML Activity Diagram for detailed user workflows.

---

**End of Software Requirements Specification**