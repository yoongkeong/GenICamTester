import React, { useEffect, useState, useRef } from 'react';
import { Camera } from '../types';

interface LiveViewProps {
    camera: Camera;
}

const LiveView: React.FC<LiveViewProps> = ({ camera }) => {
    const [isStreaming, setIsStreaming] = useState(false);
    const [status, setStatus] = useState<string>('Ready');
    const [error, setError] = useState<string>('');
    const wsRef = useRef<WebSocket | null>(null);
    const imageRef = useRef<HTMLImageElement | null>(null);

    // Reset state when camera changes
    useEffect(() => {
        if (wsRef.current) {
            stopStream();
        }
        setStatus('Ready');
        setError('');
    }, [camera]);

    useEffect(() => {
        return () => {
            if (wsRef.current) {
                stopStream();
            }
        };
    }, []);

    const startStream = () => {
        try {
            console.log('Starting stream for camera:', camera.id);
            const ws = new WebSocket(`ws://localhost:8000/ws/${camera.id}`);
            wsRef.current = ws;
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                setStatus('Connected');
                setError('');
                ws.send(JSON.stringify({ command: 'start_stream' }));
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                console.log('Received message:', message.type);
                if (message.type === 'frame') {
                    if (imageRef.current) {
                        imageRef.current.src = `data:image/jpeg;base64,${message.data}`;
                    }
                } else if (message.status === 'streaming_started') {
                    setIsStreaming(true);
                    setStatus('Streaming');
                } else if (message.status === 'streaming_stopped') {
                    setIsStreaming(false);
                    setStatus('Stopped');
                } else if (message.error) {
                    setError(message.error);
                    setIsStreaming(false);
                    setStatus('Error');
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                setStatus('Connection error');
                setError('Failed to connect to camera');
                setIsStreaming(false);
            };

            ws.onclose = () => {
                console.log('WebSocket closed');
                setStatus('Disconnected');
                setIsStreaming(false);
                wsRef.current = null;
            };
        } catch (err) {
            console.error('Failed to start stream:', err);
            setError(`Failed to start stream: ${err.message}`);
            setStatus('Error');
        }
    };

    const stopStream = () => {
        try {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ command: 'stop_stream' }));
            }
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            setIsStreaming(false);
            setStatus('Ready');
        } catch (err) {
            console.error('Error stopping stream:', err);
            setError(`Failed to stop stream: ${err.message}`);
        }
    };

    return (
        <div className="live-view">
            <div className="stream-controls">
                <h3>Camera: {camera.name}</h3>
                <div className="status-bar">
                    <span>Status: {status}</span>
                    {error && <span className="error">{error}</span>}
                </div>
                <div className="controls">
                    {!isStreaming ? (
                        <button onClick={startStream} className="start-button">
                            Start Stream
                        </button>
                    ) : (
                        <button onClick={stopStream} className="stop-button">
                            Stop Stream
                        </button>
                    )}
                </div>
            </div>
            <div className="stream-container">
                <img ref={imageRef} alt="Camera stream" className="stream-image" />
            </div>
        </div>
    );
};

export default LiveView;
