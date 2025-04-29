import React, { useState } from 'react';
import { Camera, TestConfig, TestResult } from '../types';

interface TestPanelProps {
    camera: Camera;
    onTestComplete: (results: TestResult[]) => void;
}

const availableTests = [
    { id: 'initialization', name: 'Camera Initialization', default: true },
    { id: 'image_acquisition', name: 'Image Acquisition', default: true },
    { id: 'feature_access', name: 'Feature Access', default: true },
    { id: 'roi', name: 'ROI Testing', default: false },
    { id: 'power_usb', name: 'USB Power Test', default: false },
    { id: 'power_gige', name: 'GigE Power Test', default: false },
    { id: 'multicam', name: 'Multi-Camera Test', default: false },
    { id: 'max_fps', name: 'Max FPS Test', default: false },
    { id: 'io_test', name: 'I/O Test', default: false },
    { id: 'image_quality', name: 'Image Quality', default: true },
];

const TestPanel: React.FC<TestPanelProps> = ({ camera, onTestComplete }) => {
    const [selectedTests, setSelectedTests] = useState(
        availableTests.filter(test => test.default).map(test => test.id)
    );
    const [running, setRunning] = useState(false);
    const [progress, setProgress] = useState<{[key: string]: string}>({});

    const toggleTest = (testId: string) => {
        setSelectedTests(current =>
            current.includes(testId)
                ? current.filter(id => id !== testId)
                : [...current, testId]
        );
    };

    const runTests = async () => {
        if (running) return;
        setRunning(true);
        setProgress({});

        try {
            const testConfig: TestConfig = {
                camera_id: camera.id,
                tests: selectedTests
            };

            // Setup WebSocket for real-time updates
            const ws = new WebSocket(`ws://localhost:8000/ws/${camera.id}`);
            ws.onmessage = (event) => {
                const update = JSON.parse(event.data);
                if (update.type === 'test_update') {
                    setProgress(prev => ({
                        ...prev,
                        [update.test_name]: update.status
                    }));
                }
            };

            // Run tests
            const response = await fetch('http://localhost:8000/api/test/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(testConfig),
            });

            const data = await response.json();
            if (data.status === 'success') {
                onTestComplete(data.results);
            }

            ws.close();
        } catch (error) {
            console.error('Test execution failed:', error);
        } finally {
            setRunning(false);
        }
    };

    return (
        <div className="test-panel">
            <h2>Test Configuration</h2>
            <div className="test-grid">
                {availableTests.map(test => (
                    <div key={test.id} className="test-item">
                        <label>
                            <input
                                type="checkbox"
                                checked={selectedTests.includes(test.id)}
                                onChange={() => toggleTest(test.id)}
                                disabled={running}
                            />
                            {test.name}
                        </label>
                        {progress[test.id] && (
                            <span className={`status-badge ${progress[test.id]}`}>
                                {progress[test.id]}
                            </span>
                        )}
                    </div>
                ))}
            </div>
            <div className="test-controls">
                <button 
                    onClick={runTests} 
                    disabled={running || selectedTests.length === 0}
                    className={running ? 'running' : ''}
                >
                    {running ? 'Running Tests...' : 'Start Selected Tests'}
                </button>
            </div>
        </div>
    );
};