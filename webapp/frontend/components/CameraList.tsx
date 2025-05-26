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
        <div className="camera-list">
            <h2>Available Cameras</h2>
            <button onClick={fetchCameras} className="refresh-button">
                Refresh Camera List
            </button>
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
                            <p>Serial: {camera.id}</p>
                            <p>Interface: {camera.interface}</p>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default CameraList;