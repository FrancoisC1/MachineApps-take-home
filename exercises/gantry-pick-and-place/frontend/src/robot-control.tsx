import React, { useState, useEffect } from 'react';
import { createClient } from '@connectrpc/connect';
import { createConnectTransport } from '@connectrpc/connect-web';

import { API_BASE } from './config';
import { RobotControlService } from './gen/robot_control_connect';
import type { RobotStatus, EmptyOrErrorResponse } from './gen/robot_control_pb';

import './robot-control.css';

interface Position {
  x: number;
  y: number;
  z: number;
}

const parsePosition = (input: string): Position | null => {
  const cleaned = input.replace(/\s/g, '');
  const parts = cleaned.split(',');
  if (parts.length !== 3) return null;
  const [x, y, z] = parts.map(Number);
  if ([x, y, z].some(isNaN)) return null;
  return {x, y, z};
};

const transport = createConnectTransport({ baseUrl: API_BASE });
const client = createClient(RobotControlService, transport);

const useRobotPositionStream = () => {
  const [position, setPosition] = useState<Position | null>(null);
  useEffect(() => {
    const subscribe = async () => {
      try {
        for await (const response of client.robot_position_stream({})) {
          setPosition(response);
        }
      } catch (error: any) {
        setPosition(null);
        // Retry after 1 second
        setTimeout(subscribe, 1000);
      }
    };
    subscribe();
  }, []);
  return position;
};

const useRobotStatusStream = () => {
  const [status, setStatus] = useState<RobotStatus | null>(null);
  useEffect(() => {
    const subscribe = async () => {
      try {
        for await (const response of client.robot_status_stream({})) {
          setStatus(response);
        }
      } catch (error: any) {
        setStatus(null);
        // Retry after 1 second
        setTimeout(subscribe, 1000);
      }
    };
    subscribe();
  }, []);
  return status;
};

const useRobotData = () => {
  const [homePosition, setHomePosition] = useState<Position | null>(null);
  const [cubeStart, setCubeStart] = useState<Position | null>(null);
  const [cubeDestination, setCubeDestination] = useState<Position | null>(null);

  const fetchData = async () => {
    try {
      const home = await client.get_robot_home_position({});
      const start = await client.get_cube_start_position({});
      const dest = await client.get_cube_destination_position({});
      setHomePosition(home);
      setCubeStart(start);
      setCubeDestination(dest);
    } catch (error: any) {
      setHomePosition(null);
      setCubeStart(null);
      setCubeDestination(null);
      // Retry after 1 second
      setTimeout(fetchData, 1000);
    }
  };

  useEffect(() => { fetchData() }, []);

  return { homePosition, cubeStart, cubeDestination, refetch: fetchData };
};

const useErrorHandler = () => {
  const [errorMsg, setErrorMsg] = useState('');
  const handleError = (err: Error) => setErrorMsg(err.message);
  const clearError = () => setErrorMsg('');
  return { errorMsg, handleError, clearError };
};

const withMutation = <T extends any[]>(
  mutation: (...args: T) => Promise<EmptyOrErrorResponse>,
  clearError: () => void,
  handleError: (error: Error) => void,
  refetch: () => Promise<void>
) => {
  return async (...args: T) => {
    clearError();
    try {
      const response = await mutation(...args);
      if (response.error) {
        throw new Error(response.error.message);
      }
      await refetch();
    } catch (error: any) {
      handleError(error);
    }
  };
};

const CoordinateDisplay: React.FC<{ position: Position; label: string }> = ({ position, label }) => (
  <div className="coordinate-display">
    <div className="coordinate-label">{label}</div>
    <div className="coordinate-grid">
      <div className="coordinate-row">
        <span className="axis">X</span>
        <span className="value">{position.x.toFixed(2)}</span>
      </div>
      <div className="coordinate-row">
        <span className="axis">Y</span>
        <span className="value">{position.y.toFixed(2)}</span>
      </div>
      <div className="coordinate-row">
        <span className="axis">Z</span>
        <span className="value">{position.z.toFixed(2)}</span>
      </div>
    </div>
  </div>
);

const ErrorIndicator: React.FC<{ message?: string }> = ({ message = 'Failed to load data' }) => (
  <div className="error-indicator">
    <span className="error-icon">⚠</span>
    <span className="error-text">{message}</span>
  </div>
);

