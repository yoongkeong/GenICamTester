import React, { useEffect, useState } from 'react';
import { Camera } from '../types';

interface CameraListProps {
    onSelectCamera: (camera: Camera) => void;
    selectedCamera?: Camera;
}

const CameraList: React.FC<CameraListProps> = ({ onSelectCamera, selectedCamera }) => {
    const [cameras, setCameras] = useState<Camera[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string>();
    const [message, setMessage] = useState<string>();

    useEffect(() => {
        fetchCameras();
    }, []);

    const fetchCameras = async () => {
        try {
            setLoading(true);
            setError(undefined);
            setMessage(undefined);
            
            const response = await fetch('http://localhost:8000/api/cameras');
            const data = await response.json();
            
            if (data.status === 'success' || data.status === 'warning') {
                setCameras(data.cameras);
                setMessage(data.message);
            } else {
                setError(data.message || 'Failed to load cameras');
            }
        } catch (err) {
            setError('Error connecting to server');
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="camera-list loading">Loading cameras...</div>;
    if (error) return (
        <div className="camera-list error">
            <h2>Error</h2>
            <p className="error-message">{error}</p>
            <button onClick={fetchCameras} className="refresh-button">
                Try Again
            </button>
        </div>
    );

    return (
        <div className="camera-list">
            <h2>Available Cameras</h2>
            {message && <p className="status-message">{message}</p>}
            <button onClick={fetchCameras} className="refresh-button">
                Refresh Camera List
            </button>
            <div className="camera-grid">
                {cameras.length === 0 ? (
                    <div className="no-cameras">
                        <p>No cameras detected</p>
                        <p>Please connect a camera and click refresh</p>
                    </div>
                ) : (
                    cameras.map(camera => (
                        <div
                            key={camera.id}
                            className={`camera-item ${selectedCamera?.id === camera.id ? 'selected' : ''}`}
                            onClick={() => onSelectCamera(camera)}
                        >
                            <h3>{camera.name}</h3>
                            <p className="camera-info">ID: {camera.id}</p>
                            <p className="camera-info">Interface: {camera.interface}</p>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default CameraList;