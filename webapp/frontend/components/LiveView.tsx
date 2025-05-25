import React, { useEffect, useState, useRef } from 'react';
import { Camera } from '../types';

interface LiveViewProps {
  camera: Camera;
}

const LiveView: React.FC<LiveViewProps> = ({ camera }) => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const startStream = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'start_stream' }));
      setIsStreaming(true);
    } else {
      const ws = new WebSocket(`ws://localhost:8000/ws/${camera.id}`);
      
      ws.onopen = () => {
        setStatus('WebSocket connected');
        ws.send(JSON.stringify({ type: 'start_stream' }));
        setIsStreaming(true);
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'frame') {
          if (imageRef.current) {
            imageRef.current.src = `data:image/jpeg;base64,${message.data}`;
          }
        } else if (message.type === 'camera_status') {
          setStatus(message.message);
        }
      };

      ws.onerror = (error) => {
        setStatus('WebSocket error');
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        setStatus('WebSocket closed');
        setIsStreaming(false);
      };

      wsRef.current = ws;
    }
  };

  const stopStream = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop_stream' }));
      setIsStreaming(false);
    }
  };

  return (
    <div className="live-view">
      <h2>Live View</h2>
      <div className="status">{status}</div>
      <div className="stream-controls">
        <button 
          onClick={isStreaming ? stopStream : startStream}
          className={isStreaming ? 'stop' : 'start'}
        >
          {isStreaming ? 'Stop Stream' : 'Start Stream'}
        </button>
      </div>
      <div className="stream-container">
        <img ref={imageRef} alt="Camera Stream" />
      </div>
    </div>
  );
};

export default LiveView;