const PositionInput: React.FC<{
  label: string;
  onSubmit: (position: Position) => void;
}> = ({ label, onSubmit }) => {
  const [input, setInput] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    const position = parsePosition(input);
    if (!position) {
      setError('Invalid format. Use: x, y, z');
      return;
    }
    setError('');
    onSubmit(position);
    setInput('');
  };

  return (
    <div className="position-input">
      <label className="input-label">{label}</label>
      <div className="input-group">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="x, y, z"
          className={error ? 'error' : ''}
        />
        <button onClick={handleSubmit} disabled={!input}>
          SET
        </button>
      </div>
      {error && <div className="input-error">{error}</div>}
    </div>
  );
};

const RobotControlPanel: React.FC = () => {
  const { errorMsg, handleError, clearError } = useErrorHandler();
  
  const position = useRobotPositionStream();
  const status = useRobotStatusStream();
  
  const { homePosition, cubeStart, cubeDestination, refetch } = useRobotData();

  const handleSetHome = withMutation(async (pos: Position) => {
    return await client.set_robot_home_position(pos);
  }, clearError, handleError, refetch);

  const handleMoveHome = withMutation(async () => {
    return await client.move_home({});
  }, clearError, handleError, refetch);

  const handleStartSequence = withMutation(async () => {
    return await client.start_sequence({});
  }, clearError, handleError, refetch);

  const handleSetCubeStart = withMutation(async (pos: Position) => {
    return await client.set_cube_start_position(pos);
  }, clearError, handleError, refetch);

  const handleSetCubeDest = withMutation(async (pos: Position) => {
    return await client.set_cube_destination_position(pos);
  }, clearError, handleError, refetch);

  return (
    <div className="robot-control">
      <h1>Robot Control System</h1>
      <div className="control-grid">
        <div className="panel">
          <div className="panel-title">Robot Status</div>
          <div className="status-grid">
            {position ? (
              <CoordinateDisplay position={position} label="Current Position" />
            ) : (
              <ErrorIndicator message="Waiting for position data..." />
            )}
            {status ? (
              <>
                <div className="status-item">
                  <span className="status-label">Gripper</span>
                  <span className={`status-badge ${status.gripperOpen ? 'inactive' : 'active'}`}>
                    {status.gripperOpen ? 'OPEN' : 'CLOSED'}
                  </span>
                </div>
                <div className="status-item">
                  <span className="status-label">Activity</span>
                  <span className={`status-badge ${status.idle ? 'inactive' : 'active'}`}>
                    {status.idle ? 'IDLE' : 'MOVING'}
                  </span>
                </div>
                <div className="status-item">
                  <span className="status-label">State Machine</span>
                  <span className="status-value">{status.stateMachineState.replace('_', ' — ') || '—'}</span>
                </div>
              </>
            ) : (
              <ErrorIndicator message="Waiting for status data..." />
            )}
          </div>
          {homePosition ? (
            <CoordinateDisplay position={homePosition} label="Home Position" />
          ) : (
            <ErrorIndicator message="Waiting for home position..." />
          )}
          <PositionInput
            label="Set New Home Position"
            onSubmit={handleSetHome}
          />
          <div className="action-buttons">
            <button onClick={handleMoveHome}>
              Move to Home
            </button>
            <button onClick={handleStartSequence}>
              Start Sequence
            </button>
          </div>
        </div>
        <div className="panel">
          <div className="panel-title">Cube Configuration</div>
          {cubeStart ? (
            <CoordinateDisplay position={cubeStart} label="Start Position" />
          ) : (
            <ErrorIndicator message="Waiting for cube start position..." />
          )}
          <PositionInput
            label="Set Cube Start Position"
            onSubmit={handleSetCubeStart}
          />
          {cubeDestination ? (
            <CoordinateDisplay position={cubeDestination} label="Destination Position" />
          ) : (
            <ErrorIndicator message="Waiting for cube destination..." />
          )}
          <PositionInput
            label="Set Cube Destination Position"
            onSubmit={handleSetCubeDest}
          />
        </div>
      </div>
      {errorMsg && (
        <div className="error-panel">
          <div className="error-title">System Messages</div>
          <div className="error-content">{errorMsg}</div>
        </div>
      )}
    </div>
  );
};

export default RobotControlPanel;
