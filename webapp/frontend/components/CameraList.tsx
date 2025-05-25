import React, { useEffect, useState } from 'react';
import { Camera } from '../types';
import LiveView from './LiveView';

interface CameraListProps {
    onSelectCamera: (camera: Camera) => void;
    selectedCamera?: Camera;
}

const CameraList: React.FC<CameraListProps> = ({ onSelectCamera, selectedCamera }) => {
    const [cameras, setCameras] = useState<Camera[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string>();
    const [streaming, setStreaming] = useState(false);
    const [ws, setWs] = useState<WebSocket | null>(null);
    const [imageData, setImageData] = useState<string>();
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        fetchCameras();
    }, []);

    const fetchCameras = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/cameras');
            const data = await response.json();
            if (data.status === 'success') {
                setCameras(data.cameras);
            } else {
                setError('Failed to load cameras');
            }
        } catch (err) {
            setError('Error connecting to server');
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div>Loading cameras...</div>;
    if (error) return <div className="error">{error}</div>;

    return (
        <div className="camera-container">
            <div className="camera-list">
                <h2>Available Cameras</h2>
                <div className="camera-grid">
                    {cameras.length === 0 ? (
                        <div>No cameras detected</div>
                    ) : (
                        cameras.map(camera => (
                            <div 
                                key={camera.id}
                                className={`camera-item ${selectedCamera?.id === camera.id ? 'selected' : ''}`}
                                onClick={() => onSelectCamera(camera)}
                            >
                                <h3>{camera.name}</h3>
                                <p>Interface: {camera.interface}</p>
                                {camera.model && <p>Model: {camera.model}</p>}
                                <div className="camera-status">
                                    <span className={`status-indicator ${camera.status}`} />
                                    {camera.status}
                                </div>
                            </div>
                        ))
                    )}
                </div>
                <button onClick={fetchCameras} className="refresh-button">
                    Refresh Camera List
                </button>
            </div>
            {selectedCamera && <LiveView camera={selectedCamera} />}
        </div>
    );
};

export default CameraList;