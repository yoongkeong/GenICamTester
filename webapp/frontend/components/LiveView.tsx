import React, { useEffect, useState, useRef } from 'react';
import { Camera } from '../types';

interface LiveViewProps {
    camera: Camera;
}

const LiveView: React.FC<LiveViewProps> = ({ camera }) => {
    const [isStreaming, setIsStreaming] = useState(false);
    const [status, setStatus] = useState<string>('');
    const [error, setError] = useState<string>('');
    const wsRef = useRef<WebSocket | null>(null);
    const imageRef = useRef<HTMLImageElement | null>(null);

    useEffect(() => {
        // Cleanup on unmount
        return () => {
            stopStream();
        };
    }, []);

    const startStream = () => {
        try {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ command: 'start_stream' }));
            } else {
                const ws = new WebSocket(`ws://localhost:8000/ws/${camera.id}`);
                wsRef.current = ws;
                
                ws.onopen = () => {
                    setStatus('Connected to camera');
                    setError('');
                    ws.send(JSON.stringify({ command: 'start_stream' }));
                };

                ws.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    if (message.type === 'frame') {
                        if (imageRef.current) {
                            imageRef.current.src = `data:image/jpeg;base64,${message.data}`;
                        }
                    } else if (message.status === 'streaming_started') {
                        setIsStreaming(true);
                        setStatus('Streaming');
                    } else if (message.status === 'streaming_stopped') {
                        setIsStreaming(false);
                        setStatus('Stream stopped');
                    } else if (message.error) {
                        setError(message.error);
                        setIsStreaming(false);
                        setStatus('Error');
                    }
                };

                ws.onerror = (error) => {
                    setStatus('Connection error');
                    setError('WebSocket connection failed');
                    setIsStreaming(false);
                    console.error('WebSocket error:', error);
                };

                ws.onclose = () => {
                    setStatus('Disconnected');
                    setIsStreaming(false);
                    wsRef.current = null;
                };
            }
        } catch (err) {
            setError(`Failed to start stream: ${err.message}`);
            setStatus('Error');
        }
    };

    const stopStream = () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ command: 'stop_stream' }));
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setIsStreaming(false);
        setStatus('Stopped');
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
                        <button onClick={startStream}>Start Stream</button>
                    ) : (
                        <button onClick={stopStream}>Stop Stream</button>
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
