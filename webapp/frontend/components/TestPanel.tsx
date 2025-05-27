import React, { useState } from 'react';
import { Camera, TestConfig, TestResult } from '../types';

interface TestPanelProps {
    camera: Camera;
    onTestComplete: (results: TestResult[]) => void;
}

const testCategories = {
    basic: {
        title: "Basic Tests",
        tests: [
            { id: 'initialization', name: 'Camera Initialization', default: true },
            { id: 'image_acquisition', name: 'Image Acquisition', default: true },
            { id: 'feature_access', name: 'Feature Access', default: true },
        ]
    },
    functional: {
        title: "Functional Tests",
        tests: [
            { id: 'blur_detection', name: 'Blur Detection', default: false },
            { id: 'edge_detection', name: 'Edge Detection', default: false },
            { id: 'camera_calibration', name: 'Camera Calibration', default: false },
        ]
    },
    performance: {
        title: "Performance Tests",
        tests: [
            { id: 'long_run', name: 'Long Run Test', default: false },
            { id: 'max_fps', name: 'Max FPS Test', default: false },
            { id: 'power_cycle', name: 'Power Cycle Test', default: false },
        ]
    },
    advanced: {
        title: "Advanced Tests",
        tests: [
            { id: 'multicam', name: 'Multi-Camera Test', default: false },
            { id: 'roi', name: 'ROI Testing', default: false },
            { id: 'io_test', name: 'I/O Test', default: false },
            { id: 'image_quality', name: 'Image Quality', default: true },
        ]
    }
};

const TestPanel: React.FC<TestPanelProps> = ({ camera, onTestComplete }) => {
    const [selectedTests, setSelectedTests] = useState<string[]>(
        Object.values(testCategories)
            .flatMap(category => category.tests)
            .filter(test => test.default)
            .map(test => test.id)
    );
    const [running, setRunning] = useState(false);
    const [error, setError] = useState<string>();

    const handleTestSelection = (testId: string) => {
        setSelectedTests(prev => 
            prev.includes(testId) 
                ? prev.filter(id => id !== testId)
                : [...prev, testId]
        );
    };

    const runTests = async () => {
        setRunning(true);
        setError(undefined);
        
        try {
            // First initialize the camera
            const initResponse = await fetch(`http://localhost:8000/api/test/run`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    camera_id: camera.id,
                    tests: ['init'],
                    parameters: {}
                })
            });

            const initData = await initResponse.json();
            if (initData.status !== 'success') {
                throw new Error(initData.message || 'Failed to initialize camera');
            }

            // Then run the selected tests
            const response = await fetch(`http://localhost:8000/api/test/run`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    camera_id: camera.id,
                    tests: selectedTests,
                    parameters: {}
                })
            });

            const data = await response.json();
            if (data.status === 'success') {
                onTestComplete(data.results);
            } else {
                throw new Error(data.message || 'Test execution failed');
            }
        } catch (err) {
            console.error('Test execution error:', err);
            setError(err.message || 'Failed to run tests');
        } finally {
            setRunning(false);
        }
    };

    return (
        <div className="test-panel">
            <h2>Test Controls</h2>
            {error && <div className="error-message">{error}</div>}
            <div className="test-categories">
                {Object.entries(testCategories).map(([category, { title, tests }]) => (
                    <div key={category} className="test-category">
                        <h3>{title}</h3>
                        <div className="test-list">
                            {tests.map(test => (
                                <label key={test.id} className="test-item">
                                    <input
                                        type="checkbox"
                                        checked={selectedTests.includes(test.id)}
                                        onChange={() => handleTestSelection(test.id)}
                                        disabled={running}
                                    />
                                    {test.name}
                                </label>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
            <div className="test-controls">
                <button 
                    onClick={runTests} 
                    disabled={running || selectedTests.length === 0}
                    className={running ? 'running' : ''}
                >
                    {running ? 'Running Tests...' : 'Start Tests'}
                </button>
            </div>
        </div>
    );
};

export default TestPanel;