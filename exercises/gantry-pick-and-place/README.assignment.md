# Robot Pick & Place Simulation - Assignment Documentation

## Setup and Running Instructions

### Option 1: Running with Docker Compose

The stack can be launched with the following command:

```bash
# From the project root directory
docker compose up --build
```

This will:
- Build and start the backend service on port 8000
- Build and start the frontend service on port 3000
- Set up networking between services

Access the application at: **http://localhost:3000**

To stop the services:
```bash
docker compose down
```

### Option 2: Running Without Docker

#### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment**:
   > **Note**: Python 3.10 is required for this project.
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the backend server**:
   ```bash
   python api.py
   ```

   The backend will start on **http://localhost:8000**

#### Frontend Setup

1. **Navigate to frontend directory** (in a new terminal):
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Generate Protocol Buffer files**:
   
   First, ensure the backend is running (it generates the proto file automatically). Then generate TypeScript definitions:
   
   ```bash
   npm run codegen
   ```
   
   This runs the buf code generator to create TypeScript types from the proto file located at `../backend/proto/robot_control.proto`.

4. **Run the development server**:
   ```bash
   npm run dev
   ```

   The frontend will start on **http://localhost:3000**

## Design Decisions

### State Machine Architecture
The state machine uses a hierarchical structure with state groups (Home, Picking, Transporting, Placing, SequenceFinished) for clear organization and maintainability.

### Asynchronous Movement
The robot simulator requires repeated calls to `move_to()` until motion completes. This is handled through async/await patterns in the state machine callbacks, with a 0.1-second polling interval to continuously update the position.

### Position Validation
Pydantic models combined with Shapely geometric validation ensure that cube positions remain within table boundaries.

### Deferred Cube Position Updates
Once the robot is positioned above the cube or destination, any changes to those target positions are deferred. The new positions are stored in `next_*` variables and applied while the robot moves to position itself above the target, but once positioned, the coordinates are locked for all subsequent vertical operations in that sequence.

### Home Interrupt Handling
When a "Move Home" command is issued during an active sequence, the system sets a flag (`_move_home_requested`) and waits for the current operation to complete before transitioning to the home state. This ensures the robot completes its current sub-task (e.g., closing gripper) before interrupting.

### Error Display
Operation errors (such as invalid positions or state conflicts) are displayed in a dedicated "System Messages" area at the bottom of the web page.

## Assumptions and Constraints

### Physical Model Assumptions
- **Cube and destination positions** are treated as points in space directly on top of the tables
- **Table tops are at height z=0** in the coordinate system
- **Tables are positioned 10 cm (100 mm) away from the edges** of the 2000mm × 2000mm work area
- **Lifting height is 30 cm (300 mm) above the tables** during transport operations
- **Robot limits**: ±1000mm on each axis (X, Y, Z)

### Operational Constraints
- **Home position z-constraint**: The robot home position cannot be below table level (z ≥ 0)
- **Cube dropping during home interrupt**: The robot is permitted to drop a cube at the home position if its operation is interrupted by a "Move Home" request
- **Collision avoidance not implemented**: The system does not prevent the robot from bumping into hypothetical objects when interrupted by a "Move Home" command
- **Target position deferral**: Once the robot is positioned above the cube or destination, any changes to target positions are deferred until the next sequence begins
